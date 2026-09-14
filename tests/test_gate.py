"""El gate de ingesta, el `capture.json` y la sesión en disco, de punta a punta.

Cada caso usa un clip sintético de `conftest.py` contra un camino de captura
del YAML de fixture. Los rechazos se verifican por el id del chequeo que falló
y por una palabra de la frase que leería el entrenador.
"""

from __future__ import annotations

import shutil
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from kinelab.ingest import __main__ as cli
from kinelab.ingest.capture_paths import CapturePaths, load_capture_paths
from kinelab.ingest.gate import CaptureJson, Gate, run_gate
from kinelab.ingest.session import recording_date, reserve_take, sha256_file, validate_slug
from kinelab.sport import SportConfig
from kinelab.tools.fps_truth import analyze
from sports import get_sport
from sports.golf.config import GOLF

# Orden fijo de evaluación (CAPTURA.md §El gate de ingesta). Los de la Fase 1
# (encuadre, detección, una sola persona) todavía no existen.
CHECK_ORDER = [
    "capture_path_known",
    "codec_matches_path",
    "vfr_ratio_le_1_10",
    "fps_matches_path",
    "fps_min_for_gesture",
    "duration_plausible",
    "rotation_normalized",
    "view_declared",
    "gesture_known",
]

DAY = date(2026, 9, 12)


@pytest.fixture(scope="module")
def paths(capture_paths_yaml: Path) -> CapturePaths:
    return load_capture_paths(capture_paths_yaml)


@pytest.fixture
def data_dir(tmp_path: Path, capture_paths_yaml: Path) -> Path:
    """Un `data/` de mentira con el YAML de fixture adentro, para el CLI."""
    shutil.copy(capture_paths_yaml, tmp_path / "capture-paths.yaml")
    return tmp_path


def _need(clips: dict[str, Path], key: str) -> Path:
    if key not in clips:
        pytest.skip(f"fixture '{key}' no disponible en esta máquina")
    return clips[key]


def _gate(clip: Path, paths: CapturePaths, path_id: str, gesture: str = "driver", view: str = "face_on") -> Gate:
    return run_gate(analyze(clip), capture_path_id=path_id, capture_paths=paths, sport=GOLF, gesture=gesture, view=view)


def _failed(gate: Gate) -> list[str]:
    return [c.id for c in gate.checks if c.passed is False]


def _check(gate: Gate, check_id: str):
    return next(c for c in gate.checks if c.id == check_id)


def _ingest(clip: Path, paths: CapturePaths, data_dir: Path, path_id: str, **kw):
    return cli.ingest_clip(
        clip,
        athlete=kw.pop("athlete", "test"),
        gesture=kw.pop("gesture", "driver"),
        view=kw.pop("view", "face_on"),
        capture_path_id=path_id,
        capture_paths=paths,
        sport=GOLF,
        data_dir=data_dir,
        day=kw.pop("day", DAY),
    )


# --- el camino bueno, de punta a punta ------------------------------------


def test_hevc120_on_calibrated_path_is_ok_end_to_end(clips, paths, tmp_path):
    src = _need(clips, "hevc120")
    take_dir, capture = _ingest(src, paths, tmp_path, "test-hevc-120-cfr")

    assert take_dir == tmp_path / "sessions" / "test" / "2026-09-12" / "driver" / "face_on" / "take-01"
    assert capture.gate.verdict == "ok"
    assert capture.gate.reasons == []
    assert all(c.passed is True for c in capture.gate.checks)
    assert [c.id for c in capture.gate.checks] == CHECK_ORDER

    # Lo que dice el capture.json es lo que dice el contrato.
    assert capture.schema_version == "1.1.0"
    assert capture.codec == "hevc"
    assert (capture.width, capture.height) == (96, 96)
    assert capture.rotation_deg == 0
    assert capture.frames_decoded == 480
    assert capture.fps_real == 120.0
    assert capture.fps_playback == pytest.approx(120, abs=0.5)
    assert capture.stretch_factor == 1.0
    assert capture.fps_source == "capture-paths.yaml:test-hevc-120-cfr"
    assert capture.duration_s == pytest.approx(4.0, abs=0.05)
    assert capture.duration_playback_s == pytest.approx(479 / 120, abs=0.05)
    assert capture.vfr_ratio <= 1.10
    # Un CFR de punta a punta no cambia en nada con el fps efectivo: el bruto y
    # el corregido son el mismo número y no hay nada que explicar.
    assert capture.vfr_ratio_raw == capture.vfr_ratio
    assert capture.fps_playback_raw == capture.fps_playback
    assert capture.fps_note is None
    assert capture.first_delta_s == pytest.approx(1 / 120, abs=1e-3)
    assert capture.original_name == src.name
    assert capture.athlete == "test"

    # En disco: el original copiado, intocado, y el capture.json que parsea al mismo modelo.
    original = take_dir / "original.mov"
    assert original.is_file()
    assert sha256_file(original) == sha256_file(src) == capture.sha256_original
    assert src.is_file(), "se copia, nunca se mueve"
    written = CaptureJson.model_validate_json((take_dir / "capture.json").read_text(encoding="utf-8"))
    assert written == capture
    assert not (take_dir / "capture.json.tmp").exists()


