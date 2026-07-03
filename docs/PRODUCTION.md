# AI-Companion-OS — Production Guide

## Production stack (canonical)

| Component | Path | Port |
|-----------|------|------|
| **Chat API** | `v2/backend` | 8000 (internal) |
| **Web UI** | `v2/frontend` + Nginx | 80 |
| **Compose file** | `docker-compose.yml` | — |
| **Database** | SQLite `data/companion.db` | volume |

**V3** (`v3/`) is experimental (LifeKernel, Postgres). Do **not** use it as the default production entry unless explicitly migrating.

## Deploy (server)

```bash
cd /opt/AI-Companion-OS
git pull origin main

# Ensure .env exists (never commit .env)
cp -n .env.example .env   # first time only, then edit keys

docker compose up -d --build
docker compose ps
curl -s http://127.0.0.1/api/health
```

Public access: `http://YOUR_SERVER/` (port 80).

## Required `.env` keys

```env
DEEPSEEK_API_KEY=...
SILICONFLOW_API_KEY=...          # image generation
IMAGE_CONTENT_MODE=unrestricted
LLM_PROVIDER=deepseek
CONTENT_MODE=unrestricted
RESET_WORLD_ON_START=false       # set true only for one-time reset
```

## Features (V2 production)

- Private & group chat with DeepSeek/Qwen, streaming WS
- Relationship, emotion, arousal, growth engines
- **Natural chat photos**: say「发张自拍」or character uses `[PHOTO:...]` tag
- **SiliconFlow** Qwen-Image-Edit with reference templates
- **LifeScheduler**: absence emotion drift + occasional proactive messages
- **Visual memory**: generated photos stored in `character_memories`
- Character panel: stats, memories, **album grid**

## Character reference images

Place one JPG per character:

```text
config/character_templates/{character_id}.jpg
```

Update `config/visual/character_photo_templates.yaml` — one template per character (no sharing).

Image prompts: `config/visual/character_image_prompts.yaml` (runtime)  
Full reference doc: `config/visual/character_nude_prompts.md`

## API quick reference

| Endpoint | Purpose |
|----------|---------|
| `GET /api/health` | Status + LLM + image enabled |
| `WS /ws/chat/{character_id}` | Private chat |
| `POST /api/v4/image/generate` | Manual image generation |
| `GET /api/v4/image/album/{character_id}` | Photo history |

## Security

- Do **not** expose port 8000 publicly long-term; use Nginx on 80/443 only.
- Never commit `.env` or deploy scripts with passwords.
- `data/` and `data/albums/` are gitignored.

## Local dev

```bash
cd v2/backend
pip install -r ../requirements.txt
# from repo root, with .env present
uvicorn main:app --app-dir v2/backend --reload
```

Frontend: `cd v2/frontend && npm install && npm run dev`
