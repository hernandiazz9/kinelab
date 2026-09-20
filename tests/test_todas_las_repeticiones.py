"""El motor publica TODAS las repeticiones, no sólo la primera (encargo 35).

Hasta el 20/9 `explore()` armaba `datos-eventos.json`, el overlay y las fotos
por evento con `analysis["events"][0]`: de un clip de dos swings salían cuatro
cuadros rotulados de casi 3000 y una sola tabla por evento. El front no podía
elegir otra repetición porque el motor no le mandaba ninguna otra — en
`cortado3-lento` la repetición 2 tiene una escala **6 % distinta** (831,3 px
contra 783,9) y era invisible.

Lo que se prueba acá:

1. que `repeticiones_detalle` tiene una entrada por repetición, con los cuadros
   de **sus** eventos y no los de la primera;
2. que cada repetición se mide contra **su** address, y que el número que sale
   a la pantalla es el mismo que el de la métrica de `analysis.json` — la
   prueba del encargo 33, extendida a todas las repeticiones;
3. que los campos de primer nivel siguen siendo exactamente los de la
   repetición 1 (son transitorios: los retira el encargo 36);
4. que la repetición 1 conserva el nombre de sus fotos y las demás salen como
   `evento-r<N>-<id>.png`;
5. que el rótulo del overlay dice de qué repetición es cada evento.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from kinelab.explore import EVENT_ORDER, _draw, foto_de_evento
from kinelab.perception.keypoints import H
from kinelab.perception.posestore import PoseData, save_pose
from sports.golf.config import GOLF
from tests.helpers.synth_swing import synth_swing

ALTURA_M = 1.75
FPS = 120.0
#: Cuánto se corre el golfista, en píxeles, entre la primera repetición y las
#: demás. Con la escala de este sujeto (1536 px de cadena para 1,75 m) son
#: **13,7 cm**: cinco veces el MDC de 2,42 de `pelvis_sway_impact_cm`, así que si
#: una repetición se midiera contra el address de otra el error no pasaría por
#: ruido.
CORRIMIENTO_PX = 120.0


def _concatenar(partes):
    """Un clip con las repeticiones de `partes`, una atrás de la otra.

    `synth_swing` construye todas sus repeticiones iguales, y con repeticiones
    iguales no se puede ver si un número es el de una o el del clip entero: el
    pico de la repetición 2 y el del clip dan lo mismo aunque el código mire
    todos los cuadros. Cada parte trae un downswing de distinta duración, así
    que cada swing tiene su propio pico de velocidad de manos.

    El corte cae entre la quietud del final de una parte y la del principio de
    la siguiente —las dos con el sujeto en la posición de address— así que no
    hay salto de pose en la costura."""
    kp = np.concatenate([p.keypoints for p in partes], axis=0)
    sc = np.concatenate([p.scores for p in partes], axis=0)
    truth: list[dict] = []
    off = 0
    for p in partes:
        truth += [{k: v + off for k, v in t.items()} for t in p.truth]
        off += p.keypoints.shape[0]
    return replace(partes[0], keypoints=kp, scores=sc, timestamps_s=np.arange(kp.shape[0]) / partes[0].fps, truth=truth)


def _corrido_despues_de_la_primera(sw, dx: float = CORRIMIENTO_PX):
    """El golfista se corre `dx` px hacia la derecha entre el primer swing y el
    segundo, y se queda ahí: es lo que hace cualquiera que pega dos bolas.

    El corrimiento es una **rampa** repartida en la quietud entre las dos
    repeticiones, no un salto: un salto de 120 px en un cuadro son 9,4 bh/s de
    velocidad de manos contra los 0,61 del swing, y la segmentación encontraría
    una repetición que no existe. Repartido, son 0,04 bh/s.

    Adentro de cada repetición el cuerpo queda quieto, así que todos los
    desplazamientos verdaderos siguen siendo cero. Lo único que cambia es el
    cuadro de referencia de cada una: sin rebasar, la tabla por evento de la
    repetición 2 mostraría esos 120 px como si el golfista se hubiera movido
    durante el swing."""
    kp = np.array(sw.keypoints, dtype=np.float64, copy=True)
    a, b = int(sw.truth[0]["follow_end"]), int(sw.truth[1]["address"])
    rampa = np.zeros(kp.shape[0])
    rampa[a:b] = dx * np.linspace(0.0, 1.0, max(b - a, 1))
    rampa[b:] = dx
    kp[..., 0] += rampa[:, None]
    return replace(sw, keypoints=kp.astype(np.float32))


def _pose_sintetica(tmp_path: Path, sw, fps: float = FPS, width: int = 1080, height: int = 1920) -> Path:
    """Un `pose.npz` como el que escribe `kinelab_truth.mocap`: puntos ya en
    píxeles, sin video y sin estimador."""
    T = sw.keypoints.shape[0]
    d = tmp_path / "pose-fuente"
    d.mkdir(parents=True, exist_ok=True)
    prov = {
        "source": "sintetico", "fps_real": fps, "frames": T, "frame_size": [width, height],
        "rotation_deg": 0, "source_name": "synth_swing.py", "source_sha256": "0" * 64,
        "framing": {"body_height_px_median": sw.body_height_px, "body_height_px_min": sw.body_height_px,
                    "body_height_px_max": sw.body_height_px, "frac_of_frame": sw.body_height_px / height,
                    "detection_rate": 1.0, "multi_subject_frac": 0.0, "camera_motion_px": None},
        "plausibility_counts": {}, "camera_motion_px": 0.0,
    }
    lo, hi = np.nanmin(sw.keypoints, axis=1), np.nanmax(sw.keypoints, axis=1)
    save_pose(d, PoseData(sw.keypoints, sw.scores, np.concatenate([lo, hi], axis=1),
                          np.arange(T) / fps, np.zeros(T, np.uint8), prov), overwrite=True)
    return d / "pose.npz"


@pytest.fixture(scope="module")
def tres_swings(tmp_path_factory) -> tuple[dict, dict, Path]:
    """Tres repeticiones **distintas entre sí**: cada una con su downswing, y el
    golfista corrido 120 px después de la primera. Se corre `explore()` una sola
    vez, que dibuja el overlay entero."""
    from kinelab.explore import explore

    tmp = tmp_path_factory.mktemp("todas-las-reps")
    sw = _corrido_despues_de_la_primera(_concatenar([
        synth_swing(FPS, n_reps=1, downswing_s=d, frame=(1920, 1080), body_height_px=0.8 * 1920, amplitude_px=300.0)
        for d in (0.27, 0.33, 0.40)
    ]))
    out = tmp / "out"
    explore(None, out, GOLF, height_m=ALTURA_M, pose_npz=_pose_sintetica(tmp, sw), nota_fuente="prueba")
    datos = json.loads((out / "datos-eventos.json").read_text(encoding="utf-8"))
    analysis = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    assert datos["repeticiones"] == 3, f"el clip sintético tiene que dar 3 repeticiones y dio {datos['repeticiones']}: el test no prueba nada"
    return datos, analysis, out


def test_una_entrada_por_repeticion_con_los_cuadros_de_sus_propios_eventos(tres_swings):
    datos, analysis, _ = tres_swings
    detalle = datos["repeticiones_detalle"]
    assert [d["rep"] for d in detalle] == [r["rep"] for r in analysis["reps"]] == [1, 2, 3]

    for d, r, e in zip(detalle, analysis["reps"], analysis["events"]):
        assert (d["frame_start"], d["frame_end"]) == (r["frame_start"], r["frame_end"])
        # los cuadros son los de SUS eventos, tomados de `analysis.json`, no otros
        assert d["eventos_frame"] == {k: e[k]["frame"] for k in EVENT_ORDER if e.get(k)}
        assert d["eventos_tol_frames"] == {k: e[k]["tol_frames"] for k in EVENT_ORDER if e.get(k)}
        assert set(d["eventos_t_s"]) == set(d["eventos_frame"])
        # y caen adentro de la repetición que dicen ser
        assert all(d["frame_start"] <= f <= d["frame_end"] for f in d["eventos_frame"].values())
        assert d["escala_px"] == r["scale_px"] and d["escala_fuente"] == r["scale_source"]
        assert d["referencia_cuadro"] == d["eventos_frame"]["address"] and d["referencia_fuente"] == "address"

    # el punto del encargo: NO son los de la primera repetida tres veces
    cuadros = [d["eventos_frame"] for d in detalle]
    assert cuadros[1] != cuadros[0] and cuadros[2] != cuadros[0]
    assert all(detalle[i]["frame_end"] < detalle[i + 1]["frame_start"] for i in range(2)), "las repeticiones no se solapan"


def test_cada_repeticion_se_mide_contra_su_propio_address(tres_swings):
    """El número que la pantalla muestra en «en cada evento» es el mismo que el
    de la métrica de esa repetición. Es la prueba del encargo 33 —una sola
    escala, un solo número por evento— extendida a todas las repeticiones.

    El sujeto está corrido 120 px (13,7 cm) entre la primera y las otras dos: si
    una repetición se midiera contra el address de la primera, el `dx` saldría
    con esos 13,7 cm encima y la comparación de abajo se caería."""
    datos, analysis, _ = tres_swings
    pares = [("pelvis_sway_top_cm", "top", "pelvis_dx_vs_address_cm"), ("pelvis_sway_impact_cm", "impact", "pelvis_dx_vs_address_cm")]
    comparados = 0
    for d, r in zip(datos["repeticiones_detalle"], analysis["reps"]):
        assert d["en_cada_evento"]["address"]["pelvis_dx_vs_address_cm"] == pytest.approx(0.0, abs=1e-9), "el address de una repetición está a cero de sí mismo"
        for mid, evento, col in pares:
            m = r["metrics"].get(mid, {}).get("value")
            if m is None or evento not in d["en_cada_evento"]:
                continue
            assert d["en_cada_evento"][evento][col] == pytest.approx(m, abs=0.05), f"rep {d['rep']} · {mid}"
            comparados += 1
    assert comparados >= 6, f"se compararon {comparados} pares y hacen falta al menos 6 (dos por repetición)"

    # y el corrimiento existe de verdad: el cuerpo de la repetición 3 está lejos
    # del de la 1 en píxeles crudos, que es lo que hace que rebasar importe.
    x1 = datos["repeticiones_detalle"][0]["en_cada_evento"]["address"]["left_hip_x"]
    x3 = datos["repeticiones_detalle"][2]["en_cada_evento"]["address"]["left_hip_x"]
    assert abs(x3 - x1) > 0.9 * CORRIMIENTO_PX, f"el sujeto no se corrió ({x1} → {x3}): el test no prueba nada"


def test_los_picos_de_una_repeticion_son_los_de_su_tramo(tres_swings):
    """`picos` de primer nivel es el máximo del clip entero; el de cada
    repetición, el de sus cuadros. Se comprueba contra el CSV, que es la misma
    tabla que leyó `explore()`."""
    import csv

    datos, _, out = tres_swings
    with (out / "datos-por-cuadro.csv").open(newline="", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    for d in datos["repeticiones_detalle"]:
        tramo = filas[d["frame_start"] : d["frame_end"] + 1]
        for col, pico in d["picos"].items():
            vs = [float(x[col]) for x in tramo if x[col] not in ("", None)]
            assert pico == (round(max(vs), 2) if vs else None), f"rep {d['rep']} · {col}"
    # y no es el del clip entero repetido: los tres swings tienen downswings de
    # distinta duración, así que cada uno tiene su propio pico.
    global_bh = datos["picos"]["hands_speed_bh_s"]
    por_rep = [d["picos"]["hands_speed_bh_s"] for d in datos["repeticiones_detalle"]]
    assert all(v <= global_bh + 1e-9 for v in por_rep)
    assert len(set(por_rep)) == 3, f"los tres picos dan lo mismo ({por_rep}): el test no distingue el de la repetición del del clip"
    assert sum(1 for v in por_rep if v < global_bh - 1e-9) >= 2, f"al menos dos repeticiones tienen que quedar por debajo del pico del clip: {por_rep} contra {global_bh}"


def test_los_campos_de_primer_nivel_siguen_siendo_los_de_la_repeticion_1(tres_swings):
    """El corte del encargo: el primer nivel **no se mueve**, así el front sigue
    andando el día que esto entre y el 36 migra componente por componente. Son
    transitorios y están repetidos en `repeticiones_detalle[0]`; si alguna vez
    dejaran de coincidir, la pantalla mostraría dos cosas distintas para la misma
    repetición, que es el bug que el encargo 33 fue a cerrar."""
    datos, analysis, _ = tres_swings
    d0 = datos["repeticiones_detalle"][0]
    for k in ("eventos_frame", "eventos_t_s", "eventos_tol_frames", "eventos_subcuadro", "duraciones",
              "en_cada_evento", "diferencias_vs_address", "escala_px", "escala_fuente", "escala_cuadro",
              "referencia_cuadro", "referencia_fuente"):
        assert datos[k] == d0[k], f"el primer nivel y la repetición 1 no dicen lo mismo en `{k}`"
    assert datos["repeticion_mostrada"] == 1 and datos["repeticiones"] == len(analysis["reps"])
    # `picos` es el único que NO coincide, a propósito: el de arriba es el del
    # clip entero y el de abajo, el de la repetición.
    assert set(datos["picos"]) == set(d0["picos"])


def test_las_fotos_de_la_repeticion_1_conservan_su_nombre_y_las_demas_llevan_la_suya(tres_swings):
    datos, _, out = tres_swings
    esperadas = {foto_de_evento(d["rep"], e) for d in datos["repeticiones_detalle"] for e in d["eventos_frame"]}
    assert sorted(p.name for p in out.glob("evento-*.png")) == sorted(esperadas)
    # la repetición 1 no cambió de nombre: es lo que ya sirve el servicio y lo
    # que muestra la pantalla de hoy
    assert {f"evento-{e}.png" for e in datos["repeticiones_detalle"][0]["eventos_frame"]} <= esperadas
    assert (out / "evento-r2-top.png").is_file() and (out / "evento-r3-impact.png").is_file()
    assert not (out / "evento-r1-top.png").exists(), "la repetición 1 NO lleva `r1`: rompería lo que ya anda"
    # un solo overlay, no uno por repetición (ADR-014: el video anotado no es la vista)
    assert sorted(p.name for p in out.glob("*.mp4")) == ["overlay.mp4"]


def test_foto_de_evento_nombra_la_repeticion():
    assert foto_de_evento(1, "top") == "evento-top.png"
    assert foto_de_evento(2, "follow_end") == "evento-r2-follow_end.png"
    assert foto_de_evento(12, "address") == "evento-r12-address.png"


def test_el_overlay_rotula_la_repeticion_de_cada_evento(tres_swings, tmp_path):
    """De punta a punta, sobre `render`: dos cuadros **idénticos** —misma pose,
    misma fila, mismo instante— marcados como el top de la repetición 1 y el de
    la 2. Las dos fotos tienen que salir distintas, porque lo único que las
    separa es el rótulo. Si el rótulo dijera sólo «TOP», serían la misma imagen
    y no habría forma de saber de qué swing es cada evento."""
    import cv2

    from kinelab.explore import render
    from kinelab.ingest.gate import CaptureJson

    _, _, out = tres_swings
    capture = CaptureJson.model_validate_json((out / "capture.json").read_text(encoding="utf-8")).model_copy(
        update={"width": 96, "height": 96, "frames_decoded": 8}
    )
    T, J = 8, 26
    kp = np.full((T, J, 2), np.nan)
    kp[:, H.LEFT_SHOULDER], kp[:, H.LEFT_ELBOW], kp[:, H.LEFT_WRIST] = (35.0, 30.0), (40.0, 50.0), (45.0, 70.0)

    class _Pose:
        keypoints = kp
        scores = np.full((T, J), 0.9)
        timestamps_s = np.zeros(T)

    fila = {"frame": 3, "hands_speed_bh_s": 1.0, "hands_height_pct": 50.0, "trunk_lean_deg": 1.0,
            "shoulder_line_deg": 2.0, "hip_line_deg": 3.0, "elbow_left_deg": 150.0}
    rows = [dict(fila) for _ in range(T)]  # todas iguales, incluido `frame`
    d = tmp_path / "render"
    d.mkdir()
    _, snaps = render(d, _Pose(), rows, [(1, {"top": 2}), (2, {"top": 5})], 30.0, capture)
    assert sorted(p.name for p in snaps) == ["evento-r2-top.png", "evento-top.png"]
    a, b = cv2.imread(str(d / "evento-top.png")), cv2.imread(str(d / "evento-r2-top.png"))
    assert a is not None and b is not None and a.shape == b.shape
    assert not np.array_equal(a, b), "los dos cuadros son idénticos salvo el rótulo: si el rótulo no dijera la repetición, las dos fotos serían la misma imagen"


def test_el_rotulo_del_overlay_dice_de_que_repeticion_es_el_evento():
    """Dos repeticiones tienen los mismos cuatro eventos: «IMPACT» a secas no
    distingue el primero del segundo. El rótulo lleva la repetición delante."""
    frame = np.zeros((240, 320, 3), np.uint8)
    kp = np.full((26, 2), np.nan, dtype=float)
    kp[H.LEFT_ELBOW] = (100.0, 120.0)
    sc = np.full(26, 0.9)
    row = {"frame": 44, "hands_speed_bh_s": 1.0, "hands_height_pct": 50.0, "trunk_lean_deg": 3.0,
           "shoulder_line_deg": 1.0, "hip_line_deg": 2.0, "elbow_left_deg": 150.0}
    r1 = _draw(frame, kp, sc, row, "r1 impact", 0.366)
    r2 = _draw(frame, kp, sc, row, "r2 impact", 0.366)
    sin = _draw(frame, kp, sc, row, None, 0.366)
    assert not np.array_equal(r1, r2), "el rótulo de la repetición 1 y el de la 2 se dibujan igual"
    assert not np.array_equal(r1, sin) and not np.array_equal(r2, sin)
