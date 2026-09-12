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
    ap.add_argument("--quick", action="store_true", help="sólo la condición nominal de cada vista")
    ap.add_argument("--deporte", default="golf")
    args = ap.parse_args(argv)
    from sports import get_sport

    sport = get_sport(args.deporte)
    conds = None
    if args.quick:
        from dataclasses import replace

        conds = [replace(NOMINAL, view=v) for v in ("face_on", "down_the_line")]
    import importlib

    declared = getattr(importlib.import_module(f"sports.{args.deporte}.metrics"), "DECLARED_VIEWS", None)
    table = build_table(sport.metrics.registry, sport.metrics.joints, candidate_views=declared, seeds=args.seeds, conditions=conds)
    write_outputs(table, REPO / "truth" / "reports", REPO / "sports" / args.deporte / "mdc.yaml")
    for mid, s in table["summary"].items():
        print(f"  {mid:<36} views={s['views']} fps_min={s['fps_min']} mdc={s['mdc']} {s['unit']}  {s['note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
