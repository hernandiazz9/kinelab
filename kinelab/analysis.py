"""De `pose.npz` a `analysis.json` (Fase 2): señales, segmentación, eventos del
deporte, correcciones manuales, calidad y series. Todo se recalcula desde la
pose cruda; nada de acá vuelve a mirar el video ni el modelo.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import yaml

import kinelab
from kinelab.contract.write import write_analysis
from kinelab.events.manual import apply_edits, load_edits
from kinelab.events.primitives import MissingEvent
from kinelab.events.segmentation import segment_reps
from kinelab.events.signal import butterworth_lowpass, cutoff_for_fps, hands_center, speed
from kinelab.ingest.gate import DECLARED_NOTE, CaptureJson
from kinelab.ingest.session import sha256_file
from kinelab.metrics.core import SCALE_SOURCE_FRAME, MetricContext, evaluate
from kinelab.metrics.generic import repeatability_curves, repeatability_scalar
from kinelab.metrics.registry import REGISTRY, Registry
from kinelab.perception.framing import body_height_px
from kinelab.perception.gaps import interpolate_gaps
from kinelab.perception.posestore import POSE_FILE, PoseData, load_pose
from kinelab.sport import SportConfig

# 2.1.0 (encargo 33): entran `reps[].scale_px` y `reps[].scale_source`, los dos
# OPCIONALES — un campo nuevo y opcional es minor (§Versionado). Son el divisor
# en píxeles de las métricas en cm de ESA repetición y de dónde sale, porque
# `quality.scale_px` es la mediana entre repeticiones y con dos o más no es el
# divisor de ninguna. Ningún valor publicado cambia.
# 2.0.0 (ADR-018): mueren `summary.gain` y `events[].sequence_order`, los dos
# requeridos por el schema — sacar un campo requerido es major. En el mismo bump
# entran `metric_version` en cada sextuplo, `quality.scale_px` y el lugar
# opcional de `events[].<evento>.subframe.mdc`. 1.2.0: `fps_provenance` en el
# header y en cada métrica (ADR-016); 1.1.0: `subframe` opcional en los eventos.
SCHEMA_VERSION = "2.1.0"
SERIES_MAX_HZ = 10.0
QUALITY_MIN_DETECTION = 0.90
QUALITY_MAX_PLAUSIBILITY_REJECT = 0.05
QUALITY_MAX_CAMERA_MOTION_PX = 2.0


class AnalysisError(RuntimeError):
    pass


@dataclass
class SwingSignals:
    fps: float
    hands_raw: np.ndarray  # (T,2) px, con huecos ≤ max_gap rellenados
    hands: np.ndarray  # (T,2) px filtradas
    speed: np.ndarray  # (T,) alturas de cuerpo / s
    body_height: np.ndarray  # (T,) px
    valid: np.ndarray  # (T,) bool
    params: dict
    noise_floor_bh_s: float = 0.0  # p10 de la velocidad quieta de las manos: el piso de ruido del propio clip
    view: str | None = None  # vista declarada de la toma; None = desconocida (exploración por cuadro)


def swing_signals(pose: PoseData, fps: float, *, cutoff_hz_max: float = 12.0, max_gap: int = 5, view: str | None = None, wrist_score_min: float = 0.0) -> SwingSignals:
    # `wrist_score_min` es el umbral POR DEBAJO del cual una muñeca no entra al centro
    # de manos. El umbral es del deporte, no del motor (invariante 13): llega por
    # parámetro desde `build_analysis`. Default 0,0 = sin umbral, las dos muñecas
    # pesadas por su confianza.
    kp = interpolate_gaps(pose.keypoints, max_gap)
    hands_raw = hands_center(kp, pose.scores, min_score=wrist_score_min, max_gap=max_gap)
    bh = body_height_px(kp, fps)
    if np.isfinite(bh).any():
        scale = np.where(np.isfinite(bh) & (bh > 0), bh, np.nanmedian(bh))
        unit = "body_heights"
    else:
        scale = np.ones(kp.shape[0])
        unit = "px (sin altura de cuerpo)"
    cutoff = cutoff_for_fps(fps, cutoff_hz_max)
    hands = butterworth_lowpass(hands_raw, fps, cutoff_hz=cutoff)
    spd = speed(hands, fps, scale)
    # Piso de ruido del clip: p10 de la velocidad con mediana móvil corta (los cuadros más
    # quietos). p25 no sirve: en un clip corto lleno de movimiento sube hasta aceptar
    # movimiento lento como quietud (medido en el primer clip real).
    from kinelab.events.primitives import stillness_signal

    still = stillness_signal(spd, fps, 0.1)
    floor = float(np.nanpercentile(still, 10)) if np.isfinite(still).any() else 0.0
    return SwingSignals(fps=fps, hands_raw=hands_raw, hands=hands, speed=spd, body_height=bh, valid=np.isfinite(hands).all(axis=1), params={"filter": "butterworth", "order": 4, "cutoff_hz": cutoff, "cutoff_hz_max": cutoff_hz_max, "gap_fill_max_frames": max_gap, "speed_unit": unit, "signal": "hands_center", "wrist_score_min": float(wrist_score_min), "noise_floor_bh_s": round(floor, 4)}, noise_floor_bh_s=floor, view=view)


def _scale_summary(scales: list[dict]) -> dict:
    """`quality.scale_px`: el **agregado entre repeticiones** de la escala, con el
    cuadro en que se midió (CONTRATO.md §La escala).

    Hay una escala **por repetición**, y es la que divide: viaja en
    `reps[].scale_px`. Con varias, el número que se publica acá es la **mediana
    entre repeticiones** y el cuadro es el de la repetición que la aporta —nunca
    un promedio de cuadros, que no sería ningún cuadro—, así que con dos o más
    repeticiones este número **no es el divisor de ninguna fila ni de ninguna
    métrica**. El `method` lo dice, porque durante un tiempo se lo leyó como si
    lo fuera. Sin ninguna escala medible el valor es `null` y `method` dice por
    qué: en ese caso cada métrica en cm cae a `body_height_px` del cuadro."""
    ok = [s for s in scales if s.get("value") is not None]
    if not ok:
        method = "sin_repeticiones" if not scales else "sin_cadena_medible"
        note = {
            "sin_repeticiones": "no se calculó ninguna escala: no hay repeticiones con métricas",
            "sin_cadena_medible": "la cadena de la estatura no se pudo medir en ningún cuadro; cada métrica en cm cae a body_height_px (CONTRATO.md §La escala)",
        }[method]
        return {"value": None, "frame": None, "method": f"{method}: {note}"}
    med = float(np.median([s["value"] for s in ok]))
    pick = min(ok, key=lambda s: (abs(s["value"] - med), s["frame"]))
    method = pick["method"] if len(ok) == 1 else f"{pick['method']} · mediana entre {len(ok)} repeticiones: no es el divisor de ninguna, el de cada una está en reps[].scale_px"
    return {"value": round(pick["value"], 1), "frame": pick["frame"], "method": method}


def _quality(pose: PoseData, rep_count: int, scales: list[dict] | None = None) -> dict:
    prov = pose.provenance
    framing = prov.get("framing") or {}
    T = int(pose.keypoints.shape[0])
    rejected = int(np.count_nonzero(pose.plausibility))
    counts = prov.get("plausibility_counts") or {}
    rate = float(framing.get("detection_rate", 0.0) or 0.0)
    motion = prov.get("camera_motion_px")
    reasons: list[str] = []
    if rate < QUALITY_MIN_DETECTION:
        reasons.append(f"Se perdió al jugador en el {round(100 * (1 - rate))} % de los cuadros.")
    if rep_count == 0:
        reasons.append("No se encontró ninguna repetición del gesto.")
    verdict = "no_usar" if reasons else "confiable"
    if verdict == "confiable":
        if T and rejected / T > QUALITY_MAX_PLAUSIBILITY_REJECT:
            reasons.append(f"El {round(100 * rejected / T)} % de los cuadros tiene una pose implausible.")
        if motion is not None and motion > QUALITY_MAX_CAMERA_MOTION_PX:
            reasons.append(f"La cámara se movió ({motion:.1f} px entre muestras).")
        if reasons:
            verdict = "con_reservas"
    return {
        "detection_rate": rate,
        "body_height_px": {"median": framing.get("body_height_px_median"), "min": framing.get("body_height_px_min"), "max": framing.get("body_height_px_max"), "frac_of_frame": framing.get("frac_of_frame")},
        "blur_estimate": None,
        "plausibility": {"rejected_frames": rejected, "by_reason": {k: int(v) for k, v in counts.items()}},
        "camera_motion_px": motion,
        "scale_px": _scale_summary(scales or []),
        "verdict": verdict,
        "reasons": reasons,
    }


def athlete_height_m(take_dir: Path, athlete: str) -> float | None:
    """`altura_m` de data/athletes/<slug>.yaml (CONTRATO.md §Layout), si existe."""
    for parent in take_dir.resolve().parents:
        f = parent / "athletes" / f"{athlete}.yaml"
        if f.is_file():
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            h = data.get("altura_m")
            return float(h) if h else None
    return None


def build_analysis(take_dir: Path, capture: CaptureJson, pose: PoseData, sport: SportConfig, *, registry: Registry | None = None, height_m: float | None = None) -> dict:
    ev = sport.events
    if ev is None:
        raise AnalysisError(f"{sport.id}: el deporte no define eventos todavía.")
    if capture.fps_real is None:
        raise AnalysisError(
            f"{take_dir}: el capture.json no tiene tasa de captura (camino '{capture.capture_path_id}'). "
            "Declará el camino en capture-paths.yaml o filmá el cronómetro; sin fps no hay eje de tiempo."
        )
    fps = float(capture.fps_real)
    sig = swing_signals(pose, fps, cutoff_hz_max=ev.cutoff_hz_max, view=capture.view, wrist_score_min=float(getattr(ev.params, "wrist_score_min", 0.0) or 0.0))
    cands, rejected = segment_reps(sig.speed, fps, ev.segmentation)
    events_out: list[dict] = []
    reps: list[dict] = []
    # Los eventos que el deporte declaró ausentes CON su razón (`MissingEvent`).
    # En el JSON son `null` —`$defs/event` no admite campos nuevos— y la razón va
    # a `warnings[]`, como las de ADR-019. Un `None` pelado no deja rastro: es la
    # diferencia entre "no lo hay, y por esto" y "nadie lo buscó".
    event_notes: list[str] = []
    prev_end = -1
    for c in cands:
        events, reason = ev.detect(sig, c)
        if reason:
            rejected[reason] = rejected.get(reason, 0) + 1
            continue
        start = events["address"].frame
        end = events["follow_end"].frame if events.get("follow_end") else c.end
        if start <= prev_end:
            rejected["solapada"] = rejected.get("solapada", 0) + 1
            continue
        n = len(reps) + 1
        event_notes += [f"Repetición {n}: sin `{events[k].id}` — {events[k].reason}" for k in ev.order if isinstance(events.get(k), MissingEvent)]
        events_out.append({"rep": n, **{k: (events[k].to_dict() if events.get(k) else None) for k in ev.order}})
        # `scale_px` / `scale_source` se llenan abajo, con el `MetricContext` de
        # esta repetición: son el divisor de sus métricas en cm y de las filas de
        # la tabla por cuadro que caen adentro (CONTRATO.md §La escala). Arrancan
        # en `None` porque un `null` nunca se omite, y quedan en `None` si el
        # deporte no tiene registro de métricas: ahí no hay ningún cm que dividir.
        reps.append({"rep": n, "frame_start": int(start), "frame_end": int(end), "t_start": round(start / fps, 4), "t_end": round(end / fps, 4), "peak_speed_bh_s": round(c.peak_speed, 3), "scale_px": None, "scale_source": None, "metrics": {}})
        prev_end = end
    edits = load_edits(take_dir)
    if edits:
        events_out = apply_edits(events_out, edits, fps=fps, order=ev.order)
        for r, e in zip(reps, events_out):
            r["frame_start"] = e["address"]["frame"] if e.get("address") else r["frame_start"]
            r["frame_end"] = e["follow_end"]["frame"] if e.get("follow_end") else r["frame_end"]
            r["t_start"], r["t_end"] = round(r["frame_start"] / fps, 4), round(r["frame_end"] / fps, 4)
    # --- métricas por repetición y resumen (Fase 3) ---
    sm = sport.metrics
    registry = registry or (sm.registry if sm else REGISTRY)
    summary_metrics: dict = {}
    scales: list[dict] = []
    warnings: list[str] = []
    if sm is not None and reps:
        kp = interpolate_gaps(pose.keypoints, 5)
        if height_m is None:
            warnings.append("Sin altura declarada del atleta: las métricas en cm quedan en null. Creá data/athletes/<slug>.yaml con altura_m o pasá --altura-m.")
        per_metric: dict[str, list] = {m.id: [] for m in registry}
        curves: list[np.ndarray] = []
        for r, e in zip(reps, events_out):
            ev_frames = {k: e[k]["frame"] for k in ev.order if e.get(k)}
            ctx = MetricContext(keypoints=kp, scores=pose.scores, fps=fps, view=capture.view, body_height_px=sig.body_height, events=ev_frames, frame_start=r["frame_start"], frame_end=r["frame_end"], fps_provenance=capture.fps_provenance, athlete_height_m=height_m, hands_speed=sig.speed, tolerances={k: int(e[k]["tol_frames"]) for k in ev.order if e.get(k)})
            for m in registry:
                out = evaluate(m, ctx, joints=sm.joints.get(m.id, ()))
                r["metrics"][m.id] = out
                per_metric[m.id].append(out["value"])
            if "top" in ev_frames and "impact" in ev_frames:
                curves.append(sig.speed[ev_frames["top"] : ev_frames["impact"] + 1])
            det = ctx.scale_detail()
            scales.append(det)
            # La escala de ESTA repetición, al lado de sus métricas. `quality.scale_px`
            # es la mediana entre repeticiones y con dos o más no es el divisor de
            # ninguna: el divisor es éste (CONTRATO.md §La escala).
            r["scale_px"], r["scale_source"] = det["value"], det["source"]
            if det["source"] == SCALE_SOURCE_FRAME and any(m.unit == "cm" for m in registry):
                # La procedencia del fallback de `px_to_cm`, en una frase. No puede ir
                # en el sextuplo —`$defs/metric` es `additionalProperties: false`— así
                # que va a `warnings[]`, como las razones de ADR-019. Y dice lo que la
                # caída tiene de particular: el divisor no es uno solo, es la altura de
                # cuerpo del cuadro del evento cero de CADA métrica, que no es el mismo
                # para todas.
                warnings.append(
                    f"Repetición {r['rep']}: la cadena de la estatura no se pudo medir en ningún cuadro "
                    "(faltan rodillas o tobillos en todos). Cada métrica en cm se dividió por la altura de "
                    "cuerpo del cuadro de su evento cero (`body_height_px`), que es la convención anterior con "
                    "su sesgo conocido y no es el mismo número para todas (CONTRATO.md §La escala)."
                )
        for m in registry:
            vals = [v for v in per_metric[m.id] if v is not None]
            summary_metrics[m.id] = {"median": round(float(np.median(vals)), 3) if vals else None, "n": len(vals), "mdc": m.mdc, "unit": m.unit, "level": m.level, "repeatability": repeatability_scalar(per_metric[m.id])}
        summary_metrics["hands_speed_curve_top_to_impact"] = {"median": None, "n": len(curves), "mdc": None, "unit": "bh/s", "level": 1, "repeatability": repeatability_curves(curves)}
        # ADR-019: dos avisos, y son dos cosas distintas a propósito. El primero
        # es la REGLA —ningún número de acá se compara contra nada— y sale de lo
        # que el archivo realmente dice, no de una constante: si alguna métrica
        # llegara con juicio habilitado, la frase sería falsa y no se escribe. El
        # segundo es el ESTADO de la tabla de MDC del deporte, que el registro
        # declara en `mdc_note` (el motor no sabe qué dice: invariante 13).
        # Se SUMAN a los avisos de fps de ADR-016, que siguen yendo primero.
        if any(v is not None for vs in per_metric.values() for v in vs):
            if not any(mv["judgment_allowed"] for r in reps for mv in r["metrics"].values()):
                warnings.append(
                    "Ninguno de estos números es un juicio: se muestran como descriptivos, con su banda, y no se "
                    "comparan contra ningún rango. Para que una métrica pueda juzgarse hay que validar su MDC sobre "
                    "material real —el mismo estimador, el mismo camino de captura, los eventos contra etiquetas "
                    "humanas, la deriva de cámara medida y la escala trazable— y tener un rango de referencia con "
                    "procedencia. Hasta entonces, comparar dos tomas es mirar, no medir (ADR-019)."
                )
            if registry.mdc_note and any(m.mdc_validation == "sin_validar" for m in registry):
                warnings.append(f"El MDC que viaja con cada número todavía no está validado en material real: {registry.mdc_note}.")
    warnings += event_notes
    # De qué clip salió el fps que se está usando (encargo 34). Es procedencia,
    # no un chequeo: no rechaza nada y no cambia ningún número. Va por
    # `warnings[]` y no por un `Check` porque en exploración el gate no corre
    # —`explore.py` escribe un `Check` con `passed=None`— y ésta es la frase que
    # llega a la pantalla en los dos modos. Sólo tiene sentido en un camino
    # calibrado: en uno declarado no hubo cronómetro, y de eso avisa ADR-016.
    #
    # Se calcula acá y se inserta ABAJO, junto al aviso de ADR-016: los dos
    # hablan del mismo eje del tiempo y van antes de cualquier número, con el de
    # ADR-016 primero porque es el más fuerte (ahí la tasa entera es un supuesto;
    # acá está medida y lo que falta es de qué clip salió).
    aviso_calibracion: str | None = None
    if capture.capture_path_calibrated:
        cal = capture.fps_calibration
        if cal.same_file is False:
            aviso_calibracion = (
                f"El fps de captura de esta toma ({fps:g} fps) NO lo midió este archivo: lo hereda del camino "
                f"'{capture.capture_path_id}', que se calibró con otro clip (sha256 {cal.clip_sha256[:12]}…). "
                f"Este archivo es sha256 {capture.sha256_original[:12]}…. Lo que el camino garantiza es el modo y la "
                "transferencia, no que esta toma haya salido de ahí; para medirlo en la toma va el cronómetro "
                "andando dentro del mismo cuadro que el gesto (CAPTURA.md §El método preferido)."
            )
        elif cal.same_file is None:
            # La frase dice lo que sabe la TOMA, no lo que dice el YAML de hoy:
            # un `capture.json` anterior al schema 1.3.0 tampoco trae el campo, y
            # afirmar «el camino no lo declara» sería falso si el camino lo
            # declara ahora. La salida es la misma en los dos casos: re-ingestar.
            aviso_calibracion = (
                f"Esta toma no registra con qué clip se calibró el camino '{capture.capture_path_id}': no se puede "
                f"saber si el fps de captura ({fps:g} fps) lo midió este archivo o algún otro. La tasa se usa igual; "
                "lo que falta es su procedencia. Se arregla declarando `calibration_clip_sha256` del camino en "
                "capture-paths.yaml y volviendo a ingestar la toma."
            )
    if aviso_calibracion:
        warnings.insert(0, aviso_calibracion)
    # Antes de cualquier número, por qué la tasa de cuadros no está verificada
    # (ADR-016). Son DOS casos distintos y el aviso no los puede mezclar:
    #
    # - camino DECLARADO: no hay cronómetro, así que la tasa de captura se
    #   asume igual a la de reproducción. El número es un supuesto.
    # - camino CALIBRADO sin gate (modo exploración): la tasa está **medida**
    #   con cronómetro filmado; lo que nadie verificó es que ESTE archivo haya
    #   venido por ese camino, porque eso lo hace el gate (`fps_matches_path`)
    #   y el gate no corrió. Decir "fps asumidos" de una tasa medida es falso:
    #   lo encontró el encargo 24 con el primer camino calibrado del proyecto.
    if capture.fps_provenance != "medido_aqui":
        if capture.capture_path_calibrated:
            warnings.insert(
                0,
                f"Tasa de cuadros sin verificar: el camino '{capture.capture_path_id}' está calibrado y su tasa de "
                f"captura está medida con cronómetro ({fps:g} fps), pero el gate no corrió: nadie verificó que este "
                "archivo haya venido por ese camino (ADR-016). Los tiempos y las duraciones son descriptivos; "
                "ninguna métrica puede ser juicio hasta que la toma pase el gate.",
            )
        else:
            warnings.insert(
                0,
                f"Tasa de cuadros sin verificar: {DECLARED_NOTE} ('{capture.capture_path_id}', {fps:g} fps asumidos). "
                "Los tiempos y las duraciones son descriptivos; ninguna métrica puede ser juicio hasta filmar el cronómetro.",
            )
    step = max(1, int(math.ceil(fps / SERIES_MAX_HZ)))
    if edits:
        warnings.append(f"{len(edits)} corrección(es) manual(es) aplicadas desde events-manual.json.")
    return {
        "header": {
            "schema_version": SCHEMA_VERSION,
            "engine_version": kinelab.__version__,
            "registry_version": registry.version,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "source": {"pose_sha256": sha256_file(take_dir / POSE_FILE), "master_sha256": None, "capture_path_id": capture.capture_path_id, "fps_real": fps, "fps_provenance": capture.fps_provenance},
            "sport": sport.id,
            "gesture": capture.gesture,
            "view": capture.view,
        },
        "quality": _quality(pose, len(reps), scales),
        "events": events_out,
        "reps": reps,
        "summary": {"rep_count": len(reps), "reps_rejected": {"count": int(sum(rejected.values())), "reasons": rejected}, "metrics": summary_metrics},
        "series": {"t": np.round(pose.timestamps_s[::step], 4), "hands_speed_bh_s": np.round(sig.speed[::step], 4), "params": {**sig.params, "segmentation": asdict(ev.segmentation), "events": asdict(ev.params), "series_hz": fps / step}},
        "warnings": warnings,
        "deviations": [],
    }


def analyze_take(take_dir: str | Path, sport: SportConfig, *, write: bool = True, height_m: float | None = None) -> dict:
    take_dir = Path(take_dir)
    cj = take_dir / "capture.json"
    if not cj.is_file():
        raise AnalysisError(f"{take_dir}: no hay capture.json.")
    capture = CaptureJson.model_validate_json(cj.read_text(encoding="utf-8"))
    if capture.gate.verdict != "ok":
        raise AnalysisError(f"{take_dir}: el gate rechazó esta toma: {' · '.join(capture.gate.reasons)}")
    if capture.fps_real is None:
        raise AnalysisError(f"{take_dir}: sin fps_real.")
    pose = load_pose(take_dir)
    if height_m is None:
        height_m = athlete_height_m(take_dir, capture.athlete)
    analysis = build_analysis(take_dir, capture, pose, sport, height_m=height_m)
    if write:
        write_analysis(take_dir, analysis)
    return analysis
