#!/usr/bin/env bash
# V4.1 服务器部署脚本 — 在 /opt/AI-Companion-OS 下执行
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/AI-Companion-OS}"
BRANCH="${BRANCH:-v4.1-character-reality}"
BACKUP_DIR="${BACKUP_DIR:-$REPO_DIR/data/backup}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

echo "==> AI-Companion-OS V4.1 deploy"
echo "    repo:   $REPO_DIR"
echo "    branch: $BRANCH"

cd "$REPO_DIR"

if [[ ! -f .env ]]; then
  echo "ERROR: .env 不存在。请先: cp .env.example .env 并填入 API Key"
  exit 1
fi

mkdir -p "$BACKUP_DIR"
if [[ -f data/companion.db ]]; then
  cp -a data/companion.db "$BACKUP_DIR/companion.db.$TIMESTAMP"
  echo "==> 已备份 data/companion.db -> $BACKUP_DIR/companion.db.$TIMESTAMP"
fi

echo "==> git fetch & checkout"
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"

echo "==> docker compose rebuild"
docker compose down
docker compose up -d --build --force-recreate

echo "==> waiting for health (max 90s)"
for i in $(seq 1 18); do
  if curl -sf "http://127.0.0.1/api/health" >/dev/null 2>&1; then
    echo "==> health OK"
    break
  fi
  sleep 5
  if [[ "$i" -eq 18 ]]; then
    echo "ERROR: health check timeout"
    docker compose ps
    docker logs --tail 80 ai_companion_v2_api || true
    exit 1
  fi
done

echo "==> smoke test"
bash "$REPO_DIR/scripts/smoke_test_v4_1.sh"

echo ""
echo "Deploy complete."
echo "  Web:    http://$(hostname -I 2>/dev/null | awk '{print $1}')/"
echo "  Health: curl -s http://127.0.0.1/api/health | head"
echo ""
echo "如需 V4.1 关系初始化（会清空聊天记录）:"
echo "  docker exec -it ai_companion_v2_api python scripts/reset_world.py"
echo "  docker compose restart api"
