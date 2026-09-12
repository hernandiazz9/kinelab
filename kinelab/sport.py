"""La interfaz que el motor le pide a una config de deporte.

El motor define la forma; `sports/<deporte>/` la instancia. El motor nunca
importa `sports` (CONTEXTO.md, invariante 13): recibe un `SportConfig` ya
armado desde el punto de entrada que corresponda.
"""

from __future__ import annotations

from dataclasses import dataclass


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

    def __post_init__(self) -> None:
        if not self.gestures:
            raise ValueError(f"{self.id}: sin gestos")
        if not self.views:
            raise ValueError(f"{self.id}: sin vistas")
        if self.fps_min <= 0:
            raise ValueError(f"{self.id}: fps_min tiene que ser positivo")
