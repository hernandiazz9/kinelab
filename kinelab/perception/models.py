"""Registro de los pesos ONNX del motor: qué modelo, de dónde, con qué hash y bajo qué licencia.

Los pesos no viajan con el repo (`models/` está en `.gitignore`): se descargan
una vez y se fijan por hash (ADR-004). Nada de acá los descarga solo; el único
camino es explícito, `python -m kinelab.perception.models --download`. Y por
ADR-010 cada modelo declara TRES licencias por separado — código, pesos y datos
de entrenamiento — y cuando una no se pudo verificar se anota `sin_verificar`,
no se inventa.

`rtmlib` descargaría pesos en runtime y sus detectores por defecto están
entrenados en Human-Art (CC BY-NC-SA 4.0): por eso el detector de acá es el
YOLOX-m de Megvii entrenado en COCO, y el estimador jamás pasa por
`BaseTool.__init__` (ver `estimator.py`).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "DOWNLOAD_CMD",
    "MODELS",
    "ModelError",
    "ModelSpec",
    "download_model",
    "main",
    "model_path",
    "model_status",
    "models_dir",
    "sha256_file",
    "verify_model",
]

DOWNLOAD_CMD = "python -m kinelab.perception.models --download"
ENV_MODELS_DIR = "KINELAB_MODELS"

# Nombre del archivo ONNX adentro de los zips del SDK de MMPose.
ZIP_MEMBER = "end2end.onnx"


@dataclass(frozen=True)
class ModelSpec:
    """Un modelo ONNX fijado por hash, con sus tres licencias (ADR-010).

    `input_size` es `(alto, ancho)` del tensor de entrada `(1, 3, alto, ancho)`.
    OJO: rtmlib usa `(ancho, alto)` en `model_input_size`; la conversión la hace
    el estimador, no el que lee este registro.
    """

    id: str
    filename: str
    url: str
    sha256: str
    size_bytes: int
    kind: str  # "detector" | "pose"
    input_size: tuple[int, int]  # (alto, ancho)
    keypoint_set: str | None
    license_code: str
    license_weights: str
    training_data: str
    training_data_license: str
    notes: str = ""

    def __post_init__(self) -> None:
        if self.kind not in ("detector", "pose"):
            raise ValueError(f"kind tiene que ser 'detector' o 'pose'; llegó {self.kind!r}")
        if len(self.sha256) != 64:
            raise ValueError(f"sha256 tiene que tener 64 hex; llegó {len(self.sha256)}")


MODELS: dict[str, ModelSpec] = {
    "rtmpose-m-halpe26": ModelSpec(
        id="rtmpose-m-halpe26",
        filename="rtmpose-m-halpe26-4d3e73dd.onnx",
        url=(
            "https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/onnx_sdk/"
            "rtmpose-m_simcc-body7_pt-body7-halpe26_700e-256x192-4d3e73dd_20230605.zip"
        ),
        sha256="26f3a19e61304a600dfb82d1001d41d24343b89fc70a33ffc84657e0b0bf2ecf",
        size_bytes=55_685_444,
        kind="pose",
        input_size=(256, 192),
        keypoint_set="halpe26",
        license_code="Apache-2.0 (MMPose)",
        license_weights="Apache-2.0 (OpenMMLab)",
        training_data="body7: COCO, AIC, MPII, CrowdPose, JHMDB, PoseTrack18, Halpe",
        training_data_license="sin_verificar",
        notes=(
            "Zip del SDK de MMPose; el archivo es `end2end.onnx` adentro. Entrada BGR "
            "normalizada con mean=(123.675, 116.28, 103.53) y std=(58.395, 57.12, 57.375), "
            "como lo hace rtmlib. Salidas simcc_x (1, 26, 384) y simcc_y (1, 26, 512)."
        ),
    ),
    "yolox-m-coco": ModelSpec(
        id="yolox-m-coco",
        filename="yolox_m-coco-0.1.1rc0.onnx",
        url="https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_m.onnx",
        sha256="21ff6cfdeb53b013bac2249599e55f00bff3cfdfdab37ed7a4620818c1d15b3f",
        size_bytes=101_259_744,
        kind="detector",
        input_size=(640, 640),
        keypoint_set=None,
        license_code="Apache-2.0 (Megvii)",
        license_weights="Apache-2.0 (Megvii)",
        training_data="COCO 2017",
        training_data_license="CC BY 4.0 (anotaciones de COCO)",
        notes=(
            "Detector entrenado en COCO (ADR-004). Los `yolox_*_humanart` de rtmlib están "
            "prohibidos (CC BY-NC-SA 4.0, ADR-010). Salida (1, 8400, 85) sin NMS; rtmlib la "
            "decodifica. Persona = clase 0. Con este modelo `det_mode` tiene que ser "
            "'multiclass': en modo 'human' rtmlib devolvería las cajas de las 80 clases."
        ),
    ),
}


class ModelError(RuntimeError):
    """Un modelo falta, no coincide su hash, o no se pudo descargar. El mensaje dice qué hacer."""


def models_dir() -> Path:
    """Carpeta de pesos: `$KINELAB_MODELS` si está definida, si no `<repo>/models`."""
    env = os.environ.get(ENV_MODELS_DIR)
    if env:
        return Path(env).expanduser()
    return Path(__file__).resolve().parents[2] / "models"


def sha256_file(path: Path | str) -> str:
    """SHA-256 hexadecimal de un archivo, leído por bloques (los modelos pesan 50–100 MB)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def model_path(spec: ModelSpec) -> Path:
    return models_dir() / spec.filename


