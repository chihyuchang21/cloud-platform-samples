# Cloud Platform Samples（Python）

以 **software developer** 的角度，用同一組 Python HTTP API，分別部署到三個平台：

| 資料夾 | 平台 | 技術棧 | 部署型態 |
| --- | --- | --- | --- |
| [railway](railway/) | Railway | FastAPI + uvicorn | Dockerfile 容器 |
| [cloudflare](cloudflare/) | Cloudflare Workers | Python Workers（Pyodide） | 邊緣 isolate |
| [northflank](northflank/) | Northflank | FastAPI + uvicorn | Dockerfile 容器（combined service） |

三個資料夾**彼此獨立**，各有自己的相依、測試與部署設定，可以單獨部署。

## 共同的 API

| Method | Path | 說明 |
| --- | --- | --- |
| GET | `/healthz` | 健康檢查（liveness），平台的 health check 指向這裡 |
| GET | `/api/v1/info` | 平台 / 環境 / commit 資訊，示範讀取各平台注入的變數 |
| GET | `/api/v1/todos` | 列出 todo（記憶體，重啟即消失） |
| POST | `/api/v1/todos` | 建立 todo，body `{"title": "..."}`，標題長度 1–200 |
| DELETE | `/api/v1/todos/{id}` | 刪除 todo |

各平台額外端點：

- Northflank：`/readyz`（readiness probe，drain 期間回 503）
- Cloudflare：`/api/v1/geo`（邊緣地理資訊：colo / country / city）
- Railway、Northflank：`/docs`（FastAPI 自動產生的 Swagger UI）

## 快速開始

```bash
# Railway / Northflank（擇一，流程相同）
cd railway
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
uvicorn app.main:app --reload --port 8080

# Cloudflare
cd cloudflare
uv venv && uv pip install pytest && uv run pytest
uvx --from workers-py pywrangler dev        # http://localhost:8787
```

驗證：

```bash
curl -s localhost:8080/healthz
curl -s -X POST localhost:8080/api/v1/todos -H 'content-type: application/json' -d '{"title":"ship it"}'
```

## 推上 GitHub

```bash
cd /home/iec150057/dev/cloud-platform-samples
git init -b main
git add .
git commit -m "feat: railway / cloudflare / northflank Python deployment samples"
git remote add origin git@github.com:<你的帳號>/cloud-platform-samples.git
git push -u origin main
```

推上去之後，三個平台都能直接連動 GitHub repo 自動部署（各資料夾 README 有步驟；記得把 root directory 設成對應子資料夾）。
`.github/workflows/ci.yml` 會在每次 push 跑三組 pytest，並 build 兩個 Docker 映像。

## 平台差異重點（Python 開發者視角）

| 面向 | Railway | Cloudflare Workers | Northflank |
| --- | --- | --- | --- |
| 執行環境 | 容器（完整 CPython） | Pyodide / WebAssembly | 容器（完整 CPython） |
| 套件限制 | 任何 PyPI 套件 | 僅 pure Python / PyEmscripten wheel | 任何 PyPI 套件 |
| 連線埠 | 必須讀 `PORT` | 無連線埠，export `fetch` handler | service 設定指定（本範例 8080） |
| 設定檔 | `railway.json` | `wrangler.jsonc`（需 `python_workers` flag） | UI / CLI JSON / Templates |
| 本機開發 | `uvicorn --reload`、`railway run` | `pywrangler dev` | `uvicorn --reload`、Docker |
| 健康檢查 | `healthcheckPath` | 不適用（無常駐程序） | liveness + readiness 雙探針 |
| 狀態保存 | Postgres / Redis add-on | KV / D1 / R2 / Durable Objects | Postgres / Redis / MongoDB add-on |
| 密鑰 | Variables | `wrangler secret put` | Secret groups |
| 冷啟動 | 無（常駐） | 近乎 0ms | 無（常駐） |

> 三個範例的 todo 都存在記憶體，僅供示範；正式服務請接資料庫。
> Workers 的記憶體狀態甚至不保證跨請求存在。

典型組合：Cloudflare Worker 擺在最前面做驗證、快取與地理導流，後面接 Railway 或 Northflank 上的 FastAPI 服務。
