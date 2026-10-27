# Railway 範例（Python / FastAPI）

FastAPI + uvicorn，用 Dockerfile 部署到 Railway。

## 本機開發

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt     # 或 uv pip install -r requirements-dev.txt

pytest                                   # 跑測試
uvicorn app.main:app --reload --port 8080
# 或：python -m app

curl -s localhost:8080/healthz
curl -s localhost:8080/api/v1/info
curl -s -X POST localhost:8080/api/v1/todos -H 'content-type: application/json' -d '{"title":"ship it"}'
open http://localhost:8080/docs          # FastAPI 自動產生的 Swagger UI
```

用 Docker 跑（與線上同一份映像）：

```bash
docker build -t railway-sample . && docker run --rm -p 8080:8080 railway-sample
```

## 部署

```bash
npm i -g @railway/cli      # 或 bash <(curl -fsSL https://railway.com/install.sh)
```

### 方式一：從本機目錄直接部署（最快）

在**這個資料夾**裡執行：

```bash
railway up
```

`railway up` 會自行處理登入／註冊（未登入時開瀏覽器），沒有連結專案時會建立 project + service 並部署。
已登入且想另開新專案時用 `railway up --new --name cloud-platform-samples`。

### 方式二：連動 GitHub repo（建議，支援自動部署）

1. 把整個 repo 推上 GitHub。
2. Railway Dashboard → **New Project → Deploy from GitHub repo** → 選這個 repo。
3. Service → **Settings → Source → Root Directory** 設為 `railway`（本 repo 是多範例結構，`railway.json` 與 `Dockerfile` 都在子資料夾）。
4. 之後 push 到 main 就會自動 build + deploy。

### 產生公開網址

```bash
railway domain      # 配一個 *.up.railway.app 網域
railway open
```

## 常用指令

```bash
railway status --json                     # 目前連結的 project / environment / service
railway variables                         # 列出環境變數
railway variables --set "LOG_LEVEL=debug" # 設定變數（會觸發重新部署）
railway logs                              # runtime log
railway run pytest                        # 用線上環境變數在本機執行指令
railway link --project <id-or-name>       # 連結既有專案
```

## Python 開發者要注意的重點

- **一定要讀 `PORT`**：Railway 用 `PORT` 環境變數指定監聽埠，`--port` 不能寫死；Dockerfile 用 shell form `CMD` 才能展開 `${PORT}`。
- **綁 `0.0.0.0`**：綁 `127.0.0.1` 外部流量會連不進來。
- **健康檢查**：`railway.json` 的 `healthcheckPath` 指向 `/healthz`，沒通過的新版本不會接管流量。
- **優雅關閉**：部署時 Railway 送 `SIGTERM`，uvicorn 預設會等待現有請求結束，`PID 1` 的 shell form `CMD` 由 `sh -c` 轉送訊號。
- **多 worker**：CPU 密集型可改 `uvicorn ... --workers 4`，但記憶體用量乘以 worker 數，先看 Railway 的 Metrics 再調。
- **自動注入的變數**：`RAILWAY_ENVIRONMENT_NAME`、`RAILWAY_SERVICE_NAME`、`RAILWAY_GIT_COMMIT_SHA`、`RAILWAY_PUBLIC_DOMAIN`，`/api/v1/info` 就是在示範讀取它們。
- **接資料庫**：Railway 專案內新增 Postgres，然後用變數參照 `${{Postgres.DATABASE_URL}}`，不要把連線字串寫死在程式碼。
- **密鑰管理**：放 Railway Variables；`.env` 只用於本機，且已被 `.gitignore` 排除。
