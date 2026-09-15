"""`service/`: la API detrás de la página del gate, con el TestClient de FastAPI.

Los clips son los sintéticos de `conftest.py`; el `data/` es un tmp_path con el
YAML de fixture adentro. El archivo viaja como cuerpo crudo de un PUT.
"""

from __future__ import annotations

import datetime as dt
import shutil
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from service.app import create_app, safe_filename  # noqa: E402


@pytest.fixture
def data_dir(tmp_path: Path, capture_paths_yaml: Path) -> Path:
    shutil.copy(capture_paths_yaml, tmp_path / "capture-paths.yaml")
    return tmp_path


@pytest.fixture
def client(data_dir: Path):
    with TestClient(create_app(data_dir=data_dir)) as c:
        yield c


def _need(clips: dict[str, Path], key: str) -> Path:
    if key not in clips:
        pytest.skip(f"fixture '{key}' no disponible en esta máquina")
    return clips[key]


def _put(client: TestClient, url: str, clip: Path, **params):
    params.setdefault("filename", clip.name)
    return client.put(url, params=params, content=clip.read_bytes())


INGEST = dict(athlete="test", gesture="driver", view="face_on", day="2026-09-12")


# --- página y config ---------------------------------------------------------


def test_index_is_the_page(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "gate de ingesta" in r.text
    assert "/api/ingest" in r.text


def test_config_lists_sport_and_capture_paths(client, data_dir):
    cfg = client.get("/api/config").json()
    assert cfg["sport"]["id"] == "golf"
    assert cfg["sport"]["views"] == ["face_on", "down_the_line"]
    assert cfg["sport"]["fps_min"] == 100
    assert [p["id"] for p in cfg["capture_paths"]] == [
        "test-hevc-120-cfr", "test-h264-240-cfr", "test-h264-slomo-240-to-30", "test-h264-30-cfr",
        "test-declarado-video", "test-declarado-video-h264", "test-declarado-slomo", "desconocido-video",
    ]
    # La API ofrece los declarados con su bandera: quien elige el camino en la
    # pantalla tiene que poder ver que ése no tiene cronómetro (ADR-016).
    assert {p["id"]: p["calibrated"] for p in cfg["capture_paths"]}["test-declarado-video"] is False
    assert cfg["data_dir"] == str(data_dir.resolve())


def test_config_without_yaml_is_a_500_with_a_message(tmp_path):
    with TestClient(create_app(data_dir=tmp_path)) as c:
        r = c.get("/api/config")
    assert r.status_code == 500
    assert "capture-paths.yaml" in r.json()["detail"]


def test_no_docs_endpoints(client):
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


# --- nombres de archivo ---------------------------------------------------------


@pytest.mark.parametrize(
    "name,expected",
    [
        ("IMG_0412.MOV", ("IMG_0412.MOV", ".mov")),
        ("../../etc/passwd.mov", ("passwd.mov", ".mov")),
        ("C:\\clips\\swing.MP4", ("swing.MP4", ".mp4")),
        ("con espacios.m4v", ("con espacios.m4v", ".m4v")),
    ],
)
def test_safe_filename_keeps_only_the_base_name(name, expected):
    assert safe_filename(name) == expected


@pytest.mark.parametrize("name", ["", "sinextension", ".mov", "..", "a.", "a.toolongext", "a.m/v", "clip.mov/"])
def test_safe_filename_rejects(name):
    with pytest.raises(HTTPException) as e:
        safe_filename(name)
    assert e.value.status_code == 400


# --- fps-truth ------------------------------------------------------------------


def test_fps_truth_upload_reports_stretch(client, clips, data_dir):
    r = _put(client, "/api/fps-truth", clips["slowed30_h264"], real_duration_s=4.0, nominal_fps=240)
    assert r.status_code == 200, r.text
    t = r.json()
    assert t["verdict"] == "estirado"
    assert t["counted"]["frames_decoded"] == 960
    assert t["stretch_factor"] == pytest.approx(8.0, abs=0.05)
    assert t["path"] == "slowed30.mp4"
    assert not list((data_dir / "incoming").glob("*")), "el temporal se borra"


def test_fps_truth_without_real_duration(client, clips):
    t = _put(client, "/api/fps-truth", clips["real240_h264"]).json()
    assert t["verdict"] == "sin_duracion_real"
    assert t["fps_capture"] is None


def test_fps_truth_rejects_non_video(client, tmp_path):
    bogus = tmp_path / "texto.mov"
    bogus.write_text("esto no es un video", encoding="utf-8")
    r = _put(client, "/api/fps-truth", bogus)
    assert r.status_code == 422
    assert "ffprobe" in r.json()["detail"]


def test_fps_truth_rejects_empty_body(client):
    r = client.put("/api/fps-truth", params={"filename": "vacio.mov"}, content=b"")
    assert r.status_code == 400
    assert "vacío" in r.json()["detail"]


def test_fps_truth_rejects_bad_duration(client, clips):
    r = _put(client, "/api/fps-truth", clips["real240_h264"], real_duration_s=0)
    assert r.status_code == 422


# --- ingest ----------------------------------------------------------------------


def test_ingest_ok_end_to_end(client, clips, data_dir):
    src = _need(clips, "hevc120")
    r = _put(client, "/api/ingest", src, capture_path_id="test-hevc-120-cfr", **INGEST)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["take_dir"] == "sessions/test/2026-09-12/driver/face_on/take-01"
    c = body["capture"]
    assert c["gate"]["verdict"] == "ok"
    assert c["original_name"] == "hevc120.mov"
    assert c["fps_real"] == 120.0
    take = data_dir / body["take_dir"]
    assert (take / "original.mov").is_file()
    assert (take / "capture.json").is_file()
    assert not list((data_dir / "incoming").glob("*")), "el temporal se borra"


def test_ingest_reject_is_still_200_with_reasons(client, clips, data_dir):
    r = _put(client, "/api/ingest", clips["real240_h264"], capture_path_id="test-hevc-120-cfr", **INGEST)
    assert r.status_code == 200
    c = r.json()["capture"]
    assert c["gate"]["verdict"] == "reject"
    assert any("H.264" in reason for reason in c["gate"]["reasons"])
    assert (data_dir / r.json()["take_dir"] / "capture.json").is_file(), "un rechazo también deja la sesión"


def test_ingest_twice_gives_take_02(client, clips):
    a = _put(client, "/api/ingest", clips["real240_h264"], capture_path_id="test-h264-240-cfr", **INGEST).json()
    b = _put(client, "/api/ingest", clips["real240_h264"], capture_path_id="test-h264-240-cfr", **INGEST).json()
    assert a["take_dir"].endswith("take-01")
    assert b["take_dir"].endswith("take-02")


def test_ingest_unknown_path_rejects_by_capture_path_known(client, clips):
    c = _put(client, "/api/ingest", clips["real240_h264"], capture_path_id="no-calibrado", **INGEST).json()["capture"]
    assert c["gate"]["verdict"] == "reject"
    assert c["gate"]["checks"][0]["id"] == "capture_path_known"
    assert c["gate"]["checks"][0]["passed"] is False
    assert c["fps_real"] is None


def test_ingest_bad_slug_is_400_before_reading_the_body(client, clips, data_dir):
    r = _put(client, "/api/ingest", clips["real240_h264"], capture_path_id="test-h264-240-cfr", **dict(INGEST, athlete="Hernán"))
    assert r.status_code == 400
    assert "inválido" in r.json()["detail"]
    assert not (data_dir / "sessions").exists()
    assert not (data_dir / "incoming").exists(), "no se creó ni el temporal"


def test_ingest_bad_view_goes_through_the_gate(client, clips):
    """`side` es un slug válido pero no una vista de golf: lo decide el gate, no el servicio."""
    c = _put(client, "/api/ingest", clips["real240_h264"], capture_path_id="test-h264-240-cfr", **dict(INGEST, view="side")).json()["capture"]
    assert c["gate"]["verdict"] == "reject"
    assert any(ch["id"] == "view_declared" and ch["passed"] is False for ch in c["gate"]["checks"])


def test_ingest_bad_filename_is_400(client, clips):
    r = _put(client, "/api/ingest", clips["real240_h264"], filename="sinextension", capture_path_id="test-h264-240-cfr", **INGEST)
    assert r.status_code == 400


def test_ingest_missing_params_is_422(client, clips):
    r = client.put("/api/ingest", params={"filename": "a.mov"}, content=b"x")
    assert r.status_code == 422


def test_ingest_bad_date_is_422(client, clips):
    r = _put(client, "/api/ingest", clips["real240_h264"], capture_path_id="test-h264-240-cfr", **dict(INGEST, day="ayer"))
    assert r.status_code == 422


def test_ingest_filename_with_directories_is_flattened(client, clips, data_dir):
    r = _put(client, "/api/ingest", clips["real240_h264"], filename="../../fuera/IMG_9.MOV", capture_path_id="test-h264-240-cfr", **INGEST)
    assert r.status_code == 200
    c = r.json()["capture"]
    assert c["original_name"] == "IMG_9.MOV"
    assert (data_dir / r.json()["take_dir"] / "original.mov").is_file()
    assert not (data_dir.parent / "fuera").exists()


def test_ingest_non_video_is_422_and_leaves_nothing(client, tmp_path, data_dir):
    bogus = tmp_path / "texto.mov"
    bogus.write_text("esto no es un video", encoding="utf-8")
    r = _put(client, "/api/ingest", bogus, capture_path_id="test-h264-240-cfr", **INGEST)
    assert r.status_code == 422
    assert not (data_dir / "sessions").exists()
    assert not list((data_dir / "incoming").glob("*"))


# --- sessions ---------------------------------------------------------------------


def test_sessions_empty_then_listed(client, clips, data_dir):
    assert client.get("/api/sessions").json() == []
    _put(client, "/api/ingest", clips["real240_h264"], capture_path_id="test-h264-240-cfr", **INGEST)
    _put(client, "/api/ingest", clips["real240_h264"], capture_path_id="test-hevc-120-cfr", **INGEST)
    rows = client.get("/api/sessions").json()
    assert [r["take_dir"].rsplit("/", 1)[1] for r in rows] == ["take-01", "take-02"]
    assert rows[0]["verdict"] == "ok" and rows[0]["reasons"] == []
    assert rows[1]["verdict"] == "reject" and rows[1]["reasons"]
    assert rows[0]["day"] == "2026-09-12"
    assert rows[0]["athlete"] == "test"


def test_sessions_reports_unreadable_capture_json(client, data_dir):
    take = data_dir / "sessions" / "x" / "2026-09-12" / "driver" / "face_on" / "take-01"
    take.mkdir(parents=True)
    (take / "capture.json").write_text("{esto no es json", encoding="utf-8")
    rows = client.get("/api/sessions").json()
    assert len(rows) == 1
    assert "ilegible" in rows[0]["error"]


# --- exploración: PUT /api/datos → GET /api/datos/{id} → archivos ------------------


@pytest.fixture
def client_datos(data_dir: Path):
    from tests.test_perception import FakeEstimator

    with TestClient(create_app(data_dir=data_dir, estimator=FakeEstimator(True))) as c:
        yield c


class _EstimadorQueEspera:
    """El estimador falso, frenado en el primer cuadro por un `Event`.

    Deja mirar el trabajo con la pose a medio correr sin dormir un tiempo fijo:
    el test espera a `empezo`, revisa, y recién ahí suelta `seguir`.
    """

    def __init__(self) -> None:
        import threading

        from tests.test_perception import FakeEstimator

        self._real = FakeEstimator(True)
        self.empezo = threading.Event()
        self.seguir = threading.Event()

    def reset(self):
        self._real.reset()

    def provenance(self):
        return self._real.provenance()

    def __call__(self, frame):
        self.empezo.set()
        self.seguir.wait(timeout=60)
        return self._real(frame)


class _EstimadorDeSwing:
    """Devuelve, cuadro a cuadro, el swing sintético de `tests/helpers/synth_swing.py`.

    El video sólo aporta la cantidad de cuadros. Es la única forma de ver una
    métrica CON número a través del servicio: con el estimador quieto no hay
    ninguna repetición, y sin repeticiones no hay métricas de ningún tipo.
    """

    def __init__(self, fps: float) -> None:
        from tests.helpers.synth_swing import synth_swing

        self.swing = synth_swing(fps, n_reps=1)
        self.i = 0

    def reset(self) -> None:
        self.i = 0

    def provenance(self) -> dict:
        return {"model": "swing sintético", "provider": "falso"}

    def __call__(self, frame):
        import numpy as np

        from kinelab.perception.estimator import FrameEstimate

        i = min(self.i, self.swing.keypoints.shape[0] - 1)
        self.i += 1
        k, sc = self.swing.keypoints[i], self.swing.scores[i]
        (x0, y0), (x1, y1) = np.nanmin(k, axis=0), np.nanmax(k, axis=0)
        return FrameEstimate(k[None], sc[None], np.array([[x0, y0, x1, y1]], np.float32), True)


@pytest.fixture
def client_datos_swing(data_dir: Path):
    with TestClient(create_app(data_dir=data_dir, estimator=_EstimadorDeSwing(120.0))) as c:
        yield c


@pytest.fixture
def client_datos_lento(data_dir: Path):
    """El cliente con un estimador que se frena en el primer cuadro; devuelve
    `(cliente, estimador)` para poder soltarlo."""
    est = _EstimadorQueEspera()
    with TestClient(create_app(data_dir=data_dir, estimator=est)) as c:
        try:
            yield c, est
        finally:
            est.seguir.set()


def _wait(client: TestClient, job_id: str, timeout_s: float = 120.0) -> dict:
    import time

    t0 = time.monotonic()
    while True:
        j = client.get(f"/api/datos/{job_id}").json()
        if j["estado"] in ("listo", "error"):
            return j
        assert time.monotonic() - t0 < timeout_s, f"el trabajo no terminó: {j}"
        time.sleep(0.2)


def test_datos_end_to_end(client_datos, clips, data_dir):
    src = _need(clips, "hevc120")
    r = _put(client_datos, "/api/datos", src, altura_m=1.8)
    assert r.status_code == 202, r.text
    j0 = r.json()
    assert j0["estado"] == "en_cola" and j0["video"] == "hevc120.mov" and j0["altura_m"] == 1.8 and j0["resumen"] is None
    j = _wait(client_datos, j0["id"])
    assert j["estado"] == "listo", j["error"]
    assert j["progreso"]["total"] == 480 and j["progreso"]["cuadros"] == 480, "el dibujo reporta su progreso hasta el último cuadro"
    assert j["segundos"] is not None and j["terminado"] is not None
    res = j["resumen"]
    assert res["cuadros"] == 480 and res["fps_archivo"] == 120.0 and res["altura_m"] == 1.8
    assert "EXPLORACIÓN" in res["aviso"]
    assert "elbow_left_deg" in res["columnas"]
    assert set(j["archivos"]) >= {"overlay.mp4", "datos-por-cuadro.csv", "datos-eventos.json", "analysis.json", "capture.json"}
    assert j["archivos"]["overlay.mp4"] == f"/api/datos/{j['id']}/archivos/overlay.mp4"
    job_dir = data_dir / "exploracion" / j["id"]
    assert (job_dir / "trabajo.json").is_file()
    assert not (job_dir / "subida").exists(), "la subida temporal se borra"
    assert not list((data_dir / "incoming").glob("*"))


def test_datos_files_are_served_with_range(client_datos, clips):
    src = _need(clips, "hevc120")
    j = _wait(client_datos, _put(client_datos, "/api/datos", src).json()["id"])
    assert j["estado"] == "listo", j["error"]
    base = f"/api/datos/{j['id']}/archivos"

    full = client_datos.get(f"{base}/overlay.mp4")
    assert full.status_code == 200 and full.headers["content-type"] == "video/mp4"
    assert full.headers.get("accept-ranges") == "bytes"
    size = int(full.headers["content-length"])

    part = client_datos.get(f"{base}/overlay.mp4", headers={"Range": "bytes=10-19"})
    assert part.status_code == 206, "arrastrar la línea de tiempo necesita 206"
    assert part.headers["content-range"] == f"bytes 10-19/{size}"
    assert part.content == full.content[10:20]

    csv = client_datos.get(f"{base}/datos-por-cuadro.csv")
    assert csv.status_code == 200 and csv.headers["content-type"].startswith("text/csv")
    assert csv.text.splitlines()[0].startswith("frame,t_s,")
    assert len(csv.text.splitlines()) == 481

    dl = client_datos.get(f"{base}/datos-eventos.json", params={"descargar": "true"})
    assert dl.status_code == 200
    assert dl.headers["content-disposition"].startswith("attachment")
    assert "hevc120-datos-eventos.json" in dl.headers["content-disposition"]
    assert dl.json()["cuadros"] == 480


def test_datos_unknown_file_and_traversal_are_404(client_datos, clips):
    src = _need(clips, "hevc120")
    j = _wait(client_datos, _put(client_datos, "/api/datos", src).json()["id"])
    base = f"/api/datos/{j['id']}/archivos"
    assert client_datos.get(f"{base}/pose.npz").status_code == 404, "sólo la lista blanca se sirve"
    assert client_datos.get(f"{base}/trabajo.json").status_code == 404
    assert client_datos.get(f"{base}/..%2Ftrabajo.json").status_code == 404
    assert client_datos.get(f"{base}/../../capture-paths.yaml").status_code == 404


def test_datos_unknown_job_is_404(client_datos):
    assert client_datos.get("/api/datos/no-existe").status_code == 404
    assert client_datos.get("/api/datos/" + "0" * 32).status_code == 404
    assert client_datos.get("/api/datos/" + "0" * 32 + "/archivos/overlay.mp4").status_code == 404


def test_datos_bad_input_leaves_nothing(client_datos, clips, data_dir):
    src = _need(clips, "hevc120")
    assert _put(client_datos, "/api/datos", src, altura_m=0.1).status_code == 422
    assert _put(client_datos, "/api/datos", src, vista="side").status_code == 400
    assert client_datos.put("/api/datos", params={"filename": "vacio.mov"}, content=b"").status_code == 400
    assert _put(client_datos, "/api/datos", src, filename="sinextension").status_code == 400
    assert not list((data_dir / "exploracion").glob("*")) if (data_dir / "exploracion").exists() else True


def test_datos_error_is_reported_not_raised(client_datos, tmp_path):
    bogus = tmp_path / "texto.mov"
    bogus.write_text("esto no es un video", encoding="utf-8")
    r = _put(client_datos, "/api/datos", bogus)
    assert r.status_code == 202
    j = _wait(client_datos, r.json()["id"])
    assert j["estado"] == "error" and j["error"]
    assert j["resumen"] is None


def test_datos_survive_a_restart(client_datos, clips, data_dir):
    from tests.test_perception import FakeEstimator

    src = _need(clips, "hevc120")
    j = _wait(client_datos, _put(client_datos, "/api/datos", src).json()["id"])
    assert j["estado"] == "listo"
    # Un trabajo a medias al reiniciar queda en error con una razón legible.
    half = data_dir / "exploracion" / ("a" * 32)
    half.mkdir()
    (half / "trabajo.json").write_text('{"id": "%s", "video": "x.mov", "creado": "2026-09-12T00:00:00+00:00", "estado": "detectando_pose"}' % ("a" * 32), encoding="utf-8")
    with TestClient(create_app(data_dir=data_dir, estimator=FakeEstimator(True))) as c2:
        again = c2.get(f"/api/datos/{j['id']}").json()
        assert again["estado"] == "listo" and again["resumen"]["cuadros"] == 480
        assert c2.get(f"/api/datos/{j['id']}/archivos/overlay.mp4").status_code == 200
        h = c2.get("/api/datos/" + "a" * 32).json()
        assert h["estado"] == "error" and "reinició" in h["error"]


# --- exploración: la lista de trabajos anteriores y ejemplos -----------------------


def _carpeta(data_dir: Path, job_id: str, resumen: dict | None = None, **campos) -> Path:
    """Un trabajo armado a mano en disco, como el que deja otro proceso."""
    import json

    d = data_dir / "exploracion" / job_id
    d.mkdir(parents=True)
    (d / "trabajo.json").write_text(json.dumps({"estado": "listo", **campos}, ensure_ascii=False), encoding="utf-8")
    if resumen is not None:
        (d / "datos-eventos.json").write_text(json.dumps(resumen, ensure_ascii=False), encoding="utf-8")
    return d


def test_datos_lista_vacia_y_despues_del_mas_nuevo_al_mas_viejo(client_datos, data_dir):
    assert client_datos.get("/api/datos").json() == []
    _carpeta(data_dir, "b" * 32, video="viejo.mp4", creado="2026-09-10T10:00:00+00:00")
    _carpeta(data_dir, "c" * 32, video="nuevo.mp4", creado="2026-09-13T10:00:00+00:00")
    _carpeta(data_dir, "d" * 32, video="medio.mp4", creado="2026-09-12T10:00:00+00:00")
    filas = client_datos.get("/api/datos").json()
    assert [f["video"] for f in filas] == ["nuevo.mp4", "medio.mp4", "viejo.mp4"], "del más nuevo al más viejo"
    assert all(f["origen"] == "subida" for f in filas), "un trabajo.json sin origen es una subida"
    assert filas[0]["id"] == "c" * 32


def test_datos_lista_un_ejemplo_de_otro_proceso(client_datos, clips, data_dir):
    """El ejemplo aparece sin reiniciar, con su etiqueta, y se abre como cualquier trabajo."""
    src = _need(clips, "hevc120")
    j = _wait(client_datos, _put(client_datos, "/api/datos", src, altura_m=1.75).json()["id"])
    assert j["estado"] == "listo", j["error"]
    assert j["origen"] == "subida" and j["etiqueta"] is None

    # Copiado de un trabajo real, con su trabajo.json escrito a mano: sin campo
    # `id` (el id es la carpeta) y con el texto del rótulo. La fecha es relativa
    # a `now` y no literal: con una fecha quemada el ejemplo deja de ser el más
    # nuevo apenas pasa ese día y la lista se da vuelta sola.
    etiqueta = "ejemplo · mocap CMU 64_01 · cámara virtual · no es video"
    creado = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=1)).isoformat(timespec="seconds")
    ejemplo = data_dir / "exploracion" / "ejemplo-cmu-64_01-face_on"
    shutil.copytree(data_dir / "exploracion" / j["id"], ejemplo)
    (ejemplo / "trabajo.json").write_text(
        '{"estado": "listo", "origen": "ejemplo", "video": "cmu-64_01-face_on", "vista": "face_on",'
        ' "altura_m": 1.75, "creado": "%s", "etiqueta": "%s"}' % (creado, etiqueta),
        encoding="utf-8",
    )

    filas = client_datos.get("/api/datos").json()
    assert [f["origen"] for f in filas] == ["ejemplo", "subida"], "el ejemplo es más nuevo"
    fila = filas[0]
    assert fila["id"] == "ejemplo-cmu-64_01-face_on" and fila["etiqueta"] == etiqueta
    assert fila["video"] == "cmu-64_01-face_on" and fila["altura_m"] == 1.75
    assert (fila["fps_archivo"], fila["cuadros"]) == (120.0, 480), "de su datos-eventos.json, no de memoria"

    abierto = client_datos.get(f"/api/datos/{fila['id']}")
    assert abierto.status_code == 200, "un trabajo que apareció después del arranque se abre igual"
    t = abierto.json()
    assert t["origen"] == "ejemplo" and t["etiqueta"] == etiqueta
    assert t["resumen"]["cuadros"] == 480
    assert t["archivos"]["overlay.mp4"] == f"/api/datos/{fila['id']}/archivos/overlay.mp4"
    assert client_datos.get(t["archivos"]["overlay.mp4"]).status_code == 200


