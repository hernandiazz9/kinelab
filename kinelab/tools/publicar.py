"""Publicar un trabajo a internet, y despublicarlo. Un trabajo por vez, a mano.

    python -m kinelab.tools.publicar TRABAJO [--quitar] [--solo-construir]

**Publicar es deliberado.** Subir un video a la pantalla local no lo publica:
el motor corre en la Mac del entrenador y los videos son de personas. Que un
trabajo salga a internet es un acto explícito, por trabajo, reversible con
`--quitar`, y anotado en `data/publicados.json` — el único archivo de todo esto
que va a git.

**Lo publicado no va a git.** `web/public/demo/` está en `.gitignore`: veinte
swings serían 300 MB en una historia que no se borra nunca. Lo que viaja con el
repo es el **código** y el **registro de qué se mandó afuera**; los datos salen
del disco de esta Mac directo a Vercel, sin pasar por el repo.

Los cuatro pasos, en orden:

1. **exportar** el trabajo con `kinelab.tools.exportar_demo` a
   `web/public/demo/<id>/`, **sumándolo** a los que ya estaban. El índice se
   arma del conjunto que hay en disco, nunca del argumento: publicar uno nuevo
   no puede borrar del índice a los que ya estaban.
2. **registrar** en `data/publicados.json`: qué trabajo, cuándo y con qué URL.
3. **construir** el estático (`NEXT_PUBLIC_KINELAB_MODO=demo pnpm build` →
   `web/out/`) y armar `web/.vercel/output/` con la Build Output API v3, que es
   exactamente lo que se sube.
4. **desplegar** a producción con el CLI de Vercel (`vercel deploy --prebuilt
   --prod`). El token vive en la config del CLI, nunca acá: este archivo no lo
   lee, no lo escribe y no lo imprime.

`--solo-construir` corre 1, 2 y 3 y para: deja el sitio listo en `web/out/` sin
tocar internet. Es lo que usan los tests, y lo que sirve para mirar el resultado
antes de mandarlo:

    cd web/out && python3 -m http.server 8812

`--quitar ID` hace lo inverso: saca `web/public/demo/<id>/`, reescribe el índice
con los que quedan, anota la fecha en el registro, y vuelve a construir y a
desplegar. Despublicar es tan barato como publicar, a propósito.

**Por qué `--prebuilt` y no dejar que Vercel construya.** Con `--prebuilt` se
sube exactamente el árbol de archivos que se armó acá y que se puede mirar antes
de mandarlo; si el sitio se construyera del repo, los datos tendrían que estar
**en** el repo, que es justamente lo que este comando evita.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kinelab.tools.exportar_demo import ExportError, escribir_indice, exportar

ESQUEMA_PUBLICADOS = "kinelab.publicados/1.0.0"

#: El registro de qué se mandó afuera. **Va a git**: es lo único de todo esto que
#: viaja con el repo.
PUBLICADOS = "publicados.json"

#: Dónde viven los datos publicados. Ignorado por git (ver el encabezado).
DEMO_REL = Path("web/public/demo")

#: La salida de `next build` con `output: export`.
OUT_REL = Path("web/out")

#: Lo que se sube: Build Output API v3 (`static/` + `config.json`).
SALIDA_REL = Path("web/.vercel/output")

#: El sitio donde queda publicado. Es configuración de este repo, no un dato del
#: trabajo: se cambia con `--sitio` o con `KINELAB_SITIO`.
SITIO = "https://kinelab-qnm5fa60a-hernandiazz9s-projects.vercel.app"

#: El proyecto y el equipo de Vercel a los que se vincula `web/` la primera vez.
VERCEL_PROYECTO = "kinelab"
VERCEL_SCOPE = "hernandiazz9s-projects"

#: `noindex` en la respuesta, igual que `web/vercel.json`. Con `--prebuilt` el
#: `vercel.json` no se aplica —la autoridad es `config.json`—, así que la cabecera
#: se escribe acá o no existe. El enlace es para mostrárselo a alguien, no para
#: que lo indexe un buscador.
CABECERA_ROBOTS = {"X-Robots-Tag": "noindex, nofollow"}

TIMEOUT_BUILD_S = 1800
TIMEOUT_DEPLOY_S = 1800


class PublicarError(RuntimeError):
    """No se pudo publicar (o despublicar), con la razón en una frase."""


@dataclass
class Paso:
    """Un paso del proceso, para que la pantalla diga en qué va."""

    n: int
    de: int
    texto: str


#: Qué hacer con cada paso. La CLI lo imprime; el servicio lo guarda en el estado
#: del trabajo para que la pantalla lo muestre.
Progreso = Callable[[Paso], None]


def _nada(_p: Paso) -> None:
    pass


@dataclass
class Corrida:
    """El resultado de correr un comando externo."""

    cmd: list[str]
    codigo: int
    salida: str
    error: str


#: Correr un comando: `(cmd, cwd, env_extra) -> Corrida`. Se inyecta en los tests
#: para no construir el sitio ni hablar con internet (mismo patrón que el
#: estimador falso de `service.exploracion`).
Ejecutor = Callable[[list[str], Path, dict[str, str]], Corrida]


def correr(cmd: list[str], cwd: Path, env_extra: dict[str, str], *, timeout_s: int = TIMEOUT_BUILD_S) -> Corrida:
    """El ejecutor de verdad. Nunca recibe ni imprime credenciales: el token de
    Vercel lo lee su propio CLI de su config, y acá no pasa."""
    env = {**os.environ, **env_extra}
    try:
        r = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=timeout_s)
    except FileNotFoundError as e:
        raise PublicarError(f"No existe el comando `{cmd[0]}`: {e}") from e
    except subprocess.TimeoutExpired as e:
        raise PublicarError(f"`{' '.join(cmd)}` no terminó en {timeout_s} s.") from e
    return Corrida(cmd=list(cmd), codigo=r.returncode, salida=r.stdout or "", error=r.stderr or "")


# --- rutas ---------------------------------------------------------------------------


def raiz_repo() -> Path:
    return Path(__file__).resolve().parents[2]


def dir_demo(repo: Path) -> Path:
    return repo / DEMO_REL


def archivo_registro(repo: Path, data_dir: Path | None = None) -> Path:
    return (data_dir or repo / "data") / PUBLICADOS


def _ahora() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


# --- el registro ---------------------------------------------------------------------


def registro_vacio() -> dict[str, Any]:
    return {
        "schema": ESQUEMA_PUBLICADOS,
        "nota": (
            "Que trabajos estan publicados en internet, desde cuando y con que enlace. Este "
            "archivo SI va a git: es el registro de que se mando afuera. Los datos publicados "
            "NO van a git (web/public/demo/ esta en .gitignore): salen del disco de la Mac al "
            "desplegar. Lo escribe `python -m kinelab.tools.publicar`; a mano, nunca."
        ),
        "sitio": SITIO,
        "actualizado": None,
        "trabajos": {},
        "quitados": [],
    }


def leer_registro(p: Path) -> dict[str, Any]:
    """El registro, o uno vacío si todavía no existe. Un archivo ilegible es un
    error y no se pisa: es el registro de lo que salió a internet."""
    if not p.is_file():
        return registro_vacio()
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        raise PublicarError(f"{p} está ilegible ({e}). No se toca: arreglalo a mano o borralo a sabiendas.") from e
    if not isinstance(d, dict) or "trabajos" not in d:
        raise PublicarError(f"{p} no tiene la forma de un registro de publicados (le falta `trabajos`).")
    d.setdefault("quitados", [])
    return d


def escribir_registro(p: Path, reg: dict[str, Any]) -> None:
    reg["actualizado"] = _ahora()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)


def url_del_trabajo(sitio: str, job_id: str) -> str:
    """El enlace que se le pasa a alguien: la pantalla abierta en ese trabajo.
    Es el mismo `?trabajo=<id>` que usa el modo local (`web/src/lib/api.ts`)."""
    return f"{sitio.rstrip('/')}/?trabajo={job_id}"


# --- construir -----------------------------------------------------------------------


def construir(repo: Path, *, ejecutar: Ejecutor = correr, paso: Progreso = _nada, n: int = 3, de: int = 4) -> Path:
    """`pnpm build` en modo demo → `web/out/`, y de ahí `web/.vercel/output/`.

    Devuelve la carpeta de salida que se sube. Construir es también la
    comprobación de que el sitio **entra**: si el trabajo recién exportado rompe
    el build, se entera acá y no en internet.
    """
    web = repo / "web"
    if not (web / "package.json").is_file():
        raise PublicarError(f"No existe {web}/package.json: ¿está completo el repo?")
    paso(Paso(n, de, "construyendo el sitio (NEXT_PUBLIC_KINELAB_MODO=demo pnpm build)"))
    pnpm = shutil.which("pnpm") or "pnpm"
    r = ejecutar([pnpm, "build"], web, {"NEXT_PUBLIC_KINELAB_MODO": "demo"})
    if r.codigo != 0:
        raise PublicarError(f"`pnpm build` falló ({r.codigo}):\n{_cola(r)}")
    out = repo / OUT_REL
    if not (out / "index.html").is_file():
        raise PublicarError(f"El build terminó bien pero no dejó {out}/index.html. ¿Corrió en modo demo?")
    return armar_salida(repo)


def armar_salida(repo: Path) -> Path:
    """`web/out/` → `web/.vercel/output/` (Build Output API v3).

    Es lo que sube `vercel deploy --prebuilt`: el árbol de archivos exacto que se
    armó acá, sin que nadie lo vuelva a construir del repo. `config.json` lleva
    el `noindex`, porque con `--prebuilt` el `vercel.json` ya no se mira.
    """
    out, salida = repo / OUT_REL, repo / SALIDA_REL
    if salida.exists():
        shutil.rmtree(salida)
    salida.mkdir(parents=True)
    shutil.copytree(out, salida / "static")
    (salida / "config.json").write_text(
        json.dumps(
            {
                "version": 3,
                "routes": [{"src": "/(.*)", "headers": dict(CABECERA_ROBOTS), "continue": True}],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return salida


# --- desplegar -----------------------------------------------------------------------


def comando_vercel() -> list[str]:
    """Con qué se invoca el CLI de Vercel. `KINELAB_VERCEL` gana; después el
    `vercel` del PATH; si no, `npx vercel`, que es como está instalado en esta Mac."""
    if (env := os.environ.get("KINELAB_VERCEL")):
        return shlex.split(env)
    if (w := shutil.which("vercel")):
        return [w]
    if (npx := shutil.which("npx")):
        return [npx, "--yes", "vercel"]
    raise PublicarError(
        "No encuentro el CLI de Vercel ni `npx` para invocarlo. Instalalo con "
        "`npm i -g vercel`, o poné el comando en KINELAB_VERCEL."
    )


#: Lo que dice el CLI cuando el token venció o nunca hubo. Se busca en minúsculas.
_SIN_AUTH = ("not authenticated", "no existing credentials", "please log in", "credentials", "token has expired", "invalid token", "forbidden")


def _cola(r: Corrida, n: int = 1200) -> str:
    txt = (r.error.strip() or r.salida.strip())
    return txt[-n:]


def _revisar_auth(r: Corrida) -> None:
    """Un token vencido tiene que salir como una frase con el comando a correr, no
    como un stacktrace ni como la salida cruda del CLI."""
    txt = (r.salida + "\n" + r.error).lower()
    if any(s in txt for s in _SIN_AUTH):
        raise PublicarError(
            "El CLI de Vercel no está autenticado (o el token venció). Corré:\n"
            f"    {' '.join(comando_vercel())} login\n"
            "y volvé a intentarlo. El token queda en la config del CLI de Vercel; "
            "en este repo no se guarda nunca."
        )


def vincular(repo: Path, *, ejecutar: Ejecutor = correr) -> None:
    """`vercel link` de `web/` al proyecto, si todavía no está vinculado.

    Deja `web/.vercel/project.json`, que está en `web/.gitignore`: es de esta
    máquina, no del repo.
    """
    web = repo / "web"
    if (web / ".vercel" / "project.json").is_file():
        return
    r = ejecutar([*comando_vercel(), "link", "--yes", "--project", VERCEL_PROYECTO, "--scope", VERCEL_SCOPE], web, {})
    if r.codigo != 0:
        _revisar_auth(r)
        raise PublicarError(
            f"`vercel link` falló ({r.codigo}). Vinculá {web} a mano con:\n"
            f"    cd web && {' '.join(comando_vercel())} link --project {VERCEL_PROYECTO} --scope {VERCEL_SCOPE}\n"
            f"{_cola(r)}"
        )


def desplegar(repo: Path, *, ejecutar: Ejecutor = correr, paso: Progreso = _nada, n: int = 4, de: int = 4) -> str:
    """`vercel deploy --prebuilt --prod` desde `web/`. Devuelve la URL del deploy.

    Sube el árbol de `web/.vercel/output/` que armó `construir()`: lo que se ve
    en internet es lo que se miró antes de mandarlo.
    """
    paso(Paso(n, de, "desplegando a producción con el CLI de Vercel"))
    web = repo / "web"
    vincular(repo, ejecutar=ejecutar)
    r = ejecutar([*comando_vercel(), "deploy", "--prebuilt", "--prod", "--yes"], web, {})
    if r.codigo != 0:
        _revisar_auth(r)
        raise PublicarError(f"`vercel deploy` falló ({r.codigo}):\n{_cola(r)}")
    for linea in reversed((r.salida or "").splitlines()):
        if (linea := linea.strip()).startswith("https://"):
            return linea
    return ""


# --- publicar y quitar ---------------------------------------------------------------


def _resolver(trabajo: str | Path, repo: Path, data_dir: Path | None) -> tuple[str, Path]:
    """`(id, carpeta)` a partir de un id o de una ruta a `data/exploracion/<id>`.

    Un id es un nombre suelto (`72d91d03…`); cualquier cosa con una barra es una
    ruta, relativa al repo si no es absoluta. Así el mismo comando sirve desde la
    pantalla (que sólo tiene el id) y desde la terminal (donde se completa con tab).
    """
    p = Path(trabajo)
    if len(p.parts) > 1 or p.is_absolute():
        return p.name, (p if p.is_absolute() else repo / p)
    return p.name, (data_dir or repo / "data") / "exploracion" / p.name


def publicar(
    trabajo: str | Path,
    *,
    repo: Path | None = None,
    data_dir: Path | None = None,
    sitio: str = SITIO,
    solo_construir: bool = False,
    ejecutar: Ejecutor = correr,
    paso: Progreso = _nada,
    **exportar_kwargs: Any,
) -> dict[str, Any]:
    """Un trabajo → internet. Devuelve su fila del registro.

    El orden importa: primero se exporta (que es lo que puede fallar por el
    trabajo), después se registra, y recién ahí se construye y se despliega. Un
    id que no existe no deja nada escrito.
    """
    repo = repo or raiz_repo()
    job_id, d = _resolver(trabajo, repo, data_dir)
    de = 3 if solo_construir else 4

    paso(Paso(1, de, f"exportando {job_id} (recorte al sujeto, reescalado, fotos a JPEG)"))
    out = dir_demo(repo)
    out.mkdir(parents=True, exist_ok=True)
    try:
        r = exportar(d, out, **exportar_kwargs)
    except ExportError as e:
        raise PublicarError(str(e)) from e
    # El índice se arma del conjunto que hay EN DISCO, no de lo que recibió este
    # comando: si saliera del argumento, publicar uno nuevo borraría del índice a
    # los que ya estaban.
    escribir_indice(out)

    paso(Paso(2, de, "anotando en data/publicados.json"))
    reg_p = archivo_registro(repo, data_dir)
    reg = leer_registro(reg_p)
    reg["sitio"] = sitio
    anterior = reg["trabajos"].get(job_id) or {}
    fila = {
        "id": job_id,
        "video": _video_de(out / job_id) or job_id,
        "url": url_del_trabajo(sitio, job_id),
        "publicado_en": anterior.get("publicado_en") or _ahora(),
        "actualizado_en": _ahora(),
        "bytes": r.bytes,
        "archivos": len(r.archivos),
        "tramo_origen": list(r.transformacion["tramo_origen"]),
        "despliegue": anterior.get("despliegue"),
        "despliegue_null_reason": None,
    }
    reg["trabajos"][job_id] = fila
    reg["quitados"] = [q for q in reg["quitados"] if q.get("id") != job_id]
    escribir_registro(reg_p, reg)

    _construir_y_desplegar(repo, reg_p, fila, solo_construir=solo_construir, ejecutar=ejecutar, paso=paso, n=3, de=de)
    return fila


def quitar(
    trabajo: str | Path,
    *,
    repo: Path | None = None,
    data_dir: Path | None = None,
    sitio: str = SITIO,
    solo_construir: bool = False,
    ejecutar: Ejecutor = correr,
    paso: Progreso = _nada,
) -> dict[str, Any]:
    """Saca un trabajo de internet. Devuelve la fila que se dio de baja.

    Lo que se borra son los datos publicados; el registro **conserva** que ese
    trabajo estuvo afuera y desde cuándo hasta cuándo. Publicar no se deshace:
    se revierte.
    """
    repo = repo or raiz_repo()
    job_id = Path(str(trabajo)).name
    out = dir_demo(repo)
    d = out / job_id
    de = 3 if solo_construir else 4

    reg_p = archivo_registro(repo, data_dir)
    reg = leer_registro(reg_p)
    if not d.is_dir():
        publicados = ", ".join(sorted(reg["trabajos"])) or "ninguno"
        raise PublicarError(f"'{job_id}' no está publicado: no existe {d}. Publicados hoy: {publicados}.")

    paso(Paso(1, de, f"sacando {job_id} de {DEMO_REL}"))
    shutil.rmtree(d)
    escribir_indice(out)

    paso(Paso(2, de, "anotando la baja en data/publicados.json"))
    fila = reg["trabajos"].pop(job_id, None) or {"id": job_id, "publicado_en": None, "url": url_del_trabajo(sitio, job_id)}
    fila = {**fila, "quitado_en": _ahora()}
    reg["quitados"] = [q for q in reg["quitados"] if q.get("id") != job_id] + [fila]
    escribir_registro(reg_p, reg)

    _construir_y_desplegar(repo, reg_p, fila, solo_construir=solo_construir, ejecutar=ejecutar, paso=paso, n=3, de=de, en="quitados")
    return fila


def _construir_y_desplegar(
    repo: Path,
    reg_p: Path,
    fila: dict[str, Any],
    *,
    solo_construir: bool,
    ejecutar: Ejecutor,
    paso: Progreso,
    n: int,
    de: int,
    en: str = "trabajos",
) -> None:
    """Los pasos 3 y 4, comunes a publicar y a quitar, con el registro al día."""
    construir(repo, ejecutar=ejecutar, paso=paso, n=n, de=de)
    if solo_construir:
        fila["despliegue"] = None
        fila["despliegue_null_reason"] = "--solo-construir: se armó el sitio y no se desplegó. Nada salió a internet."
        _guardar_fila(reg_p, fila, en)
        return
    url = desplegar(repo, ejecutar=ejecutar, paso=paso, n=n + 1, de=de)
    fila["despliegue"] = url or None
    fila["despliegue_null_reason"] = None if url else "el CLI de Vercel no imprimió ninguna URL"
    _guardar_fila(reg_p, fila, en)


def _guardar_fila(reg_p: Path, fila: dict[str, Any], en: str) -> None:
    reg = leer_registro(reg_p)
    if en == "trabajos":
        reg["trabajos"][fila["id"]] = fila
    else:
        reg["quitados"] = [q for q in reg["quitados"] if q.get("id") != fila["id"]] + [fila]
    escribir_registro(reg_p, reg)


def _video_de(d: Path) -> str | None:
    """El nombre del video del trabajo, del `trabajo.json` exportado: es lo que la
    lista muestra, y sirve para leer el registro sin abrir nada más."""
    p = d / "trabajo.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("video")
    except (ValueError, OSError):
        return None


def publicados(repo: Path | None = None, data_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Qué está publicado ahora mismo, por id. Del registro, que es la verdad de
    qué se mandó afuera."""
    repo = repo or raiz_repo()
    try:
        return dict(leer_registro(archivo_registro(repo, data_dir))["trabajos"])
    except PublicarError:
        return {}


