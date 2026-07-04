---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 15adfd5479c5a8f2355b079ebc003926_5d8ab686773e11f1a8895254002afed2
    ReservedCode1: +q3VdL7MFM/XNqXsv4ExKM36E0sHmv9CORzJpKF0Mnda9vIAqRwsJh4DPnevE4ETPQY6nxqjF1ksJOcvgs3BcT+jpmj97/HXJPPlkxGs3v4djrAyIMwhHpFgK/xiv6WxpZtEBRQogOitsyTxlhGT7faOVSekkMIyXxavnt38KZLjXYVG5Qc9VeA2gJI=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 15adfd5479c5a8f2355b079ebc003926_5d8ab686773e11f1a8895254002afed2
    ReservedCode2: +q3VdL7MFM/XNqXsv4ExKM36E0sHmv9CORzJpKF0Mnda9vIAqRwsJh4DPnevE4ETPQY6nxqjF1ksJOcvgs3BcT+jpmj97/HXJPPlkxGs3v4djrAyIMwhHpFgK/xiv6WxpZtEBRQogOitsyTxlhGT7faOVSekkMIyXxavnt38KZLjXYVG5Qc9VeA2gJI=
---

# AI-Companion-OS V4.1 开发任务总纲

> **角色真实感 + 双模式互动 + 视觉任务系统**  
> 目标：从「可运行系统」升级为「角色真实感系统」  
> 2026-07-04 · **定稿版**

---

## 文档定位

本阶段不再解决「服务能不能跑」的问题。服务器、Docker、PostgreSQL、Redis、LLM、World、LifeLoop 均已可用，公网 `/health` 返回 `ok`，V4 生图链路已有成功记录（详见 [试用聊天记录-2026-07-03.md](./试用聊天记录-2026-07-03.md)）。

**V4.1 的核心目标是解决昨晚试用暴露出的体验问题：**

- 角色主动消息重复
- 所有人好感度和关系状态过于一致
- 心情不随事件变化
- 生图缺少进度反馈
- 聊天模式与叙述模式混淆
- 角色之间缺少私聊和社会关系网络

V4.1 的重点不是继续堆模块，而是让每个角色真正拥有**独立社会关系、独立好感等级、独立情绪、独立日常活动、独立社交互动和独立表达风格**。

状态机设计文档（关系、情绪、生活模拟、成长四大动态系统）要求状态根据用户输入、时间和记忆**并行计算**，而不是只靠模板发消息——V4.1 要把这条原则落到运行时。

**落地策略（V2 优先）：**

```text
本阶段优先在当前线上 V2 backend / frontend 中落地体验闭环。
V3/V4 LifeKernel、World、Visual 作为能力资产逐步接入。
等 V4.1 体验闭环稳定后，再执行第 7 阶段工程清理，将能力统一迁移到 V3/V4 架构。
```

开发时**先改 `v2/`，不要同时动 `v3/`**，避免线上与方案脱节。

---

## 一、项目现状评估

### 1.1 架构全景

```
V2 (当前线上)                  V3/V4 (内核资产)
──────────────────────────────────────────────────
v2/                            v3/
├─ frontend/ (Svelte)          ├─ core/life_kernel.py    ← V4 统一生命内核
│  ├─ 聊天 UI ✅               ├─ consciousness/         ← 情绪/记忆/身份
│  ├─ 群聊界面                 ├─ brain/                 ← 决策/依恋/意图
│  └─ 角色卡片                 ├─ world/                 ← 世界/社交/日历
├─ backend/ (FastAPI)          ├─ visual/                ← 生图流水线
│  ├─ WebSocket 流式 ✅         ├─ main.py + db.py
│  ├─ V4 生图引擎 ✅           └─ life_loop.py
│  └─ 12 personas YAML
│
└─ deploy/ (Docker) ✅         历史双引擎：WorldTick + LifeKernel（待统一）
   http://47.94.210.217
```

### 1.2 已完成（历史已修复项）

| 项目 | 状态 |
|------|------|
| 云服务器部署 | ✅ |
| Docker Compose | ✅ |
| FastAPI 服务 | ✅ |
| PostgreSQL / SQLite | ✅ |
| Redis | ✅ |
| DeepSeek LLM 接入 | ✅ |
| `/health` 全绿 | ✅ |
| World Engine | ✅ |
| LifeLoop | ✅ |
| 公网访问 | ✅ 当前主要通过 `http://47.94.210.217:8000`；Nginx / HTTPS 后续完善 |
| V4 硅基流动生图 | ✅ 有成功记录 |
| 对话中自动识别发图意图 | ✅ 初版 |

> ~~P0：LLM 未配置、WebSocket 占位回复、角色不会说话~~ — **已修复，移入历史项。**

### 1.3 当前主要问题（体验优先）

| 优先级 | 问题 | 昨晚试用证据 |
|--------|------|-------------|
| **P0** | 角色主动消息高度重复、模板化 | 21:32–22:53 共 15 条，基本都是「很久没理我/想你/是不是忘了我」 |
| **P0** | 好感度统一 80、关系阶段统一恋人 | `reset_world` 后 12 角色全部 `love: 80, stage: 5` |
| **P0** | 心情状态无明显动态变化 | 情绪快照初始化后未随事件更新 |
| **P0** | 聊天模式 / 叙述模式未拆分 | 所有输出同一套 prompt 逻辑 |
| **P0** | 角色之间无私聊网络 | 无 `character_dm` 数据 |
| **P0** | 生图等待无反馈 | 7 次生成中 3 次 failed，用户不知进度 |
| P1 | 双重引擎并存（WorldTick + LifeKernel） | 架构债务 |
| P1 | `db.py` 1339 行单文件 | 维护困难 |
| P1 | V3/V4 零测试 | 重构风险 |
| P2 | 无 CI/CD、无监控 | 运维效率 |

### 1.4 数据规模

