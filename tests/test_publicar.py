"""Publicar un trabajo a internet y despublicarlo (`kinelab.tools.publicar`).

Todo con `--solo-construir` y con el ejecutor de comandos **inyectado**: ningún
test construye el sitio de verdad ni habla con internet. El trabajo de prueba es
el sintético de `test_exportar_demo.py` (video hecho con ffmpeg, `pose.npz` con
un sujeto que se mueve), así que tampoco depende de ningún clip de nadie.

Lo que cada test cuida:

1. Publicar uno **no saca del índice** a los que ya estaban. Es el bug que el
   encargo 25 nombra: si el índice se armara del argumento en vez del disco,
   publicar el segundo borraría al primero del listado y el archivo seguiría ahí.
2. `--quitar` saca ese y deja a los demás, en disco y en el índice.
3. `publicados.json` queda consistente: quién está afuera, desde cuándo, con qué
   enlace, y a dónde se fue el que se dio de baja.
4. Un id que no existe falla con una frase y **no deja basura**: ni carpeta a
   medias, ni fila en el registro, ni build corrido.
5. `--solo-construir` no toca internet: el CLI de Vercel no se invoca ni una vez.
6. Un token vencido sale como un mensaje con el comando a correr, no como la
   salida cruda del CLI.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from kinelab.tools import publicar as pb
from tests.test_exportar_demo import _trabajo

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="hace falta ffmpeg/ffprobe"
)

ALTO = 160  # el video exportado, chico: acá se prueba el ciclo, no la calidad


class Ejecutor:
    """El ejecutor inyectado: anota qué comandos se pidieron y no corre ninguno.

    `pnpm build` deja un `web/out/` de mentira —`construir()` comprueba que el
    build haya dejado algo, y tiene que seguir comprobándolo— y `vercel deploy`
    imprime una URL como la imprime el de verdad.
    """

    def __init__(self, repo: Path, *, falla: str | None = None, salida_falla: str = "", codigo: int = 1) -> None:
        self.repo = repo
        self.falla = falla  # subcadena del comando que tiene que fallar
        self.salida_falla = salida_falla
        self.codigo = codigo
        self.cmds: list[list[str]] = []
        self.envs: list[dict[str, str]] = []

    def __call__(self, cmd: list[str], cwd: Path, env: dict[str, str]) -> pb.Corrida:
        self.cmds.append(list(cmd))
        self.envs.append(dict(env))
        linea = " ".join(cmd)
        if self.falla and self.falla in linea:
            return pb.Corrida(cmd=cmd, codigo=self.codigo, salida="", error=self.salida_falla)
        if "build" in cmd and cmd[-1] == "build":
            out = self.repo / "web" / "out"
            (out / "_next").mkdir(parents=True, exist_ok=True)
            (out / "index.html").write_text("<html>kinelab</html>", encoding="utf-8")
            (out / "_next" / "app.js").write_text("// js", encoding="utf-8")
            # El sitio estático lleva la demo adentro: `next build` copia `public/`.
            demo = self.repo / pb.DEMO_REL
            if demo.is_dir():
                shutil.copytree(demo, out / "demo", dirs_exist_ok=True)
            return pb.Corrida(cmd=cmd, codigo=0, salida="", error="")
        if "deploy" in cmd:
            return pb.Corrida(cmd=cmd, codigo=0, salida="Inspect: https://vercel.com/x/y\nhttps://kinelab-abc123.vercel.app\n", error="")
        return pb.Corrida(cmd=cmd, codigo=0, salida="", error="")

    @property
    def lineas(self) -> list[str]:
        return [" ".join(c) for c in self.cmds]

    def corrio(self, sub: str) -> bool:
        return any(sub in l for l in self.lineas)


@pytest.fixture(scope="module")
def fuente(tmp_path_factory) -> Path:
    """Un trabajo de `data/exploracion/` sintético, hecho una sola vez."""
    return _trabajo(tmp_path_factory.mktemp("fuente"))


@pytest.fixture
def repo(tmp_path: Path, fuente: Path) -> Path:
    """Un repo de mentira con la forma que el comando espera, y dos trabajos
    distintos en `data/exploracion/` (el mismo contenido con dos ids: lo que se
    prueba es el ciclo de publicar, no la pose)."""
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "package.json").write_text('{"name": "web"}', encoding="utf-8")
    for job_id in ("aaaa1111", "bbbb2222"):
        d = tmp_path / "data" / "exploracion" / job_id
        shutil.copytree(fuente, d)
        meta = json.loads((d / "trabajo.json").read_text(encoding="utf-8"))
        meta["video"] = f"{job_id}.mp4"
        (d / "trabajo.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def _publicar(repo: Path, job_id: str, ej: Ejecutor, **kw):
    return pb.publicar(job_id, repo=repo, solo_construir=True, ejecutar=ej, alto=ALTO, **kw)


def _indice(repo: Path) -> list[str]:
    doc = json.loads((repo / pb.DEMO_REL / "index.json").read_text(encoding="utf-8"))
    return [t["id"] for t in doc["trabajos"]]


def _registro(repo: Path) -> dict:
    return json.loads((repo / "data" / pb.PUBLICADOS).read_text(encoding="utf-8"))


# --- 1 · publicar uno, y después otro ----------------------------------------------


def test_publicar_deja_los_archivos_el_indice_y_el_registro(repo):
    ej = Ejecutor(repo)
    fila = _publicar(repo, "aaaa1111", ej)

    d = repo / pb.DEMO_REL / "aaaa1111"
    assert d.is_dir()
    assert {p.name for p in d.iterdir()} >= {"video.mp4", "transformacion.json", "pose.json", "trabajo.json", "capture.json"}
    assert _indice(repo) == ["aaaa1111"]

    reg = _registro(repo)
    assert reg["schema"] == pb.ESQUEMA_PUBLICADOS
    assert list(reg["trabajos"]) == ["aaaa1111"]
    assert reg["trabajos"]["aaaa1111"]["url"].endswith("/?trabajo=aaaa1111")
    assert reg["trabajos"]["aaaa1111"]["video"] == "aaaa1111.mp4"
    assert reg["trabajos"]["aaaa1111"]["publicado_en"] and reg["actualizado"]
    assert fila["bytes"] > 0 and fila["archivos"] >= 5


def test_publicar_el_segundo_no_saca_del_indice_al_primero(repo):
    """El bug que nombra el encargo: el índice sale del **conjunto en disco**.

    `exportar_demo.escribir_indice` recorre la carpeta de salida, así que el
    trabajo que ya estaba sigue listado. Si algún día alguien lo arma de los
    argumentos, este test se pone rojo: publicar el segundo dejaría al primero
    en disco pero invisible, que es la peor de las dos fallas (el dato sigue
    afuera y el registro dice otra cosa).
    """
    ej = Ejecutor(repo)
    _publicar(repo, "aaaa1111", ej)
    _publicar(repo, "bbbb2222", ej)

    assert sorted(_indice(repo)) == ["aaaa1111", "bbbb2222"]
    assert (repo / pb.DEMO_REL / "aaaa1111" / "video.mp4").is_file(), "el primero sigue en disco"
    assert sorted(_registro(repo)["trabajos"]) == ["aaaa1111", "bbbb2222"]


def test_publicar_dos_veces_el_mismo_conserva_desde_cuando_esta_afuera(repo):
    """Re-exportar un trabajo ya publicado no reinicia su fecha: lo que importa es
    desde cuándo está afuera, no cuándo se lo volvió a subir.

    La fecha vieja se escribe a mano y no se toma de una primera publicación: con
    `_ahora()` al segundo, las dos caerían en el mismo segundo y el test pasaría
    aunque el campo se reescribiera (medido: la mutación se escapaba).
    """
    ej = Ejecutor(repo)
    _publicar(repo, "aaaa1111", ej)
    viejo = "2026-01-02T03:04:05+00:00"
    reg_p = repo / "data" / pb.PUBLICADOS
    reg = json.loads(reg_p.read_text(encoding="utf-8"))
    reg["trabajos"]["aaaa1111"]["publicado_en"] = viejo
    reg_p.write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")

    de_nuevo = _publicar(repo, "aaaa1111", ej)
    assert de_nuevo["publicado_en"] == viejo, "desde cuándo está afuera no se reescribe"
    assert de_nuevo["actualizado_en"] != viejo, "cuándo se re-exportó, sí"
    assert _indice(repo) == ["aaaa1111"], "no se duplica"


# --- 2 · quitar ---------------------------------------------------------------------


def test_quitar_saca_ese_y_deja_a_los_demas(repo):
    ej = Ejecutor(repo)
    _publicar(repo, "aaaa1111", ej)
    _publicar(repo, "bbbb2222", ej)

    fila = pb.quitar("aaaa1111", repo=repo, solo_construir=True, ejecutar=ej)

    assert not (repo / pb.DEMO_REL / "aaaa1111").exists(), "los datos salen del disco"
    assert (repo / pb.DEMO_REL / "bbbb2222" / "video.mp4").is_file()
    assert _indice(repo) == ["bbbb2222"]

    reg = _registro(repo)
    assert list(reg["trabajos"]) == ["bbbb2222"]
    assert [q["id"] for q in reg["quitados"]] == ["aaaa1111"]
    assert fila["quitado_en"] and reg["quitados"][0]["publicado_en"], (
        "el registro conserva que estuvo afuera y desde cuándo: publicar no se deshace, se revierte"
    )


def test_quitar_y_volver_a_publicar_lo_saca_de_los_quitados(repo):
    ej = Ejecutor(repo)
    _publicar(repo, "aaaa1111", ej)
    pb.quitar("aaaa1111", repo=repo, solo_construir=True, ejecutar=ej)
    _publicar(repo, "aaaa1111", ej)
    reg = _registro(repo)
    assert list(reg["trabajos"]) == ["aaaa1111"]
    assert reg["quitados"] == [], "no puede estar publicado y quitado a la vez"


def test_quitar_lo_que_no_esta_publicado_falla_y_no_toca_nada(repo):
    ej = Ejecutor(repo)
    _publicar(repo, "aaaa1111", ej)
    antes = _registro(repo)
    ej2 = Ejecutor(repo)
    with pytest.raises(pb.PublicarError) as e:
        pb.quitar("no-existe", repo=repo, solo_construir=True, ejecutar=ej2)
    assert "no está publicado" in str(e.value) and "aaaa1111" in str(e.value), "dice cuáles sí lo están"
    assert _registro(repo) == antes and _indice(repo) == ["aaaa1111"]
    assert ej2.cmds == [], "ni siquiera se construyó"


# --- 3 · un id que no existe ---------------------------------------------------------


def test_publicar_un_id_inexistente_falla_sin_dejar_basura(repo):
    ej = Ejecutor(repo)
    _publicar(repo, "aaaa1111", ej)
    ej2 = Ejecutor(repo)
    with pytest.raises(pb.PublicarError) as e:
        _publicar(repo, "no-existe", ej2)
    assert "no existe" in str(e.value)
    assert not (repo / pb.DEMO_REL / "no-existe").exists(), "no queda una carpeta a medias"
    assert _indice(repo) == ["aaaa1111"] and list(_registro(repo)["trabajos"]) == ["aaaa1111"]
    assert ej2.cmds == [], "no se construye ni se despliega lo que no se pudo exportar"


def test_publicar_un_trabajo_sin_pose_falla_con_la_razon_del_exportador(repo):
    d = repo / "data" / "exploracion" / "cccc3333"
    d.mkdir(parents=True)
    (d / "trabajo.json").write_text('{"estado": "listo"}', encoding="utf-8")
    with pytest.raises(pb.PublicarError) as e:
        _publicar(repo, "cccc3333", Ejecutor(repo))
    assert "capture.json" in str(e.value), "la frase es la del exportador, no un stacktrace"


# --- 4 · construir y desplegar -------------------------------------------------------


def test_solo_construir_no_toca_internet(repo):
    ej = Ejecutor(repo)
    fila = _publicar(repo, "aaaa1111", ej)
    assert ej.corrio("build"), "el sitio sí se construye"
    assert not ej.corrio("vercel"), "el CLI de Vercel no se invoca ni una vez"
    assert ej.envs[0]["NEXT_PUBLIC_KINELAB_MODO"] == "demo", "sin la variable el build sale en modo local"
    assert fila["despliegue"] is None and "no se desplegó" in fila["despliegue_null_reason"]


def test_lo_que_se_sube_es_el_arbol_que_se_armo_aca(repo):
    """`web/.vercel/output/` con la Build Output API v3: `static/` + `config.json`.

    Con `--prebuilt`, `web/vercel.json` no se aplica, así que el `noindex` tiene
    que estar acá o no existe en internet.
    """
    _publicar(repo, "aaaa1111", Ejecutor(repo))
    salida = repo / pb.SALIDA_REL
    assert (salida / "static" / "index.html").is_file()
    assert (salida / "static" / "demo" / "aaaa1111" / "video.mp4").is_file(), "los datos publicados van adentro del árbol"
    cfg = json.loads((salida / "config.json").read_text(encoding="utf-8"))
    assert cfg["version"] == 3
    assert cfg["routes"][0]["headers"]["X-Robots-Tag"] == "noindex, nofollow"


def test_publicar_de_verdad_vincula_y_despliega_con_prebuilt(repo):
    ej = Ejecutor(repo)
    fila = pb.publicar("aaaa1111", repo=repo, solo_construir=False, ejecutar=ej, alto=ALTO)
    assert ej.corrio("link --yes --project kinelab --scope hernandiazz9s-projects")
    assert ej.corrio("deploy --prebuilt --prod --yes")
    assert fila["despliegue"] == "https://kinelab-abc123.vercel.app", "la URL del deploy queda anotada"
    assert _registro(repo)["trabajos"]["aaaa1111"]["despliegue"] == fila["despliegue"]


def test_no_se_vuelve_a_vincular_si_ya_esta_vinculado(repo):
    (repo / "web" / ".vercel").mkdir(parents=True)
    (repo / "web" / ".vercel" / "project.json").write_text('{"projectId": "x"}', encoding="utf-8")
    ej = Ejecutor(repo)
    pb.publicar("aaaa1111", repo=repo, solo_construir=False, ejecutar=ej, alto=ALTO)
    assert not ej.corrio("link"), "vincular es una vez por máquina"


def test_token_vencido_es_una_frase_con_el_comando(repo):
    ej = Ejecutor(repo, falla="deploy", salida_falla="Error: No existing credentials found. Please run `vercel login`.")
    with pytest.raises(pb.PublicarError) as e:
        pb.publicar("aaaa1111", repo=repo, solo_construir=False, ejecutar=ej, alto=ALTO)
    msg = str(e.value)
    assert "no está autenticado" in msg and "login" in msg
    assert "Traceback" not in msg
    # Y lo ya hecho no se pierde: los datos quedaron exportados y anotados, así
    # que reintentar el deploy no vuelve a exportar nada.
    assert _indice(repo) == ["aaaa1111"] and list(_registro(repo)["trabajos"]) == ["aaaa1111"]


def test_build_roto_no_despliega(repo):
    ej = Ejecutor(repo, falla="build", salida_falla="Type error: algo no compila")
    with pytest.raises(pb.PublicarError) as e:
        pb.publicar("aaaa1111", repo=repo, solo_construir=False, ejecutar=ej, alto=ALTO)
    assert "pnpm build" in str(e.value) and "no compila" in str(e.value)
    assert not ej.corrio("deploy"), "un sitio que no construye no sale a internet"


# --- 5 · el registro -----------------------------------------------------------------


def test_publicados_lee_el_registro(repo):
    ej = Ejecutor(repo)
    assert pb.publicados(repo) == {}
    _publicar(repo, "aaaa1111", ej)
    p = pb.publicados(repo)
    assert list(p) == ["aaaa1111"] and p["aaaa1111"]["url"].endswith("?trabajo=aaaa1111")


def test_un_registro_ilegible_no_se_pisa(repo):
    (repo / "data").mkdir(exist_ok=True)
    (repo / "data" / pb.PUBLICADOS).write_text("{esto no es json", encoding="utf-8")
    with pytest.raises(pb.PublicarError) as e:
        _publicar(repo, "aaaa1111", Ejecutor(repo))
    assert "ilegible" in str(e.value)
    assert (repo / "data" / pb.PUBLICADOS).read_text(encoding="utf-8") == "{esto no es json"


def test_el_sitio_se_puede_cambiar(repo):
    fila = _publicar(repo, "aaaa1111", Ejecutor(repo), sitio="https://ejemplo.test/")
    assert fila["url"] == "https://ejemplo.test/?trabajo=aaaa1111"
    assert _registro(repo)["sitio"] == "https://ejemplo.test/"


# --- 6 · la CLI ----------------------------------------------------------------------


def test_cli_publica_y_quita(repo, monkeypatch, capsys):
    ej = Ejecutor(repo)
    monkeypatch.setattr(pb, "raiz_repo", lambda: repo)
    monkeypatch.setattr(pb, "correr", ej)

    assert pb.main(["aaaa1111", "--solo-construir", "--alto", str(ALTO)]) == 0
    out = capsys.readouterr().out
    assert "[1/3]" in out and "[3/3]" in out and "publicado" in out
    assert _indice(repo) == ["aaaa1111"]

    assert pb.main(["aaaa1111", "--quitar", "--solo-construir"]) == 0
    assert "quitado de internet" in capsys.readouterr().out
    assert _indice(repo) == []


def test_cli_de_un_id_que_no_existe_devuelve_2(repo, monkeypatch, capsys):
    monkeypatch.setattr(pb, "raiz_repo", lambda: repo)
    monkeypatch.setattr(pb, "correr", Ejecutor(repo))
    assert pb.main(["no-existe", "--solo-construir"]) == 2
    assert "✗" in capsys.readouterr().err
