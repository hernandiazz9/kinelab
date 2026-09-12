"""Golf: lo mínimo que la ingesta necesita saber. Eventos y métricas llegan en
las Fases 2 y 3, con sus barridos en el arnés."""

from __future__ import annotations

from kinelab.sport import PerceptionGates, SportConfig

GOLF = SportConfig(
    id="golf",
    # Tres gestos para empezar; se agregan cuando haya material de cada uno.
    gestures=("driver", "iron", "wedge"),
    # Las dos vistas estándar de enseñanza. Cada métrica declarará desde cuál
    # es válida (CAPTURA.md §Encuadre).
    views=("face_on", "down_the_line"),
    # Por debajo de 100 fps de captura, los tiempos del swing no se miden: el
    # downswing dura 233–296 ms y la tolerancia por evento es ±1 cuadro.
    fps_min=100,
    # Chequeos de percepción (Fase 1). El umbral de encuadre
    # (`body_height_frac_min`) se fija MIDIENDO sobre los clips de la Fase 0
    # (ESPECIFICACION 1.3), no a mano: hasta entonces queda en `None` = no
    # evaluado, y el chequeo `body_height_frac` se reporta sin veredicto.
    # Tasa de detección y una sola persona usan los defaults de CAPTURA.md.
    perception=PerceptionGates(),
)
