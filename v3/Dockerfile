# AI-Companion-OS V3 — 生产级 Docker 镜像
FROM python:3.11-slim

# 系统依赖（curl 供 healthcheck 使用）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt ./v3/requirements.txt
RUN pip install --no-cache-dir -r v3/requirements.txt

# 复制 v3 包，保持包结构以支持相对导入
COPY . ./v3/

RUN mkdir -p v3/logs v3/data

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "v3.main:app", "--host", "0.0.0.0", "--port", "8000"]
