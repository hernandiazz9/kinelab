"""Cadena cinemática de segmentos rígidos con longitudes de de Leva (1996) como
fracción de la estatura, y su salida en los 26 puntos de Halpe26, en metros.

Marco mundo: origen entre los tobillos en el suelo; x hacia el objetivo; y hacia
ARRIBA; z hacia la pelota (saliendo del pecho del golfista en address).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from kinelab.perception.keypoints import H, J

# Fracciones de la estatura (de Leva 1996, adulto; procedencia: pares, valores
# redondeados). Suficientes para un cuerpo plausible; la geometría exacta no
# cambia lo que el arnés mide (proyección y ruido).
FRAC = {
    "shoulder_width": 0.259, "hip_width": 0.191, "thigh": 0.245, "shank": 0.246, "foot_h": 0.039,
    "trunk": 0.288, "neck": 0.052, "head": 0.130, "upper_arm": 0.186, "forearm": 0.146, "hand": 0.108,
    "eye_dx": 0.02, "ear_dx": 0.04, "foot_len": 0.152,
}


@dataclass
class Body:
    height_m: float

    def L(self, key: str) -> float:
        return FRAC[key] * self.height_m


def rot_y(deg: float) -> np.ndarray:
    """Rotación alrededor del eje vertical (yaw)."""
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def knee_position(hip: np.ndarray, ankle: np.ndarray, thigh: float, shank: float, forward: np.ndarray) -> np.ndarray:
    """Rodilla a partir de cadera y tobillo: flexiona hacia `forward` (unitario)."""
    d = float(np.linalg.norm(hip - ankle))
    d = min(d, thigh + shank - 1e-6)
    up = (hip - ankle) / d
    # ley de cosenos: distancia tobillo→proyección de la rodilla sobre la línea
    a = (d * d + shank * shank - thigh * thigh) / (2.0 * d)
    h = float(np.sqrt(max(shank * shank - a * a, 0.0)))
    fwd = forward - np.dot(forward, up) * up
    n = np.linalg.norm(fwd)
    fwd = fwd / n if n > 1e-9 else np.array([0.0, 0.0, 1.0])
    return ankle + a * up + h * fwd


def skeleton(body: Body, *, pelvis: np.ndarray, pelvis_yaw: float, thorax_yaw: float, forward_bend: float, hands: np.ndarray, knee_angles: tuple[float, float], stance: float = 0.30) -> np.ndarray:
    """Los 26 puntos Halpe26 (J,3) en metros para una configuración.

    `pelvis` es el centro de caderas (m). `knee_angles` (izq, der) en grados
    (cadera–rodilla–tobillo). `forward_bend` en grados: inclinación del tronco
    hacia la pelota (+z). Los tobillos quedan fijos en el suelo.
    """
    P = np.zeros((J, 3))
    hw, sw = body.L("hip_width") / 2, body.L("shoulder_width") / 2
    lat = rot_y(pelvis_yaw) @ np.array([1.0, 0.0, 0.0])  # dirección de la línea de caderas
    P[H.LEFT_HIP] = pelvis + hw * lat
    P[H.RIGHT_HIP] = pelvis - hw * lat
    P[H.HIP] = pelvis
    ankle_y = body.L("foot_h")
    half = stance * body.height_m / 2
    P[H.LEFT_ANKLE] = np.array([half, ankle_y, 0.0])
    P[H.RIGHT_ANKLE] = np.array([-half, ankle_y, 0.0])
    fwd = np.array([0.0, 0.0, 1.0])
    for side, hip, ankle in ((0, H.LEFT_HIP, H.LEFT_ANKLE), (1, H.RIGHT_HIP, H.RIGHT_ANKLE)):
        knee = H.LEFT_KNEE if side == 0 else H.RIGHT_KNEE
        P[knee] = knee_position(P[hip], P[ankle], body.L("thigh"), body.L("shank"), fwd)
    for a, heel, big, small, sgn in ((H.LEFT_ANKLE, H.LEFT_HEEL, H.LEFT_BIG_TOE, H.LEFT_SMALL_TOE, 1), (H.RIGHT_ANKLE, H.RIGHT_HEEL, H.RIGHT_BIG_TOE, H.RIGHT_SMALL_TOE, -1)):
        P[heel] = P[a] + np.array([0.0, -ankle_y, -0.3 * body.L("foot_len")])
        P[big] = P[a] + np.array([-0.02 * sgn, -ankle_y, 0.7 * body.L("foot_len")])
        P[small] = P[a] + np.array([0.03 * sgn, -ankle_y, 0.6 * body.L("foot_len")])
    # tronco inclinado hacia la pelota
    trunk_dir = np.array([0.0, np.cos(np.radians(forward_bend)), np.sin(np.radians(forward_bend))])
    thorax = pelvis + body.L("trunk") * trunk_dir
    lat_t = rot_y(thorax_yaw) @ np.array([1.0, 0.0, 0.0])
    P[H.LEFT_SHOULDER] = thorax + sw * lat_t
    P[H.RIGHT_SHOULDER] = thorax - sw * lat_t
    P[H.NECK] = thorax + body.L("neck") * 0.5 * trunk_dir
    head_base = thorax + body.L("neck") * trunk_dir
    P[H.HEAD] = head_base + body.L("head") * trunk_dir
    P[H.NOSE] = head_base + 0.5 * body.L("head") * trunk_dir + 0.08 * body.height_m * np.array([0.0, 0.0, 1.0])
    P[H.LEFT_EYE] = P[H.NOSE] + body.L("eye_dx") * lat_t + np.array([0.0, 0.02, 0.0])
    P[H.RIGHT_EYE] = P[H.NOSE] - body.L("eye_dx") * lat_t + np.array([0.0, 0.02, 0.0])
    P[H.LEFT_EAR] = head_base + 0.5 * body.L("head") * trunk_dir + body.L("ear_dx") * lat_t
    P[H.RIGHT_EAR] = head_base + 0.5 * body.L("head") * trunk_dir - body.L("ear_dx") * lat_t
    # brazos: las manos juntas; codos entre hombro y manos, abiertos hacia afuera
    P[H.LEFT_WRIST] = hands + 0.03 * lat_t
    P[H.RIGHT_WRIST] = hands - 0.03 * lat_t
    for sh, el, wr, sgn in ((H.LEFT_SHOULDER, H.LEFT_ELBOW, H.LEFT_WRIST, 1), (H.RIGHT_SHOULDER, H.RIGHT_ELBOW, H.RIGHT_WRIST, -1)):
        mid = (P[sh] + P[wr]) / 2
        d = float(np.linalg.norm(P[wr] - P[sh]))
        reach = body.L("upper_arm") + body.L("forearm")
        bulge = float(np.sqrt(max(reach * reach / 4 - d * d / 4, 0.0)))
        P[el] = mid + sgn * bulge * 0.8 * lat_t + np.array([0.0, -0.2 * bulge, 0.0])
    return P
