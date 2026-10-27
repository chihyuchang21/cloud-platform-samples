from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from .config import Settings
from .models import Todo, TodoIn, TodoStore

logger = logging.getLogger("northflank-sample")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    store = TodoStore()
    started_at = time.monotonic()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.ready = True
        logger.info("service ready on port %s", settings.port)
        yield
        # 先讓 readiness 轉為 false，負載平衡器把流量移走後再真正關閉。
        app.state.ready = False
        if settings.drain_seconds > 0:
            await asyncio.sleep(settings.drain_seconds)
        logger.info("service drained, shutting down")

    app = FastAPI(
        title="Northflank Python Sample",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.ready = False
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
        """Liveness probe：程序還活著就回 200，不要在這裡檢查外部依賴。"""
        return {
            "status": "ok",
            "platform": "northflank",
            "uptime_seconds": round(time.monotonic() - started_at, 1),
        }

    @app.get("/readyz", tags=["ops"])
    async def readyz() -> JSONResponse:
        """Readiness probe：還沒 ready 或正在 drain 時回 503，流量就不會進來。"""
        ready = bool(app.state.ready)
        return JSONResponse(
            status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"ready": ready},
        )

    @app.get("/api/v1/info", tags=["ops"])
    async def info() -> dict:
        return {
            "platform": "northflank",
            "environment": settings.environment,
            "service": settings.service_name,
            "commit": settings.commit,
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
