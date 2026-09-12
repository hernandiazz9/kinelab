"""Cámara pinhole con distorsión (modelo de OpenCV) y extrínsecos por vista.

Marco mundo: x hacia el objetivo, y arriba, z hacia la pelota. `face_on`: la
cámara está del lado de la pelota mirando al golfista (−z). `down_the_line`:
detrás del golfista sobre la línea de tiro mirando al objetivo (+x). Imagen en
`image_px` (y hacia abajo), como la pose real.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import yaml

CAMERAS_DIR = Path(__file__).resolve().parents[1] / "cameras"


@dataclass(frozen=True)
class Intrinsics:
    id: str
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    dist: tuple[float, ...]
    provenance: str

    @property
    def K(self) -> np.ndarray:
        return np.array([[self.fx, 0.0, self.cx], [0.0, self.fy, self.cy], [0.0, 0.0, 1.0]])

    def scaled(self, factor: float) -> "Intrinsics":
        """La misma cámara con el sujeto `factor` veces más grande en px (equivale a acercarse)."""
        return Intrinsics(self.id, self.width, self.height, self.fx * factor, self.fy * factor, self.cx, self.cy, self.dist, self.provenance)


def load_intrinsics(name_or_path: str | Path) -> Intrinsics:
    p = Path(name_or_path)
    if not p.is_file():
        p = CAMERAS_DIR / f"{name_or_path}.yaml"
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    return Intrinsics(d["id"], int(d["width"]), int(d["height"]), float(d["fx"]), float(d["fy"]), float(d["cx"]), float(d["cy"]), tuple(float(x) for x in d.get("dist", [0, 0, 0, 0, 0])), str(d.get("provenance", "sin_verificar")))


@dataclass(frozen=True)
class Extrinsics:
    position: np.ndarray  # (3,) en mundo
    target: np.ndarray  # (3,) hacia dónde mira

    def rt(self) -> tuple[np.ndarray, np.ndarray]:
        f = self.target - self.position
        f = f / np.linalg.norm(f)
        up = np.array([0.0, 1.0, 0.0])
        r = np.cross(f, up)
        r = r / np.linalg.norm(r)
        d = np.cross(f, r)  # "abajo" de la cámara (y de imagen hacia abajo)
        R = np.stack([r, d, f])
        rvec, _ = cv2.Rodrigues(R)
        tvec = -R @ self.position
        return rvec, tvec.reshape(3, 1)


def view_extrinsics(view: str, *, distance_m: float, height_m: float, azimuth_deg: float = 0.0, elevation_deg: float = 0.0, look_at_height_m: float = 1.0) -> Extrinsics:
    """Cámara a `distance_m` del golfista, a `height_m` del suelo, girada
    `azimuth_deg` alrededor del golfista respecto de la vista ideal y
    `elevation_deg` por encima de la horizontal (mira al punto a `look_at_height_m`)."""
    base = np.array([0.0, 0.0, 1.0]) if view == "face_on" else np.array([-1.0, 0.0, 0.0]) if view == "down_the_line" else None
    if base is None:
        raise ValueError(f"vista desconocida: {view}")
    c, s = np.cos(np.radians(azimuth_deg)), np.sin(np.radians(azimuth_deg))
    rot = np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])
    horiz = rot @ base
    el = np.radians(elevation_deg)
    pos = horiz * distance_m * np.cos(el)
    pos[1] = height_m + distance_m * np.sin(el)
    return Extrinsics(position=pos, target=np.array([0.0, look_at_height_m, 0.0]))


def project(points_m: np.ndarray, intr: Intrinsics, extr: Extrinsics) -> np.ndarray:
    """(T,J,3) metros → (T,J,2) píxeles image_px, con distorsión."""
    rvec, tvec = extr.rt()
    T, Jn, _ = points_m.shape
    flat = points_m.reshape(-1, 1, 3).astype(np.float64)
    px, _ = cv2.projectPoints(flat, rvec, tvec, intr.K, np.array(intr.dist, dtype=np.float64))
    return px.reshape(T, Jn, 2)
