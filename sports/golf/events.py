"""Eventos del swing de golf: las ocho definiciones de GolfDB como datos, y los
cuatro que v1 detecta compuestos con primitivas del motor (ADR-008).

Los parámetros numéricos se eligieron SIN material real (procedencia
`estimacion`): se recalibran con GolfDB (ESPECIFICACION 2.5) y con los clips de
la Fase 0. Ninguno se esconde en una constante suelta.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

from kinelab.events.onset import onset_backtrack, settle_forward
from kinelab.events.primitives import Event, direction_change_farthest_band, make_event, peak_window, stable_window_end, stable_window_start, still_noise_px, still_run_start, stillness_signal, subframe_crossing
from kinelab.events.segmentation import RepCandidate, SegmentationParams
from kinelab.events.signal import principal_axis
from kinelab.sport import SportEvents


@dataclass(frozen=True)
class EventDef:
    id: str
    name_es: str
    definition_en: str
    definition_es: str
    detector: str | None  # None = no se detecta en v1
    tol_frames: int = 1
    definition_source: str = "GolfDB (McNally et al., 2019), transcripción sin verificar"


GOLF_EVENTS: tuple[EventDef, ...] = (
    EventDef("address", "Address", "The moment just before the takeaway begins", "El instante previo al inicio del takeaway", "stable_window"),
    EventDef("toe_up", "Toe-up", "Shaft parallel to the ground during backswing", "Shaft paralelo al suelo en el backswing", None),
    EventDef("mid_backswing", "Mid-backswing", "Arm parallel to the ground during backswing", "Brazo paralelo al suelo en el backswing", None),
    EventDef("top", "Top", "The moment the club changes direction", "El instante en que el palo cambia de dirección", "direction_change_farthest"),
    EventDef("mid_downswing", "Mid-downswing", "Arm parallel to the ground during downswing", "Brazo paralelo al suelo en el downswing", None),
    EventDef("impact", "Impact", "The moment the club head contacts the ball", "El instante en que la cabeza del palo toca la pelota", "peak_window"),
    EventDef("mid_follow_through", "Mid-follow-through", "Shaft parallel to the ground during follow-through", "Shaft paralelo al suelo en el follow-through", None),
    EventDef("finish", "Finish", "Just before the golfer relaxes their final pose", "Justo antes de que el golfista relaje la pose final", "stable_window", tol_frames=2),
)

ORDER = ("address", "top", "impact", "follow_end")


@dataclass(frozen=True)
class GolfEventParams:
    still_speed_max: float = 0.15  # alturas de cuerpo / s: por debajo, quietud
    still_window_s: float = 0.3  # quietud mínima antes del takeaway para definir address (0,5 dejaba afuera un clip real que arranca ya en address; el waggle queda por ver)
    follow_still_s: float = 0.3  # quietud mínima para cerrar el follow-through
    impact_search_s: float = 0.25  # ventana alrededor del pico de velocidad de las manos para el impacto
    refine_s: float = 0.15  # cuánto se camina refinando bordes de quietud
    still_smooth_s: float = 0.1  # mediana móvil sobre la velocidad para la prueba de quietud
    noise_factor: float = 2.5  # umbral efectivo de quietud = max(still_speed_max, noise_factor × piso de ruido del clip [p10])
    subframe_window_s: float = 0.1  # ventana alrededor del impacto donde se busca el cruce sub-cuadro (≥ 2 cuadros)
    subframe_axis_s: float = 0.1  # tramo alrededor del impacto del que sale la dirección de viaje de las manos (≥ 1 cuadro)
    wrist_score_min: float = 0.55  # score por debajo del cual una muñeca no entra al centro de manos (ver abajo)
    top_band_sigmas: float = 2.0  # dos candidatos a top separados por menos de N σ_px de excursión no se distinguen
    provenance: str = "estimacion"
    note: str = "Elegidos sin material real; recalibrar con GolfDB (2.5) y con los clips de la Fase 0."


GOLF_PARAMS = GolfEventParams()

# `wrist_score_min`, medido (informe del encargo 15, ADR-017 §"Lo que la regla no
# arregla", y el barrido del 18). La señal de los tres eventos es el centro de las dos
# muñecas, y en los dos clips del 7/9 el modelo pierde la muñeca izquierda **justo en el
# top**: en `cortado.mp4` los scores de la izquierda en los cuadros 32–38 son 0,35 ·
# 0,36 · 0,40 · 0,40 · 0,43 · 0,51 · 0,39 y la x salta hasta 300 px entre cuadros,
# mientras la derecha va suave y no baja de 0,565 en todo el clip.
#
# El número NO sale de mirar esa lista: sale de barrer el umbral de 0,00 a 0,65 sobre
# los cinco clips reales y el mocap, y de un criterio que no mira el resultado —**el
# mayor umbral con el que en ningún cuadro se caen las DOS muñecas**—. Hasta 0,55 no hay
# ni un cuadro sin muñeca en ningún clip; en 0,60 aparecen 1 y 2 cuadros sueltos; en
# 0,65 `vid1.mp4` se queda con una racha de 5 y el top se va a 570. Procedencia
# `estimacion` (cinco clips de un golfista no son una tabla); se recalibra con GolfDB,
# igual que el resto de `GolfEventParams`.
#
# El MDC del instante sub-cuadro del impacto lo mide el arnés y vive en `mdc.yaml`
# §events.impact.subframe (encargo 13, 16 semillas por condición): NO se escribe a mano
# acá, igual que los MDC de las métricas (ESPECIFICACION 3.3).
MDC_TABLE = Path(__file__).with_name("mdc.yaml")


@lru_cache(maxsize=1)
def _subframe_mdc() -> dict | None:
    """El MDC del instante sub-cuadro del impacto, leído de `mdc.yaml`.

    `None` si la tabla no está o no tiene la fila: sin MDC medido no hay juicio
    (ADR-007), y el hueco se ve antes que un número inventado (invariante 12). Ojo
    con eso: si una corrida del arnés dejara de escribir la sección, el campo pasaría
    a `null` sin que nada avise, que es la misma trampa que el 13 documentó con las
    métricas muertas. Hay un test que lo agarra.

    Cacheado: la tabla es un archivo de configuración que no cambia mientras el motor
    corre, y si no, se leería una vez por repetición.
    """
    if not MDC_TABLE.is_file():
        return None
    table = yaml.safe_load(MDC_TABLE.read_text(encoding="utf-8")) or {}
    row = (((table.get("events") or {}).get("impact") or {}).get("subframe") or {})
    value = row.get("mdc_ms")
    if not value or float(value) <= 0:
        return None
    return {
        "value": round(float(value), 3),
        "unit": str(row.get("unit") or "ms"),
        # El MDC sale del arnés; el VALOR del sub-cuadro sigue siendo `estimacion`.
        # `medido_aqui` es de dónde sale el número y es literalmente cierto —lo
        # midió el arnés, acá—, y además el schema de `subframe.mdc` no admite
        # campos nuevos. Lo que **no** es, y lo dice el `source`, es un MDC
        # validado en material real (ADR-019): el arnés nivel 0 proyecta puntos y
        # les suma ruido, sin estimador de pose, con una cámara sin verificar.
        "provenance": "medido_aqui",
        "source": "sports/golf/mdc.yaml §events.impact.subframe (arnés nivel 0: proyección y ruido, sin estimador, cámara iphone17pro-1080p120 sin verificar, 16 semillas) · NO validado en material real (ADR-019)",
    }


# El instante sub-cuadro del impacto se estima proyectando la trayectoria de las manos
# sobre su dirección de viaje: desde `down_the_line` esa dirección apunta al objetivo,
# casi sobre el eje óptico, y en la imagen queda escorzada (invariante 6).
IMPACT_SUBFRAME_VIEWS = ("face_on",)
# Ventana de agudeza de 3 s: un swing es un movimiento continuo de ~2 s (backswing +
# downswing + follow); con ±1 s la ventana queda llena de movimiento y el pico
# parece "sostenido". Con ±3 s entra la quietud del address y del finish.
GOLF_SEGMENTATION = SegmentationParams(min_gap_s=2.0, prominence_floor=0.5, max_speed=15.0, sharpness_min=2.2, sharpness_window_s=3.0, lookback_s=2.0, lookahead_s=1.5)


def _hands_noise_px(sig, still_start: int, address: int) -> float | None:
    """Ruido por cuadro del centro de manos, en px, medido en la quietud del address.

    σ por eje de imagen sobre la señal **cruda** (la misma que mira el sub-cuadro),
    combinados en cuadratura: `√((σx² + σy²) / 2)`, o sea el σ de una coordenada si el
    ruido es isótropo. Se mide sobre la cruda y no sobre la filtrada aunque la excursión
    del top salga de la filtrada: el pasabajos baja el ruido y usar el número de la
    filtrada daría una banda más angosta de lo que la señal justifica. Ante la duda, la
    banda ancha.

    `None` si la racha de quietud no da tres cuadros finitos: sin ruido medido no hay
    banda, y el top sale con su `tol_frames` de 1 como siempre.
    """
    P = np.asarray(sig.hands_raw, dtype=float)
    parts = [still_noise_px(P[:, k], start=still_start, end=address) for k in (0, 1)]
    ok = [v for v in parts if v is not None and np.isfinite(v)]
    if not ok:
        return None
    return float(np.sqrt(sum(v * v for v in ok) / len(ok)))


def _impact_subframe(sig, address: int, impact: int, still_start: int, params: GolfEventParams) -> dict:
    """El instante en que las manos pasan por su posición de address, entre dos cuadros.

    El cuadro entero del impacto NO cambia: sigue siendo el de mínima distancia a la
    posición de address (`peak_window`). Esto lo refina hacia adentro del cuadro.

    La señal es la trayectoria CRUDA del centro de las dos muñecas (huecos ≤ 5 cuadros
    rellenados, sin filtrar) proyectada sobre su dirección de viaje alrededor del
    impacto; el nivel es la misma proyección en el cuadro de address. El cero de esa
    señal es el instante de máximo acercamiento a la posición de address: la versión
    continua del criterio del cuadro entero. La proyección usa las dos coordenadas de
    imagen, así que el signo de `y` cambia el resultado (invariante 15).

    El VALOR es `estimacion`; su **MDC sí está medido** y viaja al lado en `mdc`, con
    procedencia `medido_aqui` y la sección de `mdc.yaml` de donde salió. Con MDC medido
    el número deja de ser sólo descriptivo por falta de tabla; lo que hoy lo deja fuera
    de todo juicio es la procedencia del fps (ADR-016), no la falta de MDC.
    """
    fps = sig.fps
    out: dict = {
        "frame_before": None, "frame_after": None, "fraction": None, "t_sub_s": None,
        "uncertainty_frames": None, "uncertainty_s": None,
        "components": {"curvature_frames": None, "noise_frames": None, "noise_px": None, "slope_px_per_frame": None},
        "method": "hands_cross_address_linear_interp",
        "signal": "centro de las dos muñecas (crudo, huecos rellenados) proyectado sobre su dirección de viaje en el impacto",
        "views": list(IMPACT_SUBFRAME_VIEWS),
        "provenance": "estimacion",
        "mdc": _subframe_mdc(),
        "null_reason": None,
    }
    view = getattr(sig, "view", None)
    if view is not None and view not in IMPACT_SUBFRAME_VIEWS:
        out["null_reason"] = f"vista {view} no válida para el instante sub-cuadro (válidas: {', '.join(IMPACT_SUBFRAME_VIEWS)})"
        return out
    P = np.asarray(sig.hands_raw, dtype=float)
    k = max(1, int(round(params.subframe_axis_s * fps)))
    lo, hi = max(0, impact - k), min(P.shape[0] - 1, impact + k)
    axis = principal_axis(P, lo, hi)
    net = P[hi] - P[lo]
    if np.isfinite(net).all() and float(net @ axis) < 0:
        axis = -axis
    x = np.where(np.isfinite(P).all(axis=1), P @ axis, np.nan)
    level = float(P[address] @ axis) if np.isfinite(P[address]).all() else np.nan
    # Ruido por cuadro de la señal: σ de los residuos de la recta ajustada a la racha de
    # quietud del address (una deriva lenta del jugador es movimiento, no ruido).
    noise_px = still_noise_px(x, start=still_start, end=address)
    r = max(2, int(round(params.subframe_window_s * fps)))
    c = subframe_crossing(x, level, near=impact, lo=impact - r, hi=impact + r, noise_sigma=noise_px)
    out["components"]["noise_px"] = None if noise_px is None else round(noise_px, 3)
    out["components"]["slope_px_per_frame"] = c.slope
    out["components"]["curvature_frames"] = c.curvature_frames
    out["components"]["noise_frames"] = c.noise_frames
    if c.null_reason is not None or c.fraction is None:
        out["null_reason"] = c.null_reason
        return out
    out["frame_before"], out["frame_after"], out["fraction"] = c.frame_before, c.frame_after, c.fraction
    # Seis decimales (microsegundos): a 240 fps una banda de 0,001 cuadros son 4 µs, y
    # con cinco decimales el JSON la mostraría como 0,0.
    out["t_sub_s"] = round((c.frame_before + c.fraction) / fps, 6)
    out["uncertainty_frames"] = c.uncertainty_frames
    out["uncertainty_s"] = None if c.uncertainty_frames is None else round(c.uncertainty_frames / fps, 6)
    return out


def detect_golf_events(sig, cand: RepCandidate, params: GolfEventParams = GOLF_PARAMS) -> tuple[dict[str, Event | None], str | None]:
    """Address (definido), Top, Impact y fin del follow-through para un candidato.
    Devuelve `(eventos, None)` o `({}, razón)` si la repetición no califica."""
    fps, spd, hands = sig.fps, sig.speed, sig.hands
    refine = max(1, int(round(params.refine_s * fps)))
    still = stillness_signal(spd, fps, params.still_smooth_s)
    thr = max(params.still_speed_max, params.noise_factor * float(getattr(sig, "noise_floor_bh_s", 0.0) or 0.0))
    end_still = stable_window_end(still, fps, max_speed=thr, min_duration_s=params.still_window_s, before=cand.peak)
    if end_still is None:
        return {}, "sin_address"
    address = onset_backtrack(spd, end_still, refine)
    dist = np.hypot(*(hands - hands[address]).T)
    impact = peak_window(dist, peak=cand.peak, radius=max(1, int(round(params.impact_search_s * fps))))
    if impact <= address + 2:
        return {}, "sin_downswing"
    axis = principal_axis(hands, address, impact)
    proj = np.where(np.isfinite(hands).all(axis=1), hands @ axis, np.nan)
    # ADR-017: de los cambios de sentido de las manos entre address e impacto, el
    # top es aquel en que están MÁS LEJOS de su posición de address —la misma
    # distancia en el plano de imagen con la que se elige el impacto, ahí como
    # mínimo—, no el último. El último, desde `down_the_line`, es el fondo del arco
    # justo antes del impacto.
    #
    # La banda: cuando otro candidato queda a menos de `top_band_sigmas` veces el
    # ruido del clip, la ventaja del ganador no se distingue del ruido y el evento
    # sale con `tol_frames` igual a la distancia en cuadros hasta ese rival, que las
    # métricas ancladas al top propagan (invariante 8). Medido en `vid1.mp4`, el
    # único de los cinco clips reales que la enciende: los candidatos están a 590,9 /
    # 588,5 / 587,7 px del address —el ganador se lleva el top por 2,2 px sobre uno y
    # 3,2 px sobre el otro— con 4,70 px de ruido por cuadro. Antes salía con
    # `tol_frames` 1, como si no hubiera duda; ahora sale con 4.
    still_start = still_run_start(still, max_speed=thr, end=address)
    sigma_px = _hands_noise_px(sig, still_start, address)
    margin = None if sigma_px is None else params.top_band_sigmas * sigma_px
    top = direction_change_farthest_band(proj, dist, before=impact, after=address, margin=margin)
    if top.frame is None:
        return {}, "sin_top"
    follow = stable_window_start(still, fps, max_speed=thr, min_duration_s=params.follow_still_s, after=impact)
    impact_ev = make_event("impact", impact, fps, tol_frames=1, method="peak_window")
    impact_ev.subframe = _impact_subframe(sig, address, impact, still_start, params)
    events: dict[str, Event | None] = {
        "address": make_event("address", address, fps, tol_frames=1, method="stable_window"),
        "top": make_event("top", top.frame, fps, tol_frames=top.tol_frames, method="direction_change_farthest"),
        "impact": impact_ev,
        "follow_end": None if follow is None else make_event("follow_end", settle_forward(spd, follow, refine), fps, tol_frames=2, method="stable_window"),
    }
    return events, None


GOLF_SPORT_EVENTS = SportEvents(definitions=GOLF_EVENTS, order=ORDER, segmentation=GOLF_SEGMENTATION, params=GOLF_PARAMS, detect=detect_golf_events, cutoff_hz_max=12.0)
