"""El gate de ingesta y el `capture.json` que produce.

Bloqueante. Cada chequeo tiene id, resultado, valor observado, valor esperado
y una frase para el entrenador. El orden de evaluación es fijo; el primero que
falla ya decide `reject`, pero se reportan todos (CAPTURA.md §El gate).

Los chequeos de la Fase 1 (encuadre, tasa de detección, una sola persona)
todavía no existen: necesitan pose, y la pose necesita clips reales que hayan
pasado por acá primero.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from kinelab.ingest.capture_paths import CapturePath, CapturePaths
from kinelab.sport import SportConfig
from kinelab.tools.fps_truth import Truth

CAPTURE_SCHEMA_VERSION = "1.0.0"

DURATION_MIN_S = 3.0
DURATION_MAX_S = 180.0
FPS_TOLERANCE = 0.02
VFR_RATIO_MAX = 1.10


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


class CaptureJson(BaseModel):
    """El `capture.json` de una sesión (CONTRATO.md §capture.json)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = CAPTURE_SCHEMA_VERSION
    athlete: str
    gesture: str
    view: str
    capture_path_id: str
    fps_real: float | None = Field(description="tasa de captura, del camino calibrado; None si el camino es desconocido")
    fps_playback: float = Field(description="tasa de reproducción medida de los PTS del clip")
    stretch_factor: float | None
    fps_source: str
    codec: str
    width: int = Field(description="ancho como se ve, con la rotación aplicada")
    height: int
    rotation_deg: int
    frames_decoded: int
    duration_s: float = Field(description="duración REAL: frames_decoded / fps_real cuando el camino es conocido")
    duration_playback_s: float
    vfr_ratio: float
    recorded_at: str | None
    sha256_original: str
    original_name: str
    gate: Gate


def _fail(check_id: str, reason: str, **kw: Any) -> Check:
    return Check(id=check_id, passed=False, reason=reason, **kw)


def _ok(check_id: str, **kw: Any) -> Check:
    return Check(id=check_id, passed=True, **kw)


def _skip(check_id: str, reason: str) -> Check:
    return Check(id=check_id, passed=None, reason=reason)


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

    # 1. El camino tiene que estar calibrado. Sin él no hay contra qué comparar.
    if path is None:
        checks.append(
            _fail(
                "capture_path_known",
                f"El camino de captura '{capture_path_id}' no está calibrado en capture-paths.yaml. "
                "Filmá el cronómetro con ese modo y esa transferencia primero.",
                value=capture_path_id,
            )
        )
    else:
        checks.append(_ok("capture_path_known", value=capture_path_id))

    # 2. Codec: el esperado para ese camino. H.264 donde se esperaba HEVC es la
    #    firma de "Más compatible" o de un transcodificador en el camino.
    if path is None:
        checks.append(_skip("codec_matches_path", "no evaluado: camino desconocido"))
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

    # 3. Tasa variable.
    if c.vfr_ratio <= VFR_RATIO_MAX:
        checks.append(_ok("vfr_ratio_le_1_10", value=round(c.vfr_ratio, 4), expected=f"<= {VFR_RATIO_MAX}"))
    else:
        checks.append(
            _fail(
                "vfr_ratio_le_1_10",
                f"El video tiene tasa variable (delta_max/delta_min = {c.vfr_ratio:.2f}). "
                "Volvé a exportarlo desde el original, o revisá si el teléfono grabó a la tasa que dice.",
                value=round(c.vfr_ratio, 4),
                expected=f"<= {VFR_RATIO_MAX}",
            )
        )

    # 4. La reproducción del clip tiene que coincidir con la del camino.
    if path is None:
        checks.append(_skip("fps_matches_path", "no evaluado: camino desconocido"))
    else:
        rel = abs(c.fps_playback - path.fps_playback) / path.fps_playback
        if rel <= FPS_TOLERANCE:
            checks.append(
                _ok("fps_matches_path", value=round(c.fps_playback, 3), expected=path.fps_playback, tolerance=FPS_TOLERANCE)
            )
        else:
            checks.append(
                _fail(
                    "fps_matches_path",
                    f"El clip reproduce a {c.fps_playback:.2f} fps y el camino '{path.id}' declara "
                    f"{path.fps_playback:g}. Algo lo recomprimió, o vino por otro camino.",
                    value=round(c.fps_playback, 3),
                    expected=path.fps_playback,
                    tolerance=FPS_TOLERANCE,
                )
            )

    # 5. La tasa de captura tiene que alcanzar para el deporte.
    if path is None:
        checks.append(_skip("fps_min_for_gesture", "no evaluado: camino desconocido"))
    elif path.fps_real >= sport.fps_min:
        checks.append(_ok("fps_min_for_gesture", value=path.fps_real, expected=f">= {sport.fps_min}"))
    else:
        checks.append(
            _fail(
                "fps_min_for_gesture",
                f"A {path.fps_real:g} fps de captura no se pueden medir los tiempos del gesto "
                f"({sport.id} pide al menos {sport.fps_min}).",
                value=path.fps_real,
                expected=f">= {sport.fps_min}",
            )
        )

    # 6. Duración REAL plausible. Con el camino conocido, la duración real es
    #    frames / fps_real, que para un Slo-Mo estirado es mucho menor que la
    #    de reproducción.
    real_duration = c.frames_decoded / path.fps_real if path is not None else c.playback_span_s
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
    if path is not None:
        fps_real: float | None = path.fps_real
        stretch: float | None = path.stretch_factor
        fps_source = f"capture-paths.yaml:{path.id}"
        duration = c.frames_decoded / path.fps_real
    else:
        fps_real = None
        stretch = None
        fps_source = "desconocido: camino no calibrado"
        duration = c.playback_span_s
    return CaptureJson(
        athlete=athlete,
        gesture=gesture,
        view=view,
        capture_path_id=capture_path_id,
        fps_real=fps_real,
        fps_playback=round(c.fps_playback, 4),
        stretch_factor=stretch,
        fps_source=fps_source,
        codec=d.codec,
        width=width,
        height=height,
        rotation_deg=d.rotation_deg,
        frames_decoded=c.frames_decoded,
        duration_s=round(duration, 4),
        duration_playback_s=round(c.playback_span_s, 4),
        vfr_ratio=round(c.vfr_ratio, 4),
        recorded_at=d.creation_time,
        sha256_original=sha256_original,
        original_name=original_name,
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
