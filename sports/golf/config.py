"""Golf: lo mínimo que la ingesta necesita saber. Eventos y métricas llegan en
las Fases 2 y 3, con sus barridos en el arnés."""

from __future__ import annotations

from kinelab.sport import PerceptionGates, SportConfig, SportMetrics

from .events import GOLF_SPORT_EVENTS
from .metrics import JOINTS, REGISTRY

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
    # Chequeos de percepción (Fase 1). El umbral de encuadre son PÍXELES de
    # cuerpo, no fracción del cuadro: la fracción depende de la resolución y en
    # 4K un 28 % del alto son 1104 px, más que el 80 % de un 1080p (864 px).
    # 717 px es donde `head_lift_top_cm` —la métrica que manda, porque la cabeza
    # es el punto más ruidoso y su desplazamiento verdadero el más chico— cruza
    # su tolerancia de 5 cm con σ = 4,866 px. Le siguen `head_sway_top_cm` a 608
    # y `thorax_sway_top_cm` a 552. Procedencia: `estimacion` — sale del barrido
    # de tamaño de sujeto del arnés de NIVEL 0 (proyección más ruido gaussiano,
    # sin estimador de pose), informe del 15/9 §3, decidido el 16/9/2026. Se
    # revisa cuando haya σ por keypoint medido en material real.
    # Tasa de detección y una sola persona usan los defaults de CAPTURA.md.
    perception=PerceptionGates(body_height_px_min=717),
    # Eventos y segmentación (Fase 2): ver sports/golf/events.py.
    events=GOLF_SPORT_EVENTS,
    # Métricas de nivel 1 (Fase 3): ver sports/golf/metrics.py y sports/golf/mdc.yaml.
    metrics=SportMetrics(registry=REGISTRY, joints=JOINTS),
)
