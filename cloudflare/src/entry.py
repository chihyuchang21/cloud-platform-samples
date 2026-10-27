"""Cloudflare Python Worker 入口。

需要在 wrangler 設定中啟用 `python_workers` compatibility flag。
"""

import json
from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint

from api import route

JSON_HEADERS = {"Content-Type": "application/json; charset=utf-8"}


def _cf(request, key, default=None):
    """request.cf 是 JS 物件，透過 FFI 取值時要容錯（本機 dev 可能沒有）。"""
    cf = getattr(request, "cf", None)
    if cf is None:
        return default
    value = getattr(cf, key, None)
    return default if value is None else str(value)


def _env(env, key, default=""):
    value = getattr(env, key, None)
    return default if value is None else str(value)


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = urlparse(str(request.url))
        method = str(request.method).upper()

        body = None
        if method in ("POST", "PUT", "PATCH"):
            raw = await request.text()
            if raw:
                try:
                    body = json.loads(raw)
                except ValueError:
                    return Response(
                        json.dumps({"error": "invalid_json"}),
                        status=400,
                        headers=JSON_HEADERS,
                    )

        ctx = {
            "app_name": _env(self.env, "APP_NAME", "cloud-platform-samples"),
            "environment": _env(self.env, "ENVIRONMENT", "development"),
            "colo": _cf(request, "colo"),
            "country": _cf(request, "country"),
            "city": _cf(request, "city"),
            "timezone": _cf(request, "timezone"),
        }

        status, payload = route(method, url.path, body, ctx)
        if payload is None:
            return Response(None, status=status)

        headers = dict(JSON_HEADERS)
        # 讓 Cloudflare 邊緣快取純讀取的端點，其餘不快取。
        headers["Cache-Control"] = (
            "public, max-age=60" if url.path == "/api/v1/info" else "no-store"
        )
        return Response(json.dumps(payload), status=status, headers=headers)
