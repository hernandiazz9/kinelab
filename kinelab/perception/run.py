"""Correr la percepción sobre una toma ingestada: `original.<ext>` + `capture.json`
→ `pose.npz`, más los chequeos de la Fase 1 sumados al gate del `capture.json`.

Hasta la Fase 4 no hay `master.mp4`: la pose se calcula sobre el original ya
rotado como se ve, y `master_sha256` queda en null en la procedencia. Los
índices de cuadro se refieren al stream decodificado del original.

Para decidir si arranca mira **sólo los chequeos de ingesta** —los nueve de
`CONTRATO.md` §capture.json—, no el veredicto entero: los de la Fase 1 los
escribe esta misma función en ese mismo `capture.json` y se rehacen en cada
corrida. Ver `_blocking_checks`.
"""

from __future__ import annotations

import datetime as dt
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from kinelab.ingest.gate import CaptureJson, Check, Gate, with_checks
from kinelab.perception.estimator import EstimatorConfig, PoseEstimator, with_det_frequency
from kinelab.perception.framing import CHECK_IDS as PHASE1_CHECK_IDS, FramingReport, framing_checks, framing_report
from kinelab.perception.plausibility import plausibility_mask
from kinelab.perception.posestore import POSE_FILE, PoseData, save_pose
from kinelab.perception.tracking import SubjectTracker
from kinelab.perception.video import camera_motion_px, iter_frames, sample_gray
from kinelab.sport import SportConfig

CAMERA_SAMPLE_EVERY_S = 0.5


class PerceptionError(RuntimeError):
    """La toma no está lista para percepción, o algo falló antes de escribir."""


@dataclass
class PerceptionResult:
    take_dir: Path
    pose_path: Path
    frames: int
    report: FramingReport
    checks: list[Check]
    gate: Gate


def _blocking_checks(gate: Gate) -> list[Check]:
    """Los chequeos fallados que impiden correr la percepción: los de **ingesta**.

    Decisión del orquestador (encargo 30). Los tres de la Fase 1
    (`PHASE1_CHECK_IDS`: encuadre, tasa de detección, una sola persona) los
    escribe `run_perception` en el mismo `capture.json`, así que mirarlos acá es
    negarse a arrancar por el resultado de la corrida anterior: desde que el
    encuadre tiene umbral (encargo 17), una toma rechazada por encuadre no se
    podía volver a correr ni con `--overwrite`. Se rehacen en cada corrida, así
    que no deciden si hay corrida.

    Lo que sí bloquea sigue bloqueando: codec, tasa variable, camino de captura,
    fps mínimo del gesto, duración, rotación, vista y gesto. Un chequeo en
    `passed: None` no es un fallo (CONTRATO.md §capture.json) y tampoco bloquea.
    """
    return [c for c in gate.checks if c.passed is False and c.id not in PHASE1_CHECK_IDS]


def find_original(take_dir: Path) -> Path:
    found = sorted(p for p in take_dir.glob("original.*") if p.is_file())
    if not found:
        raise PerceptionError(f"{take_dir}: no hay original.<ext>; ingestá el clip primero.")
    return found[0]


def _code_sha() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5, cwd=Path(__file__).resolve().parents[2])
        return out.stdout.strip() or None if out.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def run_perception(
    take_dir: str | Path,
    sport: SportConfig,
    config: EstimatorConfig | None = None,
    *,
    estimator: PoseEstimator | None = None,
    overwrite: bool = False,
    det_frequency: int | None = None,
    progress_cb=None,
) -> PerceptionResult:
    take_dir = Path(take_dir)
    cj_path = take_dir / "capture.json"
    if not cj_path.is_file():
        raise PerceptionError(f"{take_dir}: no hay capture.json; ingestá el clip primero (python -m kinelab.ingest).")
    capture = CaptureJson.model_validate_json(cj_path.read_text(encoding="utf-8"))
    blocking = _blocking_checks(capture.gate)
    if blocking:
        razones = [c.reason or c.id for c in blocking]
        raise PerceptionError(f"{take_dir}: la ingesta rechazó esta toma; no se corre pose sobre un clip rechazado. Razones: {' · '.join(razones)}")
    if capture.fps_real is None:
        raise PerceptionError(f"{take_dir}: capture.json no tiene fps_real (camino sin calibrar).")
    pose_path = take_dir / POSE_FILE
    if pose_path.exists() and not overwrite:
        raise PerceptionError(f"{pose_path} ya existe. La pose cruda no se pisa; usá --overwrite para re-correr el modelo a propósito.")
    original = find_original(take_dir)

    cfg = config or EstimatorConfig()
    if det_frequency:
        cfg = with_det_frequency(cfg, det_frequency)
    est = estimator or PoseEstimator(cfg)
    est.reset()
    tracker = SubjectTracker(min_joint_score=cfg.min_joint_score, min_core_score=cfg.min_core_score)
    sample_every = max(1, int(round(float(capture.fps_real) * CAMERA_SAMPLE_EVERY_S)))
    gray: list[np.ndarray] = []
    frame_w = frame_h = 0
    for i, frame in iter_frames(original, rotation_deg=capture.rotation_deg, display_size=(capture.width, capture.height), progress_cb=progress_cb):
        if i == 0:
            frame_h, frame_w = frame.shape[:2]
        fe = est(frame)
        tracker.push(fe.keypoints, fe.scores, fe.bboxes)
        if i % sample_every == 0:
            gray.append(sample_gray(frame))
    track = tracker.result()
    T = int(track.keypoints.shape[0])
    if T == 0:
        raise PerceptionError(f"{original}: no se decodificó ningún cuadro.")

    mask, counts = plausibility_mask(track.keypoints, track.scores, min_score=cfg.min_joint_score)
    motion = camera_motion_px(gray)
    report = framing_report(track, float(capture.fps_real), frame_h, motion)
    checks = framing_checks(report, sport.perception)
    timestamps = np.arange(T, dtype=np.float64) / float(capture.fps_real)
    provenance = {
        **est.provenance(),
        "run_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "code_sha": _code_sha(),
        "master_sha256": None,  # Fase 4
        "source_sha256": capture.sha256_original,
        "source_name": capture.original_name,
        "frames": T,
        "fps_real": float(capture.fps_real),
        "frame_size": [int(frame_w), int(frame_h)],
        "rotation_deg": capture.rotation_deg,
        "plausibility_counts": counts,
        "camera_motion_px": motion,
        "framing": asdict(report),
    }
    save_pose(take_dir, PoseData(track.keypoints, track.scores, track.bbox, timestamps, mask, provenance), overwrite=overwrite)

    gate = with_checks(capture.gate, checks, after="rotation_normalized")
    updated = capture.model_copy(update={"gate": gate})
    tmp = cj_path.with_name("capture.json.tmp")
    tmp.write_text(updated.model_dump_json(indent=2), encoding="utf-8")
    tmp.replace(cj_path)
    return PerceptionResult(take_dir=take_dir, pose_path=pose_path, frames=T, report=report, checks=checks, gate=gate)
