from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

SETTINGS = Settings.from_env(
    {"PORT": "8080", "APP_ENV": "test", "GIT_COMMIT": "abcdef1234567", "DRAIN_SECONDS": "0"}
)


@pytest.fixture()
def client() -> TestClient:
    # with 區塊會觸發 lifespan，readiness 才會變成 true。
    with TestClient(create_app(SETTINGS)) as client:
        yield client


def test_liveness(client: TestClient) -> None:
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["platform"] == "northflank"


def test_readiness_true_after_startup(client: TestClient) -> None:
    res = client.get("/readyz")
    assert res.status_code == 200
    assert res.json()["ready"] is True


def test_readiness_false_before_startup() -> None:
    app = create_app(SETTINGS)
    with TestClient(app, raise_server_exceptions=False) as _:
        pass
    # lifespan 結束後進入 drain 狀態。
    assert app.state.ready is False


def test_info_truncates_commit(client: TestClient) -> None:
    body = client.get("/api/v1/info").json()
    assert body["environment"] == "test"
    assert body["commit"] == "abcdef1"


def test_create_and_list_todo(client: TestClient) -> None:
    created = client.post("/api/v1/todos", json={"title": "ship it"})
    assert created.status_code == 201
    assert client.get("/api/v1/todos").json()[0]["id"] == created.json()["id"]


@pytest.mark.parametrize("payload", [{}, {"title": ""}, {"title": "x" * 201}, {"title": 123}])
def test_invalid_title_rejected(client: TestClient, payload: dict) -> None:
    assert client.post("/api/v1/todos", json=payload).status_code == 422


def test_delete_todo(client: TestClient) -> None:
    todo_id = client.post("/api/v1/todos", json={"title": "remove me"}).json()["id"]
    assert client.delete(f"/api/v1/todos/{todo_id}").status_code == 204
    assert client.delete(f"/api/v1/todos/{todo_id}").status_code == 404
