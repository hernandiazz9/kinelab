"""`python -m kinelab_truth.calibrate FOTOS_DIR --cols 9 --rows 6 --square-mm 25 --out cameras/<id>.yaml`

Intrínsecos reales del teléfono con `cv2.calibrateCamera` sobre fotos de un
tablero de ajedrez (ESPECIFICACION 3.1). Filmá el tablero con el MISMO modo
(1080p120) que la sesión: el recorte del sensor cambia con el modo."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import yaml


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("photos", type=Path)
    ap.add_argument("--cols", type=int, required=True, help="esquinas interiores por fila")
    ap.add_argument("--rows", type=int, required=True)
    ap.add_argument("--square-mm", type=float, required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    objp = np.zeros((a.rows * a.cols, 3), np.float32)
    objp[:, :2] = np.mgrid[0 : a.cols, 0 : a.rows].T.reshape(-1, 2) * (a.square_mm / 1000.0)
    obj, img, size = [], [], None
    for f in sorted(a.photos.glob("*")):
        im = cv2.imread(str(f))
        if im is None:
            continue
        gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        size = gray.shape[::-1]
        ok, corners = cv2.findChessboardCorners(gray, (a.cols, a.rows))
        if ok:
            corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001))
            obj.append(objp)
            img.append(corners)
    if len(obj) < 8:
        print(f"sólo {len(obj)} fotos con tablero detectado; hacen falta ≥ 8")
        return 1
    rms, K, dist, _, _ = cv2.calibrateCamera(obj, img, size, None, None)
    out = {"id": a.id, "width": size[0], "height": size[1], "fx": float(K[0, 0]), "fy": float(K[1, 1]), "cx": float(K[0, 2]), "cy": float(K[1, 2]), "dist": [float(x) for x in dist.ravel()[:5]], "provenance": "medido_aqui", "rms_px": float(rms), "photos": len(obj)}
    a.out.write_text(yaml.safe_dump(out, sort_keys=False), encoding="utf-8")
    print(f"{a.out}: rms {rms:.3f} px con {len(obj)} fotos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
