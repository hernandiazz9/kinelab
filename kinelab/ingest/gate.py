"""El gate de ingesta y el `capture.json` que produce.

Bloqueante. Cada chequeo tiene id, resultado, valor observado, valor esperado
y una frase para el entrenador. El orden de evaluación es fijo; el primero que
falla ya decide `reject`, pero se reportan todos (CAPTURA.md §El gate).

`vfr_ratio_le_1_10` y `fps_matches_path` evalúan los números EFECTIVOS de
`fps_truth` — sin el primer delta de PTS cuando el arranque de la cámara es la
única anomalía —, que son los mismos que usa el motor. Los brutos viajan igual
en el `capture.json` (`vfr_ratio_raw`, `fps_playback_raw`, `first_delta_s`) y,
cuando difieren, el chequeo lo dice en su propio registro: nunca en silencio.
Ver CAPTURA.md §El gate de ingesta y el informe 2026-09-14-03.

`fps_calibration` NO es un chequeo: es procedencia. Dice de qué clip salió el
cronómetro del camino y si ese clip es este mismo archivo. Un camino que no lo
declara sigue pasando igual — la procedencia se registra, no se exige—, y lo
que el entrenador lee sale de `analysis.warnings`, que es el canal que llega a
la pantalla también en exploración, donde el gate no corre.

Un camino DECLARADO sin cronómetro (ADR-016) pasa `capture_path_known` y lo
dice: la tasa de captura se asume igual a la de reproducción efectiva
(`stretch_factor` 1,0), la procedencia del fps es `sin_verificar` y viaja al
`capture.json`, al `analysis.json` y a cada métrica, donde impide todo juicio.
Un `slomo` sin calibrar se rechaza: sin cronómetro el factor de estiramiento es
desconocido.

Los chequeos de la Fase 1 —`body_height_px`, `detection_rate`, `single_subject`—
**existen desde el encargo 17** y los escribe `kinelab.perception.run`, en el
mismo `capture.json`, después de correr la pose. Este módulo no los evalúa: acá
todavía no hay pose. Se rehacen en cada corrida de percepción, así que no
deciden si esa corrida arranca: lo que la bloquea son los de ingesta, los nueve
de `CONTRATO.md` §capture.json (`kinelab.perception.run._blocking_checks`,
encargo 30).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from kinelab.ingest.capture_paths import CapturePath, CapturePaths
from kinelab.sport import SportConfig
from kinelab.tools.fps_truth import Counted, Truth, first_delta_note

# 1.3.0: aparece `fps_calibration` (de qué clip salió el cronómetro del camino,
# y si es este mismo archivo), opcional. 1.2.0: aparecen
# `capture_path_calibrated` y `fps_provenance` (ADR-016), los dos opcionales.
# 1.1.0: `fps_playback` y `vfr_ratio` pasan a ser los EFECTIVOS y aparecen
# `fps_playback_raw`, `vfr_ratio_raw`, `first_delta_s` y `fps_note`.
# Un capture.json 1.0.0 sigue validando, con los nuevos en su default.
CAPTURE_SCHEMA_VERSION = "1.3.0"

DURATION_MIN_S = 3.0
DURATION_MAX_S = 180.0
FPS_TOLERANCE = 0.02
VFR_RATIO_MAX = 1.10

# Procedencia del fps real (CONTEXTO.md §procedencia). `medido_aqui` = cronómetro
# filmado en un camino calibrado; `sin_verificar` = camino declarado, o ninguno.
FpsProvenance = Literal["medido_aqui", "sin_verificar"]

# Lo que el entrenador tiene que leer antes de cualquier número cuando el camino
# es declarado. La misma frase viaja al `analysis.json` como warning.
DECLARED_NOTE = (
    "camino declarado sin cronómetro: los tiempos asumen que el archivo reproduce "
    "a la velocidad de captura"
)


class Check(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    # None = no se pudo evaluar (por ejemplo, el camino de captura es desconocido
    # y sin él no hay contra qué comparar). No cuenta como fallo, pero se ve.
    passed: bool | None
    value: Any = None
    expected: Any = None
    tolerance: Any = None
    reason: str | None = None


class Gate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: Literal["ok", "reject"]
    checks: list[Check]
    reasons: list[str]


class FpsCalibration(BaseModel):
    """De dónde sale el cronómetro con el que se midió el fps de esta toma.

    Es un dato de PROCEDENCIA, no un chequeo: nada de acá rechaza una toma ni
    cambia un número. Lo único que hace es dejar escrito lo que hasta hoy no se
    podía saber — el camino declara un `fps_real` y había que creerle sin saber
    de qué clip había salido (`capture-paths.yaml` §calibration_clip_sha256).

    - `clip_sha256`: el clip que calibró el camino, tal como el camino lo
      declara. `None` cuando no lo declara, o cuando el camino no está
      calibrado (ahí no hubo cronómetro y no hay nada que declarar).
    - `same_file`: `True` si ese clip es ESTE archivo — la toma se calibró a sí
      misma, que es el método preferido de `CAPTURA.md` §El método preferido—;
      `False` si el fps es heredado de otro archivo del mismo camino; `None`
      cuando no se puede saber porque el camino no declara el sha.
    """

    model_config = ConfigDict(extra="forbid")

    clip_sha256: str | None = None
    same_file: bool | None = None


class CaptureJson(BaseModel):
    """El `capture.json` de una sesión (CONTRATO.md §capture.json)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = CAPTURE_SCHEMA_VERSION
    athlete: str
    gesture: str
    view: str
    capture_path_id: str
    capture_path_calibrated: bool | None = Field(
        default=None,
        description="True = camino calibrado con cronómetro; False = declarado (ADR-016); None = desconocido o capture.json 1.1.0",
    )
    fps_provenance: FpsProvenance = Field(
        default="sin_verificar",
        description="de dónde sale fps_real: `medido_aqui` (cronómetro) o `sin_verificar` (asumido de la reproducción). "
        "El default es el conservador: sin el campo, nada puede ser juicio.",
    )
    fps_real: float | None = Field(description="tasa de captura: del camino calibrado, o asumida igual a la de reproducción en un camino declarado; None si no hay camino usable")
    fps_playback: float = Field(
        description="tasa de reproducción EFECTIVA, medida de los PTS: sin el primer delta cuando el arranque "
        "de la cámara es la única anomalía. Es la que evalúa el gate."
    )
    fps_playback_raw: float | None = Field(
        default=None,
        description="la misma tasa sobre todos los deltas, el primero incluido; None en un capture.json 1.0.0",
    )
    stretch_factor: float | None
    fps_source: str
    codec: str
    width: int = Field(description="ancho como se ve, con la rotación aplicada")
    height: int
    rotation_deg: int
    frames_decoded: int
    duration_s: float = Field(description="duración REAL: frames_decoded / fps_real cuando el camino es conocido")
    duration_playback_s: float = Field(description="span de PTS medido, con el hueco del arranque adentro si lo hubo")
    vfr_ratio: float = Field(description="delta_max/delta_min EFECTIVO, con el mismo criterio que fps_playback")
    vfr_ratio_raw: float | None = Field(default=None, description="el mismo cociente sobre todos los deltas; None en un capture.json 1.0.0")
    first_delta_s: float | None = Field(default=None, description="el primer delta de PTS, el del arranque de la cámara")
    fps_note: str | None = Field(default=None, description="por qué el efectivo difiere del bruto; None cuando coinciden")
    recorded_at: str | None
    sha256_original: str
    original_name: str
    fps_calibration: FpsCalibration = Field(
        default_factory=FpsCalibration,
        description="de qué clip salió el cronómetro del camino, y si es este mismo archivo. "
        "Opcional: un capture.json 1.2.0 sigue validando, con los dos campos en None.",
    )
    gate: Gate


