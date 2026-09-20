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

Aparte de eso, el **primer delta de PTS no es tasa variable**: la cámara tarda
en entregar el segundo cuadro. Medido en el original del Galaxy S22 Ultra
(265 cuadros): 263 deltas de 0,0333 s y uno de 0,2015 s, el primero. Contado
entero, el clip se declaraba VFR (ratio 6,04) y reproducía a 29,436 fps en vez
de 30,000 — todos los tiempos 1,9 % largos. Por eso `Counted` lleva los dos
juegos de números, el bruto y el `_excl_first`, y el veredicto usa el segundo
sólo cuando el primer delta es el único fuera de lugar.

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

from kinelab.ingest.session import sha256_file

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
    rotation_deg: int  # sentido horario, 0/90/180/270; iPhone en vertical = 90
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
    """Lo que hay de verdad: cuadros decodificados y sus timestamps.

    Los campos `vfr_ratio` y `fps_playback` son los BRUTOS, sobre todos los
    deltas, y no cambian de significado. Los `_excl_first` son los mismos
    números calculados sin el primer delta, porque el arranque de la cámara no
    es tasa variable: medido en un Galaxy S22 Ultra (`20260907_170638.mp4`,
    265 cuadros), 263 deltas de 0,0333 s y UNO de 0,2015 s, el primero. Con
    ese delta adentro el ratio da 6,04 y la reproducción 29,436 fps; sin él,
    1,00 y 30,000 fps. Acá se reportan los dos; el gate y el motor usan los
    `_effective` y guardan los brutos al lado (CAPTURA.md §El gate de ingesta).
    """

    frames_decoded: int
    pts_first_s: float
    pts_last_s: float
    delta_first_s: float
    delta_min_s: float
    delta_max_s: float
    delta_median_s: float
    zero_deltas: int
    vfr_ratio: float
    fps_playback: float
    vfr_ratio_excl_first: float
    fps_playback_excl_first: float

    @property
    def playback_span_s(self) -> float:
        return self.pts_last_s - self.pts_first_s

    @property
    def first_delta_is_the_only_outlier(self) -> bool:
        """El clip sería CFR si no fuera por el primer delta."""
        return self.vfr_ratio > VFR_RATIO_MAX and self.vfr_ratio_excl_first <= VFR_RATIO_MAX

    @property
    def vfr_ratio_effective(self) -> float:
        """El ratio con el que se juzga: sin el primer delta sólo si ése es el
        único anómalo. En un clip realmente VFR es el bruto, sin perdón."""
        return self.vfr_ratio_excl_first if self.first_delta_is_the_only_outlier else self.vfr_ratio

    @property
    def fps_playback_effective(self) -> float:
        """La tasa a la que el clip reproduce de verdad, con el mismo criterio."""
        return self.fps_playback_excl_first if self.first_delta_is_the_only_outlier else self.fps_playback


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
        d["counted"]["first_delta_is_the_only_outlier"] = self.counted.first_delta_is_the_only_outlier
        d["counted"]["vfr_ratio_effective"] = self.counted.vfr_ratio_effective
        d["counted"]["fps_playback_effective"] = self.counted.fps_playback_effective
        return d


def probe_declared(path: str | Path) -> Declared:
    raw = _run(["-select_streams", "v:0", "-show_streams", "-show_format", "-of", "json", str(path)])
    data = json.loads(raw)
    streams = data.get("streams") or []
    if not streams:
        raise FfprobeError(f"{path}: no tiene stream de video")
    s = streams[0]
    fmt = data.get("format") or {}

    # Convención de `rotation_deg`: grados en sentido HORARIO que hay que girar
    # el cuadro almacenado para verlo derecho (la del tag `rotate` histórico:
    # un iPhone filmando en vertical da 90). ffprobe reporta la matriz de
    # display en sentido antihorario (ese mismo clip da `rotation: -90`), así
    # que se invierte el signo para que las dos fuentes den el mismo número.
    rotation = 0
    for side in s.get("side_data_list") or []:
        if "rotation" in side:
            try:
                rotation = (-int(round(float(side["rotation"])))) % 360
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
    # Salida con claves (`pts_time=0.008333|best_effort_timestamp_time=…|`):
    # el orden de las columnas lo decide ffprobe, así que no se lee por posición.
    raw = _run(
        [
            "-select_streams", "v:0",
            "-show_entries", "frame=pts_time,best_effort_timestamp_time",
            "-of", "compact=p=0:nk=0",
            str(path),
        ]
    )
    times: list[float] = []
    for line in raw.splitlines():
        fields: dict[str, str] = {}
        for cell in line.split("|"):
            key, sep, value = cell.partition("=")
            if sep:
                fields[key.strip()] = value.strip()
        # pts_time es el timestamp de presentación; si falta (N/A), el mejor
        # esfuerzo del decodificador.
        for key in ("pts_time", "best_effort_timestamp_time"):
            value = fields.get(key)
            if value and value != "N/A":
                try:
                    times.append(float(value))
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
    fps_playback = (n - 1) / span if span > 0 else 0.0

    # Los mismos dos números sin el primer delta. El arranque de la cámara (el
    # sensor tarda en entregar el segundo cuadro) no es tasa variable, y con
    # `(n-1)/span` contamina la tasa entera: medido en el original del S22,
    # 29,436 fps en vez de 30,000, o sea todos los tiempos 1,9 % largos.
    # Se usa el span de los cuadros restantes y no la mediana de deltas porque
    # el span promedia el error de cuantización del time base sobre todo el
    # clip (263 deltas), mientras que la mediana lo hereda de un solo delta.
    rest = [d for d in deltas[1:] if d > 0]
    rest_span = times[-1] - times[1]
    if rest and rest_span > 0:
        vfr_excl, fps_excl = max(rest) / min(rest), (n - 2) / rest_span
    else:
        # Dos cuadros: no queda nada al excluir el primer delta.
        vfr_excl, fps_excl = dmax / dmin, fps_playback

    return Counted(
        frames_decoded=n,
        pts_first_s=times[0],
        pts_last_s=times[-1],
        delta_first_s=deltas[0],
        delta_min_s=dmin,
        delta_max_s=dmax,
        delta_median_s=statistics.median(positive),
        zero_deltas=zero,
        vfr_ratio=dmax / dmin,
        fps_playback=fps_playback,
        vfr_ratio_excl_first=vfr_excl,
        fps_playback_excl_first=fps_excl,
    )


