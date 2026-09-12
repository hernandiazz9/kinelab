"""Encuadre y detección (ESPECIFICACION 1.3): la altura del cuerpo en píxeles
por cuadro y los tres chequeos de la Fase 1 que van al gate de `capture.json`.

`body_height_px` es la unidad por la que después se divide toda métrica
normalizada, así que se sigue cuadro a cuadro: una toma con zoom o con el
atleta caminando hacia la cámara cambia de escala, y una mediana única sobre
todo el clip erraría por ese factor (HERENCIA.md §Cementerio, el bug de ×2,8).

Marco: `image_px`, y hacia abajo. La altura es `|y_cabeza − y_tobillos|`, así
que el signo de y no la afecta; el marco importa para todo lo demás.

Los umbrales no viven acá: llegan en `PerceptionGates` (`kinelab.sport`),
que cada deporte instancia. Este módulo no conoce ningún deporte.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from kinelab.ingest.gate import Check
from kinelab.perception.keypoints import H

if TYPE_CHECKING:  # sólo para anotar: en runtime alcanza con los atributos (duck typing)
    from kinelab.perception.tracking import TrackResult
    from kinelab.sport import PerceptionGates

# Rango plausible del cociente (cabeza→tobillos) / torso, para que la
# calibración por clip ignore cuadros con el tronco muy escorzado o un keypoint
# en cualquier lado. Estimación anatómica (procedencia `estimacion`): con la
# cabeza (no la nariz) arriba y el torso medido de hombros a caderas, el
# cociente ronda 3; el rango es ancho a propósito.
TORSO_TO_HEIGHT_RANGE = (1.5, 4.5)
TORSO_TO_HEIGHT_DEFAULT = 3.0
# Cuadros válidos mínimos para calibrar el cociente con el propio clip; por
# debajo se usa el default.
TORSO_RATIO_MIN_FRAMES = 5

CHECK_IDS = ("body_height_frac", "detection_rate", "single_subject")


def _rolling_nanmedian(x: np.ndarray, window: int) -> np.ndarray:
    """Mediana móvil centrada, tolerante a NaN, bordes sostenidos."""
    # Portado de padel-coach analyzer/padel_analyzer/kinematics.py:160-178 (ADR-013).
    n = x.size
    w = max(1, int(window) | 1)  # impar, para que la ventana sea simétrica
    if n == 0 or w <= 1:
        return x.copy()
    if w >= n:
        w = n if n % 2 else n - 1
        if w <= 1:
            return x.copy()
    pad = w // 2
    padded = np.pad(x, (pad, pad), mode="edge")
    win = np.lib.stride_tricks.sliding_window_view(padded, w)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # ventanas todas NaN son esperables
        return np.nanmedian(win, axis=1)


def _ankle_line_y(kpts: np.ndarray) -> np.ndarray:
    """`y` de la línea de piso bajo el sujeto: media de los dos tobillos,
    ignorando uno ocluido."""
    # Portado de padel-coach analyzer/padel_analyzer/kinematics.py:257-261 (ADR-013).
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmean(np.stack([kpts[..., H.LEFT_ANKLE, 1], kpts[..., H.RIGHT_ANKLE, 1]], axis=-1), axis=-1)


def _top_of_body_y(kpts: np.ndarray) -> np.ndarray:
    """`y` del extremo superior: `head` (17) si tiene valor, `nose` (0) si no."""
    head = kpts[..., H.HEAD, 1]
    nose = kpts[..., H.NOSE, 1]
    return np.where(np.isfinite(head), head, nose)


def _torso_length(kpts: np.ndarray) -> np.ndarray:
    """Distancia centro de hombros → centro de caderas, con articulaciones
    reales (no el `hip`/`neck` predicho por la red)."""
    # Portado de padel-coach analyzer/padel_analyzer/kinematics.py:69-75,106-107 (ADR-013).
    mid_shoulder = (kpts[..., H.LEFT_SHOULDER, :] + kpts[..., H.RIGHT_SHOULDER, :]) / 2.0
    mid_hip = (kpts[..., H.LEFT_HIP, :] + kpts[..., H.RIGHT_HIP, :]) / 2.0
    d = mid_shoulder - mid_hip
    return np.hypot(d[..., 0], d[..., 1])


def body_height_px(kpts: np.ndarray, fps: float, *, window_s: float = 1.0) -> np.ndarray:
    """Altura del cuerpo en píxeles por cuadro, `(T,)`.

    Medida primaria: cabeza (o nariz si la cabeza falta) a la línea de
    tobillos. Cuando faltan los dos tobillos, respaldo por el torso escalado
    por el cociente cabeza-tobillos / torso del PROPIO clip, así las dos
    medidas comparten unidad. Después, mediana móvil centrada de `window_s`
    segundos para que una agachada o un salto no achiquen la escala; los
    cuadros que ninguna ventana cubre toman la mediana global del clip.
    `NaN` en todos los cuadros sólo si ningún cuadro se pudo medir.
    """
    # Portado de padel-coach analyzer/padel_analyzer/kinematics.py:180-212 (ADR-013).
    # Cambios: Halpe26 (cabeza en vez de nariz cuando existe), `J` no fijado,
    # `window_s` como parámetro, y `(T,)` de NaN en vez de `None`.
    if fps <= 0 or not math.isfinite(fps):
        raise ValueError(f"fps tiene que ser positivo: {fps}")
    if window_s <= 0:
        raise ValueError(f"window_s tiene que ser positiva: {window_s}")
    kpts = np.asarray(kpts, dtype=np.float64)
    if kpts.ndim != 3 or kpts.shape[-1] != 2:
        raise ValueError(f"se esperaba kpts (T, J, 2); llegó {kpts.shape}")
    n_frames = kpts.shape[0]
    if n_frames == 0:
        return np.full(0, np.nan, dtype=np.float64)

    direct = np.abs(_top_of_body_y(kpts) - _ankle_line_y(kpts))
    direct = np.where(np.isfinite(direct) & (direct > 0), direct, np.nan)

    torso = _torso_length(kpts)
    torso = np.where(np.isfinite(torso) & (torso > 0), torso, np.nan)

    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = direct / torso
    ratio = ratio[np.isfinite(ratio)]
    ratio = ratio[(ratio >= TORSO_TO_HEIGHT_RANGE[0]) & (ratio <= TORSO_TO_HEIGHT_RANGE[1])]
    k = float(np.median(ratio)) if ratio.size >= TORSO_RATIO_MIN_FRAMES else TORSO_TO_HEIGHT_DEFAULT

    raw = np.where(np.isfinite(direct), direct, torso * k)
    if not np.isfinite(raw).any():
        return np.full(n_frames, np.nan, dtype=np.float64)
    smooth = _rolling_nanmedian(raw, int(round(window_s * fps)))
    fallback = float(np.nanmedian(raw))
    return np.where(np.isfinite(smooth) & (smooth > 0), smooth, fallback).astype(np.float64)


@dataclass
class FramingReport:
    """Lo que el gate de la Fase 1 mira. Estadísticos sobre los cuadros con
    sujeto detectado; `NaN` cuando no hubo ninguno."""

    body_height_px_median: float
    body_height_px_min: float
    body_height_px_max: float
    # mediana de la altura del cuerpo / alto del cuadro
    frac_of_frame: float
    detection_rate: float
    # fracción de cuadros con más de un candidato válido
    multi_subject_frac: float
    # desplazamiento mediano de cámara entre muestras, en px de la muestra; None si no se midió
    camera_motion_px: float | None


def framing_report(track: "TrackResult", fps: float, frame_height: int, camera_motion_px: float | None) -> FramingReport:
    """Resume el encuadre de una toma a partir del seguimiento de un sujeto.

    `track` es un `TrackResult` o cualquier objeto con `keypoints (T,J,2)`,
    `scores (T,J)`, `detected_mask (T,)`, `candidates (T,)` y
    `detection_rate`. `frame_height` es el alto del cuadro como se ve
    (ya rotado), en píxeles.
    """
    if frame_height <= 0:
        raise ValueError(f"frame_height tiene que ser positivo: {frame_height}")
    kpts = np.asarray(track.keypoints, dtype=np.float64)
    if kpts.ndim != 3 or kpts.shape[-1] != 2:
        raise ValueError(f"se esperaba keypoints (T, J, 2); llegó {kpts.shape}")
    n_frames = kpts.shape[0]
    detected = np.asarray(track.detected_mask, dtype=bool).reshape(-1)
    candidates = np.asarray(track.candidates).reshape(-1)
    if detected.shape != (n_frames,) or candidates.shape != (n_frames,):
        raise ValueError(f"detected_mask {detected.shape} / candidates {candidates.shape} no coinciden con T={n_frames}")

    heights = body_height_px(kpts, fps)
    valid = detected & np.isfinite(heights) & (heights > 0)
    if valid.any():
        h = heights[valid]
        median, h_min, h_max = float(np.median(h)), float(h.min()), float(h.max())
    else:
        median = h_min = h_max = math.nan
    rate = float(track.detection_rate)
    if not math.isfinite(rate):
        rate = 0.0
    multi = float(np.mean(candidates > 1)) if n_frames else 0.0
    return FramingReport(
        body_height_px_median=median,
        body_height_px_min=h_min,
        body_height_px_max=h_max,
        frac_of_frame=median / frame_height,
        detection_rate=rate,
        multi_subject_frac=multi,
        camera_motion_px=None if camera_motion_px is None else float(camera_motion_px),
    )


def _pct(x: float) -> int:
    return int(round(100.0 * x))


def _finite_or_none(x: float) -> float | None:
    return float(x) if math.isfinite(x) else None


def framing_checks(report: FramingReport, gates: "PerceptionGates") -> list[Check]:
    """Los tres chequeos de la Fase 1, en el orden del gate (CAPTURA.md):
    `body_height_frac`, `detection_rate`, `single_subject`.

    Frases para el entrenador, en español. `body_height_frac` se reporta con
    `passed=None` y razón "umbral sin medir" mientras
    `gates.body_height_frac_min` sea `None`. Nunca lanza por un reporte vacío:
    un clip sin sujeto falla con razones legibles.
    """
    checks: list[Check] = []

    frac = report.frac_of_frame
    threshold = gates.body_height_frac_min
    frac_value = _finite_or_none(frac)
    if threshold is None:
        if frac_value is None:
            reason = "Sin evaluar: umbral sin medir (se fija midiendo sobre los clips reales, ESPECIFICACION 1.3), y no se detectó al jugador en ningún cuadro."
        else:
            reason = (
                f"Sin evaluar: umbral sin medir (se fija midiendo sobre los clips reales, ESPECIFICACION 1.3). "
                f"El jugador ocupa {_pct(frac)} % del alto del cuadro."
            )
        checks.append(Check(id="body_height_frac", passed=None, value=frac_value, expected=None, reason=reason))
    elif frac_value is None:
        checks.append(
            Check(
                id="body_height_frac",
                passed=False,
                value=None,
                expected=threshold,
                reason="No se pudo medir cuánto ocupa el jugador: no se lo detectó en ningún cuadro.",
            )
        )
    elif frac >= threshold:
        checks.append(Check(id="body_height_frac", passed=True, value=round(frac, 4), expected=threshold))
    else:
        checks.append(
            Check(
                id="body_height_frac",
                passed=False,
                value=round(frac, 4),
                expected=threshold,
                reason=f"El jugador ocupa {_pct(frac)} % del alto del cuadro. Acercá la cámara.",
            )
        )

    rate = report.detection_rate if math.isfinite(report.detection_rate) else 0.0
    if rate >= gates.detection_rate_min:
        checks.append(Check(id="detection_rate", passed=True, value=round(rate, 4), expected=gates.detection_rate_min))
    else:
        checks.append(
            Check(
                id="detection_rate",
                passed=False,
                value=round(rate, 4),
                expected=gates.detection_rate_min,
                reason=f"Se perdió al jugador en el {_pct(1.0 - rate)} % de los cuadros.",
            )
        )

    multi = report.multi_subject_frac if math.isfinite(report.multi_subject_frac) else 0.0
    if multi <= gates.multi_subject_frac_max:
        checks.append(Check(id="single_subject", passed=True, value=round(multi, 4), expected=gates.multi_subject_frac_max))
    else:
        checks.append(
            Check(
                id="single_subject",
                passed=False,
                value=round(multi, 4),
                expected=gates.multi_subject_frac_max,
                reason=f"Hay más de una persona en cuadro ({_pct(multi)} % de los cuadros).",
            )
        )
    return checks
