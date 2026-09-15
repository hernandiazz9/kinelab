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

from types import SimpleNamespace

from kinelab.analysis import swing_signals
from kinelab.events.primitives import peak_window, stillness_signal
from kinelab.events.signal import principal_axis
from kinelab.metrics.core import MetricContext, evaluate
from kinelab.metrics.generic import gain
from kinelab.perception.framing import body_height_px
from kinelab.perception.keypoints import H
from kinelab_truth.camera import Intrinsics, load_intrinsics, project, view_extrinsics
from kinelab_truth.swing import SwingParams, TruthSwing, gain_params, truth_swing


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
    # Ruido ABSOLUTO en píxeles de imagen. `None` = el modelo de ESPECIFICACION 3.1
    # (σ proporcional a la altura del cuerpo). Con σ fijo en px el error relativo crece
    # cuando el sujeto se achica, que es lo único que puede dar un umbral de encuadre:
    # con el modelo relativo el MDC no depende del tamaño (ver `framing_table`).
    noise_px: float | None = None

    def label(self) -> str:
        n = f"n{self.noise_frac:g}" if self.noise_px is None else f"npx{self.noise_px:g}"
        return f"{self.view} az{self.azimuth_deg:g} el{self.elevation_deg:g} d{self.distance_m:g} s{self.size_factor:g} {n} fps{self.fps:g}"

    def sigma_px(self, body_height_px: float) -> float:
        """σ del ruido gaussiano en píxeles para este tamaño de sujeto."""
        return float(self.noise_px) if self.noise_px is not None else self.noise_frac * float(body_height_px)


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


def project_condition(sw: TruthSwing, cond: Condition, intr: Intrinsics) -> tuple[np.ndarray, float, float]:
    """Proyección limpia (T,J,2) al fps de la condición, su fps y la altura de cuerpo en px.
    No depende de la semilla: se calcula una vez y se reusa para todas."""
    extr = view_extrinsics(cond.view, distance_m=cond.distance_m, height_m=cond.camera_height_m, azimuth_deg=cond.azimuth_deg, elevation_deg=cond.elevation_deg)
    px = project(sw.points_m, intr.scaled(cond.size_factor), extr)
    step = max(1, int(round(sw.fps / cond.fps)))
    px = px[::step]
    fps = sw.fps / step
    return px, fps, float(np.nanmedian(body_height_px(px, fps)))


