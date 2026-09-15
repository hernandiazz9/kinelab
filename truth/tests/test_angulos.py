"""Los ángulos del mocap: en 3-D son verdaderos, proyectados no.

Lo que estos tests fijan, en orden de importancia:

1. **El ángulo 3-D no cambia si se gira la escena entera.** Es lo que lo define
   como ángulo del cuerpo y no de la cámara, y es el test que caza un bug de
   marco: si `angle3_deg` mirara sólo dos componentes, girar 90° lo rompería.
2. **El proyectado sí cambia con la vista**, y en la vista donde el segmento
   apunta a la cámara la diferencia explota. Es el motivo entero del encargo.
3. **Los proyectados de acá son los del motor**, columna por columna: la
   comparación 3-D contra proyección sólo es justa si los tres puntos y la
   fórmula son los mismos, y la forma de garantizarlo es no tener una copia
   sino comparar contra la salida del propio motor.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from kinelab.perception.keypoints import H, HALPE26_NAMES
from kinelab.perception.plausibility import angle_deg
from kinelab_truth.mocap import (
    ANGULOS_DECIMALES,
    CMU_FPS,
    POSE3D_JSON,
    VIEWS,
    _proyectar_con,
    angle3_deg,
    angles_table,
    angulos_3d,
    angulos_doc,
    angulos_proyectados,
    build,
    events_3d,
    write_pose,
    write_pose3d,
)

TRIAL = "64_01"


# --- la fórmula, sobre ángulos construidos a mano ----------------------------


def test_angulos_construidos_dan_el_valor_exacto():
    """Una L de 90°, un brazo a 37° y el barrido de ADR-011, en 3-D y fuera de
    los planos de los ejes: el eje del giro es `(1,1,1)`, así ningún par de
    componentes alcanza para acertar."""
    assert angle3_deg(np.array([1.0, 0.0, 0.0]), np.zeros(3), np.array([0.0, 1.0, 0.0])) == pytest.approx(90.0)
    assert angle3_deg(np.array([0.0, 0.0, 3.0]), np.zeros(3), np.array([0.0, 5.0, 0.0])) == pytest.approx(90.0)
    eje = np.array([1.0, 1.0, 1.0]) / np.sqrt(3)
    u = np.cross(eje, [0.0, 0.0, 1.0])
    u /= np.linalg.norm(u)
    w = np.cross(eje, u)
    for grados in (1.0, 37.0, 90.0, 112.0, 163.0, 179.0, *np.arange(1.0, 180.0, 1.0)):
        r = np.radians(grados)
        b = np.array([0.7, -0.2, 1.3])  # el vértice en cualquier lado: es invariante a traslación
        assert angle3_deg(b + 2.0 * u, b, b + 0.5 * (np.cos(r) * u + np.sin(r) * w)) == pytest.approx(grados, abs=1e-9)
    # simétrico y degenerado, como la del motor
    a, b, c = np.array([1.0, 2.0, 3.0]), np.zeros(3), np.array([0.0, 1.0, 1.0])
    assert angle3_deg(a, b, c) == pytest.approx(angle3_deg(c, b, a))
    assert np.isnan(angle3_deg(b, b, c))


def test_la_formula_3d_es_la_del_motor_cuando_la_z_es_cero():
    """Con `z = 0` las dos definiciones tienen que dar el mismo número: es lo
    que hace que comparar 3-D contra proyección sea comparar la misma cosa."""
    rng = np.random.default_rng(7)
    p = rng.normal(size=(500, 3, 2)) * 3.0
    plano = np.concatenate([p, np.zeros((500, 3, 1))], axis=-1)
    dos_d = np.asarray(angle_deg(p[:, 0], p[:, 1], p[:, 2]), float)
    tres_d = angle3_deg(plano[:, 0], plano[:, 1], plano[:, 2])
    assert np.abs(tres_d - dos_d).max() < 1e-10


# --- sobre el swing real -----------------------------------------------------


@pytest.fixture(scope="module")
def toma(tmp_path_factory) -> dict:
    from kinelab.perception.posestore import load_pose

    d = tmp_path_factory.mktemp("angulos")
    mp = build(TRIAL, "face_on")
    write_pose(mp, d)
    t3 = events_3d(mp.points_m)
    write_pose3d(mp, d, events={"address": 141, "top": 270, "impact": 329})
    return {"mp": mp, "dir": d, "npz": load_pose(d), "json": json.loads((d / POSE3D_JSON).read_text(encoding="utf-8")), "t3": t3}


def test_el_angulo_3d_no_cambia_al_girar_la_escena_entera(toma):
    """Un giro rígido de todo el swing —45° de azimut, 30° de elevación y una
    traslación— no puede mover un ángulo de tres puntos. Si lo moviera, el
    número estaría describiendo a la cámara y no al cuerpo, y es el test que
    caza un bug de marco: si `angle3_deg` mirara sólo dos componentes, este
    giro lo rompería.

    Los otros tres se miden **contra un eje del marco** —la vertical y la línea
    de tiro— y el archivo lo dice en `respecto_de`: girar el marco es cambiar
    la gravedad o la línea de tiro, así que tienen que moverse, y moverse
    **exactamente** lo que se giró. Eso también se verifica acá."""
    P = toma["mp"].points_m
    defs = angulos_doc()["definiciones"]
    az, el = 45.0, 30.0
    ca, sa = np.cos(np.radians(az)), np.sin(np.radians(az))
    ce, se = np.cos(np.radians(el)), np.sin(np.radians(el))
    Ry = np.array([[ca, 0, sa], [0, 1, 0], [-sa, 0, ca]])
    Rx = np.array([[1, 0, 0], [0, ce, -se], [0, se, ce]])
    base = angulos_3d(P)

    # 1 · giro cualquiera + traslación: los de tres puntos no se mueven
    entera = angulos_3d(P @ (Rx @ Ry).T + np.array([2.5, -1.0, 0.75]))
    for nombre, d in defs.items():
        if d["respecto_de"] == "los tres puntos":
            assert np.nanmax(np.abs(base[nombre] - entera[nombre])) < 1e-9, nombre
    # y los otros tres sí, o no estarían midiendo contra nada
    for nombre in ("trunk_lean_deg", "hip_line_turn_deg", "shoulder_line_turn_deg"):
        assert np.nanmax(np.abs(base[nombre] - entera[nombre])) > 1.0, nombre

    # 2 · girar sólo alrededor de la VERTICAL: la inclinación de tronco no puede
    #     cambiar (la gravedad sigue donde estaba) y los dos giros se corren
    #     exactamente el ángulo girado.
    vertical = angulos_3d(P @ Ry.T + np.array([1.0, 0.0, -2.0]))
    assert np.nanmax(np.abs(base["trunk_lean_deg"] - vertical["trunk_lean_deg"])) < 1e-9
    for nombre in ("hip_line_turn_deg", "shoulder_line_turn_deg"):
        corrido = (vertical[nombre] - base[nombre] + 180.0) % 360.0 - 180.0
        assert np.nanmax(np.abs(corrido + az)) < 1e-9, (nombre, float(np.nanmax(np.abs(corrido))))

    # 3 · la traslación sola no mueve ninguno de los once
    movido = angulos_3d(P + np.array([-3.0, 1.5, 0.25]))
    for nombre in defs:
        assert np.nanmax(np.abs(base[nombre] - movido[nombre])) < 1e-9, nombre


def test_los_proyectados_son_los_del_motor_columna_por_columna(toma):
    """La misma pose, los mismos tres puntos, la misma fórmula: si `explore.py`
    cambiara un keypoint de un ángulo, este test lo dice. La comparación del
    encargo sólo vale si el proyectado es lo que el motor de verdad calcula."""
    from kinelab.explore import per_frame_table

    pose = toma["npz"]
    _, rows = per_frame_table(pose, CMU_FPS, toma["mp"].height_m, None)
    mios = angulos_proyectados(np.asarray(pose.keypoints, float))
    for nombre in ("elbow_left_deg", "elbow_right_deg", "knee_left_deg", "knee_right_deg", "hip_left_deg", "hip_right_deg", "shoulder_left_deg", "shoulder_right_deg"):
        del_motor = np.array([r[nombre] for r in rows], float)
        assert np.abs(del_motor - mios[nombre]).max() < 1e-9, nombre
    # el tronco del motor lleva signo; el de acá es cuánto se aparta de la
    # vertical, que es el mismo número sin el signo
    tronco = np.abs(np.array([r["trunk_lean_deg"] for r in rows], float))
    assert np.abs(tronco - mios["trunk_lean_deg"]).max() < 1e-9


def test_el_proyectado_cambia_con_la_vista_y_explota_donde_el_segmento_apunta_a_la_camara(toma):
    """El brazo de atrás de un diestro en el address apunta hacia la cámara de
    `face_on` (sale del hombro derecho hacia la pelota): ahí el codo proyectado
    se despega del verdadero. Desde `down_the_line` ese mismo codo queda de
    costado y el error se cae."""
    mp = toma["mp"]
    P = mp.points_m
    addr = toma["t3"]["address"]
    v3 = angulos_3d(P)["elbow_right_deg"][addr]
    dif = {}
    for vista in VIEWS:
        pr = angulos_proyectados(_proyectar_con(P, mp.cameras[vista]))
        dif[vista] = float(pr["elbow_right_deg"][addr] - v3)
    print(f"\n  codo derecho en el address · 3-D {v3:.1f}° · proyectado {{{', '.join(f'{k} {v3 + x:.1f}°' for k, x in dif.items())}}}")
    assert abs(dif["face_on"]) > 15.0, dif
    assert abs(dif["face_on"]) > 5 * abs(dif["down_the_line"]), dif


def test_el_giro_de_las_lineas_es_directo_en_3d_e_imposible_en_2d(toma):
    """En 3-D la línea de caderas arranca apuntando al objetivo y gira hacia
    atrás en el backswing. El estimado por acortamiento acierta desde `face_on`
    —donde la línea vive en el plano de imagen— y desde `down_the_line` dice
    que las caderas están giradas ~85° cuando están en cero."""
    mp = toma["mp"]
    P = mp.points_m
    t3 = toma["t3"]
    giro = angulos_3d(P)["hip_line_turn_deg"]
    assert abs(giro[t3["address"]]) < 15.0
    assert giro[t3["top_far"]] > 35.0  # el backswing gira hacia la pelota: positivo
    assert giro[t3["impact"]] < -15.0  # y en el impacto ya pasó de largo hacia el objetivo
    est = {v: angulos_proyectados(_proyectar_con(P, mp.cameras[v]))["hip_line_turn_deg"] for v in VIEWS}
    print(f"\n  giro de caderas en el address · 3-D {giro[t3['address']]:.1f}° · " + " · ".join(f"{v} {est[v][t3['address']]:.1f}°" for v in VIEWS))
    assert abs(est["face_on"][t3["address"]] - abs(giro[t3["address"]])) < 5.0
    assert est["down_the_line"][t3["address"]] > 70.0


def test_los_pares_izquierda_derecha_no_estan_cruzados(toma):
    """En el address de este golfista la rodilla y el codo de cada lado no
    valen lo mismo, y cada nombre tiene que traer los puntos de su lado. Si el
    mapeo cruzara un par, los `puntos` de la definición lo dicen y los valores
    se intercambiarían (invariante 15)."""
    defs = angulos_doc()["definiciones"]
    for nombre, d in defs.items():
        if nombre.endswith("_left_deg"):
            assert all(p.startswith("left_") for p in d["puntos"]), (nombre, d["puntos"])
            assert d["puntos"] == [p.replace("right_", "left_") for p in defs[nombre.replace("_left_", "_right_")]["puntos"]]
        if nombre.endswith("_right_deg"):
            assert all(p.startswith("right_") for p in d["puntos"]), (nombre, d["puntos"])
    # y no dan lo mismo: si estuvieran cruzados o duplicados, esto sería 0
    v = angulos_3d(toma["mp"].points_m)
    addr = toma["t3"]["address"]
    for izq, der in (("elbow_left_deg", "elbow_right_deg"), ("knee_left_deg", "knee_right_deg"), ("hip_left_deg", "hip_right_deg")):
        assert abs(v[izq][addr] - v[der][addr]) > 0.5, (izq, der)


def test_el_tronco_se_mide_contra_la_vertical_hacia_arriba(toma):
    """Los hombros están ARRIBA de las caderas: el ángulo entre la vertical y la
    línea cadera→hombro tiene que ser agudo. Contra la vertical hacia abajo
    daría `180 − θ`, que es un número plausible —27° se leería 153°— y nada más
    lo delata. Y el 3-D y el proyectado tienen que contar la misma historia
    desde `face_on`, que es donde el tronco se ve de costado."""
    mp = toma["mp"]
    P = mp.points_m
    addr = toma["t3"]["address"]
    v3 = angulos_3d(P)
    cadera = P[:, [H.LEFT_HIP, H.RIGHT_HIP]].mean(axis=1)
    hombro = P[:, [H.LEFT_SHOULDER, H.RIGHT_SHOULDER]].mean(axis=1)
    assert (hombro[:, 1] > cadera[:, 1]).all()  # el sujeto nunca queda cabeza abajo
    assert (v3["trunk_lean_deg"] < 90.0).all()
    assert 5.0 < v3["trunk_lean_deg"][addr] < 60.0  # un golfista en address se agacha, no se acuesta
    pr = angulos_proyectados(_proyectar_con(P, mp.cameras["face_on"]))
    print(f"\n  tronco en el address · 3-D {v3['trunk_lean_deg'][addr]:.1f}° · face_on {pr['trunk_lean_deg'][addr]:.1f}°")
    assert abs(pr["trunk_lean_deg"][addr] - v3["trunk_lean_deg"][addr]) < 25.0


def test_la_diferencia_de_los_giros_va_contra_el_valor_absoluto(toma):
    """El estimado por acortamiento no puede recuperar el signo: siempre es
    positivo. En el impacto la línea de caderas ya pasó de largo hacia el
    objetivo y el 3-D es NEGATIVO; si la diferencia se calculara contra el valor
    con signo, sumaría dos veces el giro y diría que la cámara se equivoca el
    doble de lo que se equivoca."""
    mp = toma["mp"]
    P = mp.points_m
    imp = toma["t3"]["impact"]
    v3 = angulos_3d(P)["hip_line_turn_deg"]
    assert v3[imp] < -10.0, v3[imp]
    pr = angulos_proyectados(_proyectar_con(P, mp.cameras["face_on"]))["hip_line_turn_deg"]
    assert pr[imp] >= 0.0  # el estimado nunca es negativo: es un arccos
    esperado = float(pr[imp] - abs(v3[imp]))
    del_archivo = toma["json"]["angulos"]["resumen"]["por_vista"]["face_on"]["hip_line_turn_deg"]["impact"]
    print(f"\n  giro de caderas en el impacto · 3-D {v3[imp]:.1f}° · face_on {pr[imp]:.1f}° · diferencia {esperado:+.1f}° (contra el valor con signo daría {pr[imp] - v3[imp]:+.1f}°)")
    assert del_archivo == pytest.approx(esperado, abs=10.0**-ANGULOS_DECIMALES)
    assert abs(del_archivo) < abs(pr[imp] - v3[imp]) / 2


# --- lo que sale al archivo --------------------------------------------------


def test_el_archivo_trae_las_series_las_definiciones_y_el_rotulo(toma):
    d = toma["json"]
    # los ángulos son campos nuevos y opcionales: minor, y el visor tiene que
    # poder abrir un 1.0.0 (hay uno publicado en la demo) sin la capa
    assert d["schema"] == "kinelab.pose3d/1.1.0"
    defs = d["angulos"]["definiciones"]
    assert d["angulos"]["unidad"] == "grados"
    assert len(defs) == 11
    assert set(d["angulos_3d"]) == set(defs)
    assert set(d["angulos_proyectados"]) == set(VIEWS)
    for vista in VIEWS:
        assert set(d["angulos_proyectados"][vista]) == set(defs)
        for serie in d["angulos_proyectados"][vista].values():
            assert len(serie) == d["frames"]
            assert all(x is None or isinstance(x, (int, float)) for x in serie)  # `NaN` no es JSON
    # el rótulo del punto 7: la capa dice de dónde sale y por qué un celular no puede
    for frase in ("marcadores", "celular", "profundidad"):
        assert frase in d["angulos"]["rotulo"]
    # y dice que esto no es una métrica del producto
    assert "nivel 3" in d["angulos"]["nota_nivel"]
    # cada definición trae con qué tres puntos se mide y dónde se dibuja
    for nombre, x in defs.items():
        assert x["comparar"] in ("valor", "abs")
        assert all(p in HALPE26_NAMES or p in ("vertical", "hip_center", "shoulder_center") for p in x["puntos"]), nombre
        assert all(p in HALPE26_NAMES for p in x["anclaje"]), nombre
    # las series del archivo son las que calcula el módulo, redondeadas
    v = angulos_3d(toma["mp"].points_m)
    for nombre in defs:
        assert np.abs(np.array(d["angulos_3d"][nombre], float) - v[nombre]).max() <= 0.5 * 10.0**-ANGULOS_DECIMALES + 1e-12


def test_el_resumen_del_archivo_mide_la_diferencia_en_los_tres_eventos(toma):
    r = toma["json"]["angulos"]["resumen"]
    assert set(r["por_vista"]) == set(VIEWS)
    assert r["eventos"]["address"] < r["eventos"]["top"] < r["eventos"]["impact"]
    for vista, por in r["por_vista"].items():
        for nombre, col in por.items():
            assert r["ventana"][0] <= col["peor_cuadro"] <= r["ventana"][1]
            for ev in ("address", "top", "impact"):
                assert abs(col["peor_dif"]) >= abs(col[ev]) - 1e-9, (vista, nombre, ev)
    # desde down_the_line el giro de caderas en el address es el peor de todos
    assert r["por_vista"]["down_the_line"]["hip_line_turn_deg"]["address"] > 70.0


def test_la_tabla_de_los_diez_trials_da_sesgo_y_limites_de_acuerdo():
    """El entregable de medición del encargo. Es lento a propósito (los diez
    trials): se corre una vez y se mira el número, que es el que va al informe."""
    t = angles_table("64")
    assert t["n_trials"] == 10 and t["n_sujetos"] == 1
    assert "UN solo sujeto" in t["aviso"]
    for vista in VIEWS:
        for nombre, col in t["resumen"][vista].items():
            for campo in ("address", "top", "impact", "peor_dif"):
                assert col[campo]["n"] == 10
                assert col[campo]["loa"][0] <= col[campo]["sesgo"] <= col[campo]["loa"][1]
    # lo que el encargo fue a medir: desde down_the_line el giro de la línea de
    # caderas en el address está mal por más de 70° y desde face_on por menos de 5
    assert t["resumen"]["down_the_line"]["hip_line_turn_deg"]["address"]["sesgo"] > 70.0
    assert abs(t["resumen"]["face_on"]["hip_line_turn_deg"]["address"]["sesgo"]) < 5.0
    print(f"\n  giro de caderas en el address: face_on {t['resumen']['face_on']['hip_line_turn_deg']['address']['sesgo']:+.1f}° · down_the_line {t['resumen']['down_the_line']['hip_line_turn_deg']['address']['sesgo']:+.1f}°")
