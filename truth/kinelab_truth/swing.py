"""Swing paramétrico en 3D con verdades conocidas. La misma línea de tiempo del
swing sintético 2-D de tests/helpers/synth_swing.py, ahora con un cuerpo
articulado: giro de pelvis y tórax, sway/lift/thrust, cabeza, rodillas y el
arco de las manos en un plano inclinado.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from kinelab.perception.keypoints import J
from kinelab_truth.chain import Body, skeleton


def angle3d(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Ángulo anatómico en `b` en 3-D, grados. (El `angle_deg` del motor es 2-D: mide lo que la cámara ve.)"""
    v1, v2 = a - b, c - b
    return float(np.degrees(np.arctan2(np.linalg.norm(np.cross(v1, v2)), np.dot(v1, v2))))


def smoothstep(u: np.ndarray) -> np.ndarray:
    u = np.clip(u, 0.0, 1.0)
    return u * u * (3.0 - 2.0 * u)


@dataclass
class SwingParams:
    """Magnitudes verdaderas del swing sintético. Se eligen MAYORES que la tolerancia de sesgo
    del arnés para que una métrica ciega (que mide cero) no pase por válida."""

    height_m: float = 1.80
    still_s: float = 1.0
    backswing_s: float = 0.90
    downswing_s: float = 0.27
    follow_s: float = 0.60
    pelvis_rot_top_deg: float = 45.0
    thorax_rot_top_deg: float = 90.0
    pelvis_sway_top_cm: float = -3.0  # negativo = hacia el lado trasero (−x)
    pelvis_sway_impact_cm: float = 5.0
    pelvis_lift_top_cm: float = 3.0
    pelvis_thrust_top_cm: float = -4.0  # negativo = se aleja de la pelota
    thorax_sway_top_cm: float = -6.0
    thorax_lift_top_cm: float = 4.0
    head_sway_top_cm: float = -6.0
    head_lift_top_cm: float = 3.0
    forward_bend_deg: float = 35.0
    knee_angle_address_deg: float = 155.0
    lead_knee_delta_top_deg: float = 8.0  # la rodilla delantera se extiende en el top
    trail_knee_delta_top_deg: float = -3.0
    swing_plane_deg: float = 55.0  # inclinación del plano de las manos respecto de la horizontal
    arm_reach_frac: float = 0.55  # radio del arco de las manos / estatura
    # Amplitud del arco de las manos, en grados de ángulo recorrido. Dos ramas porque el
    # perfil `p` es positivo en el backswing y negativo en el acompañamiento. Eran dos
    # constantes quemadas; son parámetros para poder fijar la velocidad angular del brazo
    # (el barrido de ganancia las escala, ver `gain_params`).
    arm_arc_top_deg: float = 120.0
    arm_arc_end_deg: float = 125.0


@dataclass
class TruthSwing:
    points_m: np.ndarray  # (T,J,3)
    timestamps_s: np.ndarray
    fps: float
    events: dict[str, int]
    truth: dict[str, float]  # id de métrica → valor verdadero (cm, ms, deg)
    params: SwingParams = field(repr=False)


def _profile(params: SwingParams, fps: float) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    p_ = params
    D = p_.downswing_s + p_.follow_s
    total = p_.still_s + p_.backswing_s + D + p_.still_s
    T = int(round(total * fps))
    t = np.arange(T) / fps
    a, b, c = p_.still_s, p_.still_s + p_.backswing_s, p_.still_s + p_.backswing_s + D
    p = np.zeros(T)
    back = (t >= a) & (t < b)
    p[back] = smoothstep((t[back] - a) / p_.backswing_s)
    down = (t >= b) & (t < c)
    p[down] = 1.0 - 1.8 * smoothstep((t[down] - b) / D)
    p[t >= c] = -0.8
    i_down = np.flatnonzero(down)
    impact = int(i_down[np.argmax(p[i_down] <= 0.0)])
    events = {"address": int(np.flatnonzero(t < a)[-1]), "top": int(i_down[0]), "impact": impact, "follow_end": int(np.flatnonzero(t >= c)[0])}
    return t, p, events