def realize_seeds(sw: TruthSwing, cond: Condition, intr: Intrinsics, seeds: int):
    """Itera `seeds` realizaciones de la condición: (keypoints con ruido, scores,
    eventos verdaderos remuestreados con su jitter, fps, altura de cuerpo limpia)."""
    clean, fps, bh = project_condition(sw, cond, intr)
    step = max(1, int(round(sw.fps / cond.fps)))
    jit = cond.event_jitter_frames
    sigma = cond.sigma_px(bh)
    for seed in range(seeds):
        rng = np.random.default_rng(seed)
        events = {k: int(min(max(v // step + (rng.integers(-jit, jit + 1) if jit else 0), 0), clean.shape[0] - 1)) for k, v in sw.events.items()}
        px = clean + rng.normal(0.0, sigma, size=clean.shape) if sigma > 0 else clean
        yield px, np.full(px.shape[:2], 0.9, np.float32), events, fps, bh


def realize(sw: TruthSwing, cond: Condition, intr: Intrinsics, seed: int) -> tuple[np.ndarray, np.ndarray, dict[str, int], float]:
    """Keypoints 2-D (T,J,2) con ruido y al fps de la condición, eventos verdaderos remuestreados, fps."""
    for i, (px, sc, events, fps, _bh) in enumerate(realize_seeds(sw, cond, intr, seed + 1)):
        if i == seed:
            return px, sc, events, fps
    raise RuntimeError("semilla fuera de rango")


def evaluate_condition(sw: TruthSwing, cond: Condition, intr: Intrinsics, registry, joints: dict, seeds: int) -> dict[str, dict]:
    est: dict[str, list[float]] = {m.id: [] for m in registry}
    for px, sc, events, fps, _bh0 in realize_seeds(sw, cond, intr, seeds):
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


# ---------------------------------------------------------------------------
# Ganancia de velocidad angular (CONTRATO.md §summary.gain)
# ---------------------------------------------------------------------------

# Cocientes verdaderos con los que se arma el banco: el nominal y dos variantes.
GAIN_TARGETS: tuple[dict[str, float], ...] = (
    {"pelvis_to_torso": 1.5, "torso_to_arm": 1.5},
    {"pelvis_to_torso": 1.0, "torso_to_arm": 1.0},
    {"pelvis_to_torso": 2.0, "torso_to_arm": 2.0},
)


def _stats(err: np.ndarray, est: np.ndarray, truth: float) -> dict:
    """Sesgo, SD, límites de acuerdo, SEM y MDC de un juego de estimaciones."""
    if est.size == 0:
        return {"n": 0, "truth": truth, "bias": None, "sd": None, "loa_low": None, "loa_high": None, "sem": None, "mdc": None}
    sd = float(err.std(ddof=1)) if est.size > 1 else 0.0
    sem = float(est.std(ddof=1)) if est.size > 1 else 0.0
    return {
        "n": int(est.size), "truth": round(float(truth), 4), "mean": round(float(est.mean()), 4),
        "bias": round(float(err.mean()), 4), "sd": round(sd, 4),
        "loa_low": round(float(err.mean() - 1.96 * sd), 4), "loa_high": round(float(err.mean() + 1.96 * sd), 4),
        "sem": round(sem, 4), "mdc": round(1.96 * np.sqrt(2) * sem, 4),
    }


def evaluate_gain_condition(sw: TruthSwing, cond: Condition, intr: Intrinsics, segments: dict, truth_ratios: dict[str, float], seeds: int) -> dict:
    """Lo que el motor calcula como ganancia desde esta condición, contra la verdad 3-D."""
    est: dict[str, list[float]] = {k: [] for k in truth_ratios}
    peaks: dict[str, list[float]] = {k: [] for k in segments}
    for px, _sc, events, fps, _bh in realize_seeds(sw, cond, intr, seeds):
        g = gain(px, fps, segments, events["address"], events["follow_end"])
        for k in truth_ratios:
            v = g["ratios"].get(k)
            if v is not None and np.isfinite(v):
                est[k].append(float(v))
        for k, v in g["peaks_deg_s"].items():
            peaks[k].append(float(v))
    rows = {}
    for k, truth in truth_ratios.items():
        v = np.asarray(est[k], float)
        rows[k] = {"unit": "ratio", **_stats(v - truth, v, truth)}
    rows["_peaks_deg_s_median"] = {k: (round(float(np.median(v)), 1) if v else None) for k, v in peaks.items()}
    return rows


def gain_table(sw_factory, segments: dict, intr: Intrinsics, *, seeds: int, conditions: list[Condition] | None = None) -> dict:
    """Sesgo, límites de acuerdo y MDC de la ganancia por vista y condición, contra
    cocientes 3-D conocidos. El veredicto por vista usa la misma regla que las
    métricas: |sesgo| en la condición nominal contra `VALID_TOL['ratio']`, que es el
    ancho de rango declarado (procedencia `estimacion`)."""
    conds = conditions or sweep_conditions()
    tol = VALID_TOL["ratio"]
    rigs = []
    for targets in GAIN_TARGETS:
        params, achieved, sw = sw_factory(targets)
        truth_ratios = {k: float(achieved["ratios"][k]) for k in targets if k in achieved["ratios"]}
        results = [{"condition": asdict(c), "label": c.label(), "ratios": evaluate_gain_condition(sw, c, intr, segments, truth_ratios, seeds)} for c in conds]
        rigs.append({
            "targets": targets, "truth_ratios": truth_ratios,
            "truth_peaks_deg_s": achieved["peaks_deg_s"], "truth_peak_frames": achieved["peak_frames"],
            "params": {"pelvis_rot_top_deg": params.pelvis_rot_top_deg, "thorax_rot_top_deg": round(params.thorax_rot_top_deg, 3), "arm_arc_top_deg": round(params.arm_arc_top_deg, 3), "arm_arc_end_deg": round(params.arm_arc_end_deg, 3)},
            "results": results,
        })
    verdict: dict[str, dict] = {}
    for key in ("pelvis_to_torso", "torso_to_arm"):
        by_view: dict[str, dict] = {}
        for view in ("face_on", "down_the_line"):
            nominal_label = replace(NOMINAL, view=view).label()
            biases, mdcs = [], []
            for rig in rigs:
                row = next((r["ratios"].get(key) for r in rig["results"] if r["label"] == nominal_label), None)
                if row and row.get("bias") is not None:
                    biases.append(abs(row["bias"]))
                    mdcs.append(row["mdc"])
            worst = max(biases) if biases else None
            by_view[view] = {"abs_bias_max": None if worst is None else round(worst, 4), "mdc_max": (round(max(mdcs), 4) if mdcs else None), "passes": bool(worst is not None and worst <= tol)}
        views = [v for v, r in by_view.items() if r["passes"]]
        verdict[key] = {"unit": "ratio", "tolerance": tol, "by_view": by_view, "views": views,
                        "note": "" if views else "sin vista válida: la ganancia muere (ESPECIFICACION 3.3)"}
    return {"tolerance_ratio": tol, "segments": {k: list(v) for k, v in segments.items()}, "verdict": verdict, "rigs": rigs}


# ---------------------------------------------------------------------------
# Instante sub-cuadro del impacto (CONTRATO.md §subframe)
# ---------------------------------------------------------------------------

SUBFRAME_REF_FPS = 2400.0  # 10 × el nativo del banco: la verdad en tiempo continuo


def subframe_truth_s(sw_ref: TruthSwing, cond: Condition, intr: Intrinsics, axis_window_s: float) -> float | None:
    """El instante verdadero del cruce, en segundos, con la MISMA definición
    geométrica que el motor pero a `SUBFRAME_REF_FPS`: el centro de las muñecas
    proyectado sobre su dirección de viaje pasa por su valor de address."""
    clean, fps, _bh = project_condition(sw_ref, replace(cond, fps=sw_ref.fps), intr)
    hands = np.nanmean(np.stack([clean[:, H.LEFT_WRIST], clean[:, H.RIGHT_WRIST]], axis=1), axis=1)
    imp, addr = sw_ref.events["impact"], sw_ref.events["address"]
    k = max(1, int(round(axis_window_s * fps)))
    lo, hi = max(0, imp - k), min(hands.shape[0] - 1, imp + k)
    axis = principal_axis(hands, lo, hi)
    if float((hands[hi] - hands[lo]) @ axis) < 0:
        axis = -axis
    x = hands @ axis - float(hands[addr] @ axis)
    w = int(round(0.25 * fps))
    idx = np.arange(max(0, imp - w), min(x.size - 1, imp + w))
    cross = idx[((x[idx] <= 0) & (x[idx + 1] > 0)) | ((x[idx] >= 0) & (x[idx + 1] < 0))]
    if cross.size == 0:
        return None
    i = int(cross[np.argmin(np.abs(cross - imp))])
    return float((i + x[i] / (x[i] - x[i + 1])) / fps)


def evaluate_subframe_condition(sw: TruthSwing, cond: Condition, intr: Intrinsics, subframe_fn, event_params, truth_s: float | None, seeds: int) -> dict:
    """Sesgo y MDC del instante sub-cuadro en esta condición, en ms y en cuadros.

    El ancla es la del motor: `address` verdadero (durante la quietud la señal no se
    mueve, así que el nivel no depende de qué cuadro de la racha se tome) y el
    `impact` que da `peak_window`, la misma regla que usa el detector.
    """
    ts: list[float] = []
    bands: list[float] = []
    nulls: dict[str, int] = {}
    fps_out = cond.fps
    for px, _sc, events, fps, _bh in realize_seeds(sw, replace(cond, event_jitter_frames=0), intr, seeds):
        fps_out = fps
        sig = swing_signals(SimpleNamespace(keypoints=px.astype(np.float64)), fps, view=cond.view)
        still = stillness_signal(sig.speed, fps, event_params.still_smooth_s)
        thr = max(event_params.still_speed_max, event_params.noise_factor * float(sig.noise_floor_bh_s or 0.0))
        addr = events["address"]
        dist = np.hypot(*(sig.hands - sig.hands[addr]).T)
        imp = peak_window(dist, peak=events["impact"], radius=max(1, int(round(event_params.impact_search_s * fps))))
        out = subframe_fn(sig, addr, imp, still, thr, event_params)
        if out.get("t_sub_s") is None:
            reason = (out.get("null_reason") or "sin razón").split("(")[0].strip()
            nulls[reason] = nulls.get(reason, 0) + 1
            continue
        ts.append(float(out["t_sub_s"]))
        if out.get("uncertainty_frames") is not None:
            bands.append(float(out["uncertainty_frames"]))
    t = np.asarray(ts, float)
    row: dict = {"n": int(t.size), "n_null": int(seeds - t.size), "null_reasons": nulls, "fps": fps_out,
                 "truth_s": None if truth_s is None else round(truth_s, 6),
                 "declared_band_frames": (round(float(np.mean(bands)), 4) if bands else None)}
    if t.size == 0 or truth_s is None:
        row.update({"bias_ms": None, "sd_ms": None, "loa_low_ms": None, "loa_high_ms": None, "mdc_ms": None, "bias_frames": None, "mdc_frames": None})
        return row
    st = _stats((t - truth_s) * 1000.0, t * 1000.0, truth_s * 1000.0)
    row.update({"bias_ms": st["bias"], "sd_ms": st["sd"], "loa_low_ms": st["loa_low"], "loa_high_ms": st["loa_high"], "mdc_ms": st["mdc"],
                "bias_frames": round(st["bias"] * fps_out / 1000.0, 4), "mdc_frames": round(st["mdc"] * fps_out / 1000.0, 4)})
    return row


def subframe_conditions() -> list[Condition]:
    """fps × ruido en `face_on`, un barrido de tamaño, y una fila de `down_the_line`
    (que tiene que salir `null` por vista, invariante 6)."""
    out = [replace(NOMINAL, fps=f, noise_frac=n) for f in (240.0, 120.0, 60.0, 30.0) for n in (0.0, 0.003, 0.006, 0.012)]
    out += [replace(NOMINAL, fps=120.0, size_factor=s) for s in (0.5, 0.25, 0.11)]
    out.append(replace(NOMINAL, view="down_the_line"))
    return out


def subframe_table(sw: TruthSwing, intr: Intrinsics, *, subframe_fn, event_params, seeds: int, params: SwingParams) -> dict:
    sw_ref = truth_swing(params, fps=SUBFRAME_REF_FPS)
    conds = subframe_conditions()
    truth_by_view = {v: subframe_truth_s(sw_ref, replace(NOMINAL, view=v), intr, event_params.subframe_axis_s) for v in ("face_on", "down_the_line")}
    rows = [{"condition": asdict(c), "label": c.label(), **evaluate_subframe_condition(sw, c, intr, subframe_fn, event_params, truth_by_view.get(c.view), seeds)} for c in conds]
    ok = [r for r in rows if r["condition"]["view"] == "face_on" and r["mdc_ms"] is not None and r["condition"]["noise_frac"] == NOMINAL.noise_frac and r["condition"]["size_factor"] == 1.0]
    tol_bias, tol_mdc = VALID_TOL["ms"], MDC_TOL["ms"]
    good = [r for r in ok if abs(r["bias_ms"]) <= tol_bias and r["mdc_ms"] <= tol_mdc]
    return {
        "event": "impact", "field": "subframe", "unit": "ms",
        "reference_fps": SUBFRAME_REF_FPS,
        "truth_s": {k: (None if v is None else round(v, 6)) for k, v in truth_by_view.items()},
        "views": sorted({r["condition"]["view"] for r in rows if r["mdc_ms"] is not None}),
        "fps_min": (min(r["condition"]["fps"] for r in good) if good else None),
        "bias_ms": (round(float(np.mean([r["bias_ms"] for r in ok])), 4) if ok else None),
        "mdc_ms": (round(max(r["mdc_ms"] for r in ok), 4) if ok else None),
        "mdc_frames_by_fps": {str(int(r["condition"]["fps"])): r["mdc_frames"] for r in ok},
        "tolerance_ms": {"bias": tol_bias, "mdc": tol_mdc},
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Umbral de encuadre: a qué altura de cuerpo en px el MDC pasa la tolerancia
# ---------------------------------------------------------------------------

# Alturas de cuerpo en px del barrido (ESPECIFICACION 3.1 pide 100–900; se extiende
# hasta 1200 para cubrir los cuatro clips reales, de 973 a 1132 px).
FRAMING_BODY_PX: tuple[float, ...] = (100.0, 150.0, 200.0, 300.0, 400.0, 500.0, 600.0, 700.0, 800.0, 900.0, 1000.0, 1100.0, 1200.0)
# Clips reales medidos (informes del 04 y del 11): FHD 30 del 7/9 y los tres UHD 60.
REAL_CLIPS_BODY_PX: dict[str, dict] = {
    "s22_fhd30_20260907": {"body_px": 973.0, "clip": "20260907_170638.mp4", "mode": "Video FHD 30"},
    "s22_uhd60_vid2": {"body_px": 1083.0, "clip": "vid2.mp4", "mode": "Video UHD 60"},
    "s22_uhd60_vid1": {"body_px": 1104.0, "clip": "vid1.mp4", "mode": "Video UHD 60"},
    "s22_uhd60_vid3": {"body_px": 1132.0, "clip": "vid3.mp4", "mode": "Video UHD 60"},
}


def _crossing_px(pairs: list[tuple[float, float]], tol: float) -> float | None:
    """Altura de cuerpo (px) donde el MDC cruza `tol`, interpolando entre las dos
    alturas vecinas. `None` si nunca lo cruza dentro del barrido."""
    pts = sorted((bh, m) for bh, m in pairs if m is not None and np.isfinite(m))
    for (b0, m0), (b1, m1) in zip(pts, pts[1:]):
        if (m0 > tol) != (m1 > tol) and m0 != m1:
            return round(float(b0 + (b1 - b0) * (tol - m0) / (m1 - m0)), 1)
    return None


def framing_table(sw: TruthSwing, intr: Intrinsics, registry, joints: dict, summary: dict, *, subframe_fn=None, event_params=None, seeds: int, sigma_px: float, sigma_px_alt: float | None = None) -> dict:
    """Para cada métrica con MDC, el MDC en función de la altura del sujeto en px,
    y la altura donde cruza su tolerancia (`MDC_TOL`).

    Se corre con DOS modelos de ruido, porque sólo uno puede dar un umbral:
    `relativo` (σ = `noise_frac` · altura de cuerpo, el de ESPECIFICACION 3.1) deja
    el MDC **exactamente invariante** al tamaño —toda la cadena divide por la misma
    altura— y `absoluto` (σ fijo en px) lo hace crecer como 1/altura.
    """
    base = {v: project_condition(sw, replace(NOMINAL, view=v), intr)[2] for v in ("face_on", "down_the_line")}
    models: dict[str, dict] = {}
    for name, sigma in (("absoluto", sigma_px), ("absoluto_clips_reales", sigma_px_alt), ("relativo", None)):
        if name == "absoluto_clips_reales" and sigma is None:
            continue
        grid = FRAMING_BODY_PX if name != "relativo" else (100.0, 200.0, 400.0, 800.0)
        rows = []
        for view in ("face_on", "down_the_line"):
            for target in grid:
                cond = replace(NOMINAL, view=view, size_factor=target / base[view], noise_px=sigma)
                clean, fps, bh = project_condition(sw, cond, intr)
                met = evaluate_condition(sw, cond, intr, registry, joints, seeds)
                row = {"view": view, "target_body_px": target, "body_px": round(bh, 1), "sigma_px": round(cond.sigma_px(bh), 3), "metrics": {m.id: met[m.id]["mdc"] for m in registry}}
                if subframe_fn is not None and view == "face_on":
                    sb = evaluate_subframe_condition(sw, cond, intr, subframe_fn, event_params, subframe_truth_s(truth_swing(sw.params, fps=SUBFRAME_REF_FPS), cond, intr, event_params.subframe_axis_s), seeds)
                    row["impact_subframe_ms"] = sb["mdc_ms"]
                rows.append(row)
        per_metric: dict[str, dict] = {}
        for m in registry:
            views = summary.get(m.id, {}).get("views") or []
            if not views:
                continue
            tol = MDC_TOL.get(m.unit, 1.0)
            worst = [(r["body_px"], r["metrics"][m.id]) for r in rows if r["view"] in views]
            merged: dict[float, float] = {}
            for bh, v in worst:
                if v is not None:
                    merged[round(bh)] = max(merged.get(round(bh), 0.0), v)
            pairs = sorted(merged.items())
            per_metric[m.id] = {"unit": m.unit, "tolerance": tol, "views": views,
                                "mdc_by_body_px": {str(int(b)): round(v, 4) for b, v in pairs},
                                "crossing_body_px": _crossing_px([(float(b), v) for b, v in pairs], tol)}
        if subframe_fn is not None:
            pairs = [(r["body_px"], r.get("impact_subframe_ms")) for r in rows if r["view"] == "face_on"]
            per_metric["impact_subframe_ms"] = {"unit": "ms", "tolerance": MDC_TOL["ms"], "views": ["face_on"],
                                                "mdc_by_body_px": {str(int(b)): (None if v is None else round(v, 4)) for b, v in pairs},
                                                "crossing_body_px": _crossing_px(pairs, MDC_TOL["ms"])}
        crossings = [r["crossing_body_px"] for r in per_metric.values() if r["crossing_body_px"] is not None]
        models[name] = {"sigma_px": sigma, "rows": rows, "per_metric": per_metric,
                        "body_height_px_min_proposed": (max(crossings) if crossings else None),
                        "note": "" if crossings else "ninguna métrica cruza su tolerancia en el barrido: este modelo de ruido no puede fijar un umbral"}
    real = {}
    prop = models["absoluto"]["body_height_px_min_proposed"]
    for name, info in REAL_CLIPS_BODY_PX.items():
        real[name] = {**info, "passes_absoluto": (None if prop is None else bool(info["body_px"] >= prop))}
    return {"tolerances": MDC_TOL, "nominal_body_px": {k: round(v, 1) for k, v in base.items()}, "models": models, "real_clips": real,
            "warning": "PROPUESTA, no umbral. El gate NO lo lee: fijarlo es decisión del orquestador con CAPTURA.md (encargo 13)."}


def build_table(registry, joints: dict, *, candidate_views: dict[str, tuple[str, ...]] | None = None, camera: str = "iphone17pro-1080p120", params: SwingParams = SwingParams(), seeds: int = 16, conditions: list[Condition] | None = None, gain_segments: dict[str, tuple[int, int]] | None = None, subframe_fn=None, event_params=None, dead_metrics: dict[str, str] | None = None, extras: bool = True) -> dict:
    """`candidate_views`: las vistas que el deporte DECLARA por métrica; el arnés sólo puede
    quitar vistas (una métrica que colapsa desde una vista la pierde), nunca agregar.

    `gain_segments`, `subframe_fn` y `event_params` los pone el deporte (ver
    `__main__`): el arnés no conoce ninguno. Sin ellos, los bloques de ganancia y de
    sub-cuadro no se corren.

    `dead_metrics` son las que un barrido anterior ya mató: **no están en el
    registro**, así que el arnés no las puede volver a medir, pero su fila sigue en
    la tabla con su razón. Sin esto, cada corrida borraría la fila, y la fila
    ausente revive la métrica en el registro sin MDC en la corrida siguiente
    (`sports/<deporte>/metrics.py`, `_m`): la tabla oscilaría entre dos estados."""
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
    for mid, info in (dead_metrics or {}).items():
        d = info if isinstance(info, dict) else {"note": info}
        summary.setdefault(mid, {"unit": d.get("unit", ""), "views": [], "fps_min": None, "mdc": None, "mdc_by_view": {}, "note": d.get("note", "")})
    out = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "camera": asdict(intr), "swing_params": asdict(params), "seeds": seeds, "level": "0 (proyección + ruido; sin estimador)", "results": results, "summary": summary}
    if extras and gain_segments:
        def factory(targets: dict[str, float]):
            pr, achieved = gain_params(targets, gain_segments, base=params)
            return pr, achieved, truth_swing(pr, fps=240.0)

        out["gain"] = gain_table(factory, gain_segments, intr, seeds=seeds, conditions=conds)
    if extras and subframe_fn is not None and event_params is not None:
        out["subframe"] = subframe_table(sw, intr, subframe_fn=subframe_fn, event_params=event_params, seeds=seeds, params=params)
    if extras:
        # σ absoluto de referencia: el mismo ruido que el nominal relativo en el tamaño
        # nominal (0,6 % de ~811 px). El segundo, la mediana de lo MEDIDO en los clips
        # reales (`subframe.components.noise_px`: 1,2 · 2,3 · 3,0 px).
        nominal_bh = project_condition(sw, NOMINAL, intr)[2]
        out["framing"] = framing_table(sw, intr, registry, joints, summary, subframe_fn=subframe_fn, event_params=event_params, seeds=seeds,
                                       sigma_px=round(NOMINAL.noise_frac * nominal_bh, 3), sigma_px_alt=2.3)
    return out


def write_outputs(table: dict, reports_dir: Path, mdc_yaml: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = table["generated_at"][:10]
    (reports_dir / f"mdc-{stamp}.json").write_text(json.dumps(table, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["# Tabla de MDC por métrica — escrita por el arnés (truth/), NO a mano (ESPECIFICACION 3.3).", f"# generado: {table['generated_at']} · nivel {table['level']} · cámara {table['camera']['id']} ({table['camera']['provenance']}) · semillas {table['seeds']}", "# views: |sesgo| nominal bajo tolerancia; fps_min: menor fps con |sesgo| y MDC bajo tolerancia;", "# mdc: el peor entre nominal y azimut ≤ 30° en las vistas válidas. Ver truth/reports/.", "metrics:"]
    for mid, s in table["summary"].items():
        lines.append(f"  {mid}:")
        if s["unit"]:
            lines.append(f"    unit: {s['unit']}")
        lines.append(f"    views: [{', '.join(s['views'])}]")
        lines.append(f"    fps_min: {s['fps_min'] if s['fps_min'] is not None else 'null'}")
        lines.append(f"    mdc: {s['mdc'] if s['mdc'] is not None else 'null'}")
        if s["note"]:
            lines.append(f"    note: \"{s['note']}\"")
    if table.get("gain"):
        lines += _gain_yaml(table["gain"])
    if table.get("subframe"):
        lines += _subframe_yaml(table["subframe"])
    if table.get("framing"):
        lines += _framing_yaml(table["framing"])
    mdc_yaml.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _yaml_block(data: dict, indent: int) -> list[str]:
    """Vuelca un dict a YAML con sangría, sin inventar formato propio."""
    text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False).rstrip("\n")
    pad = " " * indent
    return [pad + line if line else line for line in text.split("\n")]


def _gain_yaml(g: dict) -> list[str]:
    lines = [
        "",
        "# Ganancia de velocidad angular pelvis→tórax→brazo (CONTRATO.md §summary.gain).",
        "# Verdad: los cocientes de los picos de velocidad angular 3-D de las MISMAS líneas,",
        "# con tres bancos de cocientes conocidos (1,5 · 1,0 · 2,0). Una vista vale si el",
        f"# |sesgo| en la condición nominal es ≤ {g['tolerance_ratio']} (ancho de rango declarado, procedencia estimacion).",
        "gain:",
    ]
    for key, v in g["verdict"].items():
        lines.append(f"  {key}:")
        lines.append(f"    unit: {v['unit']}")
        lines.append(f"    views: [{', '.join(v['views'])}]")
        lines.append(f"    tolerance: {v['tolerance']}")
        lines.append("    by_view:")
        for view, r in v["by_view"].items():
            lines.append(f"      {view}: {{abs_bias_max: {r['abs_bias_max']}, mdc_max: {r['mdc_max']}, passes: {str(r['passes']).lower()}}}")
        if v["note"]:
            lines.append(f"    note: \"{v['note']}\"")
    return lines


def _subframe_yaml(sb: dict) -> list[str]:
    lines = [
        "",
        "# Instante sub-cuadro del impacto (CONTRATO.md §subframe). NO es una métrica del",
        "# registro: es un campo del evento. La verdad es el mismo cruce geométrico calculado",
        f"# a {sb['reference_fps']:g} fps (tiempo continuo). Nadie lo lee todavía: para que viaje a",
        "# analysis.json hay que leerlo desde sports/<deporte>/events.py (ver el informe del 13).",
        "events:",
        f"  {sb['event']}:",
        f"    {sb['field']}:",
        f"      unit: {sb['unit']}",
        f"      views: [{', '.join(sb['views'])}]",
        f"      fps_min: {sb['fps_min'] if sb['fps_min'] is not None else 'null'}",
        f"      bias_ms: {sb['bias_ms']}",
        f"      mdc_ms: {sb['mdc_ms']}",
        "      mdc_frames_by_fps:",
    ]
    for fps, v in sorted(sb["mdc_frames_by_fps"].items(), key=lambda kv: -float(kv[0])):
        lines.append(f"        \"{fps}\": {v}")
    lines.append(f"      truth_s: {{{', '.join(f'{k}: {v}' for k, v in sb['truth_s'].items())}}}")
    return lines


def _framing_yaml(fr: dict) -> list[str]:
    lines = [
        "",
        "# Umbral de encuadre: a qué altura de cuerpo en px el MDC de cada métrica cruza su",
        f"# tolerancia ({', '.join(f'{k} {v:g}' for k, v in fr['tolerances'].items())}).",
        f"# {fr['warning']}",
        "framing:",
        f"  warning: \"{fr['warning']}\"",
    ]
    lines += _yaml_block({"nominal_body_px": fr["nominal_body_px"]}, 2)
    lines.append("  models:")
    for name, m in fr["models"].items():
        lines.append(f"    {name}:")
        lines += _yaml_block({"sigma_px": m["sigma_px"], "body_height_px_min_proposed": m["body_height_px_min_proposed"], "note": m["note"],
                              "crossing_body_px": {k: v["crossing_body_px"] for k, v in m["per_metric"].items()}}, 6)
    lines += _yaml_block({"real_clips": {k: v for k, v in fr["real_clips"].items()}}, 2)
    return lines
