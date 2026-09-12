"""Error de detección de eventos contra anotaciones (ESPECIFICACION 2.5).

GolfDB es CC BY-NC 4.0: sólo para MEDIR el error propio, nunca para entrenar
(ADR-010). Entrada: dos JSON `{clip_id: {evento: cuadro}}`, verdad y detección.
Por evento: n, sesgo (media detección − verdad), SD, límites de acuerdo de
Bland-Altman (sesgo ± 1,96·SD) y fracción dentro de ±1 y ±2 cuadros.
El cargador del `golfDB.pkl` original queda pendiente de tener el dataset.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def event_error_stats(truth: dict[str, dict[str, int]], pred: dict[str, dict[str, int]]) -> dict[str, dict]:
    diffs: dict[str, list[float]] = {}
    for clip, events in truth.items():
        p = pred.get(clip) or {}
        for name, frame in events.items():
            if p.get(name) is not None:
                diffs.setdefault(name, []).append(float(p[name] - frame))
    out: dict[str, dict] = {}
    for name, d in diffs.items():
        a = np.asarray(d)
        bias, sd = float(a.mean()), float(a.std(ddof=1)) if a.size > 1 else 0.0
        out[name] = {"n": int(a.size), "bias_frames": round(bias, 3), "sd_frames": round(sd, 3), "loa_low": round(bias - 1.96 * sd, 3), "loa_high": round(bias + 1.96 * sd, 3), "within_1": float(np.mean(np.abs(a) <= 1)), "within_2": float(np.mean(np.abs(a) <= 2))}
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m kinelab.tools.golfdb_eval")
    ap.add_argument("--truth", type=Path, required=True)
    ap.add_argument("--pred", type=Path, required=True)
    args = ap.parse_args(argv)
    stats = event_error_stats(json.loads(args.truth.read_text()), json.loads(args.pred.read_text()))
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