def truth_swing(params: SwingParams = SwingParams(), fps: float = 240.0) -> TruthSwing:
    t, p, events = _profile(params, fps)
    body = Body(params.height_m)
    T = t.size
    pts = np.zeros((T, J, 3))
    pel0 = np.array([0.0, body.L("foot_h") + body.L("thigh") + body.L("shank") - 0.02, 0.0])  # rodillas casi extendidas
    # perfiles: backswing usa p∈[0,1]; downswing hacia impacto usa q = 1−p entre top e impacto
    for i in range(T):
        pi = float(p[i])
        up = max(pi, 0.0)  # fracción de backswing
        if i <= events["top"]:
            sway = params.pelvis_sway_top_cm * up
            lift = params.pelvis_lift_top_cm * up
            thrust = params.pelvis_thrust_top_cm * up
            tsway, tlift = params.thorax_sway_top_cm * up, params.thorax_lift_top_cm * up
            hsway, hlift = params.head_sway_top_cm * up, params.head_lift_top_cm * up
            lead_d, trail_d = params.lead_knee_delta_top_deg * up, params.trail_knee_delta_top_deg * up
        else:
            q = float(np.clip((1.0 - pi) / 1.0, 0.0, 1.0)) if pi >= 0 else 1.0  # 0 en top, 1 en impacto y después
            sway = params.pelvis_sway_top_cm + (params.pelvis_sway_impact_cm - params.pelvis_sway_top_cm) * q
            lift = params.pelvis_lift_top_cm * (1 - q)
            thrust = params.pelvis_thrust_top_cm * (1 - q)
            tsway, tlift = params.thorax_sway_top_cm * (1 - q), params.thorax_lift_top_cm * (1 - q)
            hsway, hlift = params.head_sway_top_cm * (1 - q), params.head_lift_top_cm * (1 - q)
            lead_d, trail_d = params.lead_knee_delta_top_deg * (1 - q), params.trail_knee_delta_top_deg * (1 - q)
        pelvis = pel0 + np.array([sway, lift, thrust]) / 100.0
        yaw_p = params.pelvis_rot_top_deg * pi
        yaw_t = params.thorax_rot_top_deg * pi
        # manos: arco en un plano inclinado, ángulo α(p): 0 en address (colgando), 120° en top, −100° al final
        alpha = np.radians(params.arm_arc_top_deg * pi if pi >= 0 else params.arm_arc_end_deg * pi)
        beta = np.radians(params.swing_plane_deg)
        thorax_c = pelvis + body.L("trunk") * np.array([0.0, np.cos(np.radians(params.forward_bend_deg)), np.sin(np.radians(params.forward_bend_deg))])
        down_dir = np.array([0.0, -np.cos(beta), np.sin(beta)])
        r = params.arm_reach_frac * params.height_m
        hands = thorax_c + r * (np.cos(alpha) * down_dir - np.sin(alpha) * np.array([1.0, 0.0, 0.0]))
        # desplazamientos de tórax/cabeza respecto de la pelvis (además de lo que el giro produce)
        pts[i] = skeleton(body, pelvis=pelvis, pelvis_yaw=yaw_p, thorax_yaw=yaw_t, forward_bend=params.forward_bend_deg, hands=hands, knee_angles=(params.knee_angle_address_deg + lead_d, params.knee_angle_address_deg + trail_d))
        from kinelab.perception.keypoints import H  # local: evita el ciclo en el import del módulo

        extra_t = np.array([tsway - sway, tlift - lift, 0.0]) / 100.0
        extra_h = np.array([hsway - sway, hlift - lift, 0.0]) / 100.0
        for k in (H.LEFT_SHOULDER, H.RIGHT_SHOULDER, H.NECK):
            pts[i, k] += extra_t
        for k in (H.HEAD, H.NOSE, H.LEFT_EYE, H.RIGHT_EYE, H.LEFT_EAR, H.RIGHT_EAR):
            pts[i, k] += extra_h
    from kinelab.perception.keypoints import H

    a, tp = events["address"], events["top"]
    def knee(side_hip, side_knee, side_ankle, f):
        return angle3d(pts[f, side_hip], pts[f, side_knee], pts[f, side_ankle])
    truth = {
        "backswing_duration_ms": (events["top"] - events["address"]) / fps * 1000.0,
        "downswing_duration_ms": (events["impact"] - events["top"]) / fps * 1000.0,
        "tempo_ratio": (events["top"] - events["address"]) / max(events["impact"] - events["top"], 1),
        "follow_duration_ms": (events["follow_end"] - events["impact"]) / fps * 1000.0,
        "pelvis_sway_top_cm": params.pelvis_sway_top_cm,
        "pelvis_sway_impact_cm": params.pelvis_sway_impact_cm,
        "pelvis_lift_top_cm": params.pelvis_lift_top_cm,
        "pelvis_thrust_top_cm": params.pelvis_thrust_top_cm,
        "thorax_sway_top_cm": params.thorax_sway_top_cm,
        "thorax_lift_top_cm": params.thorax_lift_top_cm,
        "head_sway_top_cm": params.head_sway_top_cm,
        "head_lift_top_cm": params.head_lift_top_cm,
        # las rodillas salen de la geometría real de la cadena (la cadera baja al flexionar)
        "lead_knee_flexion_delta_top_deg": knee(H.LEFT_HIP, H.LEFT_KNEE, H.LEFT_ANKLE, tp) - knee(H.LEFT_HIP, H.LEFT_KNEE, H.LEFT_ANKLE, a),
        "trail_knee_flexion_delta_top_deg": knee(H.RIGHT_HIP, H.RIGHT_KNEE, H.RIGHT_ANKLE, tp) - knee(H.RIGHT_HIP, H.RIGHT_KNEE, H.RIGHT_ANKLE, a),
    }
    return TruthSwing(points_m=pts, timestamps_s=t, fps=fps, events=events, truth=truth, params=params)