def test_datos_lista_trae_fps_y_eventos_solo_si_esta_listo(client_datos, data_dir, tmp_path):
    # Los números son los de `cortado.mp4`, para que se lean como en la pantalla.
    _carpeta(
        data_dir, "a" * 32, video="cortado.mp4", creado="2026-09-13T10:00:00+00:00", altura_m=1.75, segundos=4.0,
        resumen={"fps_archivo": 29.999, "cuadros": 76, "eventos_frame": {"address": 7, "top": 39, "impact": 44}},
    )
    bogus = tmp_path / "texto.mov"
    bogus.write_text("esto no es un video", encoding="utf-8")
    _wait(client_datos, _put(client_datos, "/api/datos", bogus).json()["id"])

    filas = {f["estado"]: f for f in client_datos.get("/api/datos").json()}
    listo, error = filas["listo"], filas["error"]
    assert listo["fps_archivo"] == 29.999 and listo["cuadros"] == 76
    assert listo["eventos_frame"] == {"address": 7, "top": 39, "impact": 44}
    assert listo["altura_m"] == 1.75 and listo["segundos"] == 4.0
    assert error["fps_archivo"] is None and error["cuadros"] is None and error["eventos_frame"] is None
    assert error["error"], "el error se ve en la lista, sin abrir el trabajo"


