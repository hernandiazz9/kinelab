"""Fase 1, tests mínimos: relleno, seguimiento, plausibilidad, encuadre,
pose.npz, estimador con modelos falsos y la corrida completa sobre un clip
sintético. Lo que necesita modelos reales o clips con personas se prueba a mano
(ver ESTADO.md)."""

from __future__ import annotations

import json
import shutil
from datetime import date
from types import SimpleNamespace

import numpy as np
import pytest

from kinelab.ingest.__main__ import ingest_clip
from kinelab.ingest.capture_paths import load_capture_paths
from kinelab.ingest.gate import CaptureJson, Check, Gate, with_checks
from kinelab.perception import keypoints as K
from kinelab.perception.estimator import EstimatorConfig, FrameEstimate, PoseEstimator, PoseNaNError, PreprocessError, _Pose
from kinelab.perception.framing import body_height_px, framing_checks, framing_report
from kinelab.perception.gaps import interpolate_gaps
from kinelab.perception.models import MODELS, ModelError, verify_model
from kinelab.perception.plausibility import Flag, angle_deg, elbow_angles, plausibility_mask
from kinelab.perception.posestore import PoseData, finite_or_none, load_pose, save_pose
from kinelab.perception.run import PerceptionError, run_perception
from kinelab.perception.tracking import SubjectTracker
from kinelab.sport import PerceptionGates
from sports.golf.config import GOLF

H = K.H


def person(x0: float = 0.0, y0: float = 0.0, scale: float = 1.0) -> np.ndarray:
    """Una persona plausible de ~78 unidades de alto, de pie, brazos apenas flexionados."""
    p = np.full((K.J, 2), np.nan)
    pts = {
        H.NOSE: (48, 14), H.HEAD: (48, 10), H.NECK: (48, 28), H.LEFT_EYE: (46, 12), H.RIGHT_EYE: (50, 12),
        H.LEFT_EAR: (44, 13), H.RIGHT_EAR: (52, 13),
        H.LEFT_SHOULDER: (40, 30), H.RIGHT_SHOULDER: (56, 30), H.LEFT_ELBOW: (36, 45), H.RIGHT_ELBOW: (60, 45),
        H.LEFT_WRIST: (34, 58), H.RIGHT_WRIST: (62, 58), H.LEFT_HIP: (43, 55), H.RIGHT_HIP: (53, 55), H.HIP: (48, 55),
        H.LEFT_KNEE: (43, 72), H.RIGHT_KNEE: (53, 72), H.LEFT_ANKLE: (43, 88), H.RIGHT_ANKLE: (53, 88),
        H.LEFT_HEEL: (42, 90), H.RIGHT_HEEL: (54, 90), H.LEFT_BIG_TOE: (44, 91), H.RIGHT_BIG_TOE: (52, 91),
        H.LEFT_SMALL_TOE: (41, 91), H.RIGHT_SMALL_TOE: (55, 91),
    }
    for i, (x, y) in pts.items():
        p[i] = (x0 + x * scale, y0 + y * scale)
    return p


# --- relleno y seguimiento -----------------------------------------------------


def test_interpolate_gaps_fills_short_runs_only_and_never_edges():
    T = 20
    k = np.tile(np.arange(T, dtype=float)[:, None, None], (1, 3, 2))
    k[0] = np.nan  # borde: nunca
    k[5:10] = np.nan  # 5: se rellena
    k[12:18] = np.nan  # 6: no
    out = interpolate_gaps(k, max_gap=5)
    assert np.isnan(out[0]).all()
    np.testing.assert_allclose(out[5:10, 0, 0], np.arange(5, 10))
    assert np.isnan(out[12:18]).all()
    assert np.isnan(k[5:10]).all(), "no muta la entrada"


def test_tracker_picks_largest_then_follows_nearest_and_rejects_jumps():
    big, small = person(scale=1.0), person(x0=200, scale=0.5)
    sc = np.full((2, K.J), 0.9, np.float32)
    tr = SubjectTracker()
    assert tr.push(np.stack([small, big]), sc) == 1, "al arrancar, la más grande"
    # la chica se agranda pero la grande sigue cerca: se sigue a la cercana
    assert tr.push(np.stack([person(x0=200, scale=2.0), person(x0=2, scale=1.0)]), sc) == 1
    # el único candidato salta lejos: cuadro perdido, candidato contado igual
    assert tr.push(np.stack([person(x0=400)]), sc[:1]) is None
    r = tr.result()
    assert r.detected_mask.tolist() == [True, True, False]
    assert r.candidates.tolist() == [2, 2, 1]
    assert np.isnan(r.keypoints[2]).all() and r.scores[2].sum() == 0
    assert r.detection_rate == pytest.approx(2 / 3)
    assert r.keypoints.dtype == np.float32 and r.bbox.shape == (3, 4)


