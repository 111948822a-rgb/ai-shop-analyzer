# =============================================================================
# AI Shop Analyzer —— 后端 (FastAPI) 多阶段构建镜像
# 基础镜像：python:3.11-slim
# 构建上下文：backend/ 目录（Render 的 dockerfilePath 指向此文件）
# =============================================================================

# ---------- Stage 1: builder（仅用于编译/安装依赖，不进最终镜像）----------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# 构建期可能需要的编译工具（psycopg2-binary 自带 wheel，通常无需编译，
# 但保留以兼容个别需要编译的包）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential \
    && rm -rf /var/lib/apt/lists/*

# 先把依赖清单拷进来，利用 Docker 层缓存（仅 requirements.txt 变动时才重装）
COPY requirements.txt ./requirements.txt

# 安装到独立 venv，便于最终阶段只拷贝 venv，避免把 build-essential 带进运行时
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -r requirements.txt

# ---------- Stage 2: runtime（精简运行时）----------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# 运行时只需 libpq（psycopg2-binary 自带，但保留以防万一）；无需 gcc
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# 拷贝构建阶段装好的 venv
COPY --from=builder /opt/venv /opt/venv

# 拷贝应用代码（backend/ 下的内容，含 app/ 与 requirements.txt）
# 安全：不拷贝 .env / *.db / __pycache__（见 .dockerignore）
COPY app /app/app
COPY requirements.txt /app/requirements.txt

EXPOSE 8000

# 绑定 Render 注入的 $PORT（默认 8000）；healthcheck 由 Render 配置指向 /api/health
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
