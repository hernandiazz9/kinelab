"""Cálculos genéricos de nivel 1: duraciones, desplazamientos respecto de un
evento cero, deltas de ángulo, repetibilidad y ganancia. Sin deporte adentro."""

from __future__ import annotations

import numpy as np

from kinelab.events.order import sequence_order
from kinelab.events.signal import butterworth_lowpass, cutoff_for_fps
from kinelab.metrics.core import MetricContext, MetricNull
from kinelab.perception.plausibility import angle_deg


def duration_ms(ctx: MetricContext, shift: dict[str, int], start: str, end: str) -> float:
    a, b = ctx.frame(start, shift), ctx.frame(end, shift)
    if b <= a:
        raise MetricNull(f"{end} no está después de {start}")
    return (b - a) / ctx.fps * 1000.0


def ratio(ctx: MetricContext, shift: dict[str, int], a: tuple[str, str], b: tuple[str, str]) -> float:
    return duration_ms(ctx, shift, *a) / duration_ms(ctx, shift, *b)


def point(ctx: MetricContext, joints: tuple[int, ...], frame: int) -> np.ndarray:
    p = ctx.keypoints[frame, list(joints)]
    if not np.isfinite(p).all():
        raise MetricNull(f"keypoints faltantes en el cuadro {frame}")
    return p.mean(axis=0)


def displacement_cm(ctx: MetricContext, shift: dict[str, int], joints: tuple[int, ...], zero: str, at: str, axis: int, sign: float = 1.0) -> float:
    """Desplazamiento en cm del centro de `joints` entre el evento `zero` y `at`,
    a lo largo de `axis` (0 = x, 1 = y). `sign` vuelve positivo lo que el
    deporte define como positivo (y crece hacia abajo en image_px)."""
    f0, f1 = ctx.frame(zero, shift), ctx.frame(at, shift)
    d = (point(ctx, joints, f1) - point(ctx, joints, f0))[axis] * sign
    cm = ctx.px_to_cm(float(d), f0)
    if cm is None:
        raise MetricNull("sin altura declarada del atleta (data/athletes/<slug>.yaml) o sin altura de cuerpo en px")
    return cm


def angle_delta_deg(ctx: MetricContext, shift: dict[str, int], a: int, b: int, c: int, zero: str, at: str) -> float:
    f0, f1 = ctx.frame(zero, shift), ctx.frame(at, shift)
    k = ctx.keypoints
    v0 = float(angle_deg(k[f0, a], k[f0, b], k[f0, c]))
    v1 = float(angle_deg(k[f1, a], k[f1, b], k[f1, c]))
    if not (np.isfinite(v0) and np.isfinite(v1)):
        raise MetricNull("keypoints faltantes para el ángulo en algún cuadro ancla")
    return v1 - v0


def line_angle_rate(kpts: np.ndarray, i: int, j: int, fps: float, cutoff_hz_max: float = 12.0) -> np.ndarray:
    """Velocidad angular (°/s) de la línea i→j en el plano de imagen, filtrada."""
    d = kpts[:, j] - kpts[:, i]
    ang = np.degrees(np.unwrap(np.arctan2(d[:, 1], d[:, 0])))
    ang = butterworth_lowpass(ang, fps, cutoff_hz=cutoff_for_fps(fps, cutoff_hz_max))
    w = np.gradient(ang) * fps
    w[~np.isfinite(d).all(axis=1)] = np.nan
    return np.abs(w)


def gain(kpts: np.ndarray, fps: float, segments: dict[str, tuple[int, int]], start: int, end: int, *, min_gap_frames: int = 2) -> dict:
    """Picos de velocidad angular por segmento en [start, end] y cociente entre
    consecutivos. El orden sólo se declara si los picos están a ≥ 2 cuadros."""
    peaks: dict[str, int] = {}
    vals: dict[str, float] = {}
    for name, (i, j) in segments.items():
        w = line_angle_rate(kpts, i, j, fps)[start : end + 1]
        if not np.isfinite(w).any():
            continue
        k = int(np.nanargmax(w))
        peaks[name] = start + k
        vals[name] = float(w[k])
    names = list(segments)
    ratios = {}
    for a, b in zip(names, names[1:]):
        if a in vals and b in vals and vals[a] > 0:
            ratios[f"{a}_to_{b}"] = round(vals[b] / vals[a], 3)
    return {"peaks_deg_s": {k: round(v, 1) for k, v in vals.items()}, "peak_frames": peaks, "ratios": ratios, "sequence_order": sequence_order(peaks, min_gap_frames=min_gap_frames)}


def dtw_normalized(a: np.ndarray, b: np.ndarray) -> float:
    """Distancia DTW media por paso entre dos curvas 1-D (sin NaN), O(n·m)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    n, m = a.size, b.size
    if n == 0 or m == 0:
        return float("nan")
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0.0
    for i in range(1, n + 1):
        cost = np.abs(a[i - 1] - b)
        for j in range(1, m + 1):
            D[i, j] = cost[j - 1] + min(D[i - 1, j], D[i, j - 1], D[i - 1, j - 1])
    return float(D[n, m] / (n + m))


def repeatability_scalar(values: list[float]) -> dict:
    v = np.asarray([x for x in values if x is not None and np.isfinite(x)], float)
    if v.size < 2:
        return {"kind": "sd_abs", "value": None, "n": int(v.size), "noise_floor": None}
    return {"kind": "sd_abs", "value": round(float(v.std(ddof=1)), 3), "n": int(v.size), "noise_floor": None}


def repeatability_curves(curves: list[np.ndarray], samples: int = 50) -> dict:
    """DTW normalizado medio entre pares de curvas remuestreadas a `samples` puntos
    (normalizadas en tiempo 0–1: compara forma, no duración)."""
    rs = []
    for c in curves:
        c = np.asarray(c, float)
        c = c[np.isfinite(c)]
        if c.size >= 4:
            rs.append(np.interp(np.linspace(0, 1, samples), np.linspace(0, 1, c.size), c))
    if len(rs) < 2:
        return {"kind": "dtw_normalized", "value": None, "n": len(rs), "noise_floor": None}
    d = [dtw_normalized(rs[i], rs[j]) for i in range(len(rs)) for j in range(i + 1, len(rs))]
    return {"kind": "dtw_normalized", "value": round(float(np.mean(d)), 4), "n": len(rs), "noise_floor": None}
