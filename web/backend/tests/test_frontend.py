"""The backend serves the static single-page UI without shadowing the API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_index_is_served(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "chromadose" in resp.text


def test_assets_are_served(client: TestClient) -> None:
    assert client.get("/styles.css").status_code == 200
    js = client.get("/app.js")
    assert js.status_code == 200
    assert "javascript" in js.headers["content-type"]


def test_api_not_shadowed_by_static_mount(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_unknown_api_path_is_404_not_index(client: TestClient) -> None:
    assert client.get("/api/does-not-exist").status_code == 404


def test_api_only_when_frontend_missing(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CHROMADOSE_FRONTEND_DIR", str(tmp_path / "nope"))
    api_only = TestClient(create_app())
    assert api_only.get("/").status_code == 404
    assert api_only.get("/api/health").status_code == 200
