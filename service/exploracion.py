"""Trabajos de exploración: un video → `kinelab.explore.explore` en un hilo.

Es la cola detrás de `PUT /api/datos`. Un solo trabajo a la vez, a propósito:
el estimador (la sesión CoreML de RTMPose) se crea una vez y se reutiliza en
todos los trabajos, y dos corridas simultáneas sobre la misma sesión no están
probadas. Cada trabajo vive en `data/exploracion/<id>/` con su `trabajo.json`,
así el estado sobrevive a un reinicio del servidor y los archivos se pueden
volver a servir.

Estados, en orden: `en_cola` → `cargando_modelo` (sólo el primero) →
`detectando_pose` → `calculando` → `dibujando` → `listo`, o `error`.

**El disco manda.** `listar()` y `get()` releen los `trabajo.json` que hay en
`data/exploracion/` cada vez, en lugar de creerle a la memoria del proceso: así
aparecen los trabajos de sesiones anteriores y las carpetas que deja otro
proceso, sin reiniciar el servidor. La única excepción es un trabajo de este
proceso que todavía corre: ahí manda la memoria, que lleva el progreso por
cuadro (a disco sólo se escribe al cambiar de etapa). Y **el id de un trabajo
es el nombre de su carpeta**, no el campo `id` del JSON: el nombre de la
carpeta es lo que resuelve la URL.

Un trabajo que no viene de una subida — un ejemplo que arma otro proceso — es
una carpeta más, con los mismos archivos y un `trabajo.json` así:

```json
{"estado": "listo", "origen": "ejemplo", "video": "cmu-64_01-face_on",
 "creado": "2026-09-14T12:00:00+00:00", "altura_m": 1.75, "vista": "face_on",
 "etiqueta": "ejemplo · mocap CMU 64_01 · cámara virtual · no es video"}
```

`estado` es lo único obligatorio: `video` cae en el nombre de la carpeta y
`creado` en la fecha del archivo si faltan. Sin `origen` el trabajo es
`subida`. `etiqueta` es el texto que la pantalla muestra al lado del resultado;
lo escribe quien arma el ejemplo, acá no se inventa ninguno.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kinelab.sport import SportConfig

# Un id es el nombre de una carpeta dentro de `data/exploracion/`: los 32 hex de
# una subida, o el slug de un ejemplo (`ejemplo-cmu-64_01-face_on`). Sin barras,
# sin empezar con punto: no se puede salir de la carpeta con un id.
JOB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
TRABAJO_JSON = "trabajo.json"
ESTADOS_FINALES = ("listo", "error")
ORIGEN_SUBIDA = "subida"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _log(msg: str) -> None:
    print(f"exploración · {msg}", flush=True)


@dataclass
class Trabajo:
    id: str
    dir: Path
    video: str
    altura_m: float | None
    vista: str
    creado: str
    estado: str = "en_cola"
    origen: str = ORIGEN_SUBIDA
    etiqueta: str | None = None
    progreso: dict[str, Any] = field(default_factory=lambda: {"cuadros": 0, "total": None})
    error: str | None = None
    terminado: str | None = None
    segundos: float | None = None
    _resumen: dict[str, Any] | None = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "estado": self.estado,
            "origen": self.origen,
            "etiqueta": self.etiqueta,
            "progreso": dict(self.progreso),
            "error": self.error,
            "video": self.video,
            "altura_m": self.altura_m,
            "vista": self.vista,
            "creado": self.creado,
            "terminado": self.terminado,
            "segundos": self.segundos,
            "archivos": self.archivos(),
            "resumen": self.resumen() if self.estado == "listo" else None,
        }

    def fila(self) -> dict[str, Any]:
        """Una línea de la lista de trabajos: lo justo para elegir uno.

        Sin el resumen entero (son ~20 KB por trabajo): de ahí salen sólo el fps
        y los eventos, y sólo cuando el trabajo está listo.
        """
        r = self.resumen() if self.estado == "listo" else None
        return {
            "id": self.id,
            "estado": self.estado,
            "origen": self.origen,
            "etiqueta": self.etiqueta,
            "video": self.video,
            "altura_m": self.altura_m,
            "vista": self.vista,
            "creado": self.creado,
            "terminado": self.terminado,
            "segundos": self.segundos,
            "error": self.error,
            "fps_archivo": r.get("fps_archivo") if r else None,
            "cuadros": r.get("cuadros") if r else None,
            "eventos_frame": r.get("eventos_frame") if r else None,
        }

    def archivos(self) -> dict[str, str]:
        return {n: f"/api/datos/{self.id}/archivos/{n}" for n in ARCHIVOS if (self.dir / n).is_file()}

    def resumen(self) -> dict[str, Any] | None:
        if self._resumen is None:
            p = self.dir / "datos-eventos.json"
            if p.is_file():
                try:
                    self._resumen = json.loads(p.read_text(encoding="utf-8"))
                except (ValueError, OSError) as e:
                    _log(f"{self.id}/datos-eventos.json ilegible: {e.__class__.__name__}: {e}")
        return self._resumen

    def save(self) -> None:
        d = self.to_dict()
        d.pop("resumen", None)
        d.pop("archivos", None)
        tmp = self.dir / (TRABAJO_JSON + ".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.dir / TRABAJO_JSON)

    @classmethod
    def load(cls, dir: Path) -> "Trabajo":
        f = dir / TRABAJO_JSON
        d = json.loads(f.read_text(encoding="utf-8"))
        if not isinstance(d, dict):
            raise ValueError(f"{TRABAJO_JSON} no es un objeto JSON")
        return cls(
            # El id es la carpeta, no el campo: es lo que resuelve la URL.
            id=dir.name, dir=dir, video=d.get("video") or dir.name, altura_m=d.get("altura_m"),
            vista=d.get("vista", "face_on"), creado=d.get("creado") or _mtime(f), estado=d["estado"],
            origen=d.get("origen") or ORIGEN_SUBIDA, etiqueta=d.get("etiqueta"),
            progreso=d.get("progreso") or {"cuadros": 0, "total": None},
            error=d.get("error"), terminado=d.get("terminado"), segundos=d.get("segundos"),
        )


def _mtime(f: Path) -> str:
    return dt.datetime.fromtimestamp(f.stat().st_mtime, dt.timezone.utc).isoformat(timespec="seconds")


# Lo único que se sirve de la carpeta de un trabajo, con su media type. Cualquier
# otro nombre es 404: nada de recorrer el disco desde la URL.
ARCHIVOS: dict[str, str] = {
    "overlay.mp4": "video/mp4",
    "evento-address.png": "image/png",
    "evento-top.png": "image/png",
    "evento-impact.png": "image/png",
    "evento-follow_end.png": "image/png",
    "datos-por-cuadro.csv": "text/csv; charset=utf-8",
    "datos-eventos.json": "application/json",
    "analysis.json": "application/json",
    "capture.json": "application/json",
}


class Exploracion:
    """La cola de trabajos. `estimator` se inyecta sólo desde tests (uno falso)."""

    def __init__(self, data_dir: Path, sport: SportConfig, estimator: Any | None = None) -> None:
        self.root = data_dir / "exploracion"
        self.sport = sport
        self._estimator = estimator
        self.jobs: dict[str, Trabajo] = {}
        self._sin_json: set[str] = set()
        self._lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="exploracion")
        self._rehydrate()

    def _load(self, dir: Path) -> Trabajo | None:
        """Un trabajo desde su carpeta. Lo ilegible se saltea y queda en el log."""
        try:
            return Trabajo.load(dir)
        except (ValueError, KeyError, OSError) as e:
            _log(f"{dir.name}/{TRABAJO_JSON} ilegible, se saltea: {e.__class__.__name__}: {e}")
            return None

    def _carpetas(self) -> list[Path]:
        """Las carpetas que son un trabajo: las que tienen `trabajo.json`.

        Una carpeta sin él no es un trabajo — puede ser una subida a medio
        recibir, o una copia incompleta —: se saltea y se avisa una vez, para
        que no quede en silencio ni llene el log.
        """
        if not self.root.is_dir():
            return []
        out = []
        for d in sorted(p for p in self.root.iterdir() if p.is_dir()):
            if (d / TRABAJO_JSON).is_file():
                out.append(d)
            elif d.name not in self.jobs and d.name not in self._sin_json:
                self._sin_json.add(d.name)
                _log(f"{d.name}/ no tiene {TRABAJO_JSON}: no es un trabajo, se saltea")
        return out

    def _rehydrate(self) -> None:
        for d in self._carpetas():
            job = self._load(d)
            if job is None:
                continue
            if job.estado not in ESTADOS_FINALES:
                job.estado, job.error = "error", "El servidor se reinició mientras corría este trabajo. Subí el video de nuevo."
                job.save()
            shutil.rmtree(job.dir / "subida", ignore_errors=True)
            self.jobs[job.id] = job

    def new(self, video_name: str, altura_m: float | None, vista: str) -> Trabajo:
        job_id = uuid.uuid4().hex
        d = self.root / job_id
        d.mkdir(parents=True, exist_ok=False)
        job = Trabajo(id=job_id, dir=d, video=video_name, altura_m=altura_m, vista=vista, creado=_now())
        with self._lock:
            self.jobs[job_id] = job
        return job

    def discard(self, job: Trabajo) -> None:
        with self._lock:
            self.jobs.pop(job.id, None)
        shutil.rmtree(job.dir, ignore_errors=True)

    def _en_curso(self, job_id: str) -> Trabajo | None:
        """El trabajo de este proceso que está corriendo, si es ése: manda la memoria."""
        job = self.jobs.get(job_id)
        return job if job is not None and job.estado not in ESTADOS_FINALES else None

    def get(self, job_id: str) -> Trabajo | None:
        if not JOB_ID.match(job_id):
            return None
        en_curso = self._en_curso(job_id)
        if en_curso is not None:
            return en_curso
        d = self.root / job_id
        if not (d / TRABAJO_JSON).is_file():
            # Borrado del disco: deja de existir también acá.
            with self._lock:
                self.jobs.pop(job_id, None)
            return None
        return self._load(d)

    def listar(self) -> list[Trabajo]:
        """Todos los trabajos que hay en disco, del más nuevo al más viejo."""
        out = []
        for d in self._carpetas():
            job = self._en_curso(d.name) or self._load(d)
            if job is not None:
                out.append(job)
        out.sort(key=lambda j: (j.creado, j.id), reverse=True)
        return out

    def submit(self, job: Trabajo, upload: Path) -> None:
        job.save()
        self.pool.submit(self._run, job, upload)

    def close(self) -> None:
        self.pool.shutdown(wait=False, cancel_futures=True)

    # --- en el hilo de trabajo ------------------------------------------------------

    def _estimator_for(self, job: Trabajo) -> Any:
        if self._estimator is None:
            job.estado = "cargando_modelo"
            job.save()
            from kinelab.perception.estimator import EstimatorConfig, PoseEstimator

            self._estimator = PoseEstimator(EstimatorConfig())
        return self._estimator

    def _run(self, job: Trabajo, upload: Path) -> None:
        from kinelab.explore import explore

        t0 = time.monotonic()
        print(f"exploración {job.id[:8]} · {job.video} · empieza", flush=True)

        def stage(name: str, info: dict[str, Any]) -> None:
            job.estado = name
            job.progreso = {"cuadros": 0, "total": info.get("total")}
            job.save()

        def progress(hechos: int) -> None:
            # `iter_frames` avisa cada 10 cuadros con la cantidad ya procesada.
            total = job.progreso.get("total")
            job.progreso["cuadros"] = min(hechos, total) if total else hechos

        try:
            est = self._estimator_for(job)
            explore(upload, job.dir, self.sport, height_m=job.altura_m, view=job.vista, progress=progress, estimator=est, stage=stage)
            if job.resumen() is None:
                raise RuntimeError("terminó sin escribir datos-eventos.json")
            job.estado = "listo"
            if job.progreso.get("total"):
                job.progreso["cuadros"] = job.progreso["total"]
        except Exception as e:  # noqa: BLE001 — el error entero va al estado del trabajo
            job.estado, job.error = "error", f"{e.__class__.__name__}: {e}"
        finally:
            job.segundos = round(time.monotonic() - t0, 1)
            job.terminado = _now()
            shutil.rmtree(upload.parent, ignore_errors=True)
            job.save()
            print(f"exploración {job.id[:8]} · {job.video} · {job.estado} en {job.segundos} s" + (f" · {job.error}" if job.error else ""), flush=True)
