"""Fase 2, tests mínimos: eventos sobre swings sintéticos, negativos de
segmentación, registro, contrato, corrección manual y el CLI de punta a punta."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pytest

from kinelab.__main__ import main as kinelab_main
from kinelab.analysis import analyze_take, swing_signals
from kinelab.contract.validate import validate_analysis
from kinelab.events.manual import Edit, EventCollisionError, apply_edits
from kinelab.events.order import sequence_order
from kinelab.events.primitives import subframe_crossing
from kinelab.events.segmentation import SegmentationParams, segment_reps
from kinelab.events.signal import principal_axis
from kinelab.ingest.__main__ import ingest_clip
from kinelab.ingest.capture_paths import load_capture_paths
from kinelab.metrics.registry import Metric, Reference, Registry, judgment_allowed
from kinelab.perception.posestore import PoseData, save_pose
from kinelab.tools.golfdb_eval import event_error_stats
from sports.golf.config import GOLF
from sports.golf.events import GOLF_SEGMENTATION, GOLF_SPORT_EVENTS, detect_golf_events
from tests.helpers.synth_swing import synth_swing

REPO = Path(__file__).resolve().parents[1]


def _pose(sw) -> PoseData:
    T = sw.keypoints.shape[0]
    return PoseData(sw.keypoints, sw.scores, np.zeros((T, 4), np.float32), sw.timestamps_s, np.zeros(T, np.uint8), {"model": "sintético", "framing": {"detection_rate": 1.0, "body_height_px_median": sw.body_height_px, "body_height_px_min": sw.body_height_px, "body_height_px_max": sw.body_height_px, "frac_of_frame": sw.body_height_px / sw.frame[0]}, "plausibility_counts": {}, "camera_motion_px": 0.0})


def _detect(sw):
    sig = swing_signals(_pose(sw), sw.fps)
    cands, rejected = segment_reps(sig.speed, sw.fps, GOLF_SEGMENTATION)
    out = []
    for c in cands:
        ev, reason = detect_golf_events(sig, c)
        assert reason is None, reason
        out.append({k: v.frame if v else None for k, v in ev.items()})
    return out, rejected


@pytest.mark.parametrize("fps,noise,tol", [(120.0, 0.0, (2, 1, 1, 3)), (120.0, 2.0, (3, 2, 2, 4)), (240.0, 0.0, (3, 1, 1, 4))])
def test_golf_events_on_synthetic_swings(fps, noise, tol):
    sw = synth_swing(fps, n_reps=3, noise_px=noise)
    reps, rejected = _detect(sw)
    assert len(reps) == 3, (reps, rejected)
    for got, truth in zip(reps, sw.truth):
        for name, t in zip(("address", "top", "impact", "follow_end"), tol):
            assert abs(got[name] - truth[name]) <= t, f"{name} @ {fps} fps: {got[name]} vs {truth[name]}"


def test_events_are_fps_invariant_in_seconds():
    a = _detect(synth_swing(60.0, n_reps=2))[0]
    b = _detect(synth_swing(240.0, n_reps=2))[0]
    for ra, rb in zip(a, b):
        for name in ("address", "top", "impact"):
            assert abs(ra[name] / 60.0 - rb[name] / 240.0) <= 2 / 60.0, name


def test_still_and_walking_give_zero_reps():
    T, fps = 1200, 120.0
    still = np.zeros(T) + 0.02
    walking = 1.0 + 0.05 * np.sin(np.arange(T) / 7.0)  # velocidad sostenida sin picos
    for s in (still, walking):
        cands, _ = segment_reps(s, fps, GOLF_SEGMENTATION)
        assert cands == []


def test_sequence_order_exclusion_rule():
    assert sequence_order({"pelvis": 10, "torso": 14, "arm": 20}) == "pelvis>torso>arm"
    assert sequence_order({"pelvis": 10, "torso": 11, "arm": 20}) == "indeterminado"


def test_registry_rules_and_judgment():
    r = Registry("t")
    with pytest.raises(ValueError, match="nivel 3"):
        Metric(id="x_factor", unit="deg", level=3, views=("face_on",), fps_min=60, anchored_to=(), reference_frame="image_px")
    m = r.register(Metric(id="sway_cm", unit="cm", level=1, views=("face_on",), fps_min=60, anchored_to=("address", "top"), reference_frame="image_px", mdc=1.5, reference=Reference("range", "pares", "x", "y", range=(0.0, 4.0))))
    ok = dict(view="face_on", fps_real=120, fps_provenance="medido_aqui")
    assert judgment_allowed(m, **ok) is True
    assert judgment_allowed(m, view="down_the_line", fps_real=120, fps_provenance="medido_aqui") is False
    assert judgment_allowed(m, view="face_on", fps_real=30, fps_provenance="medido_aqui") is False
    # ADR-016: con la tasa de cuadros sin verificar no hay juicio, aunque estén
    # el MDC, el fps y la vista. El eje del tiempo es un supuesto.
    assert judgment_allowed(m, view="face_on", fps_real=120, fps_provenance="sin_verificar") is False
    wide = Metric(id="wide", unit="cm", level=1, views=("face_on",), fps_min=60, anchored_to=(), reference_frame="image_px", mdc=5.0, reference=Reference("range", "pares", "x", "y", range=(0.0, 4.0)))
    assert judgment_allowed(wide, **ok) is False, "MDC mayor que el rango: no es juicio"
    with pytest.raises(ValueError, match="repetida"):
        r.register(m)


def test_manual_edits_keep_detected_and_reject_collisions():
    ev = {"id": "top", "frame": 100, "t_s": 1.0, "tol_frames": 1, "uncertainty_s": 0.01, "method": "x", "manual": False, "frame_detected": None}
    mk = lambda rep, base: {"rep": rep, "address": {**ev, "id": "address", "frame": base}, "top": {**ev, "frame": base + 100}, "impact": {**ev, "id": "impact", "frame": base + 130}, "follow_end": None, "sequence_order": "sin_datos"}
    events = [mk(1, 0), mk(2, 500)]
    out = apply_edits(events, [Edit(1, "top", 110, "hoy")], fps=100.0, order=("address", "top", "impact", "follow_end"))
    assert out[0]["top"]["frame"] == 110 and out[0]["top"]["frame_detected"] == 100 and out[0]["top"]["manual"] is True
    assert events[0]["top"]["frame"] == 100, "no muta"
    with pytest.raises(EventCollisionError):
        apply_edits(events, [Edit(1, "top", 130, "hoy")], fps=100.0, order=("address", "top", "impact", "follow_end"))
    with pytest.raises(EventCollisionError):
        apply_edits(events, [Edit(2, "address", 129, "hoy")], fps=100.0, order=("address", "top", "impact", "follow_end"))


def test_golfdb_stats():
    s = event_error_stats({"a": {"top": 10, "impact": 20}, "b": {"top": 30, "impact": 40}}, {"a": {"top": 11, "impact": 20}, "b": {"top": 31, "impact": 43}})
    assert s["top"]["bias_frames"] == 1.0 and s["top"]["within_1"] == 1.0
    assert s["impact"]["within_2"] == 0.5


def _synthetic_take(clips, capture_paths_yaml, tmp_path):
    if "hevc120" not in clips:
        pytest.skip("sin fixture hevc120")
    paths = load_capture_paths(capture_paths_yaml)
    take, cap = ingest_clip(clips["hevc120"], athlete="t", gesture="driver", view="face_on", capture_path_id="test-hevc-120-cfr", capture_paths=paths, sport=GOLF, data_dir=tmp_path, day=date(2026, 9, 12))
    sw = synth_swing(120.0, n_reps=2)
    save_pose(take, _pose(sw))
    return take, sw


def test_analyze_and_adjust_end_to_end(clips, capture_paths_yaml, tmp_path):
    take, sw = _synthetic_take(clips, capture_paths_yaml, tmp_path)
    a = analyze_take(take, GOLF)
    assert (take / "analysis.json").is_file() and validate_analysis(json.loads((take / "analysis.json").read_text())) == []
    assert a["summary"]["rep_count"] == 2 and a["quality"]["verdict"] == "confiable"
    assert a["series"]["params"]["series_hz"] <= 10.0 and a["header"]["source"]["fps_real"] == 120.0
    top = a["events"][0]["top"]["frame"]
    rc = kinelab_main(["adjust", str(take), "--rep", "1", "--event", "top", "--frame", str(top + 3)])
    assert rc == 0
    b = json.loads((take / "analysis.json").read_text())
    assert b["events"][0]["top"]["frame"] == top + 3 and b["events"][0]["top"]["frame_detected"] == top and b["events"][0]["top"]["manual"]
    assert (take / f"analysis.{a['header']['engine_version']}.json").is_file(), "el anterior se conserva"
    rc = kinelab_main(["adjust", str(take), "--rep", "1", "--event", "top", "--frame", str(a["events"][0]["impact"]["frame"])])
    assert rc == 1, "top después del impacto: colisión"
    assert json.loads((take / "analysis.json").read_text())["events"][0]["top"]["frame"] == top + 3, "una corrección inválida no toca nada"


def test_schema_rejects_renamed_field(clips, capture_paths_yaml, tmp_path):
    take, _ = _synthetic_take(clips, capture_paths_yaml, tmp_path)
    a = analyze_take(take, GOLF, write=False)
    a["summary"]["rep_cnt"] = a["summary"].pop("rep_count")
    errs = validate_analysis(json.loads(json.dumps(a, default=lambda o: o.tolist())))
    assert any("rep_cnt" in e for e in errs) and any("rep_count" in e for e in errs)


def test_a_declared_path_keeps_the_numbers_and_kills_every_judgment(clips, capture_paths_yaml, tmp_path):
    """ADR-016 de punta a punta: con la MISMA pose y el MISMO fps, cambiar la
    procedencia de `medido_aqui` a `sin_verificar` no mueve un valor y apaga
    todos los juicios. Y el aviso queda primero en `warnings`."""
    take, _ = _synthetic_take(clips, capture_paths_yaml, tmp_path)
    calibrado = analyze_take(take, GOLF, write=False, height_m=1.80)
    con_mdc = [mid for mid, v in calibrado["reps"][0]["metrics"].items() if v["judgment_allowed"]]
    assert con_mdc, "el fixture tiene que llegar con al menos una métrica de juicio"

    cj = json.loads((take / "capture.json").read_text(encoding="utf-8"))
    cj["capture_path_calibrated"], cj["fps_provenance"] = False, "sin_verificar"
    (take / "capture.json").write_text(json.dumps(cj), encoding="utf-8")
    declarado = analyze_take(take, GOLF, write=False, height_m=1.80)

    a, b = calibrado["reps"][0]["metrics"], declarado["reps"][0]["metrics"]
    assert [a[mid]["value"] for mid in a] == [b[mid]["value"] for mid in a], "la medición no cambia"
    assert all(not v["judgment_allowed"] for v in b.values())
    assert all(v["fps_provenance"] == "sin_verificar" for v in b.values())
    assert declarado["header"]["source"]["fps_provenance"] == "sin_verificar"
    assert declarado["warnings"][0].startswith("Tasa de cuadros sin verificar")
    assert "reproduce a la velocidad de captura" in declarado["warnings"][0]
    assert not any(w.startswith("Tasa de cuadros sin verificar") for w in calibrado["warnings"])


def test_schema_requires_fps_provenance_in_header_and_in_every_metric(clips, capture_paths_yaml, tmp_path):
    """ADR-016: la procedencia del fps no es opcional. Un `analysis.json` sin
    ella no valida — ni en el header ni en una métrica —, así que no puede
    escribirse un análisis que esconda bajo qué supuesto se midió el tiempo."""
    take, _ = _synthetic_take(clips, capture_paths_yaml, tmp_path)
    a = json.loads(json.dumps(analyze_take(take, GOLF, write=False, height_m=1.80), default=lambda o: o.tolist()))
    assert validate_analysis(a) == []

    sin_header = json.loads(json.dumps(a))
    del sin_header["header"]["source"]["fps_provenance"]
    assert any("fps_provenance" in e for e in validate_analysis(sin_header))

    sin_metrica = json.loads(json.dumps(a))
    mid = next(iter(sin_metrica["reps"][0]["metrics"]))
    del sin_metrica["reps"][0]["metrics"][mid]["fps_provenance"]
    assert any("fps_provenance" in e for e in validate_analysis(sin_metrica))

    mal = json.loads(json.dumps(a))
    mal["header"]["source"]["fps_provenance"] = "a_ojo"
    assert any("a_ojo" in e for e in validate_analysis(mal)), "procedencia fuera del enum"


def test_repo_example_is_valid():
    p = REPO / "data" / "examples" / "analysis.example.json"
    if not p.is_file():
        pytest.skip("todavía no se generó el ejemplo")
    assert validate_analysis(json.loads(p.read_text(encoding="utf-8"))) == []


def test_metrics_in_analysis(clips, capture_paths_yaml, tmp_path):
    take, sw = _synthetic_take(clips, capture_paths_yaml, tmp_path)
    a = analyze_take(take, GOLF, write=True, height_m=1.80)
    assert validate_analysis(json.loads((take / "analysis.json").read_text())) == []
    m = a["reps"][0]["metrics"]
    bs = m["backswing_duration_ms"]
    assert abs(bs["value"] - 900.0) <= 25 and bs["unit"] == "ms" and bs["null_reason"] is None
    assert bs["judgment_allowed"] is (bs["mdc"] is not None), "juicio sólo con MDC de la tabla del arnés"
    # La procedencia del fps viaja en cada métrica y en el header (ADR-016).
    assert bs["fps_provenance"] == "medido_aqui" and "medido_aqui" in bs["uncertainty"]["method"]
    assert a["header"]["source"]["fps_provenance"] == "medido_aqui"
    assert all(m[mid]["fps_provenance"] == "medido_aqui" for mid in m)
    assert bs["uncertainty"]["low"] < bs["value"] < bs["uncertainty"]["high"]
    assert m["pelvis_thrust_top_cm"]["value"] is None and "down_the_line" in m["pelvis_thrust_top_cm"]["null_reason"]
    assert abs(m["pelvis_sway_top_cm"]["value"]) < 1.0, "la pelvis sintética no se mueve"
    assert a["summary"]["metrics"]["backswing_duration_ms"]["repeatability"]["kind"] == "sd_abs"
    assert a["summary"]["metrics"]["hands_speed_curve_top_to_impact"]["repeatability"]["n"] == 2
    assert "pelvis_to_torso" in a["summary"]["gain"]
    b = analyze_take(take, GOLF, write=False)
    assert b["reps"][0]["metrics"]["pelvis_sway_top_cm"]["value"] is None and "altura" in b["reps"][0]["metrics"]["pelvis_sway_top_cm"]["null_reason"]


# --- instante sub-cuadro del impacto (encargo 02) -----------------------------------
#
# El cuadro entero del impacto NO cambia: sigue siendo el de `peak_window`. Lo que se
# prueba acá es el instante estimado ENTRE dos cuadros, contra una verdad que no sabe
# nada de cómo se estima (`synth_swing` la calcula por mínima distancia sobre el modelo
# continuo). El swing lleva `hands_tilt` y `hands_miss_px`: sin ellos el arco de bajada
# pasa exactamente por el punto de address y cualquier eje da el mismo cruce, así que el
# test no distinguiría ningún bug (invariante 15).

SUBFRAME_TOL_FRAMES = 0.1  # cuadros: el error del estimador sin ruido, con margen


def _impact_subframe(sw, view: str = "face_on"):
    """(señal, eventos) de la primera repetición de un swing sintético."""
    sig = swing_signals(_pose(sw), sw.fps, view=view)
    cands, rejected = segment_reps(sig.speed, sw.fps, GOLF_SEGMENTATION)
    assert cands, rejected
    events, reason = detect_golf_events(sig, cands[0])
    assert reason is None, reason
    return sig, events


def test_impact_subframe_lands_on_the_known_crossing():
    """Cruce conocido en 71,56 (fracción 0,6 entre el 71 y el 72) a 30 fps."""
    sw = synth_swing(30.0, n_reps=2, hands_tilt=0.2, hands_miss_px=100.0)
    _, events = _impact_subframe(sw)
    impact = events["impact"]
    sf = impact.subframe
    truth = sw.truth[0]["impact_cross"]
    assert sf["null_reason"] is None and sf["fraction"] is not None
    assert 0.5 < sf["fraction"] < 0.7, "la verdad cae en una fracción no trivial: ni 0 ni 0,5"
    assert sf["frame_after"] == sf["frame_before"] + 1
    assert sf["frame_before"] in (impact.frame - 1, impact.frame), "el cruce es contiguo al cuadro del evento"
    cruce = sf["frame_before"] + sf["fraction"]
    assert abs(cruce - truth) <= SUBFRAME_TOL_FRAMES, f"{cruce} vs verdad {truth}"
    # El par de cuadros equivocado no pasaría: el test mira el instante absoluto.
    assert abs(cruce + 1 - truth) > SUBFRAME_TOL_FRAMES and abs(cruce - 1 - truth) > SUBFRAME_TOL_FRAMES
    assert abs(sf["t_sub_s"] - cruce / sw.fps) < 1e-4, "t_sub_s es el cruce en segundos"
    assert abs(cruce - impact.frame) <= 0.6, "el cuadro entero es el cuadro más cercano al cruce"
    assert sf["t_sub_s"] != impact.t_s and sf["uncertainty_s"] < impact.uncertainty_s, "más fino que ±1 cuadro"
    assert sf["provenance"] == "estimacion" and sf["views"] == ["face_on"] and sf["method"]
    assert sf["components"]["slope_px_per_frame"] > 0 and sf["components"]["noise_px"] is not None


@pytest.mark.parametrize("fps", [30.0, 60.0, 120.0, 240.0])
def test_impact_subframe_tracks_the_crossing_at_every_fps(fps):
    sw = synth_swing(fps, n_reps=2, hands_tilt=0.15, hands_miss_px=60.0)
    _, events = _impact_subframe(sw)
    sf = events["impact"].subframe
    cruce = sf["frame_before"] + sf["fraction"]
    assert abs(cruce - sw.truth[0]["impact_cross"]) <= SUBFRAME_TOL_FRAMES, f"{fps} fps: {cruce}"
    assert 0.0 < sf["uncertainty_frames"] < 1.0 and sf["uncertainty_s"] > 0


@pytest.mark.parametrize("fps", [30.0, 60.0, 120.0])
def test_impact_subframe_uncertainty_covers_the_error_with_noise(fps):
    """Con 2 px de ruido por keypoint el error crece, y la banda reportada crece con él."""
    sw = synth_swing(fps, n_reps=2, hands_tilt=0.15, hands_miss_px=60.0, noise_px=2.0)
    _, events = _impact_subframe(sw)
    sf = events["impact"].subframe
    err = abs(sf["frame_before"] + sf["fraction"] - sw.truth[0]["impact_cross"])
    assert sf["components"]["noise_frames"] > 0, "el ruido del clip entra en la banda"
    assert err <= SUBFRAME_TOL_FRAMES + 2 * sf["uncertainty_frames"], f"{fps} fps: error {err:.3f}, banda {sf['uncertainty_frames']}"


def test_impact_subframe_changes_with_the_wrong_axis_and_with_y_flipped():
    """Los tres bugs inyectados de la invariante 15 que esta señal puede tener."""
    sw = synth_swing(30.0, n_reps=2, hands_tilt=0.2, hands_miss_px=100.0)
    sig, events = _impact_subframe(sw)
    sf = events["impact"].subframe
    bueno = sf["frame_before"] + sf["fraction"]
    P = np.asarray(sig.hands_raw, dtype=float)
    address, frame = events["address"].frame, events["impact"].frame
    r = k = max(2, int(round(0.1 * sw.fps)))  # los mismos de GolfEventParams a 30 fps

    def cruce(Q, axis=None):
        if axis is None:
            axis = principal_axis(Q, frame - k, frame + k)
            if float((Q[frame + k] - Q[frame - k]) @ axis) < 0:
                axis = -axis
        c = subframe_crossing(Q @ axis, float(Q[address] @ axis), near=frame, lo=frame - r, hi=frame + r)
        return None if c.fraction is None else c.frame_before + c.fraction, axis

    _, eje = cruce(P)
    lejos = lambda t: t is None or abs(t - bueno) > SUBFRAME_TOL_FRAMES

    # 1. El eje equivocado: sólo `y`. El arco es tangente a la altura del address.
    c_y = subframe_crossing(P[:, 1], float(P[address, 1]), near=frame, lo=frame - r, hi=frame + r)
    assert lejos(None if c_y.fraction is None else c_y.frame_before + c_y.fraction)
    # 2. El eje equivocado: sólo `x`, sin la componente vertical del viaje.
    c_x = subframe_crossing(P[:, 0], float(P[address, 0]), near=frame, lo=frame - r, hi=frame + r)
    assert lejos(None if c_x.fraction is None else c_x.frame_before + c_x.fraction)
    # 3. El signo de `y` invertido en el eje y no en las posiciones: el bug clásico de
    #    mezclar "y hacia abajo" (image_px) con "y hacia arriba" en el mismo cálculo.
    assert lejos(cruce(P, axis=eje * np.array([1.0, -1.0]))[0])
    # Y al revés: espejar el clip ENTERO es una simetría, no un bug. El instante no
    #    puede moverse (test metamórfico, ADR-011).
    espejo, _ = cruce(P * np.array([1.0, -1.0]))
    assert espejo is not None and abs(espejo - bueno) < 1e-9


def test_subframe_crossing_says_why_when_there_is_no_clear_crossing():
    """Sin cruce, con más de uno, lejos del evento o sin nivel: `fraction` es None y hay razón."""
    sube = np.arange(20.0)
    c = subframe_crossing(sube, 100.0, near=10, lo=6, hi=14)
    assert c.fraction is None and "no cruza" in c.null_reason
    tiembla = np.array([-1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0])
    c = subframe_crossing(tiembla, 0.0, near=6, lo=3, hi=9)
    assert c.fraction is None and "ambiguo" in c.null_reason and "veces" in c.null_reason
    c = subframe_crossing(sube, 3.5, near=10, lo=1, hi=14)
    assert c.fraction is None and "no es contiguo" in c.null_reason
    c = subframe_crossing(sube, float("nan"), near=10, lo=6, hi=14)
    assert c.fraction is None and "sin nivel" in c.null_reason
    # Y el caso claro, con la cuenta a mano: cruza 0 entre el 10 (−1) y el 11 (+3).
    recta = np.concatenate([np.full(10, -5.0), [-1.0, 3.0], np.full(8, 7.0)])
    c = subframe_crossing(recta, 0.0, near=10, lo=8, hi=13)
    assert c.frame_before == 10 and abs(c.fraction - 0.25) < 1e-9 and c.slope == 4.0


def test_impact_subframe_is_null_from_down_the_line():
    """La dirección de viaje de las manos en el impacto apunta al objetivo: desde
    down_the_line queda sobre el eje óptico y no se puede medir (invariante 6)."""
    sw = synth_swing(30.0, n_reps=2, hands_tilt=0.2, hands_miss_px=100.0)
    _, events = _impact_subframe(sw, view="down_the_line")
    sf = events["impact"].subframe
    assert sf["fraction"] is None and sf["t_sub_s"] is None
    assert "down_the_line" in sf["null_reason"] and "face_on" in sf["null_reason"]


def test_analysis_carries_the_impact_subframe(clips, capture_paths_yaml, tmp_path):
    take, sw = _synthetic_take(clips, capture_paths_yaml, tmp_path)
    a = analyze_take(take, GOLF)
    assert validate_analysis(json.loads((take / "analysis.json").read_text())) == []
    assert a["header"]["schema_version"] == "1.2.0", "`subframe` (1.1.0) y `fps_provenance` (1.2.0)"
    for rep in a["events"]:
        assert rep["impact"]["subframe"]["fraction"] is not None
        assert rep["impact"]["frame"] == json.loads((take / "analysis.json").read_text())["events"][rep["rep"] - 1]["impact"]["frame"]
        for otro in ("address", "top"):
            assert rep[otro]["subframe"] is None, "hoy sólo el impacto lo tiene, y el campo está igual"


class SwingEstimator:
    """Estimador falso que devuelve un swing sintético, un cuadro por llamada.

    El `FakeEstimator` de `test_perception` devuelve una persona quieta y por eso no
    produce eventos. Éste hace que el modo exploración recorra el camino completo
    —video → pose → eventos → `datos-eventos.json`— sin tocar el modelo real.
    """

    def __init__(self, sw) -> None:
        self.sw, self.calls = sw, 0

    def reset(self) -> None:
        self.calls = 0

    def __call__(self, frame):
        from kinelab.perception.estimator import FrameEstimate

        i = min(self.calls, self.sw.keypoints.shape[0] - 1)
        self.calls += 1
        kp = self.sw.keypoints[i]
        x0, y0 = np.nanmin(kp, axis=0)
        x1, y1 = np.nanmax(kp, axis=0)
        return FrameEstimate(kp[None].astype(np.float32), np.full((1, kp.shape[0]), 0.9, np.float32), np.array([[x0, y0, x1, y1]], np.float32), True)

    def provenance(self) -> dict:
        return {"model": "swing sintético", "provider": "falso"}


def test_explore_writes_the_impact_subframe(clips, tmp_path):
    """De un video a `datos-eventos.json`: el instante entre cuadros llega a la pantalla."""
    from kinelab.explore import explore

    if "hevc120" not in clips:
        pytest.skip("sin fixture hevc120")
    sw = synth_swing(120.0, n_reps=1, still_s=0.5, backswing_s=0.8, downswing_s=0.25, follow_s=0.55, recover_s=0.8, amplitude_px=20.0, body_height_px=70.0, frame=(96, 96), hands_tilt=0.2, hands_miss_px=5.0)
    r = explore(clips["hevc120"], tmp_path / "out", GOLF, height_m=1.8, estimator=SwingEstimator(sw))
    escrito = json.loads((tmp_path / "out" / "datos-eventos.json").read_text(encoding="utf-8"))
    assert escrito["eventos_subcuadro"] == r["eventos_subcuadro"], "lo que se muestra es lo que se escribió"
    sf = r["eventos_subcuadro"]["impact"]
    impacto = r["eventos_frame"]["impact"]
    assert sf["frame_before"] in (impacto - 1, impacto) and sf["frame_after"] == sf["frame_before"] + 1
    assert 0.0 <= sf["fraction"] <= 1.0 and sf["null_reason"] is None
    assert abs(sf["frame_before"] + sf["fraction"] - sw.truth[0]["impact_cross"]) <= SUBFRAME_TOL_FRAMES
    assert abs(sf["t_sub_s"] - (sf["frame_before"] + sf["fraction"]) / r["fps_archivo"]) < 1e-3
