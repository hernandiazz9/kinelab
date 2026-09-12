"""Arnés: la cadena mide lo que dice, la cámara proyecta donde debe, y la tabla sale."""

from __future__ import annotations

import numpy as np
import pytest

from kinelab.perception.keypoints import H
from kinelab_truth.camera import Extrinsics, Intrinsics, project, view_extrinsics
from kinelab_truth.chain import Body, skeleton
from kinelab_truth.harness import NOMINAL, evaluate_condition, sweep_conditions
from kinelab_truth.swing import SwingParams, angle3d, truth_swing


def test_skeleton_height_and_knee_angle():
    body = Body(1.80)
    pelvis = np.array([0.0, body.L("foot_h") + body.L("thigh") + body.L("shank") - 0.02, 0.0])
    P = skeleton(body, pelvis=pelvis, pelvis_yaw=0, thorax_yaw=0, forward_bend=0, hands=np.array([0.0, 0.8, 0.3]), knee_angles=(160, 160))
    height = P[H.HEAD, 1] - P[H.LEFT_ANKLE, 1]
    assert 1.55 < height < 1.85
    assert abs(P[H.LEFT_HIP, 0] - P[H.RIGHT_HIP, 0]) == pytest.approx(body.L("hip_width"), abs=1e-6)
    # la rodilla flexiona hacia +z (la pelota) y el ángulo es coherente con la cadena
    assert P[H.LEFT_KNEE, 2] > 0
    assert 140 < angle3d(P[H.LEFT_HIP], P[H.LEFT_KNEE], P[H.LEFT_ANKLE]) < 179


def test_projection_of_known_point():
    intr = Intrinsics("t", 1920, 1080, 1000.0, 1000.0, 960.0, 540.0, (0, 0, 0, 0, 0), "test")
    extr = view_extrinsics("face_on", distance_m=4.0, height_m=1.0)
    # un punto 1 m a la derecha del origen (hacia +x) y a 1 m de alto, visto de frente: 250 px a la derecha del centro, en el centro vertical
    px = project(np.array([[[1.0, 1.0, 0.0]]]), intr, extr)[0, 0]
    assert px[0] == pytest.approx(960 + 250, abs=0.5)
    assert px[1] == pytest.approx(540, abs=0.5)
    # más alto = y de imagen menor (y hacia abajo)
    up = project(np.array([[[0.0, 1.5, 0.0]]]), intr, extr)[0, 0]
    assert up[1] < 540


def test_truth_swing_events_and_truths():
    sw = truth_swing(SwingParams(), fps=240.0)
    e = sw.events
    assert e["address"] < e["top"] < e["impact"] < e["follow_end"]
    assert sw.truth["backswing_duration_ms"] == pytest.approx(900, abs=5)
    assert sw.truth["pelvis_sway_top_cm"] == -3.0
    assert np.isfinite(sw.points_m).all()


def test_nominal_condition_has_small_bias_for_durations():
    from sports.golf.metrics import JOINTS, REGISTRY

    sw = truth_swing(SwingParams(), fps=240.0)
    from kinelab_truth.camera import load_intrinsics

    rows = evaluate_condition(sw, NOMINAL, load_intrinsics("iphone17pro-1080p120"), REGISTRY, JOINTS, seeds=3)
    assert abs(rows["backswing_duration_ms"]["bias"]) <= 5
    assert rows["pelvis_sway_top_cm"]["mdc"] is not None and rows["pelvis_sway_top_cm"]["mdc"] < 3.0
    assert len(sweep_conditions()) > 20