def _fail(check_id: str, reason: str, **kw: Any) -> Check:
    return Check(id=check_id, passed=False, reason=reason, **kw)


def _ok(check_id: str, **kw: Any) -> Check:
    return Check(id=check_id, passed=True, **kw)


def _skip(check_id: str, reason: str, **kw: Any) -> Check:
    """`passed=None`: el chequeo no se pudo evaluar. No cuenta como fallo, pero se ve."""
    return Check(id=check_id, passed=None, reason=reason, **kw)


# Lo que cada chequeo agrega a su propio registro cuando el número que evaluó no
# es el bruto del archivo. El entrenador tiene que ver que hubo una corrección y
# de cuánto; nunca en silencio (CAPTURA.md §El gate de ingesta). `None` cuando
# los dos números coinciden, que es el caso normal.


def _startup_vfr_note(c: Counted) -> str | None:
    if not c.first_delta_is_the_only_outlier:
        return None
    return (
        f"ratio {c.vfr_ratio_effective:.3f} sin el primer delta de {c.delta_first_s:.3f} s "
        f"(arranque de la cámara); bruto {c.vfr_ratio:.3f}."
    )


def _startup_fps_note(c: Counted) -> str | None:
    if not c.first_delta_is_the_only_outlier:
        return None
    return (
        f"reproducción {c.fps_playback_effective:.3f} fps sin el primer delta de {c.delta_first_s:.3f} s "
        f"(arranque de la cámara); bruto {c.fps_playback:.3f} fps."
    )