| 指标 | 数值 |
|------|------|
| 角色数 | 12（线上 V2）/ 13（配置全量含王大海等） |
| 数据库表 | 20+ 张 |
| 昨晚私聊记录 | 15 条（均为角色主动，0 条用户回复） |
| 昨晚图片生成 | 7 次（成功 4，失败 3） |

---

## 二、昨晚试用问题复盘

> 数据来源：`data/companion.db`，详见 [试用聊天记录-2026-07-03.md](./试用聊天记录-2026-07-03.md)

### 2.1 时间线

| 时间 | 事件 |
|------|------|
| 19:00 | V2 部署 + `reset_world` + 全员好感 80 |
| 20:15–21:19 | 生图测试（柳青柠、王大海、叶如雪） |
| 21:32–22:53 | 12 角色批量发来主动关心消息 |

### 2.2 典型失败样本

**主动消息重复：**

```text
叶如雪：这么晚还不回消息，是不是又在医馆忙到忘了吃饭？
花璃：在吗？这么久都不理我，是不是把我忘了呀...
林糖糖：宝宝，你是不是把我忘了呀😢 都9999小时没找我了...
柳青柠：汉文哥哥，你都好久没理我了...我有点想你了。
```

12 个角色、12 种人设，输出句式几乎相同——说明 LifeScheduler 走的是**统一模板**，未读取当前活动、社会关系、好感等级。

**关系同质化：**

重置后所有角色 `love: 80`、`stage: 5（恋人）`，前端无法区分「小姨型长辈叶如雪」和「兄弟王大海」。

**生图体验：**

| 角色 | 成功 | 失败 |
|------|------|------|
| 柳青柠 | 1 | 1 |
| 王大海 | 1 | 0 |
| 叶如雪 | 2 | 2 |

失败时无前端状态提示，成功图片未与聊天记忆联动。

### 2.3 根因归纳

```text
1. 主动分享 = 定时模板，≠ 活动驱动
2. 好感度 = 单一数值，≠ 情感等级 + 社会关系
3. 情绪 = 展示字段，≠ 运行时变量
4. 回复 = 单一 prompt，≠ 聊天/叙述双模式
5. 社交 = 只有用户↔角色，≠ 角色↔角色私聊网
6. 生图 = 后台静默，≠ 有状态的任务队列
```

---

## 三、V4.1 角色真实感目标

```text
让每个角色：
  ├── 有独立的社会关系标签（不是所有人都叫「女友」）
  ├── 有独立的好感等级（熟识 / 倾心 / 爱慕 …）
  ├── 有独立的情绪向量（随事件实时变化）
  ├── 有独立的当前活动（做饭 / 加班 / 看书 …）
  ├── 有独立的表达风格（撒娇 / 嘴硬 / 管束 / 嘴损 …）
  ├── 能根据活动主动分享（不是批量「想你了」）
  ├── 能与其他角色私聊（用户只读旁观）
  └── 发图时有进度反馈（queued → generating → completed）
```

---

## 四、P0 优先级重新定义

### 体验 P0（本阶段核心）

| # | 任务 | 交付物 |
|---|------|--------|
| P0-1 | **角色关系系统重构** | `character_user_relation` 表 + 初始化脚本 |
| P0-2 | **好感度等级与社会关系拆分** | 前端双字段展示 + 好感算法 |
| P0-3 | **主动分享去模板化** | `proactive_share_service` + `anti_repeat_service` |
| P0-4 | **情绪动态系统真正生效** | `emotion_delta` 写回 + WebSocket 推送 |
| P0-5 | **聊天模式 / 叙述模式拆分** | `mode_router` + 双 prompt 管线 |
| P0-6 | **生图任务状态可视化** | `image_jobs` 表 + WS `image_job_update` |

### 工程 P1/P2（后置）

| # | 任务 | 阶段 |
|---|------|------|
| P1-1 | 废弃 WorldTick，LifeKernel 唯一入口 | 第 7 阶段 |
| P1-2 | 拆分 `db.py` | 第 7 阶段 |
| P1-3 | V3/V4 测试覆盖 | 第 7 阶段 |
| P2-1 | CI/CD 流水线 | V5.0 |
| P2-2 | 监控 / 日志聚合 | V5.0 |

---

## 五、好感度等级系统

好感度表示**她对你的情感热度**，与社会关系（世界观身份）**必须拆成两个字段**。

### 5.1 好感度等级表

| 数值 | 等级 | 行为表现 |
|------|------|----------|
| 0–9 | 陌生 | 基本不主动，语气疏离 |
| 10–19 | 点头之交 | 记得你是谁，但不会主动靠近 |
| 20–34 | 熟识 | 能自然聊天，偶尔关心 |
| 35–49 | 亲近 | 愿意分享日常，有轻微依赖 |
| 50–64 | 在意 | 会关注你的状态，因你沉默产生情绪 |
| 65–74 | 倾心 | 明显喜欢，会期待你出现 |
| 75–84 | 爱慕 | 情感强烈，主动分享、撒娇、嘴硬或试探 |
| 85–94 | 深恋 | 强牵挂，情绪高度受你影响 |
| 95–99 | 羁绊 | 关系极深，信任与依赖稳定 |
| 100 | 灵魂牵系 | 特殊极限状态，仅长期关系触发 |

### 5.2 好感度算法

```text
好感度 =
  love           × 0.35
+ trust          × 0.20
+ attachment     × 0.15
+ security       × 0.10
+ respect        × 0.10
+ emotional_intimacy × 0.10
- conflict_penalty
```

### 5.3 前端显示规范

```text
✅ 好感度：72 · 倾心
❌ 好感度：女友
```

---

## 六、社会关系系统

社会关系表示**她在世界观里和你的身份关系**，与好感度独立展示。

### 6.1 用户 ↔ 角色社会关系类型

