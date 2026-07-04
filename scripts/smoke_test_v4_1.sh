#!/usr/bin/env bash
# V4.1 服务器冒烟测试 — 部署后或日常巡检
set -euo pipefail

BASE="${BASE:-http://127.0.0.1}"
FAIL=0

pass() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; FAIL=1; }
check_json() { python3 - "$@" <<'PY'
import json, sys
data = json.load(sys.stdin)
path = sys.argv[1].split(".")
cur = data
for p in path:
    cur = cur[p]
print(cur)
PY
}

echo "==> V4.1 smoke test @ $BASE"

# 1. Health
if curl -sf "$BASE/api/health" >/tmp/smoke_health.json; then
  status="$(python3 -c "import json; print(json.load(open('/tmp/smoke_health.json'))['status'])")"
  if [[ "$status" == "ok" ]]; then pass "GET /api/health status=ok"; else fail "health status=$status"; fi
  img="$(python3 -c "import json; print(json.load(open('/tmp/smoke_health.json'))['image']['enabled'])")"
  echo "       image.enabled=$img (生图需 SILICONFLOW_API_KEY)"
else
  fail "GET /api/health unreachable"
fi

# 2. Characters — V4.1 fields
if curl -sf "$BASE/api/characters" >/tmp/smoke_chars.json; then
  python3 <<'PY'
import json, sys
data = json.load(open("/tmp/smoke_chars.json"))
chars = {c["id"]: c for c in data.get("characters", [])}
required = [
    "social_relation_label", "affection_score", "affection_grade",
    "affection_label", "current_activity", "is_friendship", "mood",
]
missing = []
for cid, c in chars.items():
    for k in required:
        if k not in c:
            missing.append(f"{cid}.{k}")
if missing:
    print("[FAIL] /api/characters 缺字段:", ", ".join(missing[:8]))
    sys.exit(1)
# spot checks from relationship_init.yaml
checks = {
    "wang_dahai": ("兄弟", "铁哥们", True),
    "ye_ruxue": ("继母·恋子", "在意", False),
    "bai_rou": ("老婆型伴侣", "深恋", False),
}
for cid, (rel, grade, friendship) in checks.items():
    c = chars.get(cid)
    if not c:
        print(f"[FAIL] missing character {cid}")
        sys.exit(1)
    if c.get("social_relation_label") != rel:
        print(f"[WARN] {cid} social_relation_label={c.get('social_relation_label')} (expected {rel})")
    if c.get("affection_grade") != grade:
        print(f"[WARN] {cid} affection_grade={c.get('affection_grade')} (expected {grade}) — 若未 reset 可能仍是旧库")
    if c.get("is_friendship") != friendship:
        print(f"[WARN] {cid} is_friendship={c.get('is_friendship')} (expected {friendship})")
print("[PASS] GET /api/characters V4.1 fields present")
PY
else
  fail "GET /api/characters unreachable"
fi

# 3. Mode API
if curl -sf "$BASE/api/v4/mode?character_id=ye_ruxue" >/tmp/smoke_mode.json; then
  pass "GET /api/v4/mode"
else
  fail "GET /api/v4/mode"
fi

# 4. Character DM list (read-only API)
if curl -sf "$BASE/api/v4/character-dm/list" >/tmp/smoke_dm.json; then
  pass "GET /api/v4/character-dm/list"
else
  fail "GET /api/v4/character-dm/list"
fi

# 5. Image status
if curl -sf "$BASE/api/v4/image/status" >/tmp/smoke_img.json; then
  pass "GET /api/v4/image/status"
else
  fail "GET /api/v4/image/status"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "Smoke test: ALL PASS (warnings above are OK if DB not reset yet)"
else
  echo "Smoke test: FAILED — check docker logs ai_companion_v2_api"
  exit 1
fi