def test_real240_on_h264_path_is_ok(clips, paths):
    g = _gate(clips["real240_h264"], paths, "test-h264-240-cfr")
    assert g.verdict == "ok", g.reasons
    assert _check(g, "fps_matches_path").value == pytest.approx(240, abs=0.5)
    assert _check(g, "duration_plausible").value == pytest.approx(4.0, abs=0.05)


def test_slowed_clip_on_its_slomo_path_is_ok_with_real_duration(clips, paths, tmp_path):
    """Un Slo-Mo estirado ×8 pasa si el camino lo declara: reproduce a 30, se
    capturó a 240, y la duración real es la de captura (4 s), no la del
    contenedor (32 s)."""
    _, capture = _ingest(clips["slowed30_h264"], paths, tmp_path, "test-h264-slomo-240-to-30")
    assert capture.gate.verdict == "ok", capture.gate.reasons
    assert capture.stretch_factor == 8.0
    assert capture.fps_real == 240.0
    assert capture.fps_playback == pytest.approx(30, abs=0.5)
    assert capture.duration_s == pytest.approx(4.0, abs=0.05)
    assert capture.duration_playback_s == pytest.approx(32.0, abs=0.2)


# --- rechazos, uno por chequeo ---------------------------------------------


def test_h264_where_hevc_expected_is_rejected_with_readable_reason(clips, paths):
    g = _gate(clips["real240_h264"], paths, "test-hevc-120-cfr")
    assert g.verdict == "reject"
    assert "codec_matches_path" in _failed(g)
    reason = _check(g, "codec_matches_path").reason
    assert "H.264" in reason and "HEVC" in reason and "Mantener originales" in reason
    assert reason in g.reasons


def test_slowed_clip_on_cfr_path_fails_fps_match(clips, paths):
    g = _gate(clips["slowed30_h264"], paths, "test-h264-240-cfr")
    assert g.verdict == "reject"
    assert _failed(g) == ["fps_matches_path"]
    reason = g.reasons[0]
    assert "30" in reason and "240" in reason


def test_30fps_clip_fails_fps_min_for_golf(clips, paths):
    g = _gate(clips["real30_h264"], paths, "test-h264-30-cfr")
    assert g.verdict == "reject"
    assert _failed(g) == ["fps_min_for_gesture"]
    assert "tiempos" in g.reasons[0]
    assert "100" in g.reasons[0]


def test_unknown_capture_path_is_rejected_and_dependent_checks_are_not_evaluated(clips, paths):
    g = _gate(clips["real240_h264"], paths, "no-calibrado")
    assert g.verdict == "reject"
    assert _failed(g) == ["capture_path_known"]
    assert "calibrado" in g.reasons[0] and "cronómetro" in g.reasons[0]
    for cid in ("codec_matches_path", "fps_matches_path", "fps_min_for_gesture"):
        assert _check(g, cid).passed is None, cid
    for cid in ("vfr_ratio_le_1_10", "duration_plausible", "rotation_normalized", "view_declared", "gesture_known"):
        assert _check(g, cid).passed is True, cid


def test_unknown_capture_path_still_writes_capture_json_without_fps_real(clips, paths, tmp_path):
    take_dir, capture = _ingest(clips["real240_h264"], paths, tmp_path, "no-calibrado")
    assert capture.gate.verdict == "reject"
    assert capture.fps_real is None
    assert capture.stretch_factor is None
    assert capture.fps_source.startswith("desconocido")
    assert capture.duration_s == pytest.approx(capture.duration_playback_s)
    assert (take_dir / "capture.json").is_file()
    assert '"fps_real": null' in (take_dir / "capture.json").read_text(encoding="utf-8")


def test_short_clip_fails_duration(clips, paths):
    g = _gate(_need(clips, "hevc120_short"), paths, "test-hevc-120-cfr")
    assert g.verdict == "reject"
    assert _failed(g) == ["duration_plausible"]
    assert "1.0 s" in g.reasons[0]


