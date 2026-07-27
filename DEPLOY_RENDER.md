# AI Shop Analyzer 部署到 Render 教程

> 适用版本：本项目（FastAPI 后端 + Next.js 14 前端 + PostgreSQL）
> 仓库：`https://github.com/111948822a-rgb/ai-shop-analyzer`
> 本文基于仓库内已有的 `render.yaml` 编写，照做即可，**不需要手写 Dockerfile / 配置文件**。

---

## 一、先确认你已经具备的"前置条件"

| 前置项 | 状态 | 说明 |
|--------|------|------|
| GitHub 仓库代码已推送 | ✅ 已完成 | 最新提交已在 `main` 分支，包含合并冲突修复、`backend/Dockerfile` 修复、`.dockerignore` 等 |
| `render.yaml` 存在且正确 | ✅ 已完成 | 位于仓库根目录，定义了 3 个服务（PostgreSQL、后端、前端） |
| `backend/Dockerfile` 完整 | ✅ 已完成 | 6 行标准 Python 构建指令，无冲突标记 |
| 一个 Render 账号 | ⚠️ 需你准备 | 免费注册：https://render.com （用 GitHub 登录最省事） |
| 通义千问 API Key（可选） | ⚠️ 按需 | 用于 AI 分析功能，没有也能部署，只是分析接口会报错 |

如果上面 ✅ 项有疑问，先回去检查代码是否已 `git push` 到 GitHub。

---

## 二、部署方式一：Blueprint 一键部署（★ 推荐）

仓库里的 `render.yaml` 就是 **Render Blueprint（基础设施即代码）**。Render 读它会自动创建全部 3 个服务，你几乎不用点配置。

### 步骤 1：登录 Render 并新建 Blueprint
1. 打开 https://dashboard.render.com
2. 点击右上角 **New +** → **Blueprint**
3. 首次使用会让你 **Connect GitHub**，授权 Render 访问你的账号
4. 在仓库列表里选择 **`ai-shop-analyzer`**，分支选 **`main`**
5. 点 **Connect**

### 步骤 2：Render 读取 render.yaml
Render 会自动解析出 3 个服务并显示预览：
- `ai-shop-analyzer-db`（PostgreSQL，plan: starter）
- `ai-shop-analyzer-backend`（Web 服务，Docker，plan: starter，健康检查 `/health`）
- `ai-shop-analyzer-frontend`（Web 服务，Node/Next.js，plan: starter，健康检查 `/`）

### 步骤 3：填写环境变量
Blueprint 会弹出一个环境变量表单。重点：
- **`DATABASE_URL`**：自动从 PostgreSQL 服务注入，**不要手填**
- **`NEXT_PUBLIC_API_URL`**（前端）：自动从后端服务获取，**不要手填**
- 其余变量（见第三节表格）按需在 Render 控制台填，空着也能先部署

### 步骤 4：点击 Apply / Deploy
Render 会按依赖顺序创建并部署：
1. 先建 PostgreSQL（约 1–2 分钟）
2. 构建后端 Docker 镜像（约 3–5 分钟，首次 `pip install` 较慢）
3. 构建前端（约 2–3 分钟）

### 步骤 5：等部署完成
每个服务卡片从 **Build in progress** → **Live** 即成功。所有服务都 Live 后，点前端服务的 URL（形如 `https://ai-shop-analyzer-frontend.onrender.com`）即可访问。

> **自动部署**：Blueprint 关联后，Render 会自动给 GitHub 仓库挂上 webhook。以后你每次 `git push`（包括本项目的自动上传钩子），Render 都会**自动重新部署**，无需手动操作。

---

## 三、环境变量说明（哪些必填）

| 变量名 | 必填 | 作用 | 去哪拿 |
|--------|------|------|--------|
| `DATABASE_URL` | 自动 | 数据库连接串，Render 从 PostgreSQL 注入 | 不用管 |
| `PYTHONPATH` | 已固定 | 设为 `/app`，容器内找得到代码 | 已写死 |
| `NEXT_PUBLIC_API_URL` | 自动 | 前端调后端的地址，Render 从后端服务注入 | 不用管 |
| `DASHSCOPE_API_KEY` | **强烈建议** | 通义千问 Function Calling，AI 分析核心 | 阿里云百炼控制台 → API Key |
| `REDIS_URL` | 选填 | Celery 定时任务（日报）所需；**当前仓库未定义 Redis 服务**，留空则定时任务不跑 | 见第六节第 4 条 |
| `MIAODA_API_KEY` / `MIAODA_SECRET` / `MIAODA_API_URL` | 选填 | 妙搭达人分析功能 | 妙搭平台提供 |
| `FEISHU_WEBHOOK_URL` / `FEISHU_SECRET` | 选填 | 飞书推送（日报卡片） | 飞书自定义机器人 |
| `TK_PARTNER_APP_KEY` / `TK_PARTNER_APP_SECRET` 等 | 选填 | TikTok Shop 授权同步 | TikTok Partner API |
| `REPORTS_BASE_URL` | 选填 | 报告页对外访问基址（H5 报告分享用） | 填前端 URL |

**最小可跑原则**：先只填 `DASHSCOPE_API_KEY`，其他以后按需补。上传数据、清洗聚合、看板这些核心功能不依赖任何可选变量，能直接跑。

---

## 四、部署完成后的验证

1. **后端健康检查**：浏览器访问 `https://<你的后端URL>/health`
   返回 `{"status":"ok"}` 即后端存活（这也是 Render 健康检查路径）。
