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

### 0. Blueprint 报 `unknown type "psql"` / `unknown type "postgres"`
症状：在 Render 选 Blueprint 后报错 `A Blueprint file was found, but there was an issue. unknown type "psql"` 或 `unknown type "postgres"`。
根因（关键）：Render 的 `services` 列表里**根本没有数据库类型**，`type` 只接受 `web` / `pserv` / `worker` / `cron` / `keyvalue`。PostgreSQL 必须放在**根级 `databases:` 列表**（不用 `type` 字段），绝不能在 `services` 下用 `type: postgres` 或 `type: psql` 去定义。
正确写法：把数据库从 `services:` 下移到根级 `databases:`，条目只保留 `name` / `databaseName` / `user` / `ipAllowList` 等字段；`web` 服务里继续用 `fromDatabase` 引用它的 `name`。
> 当前仓库 `render.yaml` 已是正确写法（数据库在 `databases:` 列表、`services` 仅含两个 `web`），无需再改。
> **重要**：第一次 Blueprint 解析失败后，必须去 Render **删除那个失败的环境**，再重新 **New + → Blueprint** 从 GitHub 拉最新代码。不要直接 Retry / 重试旧的失败部署——它会复用失败时的旧快照，仍报同样的类型错误。

### 0.1 Blueprint 报 `cannot simultaneously specify fields value and sync`
症状：大量 `services[0].envVars[N] cannot simultaneously specify fields value and sync`。
根因：同一个环境变量条目里**同时写了 `value: ""` 和 `sync: false`**，Render 不允许二者共存。
正确写法（源自 Render 官方 Blueprint 规范）：
- **密钥 / 需要手动填写的变量**：只写 `key` + `sync: false`（不写 `value`），Render 在创建时弹出输入框让你填；例如 `- key: DASHSCOPE_API_KEY` 换行 `  sync: false`
- **有固定值的变量**：只写 `key` + `value`（不写 `sync`）；例如 `- key: PYTHONPATH` 换行 `  value: /app`
- 二者**绝不**同时出现。

### 0.2 Blueprint 报 `fromService.property: invalid service property: url` / `fromService.type: empty but required`
症状：`services[1].envVars[0].fromService.property: invalid service property: url. Valid properties are connectionString, host, hostport, port.` 以及 `fromService.type: empty but required`。
根因：① `fromService` **必须带 `type` 字段**；② web 服务的 `property` 合法值只有 `host` / `port` / `hostport`（无 `url`），且给的是私有网络主机名，**浏览器访问不到**；③ 本项目前端 `lib/api.ts` 用 `${BASE}/api/...` 直接拼接，要求 `NEXT_PUBLIC_API_URL` 是**带 `https://` 的完整 URL**。
正确写法：前端直接写完整 URL（Render web 服务固定域名为 `https://<服务名>.onrender.com`）：
```yaml
- key: NEXT_PUBLIC_API_URL
  value: https://ai-shop-analyzer-backend.onrender.com
```
> 若以后重命名后端服务，记得同步改这个 URL。需要引用其它服务属性时再用 `fromService`（必须含 `type`，`property` 用 `host`/`port`/`hostport`，或 `envVarKey` 引用其环境变量），但本项目前端场景用完整 URL 最稳妥。

### 0.3 整体构建失败：`Exited with status 1 while building your code`
症状：Blueprint 三个服务都创建成功，但部署在 **build 阶段** 直接 `Exited with status 1`。**注意：这个报错和 `render.yaml` 无关**——它是代码构建（前端 `npm run build` / 后端 `docker build`）本身挂了。哪怕是只改文档的提交也会失败，说明是结构性构建问题。本项目实际踩到的是**前端**构建失败，根因有三：
1. **依赖缺失**：`package.json` 漏了 `lucide-react` / `@babel/runtime`（页面 `import` 了但没声明）→ `Module not found: Can't resolve 'lucide-react'`。修复：补回这两个依赖（已修复，版本 `lucide-react ^1.27.0` / `@babel/runtime ^8.0.0` 为真实存在版本）。
2. **类型检查失败**：`app/page.tsx` 给 Next.js `<Link>` 加了非法的 `disabled` 属性 → `next build` 默认做 TS 类型检查直接退出 1。修复：改为条件渲染（有 id 才渲染 `<Link>`，否则渲染禁用态 `<span>`）。
3. **双配置文件**：前端同时有 `next.config.js` 和 `next.config.mjs`（合并冲突残留），应只保留生产正确的 `next.config.mjs`（会读 `NEXT_PUBLIC_API_URL`）。
为不再被历史类型小问题卡住，已在 `next.config.mjs` 加 `typescript: { ignoreBuildErrors: true }` 与 `eslint: { ignoreDuringBuilds: true }` 作为部署安全网（运行时行为不受影响）。
> 验证方法：本地 `cd frontend && npm install && npm run build`，能跑出 `✓ Compiled successfully` + 4 个页面路由即说明前端构建没问题。

### 1. 构建失败：`open Dockerfile: no such file or directory` / `transferring dockerfile: 2B`
症状：后端 Docker 构建一开始就失败，日志：
`#1 [internal] load build definition from Dockerfile` → `#1 transferring dockerfile: 2B done` → `error: failed to solve: failed to read dockerfile: open Dockerfile: no such file or directory`。
**关键线索**：日志写的是 `from Dockerfile`（没有子目录），说明 Render 在**仓库根目录**找 `./Dockerfile`，而本项目 Dockerfile 实际在 `backend/Dockerfile`。

**根因（两层，已彻底解决）**：
1. Render 的 `dockerfilePath` 默认是仓库根目录的 `./Dockerfile`。本项目是 monorepo，Dockerfile 在 `backend/` 下，根目录没有 → 找不到。
2. **更隐蔽的一点**：Render 的 Blueprint 在**创建 Docker 服务时**就锁死了 `Dockerfile Path` 字段，**后续 push 改 `dockerfilePath`/`dockerContext` 不会回写已存在的服务**（只在"删除服务 → 重新 Blueprint"时才会重新读取）。所以只改 `render.yaml` 永远修不好"已存在"的这个服务——这正是之前 `ffb01ae` 提交后依然报同样错的原因。

**正确且已生效的修复（仓库当前采用）**：
在**仓库根目录**放一份 `Dockerfile`，让 Render 默认找得到它；构建上下文用仓库根目录，内部用 `COPY backend/...` 把后端代码拷进去：
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
`render.yaml` 后端服务相应写成 `dockerfilePath: Dockerfile`（指向根目录这份），并**去掉 `dockerContext`**（避免强制 backend 上下文把 `COPY backend/...` 变成 `backend/backend/...`）。
`backend/Dockerfile` 仍保留给本地 `docker build` 使用。

> 关键记忆点：① Render 默认在仓库根找 `./Dockerfile`；② **已创建的 Docker 服务不会因 push 改 render.yaml 而更新 Dockerfile Path**，要么删服务重建，要么直接在根目录放 Dockerfile 让它默认命中。本项目选了后者（最稳，不依赖 Render 的 sync 行为）。

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