def test_vfr_clip_fails_vfr_ratio(clips, paths):
    """El clip realmente VFR (120 fps y después 60) sigue rechazado: excluir el
    primer delta no perdona nada, y el chequeo no menciona ningún arranque."""
    g = _gate(_need(clips, "hevc120_vfr"), paths, "test-hevc-120-cfr")
    assert g.verdict == "reject"
    assert "vfr_ratio_le_1_10" in _failed(g)
    assert "tasa variable" in _check(g, "vfr_ratio_le_1_10").reason
    assert "arranque" not in _check(g, "vfr_ratio_le_1_10").reason
    assert _check(g, "vfr_ratio_le_1_10").value > 1.10


def test_rotated_clip_reports_display_size(clips, paths, tmp_path):
    clip = _need(clips, "hevc120_rot90")
    _, capture = _ingest(clip, paths, tmp_path, "test-hevc-120-cfr")
    if capture.rotation_deg == 0:
        pytest.skip("ffmpeg no escribió la matriz de display en el fixture")
    assert capture.rotation_deg == 90
    assert (capture.width, capture.height) == (96, 64), "ancho y alto como se ven"
    assert _check(capture.gate, "rotation_normalized").passed is True


def test_invalid_view_is_rejected(clips, paths):
    g = _gate(clips["real240_h264"], paths, "test-h264-240-cfr", view="side")
    assert g.verdict == "reject"
    assert _failed(g) == ["view_declared"]
    assert "face_on" in g.reasons[0] and "down_the_line" in g.reasons[0]


def test_invalid_gesture_is_rejected(clips, paths):
    g = _gate(clips["real240_h264"], paths, "test-h264-240-cfr", gesture="bandeja")
    assert g.verdict == "reject"
    assert _failed(g) == ["gesture_known"]
    assert "driver" in g.reasons[0]


def test_every_check_is_reported_even_after_the_first_failure(clips, paths):
    """El primero que falla ya decide `reject`, pero se reportan todos."""
    g = _gate(clips["real30_h264"], paths, "test-hevc-120-cfr", gesture="bandeja", view="side")
    assert g.verdict == "reject"
    assert [c.id for c in g.checks] == CHECK_ORDER
    # `fps_min_for_gesture` NO falla: la tasa de captura es la del camino (120),
    # no la del clip; es el chequeo de fps_matches_path el que delata que el
    # clip no vino por ese camino. Y con 120 cuadros a los 120 fps del camino,
    # la duración real sale 1 s: también falla.
    assert _failed(g) == ["codec_matches_path", "fps_matches_path", "duration_plausible", "view_declared", "gesture_known"]
    assert len(g.reasons) == 5


# --- el primer delta de PTS no es tasa variable ------------------------------


def test_first_delta_clip_passes_both_checks_with_the_effective_numbers(clips, paths):
    """El caso medido en el Galaxy S22 Ultra: un solo delta de arranque. Con los
    números brutos el gate rechazaba cualquier clip de esa cámara; con los
    efectivos pasa, y cada chequeo dice de dónde salió su número."""
    clip = _need(clips, "first_delta30_h264")
    g = _gate(clip, paths, "test-h264-30-cfr")

    vfr, fps = _check(g, "vfr_ratio_le_1_10"), _check(g, "fps_matches_path")
    assert vfr.passed is True and fps.passed is True
    assert vfr.value == pytest.approx(1.0, abs=0.01), "el ratio sin el primer delta"
    assert fps.value == pytest.approx(30.0, abs=0.05), "la reproducción sin el primer delta"

    # Con los brutos los dos fallaban: ratio 6,0 y 28,79 fps contra 30 (4 %).
    c = analyze(clip).counted
    assert c.vfr_ratio > 1.10
    assert abs(c.fps_playback - 30.0) / 30.0 > 0.02

    # Y no en silencio: el chequeo lo dice aunque pase.
    assert "arranque de la cámara" in vfr.reason and "bruto 6.0" in vfr.reason
    assert "arranque de la cámara" in fps.reason and "bruto 28.79" in fps.reason
    # Pero no es una razón de rechazo: `reasons` sólo lleva lo que falló.
    assert vfr.reason not in g.reasons and fps.reason not in g.reasons
    assert _failed(g) == ["fps_min_for_gesture"], "lo único que falla es que 30 fps no alcanzan para golf"