def test_datos_lista_saltea_lo_roto_y_lo_registra(client_datos, data_dir, capfd):
    _carpeta(data_dir, "e" * 32, video="bueno.mp4", creado="2026-09-13T10:00:00+00:00")
    roto = data_dir / "exploracion" / ("f" * 32)
    roto.mkdir(parents=True)
    (roto / "trabajo.json").write_text("{esto no es json", encoding="utf-8")
    sin_json = data_dir / "exploracion" / ("0" * 32)
    sin_json.mkdir(parents=True)
    (sin_json / "overlay.mp4").write_bytes(b"x")
    sin_estado = data_dir / "exploracion" / ("1" * 32)
    sin_estado.mkdir(parents=True)
    (sin_estado / "trabajo.json").write_text('{"video": "sin-estado.mp4"}', encoding="utf-8")

    filas = client_datos.get("/api/datos").json()
    assert [f["video"] for f in filas] == ["bueno.mp4"], "lo ilegible y lo que no es un trabajo se saltean"
    log = capfd.readouterr().out
    assert "f" * 32 in log and "1" * 32 in log and "0" * 32 in log, "lo que se saltea queda en el log"
    assert client_datos.get("/api/datos/" + "f" * 32).status_code == 404


def test_datos_borrado_del_disco_desaparece_sin_romper(client_datos, clips, data_dir):
    src = _need(clips, "hevc120")
    j = _wait(client_datos, _put(client_datos, "/api/datos", src).json()["id"])
    assert [f["id"] for f in client_datos.get("/api/datos").json()] == [j["id"]]

    shutil.rmtree(data_dir / "exploracion" / j["id"])

    assert client_datos.get("/api/datos").json() == []
    assert client_datos.get(f"/api/datos/{j['id']}").status_code == 404, "el que guardó el navegador ya no está"
    assert client_datos.get(f"/api/datos/{j['id']}/archivos/overlay.mp4").status_code == 404