def first_delta_note(counted: Counted) -> str | None:
    """La frase que explica por qué el número efectivo difiere del bruto, o
    `None` si no difieren.

    Vive acá para que haya una sola redacción: la usan `analyze()` para su nota
    y el gate, que la guarda en el campo `fps_note` del `capture.json`.
    """
    if not counted.first_delta_is_the_only_outlier:
        return None
    return (
        f"el primer delta es {counted.delta_first_s:.4f} s (arranque de la cámara); sin él, "
        f"ratio {counted.vfr_ratio_excl_first:.2f} y reproducción {counted.fps_playback_excl_first:.3f} fps "
        f"(con él: ratio {counted.vfr_ratio:.2f}, {counted.fps_playback:.3f} fps). "
        "El resto de los deltas es uniforme: no es tasa variable."
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

    # El arranque de la cámara no es tasa variable: si el primer delta es el
    # único fuera de lugar, se juzga con los números sin él (`_effective`).
    # Los brutos quedan intactos en `counted`; nadie pierde información.
    fps_playback_eff = counted.fps_playback_effective
    arranque = first_delta_note(counted)
    if arranque:
        notes.append(arranque)

    fps_capture: float | None = None
    stretch: float | None = None
    if real_duration_s is not None:
        fps_capture = counted.frames_decoded / real_duration_s
        stretch = fps_capture / fps_playback_eff if fps_playback_eff > 0 else None

    if counted.vfr_ratio_effective > VFR_RATIO_MAX:
        verdict = "vfr"
        notes.append(
            f"tasa variable: delta_max/delta_min = {counted.vfr_ratio_effective:.2f} (> {VFR_RATIO_MAX}). "
            "Puede ser VFR real o el bug de captura del iPhone; el clip no sirve para medir tiempos."
        )
        if counted.vfr_ratio > counted.vfr_ratio_effective:
            notes.append(
                f"excluir el primer delta ({counted.delta_first_s:.4f} s) no alcanza: "
                f"quedan deltas de {counted.delta_min_s:.5f} a {counted.delta_max_s:.5f} s."
            )
    elif real_duration_s is None:
        verdict = "sin_duracion_real"
        notes.append(
            "sin una duración real no se puede saber la tasa de captura: el contenedor sólo "
            f"dice la de reproducción ({fps_playback_eff:.2f} fps). Filmá un cronómetro."
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
            f"reproducen a {fps_playback_eff:.2f} fps: factor de estiramiento {stretch:.2f}. "
            "Es un slow-motion horneado o un ready-to-play de Android; los datos se recuperan con el factor."
        )

    if counted.zero_deltas:
        notes.append(f"{counted.zero_deltas} cuadro(s) con timestamp repetido")
    if declared.r_frame_rate > 0 and abs(declared.r_frame_rate - fps_playback_eff) / declared.r_frame_rate > 0.02:
        notes.append(
            f"r_frame_rate declarado {declared.r_frame_rate:.3f} ≠ reproducción medida {fps_playback_eff:.3f}"
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
    if c.first_delta_is_the_only_outlier:
        lines.append(
            f"  sin el 1er delta ({c.delta_first_s:.5f} s): reproducción {c.fps_playback_excl_first:.3f} fps · "
            f"ratio {c.vfr_ratio_excl_first:.3f}  ← el que se usa"
        )
    if t.real_duration_s is not None:
        lines.append(
            f"  con duración real {t.real_duration_s:.3f} s: captura {t.fps_capture:.2f} fps · "
            f"factor de estiramiento {t.stretch_factor:.3f}"
        )
    lines.append(f"  veredicto:  {t.verdict.upper()}")
    for n in t.notes:
        lines.append(f"    · {n}")
    return "\n".join(lines)


def format_sha_line(sha: str) -> str:
    """El sha del clip medido, listo para pegar en `capture-paths.yaml`.

    Existe porque hasta hoy había que calcularlo aparte, y eso es exactamente
    lo que hacía que nadie declarara de qué clip salía una calibración: el
    camino decía `fps_real` y había que creerle. Ver el encargo 34 y
    `capture_paths.CapturePath.calibration_clip_sha256`.
    """
    return (
        "  para capture-paths.yaml (el clip que calibra este camino):\n"
        f'    calibration_clip_sha256: "{sha}"'
    )


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
    # El sha se calcula acá y no en `analyze()`: leer 90 MB es caro y los que
    # llaman a `analyze()` desde el motor (`explore`, la ingesta) ya tienen el
    # suyo. Reusa `sha256_file`, no hay un segundo hasher.
    sha = sha256_file(args.clip)
    if args.json:
        d = t.to_dict()
        d["sha256"] = sha
        print(json.dumps(d, indent=2, ensure_ascii=False))
    else:
        print(format_human(t))
        print(format_sha_line(sha))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