def test_first_delta_clip_capture_json_keeps_both_numbers(clips, paths, tmp_path):
    _, capture = _ingest(_need(clips, "first_delta30_h264"), paths, tmp_path, "test-h264-30-cfr")
    assert capture.fps_playback == pytest.approx(30.0, abs=0.05)
    assert capture.fps_playback_raw == pytest.approx(28.79, abs=0.05)
    assert capture.vfr_ratio == pytest.approx(1.0, abs=0.01)
    assert capture.vfr_ratio_raw == pytest.approx(6.0, abs=0.05)
    assert capture.first_delta_s == pytest.approx(0.2, abs=1e-3)
    assert capture.fps_note and "arranque de la cámara" in capture.fps_note
    # El span de PTS es el que se midió, con el hueco del arranque adentro.
    assert capture.duration_playback_s == pytest.approx(119 / 30 + 0.2 - 1 / 30, abs=0.02)


def test_a_capture_json_1_0_0_still_validates(tmp_path):
    """Campo nuevo y opcional = minor: un `capture.json` escrito antes de esto
    sigue parseando, con los brutos en `null` (CONTRATO.md §Versionado)."""
    viejo = {
        "schema_version": "1.0.0", "athlete": "hernan", "gesture": "driver", "view": "face_on",
        "capture_path_id": "x", "fps_real": 120.0, "fps_playback": 119.85, "stretch_factor": 1.0,
        "fps_source": "capture-paths.yaml:x", "codec": "hevc", "width": 1920, "height": 1080,
        "rotation_deg": 0, "frames_decoded": 2398, "duration_s": 19.98, "duration_playback_s": 20.0,
        "vfr_ratio": 1.004, "recorded_at": None, "sha256_original": "abc", "original_name": "IMG.MOV",
        "gate": {"verdict": "ok", "checks": [], "reasons": []},
    }
    import json

    c = CaptureJson.model_validate_json(json.dumps(viejo))
    assert c.schema_version == "1.0.0"
    assert c.fps_playback == 119.85
    assert c.fps_playback_raw is None and c.vfr_ratio_raw is None
    assert c.first_delta_s is None and c.fps_note is None


# --- la sesión en disco -----------------------------------------------------


def test_ingesting_twice_creates_take_01_then_take_02(clips, paths, tmp_path):
    src = clips["real240_h264"]
    first, _ = _ingest(src, paths, tmp_path, "test-h264-240-cfr")
    second, _ = _ingest(src, paths, tmp_path, "test-h264-240-cfr")
    assert first.name == "take-01"
    assert second.name == "take-02"
    assert first.parent == second.parent
    assert (first / "original.mp4").is_file() and (second / "original.mp4").is_file()


def test_original_extension_is_lowercased(clips, paths, tmp_path):
    upper = tmp_path / "IMG_0001.MOV"
    shutil.copy(_need(clips, "hevc120"), upper)
    take_dir, capture = _ingest(upper, paths, tmp_path, "test-hevc-120-cfr")
    assert (take_dir / "original.mov").is_file()
    assert capture.original_name == "IMG_0001.MOV"


def test_a_reject_also_leaves_the_folder_and_its_capture_json(clips, paths, tmp_path):
    take_dir, capture = _ingest(clips["real240_h264"], paths, tmp_path, "test-hevc-120-cfr")
    assert capture.gate.verdict == "reject"
    assert (take_dir / "original.mp4").is_file()
    written = CaptureJson.model_validate_json((take_dir / "capture.json").read_text(encoding="utf-8"))
    assert written.gate.verdict == "reject"
    assert written.gate.reasons == capture.gate.reasons


def test_missing_source_raises_before_touching_disk(paths, tmp_path):
    with pytest.raises(FileNotFoundError):
        _ingest(tmp_path / "no-existe.mov", paths, tmp_path, "test-hevc-120-cfr")
    assert not (tmp_path / "sessions").exists()


@pytest.mark.parametrize("field", ["athlete", "gesture", "view"])
def test_bad_slug_raises_before_touching_disk(clips, paths, tmp_path, field):
    with pytest.raises(ValueError, match="inválido"):
        _ingest(clips["real240_h264"], paths, tmp_path, "test-h264-240-cfr", **{field: "Con Espacio"})
    assert not (tmp_path / "sessions").exists()


def test_reserve_take_skips_existing_folders(tmp_path):
    root = tmp_path / "s"
    (root / "take-01").mkdir(parents=True)
    assert reserve_take(root).name == "take-02"
    assert reserve_take(root).name == "take-03"


@pytest.mark.parametrize("value", ["hernan", "hernan-2", "face_on", "down_the_line", "a"])
def test_validate_slug_accepts(value):
    assert validate_slug(value, "x") == value


