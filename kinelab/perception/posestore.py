"""`pose.npz`: la pose cruda con su procedencia, y la frontera NaN → null.

Portado en espíritu de padel-coach analyzer/padel_analyzer/posestore.py:23-70
(ADR-013), con las claves y dtypes de CONTRATO.md §pose.npz.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from kinelab.perception.keypoints import HALPE26_LIMBS, HALPE26_NAMES

POSE_FILE = "pose.npz"


@dataclass
class PoseData:
    keypoints: np.ndarray  # (T,J,2) float32
    scores: np.ndarray  # (T,J) float32
    bbox: np.ndarray  # (T,4) float32
    timestamps_s: np.ndarray  # (T,) float64
    plausibility: np.ndarray  # (T,) uint8
    provenance: dict


def _validate(d: PoseData) -> None:
    T = d.keypoints.shape[0]
    if d.keypoints.ndim != 3 or d.keypoints.shape[2] != 2:
        raise ValueError(f"keypoints tiene que ser (T,J,2); llegó {d.keypoints.shape}")
    for name, arr, shape in (("scores", d.scores, (T, d.keypoints.shape[1])), ("bbox", d.bbox, (T, 4)), ("timestamps_s", d.timestamps_s, (T,)), ("plausibility", d.plausibility, (T,))):
        if tuple(arr.shape) != shape:
            raise ValueError(f"{name} tiene forma {arr.shape}; se esperaba {shape}")
    if not isinstance(d.provenance, dict):
        raise ValueError("provenance tiene que ser un dict")


def save_pose(take_dir: str | Path, data: PoseData, *, overwrite: bool = False) -> Path:
    """Escribe `pose.npz` con dtypes del contrato, sin pickle y de forma atómica.
    Se niega a pisar uno existente salvo `overwrite=True` (invariante 1)."""
    path = Path(take_dir) / POSE_FILE
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} ya existe: la pose cruda no se pisa (usá overwrite=True para re-correr el modelo a propósito).")
    _validate(data)
    tmp = path.with_name(POSE_FILE + ".tmp")
    with tmp.open("wb") as f:
        np.savez_compressed(
            f,
            keypoints=np.asarray(data.keypoints, dtype=np.float32),
            scores=np.asarray(data.scores, dtype=np.float32),
            bbox=np.asarray(data.bbox, dtype=np.float32),
            timestamps_s=np.asarray(data.timestamps_s, dtype=np.float64),
            plausibility=np.asarray(data.plausibility, dtype=np.uint8),
            provenance=np.array([json.dumps(finite_or_none(data.provenance), ensure_ascii=False)]),
        )
    tmp.replace(path)
    return path


def load_pose(take_dir: str | Path) -> PoseData:
    path = Path(take_dir) / POSE_FILE
    if not path.is_file():
        raise FileNotFoundError(f"No hay {POSE_FILE} en {take_dir}: corré la percepción primero.")
    with np.load(path, allow_pickle=False) as z:
        return PoseData(
            keypoints=np.asarray(z["keypoints"], dtype=np.float32),
            scores=np.asarray(z["scores"], dtype=np.float32),
            bbox=np.asarray(z["bbox"], dtype=np.float32),
            timestamps_s=np.asarray(z["timestamps_s"], dtype=np.float64),
            plausibility=np.asarray(z["plausibility"], dtype=np.uint8),
            provenance=json.loads(str(z["provenance"][0])),
        )


def finite_or_none(obj: Any) -> Any:
    """LA única función de la frontera Python ↔ JSON (CONTRATO.md): NaN e inf → None,
    recursiva sobre dict, list, tuple y arrays de numpy. Nada más los toca."""
    if isinstance(obj, dict):
        return {str(k): finite_or_none(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [finite_or_none(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return finite_or_none(obj.tolist())
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return float(obj) if np.isfinite(obj) else None
    return obj


def pose_payload(take_dir: str | Path, from_frame: int = 0, to_frame: int | None = None) -> dict:
    """La pose como JSON para dibujar sobre el video (Fase 4): sin NaN, redondeada."""
    d = load_pose(take_dir)
    total = int(d.keypoints.shape[0])
    lo = max(0, int(from_frame))
    hi = total if to_frame is None else min(total, int(to_frame) + 1)
    if hi <= lo:
        lo, hi = 0, total
    return finite_or_none({
        "frames": total,
        "from_frame": lo,
        "to_frame": hi - 1,
        "keypoint_names": list(HALPE26_NAMES),
        "limbs": [list(l) for l in HALPE26_LIMBS],
        "timestamps_s": np.round(d.timestamps_s[lo:hi], 4),
        "keypoints": np.round(d.keypoints[lo:hi], 1),
        "scores": np.round(d.scores[lo:hi], 2),
        "bbox": np.round(d.bbox[lo:hi], 1),
        "plausibility": d.plausibility[lo:hi],
        "provenance": d.provenance,
    })
