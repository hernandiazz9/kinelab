"""De qué clip salió la calibración del fps (encargo 34).

Dos campos y una frase. `calibration_clip_sha256` en `capture-paths.yaml`
(schema 1.2.0) dice con qué clip se midió el cronómetro de un camino;
`fps_calibration.same_file` en `capture.json` (schema 1.3.0) dice si esa toma
es ese clip o sólo hereda su tasa; y `analysis.warnings` lo cuenta en
castellano, que es el canal que llega a la pantalla también en exploración,
donde el gate no corre.

La regla que estos tests fijan es que la procedencia se **registra, no se
exige**: un camino calibrado sin sha sigue siendo válido, sigue cargando y
sigue analizando. Lo único que pierde es poder decir de dónde salió su tasa.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pytest
import yaml

from tests.helpers.synth_swing import synth_swing
from kinelab.analysis import analyze_take
from kinelab.ingest.__main__ import ingest_clip
from kinelab.ingest.capture_paths import CapturePath, CapturePaths, load_capture_paths
from kinelab.ingest.gate import CaptureJson, FpsCalibration, fps_calibration_for
from kinelab.ingest.session import sha256_file
from kinelab.perception.posestore import PoseData, save_pose
from sports.golf.config import GOLF

REPO = Path(__file__).resolve().parents[1]

SHA_A = "a" * 64
SHA_B = "b" * 64

CALIBRADO = {
    "id": "camino-calibrado",
    "device": "teléfono",
    "mode": "video",
    "nominal_fps": 120,
    "codec_expected": "hevc",
    "transfer": "cable",
    "fps_real": 119.88,
    "fps_playback": 119.88,
    "stretch_factor": 1.0,
    "fps_method": "cronómetro 10 s",
    "calibrated_on": "2026-09-14",
    "calibrated_by": "hernan",
}

DECLARADO = {
    "id": "camino-declarado",
    "device": "teléfono",
    "mode": "video",
    "transfer": "cable",
    "calibrated": False,
}


def _path(**extra) -> CapturePath:
    return CapturePath.model_validate({**CALIBRADO, **extra})


# --- capture-paths: el campo nuevo es opcional ----------------------------


def test_a_calibrated_path_without_the_sha_is_still_valid():
    """La decisión del encargo: la procedencia se registra, no se exige. Si
    exigirla fuera obligatorio, el único camino calibrado del repo (n = 1) se
    caería y no hay material para reemplazarlo."""
    p = _path()
    assert p.calibrated is True
    assert p.calibration_clip_sha256 is None


def test_a_calibrated_path_with_the_sha_validates():
    assert _path(calibration_clip_sha256=SHA_A).calibration_clip_sha256 == SHA_A


@pytest.mark.parametrize(
    "malo",
    ["", "abc", "A" * 64, "z" * 64, "a" * 63, "a" * 65, " " + "a" * 64],
    ids=["vacío", "corto", "mayúsculas", "no-hex", "63", "65", "con-espacio"],
)
def test_the_sha_has_to_look_like_a_sha(malo):
    """Un sha mal pegado es peor que ninguno: diría `same_file: false` sobre el
    archivo correcto. Se rechaza al cargar, no al comparar."""
    with pytest.raises(ValueError):
        _path(calibration_clip_sha256=malo)


def test_a_declared_path_cannot_claim_a_calibration_clip():
    """Sin cronómetro no hay clip que lo haya medido. Faltar está permitido;
    declarar uno que no existe, no."""
    with pytest.raises(ValueError, match="calibration_clip_sha256"):
        CapturePath.model_validate({**DECLARADO, "calibration_clip_sha256": SHA_A})


def test_a_declared_path_without_it_is_fine():
    assert CapturePath.model_validate(DECLARADO).calibration_clip_sha256 is None


def test_a_1_1_0_file_without_the_field_still_loads(tmp_path):
    """El caso que decide si el bump es minor: un archivo de la versión
    anterior, sin el campo, tiene que cargar igual."""
    f = tmp_path / "capture-paths.yaml"
    f.write_text(yaml.safe_dump({"schema_version": "1.1.0", "paths": [CALIBRADO]}, allow_unicode=True), encoding="utf-8")
    cp = load_capture_paths(f)
    assert cp.schema_version == "1.1.0"
    assert cp.get("camino-calibrado").calibration_clip_sha256 is None


def test_a_1_2_0_file_with_the_field_loads(tmp_path):
    f = tmp_path / "capture-paths.yaml"
    f.write_text(
        yaml.safe_dump(
            {"schema_version": "1.2.0", "paths": [{**CALIBRADO, "calibration_clip_sha256": SHA_A}]},
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    assert load_capture_paths(f).get("camino-calibrado").calibration_clip_sha256 == SHA_A


# --- el repo: el único camino calibrado declara su clip --------------------


def test_the_only_calibrated_path_of_the_repo_says_which_clip_calibrated_it():
    """`Cortado-lenta.mp4`, el único de los tres clips lentos con el cronómetro
    ANDANDO en el cuadro (informe del 26). El sha se leyó del `capture.json` de
    su exploración y se verificó contra el archivo; no se inventó."""
    p = load_capture_paths(REPO / "data" / "capture-paths.yaml").get("s22ultra-slomo-fhd240-recorte-mac")
    assert p is not None and p.calibrated is True
    assert p.calibration_clip_sha256 == "ff13415e0a1a4fad938b7ab636fb04cb3761ffbeb26e4c732f3dfd726ce3829b"


def test_no_declared_path_of_the_repo_declares_a_calibration_clip():
    for p in load_capture_paths(REPO / "data" / "capture-paths.yaml").paths:
        if not p.calibrated:
            assert p.calibration_clip_sha256 is None, p.id


# --- same_file: los tres estados ------------------------------------------


def test_same_file_is_true_only_when_the_shas_match():
    assert fps_calibration_for(_path(calibration_clip_sha256=SHA_A), SHA_A) == FpsCalibration(clip_sha256=SHA_A, same_file=True)


def test_same_file_is_false_with_different_shas():
    """El caso del día uno: `cortado3-lento` salió del mismo camino pero no es
    el clip que lo calibró."""
    cal = fps_calibration_for(_path(calibration_clip_sha256=SHA_A), SHA_B)
    assert cal.same_file is False
    assert cal.clip_sha256 == SHA_A


def test_same_file_is_null_when_the_path_declares_no_sha():
    """Y `null` no es `false`: no saber no es saber que no."""
    cal = fps_calibration_for(_path(), SHA_A)
    assert cal.same_file is None and cal.clip_sha256 is None


def test_same_file_is_null_for_a_declared_path():
    assert fps_calibration_for(CapturePath.model_validate(DECLARADO), SHA_A) == FpsCalibration()


def test_same_file_is_null_without_a_path():
    assert fps_calibration_for(None, SHA_A) == FpsCalibration()


@pytest.mark.parametrize("sha_toma", ["", "A" * 64, SHA_B, SHA_A.upper()])
def test_same_file_never_says_true_by_accident(sha_toma):
    """Nunca `true` con shas distintos ni con el sha de la toma ausente. Un
    `true` de más es exactamente la mentira que este encargo vino a evitar: la
    toma diría que se calibró a sí misma sin haberlo hecho."""
    assert fps_calibration_for(_path(calibration_clip_sha256=SHA_A), sha_toma).same_file is not True


def test_same_file_is_never_true_when_there_is_no_sha_to_compare_against():
    for sha_toma in ("", SHA_A, SHA_B):
        assert fps_calibration_for(_path(), sha_toma).same_file is not True


# --- de punta a punta: la ingesta escribe `same_file` ----------------------


def _paths_for(clip: Path, *, con_sha: str | None) -> CapturePaths:
    """Un `capture-paths` de un solo camino, calibrado a mano contra el clip
    sintético de 120 fps. Se arma acá y no en el fixture compartido:
    `capture_paths_yaml` lo usan centenares de tests y agregarle un camino les
    movería el conteo."""
    d = {**CALIBRADO, "id": "camino-del-clip", "fps_real": 120.0, "fps_playback": 120.0}
    if con_sha is not None:
        d["calibration_clip_sha256"] = con_sha
    return CapturePaths.model_validate({"schema_version": "1.2.0", "paths": [d]})


def _ingest(clip: Path, paths: CapturePaths, tmp_path: Path):
    return ingest_clip(
        clip, athlete="t", gesture="driver", view="face_on",
        capture_path_id="camino-del-clip", capture_paths=paths,
        sport=GOLF, data_dir=tmp_path, day=date(2026, 9, 12),
    )


def _clip(clips) -> Path:
    if "hevc120" not in clips:
        pytest.skip("sin fixture hevc120")
    return clips["hevc120"]


def test_the_capture_json_says_when_the_clip_is_the_one_that_calibrated_the_path(clips, tmp_path):
    """El caso bueno, y el que `CAPTURA.md` §El método preferido quiere: el
    cronómetro está en este mismo archivo, así que el camino se calibró con él."""
    clip = _clip(clips)
    _, cap = _ingest(clip, _paths_for(clip, con_sha=sha256_file(clip)), tmp_path)
    assert cap.schema_version == "1.3.0"
    assert cap.fps_calibration.same_file is True
    assert cap.fps_calibration.clip_sha256 == cap.sha256_original


def test_the_capture_json_says_when_the_fps_is_inherited_from_another_clip(clips, tmp_path):
    """Lo que pasa el día uno con `cortado3-lento`: mismo camino, otro archivo."""
    clip = _clip(clips)
    _, cap = _ingest(clip, _paths_for(clip, con_sha=SHA_A), tmp_path)
    assert cap.fps_calibration.same_file is False
    assert cap.fps_calibration.clip_sha256 == SHA_A != cap.sha256_original


def test_a_path_without_the_sha_still_ingests_and_says_nothing(clips, tmp_path):
    """La decisión del encargo llevada al gate: no declarar la procedencia no
    rechaza nada. El veredicto es el mismo y `same_file` queda en `null`."""
    clip = _clip(clips)
    take, con = _ingest(clip, _paths_for(clip, con_sha=sha256_file(clip)), tmp_path)
    _, sin = _ingest(clip, _paths_for(clip, con_sha=None), tmp_path)
    assert con.gate.verdict == sin.gate.verdict == "ok"
    assert [c.id for c in con.gate.checks] == [c.id for c in sin.gate.checks], "no se agregó ningún Check: CHECK_ORDER no se mueve"
    assert sin.fps_calibration.same_file is None and sin.fps_calibration.clip_sha256 is None
    assert take.is_dir()


def test_the_provenance_is_not_a_check_that_rejects(clips, tmp_path):
    """Ni `false` ni `null` tocan el veredicto ni las razones: es procedencia,
    no un chequeo (lo prohíbe el prompt del encargo 34 y es lo correcto — un
    clip filmado por un camino calibrado sigue siendo medible)."""
    clip = _clip(clips)
    for i, sha in enumerate((None, SHA_A, sha256_file(clip))):
        _, cap = _ingest(clip, _paths_for(clip, con_sha=sha), tmp_path / f"d{i}")
        assert cap.gate.verdict == "ok" and cap.gate.reasons == []
        assert not any("calibration" in (c.reason or "") for c in cap.gate.checks)


def test_a_capture_json_without_fps_calibration_still_validates(clips, tmp_path):
    """Campo nuevo y opcional: el bump 1.2.0 → 1.3.0 es minor porque un archivo
    de la versión anterior sigue cargando, con los dos campos en `None`."""
    clip = _clip(clips)
    _, cap = _ingest(clip, _paths_for(clip, con_sha=SHA_A), tmp_path)
    viejo = cap.model_dump(mode="json")
    del viejo["fps_calibration"]
    viejo["schema_version"] = "1.2.0"
    revivido = CaptureJson.model_validate(viejo)
    assert revivido.fps_calibration.same_file is None and revivido.fps_calibration.clip_sha256 is None
    # Y lo demás no se movió: el campo nuevo no le cambió el sentido a ninguno.
    assert revivido.fps_real == cap.fps_real and revivido.gate.verdict == cap.gate.verdict


# --- la frase que llega a la pantalla -------------------------------------


def _pose(sw) -> PoseData:
    T = sw.keypoints.shape[0]
    return PoseData(
        sw.keypoints, sw.scores, np.zeros((T, 4), np.float32), sw.timestamps_s, np.zeros(T, np.uint8),
        {"model": "sintético", "framing": {"detection_rate": 1.0, "body_height_px_median": sw.body_height_px,
         "body_height_px_min": sw.body_height_px, "body_height_px_max": sw.body_height_px,
         "frac_of_frame": sw.body_height_px / sw.frame[0]}, "plausibility_counts": {}, "camera_motion_px": 0.0},
    )


def _warnings(clips, tmp_path, *, con_sha):
    clip = _clip(clips)
    take, _ = _ingest(clip, _paths_for(clip, con_sha=con_sha), tmp_path)
    save_pose(take, _pose(synth_swing(120.0, n_reps=2)))
    return analyze_take(take, GOLF, write=False, height_m=1.80)["warnings"]


def test_the_warning_says_which_clip_the_fps_came_from(clips, tmp_path):
    """`same_file: false` → la frase dice que el fps es heredado y de qué clip
    salió. Es el canal de `analysis.warnings` porque en exploración el gate no
    corre y es lo único que llega a la pantalla en los dos modos."""
    ws = _warnings(clips, tmp_path, con_sha=SHA_A)
    hit = [w for w in ws if "NO lo midió este archivo" in w]
    assert len(hit) == 1, ws
    assert SHA_A[:12] in hit[0], "tiene que decir DE QUÉ clip salió"


def test_the_warning_says_when_the_path_declares_no_clip(clips, tmp_path):
    ws = _warnings(clips, tmp_path, con_sha=None)
    hit = [w for w in ws if "no registra con qué clip" in w]
    assert len(hit) == 1, ws
    assert "calibration_clip_sha256" in hit[0], "tiene que decir qué falta y dónde"


def test_there_is_no_warning_when_the_clip_calibrated_its_own_path(clips, tmp_path):
    """El caso bueno no genera ruido: el cronómetro está en este archivo."""
    clip = _clip(clips)
    ws = _warnings(clips, tmp_path, con_sha=sha256_file(clip))
    assert not any("NO lo midió este archivo" in w or "no registra con qué clip" in w for w in ws), ws


def test_the_three_cases_produce_three_different_warnings(clips, tmp_path):
    """Y son tres frases distintas: si las tres dieran lo mismo, los tres tests
    de arriba pasarían igual sin que la pantalla dijera nada útil."""
    clip = _clip(clips)
    frases = {
        caso: {w for w in _warnings(clips, tmp_path / caso, con_sha=sha) if "clip" in w}
        for caso, sha in (("heredado", SHA_A), ("sin_sha", None), ("propio", sha256_file(clip)))
    }
    assert frases["heredado"] != frases["sin_sha"] != frases["propio"] != frases["heredado"]
    assert frases["propio"] == set(), "el caso bueno no agrega ninguna frase"


def test_the_adr_016_warning_still_goes_first(clips, tmp_path):
    """Los dos avisos hablan del eje del tiempo y van antes de cualquier número,
    pero el de ADR-016 es el más fuerte y queda primero: ahí la tasa ENTERA es
    un supuesto, mientras que acá está medida con cronómetro y lo único que
    falta es de qué clip salió. Es el caso de exploración sobre un camino
    calibrado, que es donde los dos aparecen juntos."""
    clip = _clip(clips)
    take, _ = _ingest(clip, _paths_for(clip, con_sha=SHA_A), tmp_path)
    cj = json.loads((take / "capture.json").read_text(encoding="utf-8"))
    cj["fps_provenance"] = "sin_verificar"  # como lo escribe `explore.prepare_take`
    (take / "capture.json").write_text(json.dumps(cj), encoding="utf-8")
    save_pose(take, _pose(synth_swing(120.0, n_reps=2)))

    ws = analyze_take(take, GOLF, write=False, height_m=1.80)["warnings"]
    assert ws[0].startswith("Tasa de cuadros sin verificar"), ws[0]
    assert "NO lo midió este archivo" in ws[1], ws[1]


# --- fps_truth imprime el sha, listo para pegar ---------------------------


def test_fps_truth_prints_the_sha_ready_to_paste(clips, capsys):
    """El punto 4 del encargo: hoy había que calcular el sha aparte, y eso es lo
    que hacía que nadie declarara de qué clip salía una calibración."""
    from kinelab.tools.fps_truth import main as fps_truth_main

    clip = _clip(clips)
    assert fps_truth_main([str(clip)]) == 0
    salida = capsys.readouterr().out
    esperado = f'calibration_clip_sha256: "{sha256_file(clip)}"'
    assert esperado in salida, salida
    # Y lo que imprime tiene que entrar en el YAML tal cual, sin retocar.
    linea = next(l for l in salida.splitlines() if "calibration_clip_sha256" in l)
    cargado = yaml.safe_load(linea.strip())
    assert cargado == {"calibration_clip_sha256": sha256_file(clip)}
    CapturePath.model_validate({**CALIBRADO, **cargado})


def test_fps_truth_json_carries_the_sha(clips, capsys):
    from kinelab.tools.fps_truth import main as fps_truth_main

    clip = _clip(clips)
    assert fps_truth_main([str(clip), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["sha256"] == sha256_file(clip)