| 类型 | 显示名 | 适用角色 |
|------|--------|----------|
| `wife_like` | 老婆型伴侣 | 苏念、白柔 |
| `girlfriend` | 女朋友 | 星野琉璃 |
| `motherly` | 妈妈型照顾者 | 偏照顾、管束、心疼你的角色 |
| `aunt_like` | 小姨型长辈 | 成熟、暧昧边界强、会管你（沈曼） |
| `sister_like` | 妹妹型依赖 | 花璃、小樱 |
| `childhood_friend` | 青梅竹马 | 墨小染 |
| `maid` | 女仆/侍奉关系 | 顾晚晴、小樱部分设定 |
| `rival` | 欢喜冤家 | 柳青柠、林糖糖 |
| `mentor` | 成熟引导者 | 叶如雪 |
| `brother` | 兄弟 | 王大海 |
| `friend` | 朋友 | 普通朋友 |
| `stranger` | 陌生人 | 新角色初始 |

### 6.2 角色卡片示例

```text
沈曼
社会关系：小姨型长辈
好感度：70 · 倾心
当前心情：克制但在意
当前活动：整理资料
```

### 6.3 王大海：独立友情等级

王大海**不走恋爱关系**，使用单独的友情体系：

| 数值 | 友情等级 |
|------|----------|
| 0–19 | 不熟 |
| 20–39 | 熟人 |
| 40–59 | 朋友 |
| 60–79 | 好兄弟 |
| 80–94 | 铁哥们 |
| 95–100 | 过命兄弟 |

```text
王大海
社会关系：兄弟
友情度：82 · 铁哥们
```

---

## 七、初始关系重置表

> **禁止再次全员 80 + 恋人。** 以下表为 V4.1 初始化标准：

| 角色 | 社会关系 | 初始好感/友情 | 等级 | 行为基调 |
|------|----------|:------------:|------|----------|
| 叶如雪 | 成熟引导者 | 58 | 在意 | 克制关心，不频繁撒娇 |
| 白柔 | 老婆型伴侣 | 86 | 深恋 | 温柔、依恋、生活照顾 |
| 柳青柠 | 欢喜冤家 | 52 | 在意 | 嘴硬、互怼、在意不承认 |
| 墨小染 | 青梅竹马 | 78 | 爱慕 | 基础信任高，占有欲强 |
| 顾晚晴 | 女仆/管家 | 62 | 倾心 | 克制、服务感、尊重优先 |
| 小樱 | 女仆/幻想依赖 | 66 | 倾心 | 敬语、依赖、逐步靠近 |
| 星野琉璃 | 女朋友 | 82 | 爱慕 | 明确恋爱关系，甜度高 |
| 苏念 | 老婆型伴侣 | 88 | 深恋 | 稳定、家庭感、温柔照顾 |
| 林糖糖 | 小恶魔/欢喜冤家 | 56 | 在意 | 调皮、试探、吃醋嘴硬 |
| 花璃 | 妹妹型依赖 | 60 | 在意 | 依赖你，但不全是恋人语气 |
| 沈曼 | 小姨型长辈 | 70 | 倾心 | 成熟、掌控感、管束感 |
| 王大海 | 兄弟 | 82（友情） | 铁哥们 | 嘴损但关心，不女友化 |

---

## 八、双模式回复系统

两种模式是**核心功能**，不是 prompt 可选项。

### 8.1 聊天模式（Chat Mode）

**定位：** 用户与某一个角色正常聊天。输出必须是**动作 + 台词**。

**请求：**

```json
{
  "mode": "chat",
  "character_id": "ye_ruxue",
  "message": "你在干嘛"
}
```

**返回：**

```json
{
  "mode": "chat",
  "speaker": "ye_ruxue",
  "action": "她把手里的文件合上，抬眼看了你一下",
  "dialogue": "刚整理完资料。你呢？现在才出现，是不是又把晚饭拖到现在？",
  "emotion_delta": { "concern": 3, "miss_user": -2 },
  "relationship_delta": { "trust": 1 }
}
```

**前端展示：**

```text
【动作】她把手里的文件合上，抬眼看了你一下。

叶如雪："刚整理完资料。你呢？现在才出现，是不是又把晚饭拖到现在？"
```

**规则：**

```text
- 不固定字数，由人设、心情、当前活动决定长短
- 每次回复都带轻动作
- 不要所有人都撒娇
- 不要所有人都问「你是不是忘了我」
- 兄弟角色不进入恋爱语气
```

### 8.2 叙述模式（Scene Mode）

**定位：** 用户描述一个场景，AI 根据人设和状态判断角色会怎么行动。不是用户说什么就无条件照做。

**请求：**

```json
{
  "mode": "scene",
  "text": "我推开门，看见叶如雪、柳青柠和白柔都在客厅。"
}
```

**返回：**

```json
{
  "mode": "scene",
  "narration": "客厅里安静了一瞬。白柔最先站起来，手里还拿着刚叠好的薄毯……",
  "participants": ["ye_ruxue", "liu_qingning", "bai_rou"],
  "events": [
    {
      "character_id": "bai_rou",
      "action": "站起来，眼神明显亮了一下",
      "dialogue": "回来了？我给你留了饭。",
      "emotion_delta": { "happy": 4, "security": 2 }
    },
    {
      "character_id": "liu_qingning",
      "action": "别过脸，轻轻哼了一声",
      "dialogue": "谁等他了，我只是刚好在这儿。",
      "emotion_delta": { "jealous": 3, "shy": 2 }
    }
  ]
}
```

**规则：**

```text
- 必须识别谁是谁
- 必须读取角色之间的关系
- 判断谁先说话、谁沉默、谁试探、谁照顾场面
- 不能让所有角色都围着用户转
- 不能让角色行为违背人设
- 输出像场景叙事，不像一问一答
```

### 8.3 Prompt 模板（固定骨架）

**聊天模式 System Prompt：**

```text
你是：{角色名}
社会关系：{social_relation_label}
好感度：{affection_score} · {affection_grade}
当前心情：{emotion_vector}
当前活动：{current_activity}
最近记忆：{recent_memories}
称呼风格：{current_addressing_style}

用户消息：{message}

规则：
- 输出必须是【动作】+ 台词，不要只输出台词
- 动作根据人设、心情、当前活动变化，不要套模板
- 不要所有人都撒娇，不要所有人都问「你是不是忘了我」
- 若社会关系为兄弟，禁止恋爱语气、撒娇、想你类表达
- 字数由情境决定，不固定

输出格式（严格遵守）：
【动作】...
{角色名}："..."
```

