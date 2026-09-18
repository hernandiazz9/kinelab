"""Cálculos genéricos de nivel 1: duraciones, desplazamientos respecto de un
evento cero, deltas de ángulo y repetibilidad. Sin deporte adentro.

La ganancia de velocidad angular y el orden de la secuencia **no están acá y no
vuelven** (ADR-018): el arnés midió que la velocidad angular de una línea en el
plano de imagen es un artefacto del largo proyectado del segmento (80× de error
en la línea de caderas desde `down_the_line`), no una medición.
"""

from __future__ import annotations

import numpy as np

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


# Por qué la repetibilidad sale en `null` mientras no haya piso de ruido medido
# (CONTRATO.md §summary, ADR-019). `CONTEXTO.md` §piso de ruido: "si la señal es
# menor que el piso, la métrica no existe, por más que el código la calcule", y
# la repetibilidad **siempre** lleva el piso del propio pipeline restado y
# declarado. Devolver la SD con `noise_floor: None` al lado publica como
# variación del atleta algo que puede ser entero del instrumento: en
# `cortado3-lento.mp4` la SD del backswing entre dos repeticiones dio 17,7 ms y
# la ambigüedad de los eventos que la producen es de 4 a 16 cuadros. El `n` se
# conserva: decir cuántas repeticiones entraron no afirma nada sobre el valor.
NO_NOISE_FLOOR = (
    "sin piso de ruido medido del pipeline: una SD entre repeticiones no separa "
    "la variación del atleta de la del instrumento (CONTEXTO.md §piso de ruido, ADR-019)"
)


def repeatability_scalar(values: list[float]) -> dict:
    v = np.asarray([x for x in values if x is not None and np.isfinite(x)], float)
    return {"kind": "sd_abs", "value": None, "n": int(v.size), "noise_floor": None, "null_reason": NO_NOISE_FLOOR}


def resample_curves(curves: list[np.ndarray], samples: int = 50) -> list[np.ndarray]:
    """Las curvas con al menos 4 puntos finitos, remuestreadas a `samples` puntos
    y normalizadas en tiempo 0–1 (compara forma, no duración). Es la entrada del
    DTW por pares: sigue acá para el día que haya piso de ruido medido."""
    rs = []
    for c in curves:
        c = np.asarray(c, float)
        c = c[np.isfinite(c)]
        if c.size >= 4:
            rs.append(np.interp(np.linspace(0, 1, samples), np.linspace(0, 1, c.size), c))
    return rs


def repeatability_curves(curves: list[np.ndarray], samples: int = 50) -> dict:
    """DTW normalizado medio entre pares de curvas. Mismo motivo que en
    `repeatability_scalar`: sin piso de ruido medido, `null` con razón, y `n`
    —cuántas curvas entraron— se conserva."""
    return {"kind": "dtw_normalized", "value": None, "n": len(resample_curves(curves, samples)), "noise_floor": None, "null_reason": NO_NOISE_FLOOR}
