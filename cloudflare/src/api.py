"""純 Python 的路由邏輯。

刻意不 import `workers` SDK，這樣同一份邏輯可以在一般 CPython 用 pytest 測試，
也能在 Workers 的 Pyodide runtime 上執行。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

MAX_TITLE_LENGTH = 200

# 注意：Worker 的記憶體狀態只存在於單一 isolate，隨時可能被回收，
# 也不會在多個邊緣節點之間共享。正式用途請改用 KV / D1 / Durable Objects。
_TODOS: dict[str, dict[str, Any]] = {}


def reset_store() -> None:
    _TODOS.clear()


def route(
    method: str,
    path: str,
    body: Any = None,
    ctx: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any] | None]:
    ctx = ctx or {}

    if method == "GET" and path == "/healthz":
        return 200, {"status": "ok", "platform": "cloudflare-workers", "colo": ctx.get("colo")}

    if method == "GET" and path == "/api/v1/info":
        return 200, {
            "platform": "cloudflare-workers",
            "app": ctx.get("app_name", "unknown"),
            "environment": ctx.get("environment", "unknown"),
            "colo": ctx.get("colo"),
            "runtime": "pyodide",
        }

    if method == "GET" and path == "/api/v1/geo":
        # 邊緣才有的資訊：請求是從哪個國家、哪個資料中心進來的。
        return 200, {
            "colo": ctx.get("colo"),
            "country": ctx.get("country"),
            "city": ctx.get("city"),
            "timezone": ctx.get("timezone"),
        }

    if path == "/api/v1/todos":
        if method == "GET":
            return 200, {"items": list(_TODOS.values())}
        if method == "POST":
            title = body.get("title") if isinstance(body, dict) else None
            title = title.strip() if isinstance(title, str) else ""
            if not title or len(title) > MAX_TITLE_LENGTH:
                return 422, {
                    "error": "invalid_title",
                    "message": f"title 必須是 1-{MAX_TITLE_LENGTH} 個字元的字串",
                }
            todo = {
                "id": str(uuid.uuid4()),
                "title": title,
                "done": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            _TODOS[todo["id"]] = todo
            return 201, todo
        return 405, {"error": "method_not_allowed"}

    if path.startswith("/api/v1/todos/"):
        todo_id = path.removeprefix("/api/v1/todos/")
        if method == "DELETE":
            return (204, None) if _TODOS.pop(todo_id, None) else (404, {"error": "not_found"})
        return 405, {"error": "method_not_allowed"}

    return 404, {"error": "not_found", "path": path}
