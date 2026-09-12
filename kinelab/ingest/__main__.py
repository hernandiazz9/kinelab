"""Ingestar un clip: gate + copia a la sesión + `capture.json`.

    python -m kinelab.ingest CLIP --atleta hernan --gesto driver --vista face_on \
        --camino iphone17pro-video-1080p120-airdrop [--fecha 2026-09-14] [--data data]

Un rechazo no borra nada: la sesión queda en disco con su `capture.json` y
sus razones, para corregir y volver a ingestar. Código de salida 0 si pasó,
2 si fue rechazado, 1 si algo falló antes de llegar al gate.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from kinelab.ingest.capture_paths import CapturePaths, load_capture_paths
from kinelab.ingest.gate import CaptureJson, build_capture_json, run_gate
from kinelab.ingest.session import (
    copy_original,
    recording_date,
    reserve_take,
    session_root,
    sha256_file,
    validate_slug,
)
from kinelab.sport import SportConfig
from kinelab.tools.fps_truth import FfprobeError, analyze


def ingest_clip(
    src: Path,
    *,
    athlete: str,
    gesture: str,
    view: str,
    capture_path_id: str,
    capture_paths: CapturePaths,
    sport: SportConfig,
    data_dir: Path,
    day: date | None = None,
) -> tuple[Path, CaptureJson]:
    """Corre el gate y deja la sesión en disco. Devuelve la carpeta de la toma y
    su `capture.json`, pase o no el gate."""
    validate_slug(athlete, "atleta")
    validate_slug(gesture, "gesto")
    validate_slug(view, "vista")
    if not src.is_file():
        raise FileNotFoundError(src)

    truth = analyze(src)
    gate = run_gate(
        truth,
        capture_path_id=capture_path_id,
        capture_paths=capture_paths,
        sport=sport,
        gesture=gesture,
        view=view,
    )
    take_dir = reserve_take(
        session_root(data_dir, athlete, recording_date(truth.declared.creation_time, src, day), gesture, view)
    )
    original = copy_original(src, take_dir)
    capture = build_capture_json(
        truth,
        gate,
        athlete=athlete,
        gesture=gesture,
        view=view,
        capture_path_id=capture_path_id,
        capture_paths=capture_paths,
        sha256_original=sha256_file(original),
        original_name=src.name,
    )
    # Escritura atómica: nunca queda un capture.json a medias.
    tmp = take_dir / "capture.json.tmp"
    tmp.write_text(capture.model_dump_json(indent=2), encoding="utf-8")
    tmp.replace(take_dir / "capture.json")
    return take_dir, capture


def _resolve_sport(sport_id: str) -> SportConfig:
    # El motor no importa `sports`; el punto de entrada sí (CONTEXTO.md, inv. 13).
    from sports import get_sport

    return get_sport(sport_id)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="kinelab-ingest", description="Gate de ingesta y armado de la sesión.")
    ap.add_argument("clip", type=Path)
    ap.add_argument("--atleta", required=True)
    ap.add_argument("--gesto", required=True)
    ap.add_argument("--vista", required=True)
    ap.add_argument("--camino", required=True, help="id del camino de captura en capture-paths.yaml")
    ap.add_argument("--deporte", default="golf")
    ap.add_argument("--fecha", type=date.fromisoformat, default=None, help="YYYY-MM-DD; si no, la del archivo")
    ap.add_argument("--data", type=Path, default=Path("data"))
    args = ap.parse_args(argv)

    try:
        capture_paths = load_capture_paths(args.data / "capture-paths.yaml")
        sport = _resolve_sport(args.deporte)
        take_dir, capture = ingest_clip(
            args.clip,
            athlete=args.atleta,
            gesture=args.gesto,
            view=args.vista,
            capture_path_id=args.camino,
            capture_paths=capture_paths,
            sport=sport,
            data_dir=args.data,
            day=args.fecha,
        )
    except (FfprobeError, FileNotFoundError, ValueError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(f"{take_dir}")
    print(
        f"  {capture.codec} {capture.width}x{capture.height} · {capture.frames_decoded} cuadros · "
        f"reproducción {capture.fps_playback:g} fps · captura {capture.fps_real if capture.fps_real is not None else '?'} fps · "
        f"{capture.duration_s:g} s reales"
    )
    if capture.gate.verdict == "ok":
        print("  gate: OK")
        return 0
    print("  gate: RECHAZADO")
    for r in capture.gate.reasons:
        print(f"    · {r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
