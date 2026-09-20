"""Las dos fichas del archivo tienen que ser la misma.

`service.exploracion.ficha_de_captura` (desde un `CaptureJson`) y
`kinelab.tools.exportar_demo.ficha_de_captura_min` (desde el dict crudo del
`capture.json`) son copias paralelas a propósito: el motor no puede importar
la del servicio sin arrastrar FastAPI adentro. Lo que no puede pasar es que
diverjan en silencio — el front consume las dos con el mismo tipo
(`FichaArchivo` en `web/src/lib/api.ts`), así que una clave que exista en una
y no en la otra es un `undefined` en la pantalla de la demo estática.

Hasta el encargo 34 nada testeaba que coincidieran.
"""

from __future__ import annotations

import pytest

from kinelab.ingest.gate import CaptureJson, Check, FpsCalibration, Gate
from kinelab.tools.exportar_demo import ficha_de_captura_min
from service.exploracion import ficha_de_captura

SHA_CLIP = "a" * 64
SHA_OTRO = "b" * 64

# Las claves de la ficha que hablan de la calibración del fps y de su
# procedencia. Son las que este test mira una por una, además del conjunto
# entero: si mañana alguien agrega una a una sola de las dos copias, el test
# de las claves lo agarra igual.
CLAVES_DE_CALIBRACION = (
    "fps_real",
    "fps_reproduccion",
    "fps_reproduccion_bruto",
    "stretch_factor",
    "fps_provenance",
    "camino",
    "camino_calibrado",
    "calibracion_clip_sha256",
    "calibracion_mismo_archivo",
    "fps_note",
)


def _capture(**extra) -> CaptureJson:
    base = dict(
        athlete="hernan",
        gesture="driver",
        view="face_on",
        capture_path_id="un-camino",
        capture_path_calibrated=True,
        fps_provenance="medido_aqui",
        fps_real=240.15,
        fps_playback=30.0169,
        fps_playback_raw=30.0169,
        stretch_factor=8.0005,
        fps_source="capture-paths.yaml:un-camino",
        codec="hevc",
        width=1080,
        height=1920,
        rotation_deg=90,
        frames_decoded=2977,
        duration_s=12.3964,
        duration_playback_s=99.18,
        vfr_ratio=1.0027,
        vfr_ratio_raw=1.0027,
        first_delta_s=0.033333,
        fps_note=None,
        recorded_at="2026-09-15T17:26:40.000000Z",
        sha256_original=SHA_OTRO,
        original_name="cortado3-lento.mp4",
        gate=Gate(verdict="ok", checks=[Check(id="capture_path_known", passed=True)], reasons=[]),
    )
    base.update(extra)
    return CaptureJson(**base)


CASOS = {
    # Los tres estados de `same_file`, más una toma sin calibración ninguna.
    "heredado": _capture(fps_calibration=FpsCalibration(clip_sha256=SHA_CLIP, same_file=False)),
    "propio": _capture(sha256_original=SHA_CLIP, fps_calibration=FpsCalibration(clip_sha256=SHA_CLIP, same_file=True)),
    "camino_sin_sha": _capture(),
    "declarado": _capture(capture_path_calibrated=False, fps_provenance="sin_verificar", stretch_factor=1.0),
}


@pytest.mark.parametrize("caso", sorted(CASOS), ids=sorted(CASOS))
def test_both_fichas_have_exactly_the_same_keys(caso):
    c = CASOS[caso]
    del_servicio = ficha_de_captura(c)
    del_motor = ficha_de_captura_min(c.model_dump(mode="json"))
    assert sorted(del_servicio) == sorted(del_motor), (
        "las dos fichas divergieron: son copias paralelas y el front las consume con el mismo tipo"
    )


@pytest.mark.parametrize("caso", sorted(CASOS), ids=sorted(CASOS))
def test_both_fichas_agree_on_every_value(caso):
    c = CASOS[caso]
    assert ficha_de_captura(c) == ficha_de_captura_min(c.model_dump(mode="json"))


@pytest.mark.parametrize("caso", sorted(CASOS), ids=sorted(CASOS))
def test_the_calibration_keys_are_in_both(caso):
    """Explícito además del conjunto entero: son las que agregó el encargo 34 y
    las que el prompt pide que no puedan divergir."""
    c = CASOS[caso]
    del_servicio = ficha_de_captura(c)
    del_motor = ficha_de_captura_min(c.model_dump(mode="json"))
    for k in CLAVES_DE_CALIBRACION:
        assert k in del_servicio, k
        assert k in del_motor, k
        assert del_servicio[k] == del_motor[k], k


def test_the_fichas_carry_the_three_states_of_same_file():
    """Y lo que llevan no es siempre lo mismo: si las dos copias devolvieran
    `None` en los tres casos, los tests de arriba pasarían igual."""
    estados = {caso: ficha_de_captura(c)["calibracion_mismo_archivo"] for caso, c in CASOS.items()}
    assert estados == {"heredado": False, "propio": True, "camino_sin_sha": None, "declarado": None}
    shas = {caso: ficha_de_captura(c)["calibracion_clip_sha256"] for caso, c in CASOS.items()}
    assert shas == {"heredado": SHA_CLIP, "propio": SHA_CLIP, "camino_sin_sha": None, "declarado": None}


def test_a_1_2_0_capture_json_without_the_field_still_makes_a_ficha():
    """Un `capture.json` anterior al bump no trae `fps_calibration`. Tiene que
    cargar (el campo es opcional) y la ficha tiene que decir `None`, no
    romperse ni inventar."""
    d = _capture().model_dump(mode="json")
    del d["fps_calibration"]
    c = CaptureJson.model_validate(d)
    assert c.fps_calibration.same_file is None and c.fps_calibration.clip_sha256 is None
    for ficha in (ficha_de_captura(c), ficha_de_captura_min(d)):
        assert ficha["calibracion_mismo_archivo"] is None
        assert ficha["calibracion_clip_sha256"] is None