# --- exploración: el camino de captura y la ficha del archivo ----------------------


def test_datos_camino_declarado_viaja_al_trabajo_y_al_capture(client_datos, clips, data_dir):
    import json

    src = _need(clips, "hevc120")
    j = _wait(client_datos, _put(client_datos, "/api/datos", src, camino="test-declarado-video").json()["id"])
    assert j["estado"] == "listo", j["error"]
    assert j["camino"] == "test-declarado-video"

    guardado = json.loads((data_dir / "exploracion" / j["id"] / "trabajo.json").read_text(encoding="utf-8"))
    assert guardado["camino"] == "test-declarado-video", "el camino queda en disco, no sólo en memoria"
    assert "archivo" not in guardado, "la ficha no se copia al trabajo.json: vive en capture.json"

    capture = client_datos.get(f"/api/datos/{j['id']}/archivos/capture.json").json()
    assert capture["capture_path_id"] == "test-declarado-video"
    assert capture["capture_path_calibrated"] is False
    assert capture["fps_provenance"] == "sin_verificar"
    assert j["resumen"]["camino"] == "test-declarado-video"
    assert j["resumen"]["fps_aviso"], "el aviso del camino declarado, antes de cualquier número (ADR-016)"


def test_datos_camino_por_defecto_es_el_generico(client_datos, clips):
    src = _need(clips, "hevc120")
    j = client_datos.put("/api/datos", params={"filename": src.name}, content=src.read_bytes()).json()
    assert j["camino"] == "desconocido-video", "sin elegir nada, 'no sé con qué se filmó'"
    _wait(client_datos, j["id"])


