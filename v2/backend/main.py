"""
AI Companion OS V2 — FastAPI 主入口
完整调用链：
  用户消息 → EventBus → EventAnalyzer → 关系引擎/情绪引擎 → LLM → WS 响应
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.rest_routes import router as rest_router
from api.ws_routes import router as ws_router
from bootstrap import init_all
from config import SERVER_HOST, SERVER_PORT
from personality.photo_templates import template_dir


def _maybe_reset_world() -> None:
    if os.getenv("RESET_WORLD_ON_START", "").lower() not in ("1", "true", "yes"):
        return
    from scripts.reset_world import main as reset_main

    reset_main()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _maybe_reset_world()
    init_all()
    yield


app = FastAPI(title="AI Companion OS V2.3", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_templates = template_dir()
if _templates.is_dir():
    app.mount(
        "/static/character_templates",
        StaticFiles(directory=str(_templates)),
        name="character_templates",
    )

app.include_router(rest_router)
app.include_router(ws_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=SERVER_HOST, port=SERVER_PORT, reload=True)
