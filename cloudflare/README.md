# Cloudflare 範例（Python Workers）

100% Python 的 Cloudflare Worker，跑在邊緣的 Pyodide runtime 上（不是 Node、也不是傳統容器）。

程式碼刻意拆成兩層：

| 檔案 | 用途 |
| --- | --- |
| [src/api.py](src/api.py) | 純 Python 路由邏輯，不 import `workers`，可以用一般 pytest 測試 |
| [src/entry.py](src/entry.py) | Worker 入口（`Default(WorkerEntrypoint)`），負責 Request/Response 轉換與讀取 `env`、`request.cf` |

## 本機開發

測試（一般 CPython 即可，不需要 Workers runtime）：

```bash
uv venv && uv pip install pytest
uv run pytest
```

跑真正的 Worker（需要 [uv](https://docs.astral.sh/uv/) 與 Node）：

```bash
cp .dev.vars.example .dev.vars
uvx --from workers-py pywrangler dev      # 預設 http://localhost:8787

curl -s localhost:8787/healthz
curl -s localhost:8787/api/v1/info
curl -s localhost:8787/api/v1/geo
curl -s -X POST localhost:8787/api/v1/todos -H 'content-type: application/json' -d '{"title":"ship it"}'
```

`pywrangler` 是 Python Workers 專用的 wrangler 包裝，會處理 Python 環境與套件打包；
它支援所有 wrangler 指令（`uvx --from workers-py pywrangler --help`）。

## 部署

```bash
uvx --from workers-py pywrangler deploy
```

第一次會要求登入 Cloudflare 帳號（開瀏覽器授權）。部署後會得到 `*.workers.dev` 網址。

指定環境與密鑰：

```bash
uvx --from workers-py pywrangler deploy --env production
uvx --from workers-py pywrangler secret put API_TOKEN          # 密鑰不要寫進 wrangler.jsonc
uvx --from workers-py pywrangler tail                          # 即時 log
```

從 GitHub 自動部署：Cloudflare Dashboard → **Workers & Pages → Create → Connect to Git**，
選這個 repo，root directory 設為 `cloudflare`。

## Python 開發者要注意的重點

- **必須加 `python_workers` compatibility flag**，否則 Worker 不會以 Python 模式執行（見 [wrangler.jsonc](wrangler.jsonc)）。
- **沒有「連線埠」的概念**：不是啟動一個 server，而是 export 一個 `fetch` handler；`PORT` 在這裡完全無意義。
- **不是完整 CPython**：跑的是 Pyodide（WebAssembly）。標準庫大部分可用，但沒有本機檔案系統、不能開 socket，
  只有 pure Python 或 PyEmscripten wheel 的套件可用（FastAPI、Pydantic、Langchain 等已支援）。
- **全域狀態不可靠**：`api.py` 裡的 `_TODOS` 只存在於單一 isolate，可能隨時被回收，也不跨邊緣節點共享。
  要持久化請用 **KV**（設定 / 快取）、**D1**（SQL）、**R2**（檔案）、**Durable Objects**（強一致狀態）。
- **FFI 要容錯**：`request.cf`、`env` 都是 JS 物件，透過 FFI 取值；本機 dev 可能沒有 `cf`，所以 `entry.py` 用 `getattr` 取預設值。
- **讀 body 用 `await request.text()` 再 `json.loads`**，比直接拿 JS 物件好處理。
- **快取靠 header**：回應帶 `Cache-Control` 就能讓 Cloudflare 邊緣快取，本範例只對 `/api/v1/info` 開快取。
- **適合的場景**：低延遲 API、A/B 導流、地理判斷、驗證/改寫請求後轉給後端（例如轉給 Railway 或 Northflank 上的服務）。
  長時間運算、需要本機檔案或原生套件的工作，留在容器那兩個平台。
