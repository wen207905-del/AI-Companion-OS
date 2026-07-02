# AI Companion OS — V2.3 开发指南

多角色 AI 陪伴系统：事件驱动关系/情绪引擎、长期记忆、群聊 2.0、LLM 流式输出。

**当前版本：v2.3.0**（与 `GET /api/health` 的 `version` 字段一致）

## 环境要求

- Python 3.10+
- Node.js 18+
- Ollama（推荐，本地私聊）
- DeepSeek / Qwen API Key（可选，群聊决策与云端模型）

## 快速启动

### 1. 配置环境变量

在项目根目录复制 `.env.example` 为 `.env`，按需填写 API Key 与模型。

### 2. 一键启动（Windows）

```cmd
cd D:\AI-Companion-OS\v2
start.bat
```

或 PowerShell：`.\start.ps1`

浏览器打开 http://127.0.0.1:3000（后端 8000，前端 3000）。

### 3. 手动启动

```powershell
# 后端
pip install -r v2\requirements.txt
cd v2\backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 前端
cd v2\frontend
npm install
npm run dev
```

## 目录结构

```
v2/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── bootstrap.py         # DB / 引擎 / 事件总线初始化
│   ├── app_state.py         # 全局状态
│   ├── api/
│   │   ├── rest_routes.py   # REST API
│   │   └── ws_routes.py     # WebSocket 私聊 / 群聊
│   ├── chat/                # Prompt、回复、群聊、流式投递
│   ├── engine/              # 关系、情绪、边界、成长
│   ├── memory/              # 长期记忆存储与召回
│   ├── llm/                 # Ollama / OpenAI 兼容路由
│   └── tests/               # pytest（37 项）
├── frontend/                # Svelte SPA
├── requirements.txt
├── start.bat / start.ps1
└── CHANGELOG.md
```

角色 YAML 在根目录 `config/personas/`，数据库在 `data/companion.db`。

## 主要功能

| 模块 | 说明 |
|------|------|
| 私聊 / 群聊 | WebSocket 实时对话，每会话可独立选 LLM |
| 流式输出 | `LLM_STREAM=true` 时 WS 推送 `stream_start` / `stream_delta` / `stream_end` |
| 长期记忆 | 关键词召回，注入 Prompt；角色面板显示近期记忆 |
| 边界 / 成长 | taboo 触发情绪反应；XP 等级与里程碑 |
| 群聊 2.0 | 多群、新建群、成员管理、角色接话链 |

## API 概览

| 端点 | 说明 |
|------|------|
| `GET /api/health` | 健康检查 + LLM 状态 |
| `GET /api/characters` | 角色列表 |
| `GET /api/character/{id}` | 角色详情（关系、情绪、成长、记忆） |
| `GET /api/chat/{id}/history` | 私聊历史 |
| `GET /api/groups` | 群列表 |
| `POST /api/groups` | 新建群 `{name, member_ids}` |
| `GET /api/group/{id}` | 群详情与成员 |
| `POST /api/group/{id}/members` | 添加成员 |
| `DELETE /api/group/{id}/members/{char}` | 移除成员 |
| `GET /api/dashboard` | 总览（等级、好感等） |
| `WS /ws/chat/{id}` | 私聊 |
| `WS /ws/group/{id}` | 群聊 |

错误响应使用标准 HTTP 状态码（`HTTPException`），如 404 `character not found`。

## 测试

```powershell
cd v2\backend
python -m pytest tests/ -v
```

测试覆盖：

- REST API 集成（`test_api.py`）
- 12 人 persona YAML 校验（`test_personas.py`）
- Prompt 快照防回归（`test_prompt_snapshots.py`）
- 记忆、边界、成长、历史加载等单元测试

## CI

GitHub Actions 工作流 `.github/workflows/ci.yml`：

- **backend**：`pip install -r v2/requirements.txt` → `pytest tests/`
- **frontend**：`npm ci` → `npm run build`

推送至 `main` / `master` 或 PR 时自动运行。

## 常见问题

**Ollama 连不上** — 确认 `ollama serve` 已运行，`LLM_BASE_URL` 指向 `http://127.0.0.1:11434/v1`。

**群聊决策慢** — 辅助任务走 `LLM_AUX_PROVIDER`（默认 DeepSeek），需配置 `DEEPSEEK_API_KEY`。

**群聊为空** — 启动时 `bootstrap` 只从数据库加载已有群成员，不会自动创建「全员群」；请在前端侧栏新建群聊并添加成员。

**流式不生效** — 检查 `.env` 中 `LLM_STREAM=true`，并确认所用 provider 支持 stream。

## 文档

- 根目录 [README.md](../README.md) — 项目总览
- [CHANGELOG.md](./CHANGELOG.md) — 版本变更
- [docs/V2-完整架构设计文档.md](../docs/V2-完整架构设计文档.md) — 架构设计
