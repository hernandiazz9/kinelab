"""Publicar un trabajo a internet desde la pantalla, y despublicarlo.

Es la cola detrás de `POST /api/datos/{id}/publicar` y de su `DELETE`. Corre
`kinelab.tools.publicar` en un hilo y lleva en qué paso va, porque exportar,
construir el sitio y desplegarlo tardan decenas de segundos y la pantalla no se
puede quedar colgada esperando.

**Uno por vez.** Los cuatro pasos terminan en un `vercel deploy` de todo el
sitio: dos publicaciones simultáneas se pisarían el `web/out/` y el árbol que se
sube. Un segundo pedido mientras hay uno corriendo se rechaza con 409 y dice
cuál está corriendo.

**Publicar es deliberado y por trabajo.** Nada de esto pasa al subir un video:
`kinelab.explore` no lo llama nunca. La única forma de que un trabajo salga a
internet es que alguien pida explícitamente este endpoint para ese id.

**Qué está publicado sale del disco**, de `data/publicados.json`, que es el
registro que va a git. No se lleva una copia en memoria: el registro lo escribe
el comando, y acá se lee cada vez, igual que `Exploracion.listar()` relee los
`trabajo.json` (§El disco manda).
"""

from __future__ import annotations

import datetime as dt
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kinelab.tools.publicar import (
    Ejecutor,
    Paso,
    PublicarError,
    SITIO,
    archivo_registro,
    correr,
    dir_demo,
    leer_registro,
    publicar,
    quitar,
)

PUBLICAR = "publicar"
QUITAR = "quitar"

#: Cómo se nombra cada acción mientras corre, para los mensajes al entrenador.
GERUNDIO = {PUBLICAR: "publicando", QUITAR: "quitando de internet"}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _log(msg: str) -> None:
    print(f"publicación · {msg}", flush=True)


@dataclass
class Publicacion:
    """En qué va una publicación (o una baja). Es lo que mira la pantalla."""

    id: str
    accion: str  # publicar | quitar
    estado: str = "corriendo"  # corriendo | listo | error
    paso: int = 0
    total: int = 4
    texto: str = "arrancando"
    error: str | None = None
    url: str | None = None
    empezado: str = field(default_factory=_now)
    terminado: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "accion": self.accion,
            "estado": self.estado,
            "paso": self.paso,
            "total": self.total,
            "texto": self.texto,
            "error": self.error,
            "url": self.url,
            "empezado": self.empezado,
            "terminado": self.terminado,
        }


class Publicaciones:
    """La cola de publicaciones: una sola a la vez, en un hilo aparte.

    `ejecutar` se inyecta sólo desde los tests, con un ejecutor de comandos falso
    que no construye el sitio ni habla con internet.
    """

    def __init__(self, repo: Path, data_dir: Path, ejecutar: Ejecutor | None = None) -> None:
        self.repo = repo
        self.data_dir = data_dir
        self._ejecutar: Ejecutor = ejecutar or correr
        self._lock = threading.Lock()
        self._actual: Publicacion | None = None
        self._ultima: Publicacion | None = None
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="publicacion")

    # --- lectura ---------------------------------------------------------------------

    def registro(self) -> dict[str, Any]:
        """El registro del disco. Si está ilegible, se avisa y se sigue: que no se
        pueda leer no puede tumbar la lista de trabajos."""
        try:
            return leer_registro(archivo_registro(self.repo, self.data_dir))
        except PublicarError as e:
            _log(f"{archivo_registro(self.repo, self.data_dir)}: {e}")
            return {"sitio": SITIO, "trabajos": {}, "quitados": []}

    def publicados(self) -> dict[str, dict[str, Any]]:
        return dict(self.registro().get("trabajos") or {})

    def esta_publicado(self, job_id: str) -> bool:
        """Del disco, no del registro: lo que decide es si los datos están afuera.

        El registro puede haber quedado atrás si alguien borró la carpeta a mano;
        la carpeta es la que se sube.
        """
        return (dir_demo(self.repo) / job_id).is_dir()

    def en_curso(self) -> Publicacion | None:
        with self._lock:
            return self._actual

    def estado(self) -> dict[str, Any]:
        """Lo que la pantalla necesita en una sola llamada: qué está publicado,
        con qué enlace, y si hay algo corriendo ahora mismo."""
        reg = self.registro()
        with self._lock:
            actual, ultima = self._actual, self._ultima
        return {
            "sitio": reg.get("sitio") or SITIO,
            "publicados": {
                k: {"url": v.get("url"), "publicado_en": v.get("publicado_en"), "despliegue": v.get("despliegue")}
                for k, v in (reg.get("trabajos") or {}).items()
            },
            "corriendo": actual.to_dict() if actual else None,
            "ultima": ultima.to_dict() if ultima else None,
        }

    # --- escritura -------------------------------------------------------------------

    def encolar(self, accion: str, job_id: str, job_dir: Path | None = None) -> Publicacion:
        """Arranca una publicación (o una baja). `RuntimeError` si ya hay una."""
        with self._lock:
            if self._actual is not None:
                raise RuntimeError(
                    f"Ya se está {GERUNDIO.get(self._actual.accion, self._actual.accion)} '{self._actual.id}'. "
                    "Esperá a que termine: se despliega el sitio entero y va uno por vez."
                )
            p = Publicacion(id=job_id, accion=accion)
            self._actual = p
        self.pool.submit(self._run, p, job_dir)
        return p

    def close(self) -> None:
        self.pool.shutdown(wait=False, cancel_futures=True)

    def _run(self, p: Publicacion, job_dir: Path | None) -> None:
        def paso(x: Paso) -> None:
            p.paso, p.total, p.texto = x.n, x.de, x.texto

        _log(f"{p.accion} {p.id} · empieza")
        try:
            if p.accion == PUBLICAR:
                fila = publicar(job_dir or p.id, repo=self.repo, data_dir=self.data_dir, ejecutar=self._ejecutar, paso=paso)
            else:
                fila = quitar(p.id, repo=self.repo, data_dir=self.data_dir, ejecutar=self._ejecutar, paso=paso)
            p.url = fila.get("url")
            p.estado, p.texto = "listo", "listo"
        except (PublicarError, OSError) as e:
            p.estado, p.error = "error", str(e)
        except Exception as e:  # noqa: BLE001 — el error entero va al estado, nunca al log solo
            p.estado, p.error = "error", f"{e.__class__.__name__}: {e}"
        finally:
            p.terminado = _now()
            with self._lock:
                self._actual, self._ultima = None, p
            _log(f"{p.accion} {p.id} · {p.estado}" + (f" · {p.error}" if p.error else ""))
