"""`python -m kinelab_truth [--seeds N] [--quick]`: corre los barridos y escribe
truth/reports/mdc-<fecha>.json y sports/golf/mdc.yaml."""

from __future__ import annotations

import argparse
from pathlib import Path

from kinelab_truth.harness import NOMINAL, build_table, sweep_conditions, write_outputs

REPO = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m kinelab_truth")
    ap.add_argument("--seeds", type=int, default=16)
    ap.add_argument("--quick", action="store_true", help="sólo la condición nominal de cada vista, sin los barridos de ganancia, sub-cuadro y encuadre")
    ap.add_argument("--deporte", default="golf")
    args = ap.parse_args(argv)
    from sports import get_sport

    sport = get_sport(args.deporte)
    conds = None
    if args.quick:
        from dataclasses import replace

        conds = [replace(NOMINAL, view=v) for v in ("face_on", "down_the_line")]
    import importlib

    metrics_mod = importlib.import_module(f"sports.{args.deporte}.metrics")
    declared = getattr(metrics_mod, "DECLARED_VIEWS", None)
    # Las que un barrido anterior mató ya no están en el registro: sin esto su fila
    # desaparecería de la tabla y volverían a la vida sin MDC en la corrida siguiente.
    dead = dict(getattr(metrics_mod, "DEAD_METRICS", {}) or {})
    # Lo específico del deporte se inyecta acá: el arnés no importa ningún deporte
    # (ADR-001). Los segmentos de la ganancia vienen del `SportMetrics`; el estimador
    # del instante sub-cuadro, del módulo de eventos del deporte, si lo define.
    ev_mod = importlib.import_module(f"sports.{args.deporte}.events")
    subframe_fn = getattr(ev_mod, "_impact_subframe", None)
    table = build_table(
        sport.metrics.registry,
        sport.metrics.joints,
        candidate_views=declared,
        seeds=args.seeds,
        conditions=conds,
        gain_segments=sport.metrics.gain_segments,
        subframe_fn=subframe_fn,
        event_params=sport.events.params,
        dead_metrics=dead,
        extras=not args.quick,
    )
    write_outputs(table, REPO / "truth" / "reports", REPO / "sports" / args.deporte / "mdc.yaml")
    for mid, s in table["summary"].items():
        print(f"  {mid:<36} views={s['views']} fps_min={s['fps_min']} mdc={s['mdc']} {s['unit']}  {s['note']}")
    for key, v in (table.get("gain") or {}).get("verdict", {}).items():
        print(f"  gain.{key:<31} views={v['views']} tol={v['tolerance']} {v['note']}")
        for view, r in v["by_view"].items():
            print(f"      {view:<16} |sesgo| max {r['abs_bias_max']}  MDC max {r['mdc_max']}")
    sub = table.get("subframe")
    if sub:
        print(f"  impact.subframe                      views={sub['views']} fps_min={sub['fps_min']} sesgo={sub['bias_ms']} ms MDC={sub['mdc_ms']} ms")
    fr = table.get("framing")
    if fr:
        for name, m in fr["models"].items():
            print(f"  encuadre[{name}] σ={m['sigma_px']} px → body_height_px_min propuesto: {m['body_height_px_min_proposed']} {m['note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
