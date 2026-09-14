"""Caminos de captura: `data/capture-paths.yaml`.

Un camino es dispositivo + modo + transferencia. Es configuración, no
inferencia (CONTEXTO.md, invariante 2). Hay dos clases:

- **calibrado** (`calibrated: true`): las dos tasas salen de un cronómetro
  filmado — la de captura (`fps_real`) y la de reproducción (`fps_playback`) —
  y su cociente es el `stretch_factor`. Es el único que habilita juicio.
- **declarado** (`calibrated: false`, ADR-016): dispositivo y modo los declara
  el usuario, sin cronómetro. Los seis campos de la calibración van en `null`;
  el fps de captura se **asume** igual al de reproducción efectiva del archivo
  (`stretch_factor` 1,0) con procedencia `sin_verificar`. Sólo `mode: video`
  tiene sentido: en un `slomo` sin cronómetro el factor de estiramiento es
  desconocido y cualquier tiempo sería ficción, y el gate lo rechaza.

Un clip cuyo camino no está acá se rechaza igual que antes: declarar no es
adivinar, es dejar el supuesto escrito.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

# Diferencia relativa tolerada entre stretch_factor y fps_real / fps_playback.
_STRETCH_CONSISTENCY = 0.01

# Los seis campos que sólo existen si hubo cronómetro. En un camino declarado
# los seis van en `null`: no hay medición que ponerles.
_CALIBRATION_FIELDS = ("fps_real", "fps_playback", "stretch_factor", "fps_method", "calibrated_on", "calibrated_by")

# El camino genérico para "no sé con qué se filmó". Existe en el archivo del
# repo; el id se usa como default en el modo exploración.
GENERIC_VIDEO_ID = "desconocido-video"

CAPTURE_PATHS_FILE = "capture-paths.yaml"


class CapturePath(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    device: str
    mode: Literal["video", "slomo"]
    transfer: str
    # `false` = declarado por el usuario, sin cronómetro (ADR-016). Ausente =
    # `true`: los caminos escritos antes de ADR-016 son todos calibrados.
    calibrated: bool = True
    # Lo que dice el ajuste de la cámara. `null` cuando no se sabe.
    nominal_fps: int | None = Field(default=None, gt=0)
    # `null` = el camino no declara codec: el chequeo del gate queda sin evaluar.
    codec_expected: Literal["hevc", "h264"] | None = None
    fps_real: float | None = Field(default=None, gt=0, description="tasa de CAPTURA, medida con cronómetro filmado")
    fps_playback: float | None = Field(default=None, gt=0, description="tasa a la que el archivo reproduce, medida de los PTS")
    stretch_factor: float | None = Field(default=None, gt=0, description="fps_real / fps_playback")
    fps_method: str | None = None
    calibrated_on: date | None = None
    calibrated_by: str | None = None
    notes: str = ""

    @model_validator(mode="after")
    def _calibration_is_all_or_nothing(self) -> "CapturePath":
        if self.calibrated:
            missing = [f for f in _CALIBRATION_FIELDS if getattr(self, f) is None]
            if missing:
                raise ValueError(
                    f"{self.id}: un camino calibrado necesita {', '.join(missing)}. "
                    "Si no se filmó el cronómetro, va con calibrated: false (ADR-016)."
                )
            if self.nominal_fps is None:
                raise ValueError(f"{self.id}: un camino calibrado necesita nominal_fps")
            if self.codec_expected is None:
                raise ValueError(f"{self.id}: un camino calibrado necesita codec_expected")
            expected = self.fps_real / self.fps_playback
            if abs(expected - self.stretch_factor) / expected > _STRETCH_CONSISTENCY:
                raise ValueError(
                    f"{self.id}: stretch_factor {self.stretch_factor} no coincide con "
                    f"fps_real / fps_playback = {expected:.4f}"
                )
        else:
            declared = [f for f in _CALIBRATION_FIELDS if getattr(self, f) is not None]
            if declared:
                raise ValueError(
                    f"{self.id}: un camino sin calibrar no puede declarar {', '.join(declared)}: "
                    "esos números salen del cronómetro filmado, no de una declaración (ADR-016)."
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

    def ids(self) -> list[str]:
        return [p.id for p in self.paths]


def load_capture_paths(path: str | Path) -> CapturePaths:
    text = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: el YAML tiene que ser un mapa con schema_version y paths")
    if data.get("paths") is None:
        data["paths"] = []
    return CapturePaths.model_validate(data)


def default_capture_paths_file() -> Path:
    """`data/capture-paths.yaml`: primero relativo al directorio de trabajo,
    después relativo al paquete (el repo, que es donde vive la configuración:
    CONTRATO.md §Layout). Devuelve el candidato del cwd si ninguno existe, para
    que el mensaje de error nombre la ruta que el usuario esperaba."""
    from_cwd = Path("data") / CAPTURE_PATHS_FILE
    if from_cwd.is_file():
        return from_cwd
    from_repo = Path(__file__).resolve().parents[2] / "data" / CAPTURE_PATHS_FILE
    return from_repo if from_repo.is_file() else from_cwd


def resolve_path_id(path_id: str, capture_paths: CapturePaths | None = None) -> CapturePath:
    """El camino con ese id, o un error que dice cuáles hay. Lo usa el modo
    exploración, que no corre el gate pero sí necesita saber bajo qué supuesto
    está midiendo el tiempo."""
    if capture_paths is None:
        f = default_capture_paths_file()
        if not f.is_file():
            raise ValueError(f"no existe {f}: sin capture-paths.yaml no hay camino de captura que declarar")
        capture_paths = load_capture_paths(f)
    path = capture_paths.get(path_id)
    if path is None:
        raise ValueError(f"camino de captura desconocido: '{path_id}'. Los que hay: {', '.join(capture_paths.ids()) or '(ninguno)'}")
    return path
