"""La verdad sobre la tasa de cuadros de un clip.

El fps que declara el contenedor no distingue un clip cuyos timestamps fueron
estirados (240 cuadros por segundo real, reproducidos a 30) de uno realmente
remuestreado a 30. Medido con ffprobe 9: `r_frame_rate`, `avg_frame_rate` y
el histograma de deltas de PTS son idénticos en los dos casos. Lo único que
los separa es contar cuadros contra una duración REAL conocida — un cronómetro
filmado. Ver CAPTURA.md.

Por eso esta herramienta separa tres cosas que suelen confundirse:

- lo **declarado** por el contenedor (puede mentir),
- lo **medido** de los cuadros y sus PTS: cuántos hay y a qué tasa se
  reproducen,
- y, sólo si se pasa la duración real, la **tasa de captura** y el factor de
  estiramiento.

Uso:
    python -m kinelab.tools.fps_truth clip.mov
    python -m kinelab.tools.fps_truth clip.mov --duracion-real 10.00 --nominal 240
    python -m kinelab.tools.fps_truth clip.mov --json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path

# Por encima de esto, los deltas de PTS no son uniformes: tasa variable, o el
# bug de captura de los iPhone (240 nominales grabando 114–227 reales).
VFR_RATIO_MAX = 1.10
# Un factor de estiramiento dentro de ±5% de 1 es "el archivo reproduce a la
# tasa a la que se capturó".
STRETCH_TOL = 0.05
# Si la tasa de captura medida está por debajo de este porcentaje de la nominal
# y el archivo no está estirado, los cuadros se perdieron de verdad.
DESTROYED_RATIO = 0.90


class FfprobeError(RuntimeError):
    """ffprobe no está, falló, o el archivo no tiene un stream de video usable."""


def ffprobe_bin() -> str:
    return os.environ.get("KINELAB_FFPROBE") or shutil.which("ffprobe") or "ffprobe"


def _run(args: list[str]) -> str:
    try:
        out = subprocess.run(
            [ffprobe_bin(), "-v", "error", *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=900,
        )
    except FileNotFoundError as e:
        raise FfprobeError("ffprobe no está en el PATH (brew install ffmpeg)") from e
    except subprocess.CalledProcessError as e:
        raise FfprobeError(e.stderr.strip() or f"ffprobe falló con código {e.returncode}") from e
    return out.stdout


def _fraction(value: str | None) -> float:
    if not value or value in ("0/0", "N/A"):
        return 0.0
    try:
        return float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        return 0.0


@dataclass(frozen=True)
class Declared:
    """Lo que dice el contenedor. Puede mentir; se guarda para poder compararlo."""

    codec: str
    width: int
    height: int
    rotation_deg: int
    r_frame_rate: float
    avg_frame_rate: float
    nb_frames_declared: int | None
    duration_s: float | None
    time_base: str
    creation_time: str | None

    @property
    def display_size(self) -> tuple[int, int]:
        """Ancho y alto como se ven, con la rotación de metadatos aplicada."""
        if self.rotation_deg in (90, 270):
            return self.height, self.width
        return self.width, self.height


@dataclass(frozen=True)
class Counted:
    """Lo que hay de verdad: cuadros decodificados y sus timestamps."""

    frames_decoded: int
    pts_first_s: float
    pts_last_s: float
    delta_min_s: float
    delta_max_s: float
    delta_median_s: float
    zero_deltas: int
    vfr_ratio: float
    fps_playback: float

    @property
    def playback_span_s(self) -> float:
        return self.pts_last_s - self.pts_first_s


@dataclass(frozen=True)
class Truth:
    path: str
    declared: Declared
    counted: Counted
    real_duration_s: float | None
    nominal_fps: float | None
    fps_capture: float | None
    stretch_factor: float | None
    verdict: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["declared"]["display_size"] = list(self.declared.display_size)
        d["counted"]["playback_span_s"] = self.counted.playback_span_s
        return d


def probe_declared(path: str | Path) -> Declared:
    raw = _run(["-select_streams", "v:0", "-show_streams", "-show_format", "-of", "json", str(path)])
    data = json.loads(raw)
    streams = data.get("streams") or []
    if not streams:
        raise FfprobeError(f"{path}: no tiene stream de video")
    s = streams[0]
    fmt = data.get("format") or {}

    rotation = 0
    for side in s.get("side_data_list") or []:
        if "rotation" in side:
            try:
                rotation = int(round(float(side["rotation"]))) % 360
            except (TypeError, ValueError):
                pass
    tags = s.get("tags") or {}
    if rotation == 0 and tags.get("rotate"):
        try:
            rotation = int(float(tags["rotate"])) % 360
        except ValueError:
            pass

    duration = s.get("duration") or fmt.get("duration")
    nb = s.get("nb_frames")
    creation = (fmt.get("tags") or {}).get("creation_time") or tags.get("creation_time")
    return Declared(
        codec=s.get("codec_name", "?"),
        width=int(s.get("width") or 0),
        height=int(s.get("height") or 0),
        rotation_deg=rotation,
        r_frame_rate=_fraction(s.get("r_frame_rate")),
        avg_frame_rate=_fraction(s.get("avg_frame_rate")),
        nb_frames_declared=int(nb) if isinstance(nb, str) and nb.isdigit() else None,
        duration_s=float(duration) if duration else None,
        time_base=s.get("time_base", "?"),
        creation_time=creation,
    )


def count_frames(path: str | Path) -> Counted:
    """Decodifica el stream de video entero y mide los timestamps de cada cuadro.

    Decodificar es más lento que leer paquetes, pero es la única forma de saber
    cuántos cuadros hay de verdad. Un clip de 20 s a 120 fps tarda segundos;
    aceptable para la ingesta.
    """
    raw = _run(
        [
            "-select_streams", "v:0",
            "-show_entries", "frame=pts_time,best_effort_timestamp_time",
            "-of", "csv=p=0",
            str(path),
        ]
    )
    times: list[float] = []
    for line in raw.splitlines():
        for cell in line.split(","):
            cell = cell.strip()
            if cell and cell != "N/A":
                try:
                    times.append(float(cell))
                    break
                except ValueError:
                    continue
    n = len(times)
    if n < 2:
        raise FfprobeError(f"{path}: {n} cuadro(s) decodificado(s); no alcanza para medir")

    # El decodificador entrega en orden de presentación, pero ordenar no cuesta
    # nada y protege contra streams raros.
    times.sort()
    deltas = [b - a for a, b in zip(times, times[1:])]
    zero = sum(1 for d in deltas if d <= 0)
    positive = [d for d in deltas if d > 0]
    if not positive:
        raise FfprobeError(f"{path}: todos los cuadros tienen el mismo timestamp")
    dmin, dmax = min(positive), max(positive)
    span = times[-1] - times[0]
    return Counted(
        frames_decoded=n,
        pts_first_s=times[0],
        pts_last_s=times[-1],
        delta_min_s=dmin,
        delta_max_s=dmax,
        delta_median_s=statistics.median(positive),
        zero_deltas=zero,
        vfr_ratio=dmax / dmin,
        fps_playback=(n - 1) / span if span > 0 else 0.0,
    )


def analyze(
    path: str | Path,
    real_duration_s: float | None = None,
    nominal_fps: float | None = None,
) -> Truth:
    if real_duration_s is not None and real_duration_s <= 0:
        raise ValueError("la duración real tiene que ser positiva")
    declared = probe_declared(path)
    counted = count_frames(path)
    notes: list[str] = []

    fps_capture: float | None = None
    stretch: float | None = None
    if real_duration_s is not None:
        fps_capture = counted.frames_decoded / real_duration_s
        stretch = fps_capture / counted.fps_playback if counted.fps_playback > 0 else None

    if counted.vfr_ratio > VFR_RATIO_MAX:
        verdict = "vfr"
        notes.append(
            f"tasa variable: delta_max/delta_min = {counted.vfr_ratio:.2f} (> {VFR_RATIO_MAX}). "
            "Puede ser VFR real o el bug de captura del iPhone; el clip no sirve para medir tiempos."
        )
    elif real_duration_s is None:
        verdict = "sin_duracion_real"
        notes.append(
            "sin una duración real no se puede saber la tasa de captura: el contenedor sólo "
            f"dice la de reproducción ({counted.fps_playback:.2f} fps). Filmá un cronómetro."
        )
    elif stretch is not None and abs(stretch - 1.0) <= STRETCH_TOL:
        if nominal_fps and fps_capture is not None and fps_capture < DESTROYED_RATIO * nominal_fps:
            verdict = "destruido"
            notes.append(
                f"tasa de captura {fps_capture:.1f} fps frente a una nominal de {nominal_fps:g}: "
                "el clip fue remuestreado y los cuadros se perdieron. No se recuperan."
            )
        else:
            verdict = "cfr_a_tasa_de_captura"
    else:
        verdict = "estirado"
        notes.append(
            f"los cuadros están ({fps_capture:.1f} fps de captura) pero los timestamps los "
            f"reproducen a {counted.fps_playback:.2f} fps: factor de estiramiento {stretch:.2f}. "
            "Es un slow-motion horneado o un ready-to-play de Android; los datos se recuperan con el factor."
        )

    if counted.zero_deltas:
        notes.append(f"{counted.zero_deltas} cuadro(s) con timestamp repetido")
    if declared.r_frame_rate > 0 and abs(declared.r_frame_rate - counted.fps_playback) / declared.r_frame_rate > 0.02:
        notes.append(
            f"r_frame_rate declarado {declared.r_frame_rate:.3f} ≠ reproducción medida {counted.fps_playback:.3f}"
        )

    return Truth(
        path=str(path),
        declared=declared,
        counted=counted,
        real_duration_s=real_duration_s,
        nominal_fps=nominal_fps,
        fps_capture=fps_capture,
        stretch_factor=stretch,
        verdict=verdict,
        notes=tuple(notes),
    )


def format_human(t: Truth) -> str:
    d, c = t.declared, t.counted
    w, h = d.display_size
    lines = [
        t.path,
        f"  declarado:  {d.codec} {w}x{h} (rot {d.rotation_deg}°) · r_frame_rate {d.r_frame_rate:.3f} · "
        f"avg_frame_rate {d.avg_frame_rate:.3f} · duración {d.duration_s if d.duration_s is not None else '?'} s",
        f"  medido:     {c.frames_decoded} cuadros · reproducción {c.fps_playback:.3f} fps · "
        f"deltas {c.delta_min_s:.5f}–{c.delta_max_s:.5f} s (ratio {c.vfr_ratio:.3f})",
    ]
    if t.real_duration_s is not None:
        lines.append(
            f"  con duración real {t.real_duration_s:.3f} s: captura {t.fps_capture:.2f} fps · "
            f"factor de estiramiento {t.stretch_factor:.3f}"
        )
    lines.append(f"  veredicto:  {t.verdict.upper()}")
    for n in t.notes:
        lines.append(f"    · {n}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="kinelab-fps-truth",
        description="Cuenta cuadros y mide timestamps; el fps del contenedor no es de fiar.",
    )
    ap.add_argument("clip", type=Path)
    ap.add_argument(
        "--duracion-real", type=float, default=None,
        help="segundos reales entre dos lecturas del cronómetro filmado (o la duración real de la toma)",
    )
    ap.add_argument("--nominal", type=float, default=None, help="fps nominal del modo de grabación, para detectar remuestreo")
    ap.add_argument("--json", action="store_true", help="salida JSON en vez de texto")
    args = ap.parse_args(argv)

    if not args.clip.exists():
        print(f"no existe: {args.clip}", file=sys.stderr)
        return 2
    try:
        t = analyze(args.clip, args.duracion_real, args.nominal)
    except (FfprobeError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(json.dumps(t.to_dict(), indent=2, ensure_ascii=False) if args.json else format_human(t))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
