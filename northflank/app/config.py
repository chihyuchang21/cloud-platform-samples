from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Northflank 不會自動注入應用層變數，以下都在 service 的 Environment / Secret group 設定。"""

    port: int
    host: str
    log_level: str
    environment: str
    service_name: str
    commit: str
    drain_seconds: float

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        return cls(
            port=int(env.get("PORT", "8080")),
            host=env.get("HOST", "0.0.0.0"),
            log_level=env.get("LOG_LEVEL", "info"),
            environment=env.get("APP_ENV", "local"),
            service_name=env.get("APP_SERVICE_NAME", "local-dev"),
            # GIT_COMMIT 由 Dockerfile 的 build arg 帶入。
            commit=env.get("GIT_COMMIT", "unknown")[:7],
            drain_seconds=float(env.get("DRAIN_SECONDS", "0")),
        )