def test_datos_camino_inexistente_es_400_con_la_lista(client_datos, clips, data_dir):
    src = _need(clips, "hevc120")
    r = _put(client_datos, "/api/datos", src, camino="no-existe-este-camino")
    assert r.status_code == 400
    detalle = r.json()["detail"]
    assert "no-existe-este-camino" in detalle
    assert "test-declarado-video" in detalle and "desconocido-video" in detalle, "dice cuáles hay"
    assert not (data_dir / "exploracion").exists() or not list((data_dir / "exploracion").glob("*"))


def test_datos_slomo_sin_calibrar_es_400_con_la_frase_del_gate(client_datos, clips, data_dir):
    """ADR-016: sin cronómetro el factor de estiramiento es desconocido. No se
    arranca un trabajo cuyo eje de tiempo no se conoce, y la frase es la misma
    que da el gate."""
    from kinelab.ingest.capture_paths import load_capture_paths
    from kinelab.ingest.gate import slomo_declared_reason

    src = _need(clips, "hevc120")
    r = _put(client_datos, "/api/datos", src, camino="test-declarado-slomo")
    assert r.status_code == 400
    esperada = slomo_declared_reason(load_capture_paths(data_dir / "capture-paths.yaml").get("test-declarado-slomo"))
    assert r.json()["detail"] == esperada
    assert "estiramiento es desconocido" in esperada
    assert not (data_dir / "exploracion").exists() or not list((data_dir / "exploracion").glob("*"))


