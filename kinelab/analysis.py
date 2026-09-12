"""De `pose.npz` a `analysis.json` (Fase 2): señales, segmentación, eventos del
deporte, correcciones manuales, calidad y series. Todo se recalcula desde la
pose cruda; nada de acá vuelve a mirar el video ni el modelo.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import yaml

import kinelab
from kinelab.contract.write import write_analysis
from kinelab.events.manual import apply_edits, load_edits
from kinelab.events.segmentation import segment_reps
from kinelab.events.signal import butterworth_lowpass, cutoff_for_fps, hands_center, speed
from kinelab.ingest.gate import CaptureJson
from kinelab.ingest.session import sha256_file
from kinelab.metrics.core import MetricContext, evaluate
from kinelab.metrics.generic import gain, repeatability_curves, repeatability_scalar
from kinelab.metrics.registry import REGISTRY, Registry
from kinelab.perception.framing import body_height_px
from kinelab.perception.gaps import interpolate_gaps
from kinelab.perception.posestore import POSE_FILE, PoseData, load_pose
from kinelab.sport import SportConfig

SCHEMA_VERSION = "1.0.0"
SERIES_MAX_HZ = 10.0
QUALITY_MIN_DETECTION = 0.90
QUALITY_MAX_PLAUSIBILITY_REJECT = 0.05
QUALITY_MAX_CAMERA_MOTION_PX = 2.0


class AnalysisError(RuntimeError):
    pass


@dataclass
class SwingSignals:
    fps: float
    hands_raw: np.ndarray  # (T,2) px, con huecos ≤ max_gap rellenados
    hands: np.ndarray  # (T,2) px filtradas
    speed: np.ndarray  # (T,) alturas de cuerpo / s
    body_height: np.ndarray  # (T,) px
    valid: np.ndarray  # (T,) bool
    params: dict
    noise_floor_bh_s: float = 0.0  # p10 de la velocidad quieta de las manos: el piso de ruido del propio clip


def swing_signals(pose: PoseData, fps: float, *, cutoff_hz_max: float = 12.0, max_gap: int = 5) -> SwingSignals:
    kp = interpolate_gaps(pose.keypoints, max_gap)
    hands_raw = hands_center(kp)
    bh = body_height_px(kp, fps)
    if np.isfinite(bh).any():
        scale = np.where(np.isfinite(bh) & (bh > 0), bh, np.nanmedian(bh))
        unit = "body_heights"
    else:
        scale = np.ones(kp.shape[0])
        unit = "px (sin altura de cuerpo)"
    cutoff = cutoff_for_fps(fps, cutoff_hz_max)
    hands = butterworth_lowpass(hands_raw, fps, cutoff_hz=cutoff)
    spd = speed(hands, fps, scale)
    # Piso de ruido del clip: p10 de la velocidad con mediana móvil corta (los cuadros más
    # quietos). p25 no sirve: en un clip corto lleno de movimiento sube hasta aceptar
    # movimiento lento como quietud (medido en el primer clip real).
    from kinelab.events.primitives import stillness_signal

    still = stillness_signal(spd, fps, 0.1)
    floor = float(np.nanpercentile(still, 10)) if np.isfinite(still).any() else 0.0
    return SwingSignals(fps=fps, hands_raw=hands_raw, hands=hands, speed=spd, body_height=bh, valid=np.isfinite(hands).all(axis=1), params={"filter": "butterworth", "order": 4, "cutoff_hz": cutoff, "cutoff_hz_max": cutoff_hz_max, "gap_fill_max_frames": max_gap, "speed_unit": unit, "signal": "hands_center", "noise_floor_bh_s": round(floor, 4)}, noise_floor_bh_s=floor)


def _quality(pose: PoseData, rep_count: int) -> dict:
    prov = pose.provenance
    framing = prov.get("framing") or {}
    T = int(pose.keypoints.shape[0])
    rejected = int(np.count_nonzero(pose.plausibility))
    counts = prov.get("plausibility_counts") or {}
    rate = float(framing.get("detection_rate", 0.0) or 0.0)
    motion = prov.get("camera_motion_px")
    reasons: list[str] = []
    if rate < QUALITY_MIN_DETECTION:
        reasons.append(f"Se perdió al jugador en el {round(100 * (1 - rate))} % de los cuadros.")
    if rep_count == 0:
        reasons.append("No se encontró ninguna repetición del gesto.")
    verdict = "no_usar" if reasons else "confiable"
    if verdict == "confiable":
        if T and rejected / T > QUALITY_MAX_PLAUSIBILITY_REJECT:
            reasons.append(f"El {round(100 * rejected / T)} % de los cuadros tiene una pose implausible.")
        if motion is not None and motion > QUALITY_MAX_CAMERA_MOTION_PX:
            reasons.append(f"La cámara se movió ({motion:.1f} px entre muestras).")
        if reasons:
            verdict = "con_reservas"
    return {
        "detection_rate": rate,
        "body_height_px": {"median": framing.get("body_height_px_median"), "min": framing.get("body_height_px_min"), "max": framing.get("body_height_px_max"), "frac_of_frame": framing.get("frac_of_frame")},
        "blur_estimate": None,
        "plausibility": {"rejected_frames": rejected, "by_reason": {k: int(v) for k, v in counts.items()}},
        "camera_motion_px": motion,
        "verdict": verdict,
        "reasons": reasons,
    }


def athlete_height_m(take_dir: Path, athlete: str) -> float | None:
    """`altura_m` de data/athletes/<slug>.yaml (CONTRATO.md §Layout), si existe."""
    for parent in take_dir.resolve().parents:
        f = parent / "athletes" / f"{athlete}.yaml"
        if f.is_file():
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            h = data.get("altura_m")
            return float(h) if h else None
    return None


def build_analysis(take_dir: Path, capture: CaptureJson, pose: PoseData, sport: SportConfig, *, registry: Registry | None = None, height_m: float | None = None) -> dict:
    ev = sport.events
    if ev is None:
        raise AnalysisError(f"{sport.id}: el deporte no define eventos todavía.")
    fps = float(capture.fps_real)
    sig = swing_signals(pose, fps, cutoff_hz_max=ev.cutoff_hz_max)
    cands, rejected = segment_reps(sig.speed, fps, ev.segmentation)
    events_out: list[dict] = []
    reps: list[dict] = []
    prev_end = -1
    for c in cands:
        events, reason = ev.detect(sig, c)
        if reason:
            rejected[reason] = rejected.get(reason, 0) + 1
            continue
        start = events["address"].frame
        end = events["follow_end"].frame if events.get("follow_end") else c.end
        if start <= prev_end:
            rejected["solapada"] = rejected.get("solapada", 0) + 1
            continue
        n = len(reps) + 1
        events_out.append({"rep": n, **{k: (events[k].to_dict() if events.get(k) else None) for k in ev.order}, "sequence_order": "sin_datos"})
        reps.append({"rep": n, "frame_start": int(start), "frame_end": int(end), "t_start": round(start / fps, 4), "t_end": round(end / fps, 4), "peak_speed_bh_s": round(c.peak_speed, 3), "metrics": {}})
        prev_end = end
    edits = load_edits(take_dir)
    if edits:
        events_out = apply_edits(events_out, edits, fps=fps, order=ev.order)
        for r, e in zip(reps, events_out):
            r["frame_start"] = e["address"]["frame"] if e.get("address") else r["frame_start"]
            r["frame_end"] = e["follow_end"]["frame"] if e.get("follow_end") else r["frame_end"]
            r["t_start"], r["t_end"] = round(r["frame_start"] / fps, 4), round(r["frame_end"] / fps, 4)
    # --- métricas por repetición y resumen (Fase 3) ---
    sm = sport.metrics
    registry = registry or (sm.registry if sm else REGISTRY)
    summary_metrics: dict = {}
    gain_out: dict = {}
    warnings: list[str] = []
    if sm is not None and reps:
        kp = interpolate_gaps(pose.keypoints, 5)
        if height_m is None:
            warnings.append("Sin altura declarada del atleta: las métricas en cm quedan en null. Creá data/athletes/<slug>.yaml con altura_m o pasá --altura-m.")
        per_metric: dict[str, list] = {m.id: [] for m in registry}
        curves: list[np.ndarray] = []
        gains: list[dict] = []
        for r, e in zip(reps, events_out):
            ev_frames = {k: e[k]["frame"] for k in ev.order if e.get(k)}
            ctx = MetricContext(keypoints=kp, scores=pose.scores, fps=fps, view=capture.view, body_height_px=sig.body_height, events=ev_frames, frame_start=r["frame_start"], frame_end=r["frame_end"], athlete_height_m=height_m, hands_speed=sig.speed)
            for m in registry:
                out = evaluate(m, ctx, joints=sm.joints.get(m.id, ()))
                r["metrics"][m.id] = out
                per_metric[m.id].append(out["value"])
            if "top" in ev_frames and "impact" in ev_frames:
                curves.append(sig.speed[ev_frames["top"] : ev_frames["impact"] + 1])
            g = gain(kp, fps, sm.gain_segments, r["frame_start"], r["frame_end"])
            gains.append(g)
            e["sequence_order"] = g["sequence_order"]
        for m in registry:
            vals = [v for v in per_metric[m.id] if v is not None]
            summary_metrics[m.id] = {"median": round(float(np.median(vals)), 3) if vals else None, "n": len(vals), "mdc": m.mdc, "unit": m.unit, "level": m.level, "repeatability": repeatability_scalar(per_metric[m.id])}
        summary_metrics["hands_speed_curve_top_to_impact"] = {"median": None, "n": len(curves), "mdc": None, "unit": "bh/s", "level": 1, "repeatability": repeatability_curves(curves)}
        for key in ("pelvis_to_torso", "torso_to_arm"):
            vals = [g["ratios"].get(key) for g in gains]
            vals = [v for v in vals if v is not None]
            gain_out[key] = {"value": round(float(np.median(vals)), 3) if vals else None, "unit": "ratio", "n": len(vals), "confidence": None}
        gain_out["sequence_order"] = {"by_rep": [g["sequence_order"] for g in gains], "note": "indeterminado cuando dos picos caen a < 2 cuadros (ADR-008)"}
    step = max(1, int(math.ceil(fps / SERIES_MAX_HZ)))
    if edits:
        warnings.append(f"{len(edits)} corrección(es) manual(es) aplicadas desde events-manual.json.")
    return {
        "header": {
            "schema_version": SCHEMA_VERSION,
            "engine_version": kinelab.__version__,
            "registry_version": registry.version,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "source": {"pose_sha256": sha256_file(take_dir / POSE_FILE), "master_sha256": None, "capture_path_id": capture.capture_path_id, "fps_real": fps},
            "sport": sport.id,
            "gesture": capture.gesture,
            "view": capture.view,
        },
        "quality": _quality(pose, len(reps)),
        "events": events_out,
        "reps": reps,
        "summary": {"rep_count": len(reps), "reps_rejected": {"count": int(sum(rejected.values())), "reasons": rejected}, "metrics": summary_metrics, "gain": gain_out},
        "series": {"t": np.round(pose.timestamps_s[::step], 4), "hands_speed_bh_s": np.round(sig.speed[::step], 4), "params": {**sig.params, "segmentation": asdict(ev.segmentation), "events": asdict(ev.params), "series_hz": fps / step}},
        "warnings": warnings,
        "deviations": [],
    }


def analyze_take(take_dir: str | Path, sport: SportConfig, *, write: bool = True, height_m: float | None = None) -> dict:
    take_dir = Path(take_dir)
    cj = take_dir / "capture.json"
    if not cj.is_file():
        raise AnalysisError(f"{take_dir}: no hay capture.json.")
    capture = CaptureJson.model_validate_json(cj.read_text(encoding="utf-8"))
    if capture.gate.verdict != "ok":
        raise AnalysisError(f"{take_dir}: el gate rechazó esta toma: {' · '.join(capture.gate.reasons)}")
    if capture.fps_real is None:
        raise AnalysisError(f"{take_dir}: sin fps_real.")
    pose = load_pose(take_dir)
    if height_m is None:
        height_m = athlete_height_m(take_dir, capture.athlete)
    analysis = build_analysis(take_dir, capture, pose, sport, height_m=height_m)
    if write:
        write_analysis(take_dir, analysis)
    return analysis
