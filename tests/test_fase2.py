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
from kinelab.events.segmentation import SegmentationParams, segment_reps
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
    assert judgment_allowed(m, view="face_on", fps_real=120) is True
    assert judgment_allowed(m, view="down_the_line", fps_real=120) is False
    assert judgment_allowed(m, view="face_on", fps_real=30) is False
    wide = Metric(id="wide", unit="cm", level=1, views=("face_on",), fps_min=60, anchored_to=(), reference_frame="image_px", mdc=5.0, reference=Reference("range", "pares", "x", "y", range=(0.0, 4.0)))
    assert judgment_allowed(wide, view="face_on", fps_real=120) is False, "MDC mayor que el rango: no es juicio"
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
    assert bs["uncertainty"]["low"] < bs["value"] < bs["uncertainty"]["high"]
    assert m["pelvis_thrust_top_cm"]["value"] is None and "down_the_line" in m["pelvis_thrust_top_cm"]["null_reason"]
    assert abs(m["pelvis_sway_top_cm"]["value"]) < 1.0, "la pelvis sintética no se mueve"
    assert a["summary"]["metrics"]["backswing_duration_ms"]["repeatability"]["kind"] == "sd_abs"
    assert a["summary"]["metrics"]["hands_speed_curve_top_to_impact"]["repeatability"]["n"] == 2
    assert "pelvis_to_torso" in a["summary"]["gain"]
    b = analyze_take(take, GOLF, write=False)
    assert b["reps"][0]["metrics"]["pelvis_sway_top_cm"]["value"] is None and "altura" in b["reps"][0]["metrics"]["pelvis_sway_top_cm"]["null_reason"]