# --- plausibilidad y encuadre ---------------------------------------------------


@pytest.mark.parametrize("deg", [37.0, 112.0, 163.0, 1.0, 179.0])
def test_angle_deg_matches_trigonometry_in_degrees(deg):
    b = np.array([10.0, 20.0])
    a = b + 7.0 * np.array([1.0, 0.0])
    c = b + 3.0 * np.array([np.cos(np.radians(deg)), np.sin(np.radians(deg))])
    assert angle_deg(a, b, c) == pytest.approx(deg, abs=1e-6)
    assert angle_deg(c, b, a) == pytest.approx(deg, abs=1e-6)
    assert angle_deg(a, b, c) > 0.5, "grados, no radianes"


def test_mirror_swaps_elbow_angles_and_mask_flags():
    p = person()
    p[H.LEFT_WRIST] = p[H.LEFT_ELBOW] + (p[H.LEFT_SHOULDER] - p[H.LEFT_ELBOW]) * 0.3 + np.array([1.5, 0])  # codo izq cerrado (~16°)
    k = np.stack([p, p, person()])
    e = elbow_angles(k)
    m = elbow_angles(K.mirror(k, 96))
    np.testing.assert_allclose(m[:, 0], e[:, 1], atol=1e-9)
    np.testing.assert_allclose(m[:, 1], e[:, 0], atol=1e-9)
    assert e[0, 0] < 20 < e[0, 1]
    sc = np.full(k.shape[:2], 0.9)
    mask, counts = plausibility_mask(k, sc)
    assert mask[0] & Flag.ELBOW_RANGE and not (mask[2] & Flag.ELBOW_RANGE)
    assert counts["ELBOW_RANGE"] == 2
    k2 = k.copy()
    k2[1] = np.nan
    mask2, _ = plausibility_mask(k2, sc)
    assert mask2[1] == Flag.MISSING


def test_framing_report_and_checks():
    T = 30
    k = np.stack([person(scale=5.0)] * T)  # ~390 px de alto en un cuadro de 1080
    track = SimpleNamespace(keypoints=k, scores=np.full((T, K.J), 0.9), detected_mask=np.ones(T, bool), candidates=np.ones(T, int), detection_rate=0.85)
    h = body_height_px(k, 120.0)
    assert h.shape == (T,) and h[0] == pytest.approx(390, abs=1)
    rep = framing_report(track, 120.0, 1080, camera_motion_px=0.3)
    assert rep.frac_of_frame == pytest.approx(390 / 1080, abs=0.005)
    checks = framing_checks(rep, PerceptionGates())
    assert [c.id for c in checks] == ["body_height_frac", "detection_rate", "single_subject"]
    assert checks[0].passed is None and "sin medir" in checks[0].reason
    assert checks[1].passed is False and "15 %" in checks[1].reason
    strict = framing_checks(rep, PerceptionGates(body_height_frac_min=0.5, detection_rate_min=0.8))
    assert strict[0].passed is False and "Acercá" in strict[0].reason and strict[1].passed is True


# --- pose.npz y frontera JSON ---------------------------------------------------


def test_pose_roundtrip_and_finite_or_none(tmp_path):
    T = 4
    d = PoseData(np.random.rand(T, K.J, 2).astype(np.float32), np.random.rand(T, K.J).astype(np.float32), np.zeros((T, 4), np.float32), np.arange(T) / 120.0, np.array([0, 1, 0, 8], np.uint8), {"model": "x", "n": np.float64("nan")})
    d.keypoints[1] = np.nan
    save_pose(tmp_path, d)
    with pytest.raises(FileExistsError):
        save_pose(tmp_path, d)
    back = load_pose(tmp_path)
    np.testing.assert_array_equal(back.keypoints, d.keypoints)
    assert back.timestamps_s.dtype == np.float64 and back.plausibility.dtype == np.uint8
    assert back.provenance == {"model": "x", "n": None}
    assert finite_or_none({"a": [1.0, float("inf"), np.float32(np.nan), np.array([1, np.nan])], "b": np.int64(3)}) == {"a": [1.0, None, None, [1.0, None]], "b": 3}


def test_with_checks_inserts_after_and_recomputes_verdict():
    g = Gate(verdict="ok", checks=[Check(id="a", passed=True), Check(id="rotation_normalized", passed=True), Check(id="z", passed=True)], reasons=[])
    g2 = with_checks(g, [Check(id="detection_rate", passed=False, reason="se perdió")], after="rotation_normalized")
    assert [c.id for c in g2.checks] == ["a", "rotation_normalized", "detection_rate", "z"]
    assert g2.verdict == "reject" and g2.reasons == ["se perdió"]
    assert g.verdict == "ok" and len(g.checks) == 3, "no muta"
    g3 = with_checks(g2, [Check(id="detection_rate", passed=True)], after="rotation_normalized")
    assert g3.verdict == "ok" and [c.id for c in g3.checks] == ["a", "rotation_normalized", "detection_rate", "z"]


