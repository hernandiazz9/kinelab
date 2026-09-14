"""`data/capture-paths.yaml`: el archivo de caminos de captura calibrados."""

from __future__ import annotations

import copy
from datetime import date
from pathlib import Path

import pytest
import yaml

from kinelab.ingest.capture_paths import (
    GENERIC_VIDEO_ID,
    CapturePath,
    CapturePaths,
    load_capture_paths,
    resolve_path_id,
)

REPO = Path(__file__).resolve().parents[1]

VALID = {
    "id": "iphone17pro-video-1080p120-airdrop",
    "device": "iPhone 17 Pro",
    "mode": "video",
    "nominal_fps": 120,
    "codec_expected": "hevc",
    "transfer": "airdrop-keep-originals",
    "fps_real": 119.88,
    "fps_playback": 119.88,
    "stretch_factor": 1.0,
    "fps_method": "cronómetro 10 s",
    "calibrated_on": "2026-09-14",
    "calibrated_by": "hernan",
}


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "capture-paths.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def _yaml_with(tmp_path: Path, *paths: dict) -> Path:
    return _write(tmp_path, yaml.safe_dump({"schema_version": "1.0.0", "paths": list(paths)}, allow_unicode=True))


# --- carga ----------------------------------------------------------------


def test_load_fixture(capture_paths_yaml):
    cp = load_capture_paths(capture_paths_yaml)
    assert cp.schema_version == "1.0.0"
    assert len(cp.paths) == 8  # los 7 de prueba más el genérico `desconocido-video`
    p = cp.get("test-h264-slomo-240-to-30")
    assert p is not None
    assert p.mode == "slomo"
    assert p.codec_expected == "h264"
    assert p.fps_real == 240.0
    assert p.fps_playback == 30.0
    assert p.stretch_factor == 8.0
    assert p.calibrated_on == date(2026, 9, 12)
    assert p.notes == ""
    assert cp.get("no-existe") is None


def test_empty_paths_list(tmp_path):
    cp = load_capture_paths(_write(tmp_path, 'schema_version: "1.0.0"\npaths: []\n'))
    assert cp.paths == []


def test_paths_key_with_no_value(tmp_path):
    cp = load_capture_paths(_write(tmp_path, 'schema_version: "1.0.0"\npaths:\n'))
    assert cp.paths == []


def test_paths_key_missing(tmp_path):
    cp = load_capture_paths(_write(tmp_path, 'schema_version: "1.0.0"\n'))
    assert cp.paths == []


def test_schema_version_is_required(tmp_path):
    with pytest.raises(ValueError, match="schema_version"):
        load_capture_paths(_write(tmp_path, "paths: []\n"))


def test_yaml_must_be_a_mapping(tmp_path):
    with pytest.raises(ValueError, match="mapa"):
        load_capture_paths(_write(tmp_path, "- uno\n- dos\n"))


def test_empty_file_is_a_clear_error(tmp_path):
    with pytest.raises(ValueError, match="schema_version"):
        load_capture_paths(_write(tmp_path, ""))


# --- validación de cada camino ------------------------------------------


def test_valid_path_loads(tmp_path):
    cp = load_capture_paths(_yaml_with(tmp_path, VALID))
    p = cp.get(VALID["id"])
    assert p is not None
    assert p.calibrated_on == date(2026, 9, 14)


def test_duplicate_id_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="repetido"):
        load_capture_paths(_yaml_with(tmp_path, VALID, VALID))


def test_inconsistent_stretch_factor_is_rejected(tmp_path):
    bad = dict(VALID, fps_real=240.0, fps_playback=30.0, stretch_factor=1.0)
    with pytest.raises(ValueError, match="stretch_factor"):
        load_capture_paths(_yaml_with(tmp_path, bad))


def test_consistent_stretch_factor_within_1_percent(tmp_path):
    ok = dict(VALID, fps_real=239.76, fps_playback=29.97, stretch_factor=8.0)
    cp = load_capture_paths(_yaml_with(tmp_path, ok))
    assert cp.paths[0].stretch_factor == 8.0


def test_extra_field_is_rejected(tmp_path):
    bad = dict(VALID, fps=120)
    with pytest.raises(ValueError, match="fps"):
        load_capture_paths(_yaml_with(tmp_path, bad))


@pytest.mark.parametrize("bad_id", ["iPhone17", "con espacio", "-empieza-con-guion", "con_guion_bajo", ""])
def test_id_must_be_a_slug(tmp_path, bad_id):
    with pytest.raises(ValueError):
        load_capture_paths(_yaml_with(tmp_path, dict(VALID, id=bad_id)))


@pytest.mark.parametrize("field,value", [("mode", "slow-mo"), ("codec_expected", "h265"), ("nominal_fps", 0), ("fps_real", 0), ("fps_playback", -30)])
def test_enum_and_positive_constraints(tmp_path, field, value):
    with pytest.raises(ValueError):
        load_capture_paths(_yaml_with(tmp_path, dict(VALID, **{field: value})))


def test_calibrated_on_must_be_a_date(tmp_path):
    with pytest.raises(ValueError, match="calibrated_on"):
        load_capture_paths(_yaml_with(tmp_path, dict(VALID, calibrated_on="ayer")))


def test_model_direct_construction():
    p = CapturePath.model_validate(VALID)
    cp = CapturePaths(schema_version="1.0.0", paths=[p])
    assert cp.get(p.id) is p