def test_datos_la_ficha_del_archivo_llega_antes_que_la_pose(client_datos_lento, clips):
    """La ficha sale del `capture.json`, que `prepare_take` escribe antes de
    correr el modelo: la pantalla la muestra mientras la pose sigue."""
    client, est = client_datos_lento
    src = _need(clips, "hevc120")
    job_id = _put(client, "/api/datos", src, camino="test-declarado-video").json()["id"]
    assert est.empezo.wait(timeout=60), "el estimador nunca arrancó"

    j = client.get(f"/api/datos/{job_id}").json()
    assert j["estado"] == "detectando_pose", j
    assert j["resumen"] is None, "todavía no hay ningún número derivado"
    a = j["archivo"]
    assert a is not None, "la ficha del archivo ya está"
    assert a["codec"] == "hevc" and a["cuadros"] == 480
    assert a["fps_reproduccion"] == 120.0 and a["rotacion_deg"] == 0 and a["tasa_variable"] is False
    assert a["camino"] == "test-declarado-video" and a["camino_calibrado"] is False
    assert a["fps_provenance"] == "sin_verificar", "la procedencia viaja al lado del fps"

    est.seguir.set()
    fin = _wait(client, job_id)
    assert fin["estado"] == "listo", fin["error"]
    assert fin["archivo"] == a, "la ficha no cambia cuando termina la pose"