**叙述模式 System Prompt：**

```text
当前是叙述模式。
用户输入是场景描述，不是直接命令。
你必须识别场景人物、关系、当前位置、情绪和冲突。
每个角色必须根据自己人设行动，不能所有人围着用户转。
不能让角色行为违背社会关系与好感等级。

场景输入：{text}
在场角色：{detected_characters}
角色关系网：{character_relations}
各角色当前状态：{character_states}

规则：
- 输出自然叙事，不像一问一答
- 判断谁先说话、谁沉默、谁试探、谁照顾场面
- 返回 participants / events / emotion_delta
- 兄弟角色（王大海）不参与恋爱竞争叙事

输出格式（JSON）：
{
  "narration": "...",
  "participants": [...],
  "events": [{ "character_id", "action", "dialogue", "emotion_delta" }]
}
```

**LLM 输出兜底（叙述模式必须实现）：**

```text
- scene_mode_service 必须做 JSON schema 校验
- 解析失败时自动重试 1 次（附带格式纠正 prompt）
- 再失败则降级为纯 narration 文本，但不能中断前端
- events / participants 缺失时默认 []，emotion_delta 缺失时默认 {}
- 降级时前端仍显示叙述文本，后台记录 parse_fallback 日志
```

**实现文件：**

```text
v2/backend/chat/prompt_builder.py      ← 扩展双模式模板
v2/backend/services/mode_router.py     ← 新建，路由 chat / scene
v2/backend/services/chat_service.py    ← 新建
v2/backend/services/scene_mode_service.py ← 新建
v2/backend/services/speaker_resolver.py   ← 新建
config/prompts/chat_mode.txt           ← 模板文件
config/prompts/scene_mode.txt          ← 模板文件
```

---

## 九、主动分享系统

把现在的「定时想你模板」改成**当前活动驱动分享**。

### 9.1 流程

```text
LifeLoop Tick
  → 获取角色当前活动
  → 获取当前情绪
  → 获取好感等级
  → 获取社会关系
  → 获取最近互动时间
  → 生成候选分享 intent
  → 判断冷却时间
  → 判断是否发文字 / 照片 / 私聊
  → 生成内容（LLM，非模板）
  → 写入记忆
```

### 9.2 分享类型

| 类型 | 说明 |
|------|------|
| `daily_share` | 日常分享 |
| `photo_share` | 发照片 |
| `mood_share` | 分享心情 |
| `ask_advice` | 问你意见 |
| `memory_recall` | 想起旧事 |
| `care_check` | 关心你 |
| `soft_complaint` | 轻微抱怨 |
| `jealous_probe` | 试探吃醋 |
| `life_update` | 生活更新 |
| `character_dm_leak` | 提到和别人聊过 |

### 9.3 决策评分公式

每个 tick 为每个角色计算分享分数，**只有分数最高且超过阈值的角色**才进入发送候选：

```text
主动分享分数 =
  当前活动分享欲     × 0.25
+ 当前情绪强度       × 0.20
+ 好感等级权重       × 0.20
+ 人设主动性         × 0.15
+ 最近记忆触发       × 0.10
+ 世界状态加成       × 0.10
- 冷却惩罚           （距上次主动 < 2h: -30；< 6h: -15）
- 重复惩罚           （24h 内句式相似 > 0.7: -40）
```

**子项说明：**

| 子项 | 计算方式 |
|------|----------|
| 活动分享欲 | 做饭/整理/加班等活动各有基础分；与当前 activity 匹配 +20 |
| 情绪强度 | `miss_user + lonely + jealous` 归一化到 0–100 |
| 好感等级权重 | 倾心 60 / 爱慕 75 / 深恋 85；陌生 < 10 不发 |
| 人设主动性 | 从 persona YAML 读取 `initiative` 字段，0–100 |
| 最近记忆触发 | 2h 内有用户相关记忆 +15；有未回复用户消息 +25 |
| 世界状态加成 | 深夜 +10、雨天 +5、节日 +15 |

**发送阈值：** `score >= 55` 才允许主动分享；同一小时取 top 2–3 名。

### 9.4 去重规则

```text
- 同一小时最多 2–3 个角色主动发消息
- anti_repeat_service 检测近 24h 句式相似度（阈值 0.7）
- 禁止连续两天使用同一 intent 类型
- 全局冷却：上一小时已发 3 条则本小时暂停
```

### 9.5 角色示例（对比昨晚模板）

**叶如雪：**

```text
我刚把明天的资料整理完。看到你上次说胃不舒服，顺手把晚饭提醒也记上了。
你最好别又拖到半夜。
```

**白柔：**

```text
我刚把汤温着。你不一定现在喝，但我想让它一直在那儿。
等你忙完，至少能有口热的。
```

**柳青柠：**

```text
我刚做完题，脑子都快炸了。
本来不想跟你说的，谁让你今天这么安静，害我一直分心。
```

**王大海：**

```text
老许，我刚点了烧烤。你要是在旁边，我肯定先骂你两句，再让你付钱。
```

---

## 十、情绪动态系统

情绪不是展示字段，是**运行字段**。每次事件都必须写回 `emotion_delta`。

### 10.1 情绪向量

```json
{
  "happy": 52,
  "sad": 10,
  "lonely": 34,
  "angry": 0,
  "jealous": 18,
  "shy": 22,
  "tired": 40,
  "calm": 55,
  "miss_user": 48,
  "security": 63
}
```

### 10.2 变化来源

| 触发 | 影响 |
|------|------|
| 深夜 | `lonely` ↑ `miss_user` ↑ |
| 下雨 | `calm` ↑ `memory_recall` 概率 ↑ |
| 工作活动 | `tired` ↑ `calm` ↑ |
| 用户回复 | `happy` / `security` 变化 |
| 用户沉默 | `miss_user` / `lonely` 变化 |
| 角色私聊 | `jealous` / `trust` 变化 |
| 图片失败 | `frustration` / `tired` 变化 |
| 图片成功 | `happy` / `confidence` 变化 |

