"""Trabajos de exploración: un video → `kinelab.explore.explore` en un hilo.

Es la cola detrás de `PUT /api/datos`. Un solo trabajo a la vez, a propósito:
el estimador (la sesión CoreML de RTMPose) se crea una vez y se reutiliza en
todos los trabajos, y dos corridas simultáneas sobre la misma sesión no están
probadas. Cada trabajo vive en `data/exploracion/<id>/` con su `trabajo.json`,
así el estado sobrevive a un reinicio del servidor y los archivos se pueden
volver a servir.

Estados, en orden: `en_cola` → `cargando_modelo` (sólo el primero) →
`detectando_pose` → `calculando` → `dibujando` → `listo`, o `error`.
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

JOB_ID = re.compile(r"^[a-f0-9]{32}$")
TRABAJO_JSON = "trabajo.json"
ESTADOS_FINALES = ("listo", "error")

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


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


@dataclass
class Trabajo:
    id: str
    dir: Path
    video: str
    altura_m: float | None
    vista: str
    creado: str
    estado: str = "en_cola"
    progreso: dict[str, Any] = field(default_factory=lambda: {"cuadros": 0, "total": None})
    error: str | None = None
    terminado: str | None = None
    segundos: float | None = None
    _resumen: dict[str, Any] | None = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "estado": self.estado,
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

    def archivos(self) -> dict[str, str]:
        return {n: f"/api/datos/{self.id}/archivos/{n}" for n in ARCHIVOS if (self.dir / n).is_file()}

    def resumen(self) -> dict[str, Any] | None:
        if self._resumen is None:
            p = self.dir / "datos-eventos.json"
            if p.is_file():
                self._resumen = json.loads(p.read_text(encoding="utf-8"))
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
        d = json.loads((dir / TRABAJO_JSON).read_text(encoding="utf-8"))
        return cls(
            id=d["id"], dir=dir, video=d["video"], altura_m=d.get("altura_m"), vista=d.get("vista", "face_on"),
            creado=d["creado"], estado=d["estado"], progreso=d.get("progreso") or {"cuadros": 0, "total": None},
            error=d.get("error"), terminado=d.get("terminado"), segundos=d.get("segundos"),
        )


class Exploracion:
    """La cola de trabajos. `estimator` se inyecta sólo desde tests (uno falso)."""

    def __init__(self, data_dir: Path, sport: SportConfig, estimator: Any | None = None) -> None:
        self.root = data_dir / "exploracion"
        self.sport = sport
        self._estimator = estimator
        self.jobs: dict[str, Trabajo] = {}
        self._lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="exploracion")
        self._rehydrate()

    def _rehydrate(self) -> None:
        if not self.root.is_dir():
            return
        for f in sorted(self.root.glob(f"*/{TRABAJO_JSON}")):
            try:
                job = Trabajo.load(f.parent)
            except (ValueError, KeyError, OSError):
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

    def get(self, job_id: str) -> Trabajo | None:
        if not JOB_ID.match(job_id):
            return None
        return self.jobs.get(job_id)

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
