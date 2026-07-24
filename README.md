# AI Shop Analyzer

上传店铺/达人数据（CSV/Excel）→ Pandas 清洗聚合 → LLM 深度分析 → 生成周报/月报。

## 架构

- **前端**: Next.js 14 (App Router) + TailwindCSS + Recharts
- **后端**: FastAPI + Pandas + SQLAlchemy 2.0
- **数据库**: 开发默认 SQLite（零配置），生产切 PostgreSQL
- **AI**: OpenAI 兼容接口（支持 DeepSeek / 通义 / Kimi 等）

数据安全：原始大表只存本地，发给 LLM 的只有聚合后的 JSON 摘要。

## 快速启动

### 1. 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env         # 填入你的 OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

接口文档：http://localhost:8000/docs

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000（API 请求通过 Next.js rewrite 代理到 8000 端口，无跨域问题）

### 3. （可选）切换 PostgreSQL

```bash
docker compose up -d          # 启动 postgres:16
```

然后把 `backend/.env` 中的 `DATABASE_URL` 改为：

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/shop_analyzer
```

## API 一览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/upload | 上传文件（form: file + data_type=shop\|creator），返回预处理摘要 |
| GET  | /api/datasets | 数据集列表 |
| POST | /api/analyze/{dataset_id} | 创建分析任务（body: report_type=weekly\|monthly），后台调 LLM |
| GET  | /api/reports/{id} | 查询报告（前端轮询 status，done 后渲染 content_md） |

## 数据格式说明

预处理器自动识别中英文表头别名（GMV/销售额/成交金额、订单数、达人昵称、ROI/投产比 等），
自动处理 `¥1,234`、`12.3%`、`1.2万` 等脏数据格式，CSV 自动检测 UTF-8/GBK 编码。

- **店铺数据**摘要：总GMV、订单数、客单价、转化率、Top10商品、日GMV趋势、峰谷日
- **达人数据**摘要：达人数、出单率、平均/中位ROI、ROI分布、Top10达人

## 目录结构

```
backend/
  app/
    main.py               # FastAPI 入口
    api/                  # upload / analyze / reports 路由
    services/
      preprocessor.py     # ★ Pandas 清洗聚合核心
      llm_service.py      # LLM 调用
    models/               # SQLAlchemy ORM
    schemas/              # Pydantic
  prompts/                # System Prompt 模板（店铺/达人）
frontend/
  app/                    # 首页 + 报告详情页
  components/upload/      # ★ 拖拽上传组件
  lib/api.ts              # API 封装
```

## 下一步计划

- [ ] Recharts 图表组件（GMV 趋势线、Top10 柱状图、ROI 分布饼图）
- [ ] Shadcn UI 完整接入（`npx shadcn@latest init`）
- [ ] 周报/月报对比（环比数据）
- [ ] Alembic 数据库迁移
- [ ] 用户认证

---

# 企业版 v2 · 端到端实跑（通义千问 + 飞书 + Celery）

> 核心链路：适配器/ Mock 数据 → `standard_*` 表 → `ai_tools` 数据库层聚合 →
> 通义千问 `qwen-max` Function Calling 生成报告 → 飞书交互卡片推送。
> 数据库用 SQLite（零依赖），只需 Redis 跑 Celery 异步/定时任务。

## 1. 一条龙安装与启动

```bash
cd backend

# (a) 安装依赖（含 dashscope / celery / redis）
pip install -r requirements.txt

# (b) 配置环境变量
cp .env.example .env
# 然后用编辑器打开 .env，填入：
#   DASHSCOPE_API_KEY=sk-xxx          # 阿里云百炼控制台获取
#   FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
#   FEISHU_WEBHOOK_SECRET=            # 飞书安全设置开启签名时填，否则留空
# （数据库默认 sqlite:///./dev.db，无需改）

# (c) 准备数据：建表 + 灌入高质量 Mock 数据（1200 单/50 商品/20 达人，含二八分布+水军）
python scripts/generate_mock_data.py

# (d) 启动 Redis（需要 Docker Desktop）
docker compose up -d

# (e) 同步跑通端到端日报（模拟 Celery 定时任务，不依赖 Celery 进程）
python scripts/test_e2e_daily_report.py
```

脚本会自动：查近 30 天聚合 → 调通义千问生成报告 → 推送飞书卡片，并打印执行摘要。

## 2. 三种运行模式

| 命令 | 场景 |
|------|------|
| `python scripts/test_e2e_daily_report.py` | 真实跑：需 `.env` 配好 `DASHSCOPE_API_KEY` + `FEISHU_WEBHOOK_URL` |
| `python scripts/test_e2e_daily_report.py --mock` | 无 Key 也能验证整条链路（内置 mock 报告，仍真实查库+真实组装卡片） |
| `python scripts/test_e2e_daily_report.py --no-push` | 生成报告但不推飞书，仅打印卡片 JSON，方便预览手机端效果 |

> 没填 Key / Webhook 时会自动降级：报告用 mock、卡片只打印不推送——方便你先确认链路。

## 3. 真正跑 Celery 定时任务（每天凌晨 2 点自动日报）

```bash
# 终端 1：Worker
celery -A app.tasks.celery_app.celery_app worker -l info

# 终端 2：Beat 定时调度（crontab(hour=2, minute=0) 触发 daily_report_task）
celery -A app.tasks.celery_app.celery_app beat -l info

# 或手动触发一次：
celery -A app.tasks.celery_app.celery_app call app.tasks.scheduled.daily_report_task
```

`app/tasks/scheduled.py` 的 `daily_report_task` 与 `scripts/test_e2e_daily_report.py`
走同一套 `ai_tools` + `ai_engine` + `feishu`，区别仅在于前者由 Celery 异步调度。

## 4. 飞书卡片说明
`app/services/feishu.py` 的 `build_daily_report_card` 生成移动端友好的交互卡片：
- 核心指标 **GMV（红色加粗）/ 订单数 / 客单价** 一目了然
- 疑似水军达人用 **🚨 + 红色文本** 标出，命中即整卡头部变红预警
- `wide_screen_mode` 适配手机横竖屏

## 5. 关键文件
- `scripts/generate_mock_data.py` — 高质量 Mock 数据生成器（二八定律 + 水军达人）
- `scripts/test_e2e_daily_report.py` — 端到端实跑脚本（本步交付）
- `app/services/ai_tools.py` — 数据库层 ORM 聚合（严禁拉明细进内存）
- `app/services/ai_engine.py` — 通义千问 Function Calling 核心
- `app/services/feishu.py` — 飞书 Webhook 推送 + 日报表卡片
- `app/tasks/` — Celery 配置与每日 02:00 定时任务
- `docker-compose.yml` — 仅 Redis 服务