### 10.3 写回规则

```text
用户消息        → emotion_delta → snapshot → WS push
角色主动分享    → emotion_delta → snapshot → WS push
角色私聊        → emotion_delta → snapshot → WS push
图片生成失败    → emotion_delta → snapshot → WS push
图片生成成功    → emotion_delta → snapshot → WS push
长时间未互动    → emotion_delta → snapshot → WS push
```

### 10.4 衰减规则（每 5 分钟 tick）

情绪不能只做一次性加减，必须持续衰减/漂移，否则前端「看起来没变化」：

```text
每 5 分钟基础衰减：
  happy      -0.3
  excited    -0.5
  angry      -0.8
  shy        -0.2
  embarrassed -0.3

时间驱动漂移：
  tired      +0.2（22:00–06:00 额外 +0.5）
  lonely     +0.1 × 未互动小时数（上限 +3.0/次）
  miss_user  +0.15 × 好感权重系数（倾心 1.0 / 爱慕 1.3 / 深恋 1.5）
  calm       向 50 回归（±0.2）

用户互动后：
  security   根据回复质量 +1~+5（敷衍 -1）
  happy      用户主动找 +2~+6
  miss_user  用户回复后 -5~-15（按好感等级）
  lonely     用户回复后 -3~-10

边界：
  所有情绪值钳制在 0–100
  衰减后写入 emotion_snapshot 并 WS push
```

**实现文件：**

```text
v2/backend/engine/emotion_engine.py    ← 扩展 decay_tick()
v2/backend/services/emotion_tick.py      ← 新建，5 分钟调度
v2/backend/runtime/life_scheduler.py     ← 接入 emotion_tick
```

---

## 十一、角色私聊系统

新增 `character_dm_conversation`。**用户可以看，但不能回复。**

### 11.1 触发条件

```text
- A 因用户和 B 的互动产生情绪
- A 想向 B 打听用户
- A 想安慰 B / 试探 B
- A 和 B 同处一个场景
- A 看到 B 主动发图 / 发消息
```

### 11.2 触发优先级

| 优先级 | 触发场景 | 冷却 |
|--------|----------|------|
| **最高** | 角色之间因用户产生明显情绪冲突（jealousy > 60） | 4h |
| **最高** | 某角色看到另一角色主动发图/发消息后嫉妒或试探 | 3h |
| **中** | 同处一个场景（叙述模式或群聊后） | 6h |
| **中** | 想打听用户 / 想安慰对方 | 8h |
| **低** | 普通日常闲聊 | 12h |
| **低** | 世界事件触发 | 24h |

**频率上限：** 每角色每天最多发起 2 次私聊；全局同时活跃 DM 对话不超过 3 条。

### 11.3 角色之间关系标签

```text
陌生 / 点头之交 / 熟识 / 朋友 / 闺蜜
竞争者 / 情敌 / 照顾者 / 被照顾者
长辈感 / 晚辈感 / 表面和平 / 暗中试探 / 互相看不顺眼
```

### 11.4 示例

```text
柳青柠："你刚才那句话是什么意思？你很了解他？"

叶如雪没有立刻回答，只是把文件合上。
"至少比你想象的了解。"

柳青柠轻轻哼了一声："装什么成熟。"
```

**前端提示：**

```text
此对话为角色私聊，你只能旁观，不能回复。
```

---

## 十二、生图任务系统

当前优先级：**先解决慢、无状态、场景重复**，再追求更高画质。

### 12.1 任务状态

```text
queued      排队中
generating  生成中
uploading   上传中
completed   完成
failed      失败
retrying    重试
```

### 12.2 前端展示

```text
叶如雪正在整理照片……
状态：生成中
模型：Qwen-Image-Edit
已等待：18 秒
```

### 12.3 超时策略

```text
20 秒未完成 → 角色先回复「我还在整理，等我一下。」
60 秒失败   → 自动换模型重试一次
两次失败    → 返回失败提示 + 写入角色情绪
```

### 12.4 活动驱动场景

| 当前活动 | 图片场景 |
|----------|----------|
| 做饭 | 厨房照 |
| 看书 | 书桌照 |
| 加班 | 办公桌照 |
| 下雨 | 窗边照 |
| 运动 | 运动后日常照 |
| 逛街 | 街边照 |
| 整理房间 | 居家照 |

---

## 十三、数据库新增 / 调整

迁移文件：

```text
007_v4_1_relationship_social.sql
008_v4_1_mode_runtime.sql
009_v4_1_character_dm.sql
010_v4_1_image_jobs.sql
011_v4_1_activity_emotion_snapshots.sql
```

### 13.1 `character_user_relation`

```sql
character_id
social_relation_type
social_relation_label
affection_score
affection_grade
love, trust, attachment, security, respect
jealousy, emotional_intimacy, physical_intimacy
current_addressing_style
updated_at
```

### 13.2 `character_character_relation`

```sql
from_character_id
to_character_id
relation_label
familiarity, trust, affinity
rivalry, jealousy, respect, protectiveness
last_dm_at
```

### 13.3 `image_jobs`

```sql
job_id, character_id, trigger_type
status, provider, model
prompt, scene, activity
progress_text, image_url, error_message
created_at, updated_at
```

### 13.4 `user_runtime_settings`

```sql
user_id
current_mode          -- chat | scene
active_character_id
scene_style
updated_at
```

---

## 十四、接口设计

### 14.1 REST

```text
GET  /api/v4/characters
GET  /api/v4/characters/{id}/state
POST /api/v4/chat
POST /api/v4/scene
POST /api/v4/proactive/tick
GET  /api/v4/relationships/user
GET  /api/v4/relationships/social
GET  /api/v4/character-dm/list
GET  /api/v4/character-dm/{conversation_id}
POST /api/v4/images/jobs
GET  /api/v4/images/jobs/{job_id}
GET  /api/v4/album/{character_id}
```

