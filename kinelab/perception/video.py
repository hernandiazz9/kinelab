"""Lectura de cuadros: OpenCV con transcodificación de rescate, rotación y
movimiento de cámara.

Convención de rotación: `rotation_deg` es en sentido HORARIO (iPhone en
vertical = 90), la misma del `capture.json`. OpenCV puede aplicar la rotación
por su cuenta al decodificar; la regla es no rotar dos veces (ver `iter_frames`).
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Iterator

import cv2
import numpy as np

TRANSCODE_TIMEOUT_S = 900
_ROTATIONS = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}


class VideoError(RuntimeError):
    """El archivo no se pudo abrir ni transcodificar."""


def ffmpeg_bin() -> str:
    return os.environ.get("KINELAB_FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"


def rotate_frame(frame: np.ndarray, rotation_deg: int) -> np.ndarray:
    """Gira el cuadro `rotation_deg` grados en sentido horario (0/90/180/270)."""
    r = int(rotation_deg) % 360
    if r == 0:
        return frame
    if r not in _ROTATIONS:
        raise ValueError(f"rotación no soportada: {rotation_deg}°")
    return cv2.rotate(frame, _ROTATIONS[r])


# Portado de padel-coach analyzer/padel_analyzer/video.py:92-137 (ADR-013).
def transcode_h264(src: Path, dst: Path, timeout: float = TRANSCODE_TIMEOUT_S) -> None:
    cmd = [
        ffmpeg_bin(), "-y", "-v", "error", "-nostdin", "-i", str(src),
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(dst),
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)


def open_capture(path: str | Path) -> tuple[cv2.VideoCapture, Path | None]:
    """Abre con OpenCV; si no lee ni el primer cuadro, transcodifica a H.264 en un
    temporal y abre ese. Devuelve `(capture, temporal)`; el llamador borra el
    temporal cuando no es `None`."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    cap = cv2.VideoCapture(str(path))
    ok = cap.isOpened()
    if ok:
        ok, frame = cap.read()
        ok = bool(ok) and frame is not None
    cap.release()
    if ok:
        return cv2.VideoCapture(str(path)), None
    fd, name = tempfile.mkstemp(prefix="kinelab_", suffix=".mp4")
    os.close(fd)
    tmp = Path(name)
    try:
        transcode_h264(path, tmp)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        tmp.unlink(missing_ok=True)
        raise VideoError(f"{path}: OpenCV no lo abre y ffmpeg no pudo transcodificarlo ({e.__class__.__name__}).") from e
    cap = cv2.VideoCapture(str(tmp))
    if not cap.isOpened():
        tmp.unlink(missing_ok=True)
        raise VideoError(f"{path}: no se pudo abrir ni después de transcodificar.")
    return cap, tmp


def iter_frames(
    path: str | Path,
    *,
    rotation_deg: int = 0,
    display_size: tuple[int, int] | None = None,
    progress_cb: Callable[[int], None] | None = None,
) -> Iterator[tuple[int, np.ndarray]]:
    """Produce `(índice, cuadro BGR)` ya rotado como se ve.

    Regla contra la doble rotación: si OpenCV declara que aplicó la rotación de
    metadatos (`CAP_PROP_ORIENTATION_AUTO`), o si el cuadro decodificado ya
    tiene el tamaño de `display_size` (ancho, alto) siendo distinto del
    almacenado, no se rota de nuevo.
    """
    cap, tmp = open_capture(path)
    try:
        r = int(rotation_deg) % 360
        auto = False
        if r:
            try:
                auto = bool(cap.get(cv2.CAP_PROP_ORIENTATION_AUTO)) and float(cap.get(cv2.CAP_PROP_ORIENTATION_META)) != 0.0
            except cv2.error:
                auto = False
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            if r and not auto:
                h, w = frame.shape[:2]
                already = display_size is not None and (w, h) == tuple(display_size) and w != h
                if not already:
                    frame = rotate_frame(frame, r)
            yield idx, frame
            idx += 1
            if progress_cb is not None and idx % 10 == 0:
                progress_cb(idx)
    finally:
        cap.release()
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def sample_gray(frame: np.ndarray, max_side: int = 320) -> np.ndarray:
    """Versión gris y chica de un cuadro, para medir movimiento de cámara."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    h, w = gray.shape[:2]
    scale = min(1.0, max_side / max(h, w))
    if scale < 1.0:
        gray = cv2.resize(gray, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA)
    return gray


# Portado de padel-coach analyzer/padel_analyzer/report.py:85-103 (ADR-013).
def camera_motion_px(gray_samples: list[np.ndarray]) -> float | None:
    """Mediana del corrimiento absoluto cuadro a cuadro (px, a la escala de las
    muestras) por correlación de fase. `None` si no hay dos muestras comparables."""
    if len(gray_samples) < 2:
        return None
    shifts: list[float] = []
    for a, b in zip(gray_samples[:-1], gray_samples[1:]):
        if a.shape != b.shape:
            continue
        try:
            (dx, dy), _ = cv2.phaseCorrelate(np.float32(a), np.float32(b))
        except cv2.error:
            continue
        if math.isfinite(dx) and math.isfinite(dy):
            shifts.append(math.hypot(dx, dy))
    return float(np.median(shifts)) if shifts else None
