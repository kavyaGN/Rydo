import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.request_context import REQUEST_ID_HEADER, RequestContextMiddleware, request_id_var


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"request_id": request_id_var.get()}

    return app


def test_generates_request_id_and_exposes_it_to_handlers() -> None:
    response = TestClient(_app()).get("/ping")
    request_id = response.headers[REQUEST_ID_HEADER]
    assert len(request_id) == 32
    assert response.json() == {"request_id": request_id}


def test_reuses_a_safe_incoming_request_id() -> None:
    response = TestClient(_app()).get("/ping", headers={REQUEST_ID_HEADER: "trace-abc.123"})
    assert response.headers[REQUEST_ID_HEADER] == "trace-abc.123"


def test_replaces_an_unsafe_incoming_request_id() -> None:
    response = TestClient(_app()).get("/ping", headers={REQUEST_ID_HEADER: "bad id\nwith newline"})
    assert response.headers[REQUEST_ID_HEADER] != "bad id\nwith newline"
    assert len(response.headers[REQUEST_ID_HEADER]) == 32


def test_writes_a_structured_access_log(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="rydo.access"):
        response = TestClient(_app()).get("/ping")
    record = next(r for r in caplog.records if r.name == "rydo.access")
    assert record.status_code == 200
    assert record.path == "/ping"
    assert record.duration_ms >= 0
    assert response.status_code == 200
