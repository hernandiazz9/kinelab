"""Barridos y tabla sesgo / límites de acuerdo / MDC por métrica y condición.

Para cada condición: se proyecta el swing verdadero, se agrega ruido gaussiano
(σ proporcional a la altura del cuerpo en px), se submuestrea al fps de la
condición, y se evalúan las métricas del deporte con los eventos VERDADEROS
(el error de eventos se mide aparte, contra GolfDB). Con S semillas por
condición: sesgo = media(estimado − verdad), SD, límites de acuerdo
= sesgo ± 1,96·SD, SEM = SD del estimado, MDC = 1,96·√2·SEM.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np
import yaml

from kinelab.metrics.core import MetricContext, evaluate
from kinelab.perception.framing import body_height_px
from kinelab_truth.camera import Intrinsics, load_intrinsics, project, view_extrinsics
from kinelab_truth.swing import SwingParams, TruthSwing, truth_swing


@dataclass(frozen=True)
class Condition:
    view: str = "face_on"
    azimuth_deg: float = 0.0
    elevation_deg: float = 0.0
    distance_m: float = 3.0  # con fx≈1450 y 1,80 m de estatura, ~870 px de cuerpo (el protocolo pide 80–90 % de 1080)
    size_factor: float = 1.0  # multiplica la focal: sujeto más chico/grande en px a la misma distancia
    noise_frac: float = 0.006  # σ del ruido / altura del cuerpo en px (estimación: ~5 px en 900)
    fps: float = 240.0
    camera_height_m: float = 1.0
    event_jitter_frames: int = 1  # tolerancia ±1 cuadro de los eventos (invariante 8): se sortea por semilla

    def label(self) -> str:
        return f"{self.view} az{self.azimuth_deg:g} el{self.elevation_deg:g} d{self.distance_m:g} s{self.size_factor:g} n{self.noise_frac:g} fps{self.fps:g}"


NOMINAL = Condition()


def sweep_conditions() -> list[Condition]:
    """Nominal + un factor por vez, en las dos vistas (ESPECIFICACION 3.1)."""
    out: list[Condition] = []
    for view in ("face_on", "down_the_line"):
        base = replace(NOMINAL, view=view)
        out.append(base)
        out += [replace(base, azimuth_deg=a) for a in (15, 30, 45, 60, 90)]
        out += [replace(base, elevation_deg=e) for e in (15, 30, 45)]
        out += [replace(base, distance_m=d) for d in (2.0, 4.0, 6.0, 8.0)]
        out += [replace(base, size_factor=s) for s in (0.5, 0.25, 0.11)]
        out += [replace(base, noise_frac=n) for n in (0.0, 0.003, 0.012)]
        out += [replace(base, fps=f) for f in (120.0, 60.0, 30.0)]
    return out


def realize(sw: TruthSwing, cond: Condition, intr: Intrinsics, seed: int) -> tuple[np.ndarray, np.ndarray, dict[str, int], float]:
    """Keypoints 2-D (T,J,2) con ruido y al fps de la condición, eventos verdaderos remuestreados, fps."""
    extr = view_extrinsics(cond.view, distance_m=cond.distance_m, height_m=cond.camera_height_m, azimuth_deg=cond.azimuth_deg, elevation_deg=cond.elevation_deg)
    px = project(sw.points_m, intr.scaled(cond.size_factor), extr)
    step = max(1, int(round(sw.fps / cond.fps)))
    px = px[::step]
    fps = sw.fps / step
    rng = np.random.default_rng(seed)
    jit = cond.event_jitter_frames
    events = {k: int(min(max(v // step + (rng.integers(-jit, jit + 1) if jit else 0), 0), px.shape[0] - 1)) for k, v in sw.events.items()}
    bh = float(np.nanmedian(body_height_px(px, fps)))
    if cond.noise_frac > 0:
        px = px + rng.normal(0.0, cond.noise_frac * bh, size=px.shape)
    return px, np.full(px.shape[:2], 0.9, np.float32), events, fps


def evaluate_condition(sw: TruthSwing, cond: Condition, intr: Intrinsics, registry, joints: dict, seeds: int) -> dict[str, dict]:
    est: dict[str, list[float]] = {m.id: [] for m in registry}
    for s in range(seeds):
        px, sc, events, fps = realize(sw, cond, intr, s)
        bh = body_height_px(px, fps)
        ctx = MetricContext(keypoints=px, scores=sc, fps=fps, view=cond.view, body_height_px=bh, events=events, frame_start=events["address"], frame_end=events["follow_end"], athlete_height_m=sw.params.height_m)
        for m in registry:
            out = evaluate(replace(m, views=(cond.view,), fps_min=1.0), ctx, joints=joints.get(m.id, ()))
            if out["value"] is not None:
                est[m.id].append(float(out["value"]))
    rows: dict[str, dict] = {}
    for m in registry:
        v = np.asarray(est[m.id], float)
        truth = sw.truth.get(m.id)
        if v.size == 0 or truth is None:
            rows[m.id] = {"n": int(v.size), "truth": truth, "bias": None, "sd": None, "loa_low": None, "loa_high": None, "sem": None, "mdc": None}
            continue
        err = v - truth
        sd = float(err.std(ddof=1)) if v.size > 1 else 0.0
        sem = float(v.std(ddof=1)) if v.size > 1 else 0.0
        rows[m.id] = {"n": int(v.size), "truth": round(float(truth), 3), "bias": round(float(err.mean()), 3), "sd": round(sd, 3), "loa_low": round(float(err.mean() - 1.96 * sd), 3), "loa_high": round(float(err.mean() + 1.96 * sd), 3), "sem": round(sem, 3), "mdc": round(1.96 * np.sqrt(2) * sem, 3), "unit": m.unit}
    return rows


# Una vista es válida si el SESGO (error sistemático, geométrico) cae bajo esta tolerancia por
# unidad (estimación). El MDC es ruido: se reporta, no descalifica. fps_min: el menor fps con
# sesgo bajo tolerancia y MDC ≤ 1,5 × el de 240 fps.
VALID_TOL = {"cm": 2.0, "ms": 25.0, "deg": 5.0, "ratio": 0.3}
# fps_min: el menor fps con |sesgo| ≤ VALID_TOL y MDC ≤ MDC_TOL (absoluto por unidad; el MDC de una
# duración crece 1/fps por la cuantización, y eso es exactamente lo que fija el fps mínimo).
MDC_TOL = {"cm": 5.0, "ms": 30.0, "deg": 15.0, "ratio": 0.3}  # ms: ±1 cuadro uniforme en dos eventos da ~27 ms a 120 fps (jitter pesimista)


def build_table(registry, joints: dict, *, candidate_views: dict[str, tuple[str, ...]] | None = None, camera: str = "iphone17pro-1080p120", params: SwingParams = SwingParams(), seeds: int = 16, conditions: list[Condition] | None = None) -> dict:
    """`candidate_views`: las vistas que el deporte DECLARA por métrica; el arnés sólo puede
    quitar vistas (una métrica que colapsa desde una vista la pierde), nunca agregar."""
    intr = load_intrinsics(camera)
    sw = truth_swing(params, fps=240.0)
    conds = conditions or sweep_conditions()
    results = [{"condition": asdict(c), "label": c.label(), "metrics": evaluate_condition(sw, c, intr, registry, joints, seeds)} for c in conds]
    summary: dict[str, dict] = {}
    for m in registry:
        tol = VALID_TOL.get(m.unit, 1.0)
        views: list[str] = []
        mdc_by_view: dict[str, float] = {}
        fps_min: float | None = None
        allowed = tuple((candidate_views or {}).get(m.id, ("face_on", "down_the_line")))
        for view in allowed:
            nominal = next((r for r in results if r["condition"]["view"] == view and r["label"] == replace(NOMINAL, view=view).label()), None)
            row = nominal["metrics"].get(m.id) if nominal else None
            if row and row["mdc"] is not None and abs(row["bias"]) <= tol:
                views.append(view)
                # MDC conservador: el peor entre nominal y azimut ≤ 30° en esa vista
                cands = [r["metrics"][m.id]["mdc"] for r in results if r["condition"]["view"] == view and r["condition"]["azimuth_deg"] <= 30 and r["condition"]["elevation_deg"] == 0 and r["condition"]["distance_m"] == NOMINAL.distance_m and r["condition"]["size_factor"] == 1.0 and r["condition"]["noise_frac"] == NOMINAL.noise_frac and r["condition"]["fps"] == NOMINAL.fps and r["metrics"][m.id]["mdc"] is not None]
                mdc_by_view[view] = max(cands) if cands else row["mdc"]
        if views:
            ref_view = views[0]
            fps_rows = [(r["condition"]["fps"], r["metrics"][m.id]) for r in results if r["condition"]["view"] == ref_view and r["condition"]["azimuth_deg"] == 0 and r["condition"]["elevation_deg"] == 0 and r["condition"]["distance_m"] == NOMINAL.distance_m and r["condition"]["size_factor"] == 1.0 and r["condition"]["noise_frac"] == NOMINAL.noise_frac]
            mdc_tol = MDC_TOL.get(m.unit, 1.0)
            ok_fps = [f for f, row in fps_rows if row["mdc"] is not None and abs(row["bias"]) <= tol and row["mdc"] <= mdc_tol]
            fps_min = min(ok_fps) if ok_fps else None
        summary[m.id] = {"unit": m.unit, "views": views, "fps_min": fps_min, "mdc": (round(max(mdc_by_view.values()), 3) if mdc_by_view else None), "mdc_by_view": mdc_by_view, "note": "sin vista válida: la métrica muere (ESPECIFICACION 3.3)" if not views else ""}
    return {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "camera": asdict(intr), "swing_params": asdict(params), "seeds": seeds, "level": "0 (proyección + ruido; sin estimador)", "results": results, "summary": summary}


def write_outputs(table: dict, reports_dir: Path, mdc_yaml: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = table["generated_at"][:10]
    (reports_dir / f"mdc-{stamp}.json").write_text(json.dumps(table, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["# Tabla de MDC por métrica — escrita por el arnés (truth/), NO a mano (ESPECIFICACION 3.3).", f"# generado: {table['generated_at']} · nivel {table['level']} · cámara {table['camera']['id']} ({table['camera']['provenance']}) · semillas {table['seeds']}", "# views: |sesgo| nominal bajo tolerancia; fps_min: menor fps con |sesgo| y MDC bajo tolerancia;", "# mdc: el peor entre nominal y azimut ≤ 30° en las vistas válidas. Ver truth/reports/.", "metrics:"]
    for mid, s in table["summary"].items():
        lines.append(f"  {mid}:")
        lines.append(f"    unit: {s['unit']}")
        lines.append(f"    views: [{', '.join(s['views'])}]")
        lines.append(f"    fps_min: {s['fps_min'] if s['fps_min'] is not None else 'null'}")
        lines.append(f"    mdc: {s['mdc'] if s['mdc'] is not None else 'null'}")
        if s["note"]:
            lines.append(f"    note: \"{s['note']}\"")
    mdc_yaml.write_text("\n".join(lines) + "\n", encoding="utf-8")
