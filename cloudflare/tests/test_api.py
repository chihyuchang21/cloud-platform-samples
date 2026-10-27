from __future__ import annotations

import pytest
from api import MAX_TITLE_LENGTH, reset_store, route

CTX = {"app_name": "sample", "environment": "test", "colo": "TPE", "country": "TW"}


@pytest.fixture(autouse=True)
def _clean_store() -> None:
    reset_store()


def test_healthz() -> None:
    status, body = route("GET", "/healthz", ctx=CTX)
    assert status == 200
    assert body["status"] == "ok"
    assert body["colo"] == "TPE"


def test_info_reads_worker_vars() -> None:
    status, body = route("GET", "/api/v1/info", ctx=CTX)
    assert status == 200
    assert body["environment"] == "test"
    assert body["runtime"] == "pyodide"


def test_geo_from_request_cf() -> None:
    _, body = route("GET", "/api/v1/geo", ctx=CTX)
    assert body["country"] == "TW"


def test_create_and_list_todo() -> None:
    status, created = route("POST", "/api/v1/todos", {"title": "  ship it  "}, CTX)
    assert status == 201
    assert created["title"] == "ship it"

    _, listed = route("GET", "/api/v1/todos", ctx=CTX)
    assert [t["id"] for t in listed["items"]] == [created["id"]]


@pytest.mark.parametrize(
    "body",
    [None, {}, {"title": ""}, {"title": "   "}, {"title": "x" * (MAX_TITLE_LENGTH + 1)}, {"title": 1}],
)
def test_invalid_title_rejected(body) -> None:
    status, _ = route("POST", "/api/v1/todos", body, CTX)
    assert status == 422


def test_delete_todo() -> None:
    _, created = route("POST", "/api/v1/todos", {"title": "remove me"}, CTX)
    assert route("DELETE", f"/api/v1/todos/{created['id']}", ctx=CTX)[0] == 204
    assert route("DELETE", f"/api/v1/todos/{created['id']}", ctx=CTX)[0] == 404


def test_unknown_path_and_method() -> None:
    assert route("GET", "/nope", ctx=CTX)[0] == 404
    assert route("PATCH", "/api/v1/todos", ctx=CTX)[0] == 405
