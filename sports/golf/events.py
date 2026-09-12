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
from kinelab.events.primitives import Event, direction_change, make_event, peak_window, stable_window_end, stable_window_start, stillness_signal
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
    still_window_s: float = 0.5  # quietud mínima antes del takeaway para definir address
    follow_still_s: float = 0.3  # quietud mínima para cerrar el follow-through
    impact_search_s: float = 0.25  # ventana alrededor del pico de velocidad de las manos para el impacto
    refine_s: float = 0.15  # cuánto se camina refinando bordes de quietud
    still_smooth_s: float = 0.1  # mediana móvil sobre la velocidad para la prueba de quietud
    noise_factor: float = 2.5  # umbral efectivo de quietud = max(still_speed_max, noise_factor × piso de ruido del clip)
    provenance: str = "estimacion"
    note: str = "Elegidos sin material real; recalibrar con GolfDB (2.5) y con los clips de la Fase 0."


GOLF_PARAMS = GolfEventParams()
# Ventana de agudeza de 3 s: un swing es un movimiento continuo de ~2 s (backswing +
# downswing + follow); con ±1 s la ventana queda llena de movimiento y el pico
# parece "sostenido". Con ±3 s entra la quietud del address y del finish.
GOLF_SEGMENTATION = SegmentationParams(min_gap_s=2.0, prominence_floor=0.5, max_speed=15.0, sharpness_min=2.2, sharpness_window_s=3.0, lookback_s=2.0, lookahead_s=1.5)


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
    events: dict[str, Event | None] = {
        "address": make_event("address", address, fps, tol_frames=1, method="stable_window"),
        "top": make_event("top", top, fps, tol_frames=1, method="direction_change"),
        "impact": make_event("impact", impact, fps, tol_frames=1, method="peak_window"),
        "follow_end": None if follow is None else make_event("follow_end", settle_forward(spd, follow, refine), fps, tol_frames=2, method="stable_window"),
    }
    return events, None


GOLF_SPORT_EVENTS = SportEvents(definitions=GOLF_EVENTS, order=ORDER, segmentation=GOLF_SEGMENTATION, params=GOLF_PARAMS, detect=detect_golf_events, cutoff_hz_max=12.0)