def test_datos_ficha_con_el_primer_delta_corregido(client_datos, clips):
    """El clip cuyo primer delta de PTS es el arranque de la cámara: el efectivo
    y el bruto viajan los dos, y `fps_note` explica por qué difieren."""
    src = _need(clips, "first_delta30_h264")
    j = _wait(client_datos, _put(client_datos, "/api/datos", src, camino="test-declarado-video").json()["id"])
    assert j["estado"] == "listo", j["error"]
    a = j["archivo"]
    assert a["fps_reproduccion"] == 30.0 and a["fps_reproduccion_bruto"] < 30.0
    assert a["tasa_variable"] is False and a["vfr_ratio_bruto"] > a["vfr_ratio_max"]
    assert a["primer_delta_s"] > 0.1
    assert a["fps_note"] and "arranque de la cámara" in a["fps_note"]


def test_datos_lista_trae_camino_y_procedencia(client_datos, clips):
    src = _need(clips, "hevc120")
    j = _wait(client_datos, _put(client_datos, "/api/datos", src, camino="test-declarado-video").json()["id"])
    assert j["estado"] == "listo", j["error"]
    fila = client_datos.get("/api/datos").json()[0]
    assert fila["camino"] == "test-declarado-video"
    assert fila["fps_provenance"] == "sin_verificar", "el fps de la fila no se lee sin su procedencia"


