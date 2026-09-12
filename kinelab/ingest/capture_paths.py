"""Caminos de captura calibrados: `data/capture-paths.yaml`.

Un camino es dispositivo + modo + transferencia, con las dos tasas medidas con
cronómetro: la de captura (`fps_real`) y la de reproducción (`fps_playback`).
Es configuración, no inferencia (CONTEXTO.md, invariante 2). Un clip cuyo
camino no está acá se rechaza.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

# Diferencia relativa tolerada entre stretch_factor y fps_real / fps_playback.
_STRETCH_CONSISTENCY = 0.01


class CapturePath(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    device: str
    mode: Literal["video", "slomo"]
    nominal_fps: int = Field(gt=0)
    codec_expected: Literal["hevc", "h264"]
    transfer: str
    fps_real: float = Field(gt=0, description="tasa de CAPTURA, medida con cronómetro filmado")
    fps_playback: float = Field(gt=0, description="tasa a la que el archivo reproduce, medida de los PTS")
    stretch_factor: float = Field(gt=0, description="fps_real / fps_playback")
    fps_method: str
    calibrated_on: date
    calibrated_by: str
    notes: str = ""

    @model_validator(mode="after")
    def _stretch_is_consistent(self) -> "CapturePath":
        expected = self.fps_real / self.fps_playback
        if abs(expected - self.stretch_factor) / expected > _STRETCH_CONSISTENCY:
            raise ValueError(
                f"{self.id}: stretch_factor {self.stretch_factor} no coincide con "
                f"fps_real / fps_playback = {expected:.4f}"
            )
        return self


class CapturePaths(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    paths: list[CapturePath] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ids_are_unique(self) -> "CapturePaths":
        seen: set[str] = set()
        for p in self.paths:
            if p.id in seen:
                raise ValueError(f"camino de captura repetido: {p.id}")
            seen.add(p.id)
        return self

    def get(self, path_id: str) -> CapturePath | None:
        for p in self.paths:
            if p.id == path_id:
                return p
        return None


def load_capture_paths(path: str | Path) -> CapturePaths:
    text = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: el YAML tiene que ser un mapa con schema_version y paths")
    if data.get("paths") is None:
        data["paths"] = []
    return CapturePaths.model_validate(data)
