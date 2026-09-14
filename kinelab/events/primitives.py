"""Primitivas de detección de eventos, sin deporte adentro.

Todo evento lleva su tolerancia en cuadros y la incertidumbre en segundos que
implica a ese fps (CONTEXTO.md, invariante 8).
"""

from __future__ import annotations

import math
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
    # Estimación del instante entre dos cuadros, si el deporte la define para este
    # evento (ver `subframe_crossing`). `None` = no hay. No reemplaza a `frame`, que
    # sigue siendo el ancla de todo; y una corrección manual de `frame` no la toca:
    # describe la señal, con sus dos cuadros explícitos.
    subframe: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def make_event(event_id: str, frame: int, fps: float, *, tol_frames: int, method: str) -> Event:
    return Event(id=event_id, frame=int(frame), t_s=round(frame / fps, 4), tol_frames=tol_frames, uncertainty_s=round(tol_frames / fps, 5), method=method)


def stillness_signal(speed: np.ndarray, fps: float, window_s: float = 0.1) -> np.ndarray:
    """Velocidad con mediana móvil corta: un cuadro ruidoso no rompe una ventana de quietud."""
    from scipy.signal import medfilt

    x = np.asarray(speed, dtype=float)
    ok = np.isfinite(x)
    k = max(3, int(round(window_s * fps)) | 1)
    if x.size < k:
        return x.copy()
    y = medfilt(np.where(ok, x, 0.0), k)
    y[~ok] = np.nan
    return y


def _still(speed: np.ndarray, max_speed: float) -> np.ndarray:
    with np.errstate(invalid="ignore"):
        return np.isfinite(speed) & (speed < max_speed)


def still_run_start(speed: np.ndarray, *, max_speed: float, end: int) -> int:
    """Primer cuadro de la racha de quietud (`speed < max_speed`) que termina en `end`."""
    still = _still(speed, max_speed)
    i = int(end)
    while i > 0 and still[i - 1]:
        i -= 1
    return i


@dataclass
class SubframeCrossing:
    """Instante sub-cuadro en que una señal 1-D cruza un nivel, por interpolación
    lineal entre el cuadro anterior y el posterior al cruce. Si el cruce no es
    claro, `fraction` es None y `null_reason` dice por qué: nunca un número forzado."""

    frame_before: int | None = None
    frame_after: int | None = None
    fraction: float | None = None  # 0–1 entre frame_before y frame_after
    slope: float | None = None  # unidades de la señal por cuadro, en el segmento del cruce
    curvature_frames: float | None = None  # cota: el cruce recalculado extrapolando los segmentos vecinos (±1 cuadro)
    noise_frames: float | None = None  # ruido de la señal (σ) dividido por la pendiente local
    uncertainty_frames: float | None = None  # √(curvatura² + ruido²)
    null_reason: str | None = None


def subframe_crossing(x: np.ndarray, level: float, *, near: int, lo: int, hi: int, noise_sigma: float | None = None) -> SubframeCrossing:
    """Cruce de `x` por `level` entre dos cuadros consecutivos de `[lo, hi]`, contiguo
    a `near` (el cuadro entero del evento, que no cambia).

    Cruce claro = exactamente un cambio de signo de `x − level` en la ventana, y en
    el segmento `(near − 1, near)` o `(near, near + 1)`. La fracción sale de la recta
    entre los dos cuadros. Incertidumbre (invariante 8: ±1 cuadro con la velocidad
    local): el cruce recalculado extrapolando la recta de cada segmento vecino,
    `(i − 1, i)` y `(i + 1, i + 2)`. Si la trayectoria fuera recta darían lo mismo; la
    diferencia mide cuánto se curva en un cuadro. Más el ruido de la señal
    (`noise_sigma`, en las unidades de `x`, sobre los tres valores que entran en la
    recta) propagado por la pendiente local. Las dos cotas se combinan en cuadratura.
    """
    s = np.asarray(x, dtype=float) - float(level)
    n = s.size
    if not np.isfinite(level):
        return SubframeCrossing(null_reason="sin nivel de referencia (posición no finita)")
    lo, hi = max(0, int(lo)), min(n - 1, int(hi))
    if hi - lo < 1:
        return SubframeCrossing(null_reason=f"ventana vacía [{lo}, {hi}]")
    idx = np.arange(lo, hi)
    a, b = s[idx], s[idx + 1]
    ok = np.isfinite(a) & np.isfinite(b)
    cross = idx[ok & (((a <= 0) & (b > 0)) | ((a >= 0) & (b < 0)))]
    if cross.size == 0:
        return SubframeCrossing(null_reason=f"la señal no cruza el nivel de referencia en la ventana [{lo}, {hi}]")
    if cross.size > 1:
        where = ", ".join(str(int(c)) for c in cross)
        return SubframeCrossing(null_reason=f"la señal cruza el nivel {cross.size} veces en la ventana [{lo}, {hi}] (cuadros {where}): cruce ambiguo")
    i = int(cross[0])
    if i not in (near - 1, near):
        return SubframeCrossing(null_reason=f"el cruce (entre {i} y {i + 1}) no es contiguo al cuadro del evento ({near})")
    slope = float(s[i + 1] - s[i])
    f = float(s[i] / (s[i] - s[i + 1]))
    t = i + f
    devs = []
    for k in (i - 1, i + 1):
        if 0 <= k and k + 1 < n and np.isfinite(s[k]) and np.isfinite(s[k + 1]):
            sk = float(s[k + 1] - s[k])
            if sk != 0.0 and np.sign(sk) == np.sign(slope):
                devs.append(abs(k - s[k] / sk - t))
    curv = max(devs) if devs else None
    noise = None
    if noise_sigma is not None and np.isfinite(noise_sigma) and noise_sigma > 0:
        noise = float(noise_sigma) * math.sqrt(f * f + (1.0 - f) ** 2 + 1.0) / abs(slope)
    parts = [v for v in (curv, noise) if v is not None]
    unc = math.sqrt(sum(v * v for v in parts)) if parts else None
    r = lambda v, d: None if v is None else round(float(v), d)
    return SubframeCrossing(frame_before=i, frame_after=i + 1, fraction=r(f, 4), slope=r(slope, 3), curvature_frames=r(curv, 4), noise_frames=r(noise, 4), uncertainty_frames=r(unc, 4), null_reason=None)


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
