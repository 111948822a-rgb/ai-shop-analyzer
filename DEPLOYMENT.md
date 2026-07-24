# 部署文档：AI Shop Analyzer 上线 Render

本文档说明如何用 **GitHub + Render** 把前后端和数据库部署到生产环境。
部署采用 Render **Blueprint**：把 `backend/render.yaml` 连到仓库，Render 会自动创建
**PostgreSQL + 后端(Docker) + 前端(Node)** 三个服务。

---

## 1. 架构总览

| 服务 | 类型 | 技术栈 | 端口 | 域名示例 |
|------|------|--------|------|----------|
| `ai-shop-db` | Postgres | Render 托管 (PG 16) | 5432 | 内部连接串 `DATABASE_URL` |
| `ai-shop-backend` | Web (Docker) | FastAPI + uvicorn | 8000 | `https://ai-shop-backend.onrender.com` |
| `ai-shop-frontend` | Web (Node) | Next.js | 3000 | `https://ai-shop-frontend.onrender.com` |

> 后端通过 `DATABASE_URL` 连 Postgres；前端通过 `NEXT_PUBLIC_API_URL` 调后端 API。
> 秒搭 H5 报告页由前端承载（`/report/influencer/{record_id}`），iframe 内嵌即可。

---

## 2. 一键部署步骤

1. **推代码到 GitHub**
   ```bash
   git add -A
   git commit -m "feat: production-ready for Render"
   git push origin main
   ```
   > 确认 `.gitignore` 已忽略 `.env` / `*.db` / `node_modules` / `.next`（本仓库已配好）。

2. **Render 后台创建 Blueprint**
   - Render → **Blueprints** → **New Blueprint Instance** → 连接上面的 GitHub 仓库。
   - Render 读取 `backend/render.yaml`，预览将创建 3 个服务，点击 **Apply**。

3. **在 Render 后台补全私密环境变量**
   - 打开 `ai-shop-backend` 服务的 **Environment**，把下方标 `sync: false` 的变量逐个填好
     （这些不会进代码仓库，必须手动填）。

4. **确认两个跨服务域名**
   - `ai-shop-backend` 的 **Environment** 里 `FRONTEND_BASE_URL` =
     `https://ai-shop-frontend.onrender.com`（填你真实的前端域名）。
   - `ai-shop-frontend` 的 **Environment** 里 `NEXT_PUBLIC_API_URL` =
     `https://ai-shop-backend.onrender.com`（填你真实的后端域名）。
   - 若服务名不是 `ai-shop-backend` / `ai-shop-frontend`，请改 `render.yaml` 与实际保持一致。

5. **首次部署会自动建表**
   - 应用在启动时 `Base.metadata.create_all` 自动建表，无需手工迁移（生产建议后续切 Alembic）。
   - 需要演示数据可执行：`python scripts/generate_mock_data.py`（在 backend 服务 shell 里跑）。

6. **验证**
   - 后端健康检查：`https://<你的后端域名>/api/health` → `{"status":"ok"}`
   - 前端首页：`https://<你的前端域名>/`

---

## 3. 后端环境变量清单（`ai-shop-backend`）

