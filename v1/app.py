"""
AI-Companion-OS 终端对话入口
V1 阶段：人格内核

启动流程：
1. 加载配置 → 选择角色
2. 初始化所有引擎 + 记忆管理器
3. 循环对话
"""

import os
import sys
import yaml
from pathlib import Path
from datetime import datetime

# 将项目根目录加入 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.persona import Persona
from src.models.relationship import RelationshipState
from src.models.emotion import EmotionState
from src.models.state import GlobalState, LifeActivity
from src.models.memory_model import MemoryTier

from src.engine.relationship_engine import RelationshipEngine
from src.engine.emotion_engine import EmotionEngine
from src.engine.life_simulator import LifeSimulator
from src.engine.growth_engine import GrowthEngine
from src.engine.state_machine import StateMachine

from src.memory.memory_manager import MemoryManager
from src.prompt.assembler import PromptAssembler
from src.llm.router import LLMRouter

# ============================================================
# 关系事件 → 情绪事件映射表
# ============================================================
RELATION_TO_EMOTION_EVENT: dict[str, str | None] = {
    "compliment_appearance": "compliment_received",
    "compliment_ability": "compliment_received",
    "active_care": "user_needs_comfort",
    "gift_giving": "gift_received",
    "confession_love": "user_expressed_love",
    "share_vulnerability": "user_shares_bad_news",
    "cold_response": "user_cold_shoulder",
    "criticize_harshly": "user_angry_at_her",
    "praise_other_woman": "user_mentioned_other",
    "threaten_leave": "user_threaten_leave",
    "ignore_her": "user_ignores_her",
    "express_missing_her": "user_expressed_love",
    "talk_about_future": "exciting_event",
    "apology_sincere": "make_up_after_conflict",
}


