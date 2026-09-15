"""Señales derivadas de la pose: centro de las manos, filtrado, velocidad, eje principal.

Portado en parte de padel-coach analyzer/padel_analyzer/kinematics.py:327-360
(`fill_nan_linear`, `smooth`) (ADR-013). El filtro de los detectores es
Butterworth de 4º orden con `filtfilt`, corte parametrizado por fps: nunca un
corte fijo en cuadros (ESPECIFICACION 2.3).
"""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, filtfilt, savgol_filter

from kinelab.perception.gaps import interpolate_gaps
from kinelab.perception.keypoints import H


def fill_nan_linear(x: np.ndarray) -> np.ndarray:
    """Interpola NaN interiores; los bordes toman el valor válido más cercano. (T,) o (T,K)."""
    x = np.asarray(x, dtype=float).copy()
    if x.ndim == 1:
        ok = np.isfinite(x)
        if ok.all() or not ok.any():
            return x
        idx = np.arange(x.size)
        x[~ok] = np.interp(idx[~ok], idx[ok], x[ok])
        return x
    for k in range(x.shape[1]):
        x[:, k] = fill_nan_linear(x[:, k])
    return x


def savgol(x: np.ndarray, fps: float, window_s: float = 0.06, poly: int = 2) -> np.ndarray:
    """Savitzky–Golay con ventana derivada del fps (impar, ≥ poly + 2). NaN preservados."""
    x = np.asarray(x, dtype=float)
    n = x.shape[0]
    if n < poly + 2:
        return x.copy()
    w = max(poly + 2, int(round(window_s * fps)))
    w = min(w | 1, n if n % 2 else n - 1)
    ok = np.isfinite(x)
    y = savgol_filter(fill_nan_linear(x), w, poly, axis=0, mode="interp")
    y[~ok] = np.nan
    return y


def cutoff_for_fps(fps: float, cutoff_hz_max: float = 12.0) -> float:
    """Corte del pasabajos: `min(cutoff_hz_max, 0.2 · fps)`, siempre bajo Nyquist."""
    return float(min(cutoff_hz_max, 0.2 * fps))


def butterworth_lowpass(x: np.ndarray, fps: float, *, cutoff_hz: float, order: int = 4) -> np.ndarray:
    """Pasabajos Butterworth de fase cero (`filtfilt`) sobre (T,) o (T,K).
    Los NaN se rellenan linealmente antes y se restauran después. Señales más
    cortas que el relleno del filtro vuelven rellenadas pero sin filtrar."""
    x = np.asarray(x, dtype=float)
    ok = np.isfinite(x)
    filled = fill_nan_linear(x)
    if not np.isfinite(filled).any():
        return x.copy()
    nyq = 0.5 * fps
    wn = min(cutoff_hz / nyq, 0.99)
    b, a = butter(order, wn)
    padlen = 3 * max(len(a), len(b))
    if x.shape[0] <= padlen:
        y = filled
    else:
        y = filtfilt(b, a, filled, axis=0, padlen=padlen)
    y = np.asarray(y, dtype=float)
    y[~ok] = np.nan
    return y


def hands_center(kpts: np.ndarray, scores: np.ndarray | None = None, *, min_score: float = 0.0, max_gap: int = 5) -> np.ndarray:
    """Centro de las dos muñecas `(T,2)`, **pesado por la confianza de cada muñeca en
    cada cuadro**. Las dos manos van juntas en el grip: independiente de la lateralidad.

    - `scores` `(T,J)` son los scores crudos del modelo (`pose.npz`). Sin ellos, las
      dos muñecas pesan igual, que es lo que hacía esta función antes.
    - `min_score`: una muñeca por debajo de ese score **no entra** en el cuadro. El
      umbral es del deporte (en golf, `GolfEventParams.wrist_score_min`), no del
      motor; el default 0,0 es "sin umbral".
    - Si las dos muñecas quedan afuera (o faltan) en un cuadro, el punto queda `NaN`
      y lo rellena el **mismo relleno acotado de la percepción**
      (`interpolate_gaps`, rachas ≤ `max_gap`, nunca extrapolando bordes): un hueco
      corto se interpola, uno largo se queda en `NaN`. Nunca una invención.

    Por qué (medido, informe del encargo 15 y ADR-017 §"Lo que la regla no arregla").
    En los dos clips del 7/9 el modelo **pierde la muñeca izquierda justo en el top**
    —en `cortado.mp4`, cuadros 32–38: score 0,35 · 0,36 · 0,40 · 0,40 · 0,43 · 0,51 ·
    0,39, con la x saltando 414 → 435 → 356 → 672 → 486 → 491 → 497 → 331 px— mientras
    la derecha va suave y con score ≥ 0,53 en todo el clip. Un promedio a dos manos
    con peso igual hereda entero ese salto de 300 px, y el top —que es un cambio de
    sentido de esta misma señal— se mueve con él: contra la muñeca derecha sola, el
    error del top era de −3, −2, 0 y +1 cuadros en los cuatro clips reales. Pesar por
    confianza y descartar lo que el modelo declara malo es medir con la muñeca que el
    modelo ve, sin elegirla a mano ni depender de la lateralidad.
    """
    kpts = np.asarray(kpts, dtype=float)
    pair = np.stack([kpts[:, H.LEFT_WRIST], kpts[:, H.RIGHT_WRIST]], axis=1)  # (T,2,2)
    if scores is None:
        w = np.ones(pair.shape[:2], dtype=float)
    else:
        s = np.asarray(scores, dtype=float)
        w = np.stack([s[:, H.LEFT_WRIST], s[:, H.RIGHT_WRIST]], axis=1)  # (T,2)
        w = np.where(np.isfinite(w) & (w >= float(min_score)), w, 0.0)
    w = np.where(np.isfinite(pair).all(axis=2), w, 0.0)
    total = w.sum(axis=1)
    num = np.einsum("tk,tkc->tc", w, np.nan_to_num(pair, nan=0.0))
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(total[:, None] > 0, num / np.where(total > 0, total, 1.0)[:, None], np.nan)
    return interpolate_gaps(out, max_gap)


def speed(positions: np.ndarray, fps: float, scale: np.ndarray | float) -> np.ndarray:
    """Velocidad `(T,)` en alturas de cuerpo por segundo de posiciones YA filtradas `(T,2)`."""
    p = np.asarray(positions, dtype=float)
    T = p.shape[0]
    if T < 2:
        return np.full(T, np.nan)
    ok = np.isfinite(p).all(axis=1)
    f = fill_nan_linear(p)
    v = np.gradient(f, axis=0) * fps
    s = np.hypot(v[:, 0], v[:, 1]) / np.asarray(scale, dtype=float)
    s[~ok] = np.nan
    return s


def principal_axis(positions: np.ndarray, start: int, end: int) -> np.ndarray:
    """Vector unitario del eje principal de la trayectoria entre `start` y `end` (SVD)."""
    seg = np.asarray(positions, dtype=float)[start : end + 1]
    seg = seg[np.isfinite(seg).all(axis=1)]
    if seg.shape[0] < 2:
        return np.array([1.0, 0.0])
    c = seg - seg.mean(axis=0)
    _, _, vt = np.linalg.svd(c, full_matrices=False)
    axis = vt[0]
    return axis / (np.linalg.norm(axis) or 1.0)
