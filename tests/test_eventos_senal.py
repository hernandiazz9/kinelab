"""La señal de la que salen los eventos: centro de manos pesado por confianza,
la banda del top, y el MDC del instante sub-cuadro (encargo 18).

Los tres eventos del golf —address, top, impacto— salen de una sola señal: el
centro de las dos muñecas. El encargo 15 midió que lo que limita el top desde
`face_on` no es la regla de ADR-017 sino esa señal, porque el modelo pierde una
muñeca justo en el top y el promedio a peso igual hereda el salto. Acá están los
tests de las tres cosas que el 18 le agregó: el peso por confianza con umbral, la
banda cuando dos candidatos a top no se distinguen del ruido, y el MDC medido que
el arnés le puso al sub-cuadro.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import yaml

from kinelab.analysis import swing_signals
from kinelab.events.primitives import direction_change_farthest, direction_change_farthest_band, still_noise_px
from kinelab.events.segmentation import segment_reps
from kinelab.events.signal import hands_center
from kinelab.perception.keypoints import H, J
from kinelab.perception.posestore import PoseData, load_pose
from sports.golf.events import GOLF_PARAMS, GOLF_SEGMENTATION, GOLF_SPORT_EVENTS, GolfEventParams, detect_golf_events
from tests.helpers.synth_swing import synth_swing

REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "tests" / "data"
MDC_TABLE = REPO / "sports" / "golf" / "mdc.yaml"


# --------------------------------------------------------------------------- #
# 1 · `hands_center` pesado por confianza
# --------------------------------------------------------------------------- #


def _kp(left: tuple[float, float], right: tuple[float, float], T: int = 1) -> np.ndarray:
    k = np.full((T, J, 2), np.nan)
    k[:, H.LEFT_WRIST] = left
    k[:, H.RIGHT_WRIST] = right
    return k


def _scores(left: float, right: float, T: int = 1) -> np.ndarray:
    s = np.zeros((T, J))
    s[:, H.LEFT_WRIST] = left
    s[:, H.RIGHT_WRIST] = right
    return s


def test_sin_scores_las_dos_munecas_pesan_igual():
    """La firma vieja sigue dando lo de siempre: el punto medio."""
    got = hands_center(_kp((0.0, 0.0), (100.0, 40.0)))
    assert got[0] == pytest.approx([50.0, 20.0])


def test_el_centro_se_corre_hacia_la_muneca_mas_confiable():
    """Bug inyectado: pesar por `1 − confianza`. Con 0,8 contra 0,2 el centro tiene
    que caer al 20 % del recorrido (del lado de la confiable), no al 80 %."""
    got = hands_center(_kp((0.0, 0.0), (100.0, 0.0)), _scores(0.8, 0.2))
    assert got[0, 0] == pytest.approx(20.0), "x = (0,8·0 + 0,2·100) / 1,0"
    assert got[0, 0] < 50.0, "pesar por 1 − confianza lo pondría en 80"


def test_la_muneca_bajo_el_umbral_no_entra():
    """Por debajo del umbral la muñeca no pesa poco: no entra. El centro ES la otra."""
    got = hands_center(_kp((0.0, 0.0), (100.0, 0.0)), _scores(0.30, 0.70), min_score=0.55)
    assert got[0] == pytest.approx([100.0, 0.0])
    # Y con el umbral en 0 (el otro bug inyectado) vuelve a entrar y mueve el centro.
    sin_umbral = hands_center(_kp((0.0, 0.0), (100.0, 0.0)), _scores(0.30, 0.70), min_score=0.0)
    assert sin_umbral[0, 0] == pytest.approx(70.0)


def test_sin_ninguna_muneca_queda_nan_y_lo_rellena_el_relleno_acotado():
    """Si se caen las dos, el punto no se inventa: queda NaN y lo rellena el mismo
    relleno de la percepción, que interpola rachas cortas y deja las largas."""
    T = 20
    k = _kp((0.0, 0.0), (10.0, 0.0), T)
    k[:, H.LEFT_WRIST, 0] = np.arange(T, dtype=float)
    k[:, H.RIGHT_WRIST, 0] = np.arange(T, dtype=float) + 10.0
    s = _scores(0.9, 0.9, T)
    corta, larga = slice(4, 7), slice(10, 18)  # 3 cuadros y 8 cuadros
    s[corta, H.LEFT_WRIST] = s[corta, H.RIGHT_WRIST] = 0.1
    s[larga, H.LEFT_WRIST] = s[larga, H.RIGHT_WRIST] = 0.1
    got = hands_center(k, s, min_score=0.55, max_gap=5)
    assert np.isfinite(got[corta]).all(), "una racha de 3 cuadros se interpola (≤ max_gap)"
    assert got[5, 0] == pytest.approx(10.0), "interpolada, no inventada: la recta de los vecinos"
    assert not np.isfinite(got[larga]).any(), "una racha de 8 cuadros NO se extrapola"


def test_el_umbral_no_toca_una_senal_limpia():
    """Con las dos muñecas por encima del umbral y la misma confianza, el resultado
    es idéntico al promedio de siempre. El swing sintético tiene scores 0,9."""
    sw = synth_swing(120.0, n_reps=1)
    igual = hands_center(sw.keypoints)
    pesado = hands_center(sw.keypoints, sw.scores, min_score=GOLF_PARAMS.wrist_score_min)
    assert np.allclose(igual, pesado, equal_nan=True)


# --------------------------------------------------------------------------- #
# 2 · el top no se mueve con una muñeca ruidosa y poco confiable
# --------------------------------------------------------------------------- #


def _pose(kpts: np.ndarray, scores: np.ndarray, sw) -> PoseData:
    T = kpts.shape[0]
    framing = {"detection_rate": 1.0, "body_height_px_median": sw.body_height_px, "body_height_px_min": sw.body_height_px, "body_height_px_max": sw.body_height_px, "frac_of_frame": sw.body_height_px / sw.frame[0]}
    return PoseData(kpts.astype(np.float32), scores.astype(np.float32), np.zeros((T, 4), np.float32), sw.timestamps_s, np.zeros(T, np.uint8), {"model": "sintético", "framing": framing, "plausibility_counts": {}, "camera_motion_px": 0.0})


def _tops(kpts, scores, sw, *, wrist_score_min: float, view: str | None = None, params: GolfEventParams = GOLF_PARAMS):
    sig = swing_signals(_pose(kpts, scores, sw), sw.fps, cutoff_hz_max=GOLF_SPORT_EVENTS.cutoff_hz_max, view=view, wrist_score_min=wrist_score_min)
    cands, rejected = segment_reps(sig.speed, sw.fps, GOLF_SEGMENTATION)
    out = []
    for c in cands:
        ev, reason = detect_golf_events(sig, c, params)
        assert reason is None, reason
        out.append(ev)
    assert out, rejected
    return out


def _muneca_perdida(sw, *, alrededor_de: int, ancho: int = 6, offset_px: float = 250.0, jitter_px: float = 60.0, score: float = 0.36, seed: int = 7):
    """Copia del swing con la muñeca izquierda rota alrededor de un cuadro: el modelo
    la pone en otro lado durante una racha —un corrimiento SOSTENIDO más ruido— y le
    baja el score.

    Es el modo de falla medido en `cortado.mp4`, cuadros 32–38 (informe del 15): score
    0,35–0,43 y la x en 414 → 435 → 356 → **672 → 486 → 491 → 497** → 331 px, o sea
    unos 70 px de corrimiento sostenido con saltos encima, no ruido que se promedia a
    cero. La diferencia importa: un ruido alternado lo borra el pasabajos de la señal y
    el test no probaría nada; un corrimiento sostenido pasa el filtro entero, que es
    justo lo que se le hace al top.
    """
    kpts, scores = sw.keypoints.astype(float).copy(), sw.scores.astype(float).copy()
    idx = np.arange(alrededor_de - ancho, alrededor_de + ancho + 1)
    rng = np.random.default_rng(seed)
    kpts[idx, H.LEFT_WRIST, 0] += offset_px + rng.normal(0.0, jitter_px, idx.size)
    kpts[idx, H.LEFT_WRIST, 1] += rng.normal(0.0, jitter_px, idx.size)
    scores[idx, H.LEFT_WRIST] = score
    return kpts, scores


@pytest.mark.parametrize("fps", [120.0, 240.0])
def test_una_muneca_perdida_en_el_top_deja_de_arrastrar_al_top(fps):
    """El caso del informe del 15, con verdad conocida: el mismo swing con y sin una
    muñeca rota en el top. Con el umbral puesto el top se queda mucho más cerca del
    limpio; con el umbral en 0 —uno de los dos bugs inyectados— la muñeca rota entra
    con todo su peso y se lo lleva.

    Medido acá: a 120 fps, −1 cuadro con umbral contra −11 sin él; a 240, −9 contra
    −15. No da cero, y eso está medido aparte (ver el test del escalón)."""
    sw = synth_swing(fps, n_reps=1)
    limpio = _tops(sw.keypoints, sw.scores, sw, wrist_score_min=GOLF_PARAMS.wrist_score_min)[0]["top"].frame
    kpts, scores = _muneca_perdida(sw, alrededor_de=limpio)
    con_umbral = _tops(kpts, scores, sw, wrist_score_min=GOLF_PARAMS.wrist_score_min)[0]["top"].frame
    sin_umbral = _tops(kpts, scores, sw, wrist_score_min=0.0)[0]["top"].frame
    assert abs(con_umbral - limpio) < abs(sin_umbral - limpio), f"limpio {limpio}, con umbral {con_umbral}, sin umbral {sin_umbral}"
    assert abs(sin_umbral - limpio) >= 5, "si la muñeca rota no moviera el top, el test no probaría nada"


@pytest.mark.parametrize("fps,escalon", [(120.0, 5), (240.0, 8)])
def test_dejar_afuera_una_muneca_corre_el_centro_media_empunadura(fps, escalon):
    """Lo que el umbral CUESTA, fijado con un número para que no se agrande sin que
    nadie se entere.

    Dejar una muñeca afuera no sólo saca su error: cambia de estimador a mitad de la
    señal. El centro de las dos pasa a ser la otra muñeca sola, o sea un escalón de
    **media empuñadura** (6 px en este swing sintético) mientras dura la racha. Acá la
    muñeca izquierda está PERFECTA y sólo se le baja el score: todo lo que se mueve el
    top es ese escalón, y son 5 cuadros a 120 fps y 8 a 240.

    El swing sintético lo exagera —su top es una vuelta muy plana, y con el arco real
    de un golfista el efecto medido sobre los cinco clips del S22 fue de 1 a 2 cuadros
    y siempre hacia el cuadro que da la muñeca limpia sola—. Queda anotado como
    pregunta para el orquestador (informe del encargo 18): corregir el escalón exige
    estimar el medio vector de la empuñadura, que es justo lo que más rota en el top.
    """
    sw = synth_swing(fps, n_reps=1)
    limpio = _tops(sw.keypoints, sw.scores, sw, wrist_score_min=GOLF_PARAMS.wrist_score_min)[0]["top"].frame
    scores = sw.scores.astype(float).copy()
    scores[limpio - 4 : limpio + 5, H.LEFT_WRIST] = 0.36  # sólo el score; la posición queda intacta
    movido = _tops(sw.keypoints, scores, sw, wrist_score_min=GOLF_PARAMS.wrist_score_min)[0]["top"].frame
    assert limpio - movido == escalon, f"el escalón vale {limpio - movido} cuadros a {fps:g} fps"


def test_con_las_dos_munecas_limpias_el_top_es_el_de_siempre():
    """El umbral no cambia nada donde no hay nada que arreglar: mismo swing, mismos
    scores altos, mismos cuatro eventos con y sin umbral."""
    sw = synth_swing(120.0, n_reps=2)
    con = _tops(sw.keypoints, sw.scores, sw, wrist_score_min=GOLF_PARAMS.wrist_score_min)
    sin = _tops(sw.keypoints, sw.scores, sw, wrist_score_min=0.0)
    for a, b in zip(con, sin):
        for k in ("address", "top", "impact", "follow_end"):
            assert (a[k].frame if a[k] else None) == (b[k].frame if b[k] else None), k


# --------------------------------------------------------------------------- #
# 3 · el mocap, con scores 1,0, no se mueve en ninguna vista
# --------------------------------------------------------------------------- #


def _mocap(nombre: str, view: str, *, wrist_score_min: float, params: GolfEventParams = GOLF_PARAMS):
    pose = load_pose(FIXTURES / nombre)
    fps = float(pose.provenance["fps_real"])
    sig = swing_signals(pose, fps, cutoff_hz_max=GOLF_SPORT_EVENTS.cutoff_hz_max, view=view, wrist_score_min=wrist_score_min)
    cands, rejected = segment_reps(sig.speed, fps, GOLF_SEGMENTATION)
    assert len(cands) == 1, (cands, rejected)
    ev, reason = detect_golf_events(sig, cands[0], params)
    assert reason is None, reason
    return ev


@pytest.mark.parametrize("nombre,view,top", [("cmu-64_01-face_on", "face_on", 270), ("cmu-64_01-down_the_line", "down_the_line", 263)])
def test_el_mocap_no_se_mueve_con_la_senal_pesada(nombre, view, top):
    """La pose del mocap es geometría proyectada: todos los scores valen 1,0, así que
    pesar por confianza y filtrar por umbral tienen que ser la identidad. Es el
    control del cambio: si algún número del mocap se moviera, el peso estaría
    haciendo algo que no es pesar."""
    con = _mocap(nombre, view, wrist_score_min=GOLF_PARAMS.wrist_score_min)
    sin = _mocap(nombre, view, wrist_score_min=0.0)
    for k in ("address", "top", "impact"):
        assert con[k].frame == sin[k].frame, k
    assert con["top"].frame == top, "el top de ADR-017, sin moverse"
    assert con["top"].tol_frames == 1, "con cientos de px entre candidatos no hay banda"


# --------------------------------------------------------------------------- #
# 4 · la banda del top: dos candidatos que no se distinguen del ruido
# --------------------------------------------------------------------------- #


def _tres_vueltas() -> tuple[np.ndarray, np.ndarray]:
    """Señal 1-D con tres cambios de sentido en 20, 30 y 34, y la excursión de cada
    cuadro. Las excursiones de los tres son 100,0 · 97,0 · 98,0: gana el primero por
    2,0 sobre el tercero y por 3,0 sobre el segundo."""
    T = 50
    pos = np.zeros(T)
    for a, b, v in ((0, 20, 1.0), (20, 30, -1.0), (30, 34, 1.0), (34, T, -1.0)):
        pos[a:b] = np.arange(b - a) * v + (pos[a - 1] if a else 0.0)
    exc = np.zeros(T)
    exc[20], exc[30], exc[34] = 100.0, 97.0, 98.0
    return pos, exc


def test_la_banda_es_la_distancia_al_rival_mas_lejano():
    """Con 2σ = 4,0 px los tres candidatos entran en la banda (ventajas de 2,0 y 3,0),
    y el top se lleva la distancia en cuadros hasta el más lejano de ellos."""
    pos, exc = _tres_vueltas()
    b = direction_change_farthest_band(pos, exc, before=45, after=2, margin=4.0)
    assert b.frame == 20, "la regla de ADR-017 no cambia: gana la mayor excursión"
    assert set(b.rivals) == {30, 34}
    assert b.tol_frames == 14, "|34 − 20|, el rival más lejano"


def test_sin_rivales_la_banda_es_de_un_cuadro():
    """Con 2σ = 1,0 px ningún otro candidato llega: la elección es clara y el evento
    sale con la tolerancia de siempre."""
    pos, exc = _tres_vueltas()
    b = direction_change_farthest_band(pos, exc, before=45, after=2, margin=1.0)
    assert b.frame == 20 and b.rivals == () and b.tol_frames == 1


def test_sin_ruido_medido_no_hay_banda():
    """`margin` None (la quietud del address no dio tres cuadros): sin ruido medido no
    se inventa una banda, y el evento queda como antes del 18."""
    pos, exc = _tres_vueltas()
    assert direction_change_farthest_band(pos, exc, before=45, after=2, margin=None).tol_frames == 1
    assert direction_change_farthest(pos, exc, before=45, after=2) == 20, "el atajo sigue dando el cuadro"


def test_still_noise_px_es_el_desvio_alrededor_de_la_recta():
    """El ruido sale de los residuos de una RECTA, no de la media: una deriva lenta
    del jugador acomodándose en el address es movimiento, no ruido, y contarla como
    ruido inflaría la banda."""
    rampa = np.arange(40, dtype=float) * 3.0
    assert still_noise_px(rampa, start=0, end=39) == pytest.approx(0.0, abs=1e-9)
    ruido = rampa + np.tile([1.0, -1.0], 20)
    assert still_noise_px(ruido, start=0, end=39) == pytest.approx(1.0, rel=0.05)
    assert still_noise_px(rampa, start=0, end=1) is None, "sin tres cuadros no hay σ"


def test_la_banda_del_top_llega_al_evento_del_golf():
    """El enganche completo, sobre material real: el mocap `down_the_line` tiene un
    tercer cambio de sentido (el fondo del arco antes del impacto, cuadro 327, a
    89 px del address contra 756 del top). Con el ruido medido del clip —0,8 px— ese
    candidato está lejísimos y no hay banda; si el margen se ensancha hasta
    tragárselo, el evento lo dice en su tolerancia en vez de callarlo."""
    estrecho = _mocap("cmu-64_01-down_the_line", "down_the_line", wrist_score_min=GOLF_PARAMS.wrist_score_min)
    assert estrecho["top"].tol_frames == 1
    ancho = GolfEventParams(top_band_sigmas=2000.0)
    con_banda = _mocap("cmu-64_01-down_the_line", "down_the_line", wrist_score_min=ancho.wrist_score_min, params=ancho)
    assert con_banda["top"].frame == estrecho["top"].frame, "la banda no cambia qué cuadro gana"
    # Con un margen absurdo los tres cambios de sentido (158, 263 y 327) entran, y la
    # tolerancia es la distancia al MÁS LEJANO de ellos, que acá es el primero.
    assert con_banda["top"].tol_frames == abs(158 - 263)


# --------------------------------------------------------------------------- #
# 5 · el MDC del instante sub-cuadro, con su unidad
# --------------------------------------------------------------------------- #


def test_el_subcuadro_lleva_el_mdc_del_arnes_con_su_unidad():
    """El MDC del instante sub-cuadro lo midió el arnés (encargo 13) y vivía sólo en
    `mdc.yaml`. Ahora viaja en el evento, con su unidad y su procedencia — y la
    procedencia del MDC (`medido_aqui`, sale del arnés) no es la del VALOR
    (`estimacion`). El número no se escribe a mano acá: se lee de la tabla."""
    fila = ((yaml.safe_load(MDC_TABLE.read_text(encoding="utf-8"))["events"]["impact"])["subframe"])
    sub = _mocap("cmu-64_01-face_on", "face_on", wrist_score_min=GOLF_PARAMS.wrist_score_min)["impact"].subframe
    assert sub["mdc"]["value"] == pytest.approx(float(fila["mdc_ms"]), abs=5e-4)
    assert sub["mdc"]["unit"] == fila["unit"] == "ms"
    assert sub["mdc"]["provenance"] == "medido_aqui"
    assert sub["provenance"] == "estimacion", "el MDC está medido; el valor sigue siendo estimación"
    assert "mdc.yaml" in sub["mdc"]["source"]


def test_el_mdc_del_subcuadro_esta_aunque_el_cruce_salga_null():
    """Desde `down_the_line` el cruce sale `null` por vista (invariante 6). El MDC
    describe al estimador, no a esta toma: tiene que estar igual, con su razón al
    lado. Un campo esperado nunca se omite (CONTRATO §Frontera)."""
    sub = _mocap("cmu-64_01-down_the_line", "down_the_line", wrist_score_min=GOLF_PARAMS.wrist_score_min)["impact"].subframe
    assert sub["fraction"] is None and sub["null_reason"]
    assert sub["mdc"] is not None and sub["mdc"]["unit"] == "ms"


# --------------------------------------------------------------------------- #
# 6 · una sola señal de manos: el CSV y el overlay salen de la misma que los
#     eventos (encargo 31, punto 3)
#
# `kinelab/explore.py` llamaba a `swing_signals(pose, fps)` sin el
# `wrist_score_min` del deporte: los eventos salían de la señal con umbral
# (encargo 18) y el CSV y el overlay, de la señal a peso igual. En los cuadros
# donde una muñeca cae bajo el umbral —justo donde el modelo la pierde— las dos
# difieren, y el dibujo mostraba un centro de manos que no era el que había
# elegido el evento.
# --------------------------------------------------------------------------- #


def test_la_tabla_por_cuadro_usa_la_misma_senal_que_los_eventos():
    """Con una muñeca perdida, la tabla por cuadro calculada con el umbral del deporte
    es **exactamente** la señal de la que salen los eventos, y difiere de la que salía
    antes en los cuadros en que la muñeca cae bajo el umbral. El número de cuadros que
    cambian no se quema: se cuenta de los propios scores."""
    from kinelab.explore import per_frame_table

    sw = synth_swing(120.0, n_reps=1)
    limpio = _tops(sw.keypoints, sw.scores, sw, wrist_score_min=GOLF_PARAMS.wrist_score_min)[0]["top"].frame
    kpts, scores = _muneca_perdida(sw, alrededor_de=limpio)
    pose = _pose(kpts, scores, sw)
    umbral = GOLF_PARAMS.wrist_score_min

    _, con = per_frame_table(pose, sw.fps, 1.75, None, wrist_score_min=umbral)
    _, sin = per_frame_table(pose, sw.fps, 1.75, None)
    sig = swing_signals(pose, sw.fps, wrist_score_min=umbral)

    v_con = np.array([np.nan if r["hands_speed_bh_s"] is None else r["hands_speed_bh_s"] for r in con])
    v_sin = np.array([np.nan if r["hands_speed_bh_s"] is None else r["hands_speed_bh_s"] for r in sin])
    assert np.allclose(v_con, sig.speed, equal_nan=True, atol=1e-9), "el CSV es la señal de los eventos, no otra"
    bajos = int(np.count_nonzero((scores[:, H.LEFT_WRIST] < umbral) | (scores[:, H.RIGHT_WRIST] < umbral)))
    assert bajos > 0, "el fixture tiene que tener cuadros bajo el umbral o el test no prueba nada"
    assert np.count_nonzero(~np.isclose(v_con, v_sin, equal_nan=True)) > 0, "y difiere de la señal a peso igual"


def test_con_los_scores_altos_la_tabla_por_cuadro_no_se_mueve():
    """El control: sin ninguna muñeca bajo el umbral, pasar el umbral es la identidad.
    Si esto se moviera, el umbral estaría haciendo algo que no es filtrar."""
    from kinelab.explore import per_frame_table

    sw = synth_swing(120.0, n_reps=2)
    pose = _pose(sw.keypoints.astype(float), sw.scores.astype(float), sw)
    names, con = per_frame_table(pose, sw.fps, 1.75, None, wrist_score_min=GOLF_PARAMS.wrist_score_min)
    _, sin = per_frame_table(pose, sw.fps, 1.75, None)
    assert con == sin, "todas las columnas, no sólo las de manos"
