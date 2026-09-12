"""Estimador de pose: YOLOX-m (COCO) + RTMPose-m (Halpe26) vía rtmlib, sobre
sesiones propias de onnxruntime (ADR-004): CoreML con caída a CPU,
`intra_op_num_threads=5`, pesos verificados por hash antes de cargar.

rtmlib aporta el pre y posprocesado; sus clases se construyen SIN pasar por
`BaseTool.__init__` (que descarga pesos y crea su propia sesión). Dos guardias
medidas (AGENTS.md): la entrada normalizada tiene que caer en un rango
plausible, y ninguna salida puede traer NaN: con CoreML en fp16 una entrada sin
normalizar produce scores todos NaN sin error.

Portado en espíritu de padel-coach analyzer/padel_analyzer/pose.py:57-112
(ADR-013): detector cada N cuadros, cajas siguientes desde las poses
confiables, y nunca el cuadro entero al estimador (la caja fantasma).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from pathlib import Path

import numpy as np
import onnxruntime as ort
from rtmlib import RTMPose, YOLOX

import kinelab
from kinelab.perception.keypoints import CORE_JOINTS, J
from kinelab.perception.models import MODELS, ModelSpec, verify_model

RTMPOSE_MEAN = (123.675, 116.28, 103.53)
RTMPOSE_STD = (58.395, 57.12, 57.375)
# Una imagen normalizada con esos mean/std cae en [-2.2, 2.7]; 0–255 sin normalizar, no.
PREPROCESS_RANGE = (-3.0, 3.0)


class PreprocessError(RuntimeError):
    """La entrada del modelo no está normalizada como el modelo espera."""


class PoseNaNError(RuntimeError):
    """El modelo devolvió NaN o inf: no se escribe nada con eso."""


@dataclass(frozen=True)
class EstimatorConfig:
    pose_model: str = "rtmpose-m-halpe26"
    detector: str = "yolox-m-coco"
    providers: tuple[str, ...] = ("CoreMLExecutionProvider", "CPUExecutionProvider")
    intra_op_num_threads: int = 5  # medido: onnxruntime satura en 5 hilos en el M3 Pro
    det_frequency: int = 10  # correr el detector cada N cuadros (y siempre que no haya cajas)
    det_score_thr: float = 0.5
    nms_thr: float = 0.45
    bbox_expansion: float = 1.25
    min_joint_score: float = 0.3
    min_core_score: float = 0.3


@dataclass
class FrameEstimate:
    keypoints: np.ndarray  # (N,J,2) float32, image_px del cuadro que se pasó
    scores: np.ndarray  # (N,J) float32
    bboxes: np.ndarray  # (N,4) float32 xyxy usadas para el recorte
    detector_ran: bool


def _empty(J_: int = J) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return np.zeros((0, J_, 2), np.float32), np.zeros((0, J_), np.float32), np.zeros((0, 4), np.float32)


def _check_finite(outputs: list[np.ndarray], what: str, provider: str) -> None:
    for o in outputs:
        if not np.isfinite(o).all():
            raise PoseNaNError(
                f"{what}: la salida del modelo tiene NaN/inf con {provider}. "
                "Con CoreML (fp16) es la firma de una entrada sin normalizar. No se escribe nada."
            )


class _Pose(RTMPose):
    """RTMPose de rtmlib con sesión inyectada, aserción de preprocesado y chequeo de NaN."""

    def __init__(self, session: ort.InferenceSession, input_size_wh: tuple[int, int], provider: str) -> None:  # noqa: D107 — no llama a BaseTool.__init__ a propósito
        self.session = session
        self.model_input_size = tuple(input_size_wh)
        self.mean = RTMPOSE_MEAN
        self.std = RTMPOSE_STD
        self.backend = "onnxruntime"
        self.device = provider
        self.to_openpose = False
        self.onnx_model = ""

    def inference(self, img: np.ndarray) -> list[np.ndarray]:
        x = np.ascontiguousarray(img.transpose(2, 0, 1)[None], dtype=np.float32)
        lo, hi = float(x.min()), float(x.max())
        if lo < PREPROCESS_RANGE[0] or hi > PREPROCESS_RANGE[1]:
            raise PreprocessError(
                f"la entrada de RTMPose está fuera de {PREPROCESS_RANGE}: min {lo:.2f}, max {hi:.2f}. "
                "Se saltó la normalización (mean/std)."
            )
        out = self.session.run(None, {self.session.get_inputs()[0].name: x})
        _check_finite(out, "RTMPose", self.device)
        return out


class _Detector(YOLOX):
    """YOLOX de rtmlib con sesión inyectada, en modo multiclase (persona = clase 0)."""

    def __init__(self, session: ort.InferenceSession, input_size_wh: tuple[int, int], provider: str, score_thr: float, nms_thr: float) -> None:  # noqa: D107
        self.session = session
        self.model_input_size = tuple(input_size_wh)
        self.mean = None
        self.std = None
        self.backend = "onnxruntime"
        self.device = provider
        self.det_mode = "multiclass"
        self.score_thr = score_thr
        self.nms_thr = nms_thr
        self.onnx_model = ""

    def inference(self, img: np.ndarray) -> list[np.ndarray]:
        x = np.ascontiguousarray(img.transpose(2, 0, 1)[None], dtype=np.float32)
        out = self.session.run(None, {self.session.get_inputs()[0].name: x})
        _check_finite(out, "YOLOX", self.device)
        return out


def make_session(path: Path, providers: tuple[str, ...], threads: int) -> tuple[ort.InferenceSession, str]:
    """Sesión de onnxruntime con el primer proveedor que cargue. Devuelve (sesión, proveedor activo)."""
    last: Exception | None = None
    for prov in providers:
        so = ort.SessionOptions()
        so.log_severity_level = 3
        so.intra_op_num_threads = int(threads)
        try:
            s = ort.InferenceSession(str(path), so, providers=[prov])
            return s, s.get_providers()[0]
        except Exception as e:  # noqa: BLE001 — se prueba el siguiente proveedor
            last = e
    raise RuntimeError(f"ningún proveedor de {providers} pudo cargar {path}: {last}")


def _clip_box(b: np.ndarray, w: int, h: int) -> list[float] | None:
    x0, y0 = max(0.0, float(b[0])), max(0.0, float(b[1]))
    x1, y1 = min(float(w), float(b[2])), min(float(h), float(b[3]))
    if x1 - x0 < 2 or y1 - y0 < 2:
        return None
    return [x0, y0, x1, y1]


# Portado de padel-coach analyzer/padel_analyzer/pose.py:44-54 (ADR-013).
def _pose_to_bbox(kpts: np.ndarray, scores: np.ndarray, min_score: float, expansion: float, w: int, h: int) -> list[float] | None:
    valid = scores >= min_score
    if valid.sum() < 4:
        return None
    pts = kpts[valid]
    x0, y0 = pts.min(axis=0)
    x1, y1 = pts.max(axis=0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bw, bh = max(x1 - x0, 1.0) * expansion, max(y1 - y0, 1.0) * expansion
    return _clip_box(np.array([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2]), w, h)


class PoseEstimator:
    """Un cuadro BGR → keypoints Halpe26 de cada persona detectada."""

    def __init__(self, config: EstimatorConfig | None = None) -> None:
        cfg = config or EstimatorConfig()
        pose_spec, det_spec = MODELS[cfg.pose_model], MODELS[cfg.detector]
        pose_path, det_path = verify_model(pose_spec), verify_model(det_spec)
        pose_sess, provider = make_session(pose_path, cfg.providers, cfg.intra_op_num_threads)
        det_sess, _ = make_session(det_path, (provider, *[p for p in cfg.providers if p != provider]), cfg.intra_op_num_threads)
        # ModelSpec.input_size es (alto, ancho); rtmlib quiere (ancho, alto).
        self._init(
            det=_Detector(det_sess, det_spec.input_size[::-1], provider, cfg.det_score_thr, cfg.nms_thr),
            pose=_Pose(pose_sess, pose_spec.input_size[::-1], provider),
            provider=provider, config=cfg, pose_spec=pose_spec, det_spec=det_spec,
        )

    @classmethod
    def from_models(cls, det, pose, config: EstimatorConfig | None = None, provider: str = "inyectado") -> "PoseEstimator":
        """Estimador con detector y pose inyectados (tests): no toca disco ni modelos."""
        cfg = config or EstimatorConfig()
        self = cls.__new__(cls)
        self._init(det=det, pose=pose, provider=provider, config=cfg, pose_spec=MODELS[cfg.pose_model], det_spec=MODELS[cfg.detector])
        return self

    def _init(self, *, det, pose, provider: str, config: EstimatorConfig, pose_spec: ModelSpec, det_spec: ModelSpec) -> None:
        self.det, self.pose, self.provider, self.config = det, pose, provider, config
        self.pose_spec, self.det_spec = pose_spec, det_spec
        self.reset()

    @property
    def keypoint_set(self) -> str | None:
        return self.pose_spec.keypoint_set

    def reset(self) -> None:
        self._frame_idx = 0
        self._bboxes: list[list[float]] = []

    def __call__(self, frame: np.ndarray) -> FrameEstimate:
        cfg = self.config
        h, w = frame.shape[:2]
        ran = False
        if self._frame_idx % cfg.det_frequency == 0 or not self._bboxes:
            ran = True
            boxes, cls = self.det(frame)
            boxes = np.asarray(boxes, dtype=np.float32).reshape(-1, 4)
            cls = np.asarray(cls).reshape(-1)
            person = boxes[cls == 0] if cls.size else boxes[:0]
            self._bboxes = [b for b in (_clip_box(p, w, h) for p in person) if b is not None]
        self._frame_idx += 1
        if not self._bboxes:
            # Guardia anti cajas fantasma: sin cajas no se llama al estimador.
            return FrameEstimate(*_empty(), detector_ran=ran)
        used = np.asarray(self._bboxes, dtype=np.float32).reshape(-1, 4)
        kp, sc = self.pose(frame, bboxes=self._bboxes)
        kp = np.asarray(kp, dtype=np.float32)
        sc = np.asarray(sc, dtype=np.float32)
        if kp.ndim != 3 or kp.shape[0] == 0:
            self._bboxes = []
            return FrameEstimate(*_empty(), detector_ran=ran)
        nxt: list[list[float]] = []
        for k, s in zip(kp, sc):
            if float(np.mean(s[list(CORE_JOINTS)])) >= cfg.min_core_score:
                b = _pose_to_bbox(k, s, cfg.min_joint_score, cfg.bbox_expansion, w, h)
                if b is not None:
                    nxt.append(b)
        self._bboxes = nxt
        return FrameEstimate(kp, sc, used, detector_ran=ran)

    def provenance(self) -> dict:
        cfg = self.config
        return {
            "model": self.pose_spec.id,
            "checkpoint_sha256": self.pose_spec.sha256,
            "keypoint_set": self.pose_spec.keypoint_set,
            "input_size": list(self.pose_spec.input_size[::-1]),  # (ancho, alto), como CONTRATO.md
            "detector": self.det_spec.id,
            "detector_sha256": self.det_spec.sha256,
            "provider": self.provider,
            "onnxruntime_version": ort.__version__,
            "rtmlib_version": _rtmlib_version(),
            "intra_op_num_threads": cfg.intra_op_num_threads,
            "det_frequency": cfg.det_frequency,
            "engine_version": kinelab.__version__,
        }


def _rtmlib_version() -> str | None:
    try:
        return _pkg_version("rtmlib")
    except PackageNotFoundError:
        return None


def with_det_frequency(config: EstimatorConfig, n: int) -> EstimatorConfig:
    return replace(config, det_frequency=max(1, int(n)))
