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
