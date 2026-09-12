"""`service/`: la API detrás de la página del gate, con el TestClient de FastAPI.

Los clips son los sintéticos de `conftest.py`; el `data/` es un tmp_path con el
YAML de fixture adentro. El archivo viaja como cuerpo crudo de un PUT.
"""

from __future__ import annotations

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
    ]
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
