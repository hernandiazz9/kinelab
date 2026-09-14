"""Clips sintéticos, fabricados con ffmpeg en el propio test.

Reproducen los tres casos que la investigación midió y que el contenedor no
distingue: un clip a 240 fps reales, el mismo con los timestamps estirados
ocho veces (lo que hace un slow-motion horneado), y el mismo remuestreado a 30
(los cuadros perdidos de verdad). Más un HEVC a 120 fps para el camino "ok",
una variante de tasa variable, una corta, una rotada por metadatos y una con
el primer delta de PTS largo (el arranque de la cámara, que no es VFR).

Lo verificado en ffmpeg 9.0.1 al escribir estos fixtures está en ESTADO.md
§Riesgos: qué salió como se esperaba y qué hubo que cambiar.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

SIZE = "96x96"  # chiquito: lo que importa son los timestamps, no los píxeles


def _ffmpeg() -> str | None:
    return shutil.which("ffmpeg")


def _encoders() -> str:
    out = subprocess.run([_ffmpeg(), "-hide_banner", "-encoders"], capture_output=True, text=True)
    return out.stdout


def _hevc_encoder(encoders: str) -> str | None:
    if "libx265" in encoders:
        return "libx265"
    if "hevc_videotoolbox" in encoders:
        return "hevc_videotoolbox"
    return None


def _ff(*args: str) -> None:
    subprocess.run(
        [_ffmpeg(), "-y", "-v", "error", "-nostdin", *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    )


def _x264(out: Path, *pre: str, post: tuple[str, ...] = ()) -> Path:
    _ff(*pre, "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", *post, str(out))
    return out


def _hevc(enc: str, out: Path, *pre: str, post: tuple[str, ...] = ()) -> Path:
    extra: tuple[str, ...] = ("-x265-params", "log-level=none", "-preset", "ultrafast") if enc == "libx265" else ()
    _ff(*pre, "-c:v", enc, *extra, "-pix_fmt", "yuv420p", "-tag:v", "hvc1", *post, str(out))
    return out


@pytest.fixture(scope="session")
def clips(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    if _ffmpeg() is None:
        pytest.skip("ffmpeg no está en el PATH")
    encoders = _encoders()
    if "libx264" not in encoders:
        pytest.skip("ffmpeg sin libx264")
    hevc = _hevc_encoder(encoders)

    d = tmp_path_factory.mktemp("clips")
    out: dict[str, Path] = {}

    # 240 fps reales, 4 s → 960 cuadros, CFR.
    real = _x264(d / "real240.mp4", "-f", "lavfi", "-i", f"testsrc2=size={SIZE}:rate=240", "-t", "4")
    out["real240_h264"] = real

    # Mismos 960 cuadros con los PTS estirados ×8: reproduce a 30 fps durante 32 s.
    out["slowed30_h264"] = _x264(
        d / "slowed30.mp4", "-i", str(real), "-vf", "setpts=8*PTS", "-fps_mode", "passthrough"
    )

    # Remuestreado a 30 fps: ~120 cuadros en 4 s (ffmpeg 9 da 122). Los otros
    # ~840 se perdieron.
    out["resampled30_h264"] = _x264(d / "resampled30.mp4", "-i", str(real), "-r", "30")

    # 30 fps reales desde el origen, 4 s (para el chequeo de fps mínimo).
    out["real30_h264"] = _x264(d / "real30.mp4", "-f", "lavfi", "-i", f"testsrc2=size={SIZE}:rate=30", "-t", "4")

    # Los mismos 120 cuadros con el PRIMER delta largo y el resto CFR: lo que
    # hace la cámara al arrancar. Medido en el original del Galaxy S22 Ultra:
    # 263 deltas de 0,0333 s y uno de 0,2015 s, el primero. Acá se reproduce
    # con 0,2 s exactos (6 deltas de 30 fps). `gt(N,0)` empuja todos los
    # cuadros menos el primero; la coma va escapada porque en un filtergraph
    # separa filtros.
    out["first_delta30_h264"] = _x264(
        d / "first_delta30.mp4",
        "-i", str(out["real30_h264"]),
        "-vf", r"setpts=PTS+gt(N\,0)*5/30/TB",
        "-fps_mode", "passthrough",
    )

    if hevc is not None:
        # El camino "bueno": HEVC a 120 fps, 4 s → 480 cuadros.
        h120 = _hevc(hevc, d / "hevc120.mov", "-f", "lavfi", "-i", f"testsrc2=size={SIZE}:rate=120", "-t", "4")
        out["hevc120"] = h120

        # Tasa variable: un tramo a 120 fps seguido de uno a 60, concatenados sin
        # recodificar → deltas de 8,3 y 16,7 ms, ratio 2,0; 480 cuadros en 5 s.
        # Meter jitter con `setpts` no alcanza: aun con `-fps_mode passthrough`,
        # ffmpeg 9 usa 1/fps como time base del encoder y redondea cada PTS a
        # esa grilla (medido: `-enc_time_base 1/90000` lo conserva). Ver ESTADO.md.
        seg120 = _hevc(hevc, d / "vfr_seg120.mov", "-f", "lavfi", "-i", f"testsrc2=size={SIZE}:rate=120", "-t", "3")
        seg60 = _hevc(hevc, d / "vfr_seg60.mov", "-f", "lavfi", "-i", f"testsrc2=size={SIZE}:rate=60", "-t", "2")
        concat_list = d / "vfr_concat.txt"
        concat_list.write_text(f"file '{seg120.name}'\nfile '{seg60.name}'\n", encoding="utf-8")
        _ff("-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(d / "hevc120_vfr.mov"))
        out["hevc120_vfr"] = d / "hevc120_vfr.mov"

        # Demasiado corta: 1 s.
        out["hevc120_short"] = _hevc(hevc, d / "hevc120_short.mov", "-f", "lavfi", "-i", f"testsrc2=size={SIZE}:rate=120", "-t", "1")

        # Rotada por metadatos, como un celular en vertical: el cuadro se guarda
        # 64x96 y la matriz de display pide girarlo 90° en sentido horario
        # (ffmpeg lo expresa antihorario: -90). `-metadata:s:v rotate=90` ya no
        # escribe nada en ffmpeg 9; `-display_rotation` con `-c copy` sí.
        rot_base = _hevc(hevc, d / "rot_base.mov", "-f", "lavfi", "-i", "testsrc2=size=64x96:rate=120", "-t", "4")
        try:
            _ff("-display_rotation", "-90", "-i", str(rot_base), "-c", "copy", str(d / "hevc120_rot90.mov"))
            out["hevc120_rot90"] = d / "hevc120_rot90.mov"
        except subprocess.CalledProcessError:
            pass
    return out


@pytest.fixture(scope="session")
def capture_paths_yaml(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Caminos calibrados a mano para los clips sintéticos."""
    p = tmp_path_factory.mktemp("paths") / "capture-paths.yaml"
    p.write_text(
        """schema_version: "1.0.0"
paths:
  - id: test-hevc-120-cfr
    device: sintético
    mode: video
    nominal_fps: 120
    codec_expected: hevc
    transfer: test
    fps_real: 120.0
    fps_playback: 120.0
    stretch_factor: 1.0
    fps_method: generado con ffmpeg
    calibrated_on: 2026-09-12
    calibrated_by: tests
  - id: test-h264-240-cfr
    device: sintético
    mode: video
    nominal_fps: 240
    codec_expected: h264
    transfer: test
    fps_real: 240.0
    fps_playback: 240.0
    stretch_factor: 1.0
    fps_method: generado con ffmpeg
    calibrated_on: 2026-09-12
    calibrated_by: tests
  - id: test-h264-slomo-240-to-30
    device: sintético
    mode: slomo
    nominal_fps: 240
    codec_expected: h264
    transfer: test
    fps_real: 240.0
    fps_playback: 30.0
    stretch_factor: 8.0
    fps_method: generado con ffmpeg, setpts=8*PTS
    calibrated_on: 2026-09-12
    calibrated_by: tests
  - id: test-h264-30-cfr
    device: sintético
    mode: video
    nominal_fps: 30
    codec_expected: h264
    transfer: test
    fps_real: 30.0
    fps_playback: 30.0
    stretch_factor: 1.0
    fps_method: generado con ffmpeg
    calibrated_on: 2026-09-12
    calibrated_by: tests
""",
        encoding="utf-8",
    )
    return p
