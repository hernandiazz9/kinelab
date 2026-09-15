"""El mocap de CMU: el parser, el mapeo a Halpe26 y la cámara virtual.

El parser se prueba con un ASF/AMC mínimo escrito acá, cuya cinemática se puede
verificar a mano. El mapeo y la proyección, con los archivos de verdad de
`data/examples/cmu-mocap/`, que viajan con el repo (no hay descarga en los tests).
"""

from __future__ import annotations

import numpy as np
import pytest

from kinelab.perception.keypoints import H, J
from kinelab_truth.camera import project, view_extrinsics
from kinelab_truth.mocap import (
    CMU_FPS,
    DIRECT,
    EXAMPLES,
    build,
    euler_xyz,
    events_3d,
    fit_intrinsics,
    forward_kinematics,
    parse_amc,
    parse_asf,
    stature_m,
    to_halpe26,
    to_harness_frame,
)

# Un esqueleto de dos huesos: uno vertical de 10 unidades sin grados de libertad,
# y otro de 5 que gira alrededor de x. Con `:units length 0.5`, una unidad son
# 2 pulgadas = 0,0508 m (la regla de CMU: pulgadas × units).
MINI_ASF = """# comentario que hay que ignorar
:version 1.10
:units
  mass 1.0
  length 0.5
  angle deg
:root
   order TX TY TZ RX RY RZ
   axis XYZ
   position 0 0 0
   orientation 0 0 0
:bonedata
  begin
     id 1
     name torre
     direction 0 1 0
     length 10.0
     axis 0 0 0  XYZ
  end
  begin
     id 2
     name brazo
     direction 0 1 0
     length 5.0
     axis 0 0 0  XYZ
    dof rx
    limits (-180.0 180.0)
  end
:hierarchy
  begin
    root torre
    torre brazo
  end
"""

MINI_AMC = """#!OML:ASF mini
:FULLY-SPECIFIED
:DEGREES
1
root 0 0 0 0 0 0
brazo 0
2
root 1 2 3 0 0 0
brazo 90
"""


def test_parser_minimo_y_cinematica_directa():
    skel = parse_asf(MINI_ASF)
    assert skel.units_length == 0.5
    assert skel.scale_m == pytest.approx(0.0254 / 0.5)
    assert set(skel.bones) == {"torre", "brazo"}
    assert skel.bones["brazo"].dof == ("rx",)
    assert skel.children == {"root": ["torre"], "torre": ["brazo"]}

    frames = parse_amc(MINI_AMC)
    assert len(frames) == 2
    assert frames[1]["root"] == [1.0, 2.0, 3.0, 0.0, 0.0, 0.0]

    pos, rot = forward_kinematics(skel, frames)
    u = skel.scale_m
    # cuadro 1: todo en reposo, la torre termina 10 unidades arriba y el brazo 5 más
    assert pos["torre"][0] == pytest.approx([0.0, 10 * u, 0.0], abs=1e-9)
    assert pos["brazo"][0] == pytest.approx([0.0, 15 * u, 0.0], abs=1e-9)
    # cuadro 2: la raíz se traslada (en unidades del archivo) y el brazo gira 90° en x:
    # lo que apuntaba a +y pasa a apuntar a +z
    assert pos["torre"][1] == pytest.approx([1 * u, 12 * u, 3 * u], abs=1e-9)
    assert pos["brazo"][1] == pytest.approx([1 * u, 12 * u, (3 + 5) * u], abs=1e-9)


def test_amc_con_hueco_de_cuadros_se_rechaza():
    with pytest.raises(ValueError, match="hueco"):
        parse_amc(MINI_AMC.replace("\n2\n", "\n4\n"))