def test_datos_analysis_trae_las_metricas_con_su_razon(client_datos_swing, clips):
    """El bloque «Con este archivo» de la pantalla sale de acá: cada métrica del
    registro, con valor y unidad o con la razón por la que no se calculó."""
    src = _need(clips, "hevc120")
    j = _wait(client_datos_swing, _put(client_datos_swing, "/api/datos", src, altura_m=1.75, camino="test-declarado-video").json()["id"])
    assert j["estado"] == "listo", j["error"]
    analysis = client_datos_swing.get(f"/api/datos/{j['id']}/archivos/analysis.json").json()
    assert analysis["header"]["source"]["fps_provenance"] == "sin_verificar"
    assert analysis["warnings"][0].startswith("EXPLORACIÓN")
    metricas = analysis["reps"][0]["metrics"]
    assert len(metricas) == 12
    for id_, m in metricas.items():
        assert set(m) >= {"value", "unit", "view", "mdc", "level", "fps_min", "fps_provenance", "judgment_allowed", "null_reason"}, id_
        assert (m["value"] is None) == (m["null_reason"] is not None), f"{id_}: o hay número, o hay razón"
        assert m["judgment_allowed"] is False, f"{id_}: con la tasa sin verificar nada es juicio (ADR-016)"
    con_numero = {i: m for i, m in metricas.items() if m["value"] is not None}
    assert con_numero, "a 120 fps, con un swing de verdad, alguna métrica tiene que dar un número"
    for id_, m in con_numero.items():
        # Nunca un float solo (invariante 3). `confidence` sigue en null en todo
        # el registro de golf: lo llena la Fase 3, y la pantalla tiene que
        # aguantarlo sin inventar nada.
        assert m["unit"] and m["uncertainty"], f"{id_}: valor sin unidad ni banda"
        assert m["uncertainty"]["method"], id_
    sin_numero = {i: m["null_reason"] for i, m in metricas.items() if m["value"] is None}
    assert any("vista" in r for r in sin_numero.values()), "pelvis_thrust_top_cm sólo vale desde down_the_line"


def test_datos_el_id_es_la_carpeta_y_no_se_sale_de_ella(client_datos, data_dir):
    _carpeta(data_dir, "ejemplo-cmu-64_01-face_on", video="x", id="otro-id-que-se-ignora")
    assert client_datos.get("/api/datos/ejemplo-cmu-64_01-face_on").json()["id"] == "ejemplo-cmu-64_01-face_on"
    for malo in ["..", "..%2F..%2Fcapture-paths.yaml", ".oculto", "con/barra", "a" * 65]:
        assert client_datos.get(f"/api/datos/{malo}").status_code == 404, malo