# --- caminos declarados sin calibrar (ADR-016) -------------------------------


def path_is_usable(path: CapturePath | None) -> bool:
    """Si del camino se puede sacar una tasa de captura. Un `slomo` declarado no:
    sin cronómetro el factor de estiramiento es desconocido."""
    return path is not None and (path.calibrated or path.mode == "video")


def fps_real_for(path: CapturePath | None, c: Counted) -> float | None:
    """La tasa de CAPTURA que va a usar el motor. Calibrada, sale del cronómetro;
    declarada, se ASUME igual a la de reproducción efectiva (ADR-016). Nunca se
    infiere del contenedor un factor de estiramiento."""
    if not path_is_usable(path):
        return None
    return path.fps_real if path.calibrated else round(c.fps_playback_effective, 4)


def fps_provenance_for(path: CapturePath | None) -> FpsProvenance:
    return "medido_aqui" if (path is not None and path.calibrated) else "sin_verificar"


def fps_calibration_for(path: CapturePath | None, sha256_original: str) -> FpsCalibration:
    """La procedencia del cronómetro de esta toma. Comparar sale gratis: el sha
    del original ya se calculó para el `capture.json` y no hace falta otro.

    Un camino sin calibrar no tiene cronómetro, así que tampoco tiene clip que
    lo haya medido: los dos campos quedan en `None`. Lo mismo un camino
    calibrado que no declara el sha — que sigue siendo válido a propósito
    (`capture_paths._CALIBRATION_FIELDS`).
    """
    if path is None or not path.calibrated or path.calibration_clip_sha256 is None:
        return FpsCalibration()
    return FpsCalibration(
        clip_sha256=path.calibration_clip_sha256,
        same_file=path.calibration_clip_sha256 == sha256_original,
    )


def declared_reason(path: CapturePath) -> str:
    return f"'{path.id}' es un {DECLARED_NOTE} ({path.device}, modo {path.mode}). Filmá el cronómetro para convertirlo en calibrado."


def slomo_declared_reason(path: CapturePath) -> str:
    return (
        f"El camino '{path.id}' es Slo-Mo y no está calibrado: sin cronómetro el factor de "
        "estiramiento es desconocido y cualquier tiempo sería ficción. Filmá el cronómetro con "
        "ese modo y esa transferencia primero."
    )