# --- los archivos del repo respetan el schema -----------------------------


def test_repo_capture_paths_yaml_is_valid():
    """El archivo real del repo: válido siempre. Los calibrados los llena el
    humano con el cronómetro; los declarados ya están (ADR-016)."""
    cp = load_capture_paths(REPO / "data" / "capture-paths.yaml")
    assert cp.schema_version == "1.1.0", "el campo `calibrated` es nuevo y opcional: minor"
    for p in cp.paths:
        if p.calibrated:
            assert p.stretch_factor == pytest.approx(p.fps_real / p.fps_playback, rel=0.01)
        else:
            assert all(getattr(p, f) is None for f in ("fps_real", "fps_playback", "stretch_factor", "fps_method", "calibrated_on", "calibrated_by"))
            assert p.mode == "video", f"{p.id}: un slomo sin calibrar no entra al repo (ADR-016)"


def test_repo_has_the_declared_paths_of_adr_016():
    """Los tres que pide ADR-016: el genérico y los dos del teléfono que hay."""
    cp = load_capture_paths(REPO / "data" / "capture-paths.yaml")
    assert GENERIC_VIDEO_ID in cp.ids()
    for pid in (GENERIC_VIDEO_ID, "s22ultra-video-fhd60-cable", "s22ultra-video-fhd30-cable"):
        p = cp.get(pid)
        assert p is not None and p.calibrated is False and p.mode == "video"
    generic = cp.get(GENERIC_VIDEO_ID)
    assert generic.nominal_fps is None and generic.codec_expected is None, "el genérico no sabe nada del archivo"
    assert cp.get("s22ultra-video-fhd30-cable").codec_expected == "h264", "medido en el original del S22"


# --- caminos declarados sin calibrar (ADR-016) ----------------------------

DECLARED = {"id": "declarado-video", "device": "teléfono cualquiera", "mode": "video", "transfer": "cable", "calibrated": False}


def test_declared_path_loads_with_everything_in_null(tmp_path):
    cp = load_capture_paths(_yaml_with(tmp_path, DECLARED))
    p = cp.get("declarado-video")
    assert p is not None and p.calibrated is False
    assert (p.fps_real, p.fps_playback, p.stretch_factor, p.fps_method, p.calibrated_on, p.calibrated_by) == (None,) * 6
    assert p.nominal_fps is None and p.codec_expected is None


def test_declared_path_may_declare_nominal_fps_and_codec(tmp_path):
    cp = load_capture_paths(_yaml_with(tmp_path, dict(DECLARED, nominal_fps=60, codec_expected="h264")))
    p = cp.get("declarado-video")
    assert p.nominal_fps == 60 and p.codec_expected == "h264"


def test_a_slomo_declared_path_loads_so_the_gate_can_reject_it(tmp_path):
    """El YAML lo acepta a propósito: la frase para el entrenador la dice el
    gate, no un error de carga."""
    cp = load_capture_paths(_yaml_with(tmp_path, dict(DECLARED, mode="slomo")))
    assert cp.get("declarado-video").mode == "slomo"


@pytest.mark.parametrize("field,value", [("fps_real", 30.0), ("fps_playback", 30.0), ("stretch_factor", 1.0), ("fps_method", "a ojo"), ("calibrated_on", "2026-09-14"), ("calibrated_by", "hernan")])
def test_declared_path_cannot_carry_calibration_numbers(tmp_path, field, value):
    """Declarar no es medir: los seis campos del cronómetro tienen que ir en null."""
    with pytest.raises(ValueError, match="sin calibrar"):
        load_capture_paths(_yaml_with(tmp_path, dict(DECLARED, **{field: value})))


@pytest.mark.parametrize("field", ["fps_real", "fps_playback", "stretch_factor", "fps_method", "calibrated_on", "calibrated_by", "nominal_fps", "codec_expected"])
def test_calibrated_path_needs_every_field(tmp_path, field):
    bad = copy.deepcopy(VALID)
    del bad[field]
    with pytest.raises(ValueError, match=field):
        load_capture_paths(_yaml_with(tmp_path, bad))


def test_calibrated_is_true_by_default(tmp_path):
    """Un camino escrito antes de ADR-016 (sin el campo) sigue siendo calibrado."""
    cp = load_capture_paths(_yaml_with(tmp_path, VALID))
    assert cp.get(VALID["id"]).calibrated is True


def test_resolve_path_id_names_the_alternatives(tmp_path):
    cp = load_capture_paths(_yaml_with(tmp_path, DECLARED))
    assert resolve_path_id("declarado-video", cp).device == "teléfono cualquiera"
    with pytest.raises(ValueError, match="declarado-video"):
        resolve_path_id("no-existe", cp)


def test_resolve_path_id_without_argument_uses_the_repo_file():
    assert resolve_path_id(GENERIC_VIDEO_ID).calibrated is False


def test_repo_example_is_valid():
    """El ejemplo comentado: tiene los dos tipos de camino y los dos válidos."""
    cp = load_capture_paths(REPO / "data" / "examples" / "capture-paths.example.yaml")
    assert len(cp.paths) >= 1
    assert {p.calibrated for p in cp.paths} == {True, False}, "el ejemplo muestra calibrado y declarado"
    for p in cp.paths:
        if p.calibrated:
            assert p.stretch_factor == pytest.approx(p.fps_real / p.fps_playback, rel=0.01)
