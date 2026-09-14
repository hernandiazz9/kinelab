"""`kinelab.tools.fps_truth` contra los clips sintéticos de `conftest.py`.

El test central es `test_declared_fields_do_not_separate_slowed_from_resampled`:
`r_frame_rate`, `avg_frame_rate` y la mediana de deltas de PTS son iguales en
el clip estirado (960 cuadros reproducidos a 30 fps) y en el remuestreado
(~120 cuadros a 30 fps). Lo único que los separa es contar cuadros contra una
duración real conocida. Es la razón de existir de la herramienta (CAPTURA.md).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kinelab.tools import fps_truth as ft

VFR_MAX = 1.10


def _need(clips: dict[str, Path], key: str) -> Path:
    if key not in clips:
        pytest.skip(f"fixture '{key}' no disponible en esta máquina")
    return clips[key]


# --- lo medido: cuadros y timestamps -------------------------------------


def test_real240_counts_every_frame(clips):
    c = ft.count_frames(clips["real240_h264"])
    assert c.frames_decoded == 960
    assert c.fps_playback == pytest.approx(240, abs=1)
    assert c.vfr_ratio <= VFR_MAX
    assert c.zero_deltas == 0
    assert c.playback_span_s == pytest.approx(959 / 240, abs=0.01)


def test_slowed30_keeps_all_frames_but_plays_at_30(clips):
    d = ft.probe_declared(clips["slowed30_h264"])
    c = ft.count_frames(clips["slowed30_h264"])
    assert c.frames_decoded == 960, "setpts=8*PTS conserva los cuadros"
    assert c.fps_playback == pytest.approx(30, abs=0.5)
    assert d.r_frame_rate == pytest.approx(30, abs=0.5)
    assert c.playback_span_s == pytest.approx(959 / 30, abs=0.1)


def test_resampled30_lost_the_frames(clips):
    d = ft.probe_declared(clips["resampled30_h264"])
    c = ft.count_frames(clips["resampled30_h264"])
    assert c.frames_decoded == pytest.approx(120, abs=2), "-r 30 tira 7 de cada 8 cuadros"
    assert c.fps_playback == pytest.approx(30, abs=0.5)
    assert d.r_frame_rate == pytest.approx(30, abs=0.5)


# --- el primer delta: arranque de la cámara, no tasa variable -------------


def test_first_delta_is_not_variable_rate(clips):
    """El caso medido en el original del Galaxy S22 Ultra: 263 deltas de
    0,0333 s y UNO de 0,2015 s, el primero. Con ese delta adentro el clip se
    declaraba VFR y reproducía a 29,436 fps en vez de 30,000 — todos los
    tiempos 1,9 % largos. El fixture lo reproduce con 0,2 s exactos."""
    c = ft.count_frames(clips["first_delta30_h264"])
    assert c.frames_decoded == 120, "setpts conserva los cuadros"
    assert c.delta_first_s == pytest.approx(0.2, abs=1e-3)

    # Lo bruto, que es lo que había antes y sigue estando con su significado.
    assert c.vfr_ratio == pytest.approx(6.0, abs=0.05)
    assert c.vfr_ratio > VFR_MAX
    assert c.fps_playback == pytest.approx(28.79, abs=0.05), "contaminado por el primer delta"

    # Lo nuevo: sin el primer delta el clip es CFR a 30,00 exactos.
    assert c.vfr_ratio_excl_first == pytest.approx(1.0, abs=0.01)
    assert c.fps_playback_excl_first == pytest.approx(30.0, abs=0.01)
    assert c.first_delta_is_the_only_outlier
    assert c.fps_playback_effective == pytest.approx(30.0, abs=0.01)
    assert c.vfr_ratio_effective == c.vfr_ratio_excl_first


def test_first_delta_clip_is_not_called_vfr_and_says_why(clips):
    t = ft.analyze(clips["first_delta30_h264"])
    assert t.verdict != "vfr"
    assert t.verdict == "sin_duracion_real"
    nota = [n for n in t.notes if "primer delta" in n]
    assert nota, f"falta la nota del primer delta: {t.notes}"
    assert "arranque de la cámara" in nota[0]
    assert "0.2000" in nota[0], "la nota dice cuánto mide el primer delta"
    assert "30.000 fps" in nota[0], "y la reproducción sin él"


def test_first_delta_clip_with_real_duration_is_cfr_at_capture_rate(clips):
    """El caso que importa para el cronómetro: 120 cuadros en 4 s reales son
    30 fps de captura, y el factor de estiramiento tiene que dar 1,00. Con el
    fps de reproducción bruto (28,79) daría 1,042: un clip normal parecería
    estirado un 4 %."""
    t = ft.analyze(clips["first_delta30_h264"], real_duration_s=4.0, nominal_fps=30)
    assert t.verdict == "cfr_a_tasa_de_captura"
    assert t.fps_capture == pytest.approx(30.0, abs=0.01)
    assert t.stretch_factor == pytest.approx(1.0, abs=0.01)


def test_first_delta_clip_keeps_the_raw_numbers_in_json(clips):
    """Nadie pierde información: el bruto y el corregido viajan los dos."""
    d = json.loads(json.dumps(ft.analyze(clips["first_delta30_h264"]).to_dict()))
    c = d["counted"]
    assert c["vfr_ratio"] == pytest.approx(6.0, abs=0.05)
    assert c["fps_playback"] == pytest.approx(28.79, abs=0.05)
    assert c["vfr_ratio_excl_first"] == pytest.approx(1.0, abs=0.01)
    assert c["fps_playback_excl_first"] == pytest.approx(30.0, abs=0.01)
    assert c["delta_first_s"] == pytest.approx(0.2, abs=1e-3)
    assert c["first_delta_is_the_only_outlier"] is True
    assert c["fps_playback_effective"] == pytest.approx(30.0, abs=0.01)


def test_real_vfr_clip_stays_vfr_after_excluding_the_first_delta(clips):
    """El contraste. En el clip realmente VFR (120 fps y después 60) excluir
    el primer delta no cambia nada: sigue VFR, y lo dice."""
    clip = _need(clips, "hevc120_vfr")
    c = ft.count_frames(clip)
    assert c.vfr_ratio > VFR_MAX
    assert c.vfr_ratio_excl_first > VFR_MAX, "el problema no es el arranque"
    assert not c.first_delta_is_the_only_outlier
    assert c.vfr_ratio_effective == c.vfr_ratio
    assert c.fps_playback_effective == c.fps_playback

    t = ft.analyze(clip)
    assert t.verdict == "vfr"
    assert not any("arranque de la cámara" in n for n in t.notes)


def test_cfr_clip_is_unchanged_by_the_new_fields(clips):
    """Un clip CFR de punta a punta: el corregido y el bruto coinciden y no
    aparece ninguna nota nueva."""
    c = ft.count_frames(clips["real240_h264"])
    assert not c.first_delta_is_the_only_outlier
    assert c.fps_playback_excl_first == pytest.approx(c.fps_playback, rel=0.01)
    assert c.vfr_ratio_excl_first <= VFR_MAX
    assert not any("primer delta" in n for n in ft.analyze(clips["real240_h264"]).notes)


def test_first_delta_cli_shows_both_numbers(clips, capsys):
    rc = ft.main([str(clips["first_delta30_h264"])])
    assert rc == 0
    out = capsys.readouterr().out
    assert "VFR" not in out
    medido = next(l for l in out.splitlines() if "medido:" in l)
    corregida = next(l for l in out.splitlines() if "sin el 1er delta" in l)
    assert "28.790 fps" in medido, "el bruto sigue estando, con su significado"
    assert "30.000 fps" in corregida and "ratio 1.000" in corregida


def test_declared_fields_do_not_separate_slowed_from_resampled(clips):
    """El test central. Si alguna vez falla porque el contenedor empezó a
    distinguirlos, cambió ffmpeg, no el problema: verificar con un clip real
    antes de tocar nada."""
    slowed = ft.analyze(clips["slowed30_h264"])
    resampled = ft.analyze(clips["resampled30_h264"])

    # Lo que declara el contenedor: indistinguible.
    assert abs(slowed.declared.r_frame_rate - resampled.declared.r_frame_rate) < 0.5
    assert abs(slowed.declared.avg_frame_rate - resampled.declared.avg_frame_rate) < 0.5
    # Lo que se mide de los PTS sin duración real: también indistinguible.
    assert abs(slowed.counted.delta_median_s - resampled.counted.delta_median_s) < 1e-4
    assert abs(slowed.counted.fps_playback - resampled.counted.fps_playback) < 0.5
    assert slowed.counted.vfr_ratio <= VFR_MAX
    assert resampled.counted.vfr_ratio <= VFR_MAX
    # Lo único que los separa: cuántos cuadros hay de verdad.
    assert slowed.counted.frames_decoded == 960
    assert resampled.counted.frames_decoded == pytest.approx(120, abs=2)
    assert slowed.counted.frames_decoded > 7 * resampled.counted.frames_decoded


# --- lo declarado --------------------------------------------------------


def test_probe_declared_basics(clips):
    d = ft.probe_declared(clips["real240_h264"])
    assert d.codec == "h264"
    assert (d.width, d.height) == (96, 96)
    assert d.rotation_deg == 0
    assert d.display_size == (96, 96)
    assert d.nb_frames_declared == 960
    assert d.duration_s == pytest.approx(4.0, abs=0.05)


def test_hevc_codec_is_reported_as_hevc(clips):
    d = ft.probe_declared(_need(clips, "hevc120"))
    assert d.codec == "hevc"


def test_rotation_metadata_is_read_clockwise_and_swaps_display_size(clips):
    """Un celular en vertical: el cuadro se guarda apaisado y la matriz de
    display dice que hay que girarlo 90° en sentido horario. `rotation_deg`
    usa esa convención (la del tag `rotate` histórico de los iPhone)."""
    d = ft.probe_declared(_need(clips, "hevc120_rot90"))
    if d.rotation_deg == 0:
        pytest.skip("ffmpeg no escribió la matriz de display en el fixture")
    assert d.rotation_deg == 90
    assert (d.width, d.height) == (64, 96), "el cuadro almacenado no cambia"
    assert d.display_size == (96, 64), "lo que se ve, sí"


# --- veredictos con duración real ----------------------------------------


def test_real_clip_is_cfr_at_capture_rate(clips):
    t = ft.analyze(clips["real240_h264"], real_duration_s=4.0, nominal_fps=240)
    assert t.verdict == "cfr_a_tasa_de_captura"
    assert t.fps_capture == pytest.approx(240, abs=1)
    assert t.stretch_factor == pytest.approx(1.0, abs=0.01)


def test_slowed_clip_is_stretched_by_8(clips):
    t = ft.analyze(clips["slowed30_h264"], real_duration_s=4.0, nominal_fps=240)
    assert t.verdict == "estirado"
    assert t.fps_capture == pytest.approx(240, abs=1)
    assert t.stretch_factor == pytest.approx(8.0, abs=0.05)
    assert any("estiramiento" in n for n in t.notes)


def test_resampled_clip_is_destroyed_when_nominal_is_known(clips):
    t = ft.analyze(clips["resampled30_h264"], real_duration_s=4.0, nominal_fps=240)
    assert t.verdict == "destruido"
    assert t.fps_capture == pytest.approx(30, abs=1)
    assert t.stretch_factor == pytest.approx(1.0, abs=0.05)


def test_resampled_clip_without_nominal_cannot_be_called_destroyed(clips):
    """Sin la tasa nominal del modo, nada dice que faltan cuadros: 30 fps
    capturados y reproducidos a 30 es, hasta donde se puede saber, un clip
    normal. Por eso el cronómetro se filma con cada modo."""
    t = ft.analyze(clips["resampled30_h264"], real_duration_s=4.0)
    assert t.verdict == "cfr_a_tasa_de_captura"


def test_without_real_duration_there_is_no_capture_rate(clips):
    t = ft.analyze(clips["slowed30_h264"])
    assert t.verdict == "sin_duracion_real"
    assert t.fps_capture is None
    assert t.stretch_factor is None
    assert any("cronómetro" in n for n in t.notes)


def test_real_duration_must_be_positive(clips):
    with pytest.raises(ValueError):
        ft.analyze(clips["real240_h264"], real_duration_s=0)
    with pytest.raises(ValueError):
        ft.analyze(clips["real240_h264"], real_duration_s=-1)


def test_vfr_clip_is_rejected_before_anything_else(clips):
    clip = _need(clips, "hevc120_vfr")
    c = ft.count_frames(clip)
    assert c.vfr_ratio > VFR_MAX
    assert ft.analyze(clip).verdict == "vfr"
    # Con duración real también: la tasa variable manda sobre cualquier otro veredicto.
    assert ft.analyze(clip, real_duration_s=4.0, nominal_fps=120).verdict == "vfr"


def test_to_dict_is_json_serializable(clips):
    t = ft.analyze(clips["real240_h264"], real_duration_s=4.0)
    d = json.loads(json.dumps(t.to_dict()))
    assert d["verdict"] == "cfr_a_tasa_de_captura"
    assert d["declared"]["display_size"] == [96, 96]
    assert d["counted"]["frames_decoded"] == 960
    assert "playback_span_s" in d["counted"]


# --- CLI ------------------------------------------------------------------


def test_cli_json_output(clips, capsys):
    rc = ft.main([str(clips["slowed30_h264"]), "--duracion-real", "4", "--nominal", "240", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["verdict"] == "estirado"
    assert out["stretch_factor"] == pytest.approx(8.0, abs=0.05)


def test_cli_human_output(clips, capsys):
    rc = ft.main([str(clips["slowed30_h264"]), "--duracion-real", "4"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ESTIRADO" in out
    assert "960 cuadros" in out


def test_cli_missing_file_returns_2(tmp_path, capsys):
    rc = ft.main([str(tmp_path / "no-existe.mov")])
    assert rc == 2
    assert "no existe" in capsys.readouterr().err


def test_cli_non_video_file_returns_2(tmp_path, capsys):
    bogus = tmp_path / "texto.mov"
    bogus.write_text("esto no es un video", encoding="utf-8")
    rc = ft.main([str(bogus)])
    assert rc == 2
    assert "error" in capsys.readouterr().err


def test_ffprobe_missing_is_a_clear_error(monkeypatch, clips):
    monkeypatch.setenv("KINELAB_FFPROBE", "/no/existe/ffprobe")
    with pytest.raises(ft.FfprobeError, match="ffprobe"):
        ft.probe_declared(clips["real240_h264"])
