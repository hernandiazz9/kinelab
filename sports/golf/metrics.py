"""Métricas de nivel 1 del golf (CONTRATO.md §Niveles), declaradas en el
registro con sus seis cosas. `mdc`, `fps_min` y `views` se leen de
`sports/golf/mdc.yaml`, que escribe el arnés (`truth/`): no se escriben a mano
(ESPECIFICACION 3.3). Sin esa tabla, `mdc` es None y ninguna es juicio.
"""

from __future__ import annotations

from functools import partial
from pathlib import Path

import yaml

from kinelab.metrics.generic import angle_delta_deg, displacement_cm, duration_ms, ratio
from kinelab.metrics.registry import Metric, Reference, Registry
from kinelab.perception.keypoints import H

MDC_TABLE = Path(__file__).with_name("mdc.yaml")

PELVIS = (H.LEFT_HIP, H.RIGHT_HIP)
THORAX = (H.LEFT_SHOULDER, H.RIGHT_SHOULDER)
HEAD = (H.HEAD,)
# Segmentos para la ganancia de velocidad angular pelvis → tórax → brazo (línea hombro→muñeca).
GAIN_SEGMENTS = {"pelvis": (H.LEFT_HIP, H.RIGHT_HIP), "torso": (H.LEFT_SHOULDER, H.RIGHT_SHOULDER), "arm": (H.LEFT_SHOULDER, H.LEFT_WRIST)}

_DESC = partial(Reference, "descriptive", "estimacion", "sin referencia todavía", "")


def _load_table() -> dict:
    if not MDC_TABLE.is_file():
        return {}
    return yaml.safe_load(MDC_TABLE.read_text(encoding="utf-8")).get("metrics", {}) or {}


def _m(id_: str, unit: str, anchored: tuple[str, ...], compute, *, views_default: tuple[str, ...], definition: str, joints: tuple[int, ...] = ()) -> tuple[Metric | None, tuple[int, ...]]:
    row = _load_table().get(id_, {})
    DECLARED_VIEWS[id_] = tuple(views_default)
    if row and not row.get("views"):
        DEAD_METRICS[id_] = row.get("note") or "sin vista válida en la tabla del arnés"
        return None, joints
    return (
        Metric(
            id=id_, unit=unit, level=1,
            views=tuple(row.get("views") or views_default),
            fps_min=float(row.get("fps_min") or 30.0),
            anchored_to=anchored, reference_frame="image_px", compute=compute,
            reference=Reference("descriptive", "estimacion", "sin rango de referencia; se muestra como descriptiva (ADR-012)", definition),
            mdc=(row.get("mdc") or None) if (row.get("mdc") or 0) > 0 else None,
        ),
        joints,
    )


# Vistas DECLARADAS por métrica (las candidatas que el arnés puede confirmar o quitar).
DECLARED_VIEWS: dict[str, tuple[str, ...]] = {}
# Métricas que el arnés mató (sin vista válida): no se registran, quedan acá con su razón.
DEAD_METRICS: dict[str, str] = {}


def build_registry() -> tuple[Registry, dict[str, tuple[int, ...]]]:
    reg = Registry(version="0.1.0")
    joints: dict[str, tuple[int, ...]] = {}
    specs = [
        _m("backswing_duration_ms", "ms", ("address", "top"), partial(duration_ms, start="address", end="top"), views_default=("face_on", "down_the_line"), definition="tiempo de address a top"),
        _m("downswing_duration_ms", "ms", ("top", "impact"), partial(duration_ms, start="top", end="impact"), views_default=("face_on", "down_the_line"), definition="tiempo de top a impact"),
        _m("tempo_ratio", "ratio", ("address", "top", "impact"), partial(ratio, a=("address", "top"), b=("top", "impact")), views_default=("face_on", "down_the_line"), definition="backswing / downswing; descriptivo, nunca contra 3:1 (ADR-012)"),
        _m("follow_duration_ms", "ms", ("impact", "follow_end"), partial(duration_ms, start="impact", end="follow_end"), views_default=("face_on", "down_the_line"), definition="tiempo de impact a fin del follow-through"),
        _m("pelvis_sway_top_cm", "cm", ("address", "top"), partial(displacement_cm, joints=PELVIS, zero="address", at="top", axis=0), views_default=("face_on",), definition="desplazamiento lateral del centro de caderas (Halpe26 11/12) address→top, x de imagen, cm por altura declarada", joints=PELVIS),
        _m("pelvis_sway_impact_cm", "cm", ("address", "impact"), partial(displacement_cm, joints=PELVIS, zero="address", at="impact", axis=0), views_default=("face_on",), definition="ídem address→impact", joints=PELVIS),
        _m("pelvis_lift_top_cm", "cm", ("address", "top"), partial(displacement_cm, joints=PELVIS, zero="address", at="top", axis=1, sign=-1.0), views_default=("face_on", "down_the_line"), definition="subida del centro de caderas address→top (positivo = sube)", joints=PELVIS),
        _m("thorax_sway_top_cm", "cm", ("address", "top"), partial(displacement_cm, joints=THORAX, zero="address", at="top", axis=0), views_default=("face_on",), definition="desplazamiento lateral del centro de hombros address→top", joints=THORAX),
        _m("thorax_lift_top_cm", "cm", ("address", "top"), partial(displacement_cm, joints=THORAX, zero="address", at="top", axis=1, sign=-1.0), views_default=("face_on", "down_the_line"), definition="subida del centro de hombros address→top", joints=THORAX),
        _m("pelvis_thrust_top_cm", "cm", ("address", "top"), partial(displacement_cm, joints=PELVIS, zero="address", at="top", axis=0), views_default=("down_the_line",), definition="desplazamiento del centro de caderas hacia/desde la pelota address→top, x de imagen en down_the_line", joints=PELVIS),
        _m("head_sway_top_cm", "cm", ("address", "top"), partial(displacement_cm, joints=HEAD, zero="address", at="top", axis=0), views_default=("face_on",), definition="desplazamiento lateral de la cabeza address→top", joints=HEAD),
        _m("head_lift_top_cm", "cm", ("address", "top"), partial(displacement_cm, joints=HEAD, zero="address", at="top", axis=1, sign=-1.0), views_default=("face_on", "down_the_line"), definition="subida de la cabeza address→top", joints=HEAD),
        _m("lead_knee_flexion_delta_top_deg", "deg", ("address", "top"), partial(angle_delta_deg, a=H.LEFT_HIP, b=H.LEFT_KNEE, c=H.LEFT_ANKLE, zero="address", at="top"), views_default=("face_on",), definition="ángulo de rodilla izquierda (cadera–rodilla–tobillo) en top menos en address; delta, nunca absoluto (ADR-007)", joints=(H.LEFT_HIP, H.LEFT_KNEE, H.LEFT_ANKLE)),
        _m("trail_knee_flexion_delta_top_deg", "deg", ("address", "top"), partial(angle_delta_deg, a=H.RIGHT_HIP, b=H.RIGHT_KNEE, c=H.RIGHT_ANKLE, zero="address", at="top"), views_default=("face_on",), definition="ídem rodilla derecha", joints=(H.RIGHT_HIP, H.RIGHT_KNEE, H.RIGHT_ANKLE)),
    ]
    for metric, j in specs:
        if metric is None:
            continue
        reg.register(metric)
        joints[metric.id] = j
    return reg, joints


REGISTRY, JOINTS = build_registry()