def segment_rate_3d(points_m: np.ndarray, i: int, j: int, fps: float) -> np.ndarray:
    """Velocidad angular 3-D de la línea `i→j`, en °/s, cuadro a cuadro.

    Es `|dû/dt|` con `û` la dirección unitaria del segmento: la rapidez con que la
    línea cambia de orientación en el espacio. Una línea no tiene giro sobre su
    propio eje, así que esto es TODA su velocidad angular, y es la verdad contra la
    que se compara `kinelab.metrics.generic.line_angle_rate`, que mide lo mismo
    pero sobre la proyección en el plano de imagen.
    """
    d = points_m[:, j] - points_m[:, i]
    n = np.linalg.norm(d, axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        u = d / n
    du = np.gradient(u, axis=0) * fps
    w = np.degrees(np.linalg.norm(du, axis=1))
    w[(n[:, 0] <= 0) | ~np.isfinite(n[:, 0])] = np.nan
    return w


def truth_gain(sw: TruthSwing, segments: dict[str, tuple[int, int]], *, start: int | None = None, end: int | None = None) -> dict:
    """Picos de velocidad angular 3-D por segmento y sus cocientes consecutivos.

    La ventana es la misma que usa el motor para la ganancia: de `address` a
    `follow_end` (`kinelab/analysis.py`). Los nombres de `segments` van en orden
    proximal→distal y los cocientes se arman entre consecutivos, igual que
    `metrics.generic.gain`, para que verdad y medición sean comparables término a
    término.
    """
    a = sw.events["address"] if start is None else int(start)
    b = sw.events["follow_end"] if end is None else int(end)
    peaks: dict[str, float] = {}
    frames: dict[str, int] = {}
    for name, (i, j) in segments.items():
        w = segment_rate_3d(sw.points_m, i, j, sw.fps)[a : b + 1]
        if not np.isfinite(w).any():
            continue
        k = int(np.nanargmax(w))
        peaks[name] = float(w[k])
        frames[name] = a + k
    names = list(segments)
    ratios = {f"{x}_to_{y}": peaks[y] / peaks[x] for x, y in zip(names, names[1:]) if peaks.get(x)}
    return {"peaks_deg_s": {k: round(v, 1) for k, v in peaks.items()}, "peak_frames": frames, "ratios": {k: round(v, 4) for k, v in ratios.items()}}


def gain_params(targets: dict[str, float], segments: dict[str, tuple[int, int]], *, base: SwingParams | None = None, fps: float = 240.0, iters: int = 8) -> tuple[SwingParams, dict]:
    """Un swing con cocientes de velocidad angular 3-D **conocidos**.

    `targets` lleva los mismos nombres que `truth_gain().ratios`
    (`pelvis_to_torso`, `torso_to_arm`). El giro del tórax sale exacto —la pelvis y
    el tórax comparten el perfil temporal, así que el cociente de picos es el de
    amplitudes—; la amplitud del arco de las manos se resuelve iterando, porque el
    hombro está desplazado del centro del arco y la línea hombro→muñeca no gira
    exactamente como el arco. Devuelve los parámetros y lo que efectivamente se
    consiguió, que es la verdad que se reporta (nunca el objetivo pedido).
    """
    p = base or SwingParams()
    names = list(segments)
    if len(names) >= 2 and f"{names[0]}_to_{names[1]}" in targets:
        p = replace(p, thorax_rot_top_deg=p.pelvis_rot_top_deg * float(targets[f"{names[0]}_to_{names[1]}"]))
    key = f"{names[1]}_to_{names[2]}" if len(names) >= 3 else None
    achieved = truth_gain(truth_swing(p, fps=fps), segments)
    if key is not None and key in targets:
        for _ in range(iters):
            got = achieved["ratios"].get(key)
            if not got:
                break
            scale = float(targets[key]) / got
            if abs(scale - 1.0) < 1e-4:
                break
            p = replace(p, arm_arc_top_deg=p.arm_arc_top_deg * scale, arm_arc_end_deg=p.arm_arc_end_deg * scale)
            achieved = truth_gain(truth_swing(p, fps=fps), segments)
    return p, achieved
