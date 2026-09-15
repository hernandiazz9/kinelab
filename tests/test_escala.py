"""La escala: cuántos píxeles mide la estatura declarada, y de ahí toda métrica
en cm (`kinelab/metrics/core.py`, `CONTRATO.md` §La escala).

Lo que se prueba es la geometría, con ángulos no triviales y sin ningún número
mágico: un sujeto erguido tiene que dar exactamente la escala de antes, y uno
inclinado tiene que dar la que la trigonometría del propio test dice.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from kinelab.metrics.core import SCALE_SMOOTH_S, MetricContext, evaluate, stature_chain_px
from kinelab.metrics.generic import displacement_cm
from kinelab.metrics.registry import Metric, Reference
from kinelab.perception.framing import body_height_px
from kinelab.perception.keypoints import H
from tests.helpers.synth_swing import synth_swing

FPS = 120.0
ALTURA_M = 1.80
INCLINACION_DEG = 37.0  # no trivial a propósito (ADR-011): ni 0, ni 30, ni 45, ni 90


def _ctx(kp: np.ndarray, *, start: int = 0, end: int | None = None, altura: float | None = ALTURA_M) -> MetricContext:
    T = kp.shape[0]
    return MetricContext(
        keypoints=kp, scores=np.full((T, kp.shape[1]), 0.9, np.float32), fps=FPS, view="face_on",
        body_height_px=body_height_px(kp, FPS), events={}, frame_start=start,
        frame_end=T - 1 if end is None else end, athlete_height_m=altura,
    )


ENCIMA_DE_LA_CADERA = (H.HEAD, H.NOSE, H.NECK, H.LEFT_EYE, H.RIGHT_EYE, H.LEFT_EAR, H.RIGHT_EAR, H.LEFT_SHOULDER, H.RIGHT_SHOULDER)


def _agachar(kp: np.ndarray, deg: float, frames: slice | None = None) -> np.ndarray:
    """Agacha el tronco **hacia la cámara**: todo lo que está por encima de la
    cadera se acerca a ella por `cos(deg)`.

    Es lo que la perspectiva le hace a un golfista en address filmado `face_on`:
    el tronco se inclina sobre el eje óptico y en la imagen no se ve girar, se
    ve **más corto**. Un giro en el plano de imagen no serviría acá: ése la
    cadena lo recupera sola (el otro test)."""
    out = np.array(kp, dtype=np.float64, copy=True)
    sl = frames or slice(None)
    cadera = (out[sl, H.LEFT_HIP] + out[sl, H.RIGHT_HIP]) / 2.0
    for j in ENCIMA_DE_LA_CADERA:
        out[sl, j] = cadera + math.cos(math.radians(deg)) * (out[sl, j] - cadera)
    return out


def _inclinar(kp: np.ndarray, deg: float, frames: slice | None = None) -> np.ndarray:
    """Gira el cuerpo entero alrededor del punto medio de los tobillos, en el
    plano de imagen. Es un giro rígido: la cadena de la estatura no cambia de
    largo y la extensión vertical se acorta por `cos`."""
    out = np.array(kp, dtype=np.float64, copy=True)
    sl = frames or slice(None)
    pivot = (out[sl, H.LEFT_ANKLE] + out[sl, H.RIGHT_ANKLE]) / 2.0
    a = math.radians(deg)
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    out[sl] = (out[sl] - pivot[:, None, :]) @ R.T + pivot[:, None, :]
    return out


def test_erguido_la_cadena_es_la_altura_del_cuerpo_y_la_escala_no_cambia():
    s = synth_swing(FPS, n_reps=1)
    kp = s.keypoints.astype(np.float64)
    cadena = stature_chain_px(kp, FPS)
    bh = body_height_px(kp, FPS)
    # De pie y de frente, la suma de los eslabones ES la extensión vertical: el
    # cuerpo está sobre una sola recta vertical.
    assert cadena == pytest.approx(np.full(kp.shape[0], s.body_height_px), abs=1e-6)
    assert bh == pytest.approx(cadena, abs=1e-6)

    ctx = _ctx(kp)
    assert ctx.scale_px() == pytest.approx(s.body_height_px, abs=1e-6)
    # La conversión es exactamente la de antes: px / altura_de_cuerpo × estatura.
    assert ctx.px_to_cm(100.0, 0) == pytest.approx(100.0 / s.body_height_px * ALTURA_M * 100.0, rel=1e-9)


def test_inclinado_en_el_plano_de_imagen_la_escala_vieja_sobrelee_y_la_nueva_no():
    s = synth_swing(FPS, n_reps=1)
    kp = _inclinar(s.keypoints.astype(np.float64), INCLINACION_DEG)
    h, cos = s.body_height_px, math.cos(math.radians(INCLINACION_DEG))

    # Giro rígido: la cadena mide lo mismo; la extensión vertical, `h·cos(37°)`.
    assert stature_chain_px(kp, FPS) == pytest.approx(np.full(kp.shape[0], h), abs=1e-6)
    assert body_height_px(kp, FPS) == pytest.approx(np.full(kp.shape[0], h * cos), abs=1e-6)

    ctx = _ctx(kp)
    assert ctx.scale_px() == pytest.approx(h, abs=1e-6)
    nuevo = ctx.px_to_cm(100.0, 0)
    viejo = 100.0 / (h * cos) * ALTURA_M * 100.0  # la convención anterior, escrita a mano
    assert nuevo == pytest.approx(100.0 / h * ALTURA_M * 100.0, rel=1e-9)
    # 1/cos(37°) = 1,2521: lo que la convención vieja inflaba.
    assert viejo / nuevo == pytest.approx(1.0 / cos, rel=1e-9) == pytest.approx(1.2521, rel=1e-3)


def test_agachado_hacia_la_camara_la_escala_sale_del_cuadro_extendido_de_la_repeticion():
    """El caso real medido en el mocap: en `face_on` el golfista se agacha
    SOBRE el eje óptico, así que en la imagen la cadena se acorta igual que la
    extensión vertical y mirar el address no alcanza. Lo que lo arregla es el
    máximo dentro de la repetición: el finish, cuando se endereza."""
    s = synth_swing(FPS, n_reps=1)
    n = s.keypoints.shape[0]
    corte = n // 2
    kp = _agachar(s.keypoints.astype(np.float64), INCLINACION_DEG, slice(0, corte))
    h, cos = s.body_height_px, math.cos(math.radians(INCLINACION_DEG))
    # De la cadera para arriba hay 0,48 h de cuerpo (hombros 0,82 h, caderas 0,52 h,
    # coronilla 1,00 h): agachado, la cadena mide 0,52 h + 0,48 h·cos(37°)…
    agachado = 0.52 * h + 0.48 * h * cos
    assert float(stature_chain_px(kp, FPS)[0]) == pytest.approx(agachado, abs=1e-6)
    # …y la extensión vertical mide EXACTAMENTE lo mismo: agacharse hacia la
    # cámara engaña a las dos por igual (por eso la candidata "cadena en el
    # address" no mejoró nada sobre los diez trials de mocap).
    assert float(body_height_px(kp, FPS)[0]) == pytest.approx(agachado, abs=1e-6)

    # Con la repetición entera, la escala es la del cuerpo extendido.
    assert _ctx(kp, start=0, end=n - 1).scale_px() == pytest.approx(h, abs=1e-6)
    # Si la repetición termina antes de que se enderece, la escala es la
    # agachada: la convención no inventa una extensión que el clip no tiene.
    assert _ctx(kp, start=0, end=corte - 40).scale_px() == pytest.approx(agachado, abs=1e-6)
    # Y en cm: agachado se sobre-lee 1/(0,52 + 0,48·cos 37°) = +8,0 %.
    assert _ctx(kp, start=0, end=corte - 40).px_to_cm(100.0, 0) / _ctx(kp, start=0, end=n - 1).px_to_cm(100.0, 0) == pytest.approx(h / agachado, rel=1e-9)


def test_una_racha_corta_de_keypoints_malos_no_mueve_la_escala_y_una_larga_si():
    """La mediana móvil de `SCALE_SMOOTH_S` existe por esto: un máximo crudo lo
    rompe un solo cuadro con la cabeza en otro lado (cementerio 6 de HERENCIA)."""
    s = synth_swing(FPS, n_reps=1)
    base = _ctx(s.keypoints.astype(np.float64)).scale_px()
    media_ventana = int(round(SCALE_SMOOTH_S * FPS)) // 2  # 15 cuadros a 120 fps

    corta = np.array(s.keypoints, dtype=np.float64, copy=True)
    corta[100 : 100 + media_ventana, H.HEAD, 1] -= 200.0
    assert _ctx(corta).scale_px() == pytest.approx(base, abs=1e-6)

    larga = np.array(s.keypoints, dtype=np.float64, copy=True)
    larga[100 : 100 + 4 * media_ventana, H.HEAD, 1] -= 200.0
    assert _ctx(larga).scale_px() > base + 150.0  # una cabeza 200 px más arriba durante medio segundo SÍ es el sujeto


def test_la_escala_es_invariante_a_reescalar_la_imagen():
    """Invariante de ADR-011: la misma pose filmada más grande da los mismos cm."""
    s = synth_swing(FPS, n_reps=1)
    kp = s.keypoints.astype(np.float64)
    for k in (0.5, 2.0, 3.7):
        assert _ctx(kp * k).px_to_cm(100.0 * k, 0) == pytest.approx(_ctx(kp).px_to_cm(100.0, 0), rel=1e-9)


def test_sin_cadena_medible_cae_a_la_altura_de_cuerpo_del_cuadro():
    s = synth_swing(FPS, n_reps=1)
    kp = np.array(s.keypoints, dtype=np.float64, copy=True)
    kp[:, [H.LEFT_KNEE, H.RIGHT_KNEE]] = np.nan  # sin rodillas no hay cadena
    ctx = _ctx(kp)
    assert ctx.scale_px() is None
    esperado = 100.0 / float(ctx.body_height_px[0]) * ALTURA_M * 100.0
    assert ctx.px_to_cm(100.0, 0) == pytest.approx(esperado, rel=1e-9)
    # y sin nada que medir tampoco hay número: `null`, no un cero
    vacio = _ctx(np.full_like(kp, np.nan))
    assert vacio.scale_px() is None and vacio.px_to_cm(100.0, 0) is None


def test_sin_altura_declarada_no_hay_cm():
    s = synth_swing(FPS, n_reps=1)
    assert _ctx(s.keypoints.astype(np.float64), altura=None).px_to_cm(100.0, 0) is None


def test_una_metrica_de_desplazamiento_de_punta_a_punta():
    """El sextuplo entero con la escala nueva: el valor sale de la cadena, no de
    la extensión vertical del address."""
    from functools import partial

    s = synth_swing(FPS, n_reps=1)
    n = s.keypoints.shape[0]
    corte = n // 2
    kp = _inclinar(s.keypoints.astype(np.float64), INCLINACION_DEG, slice(0, corte))
    # Un desplazamiento conocido: el cuerpo entero se corre 50 px en x a partir
    # del corte (traslación rígida: la cadena no cambia de largo).
    kp[corte:, :, 0] += 50.0
    ctx = _ctx(kp, start=0, end=n - 1)
    ctx.events = {"address": 0, "top": corte + 40}

    m = Metric(
        id="cadera_sway_cm", unit="cm", level=1, views=("face_on",), fps_min=30.0,
        anchored_to=("address", "top"), reference_frame="image_px",
        compute=partial(displacement_cm, joints=(H.LEFT_HIP, H.RIGHT_HIP), zero="address", at="top", axis=0),
        reference=Reference("descriptive", "estimacion", "test", "sway de caderas"),
    )
    out = evaluate(m, ctx, joints=(H.LEFT_HIP, H.RIGHT_HIP))
    # px: los 50 del corrimiento más lo que el giro de 37° movió a la cadera.
    d_px = float((kp[ctx.events["top"], [H.LEFT_HIP, H.RIGHT_HIP]].mean(axis=0) - kp[0, [H.LEFT_HIP, H.RIGHT_HIP]].mean(axis=0))[0])
    assert out["value"] == pytest.approx(round(d_px / s.body_height_px * ALTURA_M * 100.0, 1), abs=0.05)
    assert out["unit"] == "cm" and out["null_reason"] is None and out["judgment_allowed"] is False
    assert out["uncertainty"]["low"] <= out["value"] <= out["uncertainty"]["high"]
