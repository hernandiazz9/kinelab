"""La API local. La usan la app Next.js de `web/` y la página vieja del gate
en `service/static/index.html`.

- `PUT /api/fps-truth`  sube un clip y devuelve lo que imprime
  `kinelab.tools.fps_truth` (para calibrar el cronómetro).
- `PUT /api/ingest`     sube un clip, lo pasa por el gate y deja la sesión en
  disco con su `capture.json`, pase o no.
- `GET /api/sessions`   lista los `capture.json` que hay en `data/sessions/`.
- `PUT /api/datos`      sube un video y encola el modo exploración
  (`kinelab.explore`): 202 con el id del trabajo. `camino` es el camino de
  captura declarado (ADR-016), por defecto el genérico "no sé con qué se
  filmó"; se valida ANTES de recibir el archivo. Ver `service/exploracion.py`.
- `GET /api/datos`      la lista de trabajos que hay en disco, del más nuevo al
  más viejo: los de sesiones anteriores y los ejemplos que deje otro proceso.
- `GET /api/datos/{id}` estado del trabajo; cuando está `listo`, trae el
  contenido de `datos-eventos.json` y las URLs de sus archivos.
- `GET /api/datos/{id}/archivos/{nombre}` sirve `overlay.mp4` (con `Range`/206:
  lo hace solo el `FileResponse` de Starlette 1.6), las fotos, el CSV y los JSON.

El archivo viaja como cuerpo crudo de un PUT (no multipart): así no hace falta
ninguna dependencia fuera de FastAPI. Se escribe por chunks a `data/incoming/`
y se borra al terminar: la copia que queda es la que hace la ingesta.
"""

from __future__ import annotations

import os
import re
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from kinelab.ingest.__main__ import ingest_clip
from kinelab.ingest.capture_paths import GENERIC_VIDEO_ID, CapturePaths, load_capture_paths, resolve_path_id
from kinelab.ingest.gate import CaptureJson, slomo_declared_reason
from kinelab.ingest.session import validate_slug
from kinelab.tools.fps_truth import FfprobeError, analyze
from service.exploracion import ARCHIVOS, Exploracion
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


def create_app(data_dir: Path | None = None, sport_id: str = "golf", estimator: Any | None = None) -> FastAPI:
    """`estimator`: sólo para tests, un estimador falso para la cola de exploración."""
    data = (data_dir or default_data_dir()).resolve()
    sport = get_sport(sport_id)
    incoming = data / "incoming"
    exploracion = Exploracion(data, sport, estimator=estimator)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        exploracion.close()

    app = FastAPI(title="kinelab · servicio local", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.data_dir = data
    app.state.sport = sport
    app.state.exploracion = exploracion

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

    # --- exploración: un video → palitos + toda la data ------------------------------

    def trabajo_or_404(job_id: str):
        job = exploracion.get(job_id)
        if job is None:
            raise HTTPException(404, f"No hay ningún trabajo de exploración con id '{job_id}'.")
        return job

    @app.put("/api/datos", status_code=202)
    async def datos_put(
        request: Request,
        filename: str = Query(...),
        altura_m: float | None = Query(None, gt=0.5, lt=2.6, description="altura del atleta en metros; sin ella no hay cm"),
        vista: str = Query("face_on"),
        camino: str = Query(GENERIC_VIDEO_ID, description="id de capture-paths.yaml: con qué se filmó (ADR-016)"),
    ) -> dict[str, Any]:
        base, _suffix = safe_filename(filename)
        if vista not in sport.views:
            raise HTTPException(400, f"Vista '{vista}' desconocida. Válidas: {', '.join(sport.views)}.")
        # El camino se valida antes de recibir el archivo: un id que no existe o
        # un Slo-Mo sin cronómetro no arrancan un trabajo cuyo eje de tiempo no
        # se conoce (ADR-016). La frase del slomo es la misma que da el gate.
        try:
            path = resolve_path_id(camino, capture_paths())
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        if not path.calibrated and path.mode == "slomo":
            raise HTTPException(400, slomo_declared_reason(path))
        job = exploracion.new(base, altura_m, vista, path.id)
        upload = job.dir / "subida" / base
        try:
            await _receive_to(request, upload)
        except BaseException:
            exploracion.discard(job)
            raise
        exploracion.submit(job, upload)
        return job.to_dict()

    @app.get("/api/datos")
    async def datos_list() -> list[dict[str, Any]]:
        """Los trabajos que hay en disco, del más nuevo al más viejo.

        Lee los `trabajo.json` en cada llamada: los trabajos de sesiones
        anteriores y las carpetas de ejemplo que deje otro proceso aparecen sin
        reiniciar el servidor, y uno borrado del disco desaparece.
        """
        return [t.fila() for t in await run_in_threadpool(exploracion.listar)]

    @app.get("/api/datos/{job_id}")
    async def datos_get(job_id: str) -> dict[str, Any]:
        return trabajo_or_404(job_id).to_dict()

    @app.get("/api/datos/{job_id}/archivos/{nombre}")
    async def datos_archivo(job_id: str, nombre: str, descargar: bool = Query(False)) -> FileResponse:
        job = trabajo_or_404(job_id)
        media = ARCHIVOS.get(nombre)
        if media is None:
            raise HTTPException(404, f"'{nombre}' no es un archivo de exploración. Hay: {', '.join(ARCHIVOS)}.")
        path = job.dir / nombre
        if not path.is_file():
            raise HTTPException(404, f"'{nombre}' todavía no existe para este trabajo (estado: {job.estado}).")
        # `filename` pone Content-Disposition: attachment → el navegador descarga en vez de mostrar.
        return FileResponse(path, media_type=media, filename=f"{Path(job.video).stem}-{nombre}" if descargar else None)

    return app


# Para `uvicorn service.app:app`. `python -m service` usa create_app() directamente.
app = create_app()
