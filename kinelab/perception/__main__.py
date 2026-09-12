"""`python -m kinelab.perception TAKE_DIR [--deporte golf] [--det-frequency N] [--cpu] [--overwrite]`

Salida 0 si pasó los chequeos de la Fase 1, 2 si los rechazó, 1 si algo falló antes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from kinelab.perception.estimator import EstimatorConfig, PoseNaNError, PreprocessError
from kinelab.perception.models import ModelError
from kinelab.perception.run import PerceptionError, run_perception
from kinelab.perception.video import VideoError


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m kinelab.perception", description="Pose cruda de una toma ingestada → pose.npz + chequeos de Fase 1.")
    ap.add_argument("take_dir", type=Path)
    ap.add_argument("--deporte", default="golf")
    ap.add_argument("--det-frequency", type=int, default=None, help="correr el detector cada N cuadros (default 10)")
    ap.add_argument("--cpu", action="store_true", help="forzar CPUExecutionProvider")
    ap.add_argument("--overwrite", action="store_true", help="re-correr el modelo aunque ya haya pose.npz")
    args = ap.parse_args(argv)

    from sports import get_sport  # el motor no importa sports; el punto de entrada sí

    cfg = EstimatorConfig(providers=("CPUExecutionProvider",)) if args.cpu else EstimatorConfig()
    try:
        sport = get_sport(args.deporte)
        n = [0]

        def progress(i: int) -> None:
            n[0] = i
            if i % 200 == 0:
                print(f"  {i} cuadros…", file=sys.stderr)

        res = run_perception(args.take_dir, sport, cfg, overwrite=args.overwrite, det_frequency=args.det_frequency, progress_cb=progress)
    except (PerceptionError, ModelError, FileNotFoundError, PreprocessError, PoseNaNError, VideoError, KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    r = res.report
    print(f"{res.pose_path}")
    print(
        f"  {res.frames} cuadros · detección {r.detection_rate:.1%} · cuerpo {r.body_height_px_median:.0f} px "
        f"({r.frac_of_frame:.0%} del alto) · cámara {r.camera_motion_px if r.camera_motion_px is None else round(r.camera_motion_px, 2)} px"
    )
    for c in res.checks:
        st = "ok" if c.passed else ("sin evaluar" if c.passed is None else "FALLA")
        print(f"  {c.id:<18} {st:<12} {c.reason or ''}")
    if res.gate.verdict == "ok":
        print("  gate: OK")
        return 0
    print("  gate: RECHAZADO")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
