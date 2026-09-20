"""El exportador de demo: los archivos que produce, la transformación afín y el
recorte que no puede cortar al sujeto.

Todo sobre un trabajo sintético armado acá mismo (video con ffmpeg, `pose.npz`
con un sujeto que se mueve de verdad): ningún test depende de un clip que esté
en la máquina de alguien.

Los tres que pide el encargo 22, más los que hicieron falta:

1. Sobre un trabajo sintético salen todos los archivos.
2. La transformación afín aplicada a un keypoint conocido cae donde debe —
   verificado contra el píxel del video exportado, no contra la fórmula.
3. El recorte no deja al sujeto fuera del cuadro en ningún cuadro del tramo.
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
from kinelab.tools import exportar_demo as ed

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="hace falta ffmpeg/ffprobe")

FPS = 30.0
T = 150
ANCHO, ALTO = 640, 480
EVENTOS = {"address": 45, "top": 70, "impact": 85, "follow_end": 100}

# El sujeto: un cuadradito que se mueve en diagonal. Lo importante no es que
# parezca una persona, sino que la caja que lo contiene NO sea todo el cuadro —
# si lo fuera, el recorte sería la identidad y el test no probaría nada.
X0, Y0, PASO = 120.0, 100.0, 1.2
LADO = 60.0


def _keypoints() -> np.ndarray:
    """(T, J, 2): los 26 puntos repartidos en un cuadrado que se desplaza."""
    k = np.zeros((T, J, 2), dtype=np.float32)
    for i in range(T):
        cx, cy = X0 + PASO * i, Y0 + PASO * i
        for j in range(J):
            ang = 2 * np.pi * j / J
            k[i, j] = (cx + LADO / 2 * np.cos(ang), cy + LADO / 2 * np.sin(ang))
    return k


def _cuadro(i: int) -> np.ndarray:
    """El cuadro `i`: un fondo cuyo nivel depende del índice, y encima el cuadrado
    del sujeto, centrado donde están sus keypoints."""
    img = np.full((ALTO, ANCHO, 3), 20 + (i * 37) % 200, np.uint8)
    cx, cy = int(X0 + PASO * i), int(Y0 + PASO * i)
    cv2.rectangle(img, (cx - 30, cy - 30), (cx + 30, cy + 30), (255, 255, 255), -1)
    cv2.circle(img, (cx, cy), 8, (0, 0, 255), -1)
    return img


def _video(dst: Path) -> None:
    """Un video donde **cada cuadro es distinto de todos los demás en cualquier
    recorte**: el fondo entero cambia de nivel con el índice, y encima va el
    cuadrado del sujeto. `testsrc` no sirve — su franja móvil deja regiones
    idénticas cuadro a cuadro, y con eso un corte por el cuadro equivocado pasa
    desapercibido (probado: los cinco vecinos daban la misma diferencia)."""
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-nostdin", "-f", "rawvideo", "-pix_fmt", "bgr24",
         "-s", f"{ANCHO}x{ALTO}", "-r", f"{FPS:g}", "-i", "-", "-c:v", "libx264",
         "-preset", "ultrafast", "-crf", "12", "-pix_fmt", "yuv420p", "-g", "12", str(dst)],
        stdin=subprocess.PIPE,
    )
    for i in range(T):
        proc.stdin.write(_cuadro(i).tobytes())
    proc.stdin.close()
    assert proc.wait(timeout=300) == 0


def _trabajo(tmp: Path) -> Path:
    """Una carpeta con la misma forma que `data/exploracion/<id>/`."""
    d = tmp / "trabajo-sintetico"
    d.mkdir(parents=True)
    k = _keypoints()
    bbox = np.stack([k[..., 0].min(1), k[..., 1].min(1), k[..., 0].max(1), k[..., 1].max(1)], axis=1).astype(np.float32)
    save_pose(d, PoseData(
        keypoints=k, scores=np.full((T, J), 0.9, np.float32), bbox=bbox,
        timestamps_s=np.arange(T) / FPS, plausibility=np.zeros(T, np.uint8),
        provenance={"model": "sintetico", "fps_real": FPS, "frame_size": [ANCHO, ALTO]},
    ))
    _video(d / "original.mp4")
    shutil.copy2(d / "original.mp4", d / "overlay.mp4")
    (d / "capture.json").write_text(json.dumps({
        "schema_version": "1.2.0", "athlete": "test", "gesture": "driver", "view": "face_on",
        "capture_path_id": "desconocido-video", "capture_path_calibrated": False,
        "fps_provenance": "sin_verificar", "fps_real": FPS, "fps_playback": FPS, "fps_playback_raw": FPS,
        "stretch_factor": 1.0, "fps_source": "test", "codec": "h264", "width": ANCHO, "height": ALTO,
        "rotation_deg": 0, "frames_decoded": T, "duration_s": T / FPS, "duration_playback_s": T / FPS,
        "vfr_ratio": 1.0, "vfr_ratio_raw": 1.0, "first_delta_s": 1 / FPS, "fps_note": None,
        "recorded_at": None, "sha256_original": "0" * 64, "original_name": "sintetico.mp4",
        "gate": {"verdict": "ok", "checks": [], "reasons": []},
    }), encoding="utf-8")
    (d / "datos-eventos.json").write_text(json.dumps({
        "aviso": "test", "video": "sintetico.mp4", "fps_archivo": FPS, "cuadros": T, "altura_m": None,
        "gate_diria": [], "eventos_frame": EVENTOS, "eventos_t_s": {k_: v / FPS for k_, v in EVENTOS.items()},
        "duraciones": {}, "picos": {}, "en_cada_evento": {}, "diferencias_vs_address": {},
        "calidad": {}, "columnas": ["frame", "t_s"],
    }), encoding="utf-8")
    (d / "datos-por-cuadro.csv").write_text(
        "frame,t_s\n" + "".join(f"{i},{i / FPS:.6f}\n" for i in range(T)), encoding="utf-8")
    (d / "analysis.json").write_text(json.dumps({"header": {}, "reps": [], "warnings": []}), encoding="utf-8")
    (d / "trabajo.json").write_text(json.dumps({
        "estado": "listo", "origen": "subida", "video": "sintetico.mp4", "altura_m": None,
        "vista": "face_on", "creado": "2026-09-15T00:00:00+00:00", "camino": "desconocido-video",
    }), encoding="utf-8")
    # Una foto por evento, del tamaño del cuadro como se ve y con el contenido de
    # ese cuadro: si fueran lisas, recortarlas o no daría lo mismo y el test de
    # `test_las_fotos_llevan_el_mismo_recorte_que_el_video` no probaría nada.
    for nombre, f in EVENTOS.items():
        cv2.imwrite(str(d / f"evento-{nombre}.png"), _cuadro(f))
    # Y una foto de una SEGUNDA repetición (encargo 35): el exportador no tiene
    # una lista de nombres, junta `evento-*.png`, así que tiene que salir sola.
    cv2.imwrite(str(d / "evento-r2-top.png"), _cuadro(EVENTOS["top"]))
    return d


@pytest.fixture(scope="module")
def exportado(tmp_path_factory) -> tuple[ed.Resultado, Path]:
    tmp = tmp_path_factory.mktemp("demo")
    d = _trabajo(tmp)
    out = tmp / "demo"
    r = ed.exportar(d, out, alto=160)
    ed.escribir_indice(out)
    return r, d


# --- 1 · todos los archivos --------------------------------------------------------


def test_escribe_todos_los_archivos(exportado):
    r, _ = exportado
    esperados = {
        ed.VIDEO_LIMPIO, ed.VIDEO_OVERLAY, ed.TRANSFORMACION, ed.POSE_JSON,
        "datos-eventos.json", "analysis.json", "capture.json", "datos-por-cuadro.csv",
        "trabajo.json", "evento-address.jpg", "evento-top.jpg", "evento-impact.jpg", "evento-follow_end.jpg",
        # la foto de la repetición 2 viaja como cualquier otra (encargo 35)
        "evento-r2-top.jpg",
    }
    assert esperados <= set(r.archivos), f"faltan: {sorted(esperados - set(r.archivos))}"
    assert all((r.dir / n).is_file() for n in esperados)
    # Las fotos en JPEG, y ni un PNG: el peso es el problema que esto resuelve.
    assert not list(r.dir.glob("*.png"))


def test_el_indice_lista_el_trabajo(exportado):
    r, _ = exportado
    doc = json.loads((r.dir.parent / ed.INDICE).read_text(encoding="utf-8"))
    assert doc["schema"] == ed.ESQUEMA_INDICE
    fila = next(f for f in doc["trabajos"] if f["id"] == r.id)
    assert fila["fps_archivo"] == FPS
    assert fila["eventos_frame"] == EVENTOS
    assert fila["fps_provenance"] == "sin_verificar"


def test_el_trabajo_json_apunta_a_demo(exportado):
    r, _ = exportado
    j = json.loads((r.dir / "trabajo.json").read_text(encoding="utf-8"))
    assert j["estado"] == "listo"
    assert all(u.startswith(f"/demo/{r.id}/") for u in j["archivos"].values())
    assert j["resumen"]["eventos_frame"] == EVENTOS
    assert j["archivo"]["fps_provenance"] == "sin_verificar"


def test_el_video_tiene_exactamente_los_cuadros_del_tramo(exportado):
    r, _ = exportado
    tr = r.transformacion
    a, b = tr["tramo_origen"]
    # Un segundo (30 cuadros) antes del primer evento y uno después del último.
    assert (a, b) == (EVENTOS["address"] - 30, EVENTOS["follow_end"] + 30) == (15, 130)
    assert tr["cuadros"] == b - a + 1 == 116
    assert (a, b) != (0, T - 1), "si el tramo fuera el clip entero, el recorte temporal no se probaría"
    for n in (ed.VIDEO_LIMPIO, ed.VIDEO_OVERLAY):
        assert ed.contar_cuadros(r.dir / n) == tr["cuadros"], n


def test_las_fotos_llevan_el_mismo_recorte_que_el_video(exportado):
    """Si la foto de un evento tuviera otro encuadre que el reproductor, el que
    mira vería dos cosas distintas del mismo cuadro."""
    r, d = exportado
    tr = r.transformacion
    rx, ry, rw, rh = (tr["recorte"][k] for k in ("x", "y", "ancho", "alto"))
    dw, dh = tr["tamano_destino"]
    for nombre, f in EVENTOS.items():
        jpg = cv2.imread(str(r.dir / f"evento-{nombre}.jpg"), cv2.IMREAD_COLOR)
        png = cv2.imread(str(d / f"evento-{nombre}.png"), cv2.IMREAD_COLOR)
        esperado = cv2.resize(png[ry : ry + rh, rx : rx + rw], (dw, dh), interpolation=cv2.INTER_AREA)
        assert [jpg.shape[1], jpg.shape[0]] == [dw, dh], nombre
        dif = float(np.mean(np.abs(jpg.astype(float) - esperado.astype(float))))
        assert dif < 6.0, f"evento-{nombre}.jpg difiere {dif:.1f} niveles del recorte hecho a mano"


def test_el_csv_se_recorta_y_no_renumera(exportado):
    r, _ = exportado
    a, b = r.transformacion["tramo_origen"]
    filas = (r.dir / "datos-por-cuadro.csv").read_text(encoding="utf-8").strip().splitlines()
    frames = [int(l.split(",")[0]) for l in filas[1:]]
    assert frames == list(range(a, b + 1)), "los números de cuadro del CSV son los del ORIGEN, no se renumeran"


def test_la_pose_json_va_en_el_marco_del_origen(exportado):
    r, d = exportado
    p = json.loads((r.dir / ed.POSE_JSON).read_text(encoding="utf-8"))
    a, b = r.transformacion["tramo_origen"]
    assert p["reference_frame"] == "image_px"
    assert p["cuadro_offset"] == a and p["cuadros"] == b - a + 1
    assert len(p["keypoints"]) == b - a + 1 and len(p["keypoints"][0]) == J
    # La fila i es el cuadro cuadro_offset + i del ORIGEN, sin transformar.
    k = _keypoints()
    assert p["keypoints"][0][H.NOSE] == pytest.approx([round(float(v), 1) for v in k[a, H.NOSE]], abs=0.05)


# --- 2 · la transformación afín ----------------------------------------------------


def test_la_transformacion_cae_donde_debe(exportado):
    """Un keypoint conocido, transformado, tiene que caer en el píxel que el video
    exportado le corresponde. Se verifica contra la geometría del recorte, no
    repitiendo la fórmula: se rehace el recorte a mano con OpenCV sobre el cuadro
    del origen y se compara el color del píxel."""
    r, d = exportado
    tr = r.transformacion
    # `cuadro_offset` y no `tramo_origen[0]`: es el campo que va a usar el que
    # dibuje, y acá lo verifica el contenido del video, no otra copia del número.
    a = tr["cuadro_offset"]
    f_origen = EVENTOS["top"]
    k = _keypoints()[f_origen, H.NOSE]

    x_demo, y_demo = ed.aplicar(tr, float(k[0]), float(k[1]))
    dw, dh = tr["tamano_destino"]
    assert 0 <= x_demo <= dw and 0 <= y_demo <= dh

    # El mismo punto, por el camino largo: recortar y reescalar el cuadro del
    # origen con OpenCV y ver que el píxel (x_demo, y_demo) del video exportado
    # es el mismo píxel que el (k[0], k[1]) del origen.
    cap = cv2.VideoCapture(str(d / "original.mp4"))
    cap.set(cv2.CAP_PROP_POS_FRAMES, f_origen)
    ok, cuadro_origen = cap.read()
    cap.release()
    assert ok
    rx, ry, rw, rh = (tr["recorte"][key] for key in ("x", "y", "ancho", "alto"))
    esperado = cv2.resize(cuadro_origen[ry : ry + rh, rx : rx + rw], (dw, dh), interpolation=cv2.INTER_AREA)

    def demo(i: int):
        cap = cv2.VideoCapture(str(r.dir / ed.VIDEO_LIMPIO))
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, img = cap.read()
        cap.release()
        assert ok, i
        return img.astype(float)

    def dif(i: int) -> float:
        return float(np.mean(np.abs(demo(i) - esperado.astype(float))))

    assert demo(f_origen - a).shape == esperado.shape
    # El cuadro que dice `cuadro_offset` es el recorte hecho a mano; los vecinos, no.
    # La segunda mitad no es adorno: sin ella el test pasaría con cualquier offset
    # sobre un video en el que no se mueva nada.
    aqui = dif(f_origen - a)
    vecinos = [dif(f_origen - a + k) for k in (-5, -3, 3, 5)]
    assert aqui < 8.0, f"el cuadro {f_origen - a} difiere {aqui:.1f} niveles del recorte hecho a mano"
    assert min(vecinos) > 4 * aqui, f"aquí {aqui:.1f}, vecinos {[round(v, 1) for v in vecinos]}: el test no distingue el cuadro"


def test_el_alto_pedido_es_el_alto_que_sale(exportado):
    """`--alto` manda: sin esto la escala puede estar invertida (`h/alto` en vez de
    `alto/h`) y todo lo demás sigue siendo consistente consigo mismo — el tamaño
    declarado también saldría del mismo número mal. El único testigo de afuera es
    el alto del archivo que escribió ffmpeg."""
    r, _ = exportado
    tr = r.transformacion
    assert tr["tamano_destino"][1] == 160, "el alto pedido a `exportar`"
    assert tr["escala"] == pytest.approx(160 / tr["recorte"]["alto"], rel=1e-4)
    for n in (ed.VIDEO_LIMPIO, ed.VIDEO_OVERLAY):
        cap = cv2.VideoCapture(str(r.dir / n))
        w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        assert [w, h] == tr["tamano_destino"], f"{n} mide {w}×{h} y la transformación dice {tr['tamano_destino']}"


def test_la_transformacion_es_invertible_y_esta_declarada(exportado):
    r, _ = exportado
    tr = r.transformacion
    assert tr["schema"] == ed.ESQUEMA_TRANSFORMACION
    assert tr["reference_frame_origen"] == "image_px"
    assert "x_demo" in tr["nota"] and "cuadro_offset" in tr["nota"]
    # El origen del recorte es el (0,0) del destino, y la esquina opuesta el tamaño.
    rx, ry, rw, rh = (tr["recorte"][k] for k in ("x", "y", "ancho", "alto"))
    assert ed.aplicar(tr, rx, ry) == pytest.approx((0.0, 0.0))
    assert ed.aplicar(tr, rx + rw, ry + rh) == pytest.approx(tuple(tr["tamano_destino"]), rel=1e-3)


def test_recorte_completo_es_la_identidad_salvo_la_escala(tmp_path):
    d = _trabajo(tmp_path)
    r = ed.exportar(d, tmp_path / "demo", alto=ALTO, modo="completo")
    tr = r.transformacion
    assert (tr["offset_x"], tr["offset_y"]) == (0, 0)
    assert tr["escala"] == pytest.approx(1.0)
    assert tr["tamano_destino"] == [ANCHO, ALTO]


def test_no_agranda_por_encima_del_origen(tmp_path):
    """`--alto` por encima del recorte no reescala para arriba: no hay información
    que agregar, y sí peso."""
    d = _trabajo(tmp_path)
    r = ed.exportar(d, tmp_path / "demo", alto=4000, modo="completo")
    assert r.transformacion["tamano_destino"] == [ANCHO, ALTO]
    assert r.transformacion["escala"] == pytest.approx(1.0)


# --- 3 · el recorte no corta al sujeto ---------------------------------------------


def test_el_recorte_no_deja_al_sujeto_afuera_en_ningun_cuadro(exportado):
    r, _ = exportado
    tr = r.transformacion
    a, b = tr["tramo_origen"]
    dw, dh = tr["tamano_destino"]
    k = _keypoints()[a : b + 1].astype(float)
    x, y = ed.aplicar(tr, k[..., 0], k[..., 1])
    assert x.min() >= 0 and x.max() <= dw, f"x fuera: [{x.min():.1f}, {x.max():.1f}] contra [0, {dw}]"
    assert y.min() >= 0 and y.max() <= dh, f"y fuera: [{y.min():.1f}, {y.max():.1f}] contra [0, {dh}]"
    assert tr["puntos_fuera_del_origen"]["n"] == 0


def test_el_recorte_es_mas_chico_que_el_cuadro(exportado):
    """Si no, el test de arriba pasa por construcción y no prueba nada."""
    tr, _ = exportado[0].transformacion, None
    assert tr["recorte"]["ancho"] < ANCHO and tr["recorte"]["alto"] < ALTO


def test_margen_cero_toca_al_sujeto_y_el_margen_lo_separa(tmp_path):
    """El margen hace lo que dice: con 0 el recorte es la caja del sujeto; con 0,10
    es más grande, en los dos ejes, y el sujeto sigue adentro."""
    d = _trabajo(tmp_path)
    t = ed.cargar(d)
    a, b = ed.tramo(t)
    x0, y0, x1, y1 = ed.caja_del_sujeto(t, a, b)
    apretado = ed.recorte(t, a, b, margen=0.0)
    holgado = ed.recorte(t, a, b, margen=0.10)
    assert apretado[0] <= x0 and apretado[1] <= y0
    assert apretado[2] >= (x1 - x0) - 2 and apretado[3] >= (y1 - y0) - 2
    assert holgado[0] < apretado[0] and holgado[1] < apretado[1]
    assert holgado[2] > apretado[2] and holgado[3] > apretado[3]


def test_los_cuatro_lados_del_recorte_son_pares(exportado):
    """yuv420p submuestrea el croma 2×2: un ancho impar lo rechaza libx264."""
    tr = exportado[0].transformacion
    assert tr["recorte"]["ancho"] % 2 == 0 and tr["recorte"]["alto"] % 2 == 0
    assert tr["tamano_destino"][0] % 2 == 0 and tr["tamano_destino"][1] % 2 == 0


def test_el_recorte_nunca_se_pasa_del_cuadro_con_tamano_impar(tmp_path):
    """Al par de **abajo**, no al de arriba: con un cuadro de lado impar, redondear
    para arriba empuja el recorte un píxel afuera y ffmpeg lo rechaza."""
    d = _trabajo(tmp_path)
    t = ed.cargar(d)
    t.tamano = (ANCHO - 1, ALTO - 1)
    a, b = ed.tramo(t)
    for modo, margen in (("completo", 0.0), ("sujeto", 10.0)):
        x, y, w, h = ed.recorte(t, a, b, modo=modo, margen=margen)
        assert x + w <= t.tamano[0] and y + h <= t.tamano[1], (modo, x, y, w, h)
        assert w % 2 == 0 and h % 2 == 0, (modo, w, h)


def test_el_recorte_se_acota_al_cuadro_del_origen(tmp_path):
    """Con un margen enorme el recorte no se sale del cuadro, y lo que quedó fuera
    del origen se cuenta en vez de desaparecer."""
    d = _trabajo(tmp_path)
    t = ed.cargar(d)
    a, b = ed.tramo(t)
    x, y, w, h = ed.recorte(t, a, b, margen=10.0)
    assert (x, y) == (0, 0) and (w, h) == (ANCHO, ALTO)
    assert ed.puntos_fuera_del_origen(t, a, b)["n"] == 0


# --- el tramo -----------------------------------------------------------------------


def test_el_tramo_auto_no_nombra_ningun_evento(tmp_path):
    """Sale del primero y el último evento, se llamen como se llamen: el motor no
    conoce los eventos de ningún deporte (invariante 13)."""
    d = _trabajo(tmp_path)
    t = ed.cargar(d)
    t.eventos = {"empieza": 40, "termina": 60}
    assert ed.tramo(t) == (10, 90)


def test_el_tramo_se_acota_al_clip(tmp_path):
    d = _trabajo(tmp_path)
    t = ed.cargar(d)
    assert ed.tramo(t, pedido="0-9999") == (0, T - 1)


def test_el_tramo_explicito_manda(tmp_path):
    d = _trabajo(tmp_path)
    t = ed.cargar(d)
    assert ed.tramo(t, pedido="10-40") == (10, 40)
    with pytest.raises(ed.ExportError, match="se espera"):
        ed.tramo(t, pedido="diez")
    with pytest.raises(ed.ExportError, match="mayor que"):
        ed.tramo(t, pedido="40-10")


def test_sin_pose_no_exporta(tmp_path):
    d = _trabajo(tmp_path)
    (d / "pose.npz").unlink()
    with pytest.raises(ed.ExportError, match="pose.npz"):
        ed.cargar(d)


def test_sin_original_el_video_limpio_es_null_con_razon(tmp_path):
    """Un trabajo que vino de un `pose.npz` y no de un video (el ejemplo de mocap)
    no tiene original: el video limpio no existe y el archivo dice por qué."""
    d = _trabajo(tmp_path)
    (d / "original.mp4").unlink()
    r = ed.exportar(d, tmp_path / "demo", alto=240)
    assert r.transformacion["video_limpio"] is None
    assert "no tiene original" in r.transformacion["video_limpio_null_reason"]
    assert ed.VIDEO_LIMPIO not in r.archivos
    assert ed.VIDEO_OVERLAY in r.archivos
