# Changelog

## v2.3.0 — 记忆、引擎、群聊 2.0

### 版本与文档
- 统一应用版本号为 `2.3.0`（`config.APP_VERSION`、health API、前端 `package.json`）
- pytest 扩展至 37 项；同步 README 与 bootstrap 群聊行为说明

### 长期记忆（B1）
- `memory/memory_manager.py`：对话快照存储与关键词召回
- `chat/context_builder.py`：记忆块注入 Prompt
- 角色详情 API 与面板展示「近期记忆」

### 引擎接线（B2）
- `boundary_engine`：persona taboo 触发情绪/关系联动
- `growth_engine`：XP、等级、里程碑；Dashboard 显示等级

### 群聊 2.0（B3）
- 多群聊：创建群、成员增删 REST API
- 角色接话链：`decide_character_chain` / `maybe_run_character_chain`
- 前端侧栏群列表

## v2.2 — 流式输出（A1）

### 后端
- `llm/ollama.py`、`openai_compat.py` 支持 stream
- `chat/stream_delivery.py`：流式片段投递
- WebSocket 事件：`stream_start`、`stream_delta`、`stream_end`
- 配置项 `LLM_STREAM`（默认 `true`）

### 前端
- `MessageBubble.svelte`、`Chat.svelte` 逐字显示
- `chat.js` 处理流式 WS 事件

## v2.1 — 架构与角色数据

### 架构拆分（P2）
- `main.py` 精简；`bootstrap.py`、`app_state.py`
- `api/rest_routes.py`、`api/ws_routes.py`
- `chat/reply_service.py` 回复编排

### 角色与 Prompt
- 12 人完整 persona：`body_experiences`、`character_relations`、`chat_behavior`
- 群聊并行生成、错峰推送、typing 指示
- 辅助 LLM 通道（群聊决策、内心独白）

### 测试
- pytest 从 11 项扩展至 36 项（v2.3 继续增至 37 项）

## v2.0 — 初始 V2

- FastAPI + WebSocket 私聊 / 群聊
- Ollama / DeepSeek / Qwen 多引擎路由
- 关系引擎、情绪引擎、事件总线
- Svelte 前端 SPA
- 每会话独立 LLM 选择

## v3.0（计划中）

- CI 流水线与文档（C 计划）— 已完成
- 视觉头像接入（A2，待人物模版）
- PWA、语音等扩展（D 计划）
