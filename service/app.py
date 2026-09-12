"""La API detrás de `service/static/index.html`.

Tres cosas, y nada más:

- `PUT /api/fps-truth`  sube un clip y devuelve lo que imprime
  `kinelab.tools.fps_truth` (para calibrar el cronómetro).
- `PUT /api/ingest`     sube un clip, lo pasa por el gate y deja la sesión en
  disco con su `capture.json`, pase o no.
- `GET /api/sessions`   lista los `capture.json` que hay en `data/sessions/`.

El archivo viaja como cuerpo crudo de un PUT (no multipart): así no hace falta
ninguna dependencia fuera de FastAPI. Se escribe por chunks a `data/incoming/`
y se borra al terminar: la copia que queda es la que hace la ingesta.
"""

from __future__ import annotations

import os
import re
import shutil
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from kinelab.ingest.__main__ import ingest_clip
from kinelab.ingest.capture_paths import CapturePaths, load_capture_paths
from kinelab.ingest.gate import CaptureJson
from kinelab.ingest.session import validate_slug
from kinelab.tools.fps_truth import FfprobeError, analyze
from sports import get_sport

STATIC = Path(__file__).resolve().parent / "static"
REPO = Path(__file__).resolve().parents[1]
_SUFFIX = re.compile(r"^\.[a-z0-9]{1,5}$")


def default_data_dir() -> Path:
    return Path(os.environ.get("KINELAB_DATA") or REPO / "data")


def safe_filename(name: str) -> tuple[str, str]:
    """Nombre base y extensión seguros para un archivo que subió el navegador.

    Se descarta cualquier directorio (el navegador no debería mandarlo, pero
    no se confía); la extensión va en minúsculas y tiene que ser corta y
    alfanumérica. Devuelve `(nombre_base, sufijo)`.
    """
    if not name or name.endswith(("/", "\\")):
        raise HTTPException(400, f"Nombre de archivo inválido: '{name}'. Se espera algo como IMG_0412.MOV.")
    base = Path(name.replace("\\", "/")).name
    suffix = Path(base).suffix.lower()
    if not base or base.startswith(".") or not _SUFFIX.match(suffix):
        raise HTTPException(400, f"Nombre de archivo inválido: '{name}'. Se espera algo como IMG_0412.MOV.")
    return base, suffix


async def _receive_to(request: Request, dest: Path) -> int:
    """Escribe el cuerpo de la petición a `dest` por chunks. Devuelve los bytes."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    with dest.open("wb") as f:
        async for chunk in request.stream():
            f.write(chunk)
            size += len(chunk)
    if size == 0:
        raise HTTPException(400, "No llegó ningún archivo: el cuerpo de la petición está vacío.")
    return size


def _session_row(data_dir: Path, capture_json: Path) -> dict[str, Any]:
    rel = capture_json.parent.relative_to(data_dir)
    row: dict[str, Any] = {"take_dir": str(rel)}
    try:
        c = CaptureJson.model_validate_json(capture_json.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        row["error"] = f"capture.json ilegible: {e.__class__.__name__}"
        return row
    row.update(
        athlete=c.athlete,
        day=rel.parts[2] if len(rel.parts) > 2 else None,
        gesture=c.gesture,
        view=c.view,
        capture_path_id=c.capture_path_id,
        verdict=c.gate.verdict,
        reasons=c.gate.reasons,
        codec=c.codec,
        fps_real=c.fps_real,
        fps_playback=c.fps_playback,
        frames_decoded=c.frames_decoded,
        duration_s=c.duration_s,
        original_name=c.original_name,
    )
    return row


def create_app(data_dir: Path | None = None, sport_id: str = "golf") -> FastAPI:
    data = (data_dir or default_data_dir()).resolve()
    sport = get_sport(sport_id)
    incoming = data / "incoming"

    app = FastAPI(title="kinelab · gate de ingesta", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.data_dir = data
    app.state.sport = sport

    def capture_paths() -> CapturePaths:
        f = data / "capture-paths.yaml"
        if not f.is_file():
            raise HTTPException(500, f"No existe {f}. Tiene que estar el capture-paths.yaml del repo.")
        try:
            return load_capture_paths(f)
        except ValueError as e:
            raise HTTPException(500, f"capture-paths.yaml inválido: {e}") from e

    def new_upload_dir() -> Path:
        d = incoming / uuid.uuid4().hex
        d.mkdir(parents=True, exist_ok=False)
        return d

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC / "index.html", media_type="text/html; charset=utf-8")

    @app.get("/api/config")
    async def config() -> dict[str, Any]:
        cp = capture_paths()
        return {
            "sport": {"id": sport.id, "gestures": list(sport.gestures), "views": list(sport.views), "fps_min": sport.fps_min},
            "capture_paths": [p.model_dump(mode="json") for p in cp.paths],
            "data_dir": str(data),
        }

    @app.put("/api/fps-truth")
    async def fps_truth(
        request: Request,
        filename: str = Query(...),
        real_duration_s: float | None = Query(None, gt=0),
        nominal_fps: float | None = Query(None, gt=0),
    ) -> dict[str, Any]:
        base, _suffix = safe_filename(filename)
        upload_dir = new_upload_dir()
        tmp = upload_dir / base
        try:
            await _receive_to(request, tmp)
            truth = await run_in_threadpool(analyze, tmp, real_duration_s, nominal_fps)
        except FfprobeError as e:
            raise HTTPException(422, f"ffprobe no pudo leer '{base}': {e}") from e
        finally:
            shutil.rmtree(upload_dir, ignore_errors=True)
        out = truth.to_dict()
        out["path"] = base
        return out

    @app.put("/api/ingest")
    async def ingest(
        request: Request,
        filename: str = Query(...),
        athlete: str = Query(...),
        gesture: str = Query(...),
        view: str = Query(...),
        capture_path_id: str = Query(...),
        day: date | None = Query(None),
    ) -> dict[str, Any]:
        base, _suffix = safe_filename(filename)
        # Lo que se puede rechazar antes de recibir 85 MB, se rechaza antes.
        try:
            validate_slug(athlete, "atleta")
            validate_slug(gesture, "gesto")
            validate_slug(view, "vista")
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        cp = capture_paths()

        upload_dir = new_upload_dir()
        tmp = upload_dir / base  # conserva el nombre: es el `original_name` del capture.json
        try:
            await _receive_to(request, tmp)
            take_dir, capture = await run_in_threadpool(
                ingest_clip,
                tmp,
                athlete=athlete,
                gesture=gesture,
                view=view,
                capture_path_id=capture_path_id,
                capture_paths=cp,
                sport=sport,
                data_dir=data,
                day=day,
            )
        except FfprobeError as e:
            raise HTTPException(422, f"ffprobe no pudo leer '{base}': {e}") from e
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        finally:
            shutil.rmtree(upload_dir, ignore_errors=True)
        return {"take_dir": str(take_dir.relative_to(data)), "capture": capture.model_dump(mode="json")}

    @app.get("/api/sessions")
    async def sessions() -> list[dict[str, Any]]:
        root = data / "sessions"
        if not root.is_dir():
            return []
        # sessions/<atleta>/<fecha>/<gesto>/<vista>/take-NN/capture.json
        files = sorted(root.glob("*/*/*/*/take-*/capture.json"))
        return [_session_row(data, f) for f in files]

    return app


# Para `uvicorn service.app:app`. `python -m service` usa create_app() directamente.
app = create_app()