# --- estimador con modelos falsos -------------------------------------------------


class FakeDet:
    def __init__(self, boxes):
        self.boxes, self.calls = boxes, 0

    def __call__(self, frame):
        self.calls += 1
        b = np.asarray(self.boxes, np.float32).reshape(-1, 4)
        return b, np.zeros(len(b), int)


class FakePose:
    def __init__(self):
        self.calls = 0

    def __call__(self, frame, bboxes):
        self.calls += 1
        n = len(bboxes)
        return np.stack([person(scale=0.9)] * n), np.full((n, K.J), 0.9, np.float32)


def test_estimator_phantom_guard_and_detector_frequency():
    est = PoseEstimator.from_models(FakeDet([]), FakePose(), EstimatorConfig(det_frequency=5))
    frame = np.zeros((96, 96, 3), np.uint8)
    for _ in range(5):
        fe = est(frame)
        assert fe.keypoints.shape == (0, K.J, 2)
    assert est.det.calls == 5 and est.pose.calls == 0, "sin cajas: detector siempre, pose nunca"
    est2 = PoseEstimator.from_models(FakeDet([[30, 5, 70, 95]]), FakePose(), EstimatorConfig(det_frequency=5))
    for _ in range(10):
        fe = est2(frame)
    assert fe.keypoints.shape == (1, K.J, 2) and est2.det.calls == 2 and est2.pose.calls == 10
    assert set(est2.provenance()) >= {"model", "checkpoint_sha256", "keypoint_set", "input_size", "detector", "detector_sha256", "provider", "onnxruntime_version", "engine_version"}


def test_pose_guards_preprocess_and_nan():
    class NaNSession:
        def get_inputs(self):
            return [SimpleNamespace(name="input")]

        def run(self, _, feeds):
            return [np.full((1, K.J, 384), np.nan, np.float32), np.zeros((1, K.J, 512), np.float32)]

    p = _Pose(NaNSession(), (192, 256), "falso")
    with pytest.raises(PreprocessError):
        p.inference(np.full((256, 192, 3), 200.0))
    with pytest.raises(PoseNaNError):
        p.inference(np.zeros((256, 192, 3)))


def test_verify_model_rejects_wrong_hash(tmp_path, monkeypatch):
    monkeypatch.setenv("KINELAB_MODELS", str(tmp_path))
    spec = MODELS["yolox-m-coco"]
    with pytest.raises(ModelError, match="Falta"):
        verify_model(spec)
    (tmp_path / spec.filename).write_bytes(b"no es el modelo")
    with pytest.raises(ModelError, match="sha256"):
        verify_model(spec)


# --- corrida completa con estimador falso ------------------------------------------


class FakeEstimator:
    def __init__(self, detect: bool):
        self.detect, self.sizes = detect, []

    def reset(self):
        pass

    def __call__(self, frame):
        self.sizes.append(frame.shape[:2])
        if not self.detect:
            return FrameEstimate(np.zeros((0, K.J, 2), np.float32), np.zeros((0, K.J), np.float32), np.zeros((0, 4), np.float32), True)
        return FrameEstimate(person()[None].astype(np.float32), np.full((1, K.J), 0.9, np.float32), np.array([[30, 5, 70, 95]], np.float32), True)

    def provenance(self):
        return {"model": "falso", "provider": "falso"}


def _take(clips, capture_paths_yaml, tmp_path, key="hevc120"):
    if key not in clips:
        pytest.skip(f"fixture {key} no disponible")
    paths = load_capture_paths(capture_paths_yaml)
    take, cap = ingest_clip(clips[key], athlete="t", gesture="driver", view="face_on", capture_path_id="test-hevc-120-cfr", capture_paths=paths, sport=GOLF, data_dir=tmp_path, day=date(2026, 9, 12))
    assert cap.gate.verdict == "ok", cap.gate.reasons
    return take


