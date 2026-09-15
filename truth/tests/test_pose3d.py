"""`pose3d.json`: el mismo swing que el `pose.npz`, con la profundidad adentro.

La prueba que importa es `test_proyectar_el_pose3d_reproduce_el_pose_npz`: la
proyección se rehace **a mano**, con la receta que el propio archivo declara en
`camaras.<vista>.modelo`, sin `cv2` y sin `camera.py`. Es el mismo código que
hay que escribir en TypeScript para el visor de la pantalla, así que si el
visor y el arnés no coinciden, este test lo dice antes. Lo mismo con el
indicador de líneas colapsadas: la fórmula se rehace acá y el número medido en
el encargo 13 —la línea de caderas apuntando a la cámara desde
`down_the_line`— tiene que reproducirse.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from kinelab.perception.keypoints import H, J
from kinelab_truth.camera import view_extrinsics
from kinelab_truth.mocap import (
    CMU_FPS,
    POSE3D_JSON,
    VIEWS,
    build,
    write_pose,
    write_pose3d,
)

TRIAL = "64_01"


# --- la receta del archivo, rehecha a mano -----------------------------------


def _rt(cam: dict) -> tuple[np.ndarray, np.ndarray]:
    """`R` y la posición, tal como lo dice `camaras.<vista>.modelo`."""
    pos = np.asarray(cam["posicion_m"], float)
    f = np.asarray(cam["objetivo_m"], float) - pos
    f = f / np.linalg.norm(f)
    r = np.cross(f, np.array([0.0, 1.0, 0.0]))
    r = r / np.linalg.norm(r)
    d = np.cross(f, r)
    return np.stack([r, d, f]), pos


def proyectar(puntos_m: np.ndarray, cam: dict) -> np.ndarray:
    """(...,3) metros → (...,2) píxeles. Sin OpenCV y sin `camera.project`."""
    R, pos = _rt(cam)
    p = (np.asarray(puntos_m, float) - pos) @ R.T
    u = cam["fx"] * p[..., 0] / p[..., 2] + cam["cx"]
    v = cam["fy"] * p[..., 1] / p[..., 2] + cam["cy"]
    return np.stack([u, v], axis=-1)


def frac_proyectada(puntos_m: np.ndarray, cam: dict, frame: int, a: int, b: int, f: float | None = None) -> float:
    """El indicador: cuánto mide la línea `a`–`b` en la imagen comparada con lo
    que mide de verdad, según `indicador.definicion` del archivo.

    `f` es la focal con la que se mira (el zoom del visor); el resultado no
    tiene que depender de ella."""
    f = float(cam["fx"] if f is None else f)
    R, pos = _rt(cam)
    p = (puntos_m[frame, [a, b]] - pos) @ R.T
    px = proyectar(puntos_m[frame, [a, b]], {**cam, "fx": f, "fy": f})
    largo_px = float(np.linalg.norm(px[0] - px[1]))
    largo_m = float(np.linalg.norm(puntos_m[frame, a] - puntos_m[frame, b]))
    z = float(p[:, 2].mean())
    return largo_px * z / (f * largo_m)


# --- fixtures ----------------------------------------------------------------


@pytest.fixture(scope="module")
def tomas(tmp_path_factory) -> dict:
    """Las dos vistas del mismo trial, cada una con su `pose.npz` en disco y su
    `pose3d.json`. Una sola vez por módulo: cada `build` es ~1,5 s."""
    from kinelab.perception.posestore import load_pose

    out = {}
    for view in VIEWS:
        d = tmp_path_factory.mktemp(view)
        mp = build(TRIAL, view)
        write_pose(mp, d)
        write_pose3d(mp, d, events={"address": 141, "top": 270, "impact": 329})
        out[view] = {
            "mp": mp,
            "dir": d,
            "npz": load_pose(d),
            "json": json.loads((d / POSE3D_JSON).read_text(encoding="utf-8")),
        }
    return out


# --- el archivo --------------------------------------------------------------


def test_el_archivo_declara_marco_unidades_y_26_puntos_finitos(tomas):
    d = tomas["face_on"]["json"]
    # el marco y las unidades van como DATO, no como comentario (CONTEXTO.md)
    assert d["marco"]["unidades"] == "m"
    assert d["marco"]["id"] == "harness_world_m"
    assert set(d["marco"]["ejes"]) == {"x", "y", "z"}
    assert "objetivo" in d["marco"]["ejes"]["x"] and "arriba" in d["marco"]["ejes"]["y"]
    assert d["fps"] == CMU_FPS == 120.0
    assert len(d["nombres"]) == J == 26
    P = np.asarray(d["puntos"], float)
    assert P.shape == (d["frames"], J, 3) == (448, 26, 3)
    assert np.isfinite(P).all()  # `NaN` no es JSON
    # tres decimales, ni más ni menos: milímetros
    assert d["decimales"] == 3
    assert np.abs(P * 1000 - np.round(P * 1000)).max() < 1e-9
    # los diez puntos que no existen en CMU dicen cómo se construyeron
    assert set(d["puntos_construidos"]) >= {"hip", "neck", "head", "cara", "talones", "puntas"}
    assert d["atribucion"].startswith("The data used in this project was obtained from mocap.cs.cmu.edu")
    for k in ("fuente", "no_es_video", "no_con_un_celular"):
        assert len(d["rotulos"][k]) > 40


def test_los_eventos_son_los_que_le_pasan_y_nunca_se_inventan(tomas, tmp_path):
    assert tomas["face_on"]["json"]["eventos"] == {"address": 141, "top": 270, "impact": 329}
    # sin análisis no hay eventos del motor: `null`, no un número puesto a dedo
    p = write_pose3d(tomas["face_on"]["mp"], tmp_path)
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["eventos"] is None
    # la verdad 3-D va igual, y aparte: es otra cosa que lo que detectó el motor
    assert d["eventos_3d"]["address"] < d["eventos_3d"]["top_far"] < d["eventos_3d"]["impact"]


def test_el_suelo_esta_en_cero_y_el_archivo_dice_donde_cae_ese_cero(tomas):
    """`y = 0` es el punto más bajo de **todo** el trial, y ése no cae en el
    cuadro de referencia: el esqueleto de CMU no apoya la planta del pie. El
    archivo lo dice con el número medido, porque el visor dibuja la grilla ahí
    y los pies del address quedan un poco por encima."""
    d = tomas["face_on"]["json"]
    P = np.asarray(d["puntos"], float)
    ref = d["cuadro_de_referencia"]
    assert P[..., 1].min() == pytest.approx(0.0, abs=1e-3)  # el redondeo a mm
    # el punto más bajo es un pie, no la cabeza: y crece hacia ARRIBA
    bajo = d["suelo"]["punto_mas_bajo"]
    assert bajo["nombre"] in ("left_big_toe", "right_big_toe", "left_small_toe", "right_small_toe", "left_heel", "right_heel")
    assert P[bajo["cuadro"], d["nombres"].index(bajo["nombre"]), 1] == pytest.approx(0.0, abs=1e-3)
    assert P[ref, H.HEAD, 1] > 1.3
    # y lo que el archivo declara de ese cero es lo que se mide en los puntos
    pies = (H.LEFT_HEEL, H.RIGHT_HEEL, H.LEFT_BIG_TOE, H.RIGHT_BIG_TOE, H.LEFT_SMALL_TOE, H.RIGHT_SMALL_TOE)
    assert d["suelo"]["pies_sobre_el_cero_en_el_cuadro_de_referencia_m"] == pytest.approx(float(P[ref, list(pies), 1].min()), abs=2e-3)
    assert 0.0 <= d["suelo"]["pies_sobre_el_cero_en_el_cuadro_de_referencia_m"] < 0.20
    # el origen está entre los tobillos: en el cuadro de referencia, x y z ~0
    assert abs(P[ref, [H.LEFT_ANKLE, H.RIGHT_ANKLE], 0].mean()) < 0.02
    assert abs(P[ref, [H.LEFT_ANKLE, H.RIGHT_ANKLE], 2].mean()) < 0.02
    print(f"\n  pies sobre el cero en el address: {d['suelo']['pies_sobre_el_cero_en_el_cuadro_de_referencia_m']:.3f} m · el cero lo pone {bajo['nombre']} en el cuadro {bajo['cuadro']}")


def test_los_pares_laterales_no_estan_cruzados(tomas):
    """Los cuatro pares izquierda/derecha del tren inferior y superior tienen
    que caer todos del mismo lado del eje x en el cuadro de referencia: x va
    hacia el objetivo y para un golfista diestro su lado izquierdo mira ahí.
    Si el mapeo cruzara **uno solo**, este test falla (invariante 15)."""
    d = tomas["face_on"]["json"]
    P = np.asarray(d["puntos"], float)
    ref = d["cuadro_de_referencia"]
    pares = ((H.LEFT_HIP, H.RIGHT_HIP), (H.LEFT_SHOULDER, H.RIGHT_SHOULDER), (H.LEFT_ANKLE, H.RIGHT_ANKLE), (H.LEFT_KNEE, H.RIGHT_KNEE), (H.LEFT_EAR, H.RIGHT_EAR), (H.LEFT_HEEL, H.RIGHT_HEEL))
    for izq, der in pares:
        assert P[ref, izq, 0] > P[ref, der, 0], f"{d['nombres'][izq]} no está del lado del objetivo respecto de {d['nombres'][der]}"
    # y el centro de cadera está en el medio de las dos caderas, no en una
    assert P[ref, H.HIP, 0] == pytest.approx((P[ref, H.LEFT_HIP, 0] + P[ref, H.RIGHT_HIP, 0]) / 2, abs=2e-3)


# --- la prueba que importa ---------------------------------------------------


def test_proyectar_el_pose3d_reproduce_el_pose_npz_en_las_dos_vistas(tomas):
    """El 3-D del visor y el 2-D del motor son el mismo swing.

    El `pose3d.json` de **cada** vista trae las cámaras de **las dos**, así que
    las cuatro combinaciones se comparan contra el `pose.npz` de la vista
    proyectada. Tolerancia 1 px; lo que sobra es el redondeo a milímetros, que
    a 3 m con una focal de 3078 px vale medio píxel."""
    peores = {}
    for archivo_de in VIEWS:
        P = np.asarray(tomas[archivo_de]["json"]["puntos"], float)
        for vista in VIEWS:
            cam = tomas[archivo_de]["json"]["camaras"][vista]
            esperado = tomas[vista]["npz"].keypoints.astype(float)
            # la distancia en el plano, no el peor eje: es el número que se
            # mide mirando la imagen, y es el más exigente de los dos
            err = np.linalg.norm(proyectar(P, cam) - esperado, axis=-1)
            peores[(archivo_de, vista)] = float(err.max())
            assert err.max() < 1.0, f"{archivo_de} → {vista}: {err.max():.3f} px"
    # y no es que todo dé cero por casualidad: cada vista pone al sujeto en otro lado
    assert max(peores.values()) < 1.0
    print("\n  error máximo de la ida y vuelta, px:", {f"{a}→{b}": round(v, 3) for (a, b), v in peores.items()})


def test_las_camaras_del_archivo_son_las_del_protocolo(tomas):
    for archivo_de in VIEWS:
        cams = tomas[archivo_de]["json"]["camaras"]
        assert set(cams) == set(VIEWS)
        for vista, cam in cams.items():
            extr = view_extrinsics(vista, distance_m=cam["distancia_m"], height_m=cam["altura_camara_m"], look_at_height_m=cam["objetivo_m"][1])
            assert cam["posicion_m"] == pytest.approx(list(extr.position), abs=1e-6)
            assert cam["objetivo_m"] == pytest.approx(list(extr.target), abs=1e-6)
            assert cam["fx"] == pytest.approx(cam["fy"])  # el indicador usa una sola focal
            assert cam["dist"] == [0.0] * 5  # sin distorsión: el visor no la implementa
            assert cam["cx"] == cam["ancho"] / 2 and cam["cy"] == cam["alto"] / 2
            assert cam["cuerpo_frac_del_alto"] == pytest.approx(0.80, abs=0.01)
            assert cam["procedencia"] == "sin_verificar"


def test_la_linea_de_caderas_colapsa_desde_down_the_line_y_no_desde_face_on(tomas):
    """El encargo 13 lo midió en °/s; acá es lo que se ve en la pantalla.

    En el address la línea de caderas apunta al objetivo, que es exactamente el
    eje óptico de `down_the_line`: en la imagen no mide nada. Desde `face_on`
    está de costado y mide casi todo. La de hombros, en el address de este
    golfista, está apenas girada respecto de la de caderas y hace lo mismo."""
    d = tomas["face_on"]["json"]
    P = np.asarray(d["puntos"], float)
    address = d["eventos_3d"]["address"]
    umbral = d["indicador"]["umbral_colapso_frac"]
    fila = {}
    for vista in VIEWS:
        cam = d["camaras"][vista]
        fila[vista] = {n: frac_proyectada(P, cam, address, *idx) for n, idx in (("caderas", (H.LEFT_HIP, H.RIGHT_HIP)), ("hombros", (H.LEFT_SHOULDER, H.RIGHT_SHOULDER)))}
    print("\n  fracción proyectada en el address:", {v: {k: round(x, 4) for k, x in f.items()} for v, f in fila.items()})
    assert fila["face_on"]["caderas"] > 0.9
    assert fila["down_the_line"]["caderas"] < umbral
    assert fila["down_the_line"]["caderas"] < fila["face_on"]["caderas"] / 10
    # en el top las caderas ya giraron: desde `down_the_line` la línea reaparece
    top = d["eventos_3d"]["top_far"]
    en_el_top = frac_proyectada(P, d["camaras"]["down_the_line"], top, H.LEFT_HIP, H.RIGHT_HIP)
    print(f"  caderas desde down_the_line en el top: {en_el_top:.4f}")
    assert en_el_top > fila["down_the_line"]["caderas"] * 3
    # la fracción nunca pasa de 1: una línea no puede medir en la imagen más de
    # lo que mide de verdad a esa distancia (perspectiva aparte, que es chica)
    for f in fila.values():
        for x in f.values():
            assert 0.0 <= x <= 1.02


def test_el_indicador_no_depende_del_zoom_ni_de_la_focal(tomas):
    """`indicador.definicion` dice que sólo depende del ángulo. Si dependiera de
    la focal, acercarse con la rueda del visor cambiaría el porcentaje y el
    número dejaría de querer decir lo que dice."""
    d = tomas["face_on"]["json"]
    P = np.asarray(d["puntos"], float)
    cam = d["camaras"]["face_on"]
    base = frac_proyectada(P, cam, d["eventos_3d"]["top_far"], H.LEFT_HIP, H.RIGHT_HIP)
    for factor in (0.3, 0.5, 2.0, 4.0):
        con_zoom = frac_proyectada(P, cam, d["eventos_3d"]["top_far"], H.LEFT_HIP, H.RIGHT_HIP, f=cam["fx"] * factor)
        assert con_zoom == pytest.approx(base, rel=1e-9), f"con la focal × {factor} el indicador cambió"