def run_gate(
    truth: Truth,
    *,
    capture_path_id: str,
    capture_paths: CapturePaths,
    sport: SportConfig,
    gesture: str,
    view: str,
) -> Gate:
    checks: list[Check] = []
    path: CapturePath | None = capture_paths.get(capture_path_id)
    d, c = truth.declared, truth.counted
    # La tasa de captura con la que se juzga todo lo temporal, y de dónde sale.
    fps_real = fps_real_for(path, c)
    provenance = fps_provenance_for(path)

    # 1. El camino tiene que estar en capture-paths.yaml. Calibrado pasa liso;
    #    declarado pasa diciendo bajo qué supuesto (ADR-016); un slomo sin
    #    calibrar no pasa, porque su factor de estiramiento es desconocido.
    if path is None:
        checks.append(
            _fail(
                "capture_path_known",
                f"El camino de captura '{capture_path_id}' no está en capture-paths.yaml. "
                "Declaralo (dispositivo y modo) o filmá el cronómetro con ese modo y esa transferencia.",
                value=capture_path_id,
            )
        )
    elif not path.calibrated and path.mode == "slomo":
        checks.append(_fail("capture_path_known", slomo_declared_reason(path), value=capture_path_id))
    elif not path.calibrated:
        checks.append(_ok("capture_path_known", value=capture_path_id, reason=declared_reason(path)))
    else:
        checks.append(_ok("capture_path_known", value=capture_path_id))

    # 2. Codec: el esperado para ese camino. H.264 donde se esperaba HEVC es la
    #    firma de "Más compatible" o de un transcodificador en el camino. Un
    #    camino que no declara codec (declarado genérico) no tiene qué comparar.
    if path is None:
        checks.append(_skip("codec_matches_path", "no evaluado: camino desconocido"))
    elif path.codec_expected is None:
        checks.append(_skip("codec_matches_path", f"no evaluado: el camino '{path.id}' no declara codec", value=d.codec))
    elif d.codec == path.codec_expected:
        checks.append(_ok("codec_matches_path", value=d.codec, expected=path.codec_expected))
    else:
        if d.codec == "h264" and path.codec_expected == "hevc":
            reason = (
                "El clip está en H.264 y el camino espera HEVC: pasó por 'Más compatible' o por "
                "un transcodificador. Volvé a exportarlo con 'Mantener originales'."
            )
        else:
            reason = f"El clip está en {d.codec} y el camino espera {path.codec_expected}."
        checks.append(_fail("codec_matches_path", reason, value=d.codec, expected=path.codec_expected))

    # 3. Tasa variable. Se juzga el ratio EFECTIVO: un solo delta de arranque no
    #    es tasa variable (informe 2026-09-14-03). Cuando difiere del bruto, el
    #    chequeo lo dice en su propio registro, pase o no.
    nota_vfr = _startup_vfr_note(c)
    if c.vfr_ratio_effective <= VFR_RATIO_MAX:
        checks.append(_ok("vfr_ratio_le_1_10", value=round(c.vfr_ratio_effective, 4), expected=f"<= {VFR_RATIO_MAX}", reason=nota_vfr))
    else:
        checks.append(
            _fail(
                "vfr_ratio_le_1_10",
                f"El video tiene tasa variable (delta_max/delta_min = {c.vfr_ratio_effective:.2f}). "
                "Volvé a exportarlo desde el original, o revisá si el teléfono grabó a la tasa que dice.",
                value=round(c.vfr_ratio_effective, 4),
                expected=f"<= {VFR_RATIO_MAX}",
            )
        )

    # 4. La reproducción del clip tiene que coincidir con la del camino, con la
    #    misma tasa efectiva que usa el motor. Un camino declarado no tiene
    #    reproducción medida: no hay contra qué comparar, y no se inventa.
    if path is None:
        checks.append(_skip("fps_matches_path", "no evaluado: camino desconocido"))
    elif not path.calibrated:
        checks.append(
            _skip(
                "fps_matches_path",
                f"no evaluado: el camino '{path.id}' no está calibrado y no declara fps de reproducción; no hay contra qué comparar",
                value=round(c.fps_playback_effective, 3),
            )
        )
    else:
        fps = c.fps_playback_effective
        nota_fps = _startup_fps_note(c)
        rel = abs(fps - path.fps_playback) / path.fps_playback
        if rel <= FPS_TOLERANCE:
            checks.append(
                _ok("fps_matches_path", value=round(fps, 3), expected=path.fps_playback, tolerance=FPS_TOLERANCE, reason=nota_fps)
            )
        else:
            checks.append(
                _fail(
                    "fps_matches_path",
                    f"El clip reproduce a {fps:.2f} fps y el camino '{path.id}' declara "
                    f"{path.fps_playback:g}. Algo lo recomprimió, o vino por otro camino."
                    + (f" ({nota_fps})" if nota_fps else ""),
                    value=round(fps, 3),
                    expected=path.fps_playback,
                    tolerance=FPS_TOLERANCE,
                )
            )

    # 5. La tasa de captura tiene que alcanzar para el deporte.
    if path is None:
        checks.append(_skip("fps_min_for_gesture", "no evaluado: camino desconocido"))
    elif fps_real is None:
        checks.append(_skip("fps_min_for_gesture", f"no evaluado: sin factor de estiramiento, el camino '{path.id}' no da tasa de captura"))
    else:
        # En un camino declarado el número es ASUMIDO, no medido: el chequeo lo
        # dice en su propio registro, pase o falle (ADR-016).
        nota_real = None if provenance == "medido_aqui" else f"Tasa de captura asumida igual a la de reproducción: {DECLARED_NOTE}."
        if fps_real >= sport.fps_min:
            checks.append(_ok("fps_min_for_gesture", value=fps_real, expected=f">= {sport.fps_min}", reason=nota_real))
        else:
            checks.append(
                _fail(
                    "fps_min_for_gesture",
                    f"A {fps_real:g} fps de captura no se pueden medir los tiempos del gesto "
                    f"({sport.id} pide al menos {sport.fps_min})." + (f" {nota_real}" if nota_real else ""),
                    value=fps_real,
                    expected=f">= {sport.fps_min}",
                )
            )

    # 6. Duración REAL plausible. Con la tasa de captura conocida, la duración
    #    real es frames / fps_real, que para un Slo-Mo estirado es mucho menor
    #    que la de reproducción. Sin tasa de captura, el span de PTS.
    real_duration = c.frames_decoded / fps_real if fps_real is not None else c.playback_span_s
    if DURATION_MIN_S <= real_duration <= DURATION_MAX_S:
        checks.append(_ok("duration_plausible", value=round(real_duration, 3), expected=f"{DURATION_MIN_S:g}–{DURATION_MAX_S:g} s"))
    else:
        checks.append(
            _fail(
                "duration_plausible",
                f"La toma dura {real_duration:.1f} s reales; se esperan entre {DURATION_MIN_S:g} y {DURATION_MAX_S:g}.",
                value=round(real_duration, 3),
                expected=f"{DURATION_MIN_S:g}–{DURATION_MAX_S:g} s",
            )
        )

    # 7. Rotación leída y dimensiones reales. La normalización al master.mp4
    #    llega en la Fase 4; acá alcanza con no mentir sobre ancho y alto.
    if d.rotation_deg in (0, 90, 180, 270):
        checks.append(_ok("rotation_normalized", value=d.rotation_deg))
    else:
        checks.append(_fail("rotation_normalized", f"Rotación de metadatos rara: {d.rotation_deg}°.", value=d.rotation_deg))

    # 8. Vista y gesto declarados existen en el deporte.
    if view in sport.views:
        checks.append(_ok("view_declared", value=view, expected=list(sport.views)))
    else:
        checks.append(
            _fail("view_declared", f"La vista '{view}' no existe en {sport.id}; las válidas son {', '.join(sport.views)}.", value=view, expected=list(sport.views))
        )
    if gesture in sport.gestures:
        checks.append(_ok("gesture_known", value=gesture, expected=list(sport.gestures)))
    else:
        checks.append(
            _fail("gesture_known", f"El gesto '{gesture}' no existe en {sport.id}; los válidos son {', '.join(sport.gestures)}.", value=gesture, expected=list(sport.gestures))
        )

    reasons = [ch.reason for ch in checks if ch.passed is False and ch.reason]
    return Gate(verdict="reject" if reasons else "ok", checks=checks, reasons=reasons)


