"""Selección y seguimiento de un solo sujeto por cuadro.

Portado de padel-coach analyzer/padel_analyzer/pose.py:124-216 (ADR-013), con
`J` como parámetro y los keypoints CRUDOS en la salida: nada de máscaras por
score ni relleno, eso es derivado (invariante 1).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from kinelab.perception.keypoints import CORE_JOINTS, H


@dataclass
class TrackResult:
    keypoints: np.ndarray  # (T,J,2) float32; toda la fila NaN cuando no hubo sujeto
    scores: np.ndarray  # (T,J) float32; 0 cuando no hubo sujeto
    bbox: np.ndarray  # (T,4) float32 xyxy usada para el recorte; NaN si no hubo
    detected_mask: np.ndarray  # (T,) bool
    candidates: np.ndarray  # (T,) int: personas válidas en el cuadro
    frames_detected: int
    detection_rate: float


def _bbox_of(kpts: np.ndarray, scores: np.ndarray, min_score: float) -> tuple[float, float, float, float] | None:
    valid = scores >= min_score
    if valid.sum() < 4:
        return None
    pts = kpts[valid]
    x0, y0 = pts.min(axis=0)
    x1, y1 = pts.max(axis=0)
    return float(x0), float(y0), float(x1), float(y1)


def _person_size(kpts: np.ndarray, scores: np.ndarray, min_score: float) -> float:
    """Área de la caja, ponderada por la altura cadera–tobillo cuando existe."""
    box = _bbox_of(kpts, scores, min_score)
    if box is None:
        return 0.0
    area = max(box[2] - box[0], 1.0) * max(box[3] - box[1], 1.0)
    hips = [i for i in (H.LEFT_HIP, H.RIGHT_HIP) if scores[i] >= min_score]
    ankles = [i for i in (H.LEFT_ANKLE, H.RIGHT_ANKLE) if scores[i] >= min_score]
    if hips and ankles:
        leg = abs(float(np.mean(kpts[ankles, 1]) - np.mean(kpts[hips, 1])))
        area *= 1.0 + leg / max(box[3] - box[1], 1.0)
    return area


class SubjectTracker:
    """Un sujeto por cuadro: el más grande al arrancar (o tras perderlo
    `reacquire_after` cuadros); después, el más cercano al centroide anterior,
    con tope de salto de `max_jump_body_heights` alturas."""

    def __init__(
        self,
        *,
        core_joints: tuple[int, ...] = CORE_JOINTS,
        min_joint_score: float = 0.3,
        min_core_score: float = 0.3,
        max_jump_body_heights: float = 0.5,
        reacquire_after: int = 15,
    ) -> None:
        self.core_joints = tuple(core_joints)
        self.min_joint_score = min_joint_score
        self.min_core_score = min_core_score
        self.max_jump = max_jump_body_heights
        self.reacquire_after = reacquire_after
        self.prev_centroid: np.ndarray | None = None
        self.prev_height: float | None = None
        self.lost_streak = 0
        self._kpts: list[np.ndarray] = []
        self._scores: list[np.ndarray] = []
        self._bbox: list[np.ndarray] = []
        self._detected: list[bool] = []
        self._candidates: list[int] = []
        self._J: int | None = None

    def _is_valid(self, scores: np.ndarray) -> bool:
        return float(np.mean(scores[list(self.core_joints)])) >= self.min_core_score

    def _choose(self, kpts: np.ndarray, scores: np.ndarray) -> tuple[int | None, int]:
        n = kpts.shape[0]
        cands = [i for i in range(n) if self._is_valid(scores[i]) and _bbox_of(kpts[i], scores[i], self.min_joint_score) is not None]
        if not cands:
            return None, 0
        if self.prev_centroid is None or self.lost_streak >= self.reacquire_after:
            return max(cands, key=lambda i: _person_size(kpts[i], scores[i], self.min_joint_score)), len(cands)
        best, best_d = None, np.inf
        for i in cands:
            box = _bbox_of(kpts[i], scores[i], self.min_joint_score)
            c = np.array([(box[0] + box[2]) / 2, (box[1] + box[3]) / 2])
            d = float(np.linalg.norm(c - self.prev_centroid))
            if d < best_d:
                best, best_d = i, d
        limit = self.max_jump * (self.prev_height or 1.0)
        if best is None or best_d > limit:
            return None, len(cands)
        return best, len(cands)

    def push(self, kpts: np.ndarray, scores: np.ndarray, bboxes: np.ndarray | None = None) -> int | None:
        """Agrega un cuadro con `N` candidatos `(N,J,2)`, `(N,J)`, `(N,4)`. Devuelve el índice elegido."""
        kpts = np.asarray(kpts, dtype=np.float32)
        scores = np.asarray(scores, dtype=np.float32)
        if self._J is None:
            self._J = int(kpts.shape[1]) if kpts.ndim == 3 else int(scores.shape[-1]) if scores.ndim == 2 else None
        J = self._J or 0
        idx, n_c = self._choose(kpts, scores) if kpts.ndim == 3 and kpts.shape[0] else (None, 0)
        self._candidates.append(n_c)
        if idx is None:
            self.lost_streak += 1
            self._kpts.append(np.full((J, 2), np.nan, np.float32))
            self._scores.append(np.zeros(J, np.float32))
            self._bbox.append(np.full(4, np.nan, np.float32))
            self._detected.append(False)
            return None
        self.lost_streak = 0
        k, s = kpts[idx], scores[idx]
        box = _bbox_of(k, s, self.min_joint_score)
        self.prev_centroid = np.array([(box[0] + box[2]) / 2, (box[1] + box[3]) / 2])
        self.prev_height = max(box[3] - box[1], 1.0)
        self._kpts.append(k.copy())
        self._scores.append(s.copy())
        used = np.asarray(bboxes, dtype=np.float32)[idx] if bboxes is not None and len(bboxes) > idx else np.array(box, np.float32)
        self._bbox.append(used.reshape(4))
        self._detected.append(True)
        return idx

    def result(self) -> TrackResult:
        T = len(self._kpts)
        J = self._J or 0
        kpts = np.stack(self._kpts) if T else np.zeros((0, J, 2), np.float32)
        scores = np.stack(self._scores) if T else np.zeros((0, J), np.float32)
        bbox = np.stack(self._bbox) if T else np.zeros((0, 4), np.float32)
        detected = np.array(self._detected, dtype=bool)
        n = int(detected.sum())
        return TrackResult(
            keypoints=kpts.astype(np.float32),
            scores=scores.astype(np.float32),
            bbox=bbox.astype(np.float32),
            detected_mask=detected,
            candidates=np.array(self._candidates, dtype=int),
            frames_detected=n,
            detection_rate=float(n / T) if T else 0.0,
        )
