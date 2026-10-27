from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture()
def client() -> TestClient:
    settings = Settings.from_env({"PORT": "8080", "RAILWAY_ENVIRONMENT_NAME": "test"})
    return TestClient(create_app(settings))


def test_healthz(client: TestClient) -> None:
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert res.json()["platform"] == "railway"


def test_info_reads_platform_env(client: TestClient) -> None:
    body = client.get("/api/v1/info").json()
    assert body["environment"] == "test"
    assert body["platform"] == "railway"


def test_create_and_list_todo(client: TestClient) -> None:
    created = client.post("/api/v1/todos", json={"title": "ship it"})
    assert created.status_code == 201
    assert created.json()["title"] == "ship it"

    items = client.get("/api/v1/todos").json()
    assert len(items) == 1
    assert items[0]["id"] == created.json()["id"]


@pytest.mark.parametrize("payload", [{}, {"title": ""}, {"title": "x" * 201}, {"title": 123}])
def test_invalid_title_rejected(client: TestClient, payload: dict) -> None:
    assert client.post("/api/v1/todos", json=payload).status_code == 422


def test_delete_todo(client: TestClient) -> None:
    todo_id = client.post("/api/v1/todos", json={"title": "remove me"}).json()["id"]
    assert client.delete(f"/api/v1/todos/{todo_id}").status_code == 204
    assert client.delete(f"/api/v1/todos/{todo_id}").status_code == 404


def test_unknown_path(client: TestClient) -> None:
    assert client.get("/nope").status_code == 404
