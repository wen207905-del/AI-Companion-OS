# AI-Companion-OS — V2.3

多角色 AI 陪伴系统：事件驱动关系/情绪引擎 + 本地 Ollama / DeepSeek LLM + Svelte 前端。

**当前版本：v2.3.0**

## 环境要求

- Python 3.10+
- Node.js 18+
- **Ollama**（推荐，本地私聊）— 已安装并拉取模型
- DeepSeek API Key（可选，用于群聊决策、内心独白等辅助任务）

## 快速启动

### 0. 确保 Ollama 在运行

```powershell
ollama list
# 应能看到 huihui_ai/qwen2.5-abliterate:7b
```

### 1. 配置 `.env`

复制 `.env.example` 为 `.env`，按需修改。默认：

- 私聊 → 本地 Ollama（`huihui_ai/qwen2.5-abliterate:7b`）
- 群聊决策 / 内心独白 → DeepSeek（需 `DEEPSEEK_API_KEY`）

### 2. 一键脚本（Windows）

**CMD 命令提示符**（你当前用的这种）：

```cmd
cd D:\AI-Companion-OS\v2
start.bat
```

**PowerShell**：

```powershell
cd D:\AI-Companion-OS\v2
.\start.ps1
```

会弹出两个窗口（Backend + Frontend），浏览器打开 http://127.0.0.1:3000

### 3. 分别启动

**后端**（端口 8000）：

```powershell
cd D:\AI-Companion-OS
pip install -r v2\requirements.txt
cd v2\backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**前端**（端口 3000，代理 `/api` 和 `/ws` 到 8000）：

```powershell
cd D:\AI-Companion-OS\v2\frontend
npm install
npm run dev
```

浏览器打开 http://127.0.0.1:3000

验证 LLM 配置：`GET http://127.0.0.1:8000/api/health`

## 项目结构

```
AI-Companion-OS/
├── config/
│   ├── personas/          # 12 个角色 YAML
│   └── visual/            # 角色视觉参考配置
├── docs/                  # 架构与设计文档
├── data/                  # SQLite 数据库（自动生成）
└── v2/
    ├── backend/           # FastAPI + WebSocket
    │   ├── main.py        # 主入口
    │   ├── engine/        # 关系/情绪引擎
    │   ├── event/         # 事件总线与分析器
    │   ├── chat/          # Prompt 构建、历史加载、群聊、流式
    │   ├── memory/        # 长期记忆
    │   └── tests/         # pytest（37 项）
    ├── frontend/          # Svelte SPA
    ├── README.md            # V2 开发指南
    ├── CHANGELOG.md         # 版本变更
    └── requirements.txt
```

## API 概览

| 端点 | 说明 |
|------|------|
| `GET /api/health` | 健康检查 + LLM 状态 |
| `GET /api/llm/providers` | 可用 AI 引擎列表 |
| `GET /api/llm/pref/{private\|group}/{id}` | 读取该会话的 LLM 选择 |
| `PUT /api/llm/pref/{private\|group}/{id}` | 保存该会话的 LLM 选择 |
| `GET /api/characters` | 角色列表 |
| `GET /api/character/{id}` | 角色详情 + 关系/情绪/成长/记忆 |
| `GET /api/chat/{id}/history` | 私聊历史 |
| `GET /api/groups` | 群列表 |
| `POST /api/groups` | 新建群聊 |
| `GET /api/group/{id}` | 群详情与成员 |
| `GET /api/dashboard` | 总览（等级、好感等） |
| `WS /ws/chat/{id}` | 私聊（支持流式 `stream_delta`） |
| `WS /ws/group/{id}` | 群聊（角色接话链） |

## 配置

根目录 `.env`（参考 `.env.example`）：

```
# 私聊主模型 — 本地 Ollama
LLM_PROVIDER=ollama
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_MODEL=huihui_ai/qwen2.5-abliterate:7b
CONTENT_MODE=unrestricted

# 辅助任务（群聊决策、内心独白）
DEEPSEEK_API_KEY=sk-...
LLM_AUX_PROVIDER=deepseek

# Qwen（阿里云 MaaS）
QWEN_API_KEY=sk-...
QWEN_BASE_URL=https://ws-xxx.cn-beijing.maas.aliyuncs.com
QWEN_MODEL=qwen3.7-plus

SERVER_PORT=8000
```

**每个私聊/群聊**可在界面右上角 🤖 按钮独立切换 Ollama / DeepSeek / Qwen，选择会自动保存。

| 变量 | 说明 |
|------|------|
| `LLM_PROVIDER` | 默认引擎：`ollama` / `deepseek` / `qwen` |
| `LLM_MODEL` | 默认模型名 |
| `QWEN_API_KEY` | 阿里云 Qwen API Key |
| `QWEN_BASE_URL` | MaaS 推理地址（OpenAI 兼容） |
| `QWEN_MODEL` | 如 `qwen3.7-plus` |
| `CONTENT_MODE` | `unrestricted` 私聊无审查；`standard` 默认 |
| `LLM_STREAM` | `true` 启用 WS 流式输出（默认开启） |
| `LLM_OLLAMA_MODELS` | Ollama 可选模型列表（逗号分隔，勿用 Windows 的 `OLLAMA_MODELS` 路径变量） |

## 测试与 CI

```powershell
cd v2\backend
python -m pytest tests/ -v
```

GitHub Actions（`.github/workflows/ci.yml`）在 push/PR 时自动运行后端 pytest 与前端 `npm run build`。

详见 `v2/README.md` 与 `v2/CHANGELOG.md`。

## 文档

详见 `docs/V2-完整架构设计文档.md`
