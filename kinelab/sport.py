"""La interfaz que el motor le pide a una config de deporte.

El motor define la forma; `sports/<deporte>/` la instancia. El motor nunca
importa `sports` (CONTEXTO.md, invariante 13): recibe un `SportConfig` ya
armado desde el punto de entrada que corresponda.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class PerceptionGates:
    """Umbrales de los chequeos de la Fase 1 (encuadre, detección, un sujeto).

    Viven en la config del deporte y llegan a `kinelab.perception.framing` por
    parámetro: el motor no conoce ningún umbral de ningún deporte.

    - `body_height_px_min`: mínimo de `body_height_px`, la altura del cuerpo en
      PÍXELES, no la fracción del cuadro. La fracción engaña porque depende de
      la resolución: en 4K un 28 % del alto son 1104 px, más que el 80 % de un
      1080p (864 px). Lo que decide el error de una métrica es el píxel
      (informe del 13, §3). `None` = no evaluado todavía: el umbral se fija
      MIDIENDO (ESPECIFICACION 1.3), nunca a mano; mientras sea `None`, el
      chequeo `body_height_px` se reporta con `passed=None` y su razón.
      (Ojo: `FramingReport.body_height_px_min` es otra cosa —el mínimo
      observado en el clip—; esto es el umbral que pide el deporte.)
    - `detection_rate_min`: fracción mínima de cuadros con el sujeto detectado
      (CAPTURA.md §El gate: 0,90).
    - `multi_subject_frac_max`: fracción máxima de cuadros con más de un
      candidato válido antes de declarar que hay más de una persona en cuadro.
    """

    body_height_px_min: float | None = None
    detection_rate_min: float = 0.90
    multi_subject_frac_max: float = 0.10

    def __post_init__(self) -> None:
        if self.body_height_px_min is not None and not self.body_height_px_min > 0.0:
            raise ValueError(f"body_height_px_min tiene que ser positivo: {self.body_height_px_min}")
        if not (0.0 <= self.detection_rate_min <= 1.0):
            raise ValueError(f"detection_rate_min fuera de [0, 1]: {self.detection_rate_min}")
        if not (0.0 <= self.multi_subject_frac_max <= 1.0):
            raise ValueError(f"multi_subject_frac_max fuera de [0, 1]: {self.multi_subject_frac_max}")


@dataclass(frozen=True)
class SportEvents:
    """Lo que el motor necesita de un deporte para segmentar y detectar eventos
    (Fase 2). Las definiciones, los parámetros y el detector son del deporte;
    el motor sólo los invoca."""

    definitions: tuple[Any, ...]  # EventDef del deporte, con su definición textual
    order: tuple[str, ...]  # ids de los eventos detectados, en orden temporal
    segmentation: Any  # kinelab.events.segmentation.SegmentationParams
    params: Any  # dataclass con los parámetros del detector (se guarda en analysis.json)
    # (SwingSignals, RepCandidate) -> (dict[id, Event | None], razón de descarte | None)
    detect: Callable[[Any, Any], tuple[dict[str, Any], str | None]]
    cutoff_hz_max: float = 12.0


@dataclass(frozen=True)
class SportMetrics:
    """Lo que el motor necesita para calcular las métricas de un deporte (Fase 3)."""

    registry: Any  # kinelab.metrics.registry.Registry con las métricas del deporte
    joints: dict[str, tuple[int, ...]]  # keypoints involucrados por métrica (para la confianza)


@dataclass(frozen=True)
class SportConfig:
    id: str
    # Gestos que se pueden declarar en la ingesta. Cada uno tendrá, en la Fase 2,
    # sus eventos y sus métricas permitidas por vista.
    gestures: tuple[str, ...]
    # Vistas con nombre. Cada métrica declara desde cuáles es válida.
    views: tuple[str, ...]
    # Tasa de captura mínima para que la capa temporal exista. Por debajo, el
    # gate rechaza la sesión: no se calcula nada "a medias" (invariante 7).
    fps_min: int
    # Umbrales de los chequeos de percepción (Fase 1). Con default para que una
    # config de la Fase 0 (id, gestures, views, fps_min) siga construyendo.
    perception: PerceptionGates = field(default_factory=PerceptionGates)
    # Eventos y segmentación (Fase 2). None = el deporte todavía no los define.
    events: SportEvents | None = None
    # Métricas (Fase 3). None = sin métricas todavía.
    metrics: SportMetrics | None = None

    def __post_init__(self) -> None:
        if not self.gestures:
            raise ValueError(f"{self.id}: sin gestos")
        if not self.views:
            raise ValueError(f"{self.id}: sin vistas")
        if self.fps_min <= 0:
            raise ValueError(f"{self.id}: fps_min tiene que ser positivo")
