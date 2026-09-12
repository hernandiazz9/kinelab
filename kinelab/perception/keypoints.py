"""Halpe26: el conjunto de keypoints del motor (ADR-004).

El orden es el de RTMPose/rtmlib y se fija con un test contra la definición de
`rtmlib.visualization.skeleton.halpe26`, así un cambio de librería no mueve un
índice en silencio. Los índices 17 (`head`), 18 (`neck`) y 19 (`hip`) los predice
la red: no son centros articulares (AGENTS.md §Cosas que muerden).

Marco de referencia de todo lo que pasa por acá: `image_px`, origen arriba a la
izquierda, x a la derecha, y hacia ABAJO, en píxeles del cuadro como se ve.
"""

from __future__ import annotations

import numpy as np

HALPE26_NAMES: tuple[str, ...] = (
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "head",
    "neck",
    "hip",
    "left_big_toe",
    "right_big_toe",
    "left_small_toe",
    "right_small_toe",
    "left_heel",
    "right_heel",
)

J = len(HALPE26_NAMES)  # 26


class H:
    """Índices Halpe26, para no escribir números sueltos en el código."""

    NOSE = 0
    LEFT_EYE = 1
    RIGHT_EYE = 2
    LEFT_EAR = 3
    RIGHT_EAR = 4
    LEFT_SHOULDER = 5
    RIGHT_SHOULDER = 6
    LEFT_ELBOW = 7
    RIGHT_ELBOW = 8
    LEFT_WRIST = 9
    RIGHT_WRIST = 10
    LEFT_HIP = 11
    RIGHT_HIP = 12
    LEFT_KNEE = 13
    RIGHT_KNEE = 14
    LEFT_ANKLE = 15
    RIGHT_ANKLE = 16
    HEAD = 17
    NECK = 18
    HIP = 19
    LEFT_BIG_TOE = 20
    RIGHT_BIG_TOE = 21
    LEFT_SMALL_TOE = 22
    RIGHT_SMALL_TOE = 23
    LEFT_HEEL = 24
    RIGHT_HEEL = 25


# Pares (izquierdo, derecho) que se intercambian al espejar la imagen.
LEFT_RIGHT_PAIRS: tuple[tuple[int, int], ...] = (
    (H.LEFT_EYE, H.RIGHT_EYE),
    (H.LEFT_EAR, H.RIGHT_EAR),
    (H.LEFT_SHOULDER, H.RIGHT_SHOULDER),
    (H.LEFT_ELBOW, H.RIGHT_ELBOW),
    (H.LEFT_WRIST, H.RIGHT_WRIST),
    (H.LEFT_HIP, H.RIGHT_HIP),
    (H.LEFT_KNEE, H.RIGHT_KNEE),
    (H.LEFT_ANKLE, H.RIGHT_ANKLE),
    (H.LEFT_BIG_TOE, H.RIGHT_BIG_TOE),
    (H.LEFT_SMALL_TOE, H.RIGHT_SMALL_TOE),
    (H.LEFT_HEEL, H.RIGHT_HEEL),
)

# Articulaciones que definen "hay una persona": hombros y caderas.
CORE_JOINTS: tuple[int, ...] = (H.LEFT_SHOULDER, H.RIGHT_SHOULDER, H.LEFT_HIP, H.RIGHT_HIP)

# Segmentos con longitud anatómica (para plausibilidad y escala).
SEGMENTS: dict[str, tuple[int, int]] = {
    "upper_arm_left": (H.LEFT_SHOULDER, H.LEFT_ELBOW),
    "forearm_left": (H.LEFT_ELBOW, H.LEFT_WRIST),
    "upper_arm_right": (H.RIGHT_SHOULDER, H.RIGHT_ELBOW),
    "forearm_right": (H.RIGHT_ELBOW, H.RIGHT_WRIST),
    "thigh_left": (H.LEFT_HIP, H.LEFT_KNEE),
    "shank_left": (H.LEFT_KNEE, H.LEFT_ANKLE),
    "thigh_right": (H.RIGHT_HIP, H.RIGHT_KNEE),
    "shank_right": (H.RIGHT_KNEE, H.RIGHT_ANKLE),
    "torso": (H.NECK, H.HIP),
    "shoulders": (H.LEFT_SHOULDER, H.RIGHT_SHOULDER),
    "hips": (H.LEFT_HIP, H.RIGHT_HIP),
}

# Huesos para dibujar y para recorrer la cadena.
HALPE26_LIMBS: tuple[tuple[int, int], ...] = (
    (H.LEFT_ANKLE, H.LEFT_KNEE),
    (H.LEFT_KNEE, H.LEFT_HIP),
    (H.LEFT_HIP, H.HIP),
    (H.RIGHT_ANKLE, H.RIGHT_KNEE),
    (H.RIGHT_KNEE, H.RIGHT_HIP),
    (H.RIGHT_HIP, H.HIP),
    (H.HEAD, H.NECK),
    (H.NECK, H.HIP),
    (H.NECK, H.LEFT_SHOULDER),
    (H.LEFT_SHOULDER, H.LEFT_ELBOW),
    (H.LEFT_ELBOW, H.LEFT_WRIST),
    (H.NECK, H.RIGHT_SHOULDER),
    (H.RIGHT_SHOULDER, H.RIGHT_ELBOW),
    (H.RIGHT_ELBOW, H.RIGHT_WRIST),
    (H.LEFT_EYE, H.RIGHT_EYE),
    (H.NOSE, H.LEFT_EYE),
    (H.NOSE, H.RIGHT_EYE),
    (H.LEFT_EYE, H.LEFT_EAR),
    (H.RIGHT_EYE, H.RIGHT_EAR),
    (H.LEFT_EAR, H.LEFT_SHOULDER),
    (H.RIGHT_EAR, H.RIGHT_SHOULDER),
    (H.LEFT_ANKLE, H.LEFT_HEEL),
    (H.LEFT_ANKLE, H.LEFT_BIG_TOE),
    (H.LEFT_ANKLE, H.LEFT_SMALL_TOE),
    (H.RIGHT_ANKLE, H.RIGHT_HEEL),
    (H.RIGHT_ANKLE, H.RIGHT_BIG_TOE),
    (H.RIGHT_ANKLE, H.RIGHT_SMALL_TOE),
)


def index_of(name: str) -> int:
    return HALPE26_NAMES.index(name)


def mirror(kpts: np.ndarray, width: int) -> np.ndarray:
    """Espeja keypoints `(..., J, 2)` horizontalmente en un cuadro de `width` px.

    `x → (width - 1) - x`, `y` queda igual, y los pares izquierda/derecha se
    intercambian: el codo izquierdo de la imagen espejada es el derecho de la
    original. Los NaN se conservan. No muta la entrada.
    """
    kpts = np.asarray(kpts)
    if kpts.shape[-2:] != (J, 2):
        raise ValueError(f"se esperaba (..., {J}, 2); llegó {kpts.shape}")
    out = kpts.copy()
    out[..., 0] = (width - 1) - out[..., 0]
    for left, right in LEFT_RIGHT_PAIRS:
        out[..., left, :], out[..., right, :] = kpts[..., right, :].copy(), kpts[..., left, :].copy()
        out[..., left, 0] = (width - 1) - kpts[..., right, 0]
        out[..., right, 0] = (width - 1) - kpts[..., left, 0]
    return out