def build_capture_json(
    truth: Truth,
    gate: Gate,
    *,
    athlete: str,
    gesture: str,
    view: str,
    capture_path_id: str,
    capture_paths: CapturePaths,
    sha256_original: str,
    original_name: str,
) -> CaptureJson:
    d, c = truth.declared, truth.counted
    path = capture_paths.get(capture_path_id)
    width, height = d.display_size
    fps_real = fps_real_for(path, c)
    if path is None:
        stretch: float | None = None
        fps_source = "desconocido: camino no calibrado"
    elif path.calibrated:
        stretch = path.stretch_factor
        fps_source = f"capture-paths.yaml:{path.id}"
    else:
        # Declarado (ADR-016): el estiramiento se asume 1,0 — el archivo
        # reproduce a la velocidad a la que capturó — y se dice de dónde sale.
        stretch = 1.0 if fps_real is not None else None
        fps_source = f"declarado:{path.id}" + ("" if fps_real is not None else " (slomo sin calibrar: factor de estiramiento desconocido)")
    duration = c.frames_decoded / fps_real if fps_real is not None else c.playback_span_s
    return CaptureJson(
        athlete=athlete,
        gesture=gesture,
        view=view,
        capture_path_id=capture_path_id,
        capture_path_calibrated=None if path is None else path.calibrated,
        fps_provenance=fps_provenance_for(path),
        fps_real=fps_real,
        fps_playback=round(c.fps_playback_effective, 4),
        fps_playback_raw=round(c.fps_playback, 4),
        stretch_factor=stretch,
        fps_source=fps_source,
        codec=d.codec,
        width=width,
        height=height,
        rotation_deg=d.rotation_deg,
        frames_decoded=c.frames_decoded,
        duration_s=round(duration, 4),
        duration_playback_s=round(c.playback_span_s, 4),
        vfr_ratio=round(c.vfr_ratio_effective, 4),
        vfr_ratio_raw=round(c.vfr_ratio, 4),
        first_delta_s=round(c.delta_first_s, 6),
        fps_note=first_delta_note(c),
        recorded_at=d.creation_time,
        sha256_original=sha256_original,
        original_name=original_name,
        # Sin hash extra: `sha256_original` ya llegó calculado.
        fps_calibration=fps_calibration_for(path, sha256_original),
        gate=gate,
    )


def with_checks(gate: Gate, new: list[Check], after: str) -> Gate:
    """Devuelve un gate nuevo con `new` insertados después del chequeo `after`
    (reemplazando los que ya existan con el mismo id) y el veredicto recalculado.
    No muta la entrada. Lo usa la Fase 1 para sumar sus chequeos al capture.json."""
    new_ids = {c.id for c in new}
    kept = [c for c in gate.checks if c.id not in new_ids]
    pos = next((i + 1 for i, c in enumerate(kept) if c.id == after), len(kept))
    checks = kept[:pos] + list(new) + kept[pos:]
    reasons = [c.reason for c in checks if c.passed is False and c.reason]
    return Gate(verdict="reject" if reasons else "ok", checks=checks, reasons=reasons)
