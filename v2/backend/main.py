"""
AI Companion OS V2 — FastAPI 主入口
完整调用链：
  用户消息 → EventBus → EventAnalyzer → 关系引擎/情绪引擎 → LLM → WS 响应
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.rest_routes import router as rest_router
from api.ws_routes import router as ws_router
from bootstrap import init_all
from config import SERVER_HOST, SERVER_PORT


@asynccontextmanager
async def lifespan(app: FastAPI):
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

app.include_router(rest_router)
app.include_router(ws_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=SERVER_HOST, port=SERVER_PORT, reload=True)