def test_euler_es_rz_ry_rx_y_no_al_reves():
    # 90° en x lleva +y a +z; 90° en y lleva +z a +x. El orden importa: con el
    # orden invertido el resultado de aplicar las dos no es el mismo.
    assert euler_xyz(90, 0, 0) @ np.array([0.0, 1.0, 0.0]) == pytest.approx([0, 0, 1], abs=1e-9)
    assert euler_xyz(0, 90, 0) @ np.array([0.0, 0.0, 1.0]) == pytest.approx([1, 0, 0], abs=1e-9)
    directa = euler_xyz(90, 90, 0) @ np.array([0.0, 1.0, 0.0])
    invertida = (euler_xyz(90, 0, 0) @ euler_xyz(0, 90, 0)) @ np.array([0.0, 1.0, 0.0])
    assert not np.allclose(directa, invertida)


def _cmu():
    skel = parse_asf((EXAMPLES / "64.asf").read_text(encoding="utf-8"))
    frames = parse_amc((EXAMPLES / "64_01.amc").read_text(encoding="utf-8"))
    return skel, frames


def test_mapeo_da_26_puntos_finitos_con_las_simetrias_bien():
    skel, frames = _cmu()
    pos, rot = forward_kinematics(skel, frames)
    P = to_halpe26(pos, rot)
    assert P.shape == (len(frames), J, 3)
    assert np.isfinite(P).all()
    assert len(DIRECT) == 16  # los que son la misma articulación en los dos esqueletos

    f = 0  # address: el sujeto está parado y quieto
    # Los cuatro pares laterales apuntan todos para el MISMO lado. Si el mapeo
    # cruzara izquierda y derecha en uno solo, este producto daría negativo
    # (invariante 15 de CONTEXTO.md).
    caderas = P[f, H.LEFT_HIP] - P[f, H.RIGHT_HIP]
    for a, b in ((H.LEFT_SHOULDER, H.RIGHT_SHOULDER), (H.LEFT_ANKLE, H.RIGHT_ANKLE), (H.LEFT_KNEE, H.RIGHT_KNEE), (H.LEFT_EAR, H.RIGHT_EAR)):
        assert float((P[f, a] - P[f, b]) @ caderas) > 0
    # El centro es el centro: `hip` en el medio de las dos caderas.
    assert P[f, H.HIP] == pytest.approx((P[f, H.LEFT_HIP] + P[f, H.RIGHT_HIP]) / 2, abs=1e-9)
    # Cadena vertical: coronilla arriba del cuello, cuello arriba de las caderas,
    # caderas arriba de las rodillas, rodillas arriba de los tobillos.
    assert P[f, H.HEAD, 1] > P[f, H.NECK, 1] > P[f, H.HIP, 1] > P[f, H.LEFT_KNEE, 1] > P[f, H.LEFT_ANKLE, 1]
    # Talones detrás de las puntas, los dos casi a la altura del piso.
    for heel, toe, ankle in ((H.LEFT_HEEL, H.LEFT_BIG_TOE, H.LEFT_ANKLE), (H.RIGHT_HEEL, H.RIGHT_BIG_TOE, H.RIGHT_ANKLE)):
        fwd = P[f, toe] - P[f, ankle]
        assert float((P[f, heel] - P[f, ankle]) @ fwd) < 0
        assert P[f, heel, 1] < P[f, ankle, 1]
    # Puntas chicas por fuera de las grandes (más lejos del eje del cuerpo).
    centro = P[f, H.HIP]
    for big, small in ((H.LEFT_BIG_TOE, H.LEFT_SMALL_TOE), (H.RIGHT_BIG_TOE, H.RIGHT_SMALL_TOE)):
        assert np.linalg.norm(P[f, small, [0, 2]] - centro[[0, 2]]) > np.linalg.norm(P[f, big, [0, 2]] - centro[[0, 2]])


def test_estatura_sale_de_los_huesos_y_es_plausible():
    skel, _ = _cmu()
    h = stature_m(skel)
    assert 1.5 < h < 1.9
    # sale del esqueleto, no del trial: no depende de qué cuadros haya
    assert stature_m(skel) == h


