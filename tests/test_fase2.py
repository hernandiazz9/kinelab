"""Fase 2, tests mínimos: eventos sobre swings sintéticos, negativos de
segmentación, registro, contrato, corrección manual y el CLI de punta a punta."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pytest

from functools import partial

from kinelab.__main__ import main as kinelab_main
from kinelab.analysis import analyze_take, build_analysis, swing_signals
from kinelab.contract.validate import validate_analysis
from kinelab.events.manual import Edit, EventCollisionError, apply_edits
from kinelab.events.primitives import MissingEvent, direction_change_farthest, direction_changes, stable_window_start, still_run_start, stillness_signal, subframe_crossing
from kinelab.events.segmentation import SegmentationParams, segment_reps
from kinelab.events.signal import principal_axis
from kinelab.ingest.__main__ import ingest_clip
from kinelab.ingest.capture_paths import load_capture_paths
from kinelab.ingest.gate import CaptureJson
from kinelab.metrics.core import MetricContext, evaluate
from kinelab.metrics.generic import duration_ms, repeatability_curves, repeatability_scalar
from kinelab.metrics.registry import FPS_MIN_TOL, Metric, Reference, Registry, fps_min_met, judgment_allowed
from kinelab.perception.gaps import interpolate_gaps
from kinelab.perception.keypoints import H, J
from kinelab.perception.posestore import PoseData, load_pose, save_pose
from kinelab.tools.golfdb_eval import event_error_stats
from sports.golf.config import GOLF
from sports.golf.events import GOLF_SEGMENTATION, GOLF_SPORT_EVENTS, detect_golf_events
from sports.golf.metrics import JOINTS as GOLF_JOINTS
from sports.golf.metrics import REGISTRY as GOLF_METRICS
from tests.helpers.synth_swing import synth_swing

REPO = Path(__file__).resolve().parents[1]


def _pose(sw) -> PoseData:
    T = sw.keypoints.shape[0]
    return PoseData(sw.keypoints, sw.scores, np.zeros((T, 4), np.float32), sw.timestamps_s, np.zeros(T, np.uint8), {"model": "sintético", "framing": {"detection_rate": 1.0, "body_height_px_median": sw.body_height_px, "body_height_px_min": sw.body_height_px, "body_height_px_max": sw.body_height_px, "frac_of_frame": sw.body_height_px / sw.frame[0]}, "plausibility_counts": {}, "camera_motion_px": 0.0})


def _detect(sw):
    sig = swing_signals(_pose(sw), sw.fps)
    cands, rejected = segment_reps(sig.speed, sw.fps, GOLF_SEGMENTATION)
    out = []
    for c in cands:
        ev, reason = detect_golf_events(sig, c)
        assert reason is None, reason
        out.append({k: v.frame if v else None for k, v in ev.items()})
    return out, rejected


@pytest.mark.parametrize("fps,noise,tol", [(120.0, 0.0, (2, 1, 1, 3)), (120.0, 2.0, (3, 2, 2, 4)), (240.0, 0.0, (3, 1, 1, 4))])
def test_golf_events_on_synthetic_swings(fps, noise, tol):
    sw = synth_swing(fps, n_reps=3, noise_px=noise)
    reps, rejected = _detect(sw)
    assert len(reps) == 3, (reps, rejected)
    for got, truth in zip(reps, sw.truth):
        for name, t in zip(("address", "top", "impact", "follow_end"), tol):
            assert abs(got[name] - truth[name]) <= t, f"{name} @ {fps} fps: {got[name]} vs {truth[name]}"


def test_events_are_fps_invariant_in_seconds():
    a = _detect(synth_swing(60.0, n_reps=2))[0]
    b = _detect(synth_swing(240.0, n_reps=2))[0]
    for ra, rb in zip(a, b):
        for name in ("address", "top", "impact"):
            assert abs(ra[name] / 60.0 - rb[name] / 240.0) <= 2 / 60.0, name


# --- el top es el cambio de sentido MÁS LEJANO, no el último (ADR-017, encargo 15) --
#
# La regla vieja (ADR-008 tal como estaba en código) tomaba el último cambio de signo
# de la velocidad de las manos proyectada. Desde `down_the_line` el eje principal queda
# casi vertical —el movimiento hacia el objetivo cae sobre el eje óptico— y aparece un
# tercer cambio, el fondo del arco justo antes del impacto, que ganaba por ser el
# último. El swing sintético no lo reproduce: su arco no vuelve sobre sí mismo. Por eso
# el caso vive en un swing de mocap real, en `tests/data/` (ver su README).

FIXTURES = REPO / "tests" / "data"


def _mocap_rep(nombre: str, view: str) -> dict:
    """La única repetición del fixture de mocap, detectada de punta a punta."""
    pose = load_pose(FIXTURES / nombre)
    fps = float(pose.provenance["fps_real"])
    sig = swing_signals(pose, fps, cutoff_hz_max=GOLF_SPORT_EVENTS.cutoff_hz_max, view=view)
    cands, rejected = segment_reps(sig.speed, fps, GOLF_SEGMENTATION)
    assert len(cands) == 1, (cands, rejected)
    ev, reason = detect_golf_events(sig, cands[0])
    assert reason is None, reason
    axis = principal_axis(sig.hands, ev["address"].frame, ev["impact"].frame)
    proj = sig.hands @ axis
    return {"ev": ev, "cambios": direction_changes(proj, before=ev["impact"].frame, after=ev["address"].frame)}


def test_top_from_down_the_line_is_the_farthest_change_and_not_the_last():
    """El mismo swing (mocap CMU 64_01) desde las dos vistas. La verdad 3-D del arnés
    pone el top en 269 (`events_3d`, `top_far`); desde `face_on` el motor da 270 y
    desde `down_the_line`, 263. Con la regla del último daba 327: el fondo del arco,
    a 5 cuadros del impacto, con un downswing de 41,7 ms."""
    face = _mocap_rep("cmu-64_01-face_on", "face_on")
    dtl = _mocap_rep("cmu-64_01-down_the_line", "down_the_line")
    assert face["ev"]["top"].frame == 270, "desde face_on el top no se mueve"
    assert abs(dtl["ev"]["top"].frame - 263) <= 2, dtl["ev"]["top"].frame
    assert dtl["ev"]["top"].method == "direction_change_farthest"
    # Los tres cambios de sentido de `down_the_line`, con el elegido en el medio: el
    # último está a menos de 10 cuadros del impacto y el primero, pegado al address.
    assert len(dtl["cambios"]) == 3 and dtl["cambios"][-1] != dtl["ev"]["top"].frame
    assert dtl["ev"]["impact"].frame - dtl["cambios"][-1] <= 10
    # Address e impacto no los toca esta regla: siguen donde estaban en el informe del 07.
    assert (dtl["ev"]["address"].frame, dtl["ev"]["impact"].frame) == (146, 332)
    assert (face["ev"]["address"].frame, face["ev"]["impact"].frame) == (141, 329)
    # Y el downswing deja de ser una ficción de 5 cuadros: la verdad 3-D dice 508,3 ms.
    ms = lambda a, b: (b - a) / 120.0 * 1000.0  # noqa: E731
    assert abs(ms(dtl["ev"]["top"].frame, dtl["ev"]["impact"].frame) - 508.3) < 100.0


def test_farthest_direction_change_is_neither_the_last_nor_the_nearest():
    """Tres cambios de sentido con excursiones conocidas: el más lejano (10) no es el
    último (30) ni el más cercano (20). Los tres bugs —quedarse con el último, con el
    primero o con el más cercano— dan cuadros distintos y rompen este test."""
    x = np.concatenate([np.linspace(0, 10, 11), np.linspace(10, 2, 11)[1:], np.linspace(2, 6, 11)[1:], np.linspace(6, 0, 11)[1:]])
    exc = np.abs(x - x[0])
    assert direction_changes(x, before=40, after=0) == [10, 20, 30]
    assert [round(float(exc[k]), 1) for k in (10, 20, 30)] == [10.0, 2.0, 6.0]
    assert direction_change_farthest(x, exc, before=40, after=0) == 10
    # Sin ningún cambio de sentido (monótona) no hay top, y se dice: nunca un cuadro forzado.
    assert direction_change_farthest(np.arange(41.0), exc, before=40, after=0) is None


def test_a_reversal_in_the_first_frame_is_not_a_top():
    """El segmento que sale del propio `after` queda afuera: si contara, el top podría
    caer en el cuadro del address y el backswing duraría 0 ms. Medido en vid1.mp4: el
    segundo candidato (un movimiento que no es un swing) producía address 862 = top 862
    e inventaba una repetición que antes se rechazaba con `sin_top`."""
    x = np.concatenate([[0.0, 0.1], np.linspace(0.1, -9.0, 20)[1:], np.linspace(-9.0, -2.0, 11)[1:]])
    v = np.gradient(x)
    assert v[0] > 0 > v[1], "la velocidad se invierte entre el cuadro 0 y el 1"
    assert direction_changes(x, before=30, after=0) == [20], "y aun así el 0 no es un cambio de sentido"
    assert direction_change_farthest(x, np.abs(x - x[0]), before=30, after=0) == 20


def test_still_and_walking_give_zero_reps():
    T, fps = 1200, 120.0
    still = np.zeros(T) + 0.02
    walking = 1.0 + 0.05 * np.sin(np.arange(T) / 7.0)  # velocidad sostenida sin picos
    for s in (still, walking):
        cands, _ = segment_reps(s, fps, GOLF_SEGMENTATION)
        assert cands == []


def test_registry_rules_and_judgment():
    r = Registry("t")
    with pytest.raises(ValueError, match="nivel 3"):
        Metric(id="x_factor", unit="deg", level=3, views=("face_on",), fps_min=60, anchored_to=(), reference_frame="image_px")
    # ADR-019: para llegar a `True` la métrica declara además el MDC validado en
    # material real; el rango con procedencia `pares` ya lo tenía.
    m = r.register(Metric(id="sway_cm", unit="cm", level=1, views=("face_on",), fps_min=60, anchored_to=("address", "top"), reference_frame="image_px", mdc=1.5, mdc_validation="material_real", reference=Reference("range", "pares", "x", "y", range=(0.0, 4.0))))
    ok = dict(view="face_on", fps_real=120, fps_provenance="medido_aqui")
    assert judgment_allowed(m, **ok) is True
    assert judgment_allowed(m, view="down_the_line", fps_real=120, fps_provenance="medido_aqui") is False
    assert judgment_allowed(m, view="face_on", fps_real=30, fps_provenance="medido_aqui") is False
    # ADR-016: con la tasa de cuadros sin verificar no hay juicio, aunque estén
    # el MDC, el fps y la vista. El eje del tiempo es un supuesto.
    assert judgment_allowed(m, view="face_on", fps_real=120, fps_provenance="sin_verificar") is False
    wide = Metric(id="wide", unit="cm", level=1, views=("face_on",), fps_min=60, anchored_to=(), reference_frame="image_px", mdc=5.0, mdc_validation="material_real", reference=Reference("range", "pares", "x", "y", range=(0.0, 4.0)))
    assert judgment_allowed(wide, **ok) is False, "MDC mayor que el rango: no es juicio"
    with pytest.raises(ValueError, match="repetida"):
        r.register(m)


# --- la tolerancia de `fps_min` (encargo 10) ----------------------------------
#
# La tabla del arnés barre en fps NOMINALES enteros (240 · 120 · 60 · 30) y las tasas
# de video reales son NTSC (239,76 · 119,88 · 59,94 · 29,97), más el redondeo del
# teléfono: el original del S22 da 29,998. Sin tolerancia, ningún clip real de 30 fps
# llega a un `fps_min` de 30. La constante vive en un solo lugar del registro.


def _fps_metric(fps_min: float) -> Metric:
    """Una métrica que tiene TODO lo demás en orden, para que lo único que decida
    `judgment_allowed` sea el fps. Desde ADR-019 «todo lo demás» incluye el MDC
    validado en material real y un rango con procedencia fuerte."""
    return Metric(
        id="m", unit="cm", level=1, views=("face_on",), fps_min=fps_min, anchored_to=(),
        reference_frame="image_px", mdc=1.0, mdc_validation="material_real",
        reference=Reference("range", "pares", "registro de prueba", "métrica de prueba", range=(0.0, 4.0)),
    )


@pytest.mark.parametrize(
    "fps_real,fps_min,met",
    [
        (29.998, 30.0, True),   # el original del Galaxy S22 Ultra, medido
        (29.97, 30.0, True),    # NTSC
        (119.88, 120.0, True),  # NTSC
        (59.94, 60.0, True),
        (239.76, 240.0, True),
        (30.0, 30.0, True),     # el nominal exacto sigue pasando
        (120.0, 30.0, True),    # de sobra
        (29.8, 30.0, False),    # 0,67 % abajo: no pasa
        (29.0, 30.0, False),
        (60.0, 120.0, False),   # la tasa de abajo entera: nunca
    ],
)
def test_fps_min_tolerates_ntsc_rates_against_the_nominal_table(fps_real, fps_min, met):
    m = _fps_metric(fps_min)
    assert fps_min_met(m, fps_real) is met
    assert judgment_allowed(m, view="face_on", fps_real=fps_real, fps_provenance="medido_aqui") is met


def test_fps_min_tolerance_is_half_a_percent_and_lives_in_one_place():
    assert FPS_MIN_TOL == 0.005
    m = _fps_metric(30.0)
    borde = 30.0 * (1.0 - FPS_MIN_TOL)  # 29,85
    assert fps_min_met(m, borde) is True and fps_min_met(m, borde - 1e-6) is False
    # El sextuplo lo reporta con la misma regla, no con una comparación propia.
    ctx = MetricContext(keypoints=np.zeros((10, J, 2), np.float32), scores=np.ones((10, J), np.float32), fps=29.998, view="face_on", body_height_px=np.full(10, 900.0), events={}, frame_start=0, frame_end=9)
    assert evaluate(m, ctx)["fps_min_met"] is True
    assert evaluate(_fps_metric(60.0), ctx)["fps_min_met"] is False


def _golf_metrics_at(fps: float, view: str = "face_on") -> dict:
    """Las métricas de golf sobre la primera repetición de un swing sintético a `fps`."""
    sw = synth_swing(fps, n_reps=2)
    sig = swing_signals(_pose(sw), sw.fps, view=view)
    cands, rejected = segment_reps(sig.speed, sw.fps, GOLF_SEGMENTATION)
    assert cands, rejected
    events, reason = detect_golf_events(sig, cands[0])
    assert reason is None, reason
    ctx = MetricContext(
        keypoints=interpolate_gaps(sw.keypoints, 5), scores=sw.scores, fps=sw.fps, view=view,
        body_height_px=sig.body_height, events={k: v.frame for k, v in events.items() if v},
        frame_start=cands[0].start, frame_end=cands[0].end, fps_provenance="medido_aqui",
        athlete_height_m=1.80, hands_speed=sig.speed,
    )
    return {m.id: evaluate(m, ctx, joints=GOLF_JOINTS.get(m.id, ())) for m in GOLF_METRICS}


def test_a_2997_fps_swing_computes_the_30fps_metrics_and_nulls_the_rest():
    """Un clip NTSC de 30 fps: las métricas de `fps_min` 30 dan número; las de 60
    y 120 quedan en `null` con la razón. Antes de la tolerancia no daba ninguna."""
    m = _golf_metrics_at(29.97)
    por_fps: dict[float, list[str]] = {}
    for mid, v in m.items():
        por_fps.setdefault(v["fps_min"], []).append(mid)
    assert set(por_fps) == {30.0, 60.0, 120.0}, por_fps

    for mid in por_fps[30.0]:
        v = m[mid]
        assert v["fps_min_met"] is True, mid
        if "face_on" not in GOLF_METRICS.get(mid).views:
            # `pelvis_thrust_top_cm` es de la otra vista: muere por vista, no por fps.
            assert v["value"] is None and "vista" in v["null_reason"], mid
            continue
        assert v["value"] is not None and v["null_reason"] is None, (mid, v["null_reason"])

    for fps_min in (60.0, 120.0):
        for mid in por_fps[fps_min]:
            v = m[mid]
            assert v["value"] is None and v["fps_min_met"] is False, mid
            assert v["null_reason"] == f"fps_real 29.97 por debajo de fps_min {fps_min:g}", mid
            assert v["judgment_allowed"] is False, mid


def test_manual_edits_keep_detected_and_reject_collisions():
    ev = {"id": "top", "frame": 100, "t_s": 1.0, "tol_frames": 1, "uncertainty_s": 0.01, "method": "x", "manual": False, "frame_detected": None}
    mk = lambda rep, base: {"rep": rep, "address": {**ev, "id": "address", "frame": base}, "top": {**ev, "frame": base + 100}, "impact": {**ev, "id": "impact", "frame": base + 130}, "follow_end": None}
    events = [mk(1, 0), mk(2, 500)]
    out = apply_edits(events, [Edit(1, "top", 110, "hoy")], fps=100.0, order=("address", "top", "impact", "follow_end"))
    assert out[0]["top"]["frame"] == 110 and out[0]["top"]["frame_detected"] == 100 and out[0]["top"]["manual"] is True
    assert events[0]["top"]["frame"] == 100, "no muta"
    with pytest.raises(EventCollisionError):
        apply_edits(events, [Edit(1, "top", 130, "hoy")], fps=100.0, order=("address", "top", "impact", "follow_end"))
    with pytest.raises(EventCollisionError):
        apply_edits(events, [Edit(2, "address", 129, "hoy")], fps=100.0, order=("address", "top", "impact", "follow_end"))


def test_golfdb_stats():
    s = event_error_stats({"a": {"top": 10, "impact": 20}, "b": {"top": 30, "impact": 40}}, {"a": {"top": 11, "impact": 20}, "b": {"top": 31, "impact": 43}})
    assert s["top"]["bias_frames"] == 1.0 and s["top"]["within_1"] == 1.0
    assert s["impact"]["within_2"] == 0.5


def _synthetic_take(clips, capture_paths_yaml, tmp_path, sw=None):
    if "hevc120" not in clips:
        pytest.skip("sin fixture hevc120")
    paths = load_capture_paths(capture_paths_yaml)
    take, cap = ingest_clip(clips["hevc120"], athlete="t", gesture="driver", view="face_on", capture_path_id="test-hevc-120-cfr", capture_paths=paths, sport=GOLF, data_dir=tmp_path, day=date(2026, 9, 12))
    sw = sw if sw is not None else synth_swing(120.0, n_reps=2)
    save_pose(take, _pose(sw))
    return take, sw


def test_analyze_and_adjust_end_to_end(clips, capture_paths_yaml, tmp_path):
    take, sw = _synthetic_take(clips, capture_paths_yaml, tmp_path)
    a = analyze_take(take, GOLF)
    assert (take / "analysis.json").is_file() and validate_analysis(json.loads((take / "analysis.json").read_text())) == []
    assert a["summary"]["rep_count"] == 2 and a["quality"]["verdict"] == "confiable"
    assert a["series"]["params"]["series_hz"] <= 10.0 and a["header"]["source"]["fps_real"] == 120.0
    top = a["events"][0]["top"]["frame"]
    rc = kinelab_main(["adjust", str(take), "--rep", "1", "--event", "top", "--frame", str(top + 3)])
    assert rc == 0
    b = json.loads((take / "analysis.json").read_text())
    assert b["events"][0]["top"]["frame"] == top + 3 and b["events"][0]["top"]["frame_detected"] == top and b["events"][0]["top"]["manual"]
    assert (take / f"analysis.{a['header']['engine_version']}.json").is_file(), "el anterior se conserva"
    rc = kinelab_main(["adjust", str(take), "--rep", "1", "--event", "top", "--frame", str(a["events"][0]["impact"]["frame"])])
    assert rc == 1, "top después del impacto: colisión"
    assert json.loads((take / "analysis.json").read_text())["events"][0]["top"]["frame"] == top + 3, "una corrección inválida no toca nada"


def test_schema_rejects_renamed_field(clips, capture_paths_yaml, tmp_path):
    take, _ = _synthetic_take(clips, capture_paths_yaml, tmp_path)
    a = analyze_take(take, GOLF, write=False)
    a["summary"]["rep_cnt"] = a["summary"].pop("rep_count")
    errs = validate_analysis(json.loads(json.dumps(a, default=lambda o: o.tolist())))
    assert any("rep_cnt" in e for e in errs) and any("rep_count" in e for e in errs)


def _judgeable_registry() -> Registry:
    """Un registro de prueba con UNA métrica que sí cumple ADR-019: MDC validado
    en material real y rango de referencia con procedencia `pares`.

    Existe porque desde ADR-019 el registro de golf **no tiene ninguna métrica de
    juicio**, y sin al menos una no habría nada que apagar: el test de ADR-016
    pasaría por vacío y dejaría de probar lo suyo. El rango es ancho a propósito
    (600–1200 ms contra un MDC de 12,601): lo que se prueba acá es la procedencia
    del fps, no el ancho del rango, que tiene su propio test."""
    reg = Registry("test-adr-016", mdc_note="registro de prueba")
    reg.register(
        Metric(
            id="backswing_duration_ms", unit="ms", level=1, views=("face_on", "down_the_line"),
            fps_min=120.0, anchored_to=("address", "top"), reference_frame="image_px",
            compute=partial(duration_ms, start="address", end="top"),
            mdc=12.601, mdc_validation="material_real",
            reference=Reference("range", "pares", "registro de prueba", "tiempo de address a top", range=(600.0, 1200.0)),
        )
    )
    return reg


def _analyze_with(take: Path, registry: Registry) -> dict:
    """`analyze_take` no acepta un registro (usa el del deporte); esto es lo mismo
    un escalón más abajo, leyendo el `capture.json` y el `pose.npz` del take."""
    capture = CaptureJson.model_validate_json((take / "capture.json").read_text(encoding="utf-8"))
    return build_analysis(take, capture, load_pose(take), GOLF, registry=registry, height_m=1.80)


def test_a_declared_path_keeps_the_numbers_and_kills_every_judgment(clips, capture_paths_yaml, tmp_path):
    """ADR-016 de punta a punta: con la MISMA pose y el MISMO fps, cambiar la
    procedencia de `medido_aqui` a `sin_verificar` no mueve un valor y apaga
    todos los juicios. Y el aviso queda primero en `warnings`.

    Corre con un registro de prueba (`_judgeable_registry`) y no con el de golf:
    desde ADR-019 el de golf no habilita ningún juicio, y este test necesita uno
    encendido para poder demostrar que el camino declarado lo apaga."""
    take, _ = _synthetic_take(clips, capture_paths_yaml, tmp_path)
    reg = _judgeable_registry()
    calibrado = _analyze_with(take, reg)
    con_mdc = [mid for mid, v in calibrado["reps"][0]["metrics"].items() if v["judgment_allowed"]]
    assert con_mdc, "el fixture tiene que llegar con al menos una métrica de juicio"

    cj = json.loads((take / "capture.json").read_text(encoding="utf-8"))
    cj["capture_path_calibrated"], cj["fps_provenance"] = False, "sin_verificar"
    (take / "capture.json").write_text(json.dumps(cj), encoding="utf-8")
    declarado = _analyze_with(take, reg)

    a, b = calibrado["reps"][0]["metrics"], declarado["reps"][0]["metrics"]
    assert [a[mid]["value"] for mid in a] == [b[mid]["value"] for mid in a], "la medición no cambia"
    assert all(not v["judgment_allowed"] for v in b.values())
    assert all(v["fps_provenance"] == "sin_verificar" for v in b.values())
    assert declarado["header"]["source"]["fps_provenance"] == "sin_verificar"
    assert declarado["warnings"][0].startswith("Tasa de cuadros sin verificar")
    assert "reproduce a la velocidad de captura" in declarado["warnings"][0]
    assert not any(w.startswith("Tasa de cuadros sin verificar") for w in calibrado["warnings"])

    # Y el registro de golf, sobre la misma toma calibrada, no enciende ninguno
    # (ADR-019): es la otra mitad de lo mismo, con el gate y el fps en orden.
    cj["capture_path_calibrated"], cj["fps_provenance"] = True, "medido_aqui"
    (take / "capture.json").write_text(json.dumps(cj), encoding="utf-8")
    golf = analyze_take(take, GOLF, write=False, height_m=1.80)
    assert all(not v["judgment_allowed"] for r in golf["reps"] for v in r["metrics"].values())


def test_a_calibrated_path_without_gate_says_the_gate_did_not_run(clips, capture_paths_yaml, tmp_path):
    """El aviso decía algo FALSO, y lo encontró el encargo 24 con el primer camino
    calibrado del proyecto: con `s22ultra-slomo-fhd240-recorte-mac` el
    `analysis.json` salía diciendo «camino declarado sin cronómetro … 240.15 fps
    asumidos», y esos 240,15 están **medidos** con un cronómetro filmado.

    Son dos casos distintos y el aviso los tiene que separar. Camino declarado: no
    hay cronómetro, la tasa es un supuesto. Camino calibrado sin gate (modo
    exploración): la tasa está medida, y lo que nadie verificó es que este archivo
    haya venido por ese camino —eso lo hace `fps_matches_path`, que es del gate—.
    Eso último es lo que ADR-016 dice de verdad."""
    take, _ = _synthetic_take(clips, capture_paths_yaml, tmp_path)
    cj = json.loads((take / "capture.json").read_text(encoding="utf-8"))
    assert cj["capture_path_calibrated"] is True

    # camino CALIBRADO, procedencia sin verificar: es exactamente lo que arma el
    # modo exploración (`kinelab/explore.py`), que no corre el gate.
    cj["fps_provenance"] = "sin_verificar"
    (take / "capture.json").write_text(json.dumps(cj), encoding="utf-8")
    w = analyze_take(take, GOLF, write=False, height_m=1.80)["warnings"][0]
    assert w.startswith("Tasa de cuadros sin verificar")
    assert "el gate no corrió" in w and "medida con cronómetro" in w
    assert "asumidos" not in w and "camino declarado sin cronómetro" not in w, "no puede decir que una tasa medida es un supuesto"

    # y el camino DECLARADO sigue diciendo lo suyo, que ahí sí es verdad
    cj["capture_path_calibrated"] = False
    (take / "capture.json").write_text(json.dumps(cj), encoding="utf-8")
    w2 = analyze_take(take, GOLF, write=False, height_m=1.80)["warnings"][0]
    assert "fps asumidos" in w2 and "reproduce a la velocidad de captura" in w2
    assert "el gate no corrió" not in w2

    # las dos frases arrancan igual: el front y `explore.py` las buscan por prefijo
    assert w2.startswith("Tasa de cuadros sin verificar")


def test_schema_requires_fps_provenance_in_header_and_in_every_metric(clips, capture_paths_yaml, tmp_path):
    """ADR-016: la procedencia del fps no es opcional. Un `analysis.json` sin
    ella no valida — ni en el header ni en una métrica —, así que no puede
    escribirse un análisis que esconda bajo qué supuesto se midió el tiempo."""
    take, _ = _synthetic_take(clips, capture_paths_yaml, tmp_path)
    a = json.loads(json.dumps(analyze_take(take, GOLF, write=False, height_m=1.80), default=lambda o: o.tolist()))
    assert validate_analysis(a) == []

    sin_header = json.loads(json.dumps(a))
    del sin_header["header"]["source"]["fps_provenance"]
    assert any("fps_provenance" in e for e in validate_analysis(sin_header))

    sin_metrica = json.loads(json.dumps(a))
    mid = next(iter(sin_metrica["reps"][0]["metrics"]))
    del sin_metrica["reps"][0]["metrics"][mid]["fps_provenance"]
    assert any("fps_provenance" in e for e in validate_analysis(sin_metrica))

    mal = json.loads(json.dumps(a))
    mal["header"]["source"]["fps_provenance"] = "a_ojo"
    assert any("a_ojo" in e for e in validate_analysis(mal)), "procedencia fuera del enum"


# --- ADR-019: contención del juicio (encargo 27) -------------------------------
#
# Dos condiciones INDEPENDIENTES, cada una con su test. Una mira el instrumento
# (¿el MDC está validado contra material real?) y la otra mira contra qué se
# compara (¿hay rango, y de dónde salió?). Los 21 `judgment_allowed: true` del
# 15/9 salieron de que la segunda no existía: una referencia descriptiva sin
# rango pasaba.


def _judgeable(**over) -> Metric:
    """Una métrica que cumple TODO lo que pide ADR-019, para poder sacarle una
    cosa por vez."""
    base = dict(
        id="m", unit="cm", level=1, views=("face_on",), fps_min=60.0, anchored_to=(),
        reference_frame="image_px", mdc=1.0, mdc_validation="material_real",
        reference=Reference("range", "pares", "fuente de prueba", "definición de prueba", range=(0.0, 4.0)),
    )
    return Metric(**{**base, **over})


_OK = dict(view="face_on", fps_real=120.0, fps_provenance="medido_aqui")


def test_a_metric_with_both_adr_019_conditions_is_judgment():
    """El caso positivo, que es el que hace que los negativos signifiquen algo."""
    assert judgment_allowed(_judgeable(), **_OK) is True


def test_an_unvalidated_mdc_is_not_judgment_even_with_everything_else_in_place():
    """Es el estado de las catorce métricas de golf: MDC medido en el arnés
    nivel 0 —proyección más ruido, sin estimador— y por eso `sin_validar`."""
    m = _judgeable(mdc_validation="sin_validar")
    assert m.mdc is not None and judgment_allowed(m, **_OK) is False
    assert Metric(id="x", unit="cm", level=1, views=("face_on",), fps_min=30.0, anchored_to=(), reference_frame="image_px").mdc_validation == "sin_validar", "el default es el conservador"
    with pytest.raises(ValueError, match="mdc_validation"):
        _judgeable(mdc_validation="medido_aqui")  # no es una procedencia: es otro enum


def test_a_validated_mdc_without_a_range_is_not_judgment():
    """La condición que faltaba. `CONTEXTO.md` define juicio como comparar contra
    un rango: sin rango no hay contra qué juzgar. La regla vieja
    (`ref is None or ref.range_width is None`) daba `True` en los dos casos de acá."""
    assert judgment_allowed(_judgeable(reference=None), **_OK) is False
    descriptiva = Reference("descriptive", "pares", "fuente de prueba", "definición de prueba")
    assert judgment_allowed(_judgeable(reference=descriptiva), **_OK) is False


@pytest.mark.parametrize("provenance", ["estimacion", "sin_verificar"])
def test_a_range_with_a_weak_provenance_is_not_judgment(provenance):
    """Invariante 12: ante la duda, el hueco antes que el número inventado. Es el
    caso de las referencias de golf, todas `estimacion`."""
    ref = Reference("range", provenance, "fuente de prueba", "definición de prueba", range=(0.0, 4.0))
    assert judgment_allowed(_judgeable(reference=ref), **_OK) is False


@pytest.mark.parametrize("provenance", ["medido_aqui", "pares", "fabricante"])
def test_a_range_with_a_strong_provenance_is_judgment(provenance):
    ref = Reference("range", provenance, "fuente de prueba", "definición de prueba", range=(0.0, 4.0))
    assert judgment_allowed(_judgeable(reference=ref), **_OK) is True


def test_no_golf_metric_is_judgment_today():
    """0 de 21 (ADR-019). Con la vista, el fps y la procedencia del fps todos en
    orden —que es el caso de `cortado3-lento.mp4`, el único clip que pasó el gate
    entero—, ninguna de las métricas de golf habilita juicio."""
    assert len(GOLF_METRICS) > 0
    for m in GOLF_METRICS:
        for view in m.views:
            assert judgment_allowed(m, view=view, fps_real=240.15, fps_provenance="medido_aqui") is False, m.id
        assert m.mdc_validation == "sin_validar", m.id
    assert GOLF_METRICS.version == "0.3.0"


def test_repeatability_without_a_noise_floor_is_null_with_a_reason():
    """`CONTEXTO.md` §piso de ruido: sin el piso del propio pipeline, una SD entre
    repeticiones no separa al atleta del instrumento. `n` se conserva."""
    escalar = repeatability_scalar([10.0, 12.0, 14.0])
    assert escalar["value"] is None and escalar["noise_floor"] is None
    assert escalar["n"] == 3 and "piso de ruido" in escalar["null_reason"]
    assert escalar["kind"] == "sd_abs"

    curvas = repeatability_curves([np.linspace(0, 1, 20), np.linspace(0, 2, 30), np.array([1.0, 2.0])])
    assert curvas["value"] is None and curvas["noise_floor"] is None
    assert curvas["n"] == 2, "la curva de 2 puntos no entra, y eso el n lo sigue diciendo"
    assert "piso de ruido" in curvas["null_reason"] and curvas["kind"] == "dtw_normalized"


def test_the_two_adr_019_warnings_reach_the_analysis(clips, capture_paths_yaml, tmp_path):
    """Los dos avisos son dos cosas distintas: la regla (nada de esto es juicio) y
    el estado de la tabla de MDC del deporte. Y el aviso de la regla no se escribe
    si el archivo se contradice: con un registro que sí habilita juicio, no sale."""
    take, _ = _synthetic_take(clips, capture_paths_yaml, tmp_path)
    a = analyze_take(take, GOLF, write=False, height_m=1.80)
    regla = [w for w in a["warnings"] if "Ninguno de estos números es un juicio" in w]
    tabla = [w for w in a["warnings"] if "no está validado en material real" in w]
    assert len(regla) == 1 and len(tabla) == 1, a["warnings"]
    assert "ADR-019" in regla[0] and "material real" in regla[0]
    assert "sin estimador de pose" in tabla[0] and "nadie verificó" in tabla[0]
    assert all(isinstance(w, str) for w in a["warnings"])
    assert validate_analysis(json.loads(json.dumps(a, default=lambda o: o.tolist()))) == []

    con_juicio = _analyze_with(take, _judgeable_registry())
    assert any(v["judgment_allowed"] for r in con_juicio["reps"] for v in r["metrics"].values())
    assert not any("Ninguno de estos números es un juicio" in w for w in con_juicio["warnings"]), "un aviso que se contradice con el archivo no se escribe"


def test_the_subframe_mdc_says_it_is_not_validated():
    """El MDC del cruce conserva `provenance: medido_aqui` —lo midió el arnés, y
    el schema de `subframe.mdc` no admite campos nuevos—, y es el `source` el que
    dice de qué arnés viene y que no está validado (ADR-019)."""
    from sports.golf.events import _subframe_mdc

    mdc = _subframe_mdc()
    assert mdc is not None and mdc["provenance"] == "medido_aqui"
    assert "mdc.yaml" in mdc["source"], "lo fija tests/test_eventos_senal.py"
    assert "arnés nivel 0" in mdc["source"] and "sin estimador" in mdc["source"]
    assert "sin verificar" in mdc["source"] and "ADR-019" in mdc["source"]


# --- contrato 2.0.0: lo que murió y lo que entró (ADR-018, encargo 16) ---------


def test_schema_rejects_the_dead_gain_and_sequence_order(clips, capture_paths_yaml, tmp_path):
    """ADR-018. Los dos campos no sólo dejan de escribirse: el validador los
    RECHAZA. Sin esto, un `analysis.json` con `summary.gain` seguiría pasando y
    la ganancia podría volver por la puerta de atrás en cualquier reescritura."""
    take, _ = _synthetic_take(clips, capture_paths_yaml, tmp_path)
    a = json.loads(json.dumps(analyze_take(take, GOLF, write=False, height_m=1.80), default=lambda o: o.tolist()))
    assert validate_analysis(a) == []
    assert "gain" not in a["summary"]
    assert all("sequence_order" not in e for e in a["events"])
    assert a["header"]["schema_version"] == "2.0.0"

    con_gain = json.loads(json.dumps(a))
    con_gain["summary"]["gain"] = {"pelvis_to_torso": {"value": 1.49}}
    assert any("gain" in e for e in validate_analysis(con_gain)), "summary.gain tiene que rebotar"

    con_orden = json.loads(json.dumps(a))
    con_orden["events"][0]["sequence_order"] = "pelvis>torso>arm"
    assert any("sequence_order" in e for e in validate_analysis(con_orden)), "events[].sequence_order tiene que rebotar"


def test_schema_requires_metric_version_and_scale_px(clips, capture_paths_yaml, tmp_path):
    """Los dos campos nuevos del 2.0.0 son OBLIGATORIOS. `metric_version` es lo
    único que avisa que una métrica cambió de valor sin cambiar de nombre (las
    ocho en cm, con la escala del encargo 14); `quality.scale_px` es el divisor
    de esas ocho, que hasta el 2.0.0 no quedaba escrito en ningún lado."""
    take, _ = _synthetic_take(clips, capture_paths_yaml, tmp_path)
    a = json.loads(json.dumps(analyze_take(take, GOLF, write=False, height_m=1.80), default=lambda o: o.tolist()))
    assert validate_analysis(a) == []

    sin_version = json.loads(json.dumps(a))
    mid = next(iter(sin_version["reps"][0]["metrics"]))
    del sin_version["reps"][0]["metrics"][mid]["metric_version"]
    assert any("metric_version" in e for e in validate_analysis(sin_version))

    sin_escala = json.loads(json.dumps(a))
    del sin_escala["quality"]["scale_px"]
    assert any("scale_px" in e for e in validate_analysis(sin_escala))

    # y el sub-cuadro tiene su LUGAR para el MDC, con la forma que pide el contrato
    con_mdc = json.loads(json.dumps(a))
    sf = con_mdc["events"][0]["impact"]["subframe"]
    sf["mdc"] = {"value": 2.9269, "unit": "ms", "provenance": "medido_aqui", "source": "sports/golf/mdc.yaml §events.impact.subframe"}
    assert validate_analysis(con_mdc) == []
    sf["mdc"] = {"value": 2.9269, "unit": "ms"}
    assert any("provenance" in e or "source" in e for e in validate_analysis(con_mdc)), "si el mdc está, va entero"
    sf["mdc"] = {"value": 2.9269, "unit": "ms", "provenance": "a_ojo", "source": "x"}
    assert any("a_ojo" in e for e in validate_analysis(con_mdc)), "procedencia fuera del enum"


def test_metric_version_travels_from_the_registry_to_the_json(clips, capture_paths_yaml, tmp_path):
    """Las ocho métricas en cm están en 1.1.0 (encargo 14: cambió la convención de
    escala) y el resto en 1.0.0; el registro de golf, en 0.3.0 (ADR-019, que no
    movió ningún valor y por eso no movió ningún `metric_version`). Lo que declara
    el registro es lo que viaja al JSON, incluso en una métrica en `null`."""
    take, _ = _synthetic_take(clips, capture_paths_yaml, tmp_path)
    a = analyze_take(take, GOLF, write=False, height_m=1.80)
    assert a["header"]["registry_version"] == "0.3.0"
    m = a["reps"][0]["metrics"]
    en_cm = sorted(mid for mid in m if m[mid]["unit"] == "cm")
    assert len(en_cm) == 8, en_cm
    assert all(m[mid]["metric_version"] == "1.1.0" for mid in en_cm)
    assert all(m[mid]["metric_version"] == "1.0.0" for mid in m if m[mid]["unit"] != "cm")
    nulo = m["pelvis_thrust_top_cm"]
    assert nulo["value"] is None and nulo["metric_version"] == "1.1.0", "un null tampoco pierde la versión"


def test_quality_scale_px_is_the_divisor_of_the_cm_metrics(clips, capture_paths_yaml, tmp_path):
    """El número que se publica tiene que ser EL que dividió, no uno parecido:
    se reconstruye la métrica en cm a mano desde la escala y los keypoints."""
    take, sw = _synthetic_take(clips, capture_paths_yaml, tmp_path)
    a = analyze_take(take, GOLF, write=False, height_m=1.80)
    sp = a["quality"]["scale_px"]
    assert sp["value"] is not None and sp["method"].startswith("max_stature_chain_px")
    assert 0 <= sp["frame"] < sw.keypoints.shape[0]
    ev = a["events"][0]
    kp = sw.keypoints.astype(float)
    hip = lambda f: (kp[f, H.LEFT_HIP] + kp[f, H.RIGHT_HIP]) / 2
    dx = hip(ev["top"]["frame"])[0] - hip(ev["address"]["frame"])[0]
    esperado = dx / sp["value"] * 1.80 * 100.0
    assert a["reps"][0]["metrics"]["pelvis_sway_top_cm"]["value"] == pytest.approx(esperado, abs=0.11)


def test_the_uncertainty_band_follows_each_event_tolerance(clips, capture_paths_yaml, tmp_path):
    """Invariante 8: la banda sale del `tol_frames` de cada evento ancla, no de un
    ±1 fijo. Con tol 1 es lo de siempre; con tol 3 en el top, el backswing se
    ensancha exactamente tres cuadros a cada lado y el follow, que no se ancla al
    top, no se mueve."""
    take, _ = _synthetic_take(clips, capture_paths_yaml, tmp_path)
    a = analyze_take(take, GOLF, write=False, height_m=1.80)
    bs = a["reps"][0]["metrics"]["backswing_duration_ms"]
    assert bs["uncertainty"]["method"].startswith("±1 cuadro(s)")
    ancho = bs["uncertainty"]["high"] - bs["uncertainty"]["low"]
    assert ancho == pytest.approx(2 * 1000.0 / 120.0, abs=0.2)

    e, r = a["events"][0], a["reps"][0]
    pose = load_pose(take)
    ctx = MetricContext(
        keypoints=pose.keypoints.astype(float), scores=pose.scores, fps=120.0, view="face_on",
        body_height_px=np.full(pose.keypoints.shape[0], 900.0),
        events={k: e[k]["frame"] for k in ("address", "top", "impact", "follow_end") if e.get(k)},
        frame_start=r["frame_start"], frame_end=r["frame_end"],
        fps_provenance="medido_aqui", athlete_height_m=1.80, tolerances={"top": 3},
    )
    out = evaluate(GOLF_METRICS.get("backswing_duration_ms"), ctx)
    assert out["uncertainty"]["high"] - out["uncertainty"]["low"] == pytest.approx(2 * 3 * 1000.0 / 120.0, abs=0.2)
    assert out["uncertainty"]["method"].startswith("±3 cuadro(s)")


def test_repo_example_is_valid():
    p = REPO / "data" / "examples" / "analysis.example.json"
    if not p.is_file():
        pytest.skip("todavía no se generó el ejemplo")
    d = json.loads(p.read_text(encoding="utf-8"))
    assert validate_analysis(d) == []
    # el ejemplo se genera con el motor (tests/helpers/gen_analysis_example.py), no
    # a mano: hasta el encargo 16 se editaba a mano y quedó con `gain`, con
    # `sequence_order` y con el `method` que ADR-017 había reemplazado.
    assert d["header"]["schema_version"] == "2.0.0" and d["header"]["registry_version"] == "0.3.0"
    assert "gain" not in d["summary"] and all("sequence_order" not in e for e in d["events"])
    assert all(e["top"]["method"] == "direction_change_farthest" for e in d["events"])
    assert d["quality"]["scale_px"]["value"] is not None
    assert all(m["metric_version"] for r in d["reps"] for m in r["metrics"].values())


def test_metrics_in_analysis(clips, capture_paths_yaml, tmp_path):
    take, sw = _synthetic_take(clips, capture_paths_yaml, tmp_path)
    a = analyze_take(take, GOLF, write=True, height_m=1.80)
    assert validate_analysis(json.loads((take / "analysis.json").read_text())) == []
    m = a["reps"][0]["metrics"]
    bs = m["backswing_duration_ms"]
    assert abs(bs["value"] - 900.0) <= 25 and bs["unit"] == "ms" and bs["null_reason"] is None
    # Antes de ADR-019 esto era `bs["judgment_allowed"] is (bs["mdc"] is not None)`:
    # tener MDC alcanzaba. Ahora no: el MDC de la tabla del arnés existe y sigue
    # viajando en el sextuplo, pero no está validado en material real y la
    # referencia de golf no tiene rango, así que no hay juicio.
    assert bs["mdc"] is not None, "el MDC de la tabla del arnés sigue viajando en el sextuplo"
    assert bs["judgment_allowed"] is False, "MDC del arnés sin validar y sin rango: no es juicio (ADR-019)"
    assert all(v["judgment_allowed"] is False for v in m.values()), "0 de 0 juicios con el registro de golf"
    # La procedencia del fps viaja en cada métrica y en el header (ADR-016).
    assert bs["fps_provenance"] == "medido_aqui" and "medido_aqui" in bs["uncertainty"]["method"]
    assert a["header"]["source"]["fps_provenance"] == "medido_aqui"
    assert all(m[mid]["fps_provenance"] == "medido_aqui" for mid in m)
    assert bs["uncertainty"]["low"] < bs["value"] < bs["uncertainty"]["high"]
    assert m["pelvis_thrust_top_cm"]["value"] is None and "down_the_line" in m["pelvis_thrust_top_cm"]["null_reason"]
    assert abs(m["pelvis_sway_top_cm"]["value"]) < 1.0, "la pelvis sintética no se mueve"
    assert a["summary"]["metrics"]["backswing_duration_ms"]["repeatability"]["kind"] == "sd_abs"
    assert a["summary"]["metrics"]["hands_speed_curve_top_to_impact"]["repeatability"]["n"] == 2
    # ADR-019: sin piso de ruido medido, la repetibilidad no es una medición.
    for mid in ("backswing_duration_ms", "hands_speed_curve_top_to_impact"):
        rep = a["summary"]["metrics"][mid]["repeatability"]
        assert rep["value"] is None and rep["noise_floor"] is None and "piso de ruido" in rep["null_reason"], mid
    b = analyze_take(take, GOLF, write=False)
    assert b["reps"][0]["metrics"]["pelvis_sway_top_cm"]["value"] is None and "altura" in b["reps"][0]["metrics"]["pelvis_sway_top_cm"]["null_reason"]


# --- instante sub-cuadro del impacto (encargo 02) -----------------------------------
#
# El cuadro entero del impacto NO cambia: sigue siendo el de `peak_window`. Lo que se
# prueba acá es el instante estimado ENTRE dos cuadros, contra una verdad que no sabe
# nada de cómo se estima (`synth_swing` la calcula por mínima distancia sobre el modelo
# continuo). El swing lleva `hands_tilt` y `hands_miss_px`: sin ellos el arco de bajada
# pasa exactamente por el punto de address y cualquier eje da el mismo cruce, así que el
# test no distinguiría ningún bug (invariante 15).

SUBFRAME_TOL_FRAMES = 0.1  # cuadros: el error del estimador sin ruido, con margen


def _impact_subframe(sw, view: str = "face_on"):
    """(señal, eventos) de la primera repetición de un swing sintético."""
    sig = swing_signals(_pose(sw), sw.fps, view=view)
    cands, rejected = segment_reps(sig.speed, sw.fps, GOLF_SEGMENTATION)
    assert cands, rejected
    events, reason = detect_golf_events(sig, cands[0])
    assert reason is None, reason
    return sig, events


def test_impact_subframe_lands_on_the_known_crossing():
    """Cruce conocido en 71,56 (fracción 0,6 entre el 71 y el 72) a 30 fps."""
    sw = synth_swing(30.0, n_reps=2, hands_tilt=0.2, hands_miss_px=100.0)
    _, events = _impact_subframe(sw)
    impact = events["impact"]
    sf = impact.subframe
    truth = sw.truth[0]["impact_cross"]
    assert sf["null_reason"] is None and sf["fraction"] is not None
    assert 0.5 < sf["fraction"] < 0.7, "la verdad cae en una fracción no trivial: ni 0 ni 0,5"
    assert sf["frame_after"] == sf["frame_before"] + 1
    assert sf["frame_before"] in (impact.frame - 1, impact.frame), "el cruce es contiguo al cuadro del evento"
    cruce = sf["frame_before"] + sf["fraction"]
    assert abs(cruce - truth) <= SUBFRAME_TOL_FRAMES, f"{cruce} vs verdad {truth}"
    # El par de cuadros equivocado no pasaría: el test mira el instante absoluto.
    assert abs(cruce + 1 - truth) > SUBFRAME_TOL_FRAMES and abs(cruce - 1 - truth) > SUBFRAME_TOL_FRAMES
    assert abs(sf["t_sub_s"] - cruce / sw.fps) < 1e-4, "t_sub_s es el cruce en segundos"
    assert abs(cruce - impact.frame) <= 0.6, "el cuadro entero es el cuadro más cercano al cruce"
    assert sf["t_sub_s"] != impact.t_s and sf["uncertainty_s"] < impact.uncertainty_s, "más fino que ±1 cuadro"
    assert sf["provenance"] == "estimacion" and sf["views"] == ["face_on"] and sf["method"]
    assert sf["components"]["slope_px_per_frame"] > 0 and sf["components"]["noise_px"] is not None


@pytest.mark.parametrize("fps", [30.0, 60.0, 120.0, 240.0])
def test_impact_subframe_tracks_the_crossing_at_every_fps(fps):
    sw = synth_swing(fps, n_reps=2, hands_tilt=0.15, hands_miss_px=60.0)
    _, events = _impact_subframe(sw)
    sf = events["impact"].subframe
    cruce = sf["frame_before"] + sf["fraction"]
    assert abs(cruce - sw.truth[0]["impact_cross"]) <= SUBFRAME_TOL_FRAMES, f"{fps} fps: {cruce}"
    assert 0.0 < sf["uncertainty_frames"] < 1.0 and sf["uncertainty_s"] > 0


@pytest.mark.parametrize("fps", [30.0, 60.0, 120.0])
def test_impact_subframe_uncertainty_covers_the_error_with_noise(fps):
    """Con 2 px de ruido por keypoint el error crece, y la banda reportada crece con él."""
    sw = synth_swing(fps, n_reps=2, hands_tilt=0.15, hands_miss_px=60.0, noise_px=2.0)
    _, events = _impact_subframe(sw)
    sf = events["impact"].subframe
    err = abs(sf["frame_before"] + sf["fraction"] - sw.truth[0]["impact_cross"])
    assert sf["components"]["noise_frames"] > 0, "el ruido del clip entra en la banda"
    assert err <= SUBFRAME_TOL_FRAMES + 2 * sf["uncertainty_frames"], f"{fps} fps: error {err:.3f}, banda {sf['uncertainty_frames']}"


def test_impact_subframe_changes_with_the_wrong_axis_and_with_y_flipped():
    """Los tres bugs inyectados de la invariante 15 que esta señal puede tener."""
    sw = synth_swing(30.0, n_reps=2, hands_tilt=0.2, hands_miss_px=100.0)
    sig, events = _impact_subframe(sw)
    sf = events["impact"].subframe
    bueno = sf["frame_before"] + sf["fraction"]
    P = np.asarray(sig.hands_raw, dtype=float)
    address, frame = events["address"].frame, events["impact"].frame
    r = k = max(2, int(round(0.1 * sw.fps)))  # los mismos de GolfEventParams a 30 fps

    def cruce(Q, axis=None):
        if axis is None:
            axis = principal_axis(Q, frame - k, frame + k)
            if float((Q[frame + k] - Q[frame - k]) @ axis) < 0:
                axis = -axis
        c = subframe_crossing(Q @ axis, float(Q[address] @ axis), near=frame, lo=frame - r, hi=frame + r)
        return None if c.fraction is None else c.frame_before + c.fraction, axis

    _, eje = cruce(P)
    lejos = lambda t: t is None or abs(t - bueno) > SUBFRAME_TOL_FRAMES

    # 1. El eje equivocado: sólo `y`. El arco es tangente a la altura del address.
    c_y = subframe_crossing(P[:, 1], float(P[address, 1]), near=frame, lo=frame - r, hi=frame + r)
    assert lejos(None if c_y.fraction is None else c_y.frame_before + c_y.fraction)
    # 2. El eje equivocado: sólo `x`, sin la componente vertical del viaje.
    c_x = subframe_crossing(P[:, 0], float(P[address, 0]), near=frame, lo=frame - r, hi=frame + r)
    assert lejos(None if c_x.fraction is None else c_x.frame_before + c_x.fraction)
    # 3. El signo de `y` invertido en el eje y no en las posiciones: el bug clásico de
    #    mezclar "y hacia abajo" (image_px) con "y hacia arriba" en el mismo cálculo.
    assert lejos(cruce(P, axis=eje * np.array([1.0, -1.0]))[0])
    # Y al revés: espejar el clip ENTERO es una simetría, no un bug. El instante no
    #    puede moverse (test metamórfico, ADR-011).
    espejo, _ = cruce(P * np.array([1.0, -1.0]))
    assert espejo is not None and abs(espejo - bueno) < 1e-9


def test_subframe_crossing_says_why_when_there_is_no_clear_crossing():
    """Sin cruce, con más de uno, lejos del evento o sin nivel: `fraction` es None y hay razón."""
    sube = np.arange(20.0)
    c = subframe_crossing(sube, 100.0, near=10, lo=6, hi=14)
    assert c.fraction is None and "no cruza" in c.null_reason
    tiembla = np.array([-1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0])
    c = subframe_crossing(tiembla, 0.0, near=6, lo=3, hi=9)
    assert c.fraction is None and "ambiguo" in c.null_reason and "veces" in c.null_reason
    c = subframe_crossing(sube, 3.5, near=10, lo=1, hi=14)
    assert c.fraction is None and "no es contiguo" in c.null_reason
    c = subframe_crossing(sube, float("nan"), near=10, lo=6, hi=14)
    assert c.fraction is None and "sin nivel" in c.null_reason
    # Y el caso claro, con la cuenta a mano: cruza 0 entre el 10 (−1) y el 11 (+3).
    recta = np.concatenate([np.full(10, -5.0), [-1.0, 3.0], np.full(8, 7.0)])
    c = subframe_crossing(recta, 0.0, near=10, lo=8, hi=13)
    assert c.frame_before == 10 and abs(c.fraction - 0.25) < 1e-9 and c.slope == 4.0


def test_impact_subframe_is_null_from_down_the_line():
    """La dirección de viaje de las manos en el impacto apunta al objetivo: desde
    down_the_line queda sobre el eje óptico y no se puede medir (invariante 6)."""
    sw = synth_swing(30.0, n_reps=2, hands_tilt=0.2, hands_miss_px=100.0)
    _, events = _impact_subframe(sw, view="down_the_line")
    sf = events["impact"].subframe
    assert sf["fraction"] is None and sf["t_sub_s"] is None
    assert "down_the_line" in sf["null_reason"] and "face_on" in sf["null_reason"]


def test_analysis_carries_the_impact_subframe(clips, capture_paths_yaml, tmp_path):
    take, sw = _synthetic_take(clips, capture_paths_yaml, tmp_path)
    a = analyze_take(take, GOLF)
    assert validate_analysis(json.loads((take / "analysis.json").read_text())) == []
    assert a["header"]["schema_version"] == "2.0.0", "mueren gain y sequence_order (ADR-018)"
    for rep in a["events"]:
        assert rep["impact"]["subframe"]["fraction"] is not None
        assert rep["impact"]["frame"] == json.loads((take / "analysis.json").read_text())["events"][rep["rep"] - 1]["impact"]["frame"]
        for otro in ("address", "top"):
            assert rep[otro]["subframe"] is None, "hoy sólo el impacto lo tiene, y el campo está igual"


class SwingEstimator:
    """Estimador falso que devuelve un swing sintético, un cuadro por llamada.

    El `FakeEstimator` de `test_perception` devuelve una persona quieta y por eso no
    produce eventos. Éste hace que el modo exploración recorra el camino completo
    —video → pose → eventos → `datos-eventos.json`— sin tocar el modelo real.
    """

    def __init__(self, sw) -> None:
        self.sw, self.calls = sw, 0

    def reset(self) -> None:
        self.calls = 0

    def __call__(self, frame):
        from kinelab.perception.estimator import FrameEstimate

        i = min(self.calls, self.sw.keypoints.shape[0] - 1)
        self.calls += 1
        kp = self.sw.keypoints[i]
        x0, y0 = np.nanmin(kp, axis=0)
        x1, y1 = np.nanmax(kp, axis=0)
        return FrameEstimate(kp[None].astype(np.float32), np.full((1, kp.shape[0]), 0.9, np.float32), np.array([[x0, y0, x1, y1]], np.float32), True)

    def provenance(self) -> dict:
        return {"model": "swing sintético", "provider": "falso"}


def test_explore_writes_the_impact_subframe(clips, tmp_path):
    """De un video a `datos-eventos.json`: el instante entre cuadros llega a la pantalla."""
    from kinelab.explore import explore

    if "hevc120" not in clips:
        pytest.skip("sin fixture hevc120")
    sw = synth_swing(120.0, n_reps=1, still_s=0.5, backswing_s=0.8, downswing_s=0.25, follow_s=0.55, recover_s=0.8, amplitude_px=20.0, body_height_px=70.0, frame=(96, 96), hands_tilt=0.2, hands_miss_px=5.0)
    r = explore(clips["hevc120"], tmp_path / "out", GOLF, height_m=1.8, estimator=SwingEstimator(sw))
    escrito = json.loads((tmp_path / "out" / "datos-eventos.json").read_text(encoding="utf-8"))
    assert escrito["eventos_subcuadro"] == r["eventos_subcuadro"], "lo que se muestra es lo que se escribió"
    sf = r["eventos_subcuadro"]["impact"]
    impacto = r["eventos_frame"]["impact"]
    assert sf["frame_before"] in (impacto - 1, impacto) and sf["frame_after"] == sf["frame_before"] + 1
    assert 0.0 <= sf["fraction"] <= 1.0 and sf["null_reason"] is None
    assert abs(sf["frame_before"] + sf["fraction"] - sw.truth[0]["impact_cross"]) <= SUBFRAME_TOL_FRAMES
    assert abs(sf["t_sub_s"] - (sf["frame_before"] + sf["fraction"]) / r["fps_archivo"]) < 1e-3


# --------------------------------------------------------------------------- #
# El fin del acompañamiento se busca DENTRO de la repetición (encargo 31)
#
# Sin cota, `stable_window_start` pedía `follow_still_s` de quietud desde el
# impacto y seguía hasta encontrarla: si la pausa del finish era más corta que
# el umbral, el evento caía en la quietud PREVIA AL GESTO SIGUIENTE. Medido en
# `cortado3-lento.mp4` (auditoría del 16/9 §1): repetición 1 con address 1052,
# impacto 1364 y candidato hasta 1765, `follow_end` 1978 y 2556,7 ms de
# acompañamiento — el address del swing siguiente. La cota es el fin del propio
# candidato de segmentación (§6 D-4); ningún umbral se movió.
# --------------------------------------------------------------------------- #


def _reps_con_eventos(sw):
    """Los eventos de cada candidato, con el objeto crudo (para ver el hueco y su razón)."""
    sig = swing_signals(_pose(sw), sw.fps)
    cands, rejected = segment_reps(sig.speed, sw.fps, GOLF_SEGMENTATION)
    out = []
    for c in cands:
        ev, reason = detect_golf_events(sig, c)
        assert reason is None, reason
        out.append((c, ev))
    assert len(out) == 2, (out, rejected)
    return sig, out


def test_sin_quietud_en_su_repeticion_el_follow_end_es_null_con_razon():
    """Dos repeticiones seguidas cuya pausa del finish (0,2 s) es más corta que la
    quietud que pide el deporte (0,3 s): el fin del acompañamiento **no existe** y lo
    dice. Lo que no puede pasar es que sea la quietud previa al swing siguiente."""
    sw = synth_swing(120.0, n_reps=2, hold_s=0.2, recover_s=0.6)
    sig, reps = _reps_con_eventos(sw)
    cand1, ev1 = reps[0]
    cand2, ev2 = reps[1]
    assert isinstance(ev1["follow_end"], MissingEvent), "sin quietud propia no hay evento"
    assert not ev1["follow_end"], "un hueco es falso en un booleano: el motor lo escribe como null"
    razon = ev1["follow_end"].reason
    assert str(ev1["impact"].frame) in razon and str(cand1.end) in razon, razon
    assert "0,3 s" in razon and "fin de la repetición" in razon, razon

    # Y lo que hacía antes, con la misma señal y el mismo umbral: sin la cota la
    # búsqueda encuentra quietud, pero es la del gesto siguiente.
    thr = max(GOLF_SPORT_EVENTS.params.still_speed_max, GOLF_SPORT_EVENTS.params.noise_factor * sig.noise_floor_bh_s)
    still = stillness_signal(sig.speed, sw.fps, GOLF_SPORT_EVENTS.params.still_smooth_s)
    sin_cota = stable_window_start(still, sw.fps, max_speed=thr, min_duration_s=GOLF_SPORT_EVENTS.params.follow_still_s, after=ev1["impact"].frame)
    need = round(GOLF_SPORT_EVENTS.params.follow_still_s * sw.fps)
    assert sin_cota is not None and sin_cota + need - 1 > cand1.end, "sin cota, la ventana de quietud se sale de la repetición"
    assert still_run_start(still, max_speed=thr, end=ev2["address"].frame) <= sin_cota <= ev2["address"].frame, (
        "y la quietud que encuentra es la del address de la repetición 2, que es el bug de cortado3-lento"
    )


def test_con_quietud_dentro_de_la_repeticion_el_follow_end_es_el_cuadro_correcto():
    """El mismo swing con la pausa del finish más larga que el umbral: el evento sale,
    marca el INICIO de la quietud (qué es el finish para el entrenador no lo decide el
    código, y por eso el `method` lo dice) y cae dentro de su propio candidato."""
    sw = synth_swing(120.0, n_reps=2, hold_s=0.4, recover_s=0.6)
    _, reps = _reps_con_eventos(sw)
    for (cand, ev), truth in zip(reps, sw.truth):
        fe = ev["follow_end"]
        assert fe, "con quietud propia el evento existe"
        assert abs(fe.frame - truth["follow_end"]) <= 2, (fe.frame, truth["follow_end"])
        assert ev["impact"].frame < fe.frame <= cand.end, "dentro de su repetición, de punta a punta"
        assert fe.method == "stable_window_in_rep"


@pytest.mark.parametrize("nombre,view", [("cmu-64_01-face_on", "face_on"), ("cmu-64_01-down_the_line", "down_the_line")])
def test_el_mocap_no_se_mueve_con_la_cota(nombre, view):
    """El trial 64_01 corta antes del final de la pose: su `follow_end` ya era `null`
    y sigue siéndolo. Es el control — la cota no puede inventar ni borrar nada donde
    no había quietud que encontrar — y ahora el hueco viene con su razón."""
    ev = _mocap_rep(nombre, view)["ev"]
    assert isinstance(ev["follow_end"], MissingEvent) and not ev["follow_end"]
    assert "fin de la repetición" in ev["follow_end"].reason
    for k in ("address", "top", "impact"):
        assert ev[k].frame is not None


def test_la_razon_del_hueco_llega_a_warnings_y_el_evento_sale_null(clips, capture_paths_yaml, tmp_path):
    """`$defs/event` admite `null` y no admite campos nuevos: el hueco va como `null` y
    la razón a `warnings[]`, que es donde ADR-019 puso las razones que no caben en el
    contrato. Un `null` pelado no distingue «no lo hay, y por esto» de «nadie lo buscó»."""
    take, _ = _synthetic_take(clips, capture_paths_yaml, tmp_path, sw=synth_swing(120.0, n_reps=2, hold_s=0.2, recover_s=0.6))
    a = analyze_take(take, GOLF, height_m=1.75)
    assert [e["follow_end"] for e in a["events"]] == [None, None]
    assert json.loads((take / "analysis.json").read_text())["events"][0]["follow_end"] is None
    razones = [w for w in a["warnings"] if "follow_end" in w]
    assert len(razones) == 2 and all(w.startswith("Repetición ") for w in razones), razones
    assert all("fin de la repetición" in w for w in razones), razones
    assert validate_analysis(json.loads((take / "analysis.json").read_text())) == [], "el null del evento valida contra el schema tal cual está"


def test_explore_escribe_la_tolerancia_de_cada_evento(clips, tmp_path):
    """`tol_frames` llega a `datos-eventos.json`, que es de donde la lee la pantalla.
    Hasta hoy la tolerancia de cada evento sólo estaba en `analysis.json` —el ±4 del
    top de `vid1` no se veía en ningún lado— y la tabla mostraba un ±1 fijo.

    No se compara contra un número quemado: se compara contra el `analysis.json` de la
    misma corrida, que es la fuente."""
    from kinelab.explore import explore

    if "hevc120" not in clips:
        pytest.skip("sin fixture hevc120")
    sw = synth_swing(120.0, n_reps=1, still_s=0.5, backswing_s=0.8, downswing_s=0.25, follow_s=0.55, recover_s=0.8, amplitude_px=20.0, body_height_px=70.0, frame=(96, 96), hands_tilt=0.2, hands_miss_px=5.0)
    r = explore(clips["hevc120"], tmp_path / "out", GOLF, height_m=1.8, estimator=SwingEstimator(sw))
    escrito = json.loads((tmp_path / "out" / "datos-eventos.json").read_text(encoding="utf-8"))
    rep = json.loads((tmp_path / "out" / "analysis.json").read_text(encoding="utf-8"))["events"][0]
    assert escrito["eventos_tol_frames"] == r["eventos_tol_frames"], "lo que se muestra es lo que se escribió"
    assert set(escrito["eventos_tol_frames"]) == set(escrito["eventos_frame"]), "una tolerancia por evento presente"
    assert escrito["eventos_tol_frames"] == {k: rep[k]["tol_frames"] for k in escrito["eventos_frame"]}, "la del analysis.json, no otra"
    assert all(isinstance(v, int) and v >= 1 for v in escrito["eventos_tol_frames"].values())


def test_el_follow_end_no_se_sale_de_la_repeticion_ni_por_el_refinamiento():
    """La cota vale también para `settle_forward`, que camina hacia adelante mientras
    la velocidad siga bajando: un evento que se llama «dentro de la repetición» no
    puede salirse de ella por el refinamiento del frenado.

    Con los parámetros de golf de hoy no llega a pasar —`refine_s` 0,15 s es la mitad
    de `follow_still_s` 0,3 s, así que la ventana siempre deja margen—, y por eso el
    caso se construye acá con la velocidad y los cuadros a mano: es la única forma de
    que el límite quede defendido si alguien mueve esos dos números."""
    from sports.golf.events import _follow_end

    spd = np.linspace(1.0, 0.0, 40)  # siempre bajando: `settle_forward` camina todo lo que le dejen
    fe = _follow_end(spd, 20, 120.0, impact=10, rep_end=25, refine=15, params=GOLF_SPORT_EVENTS.params)
    assert fe.frame == 25, "se corta en el fin de la repetición, no en el cuadro 35"
