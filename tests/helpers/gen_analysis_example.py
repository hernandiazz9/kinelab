"""Regenera `data/examples/analysis.example.json` desde el swing sintético.

    .venv/bin/python tests/helpers/gen_analysis_example.py

El ejemplo del repo es lo único que valida el contrato **fuera** de un test, y
hasta el encargo 16 se editaba a mano: quedó con `summary.gain`, con
`sequence_order` y con el `method: direction_change` que ADR-017 reemplazó, sin
que nada avisara. Se genera con el motor de verdad y se commitea.

Lo único que se fija a mano es lo que no puede ser reproducible: `generated_at`
y la procedencia del clip de origen, para que el archivo no cambie en cada
corrida y el diff diga sólo lo que cambió de verdad. La pose es sintética
(`tests/helpers/synth_swing.py`), así que los números **no son referencia de
nada**: el archivo sirve para el schema, y el propio `warnings[]` lo dice.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tests"))

from kinelab.analysis import build_analysis  # noqa: E402
from kinelab.ingest.gate import CaptureJson, Check, Gate  # noqa: E402
from kinelab.perception.posestore import PoseData, save_pose  # noqa: E402
from sports.golf.config import GOLF  # noqa: E402

from helpers.synth_swing import synth_swing  # noqa: E402

OUT = REPO / "data" / "examples" / "analysis.example.json"
GENERATED_AT = "2026-09-12T12:00:00+00:00"
CAPTURE_PATH = "iphone17pro-video-1080p120-airdrop"
FPS = 120.0
HEIGHT_M = 1.80
AVISO = "Ejemplo generado desde un swing SINTÉTICO (tests/helpers/gen_analysis_example.py): sirve para el schema, no como referencia de valores."


def _pose(sw) -> PoseData:
    T = sw.keypoints.shape[0]
    bh = sw.body_height_px
    return PoseData(
        sw.keypoints, sw.scores, np.zeros((T, 4), np.float32), sw.timestamps_s, np.zeros(T, np.uint8),
        {
            "model": "sintético",
            "framing": {"detection_rate": 1.0, "body_height_px_median": bh, "body_height_px_min": bh - 10.0, "body_height_px_max": bh + 10.0, "frac_of_frame": round(bh / sw.frame[0], 3)},
            "plausibility_counts": {"LOW_SCORE": 0, "ELBOW_RANGE": 0, "SEGMENT_LENGTH": 0, "MISSING": 0},
            "camera_motion_px": 0.03,
        },
    )


def _capture() -> CaptureJson:
    T = 0
    return CaptureJson(
        athlete="ejemplo", gesture="driver", view="face_on", capture_path_id=CAPTURE_PATH,
        capture_path_calibrated=True, fps_provenance="medido_aqui",
        fps_real=FPS, fps_playback=FPS, fps_playback_raw=FPS, stretch_factor=1.0,
        fps_source=f"capture-paths.yaml:{CAPTURE_PATH}", codec="hevc", width=1080, height=1920, rotation_deg=0,
        frames_decoded=T, duration_s=0.0, duration_playback_s=0.0, vfr_ratio=1.0, vfr_ratio_raw=1.0,
        first_delta_s=round(1.0 / FPS, 6), fps_note=None, recorded_at=GENERATED_AT, sha256_original="0" * 64,
        original_name="sintetico.mov",
        gate=Gate(verdict="ok", checks=[Check(id="ejemplo", passed=None, value=CAPTURE_PATH, reason=AVISO)], reasons=[]),
    )


def main(tmp: Path) -> int:
    sw = synth_swing(FPS, n_reps=3)
    tmp.mkdir(parents=True, exist_ok=True)
    save_pose(tmp, _pose(sw))
    a = build_analysis(tmp, _capture(), _pose(sw), GOLF, height_m=HEIGHT_M)
    a["header"]["generated_at"] = GENERATED_AT
    a["warnings"] = [AVISO, *a["warnings"]]
    from kinelab.perception.posestore import finite_or_none

    OUT.write_text(json.dumps(finite_or_none(a), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{OUT}: {a['summary']['rep_count']} repeticiones · schema {a['header']['schema_version']} · registro {a['header']['registry_version']}")
    return 0


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        raise SystemExit(main(Path(d) / "take"))