def model_status(spec: ModelSpec) -> str:
    """`"ok"`, `"falta"` o `"hash incorrecto"`. No lanza."""
    path = model_path(spec)
    if not path.is_file():
        return "falta"
    if sha256_file(path) != spec.sha256:
        return "hash incorrecto"
    return "ok"


def verify_model(spec: ModelSpec) -> Path:
    """Devuelve la ruta del modelo si existe y su hash coincide; si no, `ModelError` legible."""
    path = model_path(spec)
    if not path.is_file():
        raise ModelError(
            f"Falta el modelo '{spec.id}': no existe {path}.\n"
            f"Para bajarlo: {DOWNLOAD_CMD}\n"
            f"(o definí {ENV_MODELS_DIR} apuntando a la carpeta que lo tiene)."
        )
    got = sha256_file(path)
    if got != spec.sha256:
        raise ModelError(
            f"El modelo '{spec.id}' en {path} no es el que fija el registro.\n"
            f"  sha256 esperado: {spec.sha256}\n"
            f"  sha256 leído:    {got}\n"
            f"Borralo y volvé a bajarlo: {DOWNLOAD_CMD}"
        )
    return path


def _fetch(url: str, dest: Path) -> None:
    """Descarga `url` a `dest` en streaming. Separada para que los tests la reemplacen sin red."""
    req = urllib.request.Request(url, headers={"User-Agent": "kinelab-models/0.1"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out, length=1 << 20)


def _extract_onnx(zip_path: Path, dest: Path) -> None:
    """Saca `end2end.onnx` (o el único `.onnx`) de un zip del SDK de MMPose."""
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        candidates = [n for n in names if n.rsplit("/", 1)[-1] == ZIP_MEMBER]
        if not candidates:
            candidates = [n for n in names if n.lower().endswith(".onnx")]
        if len(candidates) != 1:
            raise ModelError(
                f"El zip {zip_path.name} no tiene exactamente un ONNX reconocible "
                f"(se esperaba {ZIP_MEMBER}); tiene {candidates or names}."
            )
        with zf.open(candidates[0]) as src, open(dest, "wb") as out:
            shutil.copyfileobj(src, out, length=1 << 20)


def download_model(spec: ModelSpec, *, force: bool = False) -> Path:
    """Descarga el modelo a `models_dir()`, verifica el hash y lo deja con escritura atómica.

    Si el archivo ya está y su hash coincide, no descarga nada (salvo `force`).
    La descarga va a un temporal en la misma carpeta; sólo si el hash coincide
    se hace `os.replace` al nombre final, así nunca queda un archivo a medias o
    con hash incorrecto bajo el nombre bueno.
    """
    final = model_path(spec)
    if not force and model_status(spec) == "ok":
        return final
    final.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=final.parent, prefix=f".{spec.id}-") as tmp:
        tmp_dir = Path(tmp)
        raw = tmp_dir / "download.bin"
        try:
            _fetch(spec.url, raw)
        except OSError as e:  # URLError hereda de OSError
            raise ModelError(f"No se pudo descargar '{spec.id}' desde {spec.url}: {e}") from e
        if zipfile.is_zipfile(raw):
            onnx = tmp_dir / spec.filename
            _extract_onnx(raw, onnx)
        else:
            onnx = raw
        got = sha256_file(onnx)
        if got != spec.sha256:
            raise ModelError(
                f"Lo descargado para '{spec.id}' no coincide con el registro.\n"
                f"  sha256 esperado: {spec.sha256}\n"
                f"  sha256 leído:    {got} ({onnx.stat().st_size} bytes; se esperaban {spec.size_bytes})\n"
                f"No se escribió nada en {final}. ¿Cambió el archivo publicado en {spec.url}?"
            )
        os.replace(onnx, final)
    return final


def main(argv: list[str] | None = None) -> int:
    """CLI: lista el estado de cada modelo; con `--download` baja los que faltan. 0 si todos ok."""
    parser = argparse.ArgumentParser(
        prog="python -m kinelab.perception.models",
        description="Estado de los pesos ONNX del motor (fijados por hash, ADR-004).",
    )
    parser.add_argument("--download", action="store_true", help="descargar los que faltan o tienen hash incorrecto")
    parser.add_argument("--force", action="store_true", help="con --download: volver a bajar aunque estén bien")
    args = parser.parse_args(argv)

    print(f"models_dir: {models_dir()}")
    all_ok = True
    for spec in MODELS.values():
        status = model_status(spec)
        if args.download and (args.force or status != "ok"):
            print(f"  {spec.id:<20} descargando {spec.url}")
            try:
                download_model(spec, force=args.force)
            except ModelError as e:
                print(f"  {spec.id:<20} ERROR: {e}")
            status = model_status(spec)
        ok = status == "ok"
        all_ok &= ok
        hint = "" if ok else f"  → {DOWNLOAD_CMD}"
        print(f"  {spec.id:<20} {status:<16} {spec.filename}  {spec.size_bytes:,} bytes{hint}".replace(",", "."))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