def test_marco_del_arnes_pone_el_suelo_en_cero_y_la_izquierda_hacia_el_objetivo():
    skel, frames = _cmu()
    pos, rot = forward_kinematics(skel, frames)
    P = to_halpe26(pos, rot)
    Q, R = to_harness_frame(P, 65)
    assert np.nanmin(Q[..., 1]) == pytest.approx(0.0, abs=1e-9)
    assert R @ R.T == pytest.approx(np.eye(3), abs=1e-9)
    assert float(np.linalg.det(R)) == pytest.approx(1.0, abs=1e-9)  # sin espejar
    # x del arnés = hacia el objetivo = del lado de la cadera izquierda del golfista
    assert Q[65, H.LEFT_HIP, 0] > Q[65, H.RIGHT_HIP, 0]
    # y del arnés sigue siendo la vertical: la coronilla arriba de los tobillos
    assert Q[65, H.HEAD, 1] > Q[65, H.LEFT_ANKLE, 1]


def test_la_proyeccion_cae_donde_dice_la_camara():
    skel, frames = _cmu()
    pos, rot = forward_kinematics(skel, frames)
    Q, _ = to_harness_frame(to_halpe26(pos, rot), 65)
    intr, extr, px, bh = fit_intrinsics(Q, "face_on", width=1080, height=1920, body_frac=0.80, distance_m=3.0, camera_height_m=1.2)
    # el encuadre que pidió el encargo: el cuerpo al 80 % del alto del cuadro
    assert bh == pytest.approx(0.80 * 1920, abs=1.0)
    assert intr.width == 1080 and intr.height == 1920 and intr.cx == 540 and intr.cy == 960
    # un punto conocido: 1 m hacia el objetivo (+x) a la altura a la que mira la
    # cámara cae a f/d px a la derecha del centro, y en el centro vertical
    mira = extr.target[1]
    p = project(np.array([[[1.0, float(mira), 0.0]]]), intr, extr)[0, 0]
    assert p[0] == pytest.approx(540 + intr.fx / 3.0, rel=0.02)
    assert p[1] == pytest.approx(960, abs=1.0)
    # más alto = y de imagen menor (image_px, y hacia abajo)
    arriba = project(np.array([[[0.0, float(mira) + 0.5, 0.0]]]), intr, extr)[0, 0]
    assert arriba[1] < 960
    # y todo el sujeto entra en el cuadro
    assert px[..., 0].min() >= 0 and px[..., 0].max() <= 1080
    assert px[..., 1].min() >= 0 and px[..., 1].max() <= 1920


def test_down_the_line_mira_desde_atras_y_no_espeja():
    skel, frames = _cmu()
    pos, rot = forward_kinematics(skel, frames)
    Q, _ = to_harness_frame(to_halpe26(pos, rot), 65)
    face = project(Q[65:66], *fit_intrinsics(Q, "face_on", width=1080, height=1920, body_frac=0.8, distance_m=3.0, camera_height_m=1.2)[:2])[0]
    dtl = project(Q[65:66], *fit_intrinsics(Q, "down_the_line", width=1080, height=1920, body_frac=0.8, distance_m=3.0, camera_height_m=1.2)[:2])[0]
    # de frente, la cadera izquierda (hacia el objetivo) cae a la DERECHA de la imagen
    assert face[H.LEFT_HIP, 0] > face[H.RIGHT_HIP, 0]
    # desde atrás sobre la línea de tiro, las dos caderas quedan casi encimadas
    # en x y la pelota (z del mundo) es la x de la imagen
    assert abs(dtl[H.LEFT_HIP, 0] - dtl[H.RIGHT_HIP, 0]) < abs(face[H.LEFT_HIP, 0] - face[H.RIGHT_HIP, 0]) / 3


def test_pose_completa_y_eventos_3d_del_trial_de_golf():
    mp = build("64_01", "face_on")
    assert mp.provenance["source"] == "cmu-mocap"
    assert mp.provenance["trial"] == "64_01"
    assert mp.provenance["fps_real"] == CMU_FPS == 120.0
    assert mp.provenance["camera"]["provenance"] == "sin_verificar"
    assert mp.provenance["model"] is None and mp.provenance["detector"] is None
    assert mp.keypoints_px.shape == (448, J, 2)
    e = events_3d(mp.points_m)
    assert e["address"] < e["top_height"] <= e["top_far"] < e["impact"]
    # el swing entero entra en el trial: hay quietud antes del takeaway y
    # medio segundo largo de bajada
    assert e["address"] > int(0.5 * CMU_FPS)
    assert (e["impact"] - e["top_far"]) / CMU_FPS > 0.2


