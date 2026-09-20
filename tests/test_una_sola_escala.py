"""Una sola escala por pantalla, y dicha (encargo 33, `CONTRATO.md` §La escala).

Hasta el 20/9 la misma pantalla mostraba **dos números en cm para el mismo
evento**: la tabla por cuadro convertía con el `body_height_px` de **cada
cuadro** y las métricas con la escala de la **repetición**, y ninguno de los dos
decía cuál había usado. Medido sobre los `pose.npz` guardados, la diferencia
llegaba a **4,39 cm** en `pelvis_sway_impact_cm` de `cortado3-lento` (22,6 cm
contra 26,99 de la tabla) — casi el doble del MDC 2,42 de esa métrica.

Lo que se prueba acá:

1. que los dos números coinciden cuando los dos existen;
2. que ningún cm sale sin su `escala_px` al lado, ni al revés;
3. que el camino **sin** `reps` sigue siendo el de antes, y lo declara.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date

import numpy as np
import pytest

from kinelab.analysis import analyze_take, build_analysis
from kinelab.contract.validate import validate_analysis
from kinelab.explore import per_frame_table
from kinelab.ingest.__main__ import ingest_clip
from kinelab.ingest.capture_paths import load_capture_paths
from kinelab.ingest.gate import CaptureJson
from kinelab.metrics.core import SCALE_SOURCE_CHAIN, SCALE_SOURCE_FRAME
from kinelab.perception.keypoints import H
from kinelab.perception.posestore import PoseData, load_pose, save_pose
from sports.golf.config import GOLF
from tests.helpers.synth_swing import synth_swing

ALTURA_M = 1.80
# Las ocho columnas en cm de la tabla por cuadro, y la novena que también divide.
COLS_CM = [f"{s}_d{e}_vs_address_cm" for s in ("pelvis", "thorax", "head", "hands") for e in ("x", "y")] + ["hands_speed_cm_s"]
# métrica del registro → (columna de la tabla, evento). El signo es el mismo: las
# dos miden `dx` hacia la derecha de la imagen y `dy` hacia arriba.
PARES = [
    ("pelvis_sway_top_cm", "pelvis_dx_vs_address_cm", "top"),
    ("pelvis_sway_impact_cm", "pelvis_dx_vs_address_cm", "impact"),
    ("pelvis_lift_top_cm", "pelvis_dy_vs_address_cm", "top"),
    ("thorax_sway_top_cm", "thorax_dx_vs_address_cm", "top"),
    ("thorax_lift_top_cm", "thorax_dy_vs_address_cm", "top"),
    ("head_sway_top_cm", "head_dx_vs_address_cm", "top"),
    ("head_lift_top_cm", "head_dy_vs_address_cm", "top"),
]


def _pose(sw) -> PoseData:
    T = sw.keypoints.shape[0]
    return PoseData(
        sw.keypoints, sw.scores, np.zeros((T, 4), np.float32), sw.timestamps_s, np.zeros(T, np.uint8),
        {"model": "sintético", "framing": {"detection_rate": 1.0, "body_height_px_median": sw.body_height_px, "body_height_px_min": sw.body_height_px, "body_height_px_max": sw.body_height_px, "frac_of_frame": sw.body_height_px / sw.frame[0]}, "plausibility_counts": {}, "camera_motion_px": 0.0},
    )


def _take(clips, capture_paths_yaml, tmp_path, sw=None):
    if "hevc120" not in clips:
        pytest.skip("sin fixture hevc120")
    paths = load_capture_paths(capture_paths_yaml)
    take, _ = ingest_clip(clips["hevc120"], athlete="t", gesture="driver", view="face_on", capture_path_id="test-hevc-120-cfr", capture_paths=paths, sport=GOLF, data_dir=tmp_path, day=date(2026, 9, 12))
    sw = sw if sw is not None else synth_swing(120.0, n_reps=2)
    save_pose(take, _pose(sw))
    return take, sw


def _tabla(take, a, *, height_m=ALTURA_M, con_reps=True):
    """La tabla por cuadro como la arma `explore()`: con las repeticiones del
    `analysis.json` y el address de la primera."""
    pose = load_pose(take)
    capture = CaptureJson.model_validate_json((take / "capture.json").read_text(encoding="utf-8"))
    rep = a["events"][0] if a["events"] else None
    address = rep["address"]["frame"] if rep and rep.get("address") else None
    kw = {"reps": a["reps"]} if con_reps else {}
    return per_frame_table(pose, float(capture.fps_real), height_m, address, wrist_score_min=float(GOLF.events.params.wrist_score_min or 0.0), **kw)


def test_la_tabla_por_cuadro_y_las_metricas_dan_EL_MISMO_cm(clips, capture_paths_yaml, tmp_path):
    """El test que le pone precio a la falsedad del 33: para el mismo evento del
    mismo clip, el cm de la tabla y el cm de la métrica tienen que ser el mismo
    número. Lo único que puede separarlos es el redondeo del sextuplo a un
    decimal (`round(value, 1)`), o sea 0,05 cm.

    Falla si la tabla vuelve a dividir por `body_height_px` del cuadro: en los
    clips reales esa diferencia va de 1,7 a 4,4 cm."""
    take, _ = _take(clips, capture_paths_yaml, tmp_path)
    a = analyze_take(take, GOLF, write=False, height_m=ALTURA_M)
    names, rows = _tabla(take, a)
    ev = a["events"][0]
    m = a["reps"][0]["metrics"]
    comparadas = 0
    for mid, col, evento in PARES:
        valor, marca = m[mid]["value"], ev.get(evento)
        if valor is None or not marca or col not in names:
            continue
        de_la_tabla = rows[marca["frame"]][col]
        assert de_la_tabla is not None, f"{col} en el cuadro de {evento} no puede estar vacío: está dentro de la repetición"
        assert de_la_tabla == pytest.approx(valor, abs=0.05), f"{mid}: métrica {valor} vs tabla {de_la_tabla} ({col} @ {evento})"
        comparadas += 1
    assert comparadas >= 5, f"el test no comparó casi nada ({comparadas}): revisá PARES"


def test_ningun_cm_sale_sin_su_escala(clips, capture_paths_yaml, tmp_path):
    """Cada cm de la tabla viaja con el divisor que lo produjo, y al revés: sin
    `escala_px` no hay cm. Un cuadro fuera de toda repetición no tiene ninguna
    escala que sea la suya, así que no tiene cm — antes tenía un número, dividido
    por una escala que no usaba nadie más."""
    take, _ = _take(clips, capture_paths_yaml, tmp_path)
    a = analyze_take(take, GOLF, write=False, height_m=ALTURA_M)
    names, rows = _tabla(take, a)
    assert "escala_px" in names
    dentro = {f for r in a["reps"] for f in range(r["frame_start"], r["frame_end"] + 1)}
    con_cm = 0
    for i, fila in enumerate(rows):
        escala = fila["escala_px"]
        cms = [fila[c] for c in COLS_CM if c in names]
        if escala is None:
            assert all(v is None for v in cms), f"cuadro {i}: hay cm sin escala"
            assert i not in dentro, f"cuadro {i} está en una repetición y no tiene escala"
        else:
            assert escala > 0 and i in dentro, f"cuadro {i}: escala fuera de toda repetición"
            con_cm += 1
    assert 0 < con_cm < len(rows), "el clip tiene que tener cuadros dentro y fuera de las repeticiones"
    # y la escala de cada fila es exactamente la de su repetición
    for r in a["reps"]:
        assert r["scale_source"] == SCALE_SOURCE_CHAIN and r["scale_px"] is not None
        for f in (r["frame_start"], (r["frame_start"] + r["frame_end"]) // 2, r["frame_end"]):
            assert rows[f]["escala_px"] == pytest.approx(r["scale_px"], abs=1e-9)


def test_la_tabla_sin_reps_se_comporta_como_antes_y_lo_declara(clips, capture_paths_yaml, tmp_path):
    """El camino de la firma anterior —el que usan `truth/` y los dos tests de
    `test_eventos_senal.py`, que llaman posicional— no cambia de números: divide
    por `body_height_px` de cada cuadro, en todos los cuadros. Lo que cambia es
    que la columna `escala_px` lo dice fila por fila en vez de dejarlo implícito."""
    take, _ = _take(clips, capture_paths_yaml, tmp_path)
    a = analyze_take(take, GOLF, write=False, height_m=ALTURA_M)
    names, rows = _tabla(take, a, con_reps=False)
    assert "escala_px" in names
    for fila in rows:
        assert fila["escala_px"] == fila["body_height_px"], "sin reps, la escala ES la altura de cuerpo del cuadro"
    # el valor: dx en px dividido por la altura de cuerpo del propio cuadro
    pose = load_pose(take)
    from kinelab.perception.gaps import interpolate_gaps

    k = interpolate_gaps(pose.keypoints, 5).astype(float)
    ref = a["events"][0]["address"]["frame"]
    for f in (ref, len(rows) // 2, len(rows) - 1):
        bh = rows[f]["body_height_px"]
        if bh is None or rows[f]["pelvis_dx_vs_address_cm"] is None:
            continue
        dx = float((k[f, [H.LEFT_HIP, H.RIGHT_HIP]].mean(axis=0) - k[ref, [H.LEFT_HIP, H.RIGHT_HIP]].mean(axis=0))[0])
        assert rows[f]["pelvis_dx_vs_address_cm"] == pytest.approx(dx / bh * ALTURA_M * 100.0, rel=1e-9)
    # y con reps hay al menos un cuadro donde los dos caminos NO coinciden: si
    # coincidieran siempre, este encargo no habría arreglado nada
    _, con = _tabla(take, a, con_reps=True)
    distintos = [i for i, (x, y) in enumerate(zip(rows, con)) if x["pelvis_dx_vs_address_cm"] != y["pelvis_dx_vs_address_cm"]]
    assert distintos, "los dos caminos dan lo mismo: el test no está probando nada"


def test_la_escala_por_repeticion_viaja_en_el_analysis(clips, capture_paths_yaml, tmp_path):
    """`reps[].scale_px` es el divisor de las métricas en cm de ESA repetición, y
    `quality.scale_px` es la mediana entre repeticiones — que con dos o más no es
    el divisor de ninguna, y el `method` lo dice."""
    take, sw = _take(clips, capture_paths_yaml, tmp_path)
    a = analyze_take(take, GOLF, write=True, height_m=ALTURA_M)
    assert validate_analysis(json.loads((take / "analysis.json").read_text())) == []
    assert len(a["reps"]) >= 2, "hacen falta dos repeticiones para que la mediana tenga sentido"
    kp = load_pose(take).keypoints.astype(float)
    for r, e in zip(a["reps"], a["events"]):
        assert r["scale_source"] in (SCALE_SOURCE_CHAIN, SCALE_SOURCE_FRAME)
        assert r["scale_px"] is not None and r["scale_source"] == SCALE_SOURCE_CHAIN
        # se reconstruye la métrica a mano CON ESA escala, no con la del `quality`
        hip = lambda f: (kp[f, H.LEFT_HIP] + kp[f, H.RIGHT_HIP]) / 2
        dx = hip(e["top"]["frame"])[0] - hip(e["address"]["frame"])[0]
        assert r["metrics"]["pelvis_sway_top_cm"]["value"] == pytest.approx(dx / r["scale_px"] * ALTURA_M * 100.0, abs=0.11)
    assert "mediana entre" in a["quality"]["scale_px"]["method"] and "reps[].scale_px" in a["quality"]["scale_px"]["method"]
    # un campo nuevo y opcional: el schema sube minor, no major
    assert a["header"]["schema_version"] == "2.2.0"


def test_sin_cadena_el_analysis_dice_que_cayo_al_fallback(clips, capture_paths_yaml, tmp_path):
    """El fallback de `px_to_cm` **no se mata** (cambiar valores publicados por un
    `null` es del dominio), pero deja de ser mudo: `reps[].scale_source` dice
    `body_height_px_frame` y `warnings[]` explica que el divisor no es uno solo.

    La razón no puede ir en el sextuplo: `$defs/metric` es
    `additionalProperties: false` y agregarle un campo sería un bump de schema."""
    sw = synth_swing(120.0, n_reps=2)
    sw = replace(sw, keypoints=np.array(sw.keypoints, dtype=np.float32, copy=True))
    sw.keypoints[:, [H.LEFT_KNEE, H.RIGHT_KNEE]] = np.nan  # sin rodillas no hay cadena
    take, _ = _take(clips, capture_paths_yaml, tmp_path, sw=sw)
    a = analyze_take(take, GOLF, write=False, height_m=ALTURA_M)
    assert a["reps"], "el clip tiene que seguir teniendo repeticiones"
    assert all(r["scale_source"] == SCALE_SOURCE_FRAME and r["scale_px"] is None for r in a["reps"])
    assert any("la cadena de la estatura no se pudo medir" in w and "body_height_px" in w for w in a["warnings"])
    # y los valores en cm siguen existiendo: el fallback sigue vivo
    assert any(m["value"] is not None for r in a["reps"] for mid, m in r["metrics"].items() if m["unit"] == "cm")
    # la tabla hace lo mismo que las métricas: divide por la altura del cuadro
    names, rows = _tabla(take, a)
    dentro = a["reps"][0]
    f = (dentro["frame_start"] + dentro["frame_end"]) // 2
    assert rows[f]["escala_px"] == pytest.approx(rows[f]["body_height_px"], rel=1e-9)
    assert validate_analysis(json.loads(json.dumps(a, default=lambda o: o.tolist()))) == []


def _primera_repeticion_mas_grande(sw, factor: float = 1.15):
    """El sujeto de la **primera** repetición es `factor` veces más grande, medido
    desde el punto medio de los tobillos de cada cuadro: un golfista que se alejó
    de la cámara después del primer swing.

    Es un escalado rígido, así que la cadena de la estatura crece por `factor` y la
    repetición 1 queda con una escala distinta de las otras dos. Hace falta así, y
    con **tres** repeticiones: `quality.scale_px` publica la repetición más cercana
    a la mediana, y con dos siempre elige la primera (empate, desempatado por el
    cuadro más chico), o sea que mostrar la del `quality` en vez de la de la
    repetición 1 no se notaría. Con tres y la primera afuera, sí."""
    kp = np.array(sw.keypoints, dtype=np.float64, copy=True)
    # El corte va en la quietud ENTRE la primera y la segunda repetición —entre el
    # fin de una y el address de la siguiente—, no a la mitad del clip: adentro de
    # un swing el salto de tamaño le cambia la velocidad a la segmentación y el
    # motor deja de encontrar la repetición.
    hasta = (int(sw.truth[0]["follow_end"]) + int(sw.truth[1]["address"])) // 2
    tobillo = np.nanmean(kp[:hasta][:, [H.LEFT_ANKLE, H.RIGHT_ANKLE], :], axis=1)[:, None, :]
    kp[:hasta] = tobillo + factor * (kp[:hasta] - tobillo)
    return replace(sw, keypoints=kp.astype(np.float32))


def _pose_sintetica(tmp_path, sw, fps=120.0, width=1080, height=1920):
    """Un `pose.npz` como el que escribe `kinelab_truth.mocap`: puntos ya en
    píxeles, sin video y sin estimador (igual que `tests/test_perception.py`)."""
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


def test_datos_eventos_dice_la_escala_la_referencia_y_que_repeticion_se_muestra(tmp_path):
    """`datos-eventos.json` —lo que lee la pantalla— lleva de dónde sale cada cm y
    contra qué cuadro se mide cada «vs address». Y dice **cuál** repetición es todo
    lo que se muestra: el overlay, las fotos, la tabla por evento y el `address` de
    la tabla por cuadro salen de `analysis["events"][0]`, y hasta hoy eso era un
    supuesto que nadie escribía."""
    from kinelab.explore import explore

    sw = _primera_repeticion_mas_grande(synth_swing(120.0, n_reps=3, frame=(1920, 1080), body_height_px=0.8 * 1920, amplitude_px=300.0))
    explore(None, tmp_path / "out", GOLF, height_m=ALTURA_M, pose_npz=_pose_sintetica(tmp_path, sw), nota_fuente="prueba")
    d = json.loads((tmp_path / "out" / "datos-eventos.json").read_text(encoding="utf-8"))
    a = json.loads((tmp_path / "out" / "analysis.json").read_text(encoding="utf-8"))

    assert d["repeticiones"] == len(a["reps"]) >= 3 and d["repeticion_mostrada"] == 1
    assert d["escala_fuente"] == SCALE_SOURCE_CHAIN
    # la repetición 1 tiene una escala DISTINTA de las otras a propósito: si todas
    # fueran iguales, publicar la del `quality` —la mediana entre repeticiones— en
    # vez de la de la repetición que se muestra pasaría desapercibido.
    escalas = [r["scale_px"] for r in a["reps"]]
    assert escalas[0] / max(escalas[1:]) > 1.05, f"la repetición 1 tiene la misma escala que las otras ({escalas}): el test no prueba nada"
    assert d["escala_px"] == a["reps"][0]["scale_px"], "la escala que se muestra es la de la repetición que se muestra"
    assert d["escala_px"] != a["quality"]["scale_px"]["value"], "la del `quality` es la mediana entre repeticiones, no el divisor de ninguna"
    assert d["referencia_fuente"] == "address" and d["referencia_cuadro"] == d["eventos_frame"]["address"]
    assert "escala_px" in d["columnas"]
    # y el número de la pantalla es el de la métrica, no otro
    m = a["reps"][0]["metrics"]["pelvis_sway_top_cm"]["value"]
    if m is not None:
        assert d["en_cada_evento"]["top"]["pelvis_dx_vs_address_cm"] == pytest.approx(m, abs=0.05)


def test_sin_address_la_referencia_lo_dice(tmp_path):
    """`explore.py` cae al cuadro 0 cuando no hay address, y lo hacía en silencio:
    ocho columnas se llaman `*_vs_address_*` y no había address. El valor no
    cambia; lo que cambia es que `referencia_fuente` lo dice y la pantalla lo
    muestra."""
    from kinelab.explore import explore

    # un sujeto quieto: cero repeticiones, cero eventos (test negativo de la spec)
    sw = synth_swing(120.0, n_reps=1, frame=(1920, 1080), body_height_px=0.8 * 1920, amplitude_px=300.0)
    quieto = replace(sw, keypoints=np.repeat(sw.keypoints[:1], sw.keypoints.shape[0], axis=0))
    r = explore(None, tmp_path / "out", GOLF, height_m=ALTURA_M, pose_npz=_pose_sintetica(tmp_path, quieto), nota_fuente="prueba")
    d = json.loads((tmp_path / "out" / "datos-eventos.json").read_text(encoding="utf-8"))
    assert d["eventos_frame"] == {} and d["repeticiones"] == 0 and d["repeticion_mostrada"] is None
    assert d["referencia_cuadro"] == 0 and d["referencia_fuente"] == "cuadro 0 (sin address)"
    # sin repeticiones no hay escala, así que no hay cm: la columna está, vacía
    assert "pelvis_dx_vs_address_cm" in d["columnas"] and d["escala_px"] is None and d["escala_fuente"] is None
    assert r["picos"]["hands_speed_cm_s"] is None


# --- el CUADRO de la escala, por repetición (encargo 36, contrato 2.2.0) -------------


def test_el_cuadro_de_la_escala_sale_por_repeticion(clips, capture_paths_yaml, tmp_path):
    """`reps[].scale_frame`: el cuadro donde la cadena de la estatura llegó a su
    máximo en ESA repetición, que es de donde salió su `scale_px`.

    Hasta el encargo 35 el único cuadro publicado era `quality.scale_px.frame`, y
    con dos o más repeticiones ése es el de la que aportó la mediana: mostrarlo al
    lado de la escala de otra manda a mirar un cuadro que no la produjo. El dato
    existía adentro del motor (`MetricContext.scale_detail()` devuelve `frame`) y
    `analysis.py` lo tiraba.

    El test pide que los cuadros sean **distintos entre repeticiones** y que cada
    uno caiga dentro de la suya: si `scale_frame` fuera el mismo número para todas
    —el del `quality`, por ejemplo— las dos cosas fallarían."""
    sw = _primera_repeticion_mas_grande(synth_swing(120.0, n_reps=3))
    take, _ = _take(clips, capture_paths_yaml, tmp_path, sw=sw)
    a = analyze_take(take, GOLF, write=False, height_m=ALTURA_M)
    assert len(a["reps"]) >= 3

    for r in a["reps"]:
        assert r["scale_source"] == SCALE_SOURCE_CHAIN and r["scale_px"] is not None
        assert isinstance(r["scale_frame"], int)
        assert r["frame_start"] <= r["scale_frame"] <= r["frame_end"], (
            f"el cuadro de la escala de la repetición {r['rep']} ({r['scale_frame']}) "
            f"cae fuera de ella ({r['frame_start']}–{r['frame_end']})"
        )
    cuadros = [r["scale_frame"] for r in a["reps"]]
    assert len(set(cuadros)) == len(cuadros), f"los cuadros de la escala se repiten ({cuadros}): sería uno solo para todas"
    # y el del `quality` es el de UNA de ellas, no el de todas: es justamente por
    # eso que hace falta el campo por repetición.
    assert a["quality"]["scale_px"]["frame"] in cuadros
    assert sum(1 for c in cuadros if c == a["quality"]["scale_px"]["frame"]) == 1
    assert validate_analysis(json.loads(json.dumps(a, default=lambda o: o.tolist()))) == []
    assert a["header"]["schema_version"] == "2.2.0", "campo nuevo y opcional: minor (CONTRATO.md §Versionado)"


def test_sin_cadena_el_cuadro_de_la_escala_es_null_y_valida(clips, capture_paths_yaml, tmp_path):
    """Con el fallback de escala no hay ningún máximo de cadena que mirar, así que
    `scale_frame` es `null` — y un `null` se escribe, no se omite (§Frontera)."""
    sw = synth_swing(120.0, n_reps=2)
    sw = replace(sw, keypoints=np.array(sw.keypoints, dtype=np.float32, copy=True))
    sw.keypoints[:, [H.LEFT_KNEE, H.RIGHT_KNEE]] = np.nan
    take, _ = _take(clips, capture_paths_yaml, tmp_path, sw=sw)
    a = analyze_take(take, GOLF, write=False, height_m=ALTURA_M)
    assert a["reps"]
    for r in a["reps"]:
        assert r["scale_source"] == SCALE_SOURCE_FRAME
        assert "scale_frame" in r and r["scale_frame"] is None, "el null va escrito, no omitido"
    assert validate_analysis(json.loads(json.dumps(a, default=lambda o: o.tolist()))) == []


def test_un_analysis_sin_scale_frame_sigue_validando(clips, capture_paths_yaml, tmp_path):
    """2.2.0 es **minor**: un `analysis.json` 2.1.0 —que no trae el campo— sigue
    validando contra el schema nuevo. Es la condición de §Versionado para que un
    campo nuevo no sea major, y el repo tiene 19 trabajos anteriores en
    `data/exploracion/` que no se regeneran."""
    take, _ = _take(clips, capture_paths_yaml, tmp_path, sw=synth_swing(120.0, n_reps=2))
    a = json.loads(json.dumps(analyze_take(take, GOLF, write=False, height_m=ALTURA_M), default=lambda o: o.tolist()))
    assert validate_analysis(a) == []
    viejo = json.loads(json.dumps(a))
    viejo["header"]["schema_version"] = "2.1.0"
    for r in viejo["reps"]:
        del r["scale_frame"]
    assert validate_analysis(viejo) == [], "un 2.1.0 sin el campo tiene que seguir validando"
    # y lo que NO pasa: un cuadro que no es un entero
    roto = json.loads(json.dumps(a))
    roto["reps"][0]["scale_frame"] = "118"
    assert validate_analysis(roto) != []


def test_datos_eventos_publica_el_cuadro_de_la_escala_de_cada_repeticion(tmp_path):
    """Lo que ve la pantalla. Hasta el encargo 35 `escala_cuadro` salía en `null`
    con más de una repetición —se calculaba una vez fuera del bucle— y ahora sale
    el de cada una, el de primer nivel incluido (que es el de la repetición 1)."""
    from kinelab.explore import explore

    sw = _primera_repeticion_mas_grande(synth_swing(120.0, n_reps=3, frame=(1920, 1080), body_height_px=0.8 * 1920, amplitude_px=300.0))
    explore(None, tmp_path / "out", GOLF, height_m=ALTURA_M, pose_npz=_pose_sintetica(tmp_path, sw), nota_fuente="prueba")
    d = json.loads((tmp_path / "out" / "datos-eventos.json").read_text(encoding="utf-8"))
    a = json.loads((tmp_path / "out" / "analysis.json").read_text(encoding="utf-8"))

    assert len(d["repeticiones_detalle"]) == len(a["reps"]) >= 3
    for det, r in zip(d["repeticiones_detalle"], a["reps"]):
        assert det["escala_cuadro"] == r["scale_frame"] is not None
        assert det["escala_px"] == r["scale_px"]
    cuadros = [det["escala_cuadro"] for det in d["repeticiones_detalle"]]
    assert len(set(cuadros)) == len(cuadros), f"un solo cuadro para todas las repeticiones ({cuadros})"
    # el de primer nivel es el de la repetición 1, como su `escala_px`
    assert d["escala_cuadro"] == a["reps"][0]["scale_frame"] == cuadros[0]