# --- CLI ------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m kinelab.tools.publicar",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("trabajo", help="id del trabajo, o la carpeta data/exploracion/<id>")
    ap.add_argument("--quitar", action="store_true", help="sacarlo de internet en vez de publicarlo")
    ap.add_argument("--solo-construir", action="store_true", help="dejar el sitio listo sin desplegar (no toca internet)")
    ap.add_argument("--sitio", default=os.environ.get("KINELAB_SITIO", SITIO), help=f"URL base del sitio (default: {SITIO})")
    ap.add_argument("--alto", type=int, default=None, help="alto del video exportado, en px (ver exportar_demo)")
    ap.add_argument("--crf", type=int, default=None)
    a = ap.parse_args(argv)

    extra: dict[str, Any] = {}
    if a.alto is not None:
        extra["alto"] = a.alto
    if a.crf is not None:
        extra["crf"] = a.crf

    def imprimir(p: Paso) -> None:
        print(f"[{p.n}/{p.de}] {p.texto}", flush=True)

    try:
        # `ejecutar=correr` explícito y no por default: el default se fija al
        # definir la función, y así los tests pueden reemplazar el ejecutor.
        if a.quitar:
            fila = quitar(a.trabajo, sitio=a.sitio, solo_construir=a.solo_construir, ejecutar=correr, paso=imprimir)
            print(f"\n✓ {fila['id']} quitado de internet.")
        else:
            fila = publicar(a.trabajo, sitio=a.sitio, solo_construir=a.solo_construir, ejecutar=correr, paso=imprimir, **extra)
            print(f"\n✓ {fila['id']} publicado · {fila['bytes'] / 1e6:.2f} MB · {fila['url']}")
    except PublicarError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    if a.solo_construir:
        print(f"  --solo-construir: nada salió a internet. Para mirarlo:\n    cd {OUT_REL} && python3 -m http.server 8812")
    elif fila.get("despliegue"):
        print(f"  deploy: {fila['despliegue']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