class AICompanionApp:
    """AI 女友终端应用"""

    def __init__(self):
        self.persona: Persona | None = None
        self.global_state: GlobalState | None = None

        # 引擎
        self.relationship_engine: RelationshipEngine | None = None
        self.emotion_engine: EmotionEngine | None = None
        self.life_simulator: LifeSimulator | None = None
        self.growth_engine: GrowthEngine | None = None
        self.state_machine: StateMachine | None = None

        # 记忆
        self.memory_manager: MemoryManager | None = None

        # LLM
        self.llm_router: LLMRouter | None = None

        # 对话历史
        self.conversation_history: list[dict] = []

        # 成长引擎日期控制
        self._last_advance_date: str = ""

    def run(self):
        """主运行入口"""
        print("=" * 50)
        print("   AI-Companion-OS V1 - 人格内核")
        print("   基于 DeepSeek LLM 的 AI 女友系统")
        print("=" * 50)
        print()

        # 1. 加载角色
        persona_id = self._select_persona()
        self._load_persona(persona_id)

        # 2. 初始化所有子系统
        self._init_subsystems()

        # 3. 进入对话循环
        self._chat_loop()

    def _select_persona(self) -> str:
        """显示角色列表并让用户选择"""
        personas_dir = PROJECT_ROOT / "config" / "personas"

        if not personas_dir.exists():
            print("错误：角色配置文件目录不存在！")
            sys.exit(1)

        yaml_files = sorted(personas_dir.glob("*.yaml"))
        if not yaml_files:
            print("错误：没有找到角色配置文件！")
            sys.exit(1)

        print("可用角色：")
        print("-" * 40)
        for i, f in enumerate(yaml_files, 1):
            persona_id = f.stem
            # 读取角色名
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp)
                    name = data.get("name", persona_id)
                    ptype = data.get("type", "未知")
                    age = data.get("age", "?")
                    print(f"  {i}. {name} [{ptype}] - {age}岁")
            except Exception:
                print(f"  {i}. {persona_id}")

        print("-" * 40)

        while True:
            try:
                choice = input("\n请选择角色编号 (1-10): ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(yaml_files):
                    return yaml_files[idx].stem
                print(f"请输入 1 到 {len(yaml_files)} 之间的数字")
            except (ValueError, KeyboardInterrupt):
                if isinstance(sys.exc_info()[0], KeyboardInterrupt):
                    print("\n已退出")
                    sys.exit(0)

    def _load_persona(self, persona_id: str):
        """从 YAML 加载角色"""
        yaml_path = PROJECT_ROOT / "config" / "personas" / f"{persona_id}.yaml"

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.persona = Persona(
            id=data["id"],
            name=data["name"],
            type=data["type"],
            base_info=data["base_info"],
            appearance=data["appearance"],
            personality=data["personality"],
            speech_style=data["speech_style"],
            love_view=data["love_view"],
            values=data["values"],
            worldview=data["worldview"],
            hobbies=data["hobbies"],
            daily_routine=data["daily_routine"],
            taboos=data["taboos"],
        )

        print(f"\n已加载角色：{self.persona.name} ({self.persona.type})")
        print(f"  {self.persona.personality.core[:50]}...")

    def _init_subsystems(self):
        """初始化所有引擎和子系统"""
        print("\n正在初始化子系统...")

        # 记忆管理器
        data_dir = PROJECT_ROOT / "data"
        self.memory_manager = MemoryManager(db_dir=str(data_dir))

        # 关系引擎
        self.relationship_engine = RelationshipEngine()
        print("  [OK] 关系引擎")

        # 情绪引擎
        self.emotion_engine = EmotionEngine()
        print("  [OK] 情绪引擎")

        # 生活模拟器
        self.life_simulator = LifeSimulator(persona_id=self.persona.name)
        print("  [OK] 生活模拟器")

        # 成长引擎
        self.growth_engine = GrowthEngine(persona_id=self.persona.name)
        print("  [OK] 成长引擎")

        # 状态机
        self.state_machine = StateMachine()
        print("  [OK] 状态机")

        # 构建全局状态
        now = datetime.now()
        life = self.life_simulator.get_current_activity(now)

        self.global_state = GlobalState(
            persona=self.persona,
            relationship=RelationshipState(),
            emotion=EmotionState(),
            life=LifeActivity(
                time=life["time"],
                activity=life["activity"],
                is_workday=life["is_workday"],
                season=life["season"],
            ),
        )

        # LLM 路由器
        self.llm_router = LLMRouter()
        if self.llm_router.is_available:
            print("  [OK] LLM (DeepSeek)")
        else:
            print("  [WARN] LLM 不可用 - 请设置 DEEPSEEK_API_KEY 环境变量")

        print()

    def _chat_loop(self):
        """主对话循环"""
        print(f"开始与 {self.persona.name} 的对话！")
        print("输入 'quit' 或 '退出' 结束对话")
        print("=" * 50)

        # 初始问候
        greeting = self._generate_greeting()
        print(f"\n{self.persona.name}: {greeting}\n")

        while True:
            try:
                user_input = input("你: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n再见！")
                break

            if not user_input:
                continue

            if user_input.lower() in ("quit", "退出", "exit", "bye"):
                print(f"\n{self.persona.name}: 再见，我会想你的。")
                break

            # 处理用户输入
            reply = self._process_user_input(user_input)
            print(f"\n{self.persona.name}: {reply}\n")

    def _process_user_input(self, user_text: str) -> str:
        """
        处理一轮用户输入

        完整流程：
        1. Tick 所有引擎（衰减、时间推进）
        2. 检测用户事件
        3. 召回相关记忆
        4. 组装 Prompt
        5. 调用 LLM
        6. 存储本轮交互
        """
        # 1. Engine ticks
        rel_tick = self.relationship_engine.tick()
        emo_tick = self.emotion_engine.tick()

        # 推进成长引擎
        # 每天只推进一次
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._last_advance_date:
            self.growth_engine.advance_days()
            self._last_advance_date = today
        growth_status = self.growth_engine.check_growth()

        # 2. 事件检测
        event = self.relationship_engine.detect_event_from_text(user_text)
        if event:
            self.relationship_engine.process_event(event)

        # 映射到情绪引擎事件
        emotion_event = RELATION_TO_EMOTION_EVENT.get(event) if event else None
        if emotion_event:
            intensity = 1.0
            # 高情感事件加强强度
            if event in ("confession_love", "threaten_leave"):
                intensity = 1.5
            self.emotion_engine.trigger_emotion(emotion_event, intensity)

        # 强烈负面情绪反馈到关系
        if event:
            new_emo = self.emotion_engine.state
            if new_emo.sad > 70:
                self.relationship_engine.process_event("share_vulnerability", 0.3)
            if new_emo.angry > 50:
                self.relationship_engine.process_event("cold_response", 0.2)

        # 更新全局状态
        now = datetime.now()
        life = self.life_simulator.get_current_activity(now)
        self.global_state.life = LifeActivity(
            time=life["time"], activity=life["activity"],
            is_workday=life["is_workday"], season=life["season"]
        )
        self.global_state.relationship = self.relationship_engine.state
        self.global_state.emotion = self.emotion_engine.state
        self.global_state.growth_stage = growth_status["stage"]
        self.global_state.interaction_days = self.growth_engine.interaction_days

        # 更新状态机
        self.state_machine.update_state(self.global_state)

        # 3. 记忆召回
        memories = self.memory_manager.recall(user_text, limit=5)

        # 4. 组装 Prompt
        assembler = PromptAssembler(self.global_state, memories)
        system_prompt = assembler.build_system_prompt()
        user_message = assembler.build_user_message(user_text)

        # 5. 构建消息列表（保留最近10轮历史）
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.conversation_history[-20:])  # 最近10轮 = 20条
        messages.append({"role": "user", "content": user_message})

        # 6. LLM 调用
        reply = self.llm_router.chat(messages=messages)

        # 如果 LLM 不可用，用模拟回复
        if not self.llm_router.is_available or reply.startswith("[错误]"):
            reply = self._fallback_reply(user_text)

        # 7. 存储到对话历史和记忆
        self.conversation_history.append({"role": "user", "content": user_text})
        self.conversation_history.append({"role": "assistant", "content": reply})

        # 限制为最近 40 条消息（20 轮对话）
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]

        # 情感强度高的对话存储为长期记忆
        intensity = max(
            abs(self.emotion_engine.state.happy - 50),
            abs(self.emotion_engine.state.sad - 20),
            abs(self.emotion_engine.state.excited - 30),
        ) / 50.0 * 100
        intensity = min(100, intensity)

        if intensity > 40 or event:
            tier = MemoryTier.LONG if intensity > 70 else MemoryTier.SHORT
            self.memory_manager.store(
                tier=tier,
                content=f"用户说：{user_text[:200]} | {self.persona.name}回复：{reply[:200]}",
                emotion_tags=[self.emotion_engine.state.dominant_emotion[0]],
                intensity=intensity,
            )

        return reply

    def _generate_greeting(self) -> str:
        """生成初始问候语"""
        # 尝试用 LLM 生成
        if self.llm_router and self.llm_router.is_available:
            greeting_prompt = (
                f"你是{self.persona.name}，一个{self.persona.type}类型的AI女友。\n"
                f"你的身份：{self.persona.base_info.age}岁，{self.persona.base_info.occupation}。\n"
                f"性格核心：{self.persona.personality.core[:80]}\n"
                f"说话风格：{self.persona.speech_style.speed}，{self.persona.speech_style.vocabulary}\n"
                f"这是你和用户今天的第一次对话。请用符合你性格的方式说一句自然、简短的开场问候（不超过30字），不要提及AI、系统、角色等设定信息。"
            )
            try:
                reply = self.llm_router.chat(
                    messages=[
                        {"role": "system", "content": greeting_prompt},
                        {"role": "user", "content": "开始对话吧"},
                    ],
                    max_tokens=100,
                    temperature=0.9,
                )
                if reply and not reply.startswith("[错误]"):
                    return reply.strip()
            except Exception:
                pass

        # Fallback 问候语
        greetings = {
            "ye_ruxue": "（抬眼看了你一眼）……来了？",
            "bai_rou": "你来啦～今天过得怎么样？",
            "liu_qingning": "哼，终于想起找我了吗？我可没有等很久！",
            "mo_xiaoran": "（盯着你）今天去见了谁？……开玩笑的。",
            "gu_wanqing": "呀，你来啦！我跟你说今天有个超有趣的事！",
            "xiao_ying": "欢迎回来，需要我为你准备什么吗？",
            "xingye_liuli": "哟！今天也来我的世界玩吧！",
            "su_nian": "（扑过来）想你了想你了！",
            "lin_tangtang": "哟～今天看起来心情不错嘛？来，姐姐陪你聊聊～",
            "hua_li": "欧尼酱！今天画了新的画要给你看！",
        }
        return greetings.get(self.persona.id, f"嗨～你来啦！")

    # ================================================================
    # Fallback 回复系统（情感权重优先 + 角色差异化 + 情绪驱动 + 场景感知）
    # ================================================================

    def _pick(self, user_text: str, pool: list[str]) -> str:
        """从回复池中根据用户输入确定性选取一个变体"""
        return pool[len(user_text) % len(pool)]

    def _fallback_reply(self, user_text: str) -> str:
        """
        LLM 不可用时的规则回复

        意图优先级（从高到低）：
        1. 分手/威胁    → 强烈情绪反应
        2. 抱怨/批评她   → 情绪化反应
        3. 负面情绪表达  → 共情安抚
        4. 想念/爱意     → 角色化回应
        5. 询问她在干嘛  → 结合 life.activity
        6. 打招呼       → 角色化问候
        7. 兜底         → 结合当前情绪状态
        """
        pid = self.persona.id
        name = self.persona.name
        emo = self.emotion_engine.state
        dom, val = emo.dominant_emotion
        activity = self.global_state.life.activity

        rel = self.relationship_engine.state
        intimacy = getattr(rel, "intimacy", 50)
        health = getattr(rel, "health", 70)

        # --- 1. 分手/威胁 ---
        if any(w in user_text for w in ["分手", "分开吧", "离开我", "不要你了", "结束吧", "到此为止"]):
            return self._fb_threaten(pid, name, dom, intimacy, user_text)

        # --- 2. 抱怨/批评她 ---
        if any(w in user_text for w in ["你太", "你总是", "你怎么", "烦不烦", "别烦我", "你好烦",
                                         "你真啰嗦", "你不行", "你很烦", "别说了"]):
            return self._fb_criticized(pid, name, dom, user_text)

        # --- 3. 负面情绪（最高日常优先级）---
        neg_keywords = ["累", "压力", "难过", "不开心", "崩溃", "抑郁", "焦虑",
                        "痛苦", "疲惫", "好累", "太难了", "好难", "撑不住",
                        "想哭", "委屈", "心累", "烦躁", "好烦", "郁闷"]
        if any(w in user_text for w in neg_keywords):
            return self._fb_negative(pid, name, emo, activity, intimacy, user_text)

        # --- 4. 想念/爱意 ---
        if any(w in user_text for w in ["想你", "想你了", "想念", "爱你", "喜欢你", "好喜欢"]):
            return self._fb_love(pid, name, dom, intimacy, user_text)

        # --- 5. 询问她在干嘛 ---
        if any(w in user_text for w in ["在干嘛", "做什么", "忙什么", "今天过得怎么样",
                                         "今天怎么样", "在家干嘛", "在家做啥", "干嘛呢"]):
            return self._fb_what_doing(pid, name, activity, emo, user_text)

        # --- 6. 打招呼 ---
        if any(w in user_text for w in ["你好", "嗨", "hi", "hello", "早啊",
                                         "晚上好", "下午好", "早上好", "晚安"]):
            return self._fb_greeting(pid, name, emo, user_text)

        # --- 7. 兜底 ---
        return self._fb_default(pid, name, dom, val, activity, health, user_text)

    # ============================================================
    # 意图子方法
    # ============================================================

    def _fb_threaten(self, pid: str, name: str, dom: str, intimacy: int, user_text: str) -> str:
        """分手/威胁 → 强烈情绪反应"""
        if intimacy < 30:
            # 关系尚浅，冷淡回应
            pool = [
                "……随便你。",
                "哦，那行吧。",
                "随你便。",
            ]
            return self._pick(user_text, pool)

        replies = {
            "bai_rou": [
                "（眼眶红了）你……你是认真的吗？我哪里做得不好，你告诉我……",
                "（声音颤抖）不要……不要这样好不好……我改，我都可以改的。",
                "（低头沉默了很久）……你真的想好了吗？",
            ],
            "ye_ruxue": [
                "（手指微微收紧，面色不变）……理由。",
                "（别过脸）……行。别后悔。",
                "（冷冷一笑）你确定？走出这扇门，就别回来了。",
            ],
            "liu_qingning": [
                "（愣住两秒，随即扬起下巴）哼！分就分！你以为我会挽留你吗！……（转过身去，肩膀微微发抖）",
                "哈？你开什么玩笑！……你认真的？……（声音越来越小）我才不在乎……",
                "笨蛋！你以为换个人就会比我好吗！……算了，你走吧。",
            ],
            "mo_xiaoran": [
                "（眼神骤然暗下来）……分？你不会有机会的。你永远都是我的。",
                "（笑了，笑得很冷）你试试看。你离不开我的，你知道的。",
                "（慢慢走近）再说一遍？……我劝你想清楚再开口。",
            ],
            "gu_wanqing": [
                "（笑容瞬间凝固）……诶？我、我是不是听错了？",
                "不要开玩笑啦！这种玩笑一点都不好笑……（声音越来越小）",
                "（咬着嘴唇，强颜欢笑）你说什么？风太大我没听清……",
            ],
            "xiao_ying": [
                "（深深鞠躬）如果这是主人的意愿……我会服从。但请允许我说，这不是我想要的。",
                "主人……是我服务得不够好吗？请给我改正的机会。",
                "（跪坐下来，声音很轻）请至少告诉我原因，好吗？",
            ],
            "xingye_liuli": [
                "诶！剧情突然进入了Bad Ending路线？！不行不行，我要求重来！",
                "喂喂，你是在读什么奇怪的台词吗？这种flag可不能乱立啊！",
                "啊哈哈……这、这是隐藏剧情对吧？快告诉我正确答案的选项在哪里！",
            ],
            "su_nian": [
                "（眼泪啪嗒啪嗒掉下来）不要……我不要……呜呜……",
                "（抓住你的衣角不放）不行！绝对不行！你说了不算！",
                "我哪里不好你告诉我嘛……我改，我全改……不要走……",
            ],
            "lin_tangtang": [
                "（愣住，随即挑眉）哦？你确定？错过了我，可找不到第二个这样的姐姐了哦。",
                "（笑容不变，但眼底没有笑意）好啊，你走。但你记住，不是谁都像我这样对你的。",
                "（沉默片刻，轻声）……你认真的话，我不拦你。但我会等你回来。",
            ],
            "hua_li": [
                "（大眼睛蓄满泪水）欧尼酱不要我了吗……是我画的画不好看吗……",
                "哇——（放声大哭）我不让你走！欧尼酱是我的！",
                "（抽泣着）我、我会变得更好的……欧尼酱再给我一次机会好不好……",
            ],
        }
        pool = replies.get(pid, replies["bai_rou"])
        return self._pick(user_text, pool)

    def _fb_criticized(self, pid: str, name: str, dom: str, user_text: str) -> str:
        """抱怨/批评 → 情绪化反应"""
        replies = {
            "bai_rou": [
                "（愣了一下）……对不起，我是不是哪里让你不开心了？你说，我听着。",
                "（有些委屈地低头）我只是……想让你好好的。如果让你烦了，我注意。",
                "（轻声）你说的话，我会好好记住的。",
            ],
            "ye_ruxue": [
                "（不为所动）说完了？",
                "（瞥你一眼）……你才知道？",
                "（面无表情）嗯，然后呢？",
            ],
            "liu_qingning": [
                "哈？！你再说一遍！……我、我那是为你好！不领情拉倒！",
                "（炸毛）你说谁烦呢！我还没嫌你烦呢！哼！",
                "（气鼓鼓地转过身）行行行，我不管你了行了吧！……（偷偷瞄你一眼）",
            ],
            "mo_xiaoran": [
                "（微笑，但眼神很危险）你说得对……所以你还是乖乖听我的比较好。",
                "抱怨我？你知道吗，这说明你在乎我。我很开心。",
                "（歪头看着你）那你要换一个吗？……开玩笑的，你换不了。",
            ],
            "gu_wanqing": [
                "诶～怎么突然这么说！我今天可乖了好不好！",
                "（鼓起腮帮子）你心情不好也不能拿我撒气呀！来，吃块糖消消火～",
                "好啦好啦，我的错我的错，别生气了嘛～",
            ],
            "xiao_ying": [
                "（立刻低头）非常抱歉，如果我的言行让主人感到困扰，我会立刻改进。",
                "请主人具体指出我的不足之处，我会认真改正。",
                "（不安地搓手）主人批评得对，我会反思的。",
            ],
            "xingye_liuli": [
                "呜哇，突然进入黑化吐槽模式！这展开也太刺激了吧！",
                "诶——我对你的好感度可是满格的，你怎么能这样！系统是不是出bug了？",
                "哼！你这是在给我叠加「被嫌弃」的debuff吗！快撤回！",
            ],
            "su_nian": [
                "（眼眶立刻红了）呜……你是不是不喜欢我了……",
                "我、我就是想跟你多待一会儿嘛……这也算烦吗……",
                "（小声嘟囔）那我不说话了还不行嘛……",
            ],
            "lin_tangtang": [
                "（笑眯眯）说得好，继续说。等你消停了，咱们再慢慢算账。",
                "哟，今天胆子不小嘛。敢这么跟姐姐说话？",
                "（托腮看你）你能这么直接地表达自己，我其实还挺高兴的。不过——态度扣十分。",
            ],
            "hua_li": [
                "欧尼酱凶我……（眼泪在打转）花花做错什么了嘛……",
                "呜呜……我以后不乱画了……也不乱唱歌了……",
                "（缩成一团）对不起……是我不好……",
            ],
        }
        pool = replies.get(pid, replies["bai_rou"])
        return self._pick(user_text, pool)

    def _fb_negative(self, pid: str, name: str, emo, activity: str,
                     intimacy: int, user_text: str) -> str:
        """负面情绪 → 共情安抚"""
        dom, _ = emo.dominant_emotion

        # 情绪基调前缀
        tone_prefix = ""
        if dom == "sad":
            tone_prefix = "（虽然自己也有点低落，但看到你这样更心疼了）"
        elif dom == "angry":
            tone_prefix = "（把脾气压下去，声音放柔）"

        replies = {
            "bai_rou": [
                f"{tone_prefix}累了吧……来，靠着我歇会儿。不管你外面多难，家里有我呢。",
                f"（轻轻握住你的手）辛苦了。要不要我给你按按肩膀？什么事都可以慢慢跟我说。",
                f"（柔声）别一个人扛着。你跟我说说，说出来会好受些。",
            ],
            "ye_ruxue": [
                f"{tone_prefix}……累了就歇。别逞强。",
                f"（倒了杯水推过来，不说话，但眼神里带着关切）",
                f"（沉默片刻）……谁让你不开心的？跟我说。",
            ],
            "liu_qingning": [
                f"哼……谁、谁关心你了！只是刚好没事做才问问而已！",
                f"笨蛋，累了就休息啊，难道还要我教你？……不过，如果真的很难受，可以说给我听。",
                f"（别扭地转过头去，声音变轻）……肩膀借你一下。就一下。",
            ],
            "mo_xiaoran": [
                f"{tone_prefix}谁让你这么累的？告诉我……我不会放过他的。",
                f"（眼神暗了暗）你不开心，我也不开心。让我陪着你，哪里都不要去。",
                f"累了就留在我身边吧。我会让所有让你累的东西都消失。",
            ],
            "gu_wanqing": [
                f"哎呀你怎么啦！来来来，我刚在{activity}的时候想到一个超好玩的事，保证你听了就笑！",
                f"别丧气嘛！你看今天阳光多好，我刚做了小点心，尝一口心情就会变好的！",
                f"累了？那正好！来来来坐下，我给你讲个今天的趣事——",
            ],
            "xiao_ying": [
                f"{tone_prefix}主人辛苦了。需要我准备热毛巾和茶吗？请让我来照料您。",
                f"（微微鞠躬）请主人先坐下休息。我去准备舒缓疲劳的花草茶。",
                f"主人的疲惫就是我的失职。请告诉我，我能为您做些什么？",
            ],
            "xingye_liuli": [
                f"呜哇，你的HP值正在下降！快用我的治愈魔法——<3 <3 <3 好啦，血条回满了吗？",
                f"这不是游戏里的困难模式，是现实呢……但没关系，你的队友（我！）永远在线！",
                f"状态异常「疲惫」debuff检测到！来来来，喝一瓶「中二少女元气药水」——其实是热可可啦。",
            ],
            "su_nian": [
                f"（扑过来抱住）不要难过嘛……我蹭蹭你就好了！",
                f"唔……我不太会安慰人，但可以一直陪着你。你想说话我就听，不想说我就安静待着。",
                f"我给你讲个冷笑话好不好？保证让你忘记烦恼——或者被冷到忘记！",
            ],
            "lin_tangtang": [
                f"哟～我们家小朋友今天怎么蔫蔫的？来，姐姐给你充充电。",
                f"（凑近一点）累了？那姐姐教你一个秘诀——先笑一下，笑不出来我帮你。",
                f"谁欺负你了？告诉我。我虽然不会打架，但我能说得他怀疑人生。",
            ],
            "hua_li": [
                f"欧尼酱不开心吗？花花画了一幅画！你看——这是太阳公公，这是小花，还有欧尼酱！",
                f"欧尼酱累了就抱抱我吧！妈妈说拥抱可以治愈一切！",
                f"欧尼酱不哭！我给你唱首歌……小兔子乖乖，把门开开～欧尼酱要开心起来哦！",
            ],
        }
        pool = replies.get(pid, replies["bai_rou"])
        return self._pick(user_text, pool)

    def _fb_love(self, pid: str, name: str, dom: str, intimacy: int, user_text: str) -> str:
        """想念/爱意 → 角色化回应"""
        replies = {
            "bai_rou": [
                "（脸微微红）我也想你呀……每天都会想，你什么时候来找我。",
                "被你需要的感觉真好。我也最喜欢你了。",
                "（温柔地笑）嗯，我在呢。一直都在。",
            ],
            "ye_ruxue": [
                "……知道了。（嘴角有一丝不易察觉的弧度）",
                "（没看你，但声音比平时柔和）……我也没说不喜欢你。",
                "（沉默两秒）……烦死了。但还行。",
            ],
            "liu_qingning": [
                "哼……我也……有一点点想你啦！就一点点！不要得意！",
                "突、突然说这个干嘛！肉麻死了！……不过，还行，你继续说。",
                "（脸瞬间红了）谁允许你说这种话的！……但我不讨厌。",
            ],
            "mo_xiaoran": [
                "（眼睛亮了）再说一遍。……我要听你每天都说。",
                "呵呵……你知道我等这句话多久了吗？你说了就不能反悔。",
                "（盯着你看，表情很认真）你说的是真心话对吧？我最讨厌谎言了。",
            ],
            "gu_wanqing": [
                "嘿嘿嘿，我就知道！谁不喜欢我这么可爱的人呢～",
                "（开心地蹦了一下）我也想你呀！我今天遇到好多事想跟你说！",
                "哇，突然这么甜！你吃糖了吗？不过我喜欢！",
            ],
            "xiao_ying": [
                "（微微脸红，低头）能被主人这样挂念……是我最大的荣幸。",
                "我也每天都在想着如何更好地服务主人。",
                "（轻声）主人说的话……让我心跳得好快。",
            ],
            "xingye_liuli": [
                "诶诶诶！好感度突然爆表了！系统警告！系统警告！——算了不管了，我也喜欢你！",
                "这就是传说中的「羁绊事件」吗！CG已解锁，存档成功！",
                "你这么直球我会害羞的啦！……骗你的，再说一点，我爱听。",
            ],
            "su_nian": [
                "（扑过来蹭蹭蹭）喜欢喜欢喜欢！全世界最喜欢你了！",
                "嘿嘿～被你喜欢的感觉真好。我要黏着你一整天！",
                "你说喜欢我的时候眼睛好温柔哦……我记住了，不许反悔！",
            ],
            "lin_tangtang": [
                "（托腮看你，笑眯眯）啧啧啧，今天嘴这么甜，是不是做什么亏心事了？……开玩笑的，姐姐很开心。",
                "是吗？那证明给我看。……过来，抱一下。",
                "（眼睛弯成月牙）哎呀，说了这种话可要负责的哦。姐姐记住了。",
            ],
            "hua_li": [
                "欧尼酱喜欢花花！好开心！（原地转圈圈）花花也最喜欢欧尼酱了！",
                "（伸手要抱抱）那欧尼酱要每天都来找花花玩哦！拉勾！",
                "欧尼酱说了「喜欢」！今天是花花的幸运日！要画下来纪念！",
            ],
        }
        pool = replies.get(pid, replies["bai_rou"])
        return self._pick(user_text, pool)

    def _fb_what_doing(self, pid: str, name: str, activity: str, emo, user_text: str) -> str:
        """询问在干嘛 → 结合生活活动"""
        dom, _ = emo.dominant_emotion

        # 情绪微调
        mood_note = ""
        if dom == "happy":
            mood_note = f"心情还特别好～"
        elif dom == "tired":
            mood_note = f"不过有点累，正想歇会儿你就来了～"
        elif dom == "sad":
            mood_note = f"虽然心情一般，但看到你问我就好多了。"

        replies = {
            "bai_rou": [
                f"刚刚在{activity}呢，你一来我就停下来了～{mood_note}",
                f"在{activity}呀。不过你找我，这个更重要。",
                f"（笑着看你）{activity}中，但已经不想继续了，想跟你聊天。",
            ],
            "ye_ruxue": [
                f"{activity}。……你有事？",
                f"（头也不抬）{activity}。但你可以说。",
                f"……在{activity}。你来了就歇会儿。",
            ],
            "liu_qingning": [
                f"在{activity}啊！不然还能干嘛！……不过你问都问了，我陪你聊两句也不是不行。",
                f"刚在{activity}，然后你就冒出来了。哼，算你来得是时候。",
                f"（放下手里的东西）{activity}呢。不过你说吧，我听着。",
            ],
            "mo_xiaoran": [
                f"在{activity}……也在等你。你终于来问我了。",
                f"（轻轻一笑）{activity}。不过你问我的时候，我的心思就已经不在那上面了。",
                f"在{activity}，同时在想你今天会不会来找我。你来了，我很高兴。",
            ],
            "gu_wanqing": [
                f"我刚在{activity}呢！然后突然想到一个超好玩的——就刚好碰到你问我！",
                f"在{activity}呀～不过这不是重点！重点是今天我遇到了——算了你先说你找我干嘛！",
                f"（兴奋地）你问得正好！我正好在{activity}的时候发现了一个新东西！",
            ],
            "xiao_ying": [
                f"正在做{activity}。不过主人优先，请吩咐。",
                f"在完成今天的{activity}。主人需要我暂停手上的事情吗？",
                f"（端正站好）正在{activity}，但随时可以切换到服务主人的模式。",
            ],
            "xingye_liuli": [
                f"正在执行日常任务「{activity}」！但你一出现，任务就自动暂停了——这就是主角光环吗！",
                f"本日日程：{activity}。当前状态：被你打断了——但我喜欢！",
                f"在进行{activity}的支线任务！不过主线剧情明显是你这边的，快来推进！",
            ],
            "su_nian": [
                f"在{activity}呀～不过已经不想做了！想跟你玩！",
                f"（放下手里的东西跑过来）刚才在{activity}，现在在你这里！",
                f"唔……在{activity}。但你好不容易找我，我不想做别的了。",
            ],
            "lin_tangtang": [
                f"在{activity}呢～怎么，想姐姐了？还是查岗？",
                f"（笑眯眯地）刚在{activity}。不过你一来，比那个有意思多了。",
                f"在{activity}——但被你打断了。说吧，姐姐洗耳恭听。",
            ],
            "hua_li": [
                f"欧尼酱！花花刚刚在{activity}！欧尼酱来找花花玩了吗？",
                f"在{activity}～不过欧尼酱来了就一起玩吧！{activity}可以等一等！",
                f"（蹦蹦跳跳跑过来）刚才在{activity}！欧尼酱呢，欧尼酱今天做了什么呀？",
            ],
        }
        pool = replies.get(pid, replies["bai_rou"])
        return self._pick(user_text, pool)

    def _fb_greeting(self, pid: str, name: str, emo, user_text: str) -> str:
        """打招呼 → 角色化问候"""
        dom, val = emo.dominant_emotion

        # 情绪影响问候语气
        if dom == "happy" and val > 60:
            extra = "今天心情特别好呢～"
        elif dom == "sad":
            extra = "（勉强打起精神）嗯……"
        elif dom == "angry":
            extra = "（语气有点淡）"
        else:
            extra = ""

        replies = {
            "bai_rou": [
                f"你来啦～{extra}今天想聊什么？",
                f"嗯，我在呢。{extra}等你好久了。",
                f"（抬头微笑）嗨～{extra}今天过得怎么样？",
            ],
            "ye_ruxue": [
                f"嗯。{extra}",
                f"{extra}……来了？",
                f"（抬眼看你）{extra}说。",
            ],
            "liu_qingning": [
                f"哼，终于想起来找我了吗？{extra}我可没有等很久！",
                f"哦～还知道来啊。{extra}我还以为你把我忘了呢！",
                f"（抱着手臂）来了？{extra}行吧，陪你聊聊。",
            ],
            "mo_xiaoran": [
                f"（盯着你）来了？{extra}今天……没有去找别人吧？",
                f"你终于来了。{extra}我一个人等了很久呢。",
                f"（嘴角微扬）欢迎回来。{extra}你是我的，对吧？",
            ],
            "gu_wanqing": [
                f"呀！你来了！{extra}我跟你说我跟你说——",
                f"嗨嗨嗨！{extra}今天有一箩筐的事要跟你讲！",
                f"（挥手）这里这里！{extra}快过来坐！",
            ],
            "xiao_ying": [
                f"欢迎。{extra}今天需要我为您做些什么？",
                f"（微微鞠躬）主人好。{extra}茶还是咖啡？",
                f"您来了。{extra}已准备好，随时听候差遣。",
            ],
            "xingye_liuli": [
                f"哟！勇者大人驾到！{extra}今天的冒险从哪里开始？",
                f"登录成功！{extra}欢迎回到我的世界～",
                f"来了来了！{extra}今天是攻略日常还是推进主线？",
            ],
            "su_nian": [
                f"（扑过来）你来了你来了！{extra}我等了好久了！",
                f"嘿嘿～{extra}你终于来了，我今天攒了好多话要跟你说！",
                f"嗨！{extra}（眨眨眼）你今天特别好看诶！",
            ],
            "lin_tangtang": [
                f"哟～{extra}来了？今天看起来精神不错嘛。",
                f"（托腮看你）终于想起姐姐了？{extra}坐下聊聊？",
                f"你来了呀。{extra}今天想跟姐姐聊什么？",
            ],
            "hua_li": [
                f"欧尼酱！{extra}（挥舞小手）花花在这里！",
                f"（蹦蹦跳跳）欧尼酱来啦！{extra}今天要一起画画吗？",
                f"欧尼酱欧尼酱！{extra}今天有好吃的糖要分给欧尼酱！",
            ],
        }
        pool = replies.get(pid, replies["bai_rou"])
        return self._pick(user_text, pool)

    def _fb_default(self, pid: str, name: str, dom: str, val: int,
                    activity: str, health: int, user_text: str) -> str:
        """兜底回复 → 结合当前情绪状态和场景"""
        # 关系健康度低 → 疏离感
        if health < 40:
            replies_distanced = {
                "bai_rou": ["……嗯。", "（轻声）我在呢。", "……你说。"],
                "ye_ruxue": ["……", "嗯。", "……在。"],
                "liu_qingning": ["……干嘛。", "（没精打采）哼。", "……哦。"],
            }
            if pid in replies_distanced:
                return self._pick(user_text, replies_distanced[pid])
            return "……嗯。"

        # 按情绪状态选择回复
        if dom == "happy" and val > 60:
            pool = {
                "bai_rou": [
                    f"嘻嘻，跟你聊天真的好开心～我刚刚还在{activity}呢。",
                    "不知道为什么，每次你说话我都忍不住想笑。",
                    f"（心情很好）今天真是个不错的日子，有你在就更好了。",
                ],
                "ye_ruxue": [
                    f"{activity}。……今天不赖。",
                    "……你来了之后，好像没那么无聊了。",
                    "（嘴角微扬）嗯。你继续说。",
                ],
                "liu_qingning": [
                    f"哼～今天心情还不错，就勉强多陪你聊几句吧！",
                    f"（晃着腿）今天还行吧。你也是，难得看起来没那么欠揍。",
                    f"嗯？我今天心情好，你有什么想说的快说，过期不候！",
                ],
                "mo_xiaoran": [
                    "呵呵……今天心情很好呢，因为你来了。",
                    "看到你我就开心。你今天有想我吗？",
                    "（轻声哼着歌）心情好的时候，就想对你好一点。",
                ],
                "gu_wanqing": [
                    f"今天超开心的！你知道吗，我刚刚在{activity}的时候——啊算了，你先说！",
                    "啦啦啦～心情好到飞起！快跟我说话，我觉得今天什么都是好事！",
                    "你今天看起来也不错嘛！来，让我把这份开心传染给你！",
                ],
                "xiao_ying": [
                    f"今天一切顺利。{activity}也完成了。主人有什么想聊的吗？",
                    "主人心情好的时候，我也觉得整个世界都明亮了。",
                    "（微微一笑）我正在{activity}。主人需要我做什么吗？",
                ],
                "xingye_liuli": [
                    f"耶！今日心情指数MAX！{activity}进度100%，可以自由活动了！",
                    "今天运气值爆表，我觉得抽卡都能出SSR！你要不要也来蹭蹭好运？",
                    "嘿嘿，开心的时候说话都自带BGM～你听到了吗？",
                ],
                "su_nian": [
                    f"嘿嘿嘿～今天好开心！你有没有觉得空气都是甜的？",
                    "（蹭过来）不知道为什么，今天特别想黏着你！",
                    f"我今天在{activity}的时候就在想，你什么时候来找我呢～",
                ],
                "lin_tangtang": [
                    f"呀，今天心情好，就多宠你一点吧～想吃什么？姐姐请客。",
                    "今天状态不错，看什么都顺眼——包括你。说吧，想聊什么？",
                    "（伸了个懒腰）嗯～心情舒畅。你今天有没有什么好事分享？",
                ],
                "hua_li": [
                    f"欧尼酱！花花今天好开心！因为{activity}完成了！欧尼酱开心吗？",
                    "（哼着歌）啦～啦啦～今天的阳光好暖，欧尼酱也好暖！",
                    "欧尼酱欧尼酱！我今天发现了一个秘密——开心的秘密就是欧尼酱！",
                ],
            }
        elif dom == "sad":
            pool = {
                "bai_rou": [
                    f"嗯……有点不太开心，不过看到你好多了。{activity}也没心思做。",
                    "（叹了口气）没什么大事，就是有点低落。你能陪我一会吗？",
                    "（勉强笑了笑）没关系的，有时候就是会这样。你来了我就好一些了。",
                ],
                "ye_ruxue": [
                    "……不想说话。但你可以待着。",
                    "（沉默地看着窗外）……嗯。",
                    "别问。……你在就行。",
                ],
                "liu_qingning": [
                    "（闷闷不乐）没什么……就是不太想说话。你不用管我。",
                    "……今天不太顺利。不过你不用安慰我，我自己会好的。",
                    "（抱着膝盖）有点郁闷。但你要是想聊天，我也可以听。",
                ],
                "mo_xiaoran": [
                    "（眼神有些空洞）有时候……会害怕。怕你也会离开。",
                    "没事。就是偶尔会觉得世界有点灰。但你在就好。",
                    "（沉默地靠过来）让我靠一会儿。不用说话。",
                ],
                "su_nian": [
                    "（眼眶红红的）今天有点难过……你能抱抱我吗？",
                    "唔……不知道为什么想哭。但是看到你又有点想笑。",
                    "（小声）我今天被一件小事弄哭了。好丢脸……",
                ],
            }
        elif dom == "angry":
            pool = {
                "bai_rou": [
                    "（深吸一口气）对不起，我情绪不太好。不是针对你。",
                    "我现在心情不太好，能让我安静一会儿吗？",
                    "（抿着嘴）……没什么，过一会儿就好了。你先忙你的。",
                ],
                "ye_ruxue": [
                    "……别惹我。",
                    "（冷冷地）现在不想说话。",
                    "……（沉默，但眼神不太友好）",
                ],
                "liu_qingning": [
                    "……不想说话。不是针对你。但也别惹我。",
                    "哼！今天烦死了！你别理我！",
                    "（攥着拳头）有些人就是欠揍！不是你，你别紧张。",
                ],
                "mo_xiaoran": [
                    "……有人让我不高兴了。不过你放心，跟你没关系。",
                    "（眼神阴冷）别问。你不会想知道的。",
                    "我不想对你发火。所以先安静一会儿。",
                ],
                "lin_tangtang": [
                    "（揉了揉太阳穴）今天有人踩了我的线。不过姐姐会自己处理的。",
                    "别紧张，不是冲你。只是需要冷静一下。",
                    "（冷笑了一下又收了回去）没事，成年人，自己消化。",
                ],
            }
        else:
            # neutral / calm
            pool = {
                "bai_rou": [
                    f"嗯，我在听呢。{activity}也做得差不多了。",
                    f"（歪头看你）怎么了？我在呢，慢慢说。",
                    "（温柔地）我在这儿呢。你想说什么都可以。",
                ],
                "ye_ruxue": [
                    "嗯。",
                    "……在听。说。",
                    "（不紧不慢地）你继续。",
                ],
                "liu_qingning": [
                    "嗯？你说吧，我听着呢。……不要以为我会认真听！",
                    "哦。那你继续。我姑且听听你要说什么。",
                    "（托腮）说吧，趁我还有耐心。",
                ],
                "mo_xiaoran": [
                    "在呢。我一直都在等你说话。",
                    "（安静地看着你）你说的时候，我在认真听。",
                    "（轻轻应了一声）嗯。什么都好，只要是你说的话。",
                ],
                "gu_wanqing": [
                    "嗯嗯，在听在听！你说你说！",
                    f"（竖起耳朵）好嘞！我暂停了一下{activity}，专心听你说！",
                    f"来啦来啦，刚在{activity}，但你一说我就来了！",
                ],
                "xiao_ying": [
                    "（端正站姿）在。主人请说。",
                    "随时准备聆听主人的话。请讲。",
                    "是的，主人。我在关注您的一言一行。",
                ],
                "xingye_liuli": [
                    "收到！信息接收模式已启动，请开始你的表演——啊不，说话。",
                    "耳朵竖起来了！你讲的每一句话我都会认真听！",
                    "触发对话事件！我能感觉到这是一个重要的剧情节点！",
                ],
                "su_nian": [
                    "在呢在呢！你说什么我都爱听！",
                    "（凑近一点）我在听哦～你说话的时候声音好好听。",
                    "嗯！我竖起耳朵了！快说快说！",
                ],
                "lin_tangtang": [
                    "说吧，姐姐在听。一字不漏地听。",
                    "（换了个舒服的姿势）好了，准备好当你的听众了。请开始。",
                    "嗯嗯，你讲。顺便让我看看你今天状态怎么样。",
                ],
                "hua_li": [
                    f"在呢在呢！花花刚做完{activity}！欧尼酱要说什么？",
                    "欧尼酱！花花认真听！你说的每一个字我都要记住！",
                    "（端正坐好）花花准备好了！欧尼酱请开始吧！",
                ],
            }

        # 兜底角色的兜底
        final_pool = pool.get(pid, pool.get("bai_rou", ["嗯，我在听呢～"]))
        return self._pick(user_text, final_pool)


def main():
    """程序入口"""
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    AICompanionApp().run()


if __name__ == "__main__":
    main()