def test_la_altura_cabeza_tobillos_del_address_no_es_la_estatura():
    """El origen del +12,3 %: un golfista en address mide, de la coronilla a los
    tobillos, bastante menos que de pie. Es lo que la escala vieja usaba de
    divisor (encargo 14)."""
    mp = build("64_01", "face_on")
    P = mp.points_m
    address = events_3d(P)["address"]
    tobillos = (P[address, H.LEFT_ANKLE, 1] + P[address, H.RIGHT_ANKLE, 1]) / 2.0
    aparente = float(P[address, H.HEAD, 1] - tobillos)
    assert aparente == pytest.approx(1.4554, abs=0.005)
    assert mp.height_m == pytest.approx(1.6405, abs=0.005)
    assert aparente / mp.height_m == pytest.approx(0.887, abs=0.01)


def test_las_candidatas_de_escala_se_ordenan_como_dice_la_geometria():
    """Cada eslabón se acorta con la perspectiva y nunca se alarga, así que la
    cadena es una cota inferior de la estatura en px: el máximo dentro de la
    repetición tiene que quedar entre el address y la escala exacta."""
    from kinelab_truth.mocap import _scale_divisors

    mp = build("64_01", "face_on")
    kp = mp.keypoints_px.astype(float)
    address = events_3d(mp.points_m)["address"]
    tobillos = (mp.points_m[address, H.LEFT_ANKLE, 1] + mp.points_m[address, H.RIGHT_ANKLE, 1]) / 2.0
    cociente = float(mp.points_m[address, H.HEAD, 1] - tobillos) / float(mp.height_m)
    d = _scale_divisors(kp, CMU_FPS, address, address, kp.shape[0] - 1, cociente)
    # agacharse hacia la cámara acorta la cadena tanto como la vertical: en el
    # address las dos primeras candidatas son la misma cosa
    assert d["b_cadena_address"] == pytest.approx(d["a_cabeza_tobillos_address"], rel=0.005)
    # el máximo dentro de la repetición recupera parte de lo que la postura comió
    assert d["a_cabeza_tobillos_address"] < d["c_vertical_max_rep"] < d["d_cadena_max_rep"] < d["z_escala_exacta"]
    # y llega al 95 % de la escala exacta, contra el 89 % del address
    assert d["d_cadena_max_rep"] / d["z_escala_exacta"] > 0.95
    assert d["a_cabeza_tobillos_address"] / d["z_escala_exacta"] == pytest.approx(0.887, abs=0.01)


def test_tabla_de_escala_sobre_dos_trials():
    """La tabla que decidió la convención, en chico: la candidata implementada
    tiene que bajar el sesgo medio contra la verdad 3-D."""
    from kinelab_truth.mocap import scale_table

    t = scale_table("64", "face_on", trials=["64_01", "64_02"])
    assert t["n_trials"] == 2 and t["n_sujetos"] == 1
    assert 0.85 < t["aparente_sobre_estatura"]["media"] < 0.92
    actual = t["resumen"]["a_cabeza_tobillos_address"]["sesgo_abs_medio"]
    nueva = t["resumen"]["d_cadena_max_rep"]["sesgo_abs_medio"]
    assert nueva < actual / 2
    assert t["resumen"]["d_cadena_max_rep"]["empeora_mas_cm"] <= 1.0
    # las siete de `face_on`: la de thrust es de down_the_line y no entra
    fila = t["trials"][0]["metricas"]
    assert len(fila) == 7 and "pelvis_thrust_top_cm" not in fila
    # el `motor_cm` del analysis.json es el de la convención implementada
    for mid, m in fila.items():
        assert m["motor_cm"] == pytest.approx(m["cm"]["d_cadena_max_rep"], abs=0.06), mid
