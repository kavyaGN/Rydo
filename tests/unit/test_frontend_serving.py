from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.frontend import mount_frontend


def _client(tmp_path) -> TestClient:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>app shell</html>")
    (tmp_path / "assets" / "app.js").write_text("console.log('hi')")
    (tmp_path / "favicon.ico").write_bytes(b"ico")

    app = FastAPI()

    @app.get("/api/v1/ping")
    def ping() -> dict[str, bool]:
        return {"ok": True}

    assert mount_frontend(app, str(tmp_path))
    return TestClient(app)


def test_serves_index_for_client_side_routes(tmp_path) -> None:
    client = _client(tmp_path)
    for path in ("/", "/history", "/rides/123/tracking"):
        response = client.get(path)
        assert response.status_code == 200
        assert "app shell" in response.text


def test_serves_assets_and_top_level_files(tmp_path) -> None:
    client = _client(tmp_path)
    assert client.get("/assets/app.js").text == "console.log('hi')"
    assert client.get("/favicon.ico").content == b"ico"


def test_never_shadows_the_api(tmp_path) -> None:
    client = _client(tmp_path)
    assert client.get("/api/v1/ping").json() == {"ok": True}
    unknown = client.get("/api/v1/does-not-exist")
    assert unknown.status_code == 404
    assert "app shell" not in unknown.text


def test_cannot_escape_the_dist_folder(tmp_path) -> None:
    (tmp_path.parent / "secret.txt").write_text("nope")
    response = _client(tmp_path).get("/../secret.txt")
    assert "nope" not in response.text


def test_disabled_when_no_build_is_present(tmp_path) -> None:
    assert mount_frontend(FastAPI(), None) is False
    assert mount_frontend(FastAPI(), str(tmp_path / "missing")) is False
