# AI-Companion-OS V3 — 生产级 Docker 镜像
FROM python:3.11-slim

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 创建日志目录
RUN mkdir -p logs

# 暴露端口
EXPOSE 8000

# 启动 FastAPI 服务
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