@pytest.mark.parametrize("value", ["Hernan", "con espacio", "", "-guion", "_guion-bajo", "ñandu", "a/b"])
def test_validate_slug_rejects(value):
    with pytest.raises(ValueError, match="inválido"):
        validate_slug(value, "x")


def test_view_slug_with_underscore_is_accepted_by_ingest(clips, paths, tmp_path):
    """`face_on` y `down_the_line` llevan guion bajo: el slug lo tiene que aceptar."""
    _, capture = _ingest(clips["real240_h264"], paths, tmp_path, "test-h264-240-cfr", view="down_the_line")
    assert capture.view == "down_the_line"
    assert _check(capture.gate, "view_declared").passed is True


def test_recording_date_parses_quicktime_creation_time(tmp_path):
    f = tmp_path / "x.mov"
    f.write_bytes(b"x")
    assert recording_date("2026-09-14T10:32:11.000000Z", f, None) == date(2026, 9, 14)
    assert recording_date("2026-09-14T10:32:11+10:00", f, None) == date(2026, 9, 14)
    assert recording_date("2026-09-14T10:32:11.000000Z", f, date(2026, 1, 1)) == date(2026, 1, 1), "el humano manda"
    mtime_day = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).date()
    assert recording_date(None, f, None) == mtime_day
    assert recording_date("ayer a la tarde", f, None) == mtime_day


# --- config de deporte ------------------------------------------------------


def test_golf_config_is_what_the_gate_needs():
    assert GOLF.id == "golf"
    assert GOLF.fps_min == 100
    assert set(GOLF.views) == {"face_on", "down_the_line"}
    assert "driver" in GOLF.gestures
    assert get_sport("golf") is GOLF


def test_unknown_sport_is_a_clear_error():
    with pytest.raises(KeyError, match="desconocido"):
        get_sport("padel")


@pytest.mark.parametrize(
    "kw",
    [dict(gestures=()), dict(views=()), dict(fps_min=0)],
)
def test_sport_config_rejects_empty_or_zero(kw):
    base = dict(id="x", gestures=("a",), views=("b",), fps_min=1)
    with pytest.raises(ValueError):
        SportConfig(**{**base, **kw})


# --- CLI --------------------------------------------------------------------


def _cli(clip: Path, data_dir: Path, path_id: str, **overrides: str) -> list[str]:
    args = {"--atleta": "test", "--gesto": "driver", "--vista": "face_on", "--camino": path_id, "--data": str(data_dir), "--fecha": "2026-09-12"}
    args.update(overrides)
    return [str(clip), *(x for kv in args.items() for x in kv)]


def test_cli_ok_returns_0(clips, data_dir, capsys):
    rc = cli.main(_cli(_need(clips, "hevc120"), data_dir, "test-hevc-120-cfr"))
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "gate: OK" in out
    assert "take-01" in out
    assert (data_dir / "sessions" / "test" / "2026-09-12" / "driver" / "face_on" / "take-01" / "capture.json").is_file()


def test_cli_reject_returns_2_and_prints_reasons(clips, data_dir, capsys):
    rc = cli.main(_cli(clips["real240_h264"], data_dir, "test-hevc-120-cfr"))
    out = capsys.readouterr().out
    assert rc == 2
    assert "RECHAZADO" in out
    assert "H.264" in out


def test_cli_missing_clip_returns_1(data_dir, tmp_path, capsys):
    rc = cli.main(_cli(tmp_path / "no-existe.mov", data_dir, "test-hevc-120-cfr"))
    assert rc == 1
    assert "error" in capsys.readouterr().err


def test_cli_unknown_sport_returns_1(clips, data_dir, capsys):
    rc = cli.main(_cli(clips["real240_h264"], data_dir, "test-h264-240-cfr", **{"--deporte": "padel"}))
    assert rc == 1
    assert "desconocido" in capsys.readouterr().err


def test_cli_bad_athlete_slug_returns_1(clips, data_dir, capsys):
    rc = cli.main(_cli(clips["real240_h264"], data_dir, "test-h264-240-cfr", **{"--atleta": "Hernán"}))
    assert rc == 1
    assert "inválido" in capsys.readouterr().err


def test_cli_without_capture_paths_yaml_returns_1(clips, tmp_path, capsys):
    rc = cli.main(_cli(clips["real240_h264"], tmp_path / "vacio", "test-h264-240-cfr"))
    assert rc == 1
    assert "error" in capsys.readouterr().err
