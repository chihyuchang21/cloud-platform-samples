from __future__ import annotations

import logging
import time

from fastapi import FastAPI, HTTPException, Request, Response, status

from .config import Settings
from .models import Todo, TodoIn, TodoStore

logger = logging.getLogger("railway-sample")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    store = TodoStore()
    started_at = time.monotonic()

    app = FastAPI(
        title="Railway Python Sample",
        version="1.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.state.settings = settings
    app.state.store = store

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        logger.info(
            "%s %s -> %s (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - start) * 1000,
        )
        return response

    @app.get("/healthz", tags=["ops"])
    async def healthz() -> dict:
        """Railway healthcheckPath 指向這裡。"""
        return {
            "status": "ok",
            "platform": "railway",
            "uptime_seconds": round(time.monotonic() - started_at, 1),
        }

    @app.get("/api/v1/info", tags=["ops"])
    async def info() -> dict:
        return {
            "platform": "railway",
            "environment": settings.environment,
            "service": settings.service_name,
            "commit": settings.commit,
            "public_domain": settings.public_domain,
            "region": settings.region,
        }

    @app.get("/api/v1/todos", response_model=list[Todo], tags=["todos"])
    async def list_todos() -> list[Todo]:
        return store.list()

    @app.post(
        "/api/v1/todos",
        response_model=Todo,
        status_code=status.HTTP_201_CREATED,
        tags=["todos"],
    )
    async def create_todo(payload: TodoIn) -> Todo:
        return store.add(payload)

    @app.delete("/api/v1/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["todos"])
    async def delete_todo(todo_id: str) -> Response:
        if not store.delete(todo_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="todo not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


app = create_app()
