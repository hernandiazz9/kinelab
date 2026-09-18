"""CLI del motor, sin servidor (HERENCIA.md):

    python -m kinelab analyze TAKE_DIR [--deporte golf]
    python -m kinelab adjust TAKE_DIR --rep N --event top --frame F [--note ...]
    python -m kinelab datos VIDEO.mp4 --altura-m 1.75      # exploración: todo dibujado y en tablas, sin gate
    python -m kinelab datos VIDEO.mp4 --camino s22ultra-video-fhd30-cable   # declarando con qué se filmó
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from kinelab.analysis import AnalysisError, analyze_take
from kinelab.contract.validate import ContractError
from kinelab.events.manual import Edit, EventCollisionError, load_edits, save_edits
from kinelab.ingest.capture_paths import GENERIC_VIDEO_ID


def _print_summary(a: dict) -> None:
    q = a["quality"]
    print(f"  calidad: {q['verdict']}" + (f" · {' · '.join(q['reasons'])}" if q["reasons"] else ""))
    print(f"  repeticiones: {a['summary']['rep_count']} (descartadas {a['summary']['reps_rejected']['count']}: {a['summary']['reps_rejected']['reasons']})")
    for mid, m in list(a["summary"]["metrics"].items())[:6]:
        # La repetibilidad puede venir en `null` con su razón (ADR-019: sin piso
        # de ruido medido no es una medición). Se imprime la razón, no "SD None",
        # que se lee como si el número no hubiera salido por casualidad.
        rep = m["repeatability"]
        sd = f"SD {rep['value']}" if rep["value"] is not None else f"sin repetibilidad ({rep.get('null_reason') or 'sin razón declarada'})"
        print(f"    {mid}: mediana {m['median']} {m['unit']} · n {m['n']} · {sd} · MDC {m['mdc']}")
    for e in a["events"]:
        parts = [f"{k} {e[k]['frame']}{'*' if e[k]['manual'] else ''}" if e.get(k) else f"{k} —" for k in ("address", "top", "impact", "follow_end")]
        print(f"    rep {e['rep']}: " + " · ".join(parts))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m kinelab")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze", help="pose.npz → analysis.json")
    a.add_argument("take_dir", type=Path)
    a.add_argument("--deporte", default="golf")
    a.add_argument("--altura-m", type=float, default=None, help="altura del atleta en m (si no hay data/athletes/<slug>.yaml)")
    j = sub.add_parser("adjust", help="corregir un evento a mano y recalcular")
    j.add_argument("take_dir", type=Path)
    j.add_argument("--deporte", default="golf")
    j.add_argument("--rep", type=int, required=True)
    j.add_argument("--event", required=True)
    j.add_argument("--frame", type=int, required=True)
    j.add_argument("--note", default="")
    j.add_argument("--altura-m", type=float, default=None)
    x = sub.add_parser("datos", help="exploración: un video → overlay, fotos por evento, CSV por cuadro y JSON por evento")
    x.add_argument("video", type=Path)
    x.add_argument("--altura-m", type=float, default=None)
    x.add_argument("--vista", default="face_on")
    x.add_argument("--camino", default=GENERIC_VIDEO_ID, help=f"id del camino de captura en data/capture-paths.yaml (por defecto {GENERIC_VIDEO_ID}: 'no sé con qué se filmó')")
    x.add_argument("--out", type=Path, default=None, help="carpeta de salida (por defecto <video>.kinelab/)")
    x.add_argument("--cpu", action="store_true")
    x.add_argument("--deporte", default="golf")
    args = ap.parse_args(argv)

    from sports import get_sport

    if args.cmd == "datos":
        from kinelab.explore import explore

        try:
            out = args.out or args.video.with_name(args.video.stem + ".kinelab")
            r = explore(args.video, out, get_sport(args.deporte), height_m=args.altura_m, view=args.vista, camino=args.camino, cpu=args.cpu, progress=lambda i: print(f"  {i} cuadros…", file=sys.stderr) if i % 200 == 0 else None)
        except Exception as e:  # noqa: BLE001 — modo exploración: el error se muestra entero
            print(f"error: {e}", file=sys.stderr)
            return 1
        print(f"{out}")
        print(f"  camino {r['camino']} · fps {r['fps_provenance']}" + (" (declarado, sin cronómetro)" if r["camino_calibrado"] is False else ""))
        print(f"  {r['cuadros']} cuadros a {r['fps_archivo']:g} fps · eventos {r['eventos_t_s']} · duraciones {r['duraciones']}")
        print(f"  picos {r['picos']}")
        if r["gate_diria"]:
            print("  el gate diría: " + " · ".join(r["gate_diria"]))
        for f in r["archivos"]:
            print(f"  {f}")
        return 0

    try:
        sport = get_sport(args.deporte)
        if args.cmd == "adjust":
            edits = load_edits(args.take_dir)
            edits.append(Edit(rep=args.rep, event=args.event, frame=args.frame, edited_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), note=args.note))
            analysis = analyze_take(args.take_dir, sport, write=False)  # valida la colisión antes de guardar
            from kinelab.events.manual import apply_edits

            apply_edits(analysis["events"], edits[-1:], fps=analysis["header"]["source"]["fps_real"], order=tuple(sport.events.order))
            save_edits(args.take_dir, edits)
        analysis = analyze_take(args.take_dir, sport, height_m=args.altura_m)
    except (AnalysisError, ContractError, EventCollisionError, FileNotFoundError, KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"{args.take_dir / 'analysis.json'}")
    _print_summary(analysis)
    return 0 if analysis["quality"]["verdict"] != "no_usar" else 2


if __name__ == "__main__":
    raise SystemExit(main())
