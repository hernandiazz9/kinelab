"""Swing sintético 2-D con verdad conocida, para los tests de eventos (Fase 2)
y semilla del swing paramétrico del arnés (Fase 3).

Una persona de pie; las dos muñecas juntas siguen un arco suave: quietud →
backswing (las manos se alejan y suben) → top → downswing continuo hasta el
follow-through (pasa por la posición de address con velocidad máxima) →
quietud → vuelta lenta al address. Marco image_px, y hacia abajo.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from kinelab.perception.keypoints import H, J


@dataclass
class SynthSwing:
    keypoints: np.ndarray  # (T,J,2) float32
    scores: np.ndarray  # (T,J) float32
    timestamps_s: np.ndarray
    fps: float
    truth: list[dict]  # por repetición: address, top, impact, follow_end (cuadros)
    body_height_px: float
    frame: tuple[int, int]  # (alto, ancho)


def smoothstep(u: np.ndarray) -> np.ndarray:
    u = np.clip(u, 0.0, 1.0)
    return u * u * (3.0 - 2.0 * u)


def synth_swing(fps: float, n_reps: int = 3, *, still_s: float = 1.0, backswing_s: float = 0.9, downswing_s: float = 0.27, follow_s: float = 0.6, recover_s: float = 2.0, amplitude_px: float = 400.0, body_height_px: float = 900.0, frame: tuple[int, int] = (1080, 1920), noise_px: float = 0.0, seed: int = 0) -> SynthSwing:
    D = downswing_s + follow_s
    cycle = still_s + backswing_s + D + still_s + recover_s
    T = int(round(cycle * fps * n_reps)) + int(round(still_s * fps))
    t = np.arange(T) / fps
    p = np.zeros(T)
    truth: list[dict] = []
    for k in range(n_reps):
        t0 = k * cycle
        a, b, c, d = t0 + still_s, t0 + still_s + backswing_s, t0 + still_s + backswing_s + D, t0 + still_s + backswing_s + D + still_s
        back = (t >= a) & (t < b)
        p[back] = smoothstep((t[back] - a) / backswing_s)
        down = (t >= b) & (t < c)
        p[down] = 1.0 - 1.8 * smoothstep((t[down] - b) / D)
        hold = (t >= c) & (t < d)
        p[hold] = -0.8
        rec = (t >= d) & (t < d + recover_s)
        p[rec] = -0.8 * (1.0 - smoothstep((t[rec] - d) / recover_s))
        i_down = np.flatnonzero(down)
        impact = int(i_down[np.argmax(p[i_down] <= 0.0)]) if (p[i_down] <= 0.0).any() else int(i_down[-1])
        truth.append({"address": int(np.flatnonzero(t < a)[-1]), "top": int(np.flatnonzero(down)[0]), "impact": impact, "follow_end": int(np.flatnonzero(hold)[0])})
    x0, y0 = frame[1] / 2, frame[0] - 0.9 * body_height_px * 0.55  # manos a la altura de la cadera
    hands = np.stack([x0 - amplitude_px * p, y0 - 0.3 * amplitude_px * p * p], axis=1)
    h = body_height_px
    kp = np.full((T, J, 2), np.nan)
    ankle_y = frame[0] - 80.0
    base = {H.HEAD: (x0, ankle_y - h), H.NOSE: (x0, ankle_y - 0.95 * h), H.NECK: (x0, ankle_y - 0.85 * h), H.LEFT_EYE: (x0 - 0.02 * h, ankle_y - 0.96 * h), H.RIGHT_EYE: (x0 + 0.02 * h, ankle_y - 0.96 * h), H.LEFT_EAR: (x0 - 0.04 * h, ankle_y - 0.95 * h), H.RIGHT_EAR: (x0 + 0.04 * h, ankle_y - 0.95 * h), H.LEFT_SHOULDER: (x0 - 0.12 * h, ankle_y - 0.82 * h), H.RIGHT_SHOULDER: (x0 + 0.12 * h, ankle_y - 0.82 * h), H.LEFT_HIP: (x0 - 0.08 * h, ankle_y - 0.52 * h), H.RIGHT_HIP: (x0 + 0.08 * h, ankle_y - 0.52 * h), H.HIP: (x0, ankle_y - 0.52 * h), H.LEFT_KNEE: (x0 - 0.08 * h, ankle_y - 0.27 * h), H.RIGHT_KNEE: (x0 + 0.08 * h, ankle_y - 0.27 * h), H.LEFT_ANKLE: (x0 - 0.08 * h, ankle_y), H.RIGHT_ANKLE: (x0 + 0.08 * h, ankle_y), H.LEFT_HEEL: (x0 - 0.09 * h, ankle_y + 0.02 * h), H.RIGHT_HEEL: (x0 + 0.09 * h, ankle_y + 0.02 * h), H.LEFT_BIG_TOE: (x0 - 0.06 * h, ankle_y + 0.03 * h), H.RIGHT_BIG_TOE: (x0 + 0.06 * h, ankle_y + 0.03 * h), H.LEFT_SMALL_TOE: (x0 - 0.1 * h, ankle_y + 0.03 * h), H.RIGHT_SMALL_TOE: (x0 + 0.1 * h, ankle_y + 0.03 * h)}
    for i, (x, y) in base.items():
        kp[:, i] = (x, y)
    kp[:, H.LEFT_WRIST] = hands + (-6.0, 0.0)
    kp[:, H.RIGHT_WRIST] = hands + (6.0, 0.0)
    kp[:, H.LEFT_ELBOW] = (kp[:, H.LEFT_SHOULDER] + hands) / 2 + (-20.0, 0.0)
    kp[:, H.RIGHT_ELBOW] = (kp[:, H.RIGHT_SHOULDER] + hands) / 2 + (20.0, 0.0)
    if noise_px > 0:
        kp += np.random.default_rng(seed).normal(0.0, noise_px, size=kp.shape)
    return SynthSwing(keypoints=kp.astype(np.float32), scores=np.full((T, J), 0.9, np.float32), timestamps_s=t, fps=fps, truth=truth, body_height_px=h, frame=frame)
