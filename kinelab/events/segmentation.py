"""Segmentación de repeticiones sobre la velocidad de las manos.

Portado en espíritu de padel-coach analyzer/padel_analyzer/events.py:123-160
(ADR-013): picos con prominencia relativa al propio clip, y dos filtros
negativos que separan un gesto de alguien que camina o gesticula: velocidad
plausible máxima (más rápido es el tracker saltando) y agudeza (el pico contra
lo que la persona venía haciendo alrededor). Los umbrales llegan por parámetro.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import find_peaks


@dataclass(frozen=True)
class SegmentationParams:
    min_gap_s: float = 2.0  # dos repeticiones no pueden estar más cerca que esto
    prominence_floor: float = 0.5  # alturas de cuerpo / s
    max_speed: float = 15.0  # alturas/s: un brazo no llega; el tracker sí
    sharpness_min: float = 2.2  # pico / mediana en la ventana de ±sharpness_window_s
    sharpness_window_s: float = 1.0
    lookback_s: float = 2.0  # ventana provisoria hacia atrás del pico
    lookahead_s: float = 1.5


@dataclass
class RepCandidate:
    peak: int
    peak_speed: float
    start: int
    end: int


def segment_reps(speed: np.ndarray, fps: float, params: SegmentationParams) -> tuple[list[RepCandidate], dict[str, int]]:
    """Candidatos a repetición y conteo de descartes por razón."""
    s = np.asarray(speed, dtype=float)
    T = s.size
    valid = np.isfinite(s)
    discards: dict[str, int] = {}
    if valid.sum() < 3 or fps <= 0:
        return [], {"sin_datos": 1}
    x = np.where(valid, s, 0.0)
    vals = x[valid]
    prominence = max(0.25 * (float(np.percentile(vals, 95)) - float(np.median(vals))), params.prominence_floor)
    distance = max(1, int(round(params.min_gap_s * fps)))
    peaks, _ = find_peaks(x, distance=distance, prominence=prominence)
    win = max(1, int(round(params.sharpness_window_s * fps)))
    out: list[RepCandidate] = []
    for p in (int(q) for q in peaks):
        if not valid[p]:
            discards["nan"] = discards.get("nan", 0) + 1
            continue
        if x[p] > params.max_speed:
            discards["velocidad_implausible"] = discards.get("velocidad_implausible", 0) + 1
            continue
        ctx = x[max(0, p - win) : p + win + 1]
        med = float(np.median(ctx[np.isfinite(ctx)]))
        if x[p] < params.sharpness_min * max(med, 1e-6):
            discards["sin_pico"] = discards.get("sin_pico", 0) + 1
            continue
        out.append(RepCandidate(peak=p, peak_speed=float(x[p]), start=max(0, p - int(round(params.lookback_s * fps))), end=min(T - 1, p + int(round(params.lookahead_s * fps)))))
    return out, discards
