"""Eventos del swing de golf: las ocho definiciones de GolfDB como datos, y los
cuatro que v1 detecta compuestos con primitivas del motor (ADR-008).

Los parámetros numéricos se eligieron SIN material real (procedencia
`estimacion`): se recalibran con GolfDB (ESPECIFICACION 2.5) y con los clips de
la Fase 0. Ninguno se esconde en una constante suelta.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from kinelab.events.onset import onset_backtrack, settle_forward
from kinelab.events.primitives import Event, direction_change, make_event, peak_window, stable_window_end, stable_window_start, still_run_start, stillness_signal, subframe_crossing
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
    EventDef("top", "Top", "The moment the club changes direction", "El instante en que el palo cambia de dirección", "direction_change"),
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
    provenance: str = "estimacion"
    note: str = "Elegidos sin material real; recalibrar con GolfDB (2.5) y con los clips de la Fase 0."


GOLF_PARAMS = GolfEventParams()

# El instante sub-cuadro del impacto se estima proyectando la trayectoria de las manos
# sobre su dirección de viaje: desde `down_the_line` esa dirección apunta al objetivo,
# casi sobre el eje óptico, y en la imagen queda escorzada (invariante 6).
IMPACT_SUBFRAME_VIEWS = ("face_on",)
# Ventana de agudeza de 3 s: un swing es un movimiento continuo de ~2 s (backswing +
# downswing + follow); con ±1 s la ventana queda llena de movimiento y el pico
# parece "sostenido". Con ±3 s entra la quietud del address y del finish.
GOLF_SEGMENTATION = SegmentationParams(min_gap_s=2.0, prominence_floor=0.5, max_speed=15.0, sharpness_min=2.2, sharpness_window_s=3.0, lookback_s=2.0, lookahead_s=1.5)


def _impact_subframe(sig, address: int, impact: int, still: np.ndarray, thr: float, params: GolfEventParams) -> dict:
    """El instante en que las manos pasan por su posición de address, entre dos cuadros.

    El cuadro entero del impacto NO cambia: sigue siendo el de mínima distancia a la
    posición de address (`peak_window`). Esto lo refina hacia adentro del cuadro.

    La señal es la trayectoria CRUDA del centro de las dos muñecas (huecos ≤ 5 cuadros
    rellenados, sin filtrar) proyectada sobre su dirección de viaje alrededor del
    impacto; el nivel es la misma proyección en el cuadro de address. El cero de esa
    señal es el instante de máximo acercamiento a la posición de address: la versión
    continua del criterio del cuadro entero. La proyección usa las dos coordenadas de
    imagen, así que el signo de `y` cambia el resultado (invariante 15).

    Sin MDC medido: es descriptivo, no juicio (ADR-007). Procedencia `estimacion`.
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
    noise_px = None
    start = still_run_start(still, max_speed=thr, end=address)
    seg = x[start : address + 1]
    seg = seg[np.isfinite(seg)]
    if seg.size >= 3:
        t = np.arange(seg.size, dtype=float)
        noise_px = float(np.std(seg - np.polyval(np.polyfit(t, seg, 1), t), ddof=1))
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
    top = direction_change(proj, before=impact, after=address)
    if top is None:
        return {}, "sin_top"
    follow = stable_window_start(still, fps, max_speed=thr, min_duration_s=params.follow_still_s, after=impact)
    impact_ev = make_event("impact", impact, fps, tol_frames=1, method="peak_window")
    impact_ev.subframe = _impact_subframe(sig, address, impact, still, thr, params)
    events: dict[str, Event | None] = {
        "address": make_event("address", address, fps, tol_frames=1, method="stable_window"),
        "top": make_event("top", top, fps, tol_frames=1, method="direction_change"),
        "impact": impact_ev,
        "follow_end": None if follow is None else make_event("follow_end", settle_forward(spd, follow, refine), fps, tol_frames=2, method="stable_window"),
    }
    return events, None


GOLF_SPORT_EVENTS = SportEvents(definitions=GOLF_EVENTS, order=ORDER, segmentation=GOLF_SEGMENTATION, params=GOLF_PARAMS, detect=detect_golf_events, cutoff_hz_max=12.0)
