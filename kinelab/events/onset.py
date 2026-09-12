"""Refinamiento de bordes de quietud: un umbral de velocidad corta unos cuadros
tarde al arrancar y unos cuadros temprano al frenar; se camina hasta el punto
donde la velocidad deja de bajar (el inicio real) o de subir."""

from __future__ import annotations

import numpy as np


def onset_backtrack(speed: np.ndarray, end: int, max_back: int) -> int:
    """Desde el último cuadro quieto `end`, retrocede mientras la velocidad venga
    estrictamente bajando hacia atrás (o sea, subiendo hacia adelante)."""
    s = np.asarray(speed, dtype=float)
    i = int(end)
    while i > 0 and end - i < max_back and np.isfinite(s[i - 1]) and np.isfinite(s[i]) and s[i - 1] < s[i]:
        i -= 1
    return i


def settle_forward(speed: np.ndarray, start: int, max_forward: int) -> int:
    """Desde el primer cuadro quieto `start`, avanza mientras la velocidad siga
    bajando: el frenado real termina donde deja de bajar."""
    s = np.asarray(speed, dtype=float)
    i = int(start)
    n = s.size
    while i + 1 < n and i - start < max_forward and np.isfinite(s[i + 1]) and np.isfinite(s[i]) and s[i + 1] < s[i]:
        i += 1
    return i