| 变量 | 必填 | 说明 | 来源 |
|------|------|------|------|
| `DATABASE_URL` | ✅ | PostgreSQL 连接串；`postgres://` 会自动规范成 `postgresql://` 并补 `sslmode=require` | Render 从 Postgres 服务**自动注入** |
| `DASHSCOPE_API_KEY` | ✅ | 阿里云通义千问 API Key（AI 分析引擎） | 手动填 `sync:false` |
| `QWEN_MODEL` | ⬜ | 模型名，默认 `qwen3.7-max` | 固定值 |
| `FEISHU_WEBHOOK_URL` | ⬜* | 飞书自定义机器人 Webhook（日报推送） | 手动填 |
| `FEISHU_WEBHOOK_SECRET` | ⬜* | 飞书机器人签名密钥 | 手动填 |
| `FEISHU_APP_ID` | ⬜** | 飞书开放平台应用 ID（主动回写多维表格） | 手动填 |
| `FEISHU_APP_SECRET` | ⬜** | 飞书开放平台应用 Secret | 手动填 |
| `MIAODA_WEBHOOK_SECRET` | ⬜** | 秒搭 → 后端 的 `X-Miaoda-Secret` 校验密钥（生产务必配置） | 手动填 |
| `MIAODA_BITABLE_APP_TOKEN` | ⬜** | 秒搭底层飞书多维表格 app_token | 手动填 |
| `MIAODA_BITABLE_TABLE_ID` | ⬜** | 秒搭底层飞书多维表格 table_id | 手动填 |
| `MIAODA_USE_CELERY` | ⬜ | `false`(默认，用 BackgroundTasks 防超时) / `true`(走 Celery，需 Redis) | 固定值 |
| `FRONTEND_BASE_URL` | ✅ | 前端域名，用于拼 H5 报告链接 `ai_report_url` | 手动填（见步骤 4） |
| `REDIS_URL` | ⬜*** | 仅启用 Celery 时需要 | 手动填 / 从 Redis 服务注入 |

> \* 日报推送用到；\*\* 秒搭主动回写 + 防超时校验用到；\*\*\* 仅 `MIAODA_USE_CELERY=true` 时需要。

> 本地开发仍可保留 `backend/.env`（已被 .gitignore 忽略）。生产环境 **一律用 Render 环境变量**，
> 不要在容器里放 `.env` 文件。

---

## 4. 前端环境变量清单（`ai-shop-frontend`）

| 变量 | 必填 | 说明 |
|------|------|------|
| `NEXT_PUBLIC_API_URL` | ✅ | 后端基址，如 `https://ai-shop-backend.onrender.com`；前端所有 `/api/*` 请求会拼到此地址 |
| `NODE_ENV` | ⬜ | 固定 `production`（Render 一般自动设） |
| `NEXT_TELEMETRY_DISABLED` | ⬜ | 固定 `1`，关闭 Next.js 遥测 |

> `NEXT_PUBLIC_*` 是**构建期**注入的：Render 在 `npm run build` 时把值打进前端包，
> 所以修改后需要 **重新部署（Clear build cache + Deploy）** 才生效。

---

## 5. 本地 vs 生产 数据库连接切换说明

`backend/app/db.py` 的切换逻辑：

- 设置环境变量 `DATABASE_URL`（Render 的 Postgres 会自动注入） → 使用 PostgreSQL。
- `postgres://` 开头会自动替换为 SQLAlchemy 要求的 `postgresql://`。
- Postgres 连接串若未声明 `sslmode`，会自动补 `?sslmode=require`（Render 强制 SSL）。
- **未设置** `DATABASE_URL` 时，回退到默认 `sqlite:///./dev.db`（本地开发零依赖）。

无需改任何业务代码，DB 切换完全由环境变量驱动。

---

## 6. （可选）启用 Celery 异步

默认分析用 FastAPI `BackgroundTasks`，**无需 Redis 即可上线**。若需 Celery（高并发/多 worker）：

1. 在 `render.yaml` 增加 Redis 服务，并把 `REDIS_URL` 注入 `ai-shop-backend`；
2. 把 `MIAODA_USE_CELERY` 设为 `true`；
3. 再加一个 worker 服务：`celery -A app.tasks.celery_app.celery_app worker`。

---

## 7. 常见问题

- **前端报 404 / CORS**：检查 `NEXT_PUBLIC_API_URL` 是否指向正确后端域名，且后端 `FRONTEND_BASE_URL`
  是否指向正确前端域名；两服务需互相可达。
- **后端连不上数据库**：确认 `DATABASE_URL` 来自 Postgres 服务（Blueprint 已 `fromService` 绑定），
  且连接串以 `postgresql://` 开头（本项目已自动处理）。
- **建表失败**：应用启动 `create_all` 会在首次部署建表；若后续改了表结构，请用 Alembic 迁移。
