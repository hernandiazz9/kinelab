"""Plausibilidad anatómica por cuadro (ESPECIFICACION 1.4).

Tres señales de que la pose de un cuadro no es de fiar: confianza baja en
demasiados keypoints, un codo fuera del rango anatómico, y una longitud de
segmento que se aparta de la mediana del propio clip. Cada una es un bit de
`Flag`; la máscara `(T,)` uint8 se guarda en `pose.npz` como `plausibility`
(CONTRATO.md §pose.npz). **Marca, no borra**: los keypoints quedan intactos,
los cuadros marcados se cuentan y se muestran (CONTEXTO.md, invariante 5).

Marco de todo lo que entra: `image_px` (origen arriba a la izquierda, y hacia
abajo). Los ángulos son invariantes a ese marco; las longitudes también.
`J` es el segundo eje de los arrays, nunca un número fijo en la lógica.
"""

from __future__ import annotations

from enum import IntFlag

import numpy as np

from kinelab.perception.keypoints import SEGMENTS, H


class Flag(IntFlag):
    """Bits de `plausibility` en `pose.npz`. Los valores son contrato: no se
    renumeran."""

    LOW_SCORE = 1  # pocos keypoints con confianza ≥ `min_score`
    ELBOW_RANGE = 2  # algún codo fuera de `elbow_range`
    SEGMENT_LENGTH = 4  # alguna longitud de segmento lejos de la mediana del clip
    MISSING = 8  # cuadro sin sujeto: todos los keypoints NaN


