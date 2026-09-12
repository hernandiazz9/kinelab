"""Primitivas de detección de eventos, sin deporte adentro.

Todo evento lleva su tolerancia en cuadros y la incertidumbre en segundos que
implica a ese fps (CONTEXTO.md, invariante 8).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from kinelab.events.signal import butterworth_lowpass


@dataclass
class Event:
    id: str
    frame: int
    t_s: float
    tol_frames: int
    uncertainty_s: float
    method: str
    manual: bool = False
    frame_detected: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def make_event(event_id: str, frame: int, fps: float, *, tol_frames: int, method: str) -> Event:
    return Event(id=event_id, frame=int(frame), t_s=round(frame / fps, 4), tol_frames=tol_frames, uncertainty_s=round(tol_frames / fps, 5), method=method)


def _still(speed: np.ndarray, max_speed: float) -> np.ndarray:
    with np.errstate(invalid="ignore"):
        return np.isfinite(speed) & (speed < max_speed)


def stable_window_end(speed: np.ndarray, fps: float, *, max_speed: float, min_duration_s: float, before: int) -> int | None:
    """Último cuadro de la ventana de quietud (≥ `min_duration_s`) que precede al
    movimiento anterior a `before`. `None` si no hay ninguna."""
    still = _still(speed, max_speed)
    need = max(1, int(round(min_duration_s * fps)))
    i = min(int(before), still.size) - 1
    while i >= 0:
        if not still[i]:
            i -= 1
            continue
        end = i
        while i >= 0 and still[i]:
            i -= 1
        if end - i >= need:
            return end
    return None


def stable_window_start(speed: np.ndarray, fps: float, *, max_speed: float, min_duration_s: float, after: int) -> int | None:
    """Primer cuadro de la primera ventana de quietud (≥ `min_duration_s`) después de `after`."""
    still = _still(speed, max_speed)
    need = max(1, int(round(min_duration_s * fps)))
    i = max(int(after) + 1, 0)
    n = still.size
    while i < n:
        if not still[i]:
            i += 1
            continue
        start = i
        while i < n and still[i]:
            i += 1
        if i - start >= need:
            return start
    return None


def direction_change(pos_axis: np.ndarray, *, before: int, after: int) -> int | None:
    """Último cuadro en `(after, before)` donde la velocidad 1-D cambia de signo:
    el instante en que el movimiento se invierte. `None` si es monótono."""
    x = np.asarray(pos_axis, dtype=float)
    if before - after < 3:
        return None
    v = np.gradient(x)
    for i in range(int(before) - 1, int(after) + 1, -1):
        a, b = v[i - 1], v[i]
        if not (np.isfinite(a) and np.isfinite(b)) or a == 0.0:
            continue
        if a * b <= 0:
            return i - 1 if abs(a) < abs(b) else i
    return None


def peak_window(criterion: np.ndarray, *, peak: int, radius: int, valid: np.ndarray | None = None) -> int:
    """Cuadro de mínimo `criterion` dentro de `[peak − radius, peak + radius]`."""
    c = np.asarray(criterion, dtype=float)
    lo, hi = max(0, int(peak) - int(radius)), min(c.size - 1, int(peak) + int(radius))
    idx = np.arange(lo, hi + 1)
    ok = np.isfinite(c[idx]) if valid is None else (np.isfinite(c[idx]) & np.asarray(valid)[idx])
    if not ok.any():
        return int(peak)
    idx = idx[ok]
    return int(idx[int(np.argmin(c[idx]))])


def d2_inflection(x: np.ndarray, fps: float, *, cutoff_hz: float) -> np.ndarray:
    """Índices donde la segunda derivada de la señal filtrada cruza por cero."""
    y = butterworth_lowpass(np.asarray(x, dtype=float), fps, cutoff_hz=cutoff_hz)
    a = np.gradient(np.gradient(y)) * fps * fps
    s = np.sign(a)
    s[s == 0] = 1
    return np.flatnonzero(s[1:] != s[:-1]) + 1