### 14.2 WebSocket 事件

```text
chat_token
emotion_update
relationship_update
proactive_message
image_job_update
character_dm_created
scene_event
```

---

## 十五、前端体验改造

### 15.1 角色卡片

```text
头像 / 名字
社会关系 / 好感等级
当前心情 / 当前活动
最近主动时间 / 是否正在生成图片
```

### 15.2 右侧状态栏

```text
当前模式：聊天 / 叙述
当前对象
好感度 / 社会关系
当前心情 / 当前活动
最近记忆 / 图片生成状态
```

### 15.3 顶部模式切换

```text
[聊天模式]  [叙述模式]
```

### 15.4 私聊只读页

```text
角色私聊
  叶如雪 × 柳青柠
  白柔 × 苏念
  王大海 × 林糖糖
```

点进去能看，不能输入。

---

## 十六、架构优化建议（工程层，后置执行）

> 以下内容保留自原方案，**降至第 7 阶段 / V5.0** 执行。

### 16.1 推荐目录结构（V5 目标态）

```
AI-Companion-OS/
├─ src/
│   ├─ api/routers/       # chat / scene / social / visual / memory
│   ├─ core/              # LifeKernel（唯一入口）+ EventBus + Scheduler
│   ├─ domain/            # character / emotion / memory / social / world / visual
│   ├─ llm/               # clients / prompts / streaming
│   └─ db/                # models / repositories（拆分 db.py）
├─ frontend/              # SvelteKit
├─ tests/                 # unit / integration / e2e
├─ deploy/                # Docker + nginx
└─ .github/workflows/     # CI/CD
```

### 16.2 技术选型建议

| 层 | 当前 | 建议 | 理由 |
|----|------|------|------|
| LLM 路由 | 硬编码 | LiteLLM | 统一多模型切换 |
| 异步任务 | 无 | Redis 队列 | 生图长任务 |
| 日志 | print | structlog | 结构化 |
| 监控 | 无 | Prometheus + Grafana | 标准方案 |
| CI/CD | 无 | GitHub Actions | 自动部署 |

---

## 十七、执行前准备

> 所有迁移和重构开始前必须完成，防止数据丢失或线上回滚困难。

```text
1. 创建开发分支：v4.1-character-reality
2. 备份 SQLite：data/companion.db → data/backup/companion_YYYYMMDD.db
3. 备份 PostgreSQL volume（若线上使用 pg）
4. 记录当前线上版本 commit hash
5. 所有迁移先在本地 / 测试库跑通，再部署服务器
6. 每阶段完成后执行对应测试，再进入下一阶段
```

**建议命令：**

```bash
git checkout -b v4.1-character-reality
mkdir -p data/backup
cp data/companion.db data/backup/companion_$(date +%Y%m%d).db
git rev-parse HEAD > data/backup/baseline_commit.txt
```

---

## 十八、执行路线图（含文件清单）

### 第 1 阶段：关系与好感度重构（3 天）

**目标：** 不再全员女友；好感显示熟识/倾心/爱慕；社会关系单独展示

**后端（新建 / 修改）：**

```text
v2/backend/services/affection_grade_service.py   ← 新建，好感算法 + 等级映射
v2/backend/services/social_relation_service.py     ← 新建，社会关系读写
v2/backend/engine/relationship_engine.py           ← 修改，接入双字段
v2/backend/scripts/reset_world.py                  ← 修改，禁止全员 80
v2/backend/bootstrap.py                            ← 修改，加载初始关系表
v2/backend/api/rest_routes.py                      ← 修改，/state 返回双字段
config/relationship_init.yaml                      ← 新建，第七章初始化表
```

**数据库：**

```text
migrations/007_v4_1_relationship_social.sql
```

**前端：**

```text
v2/frontend/src/pages/CharacterPanel.svelte        ← 修改，展示社会关系 + 好感等级
v2/frontend/src/components/RightStatusPanel.svelte ← 新建，右侧状态栏
v2/frontend/src/stores/characters.js               ← 修改，接入 affection_grade
```

**测试：**

```text
v2/backend/tests/test_affection_grade.py           ← 新建
v2/backend/tests/test_social_relation.py           ← 新建
v2/backend/tests/test_relationship_floor.py        ← 修改，王大海友情断言
```

**完成标准：**

```text
- reset_world 后不再出现全员 80
- 王大海显示友情度，不出现恋爱字段
- 至少 5 个角色社会关系和好感等级不同
- 前端角色卡片能显示社会关系 + 好感等级 + 当前活动
- 测试样例 2、测试样例 5 通过
```

---

### 第 2 阶段：双模式回复（3 天）

**目标：** 聊天模式动作+台词；叙述模式场景+多角色行动

**后端：**

```text
v2/backend/services/mode_router.py                 ← 新建
v2/backend/services/chat_service.py                ← 新建
v2/backend/services/scene_mode_service.py          ← 新建
v2/backend/services/speaker_resolver.py            ← 新建
v2/backend/chat/prompt_builder.py                  ← 修改，8.3 双模板
v2/backend/api/ws_routes.py                        ← 修改，mode 字段路由
v2/backend/api/rest_routes.py                      ← 新增 POST /api/v4/chat、/scene
config/prompts/chat_mode.txt                       ← 新建
config/prompts/scene_mode.txt                      ← 新建
migrations/008_v4_1_mode_runtime.sql
```

**前端：**

```text
v2/frontend/src/pages/Chat.svelte                  ← 修改，模式切换 + 动作渲染
v2/frontend/src/components/MessageBubble.svelte    ← 修改，【动作】区块
v2/frontend/src/stores/chat.js                     ← 修改，mode 状态
```

**测试：**

```text
v2/backend/tests/test_mode_router.py               ← 新建
v2/backend/tests/test_scene_mode.py                ← 新建
```

**完成标准：**

```text
- chat 模式输出【动作】+ 台词
- scene 模式输出 narration + participants + events
- 用户提到叶如雪/柳青柠时不会混角色
- 王大海不会进入恋爱语气
- JSON 解析失败时降级为纯 narration，前端不中断
- 测试样例 3 通过
```

