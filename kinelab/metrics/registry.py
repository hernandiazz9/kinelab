"""Registro declarativo de métricas (CONTRATO.md §El registro de métricas).

Cada métrica es un objeto que el motor puede inspeccionar antes de calcular:
unidad, nivel, vistas válidas, fps mínimo, a qué eventos se ancla, referencia
con procedencia y MDC. `judgment_allowed` se deriva en código, nunca a mano.
En la Fase 2 el registro está vacío a propósito: las métricas entran en la
Fase 3, una por una, con su barrido en el arnés.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

PROVENANCES = ("medido_aqui", "pares", "fabricante", "estimacion", "sin_verificar")

# Si el MDC de la métrica está validado en MATERIAL REAL (ADR-019). Es una
# pregunta distinta de la procedencia: `PROVENANCES` dice **de dónde sale** un
# número —y el MDC del arnés es `medido_aqui`, lo medimos nosotros—, esto dice
# **contra qué se validó**. Un MDC del arnés, de cualquier nivel y aunque los
# intrínsecos estén calibrados, es `sin_validar`: el arnés proyecta puntos y les
# suma ruido, sin estimador de pose en el medio. `material_real` exige las siete
# cosas juntas —estimador real, material real, el camino de captura de la toma,
# eventos contra etiquetas humanas, deriva medida, escala trazable e intrínsecos
# con tablero— y hoy no lo declara ninguna métrica.
MDC_VALIDATIONS = ("sin_validar", "material_real")

# Las procedencias que NO alcanzan para juzgar contra un rango (ADR-019, que
# lleva al código la invariante 12: ante la duda, el hueco antes que el número
# inventado). `estimacion` es un número que nos inventamos nosotros y
# `sin_verificar` es uno que nadie miró.
WEAK_PROVENANCES = ("estimacion", "sin_verificar")
_SLUG = re.compile(r"^[a-z][a-z0-9_]*$")

# Tolerancia de la comparación `fps_real >= fps_min`, en un solo lugar.
# El arnés barre en fps NOMINALES enteros (240, 120, 60, 30) y escribe esa tabla
# en `mdc.yaml`; las tasas de video reales son NTSC (239,76 · 119,88 · 59,94 ·
# 29,97) y un teléfono entrega además su propio redondeo (29,998 medido en el
# Galaxy S22 Ultra). Sin tolerancia, todo clip real de 30 fps pierde las
# métricas de `fps_min: 30` por milésimas. 0,5 % cubre el hueco NTSC (0,1 %) con
# margen y no alcanza para colar un clip de la tasa de abajo (29,8 contra 30 no
# pasa). Ver CONTRATO.md §El sextuplo de toda métrica.
FPS_MIN_TOL = 0.005


@dataclass(frozen=True)
class Reference:
    kind: str  # "descriptive" | "range"
    provenance: str  # uno de PROVENANCES
    source: str
    definition: str
    range: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        if self.kind not in ("descriptive", "range"):
            raise ValueError(f"kind tiene que ser 'descriptive' o 'range': {self.kind!r}")
        if self.provenance not in PROVENANCES:
            raise ValueError(f"procedencia desconocida {self.provenance!r}; válidas: {PROVENANCES}")
        if self.kind == "range":
            if self.range is None or len(self.range) != 2 or not (self.range[0] < self.range[1]):
                raise ValueError("una referencia 'range' necesita range=(low, high) con low < high")

    @property
    def range_width(self) -> float | None:
        return None if self.range is None else float(self.range[1] - self.range[0])


@dataclass(frozen=True)
class Metric:
    id: str
    unit: str
    level: int
    views: tuple[str, ...]
    fps_min: float
    anchored_to: tuple[str, ...]
    reference_frame: str
    compute: Callable[..., Any] | None = None
    confidence: Callable[..., Any] | None = None
    reference: Reference | None = None
    mdc: float | None = None
    # ADR-019. Default conservador: una métrica que no dice nada no es juicio.
    mdc_validation: str = "sin_validar"
    metric_version: str = "1.0.0"

    def __post_init__(self) -> None:
        if not _SLUG.match(self.id):
            raise ValueError(f"id de métrica inválido: {self.id!r}")
        if self.level not in (1, 2):
            raise ValueError(f"{self.id}: nivel {self.level} no existe en el registro; el nivel 3 no se construye (ADR-007)")
        if not self.views:
            raise ValueError(f"{self.id}: una métrica declara al menos una vista válida")
        if self.fps_min <= 0:
            raise ValueError(f"{self.id}: fps_min tiene que ser positivo")
        if self.mdc is not None and self.mdc <= 0:
            raise ValueError(f"{self.id}: el MDC tiene que ser positivo")
        if self.mdc_validation not in MDC_VALIDATIONS:
            raise ValueError(f"{self.id}: mdc_validation {self.mdc_validation!r} no existe; válidas: {MDC_VALIDATIONS} (ADR-019)")


def fps_min_met(metric: Metric, fps_real: float) -> bool:
    """`fps_real >= fps_min · (1 − FPS_MIN_TOL)`. El único lugar donde se compara
    la tasa de la toma contra el mínimo de la métrica: lo usan `judgment_allowed`,
    `null_metric` y `metrics.core.evaluate`."""
    return fps_real >= metric.fps_min * (1.0 - FPS_MIN_TOL)


def judgment_allowed(metric: Metric, *, view: str, fps_real: float, fps_provenance: str) -> bool:
    """La regla del MDC, tal cual CONTRATO.md §El sextuplo; nunca se escribe a mano.

    `fps_provenance` es de dónde sale el `fps_real` de la toma: sólo
    `medido_aqui` —cronómetro filmado en un camino calibrado— habilita juicio.
    Con un camino declarado (`sin_verificar`, ADR-016) el número se muestra,
    pero no se compara contra nada: el eje del tiempo es un supuesto.

    Las dos últimas condiciones son ADR-019 y son **independientes**: una mira
    el instrumento (¿el MDC se validó contra material real?) y la otra mira
    contra qué se compara (¿hay un rango, y de dónde salió?). Cualquiera de las
    dos alcanza para que no haya juicio."""
    ref = metric.reference
    return (
        metric.level == 1
        and metric.mdc is not None
        and fps_min_met(metric, fps_real)
        and fps_provenance == "medido_aqui"
        and view in metric.views
        # ADR-019 (a): el MDC de `mdc.yaml` lo mide el arnés proyectando puntos y
        # sumándoles ruido, sin estimador de pose y con una cámara que no es la
        # que filmó. Que el MDC **exista** no dice que describa a este camino de
        # captura: eso se mide sobre material real, y hasta entonces el número se
        # muestra con su banda pero no se compara.
        and metric.mdc_validation == "material_real"
        # ADR-019 (b): juicio es COMPARAR CONTRA UN RANGO (CONTEXTO.md
        # §Vocabulario). Sin rango no hay contra qué juzgar, y un rango de
        # procedencia `estimacion` o `sin_verificar` es el número inventado que
        # prohíbe la invariante 12. La forma del rango ya la garantizó
        # `Reference.__post_init__`.
        and ref is not None
        and ref.kind == "range"
        and ref.provenance not in WEAK_PROVENANCES
        # ADR-007, que sigue en pie: un MDC más ancho que el rango no distingue
        # un extremo del otro. Con `kind == "range"` el ancho siempre existe.
        and metric.mdc <= ref.range_width
    )


def null_metric(metric: Metric, reason: str, *, view: str, fps_real: float, fps_provenance: str = "sin_verificar") -> dict:
    """El sextuplo con `value: null` y su razón (CONTRATO.md: un null nunca se omite)."""
    return {
        "value": None,
        "unit": metric.unit,
        "metric_version": metric.metric_version,
        "confidence": None,
        "uncertainty": None,
        "view": view,
        "mdc": metric.mdc,
        "level": metric.level,
        "fps_min": metric.fps_min,
        "fps_min_met": fps_min_met(metric, fps_real),
        "fps_provenance": fps_provenance,
        "judgment_allowed": False,
        "null_reason": reason,
    }


class Registry:
    def __init__(self, version: str, *, mdc_note: str | None = None) -> None:
        self.version = version
        # Una frase legible por el entrenador que dice de dónde salen los MDC de
        # ESTE registro (ADR-019). La escribe el deporte, que es el que tiene la
        # tabla; el motor sólo la transcribe a `warnings[]` y no sabe qué dice
        # (invariante 13). `None` = el registro no declara nada y no hay aviso.
        self.mdc_note = mdc_note
        self._metrics: dict[str, Metric] = {}

    def register(self, metric: Metric) -> Metric:
        if metric.id in self._metrics:
            raise ValueError(f"métrica repetida: {metric.id}")
        self._metrics[metric.id] = metric
        return metric

    def get(self, metric_id: str) -> Metric:
        return self._metrics[metric_id]

    def ids(self) -> list[str]:
        return list(self._metrics)

    def __len__(self) -> int:
        return len(self._metrics)

    def __iter__(self):
        return iter(self._metrics.values())


# Vacío hasta la Fase 3: cada métrica entra con sus seis cosas (AGENTS.md).
REGISTRY = Registry(version="0.1.0")
