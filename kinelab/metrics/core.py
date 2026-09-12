"""Evaluación de una métrica: del registro al sextuplo del CONTRATO.

`evaluate` corre `metric.compute(ctx, shift)` con los eventos anclados sin
mover y movidos ±1 cuadro (invariante 8): el rango que sale es la
incertidumbre. La confianza es la media de los scores de los keypoints
involucrados en los cuadros ancla. `judgment_allowed` viene del registro.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from kinelab.metrics.registry import Metric, judgment_allowed


@dataclass
class MetricContext:
    """Todo lo que una métrica puede mirar: pose (con huecos rellenados),
    escala, eventos de la repetición y vista. Nada de deporte."""

    keypoints: np.ndarray  # (T,J,2) px, huecos rellenados
    scores: np.ndarray  # (T,J)
    fps: float
    view: str
    body_height_px: np.ndarray  # (T,)
    events: dict[str, int]  # id → cuadro, para esta repetición
    frame_start: int
    frame_end: int
    athlete_height_m: float | None = None
    hands_speed: np.ndarray | None = None  # (T,) alturas/s
    extra: dict = field(default_factory=dict)

    def frame(self, event: str, shift: dict[str, int] | None = None) -> int:
        f = self.events[event] + (shift or {}).get(event, 0)
        return int(min(max(f, 0), self.keypoints.shape[0] - 1))

    def px_to_cm(self, px: float, frame: int) -> float | None:
        """Píxeles → cm con la altura de cuerpo en px de ese cuadro y la altura declarada."""
        if self.athlete_height_m is None:
            return None
        bh = float(self.body_height_px[frame])
        if not np.isfinite(bh) or bh <= 0:
            return None
        return float(px / bh * self.athlete_height_m * 100.0)


class MetricNull(Exception):
    """La métrica no se puede calcular; el mensaje es el `null_reason`."""


Compute = Callable[[MetricContext, dict[str, int]], float]


def _confidence(ctx: MetricContext, metric: Metric, joints: tuple[int, ...]) -> dict | None:
    frames = [ctx.frame(e) for e in metric.anchored_to if e in ctx.events]
    if not frames or not joints:
        return None
    s = ctx.scores[np.ix_(frames, list(joints))]
    s = s[np.isfinite(s)]
    return None if s.size == 0 else {"value": round(float(s.mean()), 3), "method": "keypoint_scores_at_anchors"}


def evaluate(metric: Metric, ctx: MetricContext, *, joints: tuple[int, ...] = ()) -> dict:
    fps_min_met = ctx.fps >= metric.fps_min
    base = {
        "unit": metric.unit,
        "view": ctx.view,
        "mdc": metric.mdc,
        "level": metric.level,
        "fps_min": metric.fps_min,
        "fps_min_met": fps_min_met,
        "judgment_allowed": judgment_allowed(metric, view=ctx.view, fps_real=ctx.fps),
        "confidence": None,
        "uncertainty": None,
    }
    if ctx.view not in metric.views:
        return {"value": None, **base, "judgment_allowed": False, "null_reason": f"vista {ctx.view} no válida para esta métrica (válidas: {', '.join(metric.views)})"}
    if not fps_min_met:
        return {"value": None, **base, "judgment_allowed": False, "null_reason": f"fps_real {ctx.fps:g} por debajo de fps_min {metric.fps_min:g}"}
    missing = [e for e in metric.anchored_to if e not in ctx.events]
    if missing:
        return {"value": None, **base, "judgment_allowed": False, "null_reason": f"sin evento {', '.join(missing)} en esta repetición"}
    if metric.compute is None:
        return {"value": None, **base, "judgment_allowed": False, "null_reason": "métrica sin implementación"}
    try:
        value = float(metric.compute(ctx, {}))
        alts = [value]
        for e in metric.anchored_to:
            for d in (-1, 1):
                alts.append(float(metric.compute(ctx, {e: d})))
    except MetricNull as e:
        return {"value": None, **base, "judgment_allowed": False, "null_reason": str(e)}
    alts = [a for a in alts if np.isfinite(a)]
    if not alts or not np.isfinite(value):
        return {"value": None, **base, "judgment_allowed": False, "null_reason": "valor no finito (keypoints faltantes en los cuadros ancla)"}
    nd = 1 if metric.unit in ("ms", "cm") else 3
    return {
        "value": round(value, nd),
        **base,
        "confidence": _confidence(ctx, metric, joints),
        "uncertainty": {"low": round(min(alts), nd), "high": round(max(alts), nd), "method": f"±1 cuadro en cada evento ancla a {ctx.fps:g} fps"},
        "null_reason": None,
    }
