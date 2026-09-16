"""Los dos barridos vivos del encargo 13: instante sub-cuadro y encuadre.

Lo que se verifica acá es el ARNÉS, no el motor: que la verdad del cruce sea el
mismo criterio geométrico en tiempo continuo, y que los dos modelos de ruido se
comporten como dicen (el relativo deja el MDC invariante al tamaño; el absoluto
lo hace crecer). El veredicto —el sub-cuadro vive— sale de la corrida, no de
estos tests.

El barrido de **ganancia** que este archivo tenía no está más: ADR-018 la mató
en las dos vistas y el motor dejó de calcularla, así que el arnés no tiene qué
medir. La evidencia quedó en `docs/informes/2026-09-15-13-*.md`, en ADR-018 y en
`truth/reports/mdc-2026-09-15.json`, que es la corrida que la mató.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from kinelab.perception.keypoints import H
from kinelab_truth.camera import load_intrinsics
from kinelab_truth.harness import (
    NOMINAL,
    Condition,
    evaluate_subframe_condition,
    framing_table,
    project_condition,
    realize,
    realize_seeds,
    subframe_truth_s,
)
from kinelab_truth.swing import SwingParams, truth_swing

CAMERA = "iphone17pro-1080p120"


@pytest.fixture(scope="module")
def intr():
    return load_intrinsics(CAMERA)


# --- el instante sub-cuadro --------------------------------------------------


def test_subframe_truth_es_el_mismo_cruce_en_tiempo_continuo(intr):
    """La verdad cae dentro del swing y en las dos vistas es distinta: el nivel y el
    eje de viaje dependen de la cámara, así que la verdad se calcula por vista."""
    sw_ref = truth_swing(SwingParams(), fps=2400.0)
    t_face = subframe_truth_s(sw_ref, replace(NOMINAL, view="face_on"), intr, 0.1)
    t_dtl = subframe_truth_s(sw_ref, replace(NOMINAL, view="down_the_line"), intr, 0.1)
    impacto_s = truth_swing(SwingParams(), fps=240.0).events["impact"] / 240.0
    assert t_face == pytest.approx(impacto_s, abs=0.05)
    assert t_face != t_dtl


def test_subframe_sin_ruido_clava_la_verdad(intr):
    """Sin ruido el estimador tiene que dar el cruce verdadero: el sesgo es el error
    de la interpolación lineal entre dos cuadros, no del arnés."""
    from sports.golf.events import GOLF_PARAMS, _impact_subframe

    params = SwingParams()
    sw = truth_swing(params, fps=240.0)
    sw_ref = truth_swing(params, fps=2400.0)
    cond = replace(NOMINAL, view="face_on", fps=120.0, noise_frac=0.0)
    truth = subframe_truth_s(sw_ref, cond, intr, GOLF_PARAMS.subframe_axis_s)
    row = evaluate_subframe_condition(sw, cond, intr, _impact_subframe, GOLF_PARAMS, truth, seeds=1)
    assert row["n"] == 1 and row["n_null"] == 0
    assert abs(row["bias_ms"]) < 1.0


def test_subframe_es_null_desde_down_the_line(intr):
    """Invariante 6: la vista la declara el deporte y el arnés la respeta."""
    from sports.golf.events import GOLF_PARAMS, _impact_subframe

    sw = truth_swing(SwingParams(), fps=240.0)
    row = evaluate_subframe_condition(sw, replace(NOMINAL, view="down_the_line"), intr, _impact_subframe, GOLF_PARAMS, 2.35, seeds=2)
    assert row["n"] == 0 and row["n_null"] == 2
    assert any("down_the_line" in r for r in row["null_reasons"])


# --- ruido absoluto y umbral de encuadre ------------------------------------


def test_noise_px_reemplaza_al_relativo(intr):
    c_rel = Condition(noise_frac=0.006)
    c_abs = Condition(noise_frac=0.006, noise_px=3.0)
    assert c_rel.sigma_px(800.0) == pytest.approx(4.8)
    assert c_abs.sigma_px(800.0) == pytest.approx(3.0)
    assert c_rel.label() != c_abs.label()


def test_el_sorteo_por_semilla_esta_clavado(intr):
    """Por semilla se sortea PRIMERO el jitter de los cuatro eventos y DESPUÉS el
    ruido, y σ sale de la altura de cuerpo de la proyección limpia. Invertir ese
    orden mueve todos los MDC de la tabla sin que nada avise, así que el orden se
    reconstruye acá a mano en vez de compararlo contra la misma función."""
    sw = truth_swing(SwingParams(), fps=240.0)
    cond = replace(NOMINAL, view="face_on", fps=120.0)
    clean, fps, bh = project_condition(sw, cond, intr)
    step = int(round(sw.fps / cond.fps))
    rng = np.random.default_rng(0)
    jitter = {k: int(rng.integers(-1, 2)) for k in sw.events}
    ruido = rng.normal(0.0, cond.noise_frac * bh, size=clean.shape)

    px, sc, ev, fps_out = realize(sw, cond, intr, 0)
    assert fps_out == fps == 120.0
    assert ev == {k: v // step + jitter[k] for k, v in sw.events.items()}
    assert np.allclose(px, clean + ruido)
    assert np.all(sc == np.float32(0.9))
    # y el iterador da exactamente lo mismo que la función de una sola semilla
    for seed, (px2, sc2, ev2, fps2, _bh) in enumerate(realize_seeds(sw, cond, intr, 3)):
        p1, s1, e1, f1 = realize(sw, cond, intr, seed)
        assert np.array_equal(px2, p1) and np.array_equal(sc2, s1) and ev2 == e1 and fps2 == f1


def test_el_modelo_relativo_no_puede_fijar_umbral_de_encuadre(intr):
    """σ ∝ altura del cuerpo deja el MDC EXACTAMENTE invariante al tamaño: toda la
    cadena divide por la misma altura. Es el resultado que obliga al modelo
    absoluto (ESPECIFICACION 3.1 pide sólo el relativo)."""
    from sports.golf.metrics import JOINTS, REGISTRY

    sw = truth_swing(SwingParams(), fps=240.0)
    base = project_condition(sw, NOMINAL, intr)[2]
    from kinelab_truth.harness import evaluate_condition

    grande = evaluate_condition(sw, replace(NOMINAL, size_factor=1.0), intr, REGISTRY, JOINTS, seeds=4)
    chico = evaluate_condition(sw, replace(NOMINAL, size_factor=200.0 / base), intr, REGISTRY, JOINTS, seeds=4)
    for m in REGISTRY:
        if grande[m.id]["mdc"] is not None:
            assert chico[m.id]["mdc"] == pytest.approx(grande[m.id]["mdc"], abs=1e-6), m.id


def test_framing_table_cruza_con_ruido_absoluto(intr):
    """Con σ fijo en px el MDC en cm crece como 1/altura y sí cruza la tolerancia."""
    from sports.golf.metrics import JOINTS, REGISTRY

    sw = truth_swing(SwingParams(), fps=240.0)
    summary = {m.id: {"views": ["face_on"]} for m in REGISTRY}
    fr = framing_table(sw, intr, REGISTRY, JOINTS, summary, seeds=3, sigma_px=4.87)
    abs_model = fr["models"]["absoluto"]
    assert abs_model["body_height_px_min_proposed"] is not None
    assert fr["models"]["relativo"]["body_height_px_min_proposed"] is None
    fila = abs_model["per_metric"]["pelvis_sway_top_cm"]["mdc_by_body_px"]
    assert fila["100"] > fila["800"] > 0
    # los cuatro clips reales, con su altura medida
    assert {v["body_px"] for v in fr["real_clips"].values()} == {973.0, 1083.0, 1104.0, 1132.0}