2. **API 文档**：访问 `https://<你的后端URL>/docs`（FastAPI 自带 Swagger）。
3. **前端页面**：访问前端 URL，能看到分析界面即前端部署成功。
4. **跑一次真实流程**：上传一份 CSV → 点分析 → 看报告。这一步能验证 AI Key 是否生效。

---

## 五、部署方式二：手动创建服务（不用 render.yaml，备选）

如果你不想用 Blueprint，可以在 Render 里手动建 3 个服务：

### 后端（Docker Web Service）
- New → Web Service → 选仓库 → **Runtime 选 Docker**
- Root Directory：`backend`
- Branch：`main`
- 因为仓库有 `backend/Dockerfile`，Render 会自动用它构建
- Health Check Path：`/health`
- 环境变量：手动加 `DATABASE_URL`（连你手动建的 Postgres）、`DASHSCOPE_API_KEY`、`PYTHONPATH=/app`

### 前端（Node Web Service）
- New → Web Service → 选仓库 → **Runtime 选 Node**
- Root Directory：`frontend`
- Build Command：`npm install && npm run build`
- Start Command：`npm run start`
- 环境变量：`NEXT_PUBLIC_API_URL` = 后端服务 URL

### 数据库（PostgreSQL）
- New → PostgreSQL → 取名 `ai-shop-analyzer-db`
- 建好后把 Internal Database URL 复制给后端的 `DATABASE_URL`

> 手动方式容易漏配环境变量和依赖顺序，**除非 Blueprint 报错，否则一律用方式一**。

---

## 六、常见问题排查

### 0. Blueprint 报 `unknown type "psql"`
症状：在 Render 选 Blueprint 后立刻报错 `A Blueprint file was found, but there was an issue. unknown type "psql"`。
原因：`render.yaml` 里数据库服务写成了 `type: psql`，但 Render 的正确类型名是 **`postgres`**（`psql` 是 psql 客户端的名字，不是服务类型）。
修复：把数据库服务的 `type: psql` 改成 `type: postgres`，提交推送后回到 Render 重新走 Blueprint 流程即可。
> 当前仓库已修复（commit `147dff4`），无需再改。
> **重要**：第一次 Blueprint 解析失败后，必须去 Render **删除那个失败的环境**，再重新 **New + → Blueprint** 从 GitHub 拉最新代码。不要直接 Retry / 重试旧的失败部署——它会复用失败时的旧快照，仍然报 `psql`。

### 1. 构建失败：`Dockerfile: 2B` 或 `transferring dockerfile` 报错
症状见你之前遇到的坑。原因几乎都是 `backend/Dockerfile` 被合并冲突标记污染。
- 确认文件是完整的 6 行（见仓库当前版本）
- 本地用 `head -c 200 backend/Dockerfile` 看字节数，正常应 >150 字节
- 已修复，正常情况下不会再出现

### 2. 后端启动即崩：`ModuleNotFoundError` / `SyntaxError`
- 之前 15 个文件有合并冲突，现已全部清理。若仍崩，先 `git pull` 确认拉到最新 `main`
- 检查 `backend/requirements.txt` 是否包含全部依赖（已补 `requests`）

### 3. 健康检查一直失败（`/health` 返回非 200）
- 确认 `backend/app/main.py` 里有 `@app.get("/health")` 端点（已补）
- 也可能是 `DATABASE_URL` 没连上 Postgres，导致应用启动初始化失败 → 看后端日志的报错栈

### 4. AI 分析接口报错（401 / 空响应）
- 99% 是 `DASHSCOPE_API_KEY` 没填或填错 → 去阿里云百炼核对 Key
- 与部署无关，是运行期配置问题

### 5. 定时日报（Celery）不工作
- 当前 `render.yaml` **没有定义 Redis 和 Celery worker 服务**，只有空的 `REDIS_URL`
- 如需定时任务：在 Render 加一个 Redis 服务，把 `REDIS_URL` 填上，再单独加一个启动 `celery -A app.tasks.celery_app worker` 的后台服务
- 不影响手动上传/分析/看板等主流程

### 6. 前端跨域（调后端报 CORS）
- `main.py` 的 CORS 已放开为允许所有来源，正常情况下不会跨域
- 若仍报，确认前端 `NEXT_PUBLIC_API_URL` 指向的是**后端公网 URL** 而非 localhost

### 7. 免费版休眠（页面半天打不开）
- `render.yaml` 用的是 `starter` plan（不休眠，但计费）
- 想省钱可改成 `free`：编辑 `render.yaml` 把对应 `plan: starter` 改成 `plan: free`，提交后 Render 会更新；免费版 15 分钟无流量会休眠，下次访问需冷启动（约 30 秒）

---

## 七、更新代码（你已经打通了自动链路）

本项目已配置：
- `post-commit` 钩子：每次 `git commit` 自动 `git push origin main`
- Render webhook：每次 push 自动重新部署

所以你（或本助手）改完代码 → `commit` → **GitHub 自动更新 → Render 自动重新部署**，全程无需登 Render 手动操作。

> 注意：改完务必 `git push` 成功（看终端是否出现 `main -> main`）。只有代码进了 `main` 分支，Render 才会触发部署。

---

## 八、一句话流程回顾

```
GitHub(main) ──push──▶ Render(Blueprint) ──建库/构建──▶ 后端+前端+数据库 全部 Live
        ▲                                                        │
        └──────────── 自动 webhook 重新部署 ◀───────────────────┘
```

搞定。有问题看 Render 每个服务的 **Logs** 标签页，报错信息比本地更直观。
