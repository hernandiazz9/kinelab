"""Modo exploración: un video → toda la data del cuerpo, dibujada y en tablas.

Sin gate y sin juicio: sirve para MIRAR lo que el modelo ve y todo lo que se
puede derivar de eso, a cualquier fps. Cada archivo lleva la advertencia. El
producto sigue siendo el visor sobre datos (ADR-014); esto es la lupa.

    python -m kinelab datos VIDEO.mp4 --altura-m 1.75 [--vista face_on] [--out DIR] [--cpu]

Deja en DIR (por defecto <video>.kinelab/):
    overlay.mp4          el video con los palitos, ángulos y eventos dibujados
    evento-<id>.png      una foto por evento con el esqueleto y los números
    datos-por-cuadro.csv una fila por cuadro: 26 puntos (px, score), ángulos, alturas, desplazamientos, velocidades
    datos-eventos.json   todo eso en cada evento, más diferencias respecto del address y duraciones
    analysis.json, pose.npz, capture.json   lo mismo que produce el motor
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np

from kinelab.analysis import build_analysis, swing_signals
from kinelab.events.signal import butterworth_lowpass, cutoff_for_fps, fill_nan_linear
from kinelab.ingest.gate import CaptureJson, Check, Gate
from kinelab.ingest.session import sha256_file
from kinelab.metrics.generic import line_angle_rate
from kinelab.perception.estimator import EstimatorConfig
from kinelab.perception.gaps import interpolate_gaps
from kinelab.perception.keypoints import HALPE26_LIMBS, HALPE26_NAMES, H, LEFT_RIGHT_PAIRS
from kinelab.perception.plausibility import angle_deg
from kinelab.perception.posestore import finite_or_none, load_pose
from kinelab.perception.run import run_perception
from kinelab.perception.video import ffmpeg_bin, iter_frames
from kinelab.sport import SportConfig
from kinelab.tools.fps_truth import analyze as fps_analyze

AVISO = "EXPLORACIÓN: sin gate, sin MDC, tasa de cuadros del archivo sin calibrar. Números descriptivos para mirar, no para juzgar."
EVENT_ORDER = ("address", "top", "impact", "follow_end")
LEFT = {H.LEFT_EYE, H.LEFT_EAR, H.LEFT_SHOULDER, H.LEFT_ELBOW, H.LEFT_WRIST, H.LEFT_HIP, H.LEFT_KNEE, H.LEFT_ANKLE, H.LEFT_BIG_TOE, H.LEFT_SMALL_TOE, H.LEFT_HEEL}
RIGHT = {r for _, r in LEFT_RIGHT_PAIRS}


def prepare_take(video: Path, out_dir: Path, *, view: str, athlete: str = "exploracion") -> Path:
    """Arma una toma sin pasar por el gate: capture.json con la tasa del archivo y aviso."""
    out_dir.mkdir(parents=True, exist_ok=True)
    original = out_dir / f"original{video.suffix.lower()}"
    if not original.exists() or sha256_file(original) != sha256_file(video):
        shutil.copy2(video, original)
    t = fps_analyze(original)
    c, d = t.counted, t.declared
    cj = CaptureJson(
        athlete=athlete, gesture="driver", view=view, capture_path_id="exploracion",
        fps_real=round(c.fps_playback, 3), fps_playback=round(c.fps_playback, 3), stretch_factor=1.0,
        fps_source=AVISO, codec=d.codec, width=d.display_size[0], height=d.display_size[1], rotation_deg=d.rotation_deg,
        frames_decoded=c.frames_decoded, duration_s=round(c.frames_decoded / c.fps_playback, 3), duration_playback_s=round(c.playback_span_s, 3),
        vfr_ratio=round(c.vfr_ratio, 3), recorded_at=d.creation_time, sha256_original=sha256_file(original), original_name=video.name,
        gate=Gate(verdict="ok", checks=[Check(id="exploracion", passed=None, reason=AVISO)], reasons=[]),
    )
    (out_dir / "capture.json").write_text(cj.model_dump_json(indent=2), encoding="utf-8")
    return out_dir


def _ang(k, a, b, c):
    return angle_deg(k[:, a], k[:, b], k[:, c])


def _line_deg(k, i, j):
    """Ángulo de la línea i→j respecto de la horizontal de la imagen, en grados (y hacia abajo: positivo = j más abajo que i)."""
    d = k[:, j] - k[:, i]
    return np.degrees(np.arctan2(d[:, 1], d[:, 0]))


def _vs_vertical_deg(k, i, j):
    """Ángulo del vector i→j respecto de la vertical hacia abajo, con signo (positivo = hacia la derecha de la imagen)."""
    d = k[:, j] - k[:, i]
    return np.degrees(np.arctan2(d[:, 0], d[:, 1]))


def per_frame_table(pose, fps: float, height_m: float | None, address: int | None) -> tuple[list[str], list[dict]]:
    k = interpolate_gaps(pose.keypoints, 5).astype(float)
    sig = swing_signals(pose, fps)
    bh = sig.body_height
    T = k.shape[0]
    mid_hip = (k[:, H.LEFT_HIP] + k[:, H.RIGHT_HIP]) / 2
    mid_sh = (k[:, H.LEFT_SHOULDER] + k[:, H.RIGHT_SHOULDER]) / 2
    ankle_y = np.nanmean(np.stack([k[:, H.LEFT_ANKLE, 1], k[:, H.RIGHT_ANKLE, 1]]), axis=0)
    hands = sig.hands_raw
    cm = (height_m * 100.0 / bh) if height_m else None  # cm por píxel, por cuadro
    ref = address if address is not None else 0
    cols: dict[str, np.ndarray] = {
        "frame": np.arange(T), "t_s": pose.timestamps_s, "plausibility_flags": pose.plausibility.astype(int), "body_height_px": bh,
        "elbow_left_deg": _ang(k, H.LEFT_SHOULDER, H.LEFT_ELBOW, H.LEFT_WRIST), "elbow_right_deg": _ang(k, H.RIGHT_SHOULDER, H.RIGHT_ELBOW, H.RIGHT_WRIST),
        "knee_left_deg": _ang(k, H.LEFT_HIP, H.LEFT_KNEE, H.LEFT_ANKLE), "knee_right_deg": _ang(k, H.RIGHT_HIP, H.RIGHT_KNEE, H.RIGHT_ANKLE),
        "hip_left_deg": _ang(k, H.LEFT_SHOULDER, H.LEFT_HIP, H.LEFT_KNEE), "hip_right_deg": _ang(k, H.RIGHT_SHOULDER, H.RIGHT_HIP, H.RIGHT_KNEE),
        "shoulder_left_deg": _ang(k, H.LEFT_ELBOW, H.LEFT_SHOULDER, H.LEFT_HIP), "shoulder_right_deg": _ang(k, H.RIGHT_ELBOW, H.RIGHT_SHOULDER, H.RIGHT_HIP),
        "trunk_lean_deg": -_vs_vertical_deg(np.stack([mid_hip, mid_sh], axis=1), 0, 1) + 180.0 * 0,  # tronco: cadera→hombro respecto de la vertical
        "shoulder_line_deg": _line_deg(k, H.RIGHT_SHOULDER, H.LEFT_SHOULDER), "hip_line_deg": _line_deg(k, H.RIGHT_HIP, H.LEFT_HIP),
        "arm_left_vs_vertical_deg": _vs_vertical_deg(k, H.LEFT_SHOULDER, H.LEFT_WRIST), "arm_right_vs_vertical_deg": _vs_vertical_deg(k, H.RIGHT_SHOULDER, H.RIGHT_WRIST),
        "hands_x_vs_hip_bh": (hands[:, 0] - mid_hip[:, 0]) / bh, "hands_height_pct": (ankle_y - hands[:, 1]) / bh * 100.0,
        "hands_speed_bh_s": sig.speed,
        "shoulder_line_rate_deg_s": line_angle_rate(k, H.RIGHT_SHOULDER, H.LEFT_SHOULDER, fps), "hip_line_rate_deg_s": line_angle_rate(k, H.RIGHT_HIP, H.LEFT_HIP, fps),
        "arm_left_rate_deg_s": line_angle_rate(k, H.LEFT_SHOULDER, H.LEFT_WRIST, fps),
    }
    # el tronco: ángulo cadera→hombro respecto de la vertical hacia ARRIBA, positivo = hombros hacia la derecha de la imagen
    d = mid_sh - mid_hip
    cols["trunk_lean_deg"] = np.degrees(np.arctan2(d[:, 0], -d[:, 1]))
    for name, pt in (("pelvis", mid_hip), ("thorax", mid_sh), ("head", k[:, H.HEAD]), ("hands", hands)):
        dx, dy = pt[:, 0] - pt[ref, 0], -(pt[:, 1] - pt[ref, 1])  # dy positivo = sube
        cols[f"{name}_dx_vs_address_pct"], cols[f"{name}_dy_vs_address_pct"] = dx / bh * 100.0, dy / bh * 100.0
        if cm is not None:
            cols[f"{name}_dx_vs_address_cm"], cols[f"{name}_dy_vs_address_cm"] = dx * cm, dy * cm
    if cm is not None:
        cols["hands_speed_cm_s"] = sig.speed * bh * cm
    for j, name in enumerate(HALPE26_NAMES):
        cols[f"{name}_x"], cols[f"{name}_y"], cols[f"{name}_score"] = pose.keypoints[:, j, 0], pose.keypoints[:, j, 1], pose.scores[:, j]
    names = list(cols)
    rows = [{n: (None if (isinstance(v := cols[n][i], float) and not np.isfinite(v)) else (float(v) if isinstance(v, (float, np.floating)) else int(v))) for n in names} for i in range(T)]
    return names, rows


def _draw(frame: np.ndarray, kp: np.ndarray, sc: np.ndarray, row: dict, label: str | None, t_s: float) -> np.ndarray:
    img = frame.copy()
    h = img.shape[0]
    th = max(2, h // 400)
    for a, b in HALPE26_LIMBS:
        if np.isfinite(kp[a]).all() and np.isfinite(kp[b]).all() and sc[a] > 0.3 and sc[b] > 0.3:
            color = (80, 220, 80) if (a in LEFT or b in LEFT) else (60, 140, 255) if (a in RIGHT or b in RIGHT) else (255, 255, 255)
            cv2.line(img, tuple(np.round(kp[a]).astype(int)), tuple(np.round(kp[b]).astype(int)), color, th, cv2.LINE_AA)
    for j in range(kp.shape[0]):
        if np.isfinite(kp[j]).all() and sc[j] > 0.3:
            cv2.circle(img, tuple(np.round(kp[j]).astype(int)), th + 2, (0, 0, 255) if sc[j] < 0.5 else (255, 255, 255), -1, cv2.LINE_AA)
    fs = h / 1400.0
    def put(text, x, y, color=(255, 255, 255)):
        cv2.putText(img, text, (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, fs, (0, 0, 0), th + 2, cv2.LINE_AA)
        cv2.putText(img, text, (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, fs, color, th, cv2.LINE_AA)
    for key, j in (("elbow_left_deg", H.LEFT_ELBOW), ("elbow_right_deg", H.RIGHT_ELBOW), ("knee_left_deg", H.LEFT_KNEE), ("knee_right_deg", H.RIGHT_KNEE)):
        v = row.get(key)
        if v is not None and np.isfinite(kp[j]).all():
            put(f"{v:.0f}", kp[j, 0] + 8 * th, kp[j, 1] - 4 * th, (0, 255, 255))
    y0 = int(30 * fs * 1.5)
    lines = [f"{row['frame']}  t={t_s:.3f}s" + (f"   {label.upper()}" if label else ""), f"manos {row['hands_speed_bh_s'] or 0:.2f} bh/s  altura manos {row['hands_height_pct'] or 0:.0f}%", f"tronco {row['trunk_lean_deg'] or 0:+.0f}  hombros {row['shoulder_line_deg'] or 0:+.0f}  caderas {row['hip_line_deg'] or 0:+.0f}"]
    for i, text in enumerate(lines):
        put(text, 10 * th, y0 * (i + 1), (0, 255, 255) if (label and i == 0) else (255, 255, 255))
    return img


def render(take_dir: Path, pose, rows: list[dict], events: dict[str, int], fps: float, capture: CaptureJson) -> tuple[Path, list[Path]]:
    original = next(take_dir.glob("original.*"))
    frame_events = {f: name for name, f in events.items()}
    out = take_dir / "overlay.mp4"
    proc = None
    snaps: list[Path] = []
    try:
        for i, frame in iter_frames(original, rotation_deg=capture.rotation_deg, display_size=(capture.width, capture.height)):
            if i >= len(rows):
                break
            label = frame_events.get(i)
            img = _draw(frame, pose.keypoints[i], pose.scores[i], rows[i], label, float(pose.timestamps_s[i]))
            if proc is None:
                hh, ww = img.shape[:2]
                proc = subprocess.Popen([ffmpeg_bin(), "-y", "-v", "error", "-nostdin", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{ww}x{hh}", "-r", f"{fps:.4f}", "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
            proc.stdin.write(img.tobytes())
            if label:
                p = take_dir / f"evento-{label}.png"
                cv2.imwrite(str(p), img)
                snaps.append(p)
    finally:
        if proc is not None:
            proc.stdin.close()
            proc.wait(timeout=600)
    return out, snaps


def explore(video: Path, out_dir: Path, sport: SportConfig, *, height_m: float | None, view: str = "face_on", cpu: bool = False, progress=None, estimator=None) -> dict:
    take = prepare_take(video, out_dir, view=view)
    cfg = EstimatorConfig(providers=("CPUExecutionProvider",)) if cpu else EstimatorConfig()
    run_perception(take, sport, cfg, overwrite=True, progress_cb=progress, estimator=estimator)
    capture = CaptureJson.model_validate_json((take / "capture.json").read_text(encoding="utf-8"))
    gate_notes = [c.reason for c in capture.gate.checks if c.passed is False and c.reason]
    pose = load_pose(take)
    analysis = build_analysis(take, capture, pose, sport, height_m=height_m)
    analysis["warnings"] = [AVISO, *gate_notes, *analysis["warnings"]]
    from kinelab.contract.write import write_analysis

    write_analysis(take, analysis)
    fps = float(capture.fps_real)
    events: dict[str, int] = {}
    rep = analysis["events"][0] if analysis["events"] else None
    if rep:
        events = {k: rep[k]["frame"] for k in EVENT_ORDER if rep.get(k)}
    names, rows = per_frame_table(pose, fps, height_m, events.get("address"))
    with (take / "datos-por-cuadro.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=names)
        w.writeheader()
        w.writerows(rows)
    at = {name: rows[f] for name, f in events.items()}
    deltas = {}
    if "address" in at:
        for name, r in at.items():
            if name == "address":
                continue
            deltas[f"{name}_vs_address"] = {k: round(r[k] - at["address"][k], 2) for k in names if k.endswith("_deg") and r.get(k) is not None and at["address"].get(k) is not None}
    durations = {}
    for a, b in zip(EVENT_ORDER, EVENT_ORDER[1:]):
        if a in events and b in events:
            durations[f"{a}_to_{b}_ms"] = round((events[b] - events[a]) / fps * 1000.0, 1)
    if "address" in events and "top" in events and "impact" in events and events["impact"] > events["top"]:
        durations["tempo_ratio"] = round((events["top"] - events["address"]) / (events["impact"] - events["top"]), 2)
    peaks = {k: (None if not np.isfinite(v := np.nanmax([r[k] for r in rows if r[k] is not None] or [np.nan])) else round(float(v), 2)) for k in ("hands_speed_bh_s", "hands_speed_cm_s", "shoulder_line_rate_deg_s", "hip_line_rate_deg_s", "arm_left_rate_deg_s") if k in names}
    summary = {"aviso": AVISO, "video": video.name, "fps_archivo": fps, "cuadros": len(rows), "altura_m": height_m, "gate_diria": gate_notes, "eventos_frame": events, "eventos_t_s": {k: round(f / fps, 3) for k, f in events.items()}, "duraciones": durations, "picos": peaks, "en_cada_evento": finite_or_none(at), "diferencias_vs_address": deltas, "calidad": analysis["quality"], "columnas": names}
    (take / "datos-eventos.json").write_text(json.dumps(finite_or_none(summary), ensure_ascii=False, indent=2), encoding="utf-8")
    overlay, snaps = render(take, pose, rows, events, fps, capture)
    summary["archivos"] = [str(take / "datos-por-cuadro.csv"), str(take / "datos-eventos.json"), str(overlay), *map(str, snaps)]
    return summary
