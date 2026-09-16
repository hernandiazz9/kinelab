"""Evaluación de una métrica: del registro al sextuplo del CONTRATO.

`evaluate` corre `metric.compute(ctx, shift)` con los eventos anclados sin
mover y movidos ± la tolerancia en cuadros de cada evento (invariante 8; ±1 si
la repetición no declara otra): el rango que sale es la incertidumbre. La
confianza es la media de los scores de los keypoints involucrados en los
cuadros ancla. `judgment_allowed` viene del registro.

Acá vive también **la escala**: cuántos píxeles mide la estatura declarada del
atleta en esta repetición, que es el divisor de toda métrica en cm. Ver
`stature_chain_px` y `MetricContext.scale_px`, y `CONTRATO.md` §La escala.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from kinelab.metrics.registry import Metric, fps_min_met, judgment_allowed

# `_rolling_nanmedian` es la mediana móvil de `body_height_px`, la misma que
# suaviza la otra escala del motor. Es privada por ahora: cuando
# `kinelab/perception/framing.py` esté libre pasa a pública y las dos escalas
# viven juntas (ver el informe del encargo 14).
from kinelab.perception.framing import _rolling_nanmedian
from kinelab.perception.keypoints import H

# Cadena de la estatura en el plano de imagen: tobillo → rodilla → cadera →
# hombro → cabeza, cada eslabón entre los puntos MEDIOS de los dos lados (la
# coronilla no tiene par). Son los mismos centros articulares con los que el
# motor ya mide; ningún largo de segmento sale de una tabla.
STATURE_CHAIN: tuple[tuple[int, ...], ...] = (
    (H.LEFT_ANKLE, H.RIGHT_ANKLE),
    (H.LEFT_KNEE, H.RIGHT_KNEE),
    (H.LEFT_HIP, H.RIGHT_HIP),
    (H.LEFT_SHOULDER, H.RIGHT_SHOULDER),
    (H.HEAD,),
)
# Ventana de la mediana móvil que se le pasa a la cadena antes de tomar el
# máximo. Va en SEGUNDOS, no en cuadros. Un máximo crudo lo rompe un solo
# cuadro malo: medido sobre 64_01, la cabeza saltando 200 px durante 1 a 15
# cuadros infla el máximo un 6,6 % —y achica un 6,2 % las siete métricas en
# cm—, y esta ventana lo absorbe entero (una racha mala tiene que durar más de
# media ventana, 0,125 s, para pasar). Es la misma disciplina que
# `body_height_px`, que suaviza con 1 s; acá es más corta porque la extensión
# del finish dura poco y una ventana larga la aplanaría.
SCALE_SMOOTH_S = 0.25


def _link_point(kpts: np.ndarray, joints: tuple[int, ...]) -> np.ndarray:
    """El punto medio de `joints` por cuadro, `(T,2)`. Con un solo keypoint es
    ese keypoint; la coronilla cae a la nariz si falta, igual que en
    `body_height_px`."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # cuadros sin ninguno de los dos keypoints
        p = np.nanmean(kpts[:, list(joints), :], axis=1)
    if joints == (H.HEAD,):
        p = np.where(np.isfinite(p), p, kpts[:, H.NOSE, :])
    return p