def test_run_perception_ok_and_timestamps(clips, capture_paths_yaml, tmp_path):
    take = _take(clips, capture_paths_yaml, tmp_path)
    res = run_perception(take, GOLF, estimator=FakeEstimator(True))
    assert res.frames == 480 and res.gate.verdict == "ok", res.gate.reasons
    d = load_pose(take)
    assert d.keypoints.shape == (480, K.J, 2) and d.timestamps_s[1] - d.timestamps_s[0] == 1.0 / 120.0
    assert d.timestamps_s[-1] == pytest.approx(479 / 120.0)
    assert int(d.plausibility.sum()) == 0
    cj = CaptureJson.model_validate_json((take / "capture.json").read_text(encoding="utf-8"))
    ids = [c.id for c in cj.gate.checks]
    assert ids.index("detection_rate") == ids.index("rotation_normalized") + 2 and ids[-1] == "gesture_known"
    with pytest.raises(PerceptionError, match="ya existe"):
        run_perception(take, GOLF, estimator=FakeEstimator(True))
    assert d.provenance["source_sha256"] == cj.sha256_original and d.provenance["fps_real"] == 120.0


def test_run_perception_without_subject_rejects_but_writes_pose(clips, capture_paths_yaml, tmp_path):
    take = _take(clips, capture_paths_yaml, tmp_path)
    res = run_perception(take, GOLF, estimator=FakeEstimator(False))
    assert res.gate.verdict == "reject" and any("perdió" in r for r in res.gate.reasons)
    d = load_pose(take)
    assert np.isnan(d.keypoints).all() and (d.plausibility == Flag.MISSING).all()


def test_run_perception_applies_rotation(clips, capture_paths_yaml, tmp_path):
    take = _take(clips, capture_paths_yaml, tmp_path, key="hevc120_rot90")
    est = FakeEstimator(True)
    run_perception(take, GOLF, estimator=est)
    assert est.sizes[0] == (64, 96), "el cuadro llega como se ve: 96 de ancho, 64 de alto"


def test_run_perception_refuses_rejected_take(clips, capture_paths_yaml, tmp_path):
    paths = load_capture_paths(capture_paths_yaml)
    take, cap = ingest_clip(clips["real240_h264"], athlete="t", gesture="driver", view="face_on", capture_path_id="test-hevc-120-cfr", capture_paths=paths, sport=GOLF, data_dir=tmp_path, day=date(2026, 9, 12))
    assert cap.gate.verdict == "reject"
    with pytest.raises(PerceptionError, match="rechazó"):
        run_perception(take, GOLF, estimator=FakeEstimator(True))
    assert not (take / "pose.npz").exists()


def test_explore_uses_the_effective_fps_not_the_raw_one(clips, tmp_path):
    """Con un solo delta de arranque, `(n-1)/span` da 28,79 fps y todos los
    tiempos salen 4 % largos. Exploración usa el efectivo: 30,00 (medido en el
    S22 original, 29,436 → 29,998; informe 2026-09-14-03)."""
    from kinelab.explore import explore
    from kinelab.ingest.gate import CaptureJson

    if "first_delta30_h264" not in clips:
        pytest.skip("sin fixture first_delta30_h264")
    r = explore(clips["first_delta30_h264"], tmp_path / "out", GOLF, height_m=1.8, estimator=FakeEstimator(True))
    assert r["fps_archivo"] == pytest.approx(30.0, abs=0.01)
    assert r["cuadros"] == 120

    cj = CaptureJson.model_validate_json((tmp_path / "out" / "capture.json").read_text(encoding="utf-8"))
    assert cj.fps_real == cj.fps_playback == pytest.approx(30.0, abs=0.01)
    assert cj.fps_playback_raw == pytest.approx(28.79, abs=0.05), "el bruto queda a la vista"
    assert cj.vfr_ratio == pytest.approx(1.0, abs=0.01) and cj.vfr_ratio_raw == pytest.approx(6.0, abs=0.05)
    assert cj.first_delta_s == pytest.approx(0.2, abs=1e-3)
    assert cj.fps_note and "arranque de la cámara" in cj.fps_note
    assert cj.duration_s == pytest.approx(4.0, abs=0.01), "120 cuadros a 30 fps"


def test_explore_mode_writes_everything_even_without_a_person(clips, tmp_path):
    """Modo exploración: sin gate; con el clip sintético (nadie) deja overlay, CSV y JSON igual."""
    from kinelab.explore import explore

    if "hevc120" not in clips:
        pytest.skip("sin fixture hevc120")
    r = explore(clips["hevc120"], tmp_path / "out", GOLF, height_m=1.8, estimator=FakeEstimator(True))
    out = tmp_path / "out"
    assert (out / "overlay.mp4").is_file() and (out / "datos-por-cuadro.csv").is_file() and (out / "datos-eventos.json").is_file()
    assert r["cuadros"] == 480 and "elbow_left_deg" in r["columnas"] and "pelvis_dx_vs_address_cm" in r["columnas"]
    assert r["aviso"].startswith("EXPLORACIÓN")
    assert r["eventos_frame"] == {} and r["eventos_subcuadro"] == {}, "sin eventos no hay instante entre cuadros, y la clave está igual"