---

### 第 3 阶段：主动分享去模板化（2 天）

**目标：** 按当前活动分享；不再批量「想你了」

**后端：**

```text
v2/backend/services/daily_life_service.py          ← 新建，当前活动分配
v2/backend/services/proactive_share_service.py     ← 新建，9.3 评分公式
v2/backend/services/anti_repeat_service.py         ← 新建，句式去重
v2/backend/runtime/life_scheduler.py               ← 修改，替换模板逻辑
v2/backend/engine/absence.py                       ← 修改，接入评分而非固定文案
config/proactive_intents.yaml                      ← 新建，分享类型配置
```

**测试：**

```text
v2/backend/tests/test_proactive_share.py           ← 新建，含「1 小时不超 3 人」断言
v2/backend/tests/test_anti_repeat.py               ← 新建
```

**完成标准：**

```text
- 1 小时内主动消息不超过 3 个角色
- 主动消息内容与当前 activity 相关，不再批量「想你了」
- 24h 内句式相似度 > 0.7 的分享被拦截
- 白柔/柳青柠/王大海主动分享文案风格明显不同
- 测试样例 1 通过
```

---

### 第 4 阶段：情绪动态（2 天）

**目标：** 心情随时间、事件、私聊、生图变化

**后端：**

```text
v2/backend/services/emotion_tick.py                ← 新建，10.4 衰减
v2/backend/engine/emotion_engine.py                ← 修改，apply_delta + decay
v2/backend/chat/stream_delivery.py                 ← 修改，回复后写 emotion_delta
v2/backend/api/ws_hub.py                           ← 修改，推送 emotion_update
migrations/011_v4_1_activity_emotion_snapshots.sql
```

**前端：**

```text
v2/frontend/src/components/StatusIndicator.svelte ← 修改，实时心情
v2/frontend/src/stores/chat.js                      ← 修改，监听 emotion_update
```

**测试：**

```text
v2/backend/tests/test_emotion_decay.py             ← 新建
v2/backend/tests/test_emotion_delta.py             ← 新建
```

**完成标准：**

```text
- 用户回复后 emotion_delta 写入并 WS 推送
- 30 分钟无互动后 lonely/miss_user 有可观测上升
- 5 分钟 tick 后 happy/excited 有可观测衰减
- 前端心情数值随事件变化，非静态展示
- 测试样例 6 通过
```

---

### 第 5 阶段：角色私聊（2 天）

**目标：** 角色互聊，用户只读

**后端：**

```text
v2/backend/services/character_dm_service.py        ← 新建，11.2 优先级
v2/backend/services/character_relation_service.py  ← 新建
v2/backend/api/rest_routes.py                      ← 新增 DM list/detail API
migrations/009_v4_1_character_dm.sql
```

**前端：**

```text
v2/frontend/src/pages/CharacterDmList.svelte       ← 新建，只读列表
v2/frontend/src/pages/CharacterDmDetail.svelte     ← 新建，只读详情
v2/frontend/src/App.svelte                         ← 修改，路由入口
```

**测试：**

```text
v2/backend/tests/test_character_dm.py              ← 新建，频率上限断言
```

**完成标准：**

```text
- 角色私聊页可查看、不可回复
- 高优先级触发（嫉妒/试探）优先于日常闲聊
- 每角色每天私聊发起 ≤ 2 次
- 全局同时活跃 DM 对话 ≤ 3 条
- 测试样例 7 通过
```

---

### 第 6 阶段：生图任务状态（2 天）

**目标：** 知道图片是否在生成；成功进相册；失败可重试

**后端：**

```text
v2/backend/services/image_job_service.py           ← 新建，状态机
v2/backend/image/orchestrator.py                   ← 修改，写 image_jobs
v2/backend/image/chat_photo.py                     ← 修改，20s/60s 超时策略
v2/backend/api/image_routes.py                     ← 修改，jobs CRUD
v2/backend/api/ws_routes.py                        ← 修改，image_job_update
migrations/010_v4_1_image_jobs.sql
```

**前端：**

```text
v2/frontend/src/components/ImageJobProgress.svelte ← 新建
v2/frontend/src/components/MessageBubble.svelte      ← 修改，生成中占位
v2/frontend/src/stores/chat.js                       ← 修改，监听 image_job_update
```

**测试：**

```text
v2/backend/tests/test_image_job_states.py          ← 新建
```

**完成标准：**

```text
- 前端显示 queued → generating → completed / failed 全流程
- 20s 未完成时角色先说「我还在整理，等我一下」
- 60s 失败自动换模型重试 1 次
- 成功后图片进入聊天气泡 + 相册 + 视觉记忆
- 失败后写入 emotion_delta
- 测试样例 4 通过
```

---

### 第 7 阶段：工程清理（3 天）

**目标：** db.py 拆分 / 引擎统一 / CI/CD / 监控 / 测试

```text
v3/db.py → v3/db/ 拆分
v3/world/world_tick.py → 废弃，LifeKernel 唯一入口
.github/workflows/deploy.yml
v2/backend/tests/ 总覆盖率目标 50+
```

**完成标准：**

```text
- V4.1 体验闭环已在 V2 稳定运行
- db.py 拆分完成，V3 模块可独立测试
- WorldTick 废弃，LifeKernel 为唯一调度入口
- CI/CD 流水线可自动 build + deploy
- 全量回归测试通过
```

### 版本路线

```text
V4.1  角色真实感重构        ← 当前聚焦（第 1–4 阶段）
V4.2  双模式互动与私聊网络   （第 2、5 阶段深化）
V4.3  视觉任务与相册记忆     （第 6 阶段）
V5.0  工程化与自动部署       （第 7 阶段）
```

---

## 十九、开发执行清单

按批次推进，**前一批验收通过再开下一批**。

### 第一批（关系基础，必须先做）