def stature_chain_px(kpts: np.ndarray, fps: float, *, window_s: float = SCALE_SMOOTH_S) -> np.ndarray:
    """Suma de los largos **proyectados** de `STATURE_CHAIN` por cuadro, `(T,)`,
    con mediana móvil de `window_s` segundos.

    Es la estatura del sujeto "desdoblada" en el plano de imagen: cada eslabón
    se acorta con la perspectiva, nunca se alarga, así que la cadena es una
    cota inferior de lo que mediría el sujeto de pie y paralelo al plano de
    imagen. De ahí que la escala se tome como su **máximo** dentro de la
    repetición (`MetricContext.scale_px`).
    """
    if fps <= 0 or not np.isfinite(fps):
        raise ValueError(f"fps tiene que ser positivo: {fps}")
    kpts = np.asarray(kpts, dtype=np.float64)
    if kpts.ndim != 3 or kpts.shape[-1] != 2:
        raise ValueError(f"se esperaba kpts (T, J, 2); llegó {kpts.shape}")
    if kpts.shape[0] == 0:
        return np.full(0, np.nan)
    pts = [_link_point(kpts, j) for j in STATURE_CHAIN]
    total = np.zeros(kpts.shape[0])
    for a, b in zip(pts, pts[1:]):
        d = b - a
        total += np.hypot(d[:, 0], d[:, 1])
    total = np.where(np.isfinite(total) & (total > 0), total, np.nan)
    return _rolling_nanmedian(total, int(round(window_s * fps)))


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
    # De dónde sale `fps`: `medido_aqui` (cronómetro, camino calibrado) o
    # `sin_verificar` (camino declarado, ADR-016). El default es el conservador:
    # una toma de procedencia desconocida no habilita juicio.
    fps_provenance: str = "sin_verificar"
    athlete_height_m: float | None = None
    hands_speed: np.ndarray | None = None  # (T,) alturas/s
    # Tolerancia en cuadros de cada evento ancla en ESTA repetición (`tol_frames`).
    # La invariante 8 se propaga desde ahí y no desde un ±1 fijo: un evento cuya
    # regla decidió dentro del ruido declara una banda más ancha y las métricas
    # ancladas a él la heredan. Vacío = ±1 cuadro, que es lo de siempre.
    tolerances: dict[str, int] = field(default_factory=dict)
    extra: dict = field(default_factory=dict)
    _scale_px: float | None = field(default=None, repr=False, compare=False)
    _scale_frame: int | None = field(default=None, repr=False, compare=False)

    def frame(self, event: str, shift: dict[str, int] | None = None) -> int:
        f = self.events[event] + (shift or {}).get(event, 0)
        return int(min(max(f, 0), self.keypoints.shape[0] - 1))

    def scale_px(self) -> float | None:
        """Píxeles que mide la **estatura declarada** en esta repetición: el
        máximo de `stature_chain_px` entre `frame_start` y `frame_end`.

        Una sola escala por repetición, no por cuadro: el tamaño del atleta no
        cambia durante el swing y su *extensión vertical aparente* sí. Medido
        sobre los diez swings de mocap del sujeto 64 de CMU, la altura
        cabeza→tobillos del address —la escala anterior— mide el 89,1 % de la
        estatura (un golfista en address está agachado y girado hacia la
        cámara), y de ahí salía un +12,3 % en toda métrica en cm. El máximo de
        la cadena dentro de la repetición llega al 95,9 % y baja el sesgo medio
        contra la verdad 3-D de 1,04 cm a 0,49 cm. Ver `CONTRATO.md` §La escala
        y el informe del encargo 14.
        """
        if self._scale_px is None:
            chain = stature_chain_px(self.keypoints, self.fps)
            lo = max(0, min(int(self.frame_start), chain.size - 1))
            hi = max(lo, min(int(self.frame_end), chain.size - 1))
            w = chain[lo : hi + 1]
            if np.isfinite(w).any():
                self._scale_px = float(np.nanmax(w))
                self._scale_frame = lo + int(np.nanargmax(w))
            else:
                self._scale_px = float("nan")
        return None if not np.isfinite(self._scale_px) or self._scale_px <= 0 else self._scale_px

    def scale_detail(self) -> dict:
        """La escala de esta repetición, con el cuadro en que la cadena llegó a su
        máximo y cómo se obtuvo. Es el número que divide a toda métrica en cm: va
        a `quality.scale_px` para que se pueda auditar (CONTRATO.md §La escala)."""
        value = self.scale_px()
        if value is None:
            return {"value": None, "frame": None, "method": "sin_cadena_medible"}
        return {"value": round(value, 1), "frame": int(self._scale_frame), "method": "max_stature_chain_px"}

    def px_to_cm(self, px: float, frame: int) -> float | None:
        """Píxeles → cm con la escala de la repetición y la altura declarada.

        Si la cadena de la estatura no se pudo medir en ningún cuadro de la
        repetición (faltan rodillas o tobillos en todos), cae a la altura de
        cuerpo en px de `frame`, que es la escala anterior: sigue siendo un
        número, con su sesgo conocido, en vez de un `null`."""
        if self.athlete_height_m is None:
            return None
        scale = self.scale_px()
        if scale is None:
            bh = float(self.body_height_px[frame])
            if not np.isfinite(bh) or bh <= 0:
                return None
            scale = bh
        return float(px / scale * self.athlete_height_m * 100.0)


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
    # La comparación con `fps_min` vive en el registro, con su tolerancia (FPS_MIN_TOL).
    met = fps_min_met(metric, ctx.fps)
    base = {
        "unit": metric.unit,
        # Versión de ESTA métrica (CONTRATO.md §Versionado). Sin ella, mejorar
        # una métrica es invisible para quien lee un análisis: los siete números
        # en cm cambiaron con la escala del encargo 14 y nada lo avisaba.
        "metric_version": metric.metric_version,
        "view": ctx.view,
        "mdc": metric.mdc,
        "level": metric.level,
        "fps_min": metric.fps_min,
        "fps_min_met": met,
        "fps_provenance": ctx.fps_provenance,
        "judgment_allowed": judgment_allowed(metric, view=ctx.view, fps_real=ctx.fps, fps_provenance=ctx.fps_provenance),
        "confidence": None,
        "uncertainty": None,
    }
    if ctx.view not in metric.views:
        return {"value": None, **base, "judgment_allowed": False, "null_reason": f"vista {ctx.view} no válida para esta métrica (válidas: {', '.join(metric.views)})"}
    if not met:
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
            d0 = max(1, int(ctx.tolerances.get(e, 1)))
            for d in (-d0, d0):
                alts.append(float(metric.compute(ctx, {e: d})))
    except MetricNull as e:
        return {"value": None, **base, "judgment_allowed": False, "null_reason": str(e)}
    tol_max = max([1] + [int(ctx.tolerances.get(e, 1)) for e in metric.anchored_to])
    alts = [a for a in alts if np.isfinite(a)]
    if not alts or not np.isfinite(value):
        return {"value": None, **base, "judgment_allowed": False, "null_reason": "valor no finito (keypoints faltantes en los cuadros ancla)"}
    nd = 1 if metric.unit in ("ms", "cm") else 3
    return {
        "value": round(value, nd),
        **base,
        "confidence": _confidence(ctx, metric, joints),
        # La procedencia del fps va también en la frase que lee un humano: la
        # incertidumbre de ±1 cuadro se calcula sobre un eje de tiempo que, en un
        # camino declarado, es un supuesto (ADR-016).
        "uncertainty": {"low": round(min(alts), nd), "high": round(max(alts), nd), "method": f"±{tol_max} cuadro(s) en cada evento ancla a {ctx.fps:g} fps ({ctx.fps_provenance})"},
        "null_reason": None,
    }
