# 构建上下文为仓库根目录（Render 默认在仓库根找 ./Dockerfile）。
# 后端服务代码位于 backend/，因此这里用 COPY backend/... 把后端拷进镜像。
FROM python:3.11-slim

WORKDIR /app

# 后端依赖清单
COPY backend/requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# 后端全部代码（app/、prompts/ 等）
COPY backend/ .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