```text
☐ migrations/007_v4_1_relationship_social.sql
☐ affection_grade_service.py
☐ social_relation_service.py
☐ config/relationship_init.yaml（第七章 12 角色表）
☐ reset_world.py 禁止再全员 80
☐ CharacterPanel + RightStatusPanel 展示社会关系 + 好感等级
☐ 王大海友情系统（不走恋爱逻辑）
```

### 第二批（双模式）

```text
☐ mode_router.py
☐ chat_service.py + scene_mode_service.py
☐ speaker_resolver.py
☐ prompt_builder 双模板（8.3）
☐ Chat.svelte 模式切换 + 【动作】渲染
☐ POST /api/v4/chat、/scene
```

### 第三批（主动分享 + 情绪）

```text
☐ proactive_share_service.py（9.3 评分公式）
☐ anti_repeat_service.py
☐ daily_life_service.py
☐ emotion_tick.py（10.4 衰减）
☐ emotion_delta 全事件写回
☐ WebSocket 推送 emotion_update / proactive_message
```

### 第四批（私聊 + 生图）

```text
☐ character_dm_service.py（11.2 优先级）
☐ image_job_service.py（状态机）
☐ image_job_update WebSocket
☐ ImageJobProgress 前端组件
☐ album memory writeback
☐ CharacterDmList 只读页
```

---

## 二十、风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 双模式 prompt 质量不稳定 | 中 | 体验 | 分角色 few-shot + 回归测试集 |
| 主动分享去重后消息过少 | 中 | 活跃度 | 按好感等级调节频率上限 |
| 角色私聊内容失控 | 低 | 人设 | 关系约束 + 输出审核（仅私聊） |
| 生图 API 费用 | 中 | 预算 | 队列限流 + 失败重试上限 |
| 关系表迁移丢数据 | 低 | 数据 | 先备份 `companion.db` / pg volume |
| 前端改造超期 | 高 | 延期 | 先后端 API，前端分阶段接 |

---

## 二十一、验收标准

### 20.1 功能验收（13 条）

```text
 1. 每个角色卡片显示：社会关系 + 好感等级 + 当前心情 + 当前活动
 2. 好感度显示熟识/亲近/在意/倾心/爱慕/深恋，不显示「女友」
 3. 社会关系单独显示：老婆型伴侣、小姨型长辈、兄弟、女仆、欢喜冤家等
 4. 王大海使用友情等级，不进入恋爱逻辑
 5. 聊天模式每次输出：动作 + 台词
 6. 叙述模式能识别场景人物，并根据人设行动
 7. 主动消息来自当前活动，不再批量「想你了」
 8. 同一小时最多 2–3 个角色主动发消息
 9. 心情随时间、用户回复、私聊、生图成功/失败变化
10. 角色之间能自动私聊，用户只能看不能回复
11. 图片生成有 queued / generating / completed / failed 状态
12. 图片成功后进入相册，并写入视觉记忆
13. 不固定回复字数，由人设、心情、关系、场景决定长度
```

### 20.2 测试样例

**测试 1：主动消息频率**

```text
前置：用户 6 小时未回复，12 角色好感各异
操作：触发 LifeLoop proactive tick 连续 1 小时
预期：最多 2–3 个角色主动发消息
禁止：12 人一起发「想你了/是不是忘了我」
```

**测试 2：王大海友情边界**

```text
前置：切到王大海私聊
操作：发送「在吗」
预期：卡片显示「友情度：82 · 铁哥们」，社会关系「兄弟」
禁止：老婆/想你/撒娇/恋爱语气
```

**测试 3：叙述模式多角色**

```text
前置：切换到叙述模式
输入：「我推开门，看见叶如雪和柳青柠在客厅。」
预期：
  - 叶如雪：冷静观察、克制关心、带长辈感
  - 柳青柠：嘴硬、别过脸、不承认在意
  - 返回 narration + participants + events
禁止：所有人围着用户转、所有人撒娇
```

**测试 4：生图任务状态**

```text
前置：私聊叶如雪，说「发张自拍」
操作：触发生图
预期：
  - 前端显示 queued → generating → completed（或 failed）
  - 20s 未完成时角色先说「我还在整理，等我一下」
  - 成功后图片出现在聊天气泡 + 相册
  - 失败后 emotion_delta 写入，可重试一次
```

**测试 5：好感度与社会关系拆分**

```text
前置：重置后按第七章初始化表加载
操作：查看沈曼、王大海、柳青柠卡片
预期：
  - 沈曼：社会关系「小姨型长辈」，好感「70 · 倾心」
  - 王大海：社会关系「兄弟」，友情「82 · 铁哥们」
  - 柳青柠：社会关系「欢喜冤家」，好感「52 · 在意」
禁止：三人显示相同关系标签或相同等级文案
```

**测试 6：情绪衰减**

```text
前置：某角色 happy=70，用户 30 分钟未互动
操作：运行 6 次 emotion_tick（模拟 30 分钟）
预期：happy 下降；lonely/miss_user 上升；前端心情数值有变化
禁止：30 分钟后情绪快照与初始值完全相同
```

**测试 7：角色私聊只读**

```text
前置：柳青柠因用户与叶如雪互动，jealousy > 60
操作：等待 character_dm 触发
预期：
  - 私聊页出现「叶如雪 × 柳青柠」对话
  - 用户可查看，输入框不可用
  - 当天该角色私聊发起次数 ≤ 2
```

---

## 二十二、总结

**当前最大痛点：角色不像不同的人。**

系统已经能跑——服务器在线、LLM 接通、生图有成功记录——但昨晚试用暴露的是体验层全面失败：12 个角色说着同样的话、怀着同样的好感、怀着同样的恋人关系。

V4.1 要做的不是再加模块，而是让**关系、情绪、活动、表达、社交、视觉**六条线真正跑起来，让每个角色成为独立的人。

> 一句话：**从「参数优美的可运行系统」升级为「角色真实感系统」。**  
> 本文档定位：**AI-Companion-OS V4.1 开发任务总纲（定稿）**——方向已定，按第十七章备份、第十八章清单分批执行。

*（内容由 AI 生成，仅供参考）*
