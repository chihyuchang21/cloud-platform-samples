from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """從環境變數讀設定；Railway 會在 runtime 自動注入 RAILWAY_* 變數。"""

    port: int
    host: str
    log_level: str
    environment: str
    service_name: str
    commit: str
    public_domain: str
    region: str

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        port = int(env.get("PORT", "8080"))
        return cls(
            port=port,
            host=env.get("HOST", "0.0.0.0"),
            log_level=env.get("LOG_LEVEL", "info"),
            environment=env.get("RAILWAY_ENVIRONMENT_NAME", "local"),
            service_name=env.get("RAILWAY_SERVICE_NAME", "local-dev"),
            commit=env.get("RAILWAY_GIT_COMMIT_SHA", "unknown")[:7],
            public_domain=env.get("RAILWAY_PUBLIC_DOMAIN", f"localhost:{port}"),
            region=env.get("RAILWAY_REPLICA_REGION", "local"),
        )
