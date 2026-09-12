"""Relleno de huecos acotado sobre series de keypoints.

Derivado, no crudo: se aplica al leer `pose.npz`, nunca antes de escribirlo
(CONTEXTO.md, invariante 1).
"""

from __future__ import annotations

import numpy as np


def gap_runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Rachas `[start, end)` de `True` en una máscara 1-D."""
    mask = np.asarray(mask, dtype=bool)
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(mask)))
    return runs


# Portado de padel-coach analyzer/padel_analyzer/pose.py:219-246 (ADR-013).
def interpolate_gaps(kpts: np.ndarray, max_gap: int = 5) -> np.ndarray:
    """Rellena linealmente las rachas de NaN de largo ≤ `max_gap`, por articulación
    y eje. Sólo rachas acotadas por valores válidos a ambos lados: los bordes
    nunca se extrapolan. No muta la entrada. Acepta `(T, J, 2)` o `(T, K)`."""
    src = np.asarray(kpts)
    out = src.copy()
    T = out.shape[0]
    if T < 3:
        return out
    idx = np.arange(T)
    flat = out.reshape(T, -1)
    for c in range(flat.shape[1]):
        col = flat[:, c]
        nan = np.isnan(col)
        if not nan.any() or nan.all():
            continue
        filled = np.interp(idx, idx[~nan], col[~nan])
        for start, end in gap_runs(nan):
            if start > 0 and end < T and (end - start) <= max_gap:
                col[start:end] = filled[start:end]
    return out
