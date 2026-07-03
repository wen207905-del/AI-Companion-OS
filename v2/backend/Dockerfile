# AI-Companion-OS V2 Backend
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY v2/requirements.txt ./v2/requirements.txt
RUN pip install --no-cache-dir -r v2/requirements.txt

COPY v2/backend ./v2/backend
COPY config ./config

ENV PYTHONPATH=/app/v2/backend
WORKDIR /app/v2/backend

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
