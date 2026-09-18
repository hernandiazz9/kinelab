"""La deriva de cámara, contra fondos cuyo movimiento conocemos de antemano.

Todo lo que se verifica acá es contra una transformación **construida en el
test**: una traslación de (3,0 · 1,5) px, una rotación chica, un fondo quieto,
una deformación que ninguna homografía puede seguir. Nunca contra un número
copiado de una corrida anterior, que cambiaría solo.

Los dos bugs que estos tests tienen que matar (y matan, verificado a mano
invirtiendo el código):

- **máscara invertida** — `test_un_sujeto_que_se_mueve_no_mueve_la_deriva`: con
  la máscara al revés SIFT sólo ve al sujeto y la "deriva" pasa a ser el
  movimiento del sujeto, decenas de px donde se esperan décimas.
- **homografía evaluada en la fila equivocada** —
  `test_cada_fila_recupera_su_propio_desplazamiento`: bajo una rotación, las
  cuatro filas tienen desplazamientos distintos y conocidos; evaluar todas en
  una sola fila rompe tres de las cuatro.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
import pytest

from kinelab.perception.keypoints import H, J
from kinelab.perception.posestore import PoseData, save_pose
from kinelab.tools.camera_drift import (
    FILAS,
    UMBRAL_INLIERS_FRAC,
    UMBRAL_NO_RIGIDO_PX,
    DriftError,
    Params,
    correr,
    estimar,
    filas_de,
    mascara,
)

W, HGT = 320, 256
TOL_PX = 0.3  # lo que el prompt pide recuperar: ±0,3 px
DX_CONOCIDO, DY_CONOCIDO = 3.0, 1.5
# Filas del "sujeto" sintético, bien separadas para que una rotación las
# distinga: son las que van a `pose.npz` y las que el modelo evalúa.
FILAS_Y = {"cabeza": 60.0, "hombros": 90.0, "caderas": 140.0, "pies": 210.0}
COLUMNA_X = 150.0


def textura(seed: int, w: int = W, h: int = HGT) -> np.ndarray:
    """Fondo con manchas: material de sobra para SIFT, y reproducible."""
    rng = np.random.default_rng(seed)
    img = np.full((h, w), 128, np.uint8)
    for _ in range(400):
        cv2.circle(img, (int(rng.integers(0, w)), int(rng.integers(0, h))),
                   int(rng.integers(3, 14)), int(rng.integers(15, 240)), -1)
    return cv2.GaussianBlur(img, (5, 5), 1.0)


SUJETO_W, SUJETO_H = 70, 190


def con_sujeto(fondo: np.ndarray, x: int, y: int, seed: int = 99) -> tuple[np.ndarray, np.ndarray]:
    """Pega un "sujeto" texturado en `(x, y)`. Devuelve `(imagen, bbox)`.

    Texturado a propósito: si la máscara se invierte, el sujeto tiene puntos
    SIFT de sobra para que la homografía lo siga y el test lo note.
    """
    img = fondo.copy()
    parche = textura(seed, SUJETO_W, SUJETO_H)
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(img.shape[1], x + SUJETO_W), min(img.shape[0], y + SUJETO_H)
    img[y0:y1, x0:x1] = parche[: y1 - y0, : x1 - x0]
    return img, np.array([x0, y0, x1, y1], np.float32)


def pose_de(bboxes: list[np.ndarray], columna: float = COLUMNA_X) -> PoseData:
    """Una `PoseData` mínima: los keypoints de las cuatro filas y las muñecas."""
    T = len(bboxes)
    kp = np.full((T, J, 2), np.nan, np.float32)
    for t in range(T):
        for idx, y in ((H.LEFT_HIP, FILAS_Y["caderas"]), (H.RIGHT_HIP, FILAS_Y["caderas"]),
                       (H.LEFT_SHOULDER, FILAS_Y["hombros"]), (H.RIGHT_SHOULDER, FILAS_Y["hombros"]),
                       (H.LEFT_ANKLE, FILAS_Y["pies"]), (H.RIGHT_ANKLE, FILAS_Y["pies"]),
                       (H.HEAD, FILAS_Y["cabeza"])):
            kp[t, idx] = (columna, y)
        kp[t, H.LEFT_WRIST] = kp[t, H.RIGHT_WRIST] = (columna, FILAS_Y["caderas"])
    return PoseData(
        keypoints=kp, scores=np.ones((T, J), np.float32), bbox=np.stack(bboxes).astype(np.float32),
        timestamps_s=np.arange(T, dtype=np.float64) / 30.0, plausibility=np.zeros(T, np.uint8),
        provenance={"model": "sintético", "keypoint_set": "halpe26"},
    )


def deformar(img: np.ndarray, amp: float = 9.0, periodos: float = 2.0) -> np.ndarray:
    """Corre cada columna en y por una sinusoide: localmente es una traslación
    —los descriptores siguen emparejando— y globalmente no hay homografía que
    la siga."""
    ys, xs = np.mgrid[0 : img.shape[0], 0 : img.shape[1]].astype(np.float32)
    return cv2.remap(img, xs, ys + amp * np.sin(2 * np.pi * xs / (img.shape[1] / periodos)), cv2.INTER_CUBIC)


def esperado(M: np.ndarray, columna: float, fila: float) -> tuple[float, float]:
    """El desplazamiento que la transformación construida induce en un punto."""
    q = M[:2, :2] @ np.array([columna, fila]) + M[:2, 2]
    return float(q[0] - columna), float(q[1] - fila)


def mide(ref: np.ndarray, m_ref: np.ndarray, muestra: np.ndarray, m_muestra: np.ndarray, p: Params | None = None):
    p = p or Params()
    modelo, razon = estimar(ref, m_ref, muestra, m_muestra, p)
    assert modelo is not None, f"se esperaba un modelo y no lo hubo: {razon}"
    return modelo


def mascaras(pose: PoseData, p: Params, *frames: int) -> list[np.ndarray]:
    alto = FILAS_Y["pies"] - FILAS_Y["cabeza"]
    return [mascara((HGT, W), pose, f, alto, p) for f in frames]


# --------------------------------------------------------------- el método

def test_recupera_un_desplazamiento_conocido():
    """Fondo corrido (3,0 · 1,5) px con el sujeto enmascarado: ±0,3 px."""
    fondo = textura(1)
    M = np.array([[1.0, 0.0, DX_CONOCIDO], [0.0, 1.0, DY_CONOCIDO]], np.float32)
    ref, b0 = con_sujeto(fondo, 120, 55)
    muestra, b1 = con_sujeto(cv2.warpAffine(fondo, M, (W, HGT), flags=cv2.INTER_CUBIC), 128, 60)
    pose = pose_de([b0, b1])
    p = Params()
    m0, m1 = mascaras(pose, p, 0, 1)
    modelo = mide(ref, m0, muestra, m1, p)
    for nombre, y in FILAS_Y.items():
        dx, dy = modelo.desplazamiento(COLUMNA_X, y)
        assert abs(dx - DX_CONOCIDO) < TOL_PX, f"{nombre}: dx {dx}"
        assert abs(dy - DY_CONOCIDO) < TOL_PX, f"{nombre}: dy {dy}"


def test_sin_desplazamiento_da_cero():
    fondo = textura(2)
    ref, b0 = con_sujeto(fondo, 120, 55)
    muestra, b1 = con_sujeto(fondo, 120, 55)
    pose = pose_de([b0, b1])
    p = Params()
    m0, m1 = mascaras(pose, p, 0, 1)
    modelo = mide(ref, m0, muestra, m1, p)
    for nombre, y in FILAS_Y.items():
        dx, dy = modelo.desplazamiento(COLUMNA_X, y)
        assert abs(dx) < TOL_PX and abs(dy) < TOL_PX, f"{nombre}: {dx}, {dy}"


def test_un_sujeto_que_se_mueve_no_mueve_la_deriva():
    """Fondo quieto y sujeto que cruza medio cuadro: la deriva sigue en cero.

    Es el test de la máscara. Con la máscara invertida SIFT ve solamente al
    sujeto y la homografía devuelve su traslación, que acá son 70 px.
    """
    fondo = textura(3)
    ref, b0 = con_sujeto(fondo, 60, 40)
    muestra, b1 = con_sujeto(fondo, 130, 55)
    assert abs(b1[0] - b0[0]) > 50, "el sujeto tiene que moverse mucho para que el test discrimine"
    pose = pose_de([b0, b1])
    p = Params()
    m0, m1 = mascaras(pose, p, 0, 1)
    modelo = mide(ref, m0, muestra, m1, p)
    for nombre, y in FILAS_Y.items():
        dx, dy = modelo.desplazamiento(COLUMNA_X, y)
        assert abs(dx) < TOL_PX and abs(dy) < TOL_PX, f"{nombre}: {dx}, {dy}"


def test_cada_fila_recupera_su_propio_desplazamiento():
    """Bajo una rotación, las cuatro filas se mueven distinto, y cada una tiene
    que dar lo suyo. Evaluar el modelo en una sola fila rompe tres de cuatro."""
    fondo = textura(4)
    # Rotación Y zoom: una rotación sola separa las filas en dx pero no en dy
    # (el término que depende de y es cos θ − 1, que a 1,5° son 0,05 px).
    M = cv2.getRotationMatrix2D((W / 2, HGT / 2), 1.5, 1.03).astype(np.float32)
    ref, b0 = con_sujeto(fondo, 120, 55)
    muestra, b1 = con_sujeto(cv2.warpAffine(fondo, M, (W, HGT), flags=cv2.INTER_CUBIC), 124, 58)
    pose = pose_de([b0, b1])
    p = Params()
    m0, m1 = mascaras(pose, p, 0, 1)
    modelo = mide(ref, m0, muestra, m1, p)

    medidos, teoricos = {}, {}
    for nombre, y in FILAS_Y.items():
        medidos[nombre] = modelo.desplazamiento(COLUMNA_X, y)
        teoricos[nombre] = esperado(M, COLUMNA_X, y)
        assert abs(medidos[nombre][0] - teoricos[nombre][0]) < TOL_PX, f"{nombre}: dx {medidos[nombre]} vs {teoricos[nombre]}"
        assert abs(medidos[nombre][1] - teoricos[nombre][1]) < TOL_PX, f"{nombre}: dy {medidos[nombre]} vs {teoricos[nombre]}"
    # El test sólo discrimina si las filas de verdad difieren entre sí: con 150 px
    # entre la cabeza y los pies, la rotación las separa en dx y el zoom en dy.
    dys = [teoricos[n][1] for n in FILAS_Y]
    dxs = [teoricos[n][0] for n in FILAS_Y]
    assert max(dxs) - min(dxs) > 4 * TOL_PX, f"las filas no se distinguen en dx: {dxs}"
    assert max(dys) - min(dys) > 4 * TOL_PX, f"las filas no se distinguen en dy: {dys}"


def test_sin_inliers_suficientes_devuelve_null_con_razon():
    """Las dos formas de quedarse sin modelo, cada una con su frase: un cuadro
    liso (SIFT no encuentra nada) y un fondo ajeno (nada se empareja)."""
    fondo = textura(5)
    ref, b0 = con_sujeto(fondo, 120, 55)
    ajeno, b1 = con_sujeto(textura(77), 120, 55)
    p = Params()
    m0, m1 = mascaras(pose_de([b0, b1]), p, 0, 1)

    modelo, razon = estimar(ref, m0, np.full((HGT, W), 128, np.uint8), m1, p)
    assert modelo is None
    assert razon and "SIFT" in razon and " 0 " in razon, razon

    modelo, razon = estimar(ref, m0, ajeno, m1, p)
    assert modelo is None
    assert razon and str(p.min_inliers) in razon, razon


def test_un_fondo_que_no_es_rigido_se_marca_y_uno_rigido_no():
    """La deformación de `deformar()` no la puede seguir ninguna homografía.

    Las dos señales de `no_rigido`, contra el mismo fondo sin deformar como
    control: el residuo de los inliers sube y la fracción de inliers baja. La
    segunda es la que separa con margen — la primera está acotada por
    `ransac_px`, y de ahí que la regla mire las dos.
    """
    fondo = textura(6)
    ref, b0 = con_sujeto(fondo, 120, 55)
    rigido, b1 = con_sujeto(fondo, 124, 58)
    flojo, b2 = con_sujeto(deformar(fondo), 124, 58)
    p = Params()
    m0, m1, m2 = mascaras(pose_de([b0, b1, b2]), p, 0, 1, 2)

    control = mide(ref, m0, rigido, m1, p)
    assert control.no_rigido(p) == (False, None), control
    assert control.residuo_px <= UMBRAL_NO_RIGIDO_PX and control.inliers_frac >= UMBRAL_INLIERS_FRAC

    modelo = mide(ref, m0, flojo, m2, p)
    marcado, por = modelo.no_rigido(p)
    assert marcado, modelo
    assert "inliers" in por, f"{por}: {modelo.inliers}/{modelo.coincidencias}"
    assert modelo.inliers_frac < control.inliers_frac
    assert modelo.residuo_px <= p.ransac_px, "RANSAC acota el residuo de los inliers por construcción"


def test_filas_en_null_cuando_falta_el_keypoint():
    pose = pose_de([np.array([0, 0, 10, 10], np.float32)])
    pose.keypoints[0, H.HEAD] = np.nan
    filas = filas_de(pose, 0)
    assert filas["cabeza"]["y_px"] is None and "cuadro de referencia 0" in filas["cabeza"]["null_reason"]
    assert filas["caderas"]["y_px"] == pytest.approx(FILAS_Y["caderas"])


# --------------------------------------------------------------- de punta a punta

# El address NO es el cuadro de referencia (que es el 0): si lo fuera, su deriva
# sería cero y restarla o sumarla daría lo mismo — la resta dejaría de estar
# verificada. Medido: con ADDRESS = 0 la mutación «resta → suma» pasaba en verde.
ADDRESS, TOP, IMPACT, NO_RIGIDO, PLANO = 4, 8, 16, 20, 22
N_CUADROS = 24
PASO_X, PASO_Y = 0.25, 0.125  # px por cuadro de deriva construida


@pytest.fixture(scope="module")
def clip_con_deriva(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Un clip donde la imagen se corre `PASO_X`/`PASO_Y` px por cuadro, con un
    cuadro deformado y uno liso. La pose y los eventos, al lado."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg no está en el PATH")
    d = tmp_path_factory.mktemp("drift")
    fondo = textura(7)
    cuadros, bboxes = [], []
    for k in range(N_CUADROS):
        M = np.array([[1.0, 0.0, PASO_X * k], [0.0, 1.0, PASO_Y * k]], np.float32)
        img = cv2.warpAffine(fondo, M, (W, HGT), flags=cv2.INTER_CUBIC)
        if k == NO_RIGIDO:
            img = deformar(img)
        if k == PLANO:
            img = np.full((HGT, W), 128, np.uint8)
        img, caja = con_sujeto(img, 110 + (k % 5) * 4, 50 + (k % 3) * 3)
        cuadros.append(img)
        bboxes.append(caja)

    video = d / "deriva.mp4"
    cmd = [
        shutil.which("ffmpeg"), "-y", "-v", "error", "-nostdin",
        "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{HGT}", "-r", "30", "-i", "-",
        # Sin pérdida: el ruido de compresión movería los puntos SIFT y el test
        # dejaría de medir la deriva construida.
        "-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", "-pix_fmt", "gray", str(video),
    ]
    proc = subprocess.run(cmd, input=b"".join(c.tobytes() for c in cuadros), capture_output=True, timeout=300)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")

    save_pose(d, pose_de(bboxes))
    (d / "analysis.json").write_text(json.dumps({"events": [
        {"rep": 1, "address": {"frame": ADDRESS}, "top": {"frame": TOP}, "impact": {"frame": IMPACT}},
    ]}), encoding="utf-8")
    return d


@pytest.fixture(scope="module")
def deriva(clip_con_deriva):
    d, _ = correr(clip_con_deriva / "deriva.mp4", clip_con_deriva / "pose.npz", cada=2)
    return d


def test_muestrea_los_cuadros_pedidos_y_los_de_los_eventos(deriva):
    frames = [m.frame for m in deriva.muestras]
    assert frames == sorted(set(frames)), "las muestras van ordenadas y sin repetir"
    assert set(range(0, N_CUADROS, 2)) <= set(frames)
    assert {ADDRESS, TOP, IMPACT} <= set(frames)
    assert deriva.ref == 0 and deriva.frames == N_CUADROS
    assert ADDRESS != deriva.ref, "el address tiene que tener deriva propia para que la resta esté verificada"


def test_la_deriva_por_cuadro_es_la_construida(deriva):
    for m in deriva.con_modelo:
        if m.frame in (NO_RIGIDO, PLANO):
            continue
        for nombre in FILAS:
            assert abs(m.dx(nombre) - PASO_X * m.frame) < TOL_PX, f"cuadro {m.frame} fila {nombre}: {m.dx(nombre)}"
            assert abs(m.dy(nombre) - PASO_Y * m.frame) < TOL_PX, f"cuadro {m.frame} fila {nombre}: {m.dy(nombre)}"


def test_el_cuadro_liso_queda_en_null_con_razon(deriva):
    m = deriva.en(PLANO)
    assert m is not None and m.filas is None and m.null_reason
    assert m.residuo_px is None and m.inliers is None


def test_el_cuadro_deformado_se_marca_no_rigido(deriva):
    assert deriva.en(NO_RIGIDO).no_rigido is True
    otros = [m for m in deriva.con_modelo if m.frame != NO_RIGIDO]
    assert otros and not any(m.no_rigido for m in otros)
    assert deriva.resumen()["cuadros_no_rigidos"] == 1


def test_el_desplazamiento_entre_eventos_es_la_diferencia_de_derivas(deriva):
    (ev,) = deriva.eventos
    assert ev["rep"] == 1
    for clave, hasta in (("address_a_top", TOP), ("address_a_impacto", IMPACT)):
        for nombre in FILAS:
            assert abs(ev[clave][nombre]["dx_px"] - PASO_X * (hasta - ADDRESS)) < TOL_PX
            assert abs(ev[clave][nombre]["dy_px"] - PASO_Y * (hasta - ADDRESS)) < TOL_PX


def test_el_resumen_reporta_el_maximo_con_su_cuadro(deriva):
    r = deriva.resumen()
    peor = max((m for m in deriva.con_modelo), key=lambda m: abs(m.dx("caderas")))
    assert r["max_abs_dx_px"]["frame"] == peor.frame
    assert abs(r["max_abs_dx_px"]["value"]) >= abs(peor.dx("caderas")) - 1e-9
    assert r["cuadros_con_modelo"] + r["cuadros_sin_modelo"] == r["cuadros_muestreados"]


def test_el_json_se_escribe_y_es_json_valido(clip_con_deriva, tmp_path):
    from kinelab.tools.camera_drift import main

    salida = tmp_path / "camera-drift.json"
    assert main([str(clip_con_deriva / "deriva.mp4"), "--pose", str(clip_con_deriva / "pose.npz"),
                 "--cada", "8", "--out", str(salida), "--dibujar", str(IMPACT)]) == 0
    d = json.loads(salida.read_text(encoding="utf-8"))
    assert d["herramienta"] == "kinelab.tools.camera_drift"
    assert d["params"]["procedencia_umbrales_no_rigido"] == "estimacion"
    assert d["procedencia_deriva"] == "medido_aqui"
    assert set(d["filas_ref"]) == set(FILAS)
    assert (tmp_path / f"camera-drift-{IMPACT}.png").is_file()
    # La frontera NaN → null: ningún NaN sobrevive a `json.loads`.
    assert "NaN" not in salida.read_text(encoding="utf-8")


def test_no_toca_ni_la_pose_ni_el_analisis(clip_con_deriva, tmp_path):
    from kinelab.tools.camera_drift import main

    antes = {p.name: p.read_bytes() for p in clip_con_deriva.glob("*") if p.name in ("pose.npz", "analysis.json")}
    assert main([str(clip_con_deriva / "deriva.mp4"), "--pose", str(clip_con_deriva / "pose.npz"),
                 "--cada", "8", "--out", str(tmp_path / "x.json")]) == 0
    assert {p.name: p.read_bytes() for p in clip_con_deriva.glob("*") if p.name in antes} == antes


def test_la_mascara_tapa_al_sujeto_y_el_alcance_del_palo():
    """Lo que la máscara tiene que tapar, y hasta dónde.

    El disco del palo es lo único de la máscara que ningún otro test defiende:
    medido sobre `cortado3-lento.mp4`, apagarlo mueve la deriva ≤ 0,5 px, así
    que no hay un test de resultado que lo pueda distinguir. Éste verifica su
    geometría, que es lo que sí se puede afirmar.
    """
    alto = 150.0
    caja = np.array([100.0, 50.0, 170.0, 240.0], np.float32)
    pose = pose_de([caja])
    # La muñeca queda en el centro de la caja; el palo llega bastante más lejos.
    radio = Params().palo_radio_frac * alto
    m = mascara((HGT, W), pose, 0, alto, Params())
    mx, my = int(pose.keypoints[0, H.LEFT_WRIST, 0]), int(pose.keypoints[0, H.LEFT_WRIST, 1])
    assert m[int((caja[1] + caja[3]) / 2), int((caja[0] + caja[2]) / 2)] == 0, "el sujeto tiene que estar tapado"
    dentro = (my, int(mx - radio * 0.9))
    fuera = (my, int(mx + radio * 1.2))
    assert 0 <= dentro[1] and fuera[1] < W, "el test necesita los dos puntos dentro del cuadro"
    assert m[dentro] == 0, "a 0,9 radios de la muñeca el palo sigue tapado"
    assert m[fuera] == 255, "a 1,2 radios ya es fondo utilizable"
    sin_palo = mascara((HGT, W), pose, 0, alto, Params(con_palo=False))
    assert sin_palo[dentro] == 255, "con --sin-palo ese mismo punto es fondo"


def test_la_region_recorta_donde_se_busca_fondo(clip_con_deriva):
    pose = pose_de([np.array([100, 50, 170, 240], np.float32)])
    sup = mascara((HGT, W), pose, 0, 150.0, Params(region="superior"))
    inf = mascara((HGT, W), pose, 0, 150.0, Params(region="inferior"))
    assert sup[HGT // 2:].max() == 0 and sup[: HGT // 2].max() == 255
    assert inf[: HGT // 2].max() == 0 and inf[HGT // 2:].max() == 255


def test_parametros_invalidos_se_rechazan(clip_con_deriva):
    with pytest.raises(ValueError, match="region"):
        Params(region="izquierda")
    with pytest.raises(ValueError, match="ratio"):
        Params(ratio=1.5)
    with pytest.raises(DriftError, match="--cada"):
        correr(clip_con_deriva / "deriva.mp4", clip_con_deriva / "pose.npz", cada=0)
    with pytest.raises(DriftError, match="--ref"):
        correr(clip_con_deriva / "deriva.mp4", clip_con_deriva / "pose.npz", ref=N_CUADROS + 5)
