# Northflank 範例（Python / FastAPI）

FastAPI + uvicorn，用 Dockerfile 部署成 Northflank 的 **combined service**（同一個 service 同時負責 build 與 run）。
和 Railway 範例的差別在於這裡示範了 **liveness / readiness 雙探針** 與 **drain（排空流量）** 流程。

## 本機開發

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

pytest
uvicorn app.main:app --reload --port 8080     # 或 python -m app

curl -s localhost:8080/healthz    # liveness
curl -s localhost:8080/readyz     # readiness
curl -s localhost:8080/api/v1/info
```

用 Docker 跑：

```bash
docker build --build-arg GIT_COMMIT=$(git rev-parse HEAD) -t northflank-sample .
docker run --rm -p 8080:8080 -e APP_ENV=docker northflank-sample
```

## 部署

### 方式一：Dashboard（最直覺）

1. 把 repo 推上 GitHub，並在 Northflank 連結你的 GitHub 帳號。
2. 建立 **Project**（選區域）。
3. 在專案內建立 **Service → Combined service（build + deploy）**，來源選這個 repo 與分支。
4. Build 設定：
   - Build type：**Dockerfile**
   - Build context：`/northflank`
   - Dockerfile path：`/northflank/Dockerfile`
   - Build arguments：`GIT_COMMIT` =（可用 commit SHA 變數）
5. Runtime 設定：
   - Port：`8080`，protocol **HTTP**，勾選 publicly expose 取得 `*.code.run` 網址
   - Environment variables：`APP_ENV`、`APP_SERVICE_NAME`、`LOG_LEVEL`、`DRAIN_SECONDS`
   - Health checks：liveness → HTTP `GET /healthz`；readiness → HTTP `GET /readyz`
6. 開啟 **CI/CD → build & deploy on push**，之後 push 就會自動重建。

> UI 文字會隨版本微調，但上述欄位（build context / dockerfile path / port / health check）名稱一致。

### 方式二：CLI

```bash
npm i -g @northflank/cli
northflank login                       # 瀏覽器選擇或建立 API token
northflank context ls                  # 檢視 / 切換 context

northflank create project              # 互動式建立專案
northflank create service --help       # 看可用的 service 類型與參數
northflank create service combined -f ./service.json   # 用 JSON 定義建立（等同 API request body）
```

CLI 的 `--input/-i`（JSON/YAML 字串）或 `--file/-f`（檔案）接受的定義，就是 API 文件裡的 request body，
所以可以把 service 定義版控在 repo 內，等同於輕量版 IaC；要更完整的 IaC 可用 Northflank **Templates**。

常用：

```bash
northflank get service --project <project> --service <service>
northflank logs service --project <project> --service <service>
northflank forward service --project <project> --service <service>   # 本機 port-forward
```

## Python 開發者要注意的重點

- **Port 要一致**：程式監聽 `PORT`（預設 8080），Northflank service 的 port 設定也要是 8080，否則健康檢查永遠失敗。
- **liveness ≠ readiness**：
  - `/healthz` 只回報程序活著，**不要**檢查資料庫，否則 DB 短暫抖動會讓容器被重啟。
  - `/readyz` 才檢查「能不能接流量」，回 503 時平台會把流量移開但不殺掉容器。
- **Drain**：收到 `SIGTERM` 後本範例先把 readiness 設為 false、等 `DRAIN_SECONDS` 秒，再讓 uvicorn 結束剩餘請求（`--timeout-graceful-shutdown 30`），避免滾動更新時掉請求。
- **build arg 帶版本**：`GIT_COMMIT` 透過 Dockerfile `ARG` 注入，`/api/v1/info` 可以回報目前跑的是哪個 commit，排查問題很有用。
- **密鑰**：用 Northflank 的 **Secret groups**（可跨 service 共用、分環境），不要寫進映像或 commit `.env`。
- **資料庫**：用 Northflank add-on（Postgres / Redis / MongoDB），連線字串以 secret 注入環境變數。
- **非 root 執行**：Dockerfile 已建立 `appuser`，符合容器安全基本要求。