def angle_deg(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Ángulo en `b` formado por A-B-C, en GRADOS, en [0, 180].

    Vectorizado sobre `(..., 2)`: las tres entradas se difunden entre sí.
    `NaN` si falta cualquier coordenada o si `a == b` o `c == b` (no hay
    ángulo). Es simétrico: `angle_deg(a, b, c) == angle_deg(c, b, a)`, e
    invariante a traslación, escala uniforme, rotación rígida y espejado.
    """
    # Portado de padel-coach analyzer/padel_analyzer/kinematics.py:31-44 (ADR-013).
    # Cambio: `arctan2(|v1 × v2|, v1 · v2)` en vez de `arccos` del coseno, que
    # pierde precisión cerca de 0° y 180° (el barrido 1–179° con 1e-6 lo exige).
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    c = np.asarray(c, dtype=np.float64)
    v1 = a - b
    v2 = c - b
    dot = v1[..., 0] * v2[..., 0] + v1[..., 1] * v2[..., 1]
    cross = v1[..., 0] * v2[..., 1] - v1[..., 1] * v2[..., 0]
    n1 = np.hypot(v1[..., 0], v1[..., 1])
    n2 = np.hypot(v2[..., 0], v2[..., 1])
    ang = np.degrees(np.arctan2(np.abs(cross), dot))
    degenerate = (n1 == 0) | (n2 == 0)
    return np.where(degenerate, np.nan, ang)


def elbow_angles(kpts: np.ndarray) -> np.ndarray:
    """Ángulos de codo `(..., 2)`: columna 0 izquierdo, columna 1 derecho.

    Hombro–codo–muñeca de cada lado, en grados. `kpts` es `(..., J, 2)`.
    """
    kpts = np.asarray(kpts, dtype=np.float64)
    left = angle_deg(kpts[..., H.LEFT_SHOULDER, :], kpts[..., H.LEFT_ELBOW, :], kpts[..., H.LEFT_WRIST, :])
    right = angle_deg(kpts[..., H.RIGHT_SHOULDER, :], kpts[..., H.RIGHT_ELBOW, :], kpts[..., H.RIGHT_WRIST, :])
    return np.stack([left, right], axis=-1)


def segment_lengths(kpts: np.ndarray) -> dict[str, np.ndarray]:
    """Longitud en píxeles de cada segmento de `keypoints.SEGMENTS`, `(...,)`
    por segmento. `NaN` donde falta un extremo."""
    kpts = np.asarray(kpts, dtype=np.float64)
    out: dict[str, np.ndarray] = {}
    for name, (i, j) in SEGMENTS.items():
        d = kpts[..., j, :] - kpts[..., i, :]
        out[name] = np.hypot(d[..., 0], d[..., 1])
    return out


def plausibility_mask(
    kpts: np.ndarray,
    scores: np.ndarray,
    *,
    min_score: float = 0.3,
    elbow_range: tuple[float, float] = (20.0, 180.0),
    segment_tolerance: float = 0.35,
    min_scored_joints: int | None = None,
    segments: tuple[str, ...] | None = None,
) -> tuple[np.ndarray, dict[str, int]]:
    """Máscara de plausibilidad `(T,)` uint8 y conteo de cuadros por razón.

    - `MISSING`: todos los keypoints del cuadro son NaN (no hubo sujeto). Es
      excluyente: en un cuadro vacío no se evalúa nada más.
    - `LOW_SCORE`: menos de `min_scored_joints` keypoints con coordenadas
      finitas y `score ≥ min_score`. Por defecto la mitad de `J`, redondeada
      hacia arriba: un keypoint suelto ocluido (un dedo del pie) no marca el
      cuadro; medio esqueleto dudoso, sí.
    - `ELBOW_RANGE`: algún codo con ángulo finito fuera de `elbow_range`
      (grados, cerrado).
    - `SEGMENT_LENGTH`: alguna longitud de `SEGMENTS` que se aparta más de
      `segment_tolerance` (relativo) de la mediana de ese segmento en el clip.
      Un segmento sin mediana finita y positiva no se evalúa.

    Devuelve `(mask, counts)`: `mask[t]` es la OR de los bits de `Flag`;
    `counts` tiene una entrada por nombre de `Flag` con cuántos cuadros llevan
    ese bit. No muta las entradas.
    """
    kpts = np.asarray(kpts, dtype=np.float64)
    scores = np.asarray(scores, dtype=np.float64)
    if kpts.ndim != 3 or kpts.shape[-1] != 2:
        raise ValueError(f"se esperaba kpts (T, J, 2); llegó {kpts.shape}")
    if scores.shape != kpts.shape[:2]:
        raise ValueError(f"scores {scores.shape} no coincide con kpts {kpts.shape[:2]}")
    lo, hi = elbow_range
    if not (0.0 <= lo < hi <= 180.0):
        raise ValueError(f"elbow_range tiene que estar en [0, 180] y ordenado: {elbow_range}")
    if segment_tolerance <= 0.0:
        raise ValueError(f"segment_tolerance tiene que ser positiva: {segment_tolerance}")

    n_frames, n_joints = kpts.shape[:2]
    if min_scored_joints is None:
        min_scored_joints = (n_joints + 1) // 2
    mask = np.zeros(n_frames, dtype=np.uint8)
    if n_frames == 0:
        return mask, {flag.name: 0 for flag in Flag}

    finite_joint = np.isfinite(kpts).all(axis=-1)  # (T, J)
    missing = ~finite_joint.any(axis=-1)  # (T,)

    scored = finite_joint & (scores >= min_score)
    low_score = scored.sum(axis=-1) < min_scored_joints

    elbows = elbow_angles(kpts)  # (T, 2)
    with np.errstate(invalid="ignore"):
        elbow_bad = (np.isfinite(elbows) & ((elbows < lo) | (elbows > hi))).any(axis=-1)

    # Por defecto, muslos, piernas y tronco: brazos, línea de hombros y línea de caderas se
    # escorzan legítimamente en un gesto (con 90° de giro la línea de hombros mide casi cero).
    names = segments or tuple(n for n in SEGMENTS if n.startswith(("thigh", "shank", "torso")))
    segment_bad = np.zeros(n_frames, dtype=bool)
    for name, length in segment_lengths(kpts).items():
        if name not in names:
            continue
        valid = np.isfinite(length) & (length > 0)
        if not valid.any():
            continue
        median = float(np.median(length[valid]))
        if not (np.isfinite(median) and median > 0):
            continue
        with np.errstate(invalid="ignore"):
            deviation = np.abs(length - median) / median
        segment_bad |= valid & (deviation > segment_tolerance)

    present = ~missing
    mask[present & low_score] |= np.uint8(Flag.LOW_SCORE)
    mask[present & elbow_bad] |= np.uint8(Flag.ELBOW_RANGE)
    mask[present & segment_bad] |= np.uint8(Flag.SEGMENT_LENGTH)
    mask[missing] |= np.uint8(Flag.MISSING)

    counts = {flag.name: int(((mask & int(flag)) != 0).sum()) for flag in Flag}
    return mask, counts
