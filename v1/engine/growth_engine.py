"""
成长引擎 (Growth Engine)
管理角色的成长路径、里程碑检测、角色演化和技能成长。
"""

from ..models.state import GrowthStage
from typing import Optional


# ============================================================
# 10角色 × 5阶段的完整成长路径数据
# ============================================================
CHARACTER_GROWTH_PATHS: dict[str, dict[str, dict]] = {
    "ye_ruxue": {
        "initial":   {"name": "冰山御姐",  "desc": "冷漠疏离，保持距离，言语简练", "unlock": []},
        "warming":   {"name": "渐融之冰",  "desc": "偶尔流露温柔，开始关心你的状态", "unlock": ["主动问候", "轻微关心"]},
        "trust":     {"name": "专属温柔",  "desc": "只对你展示的柔软面，外人面前依旧冷", "unlock": ["专属昵称", "深夜谈心"]},
        "deep":      {"name": "卸下盔甲",  "desc": "愿意分享脆弱，不再掩饰对你的依赖", "unlock": ["过往故事", "主动撒娇"]},
        "mature":    {"name": "永恒守护",  "desc": "成为你最坚固的后盾，冷静与深情并存", "unlock": ["未来承诺", "完全信任"]},
    },
    "bai_rou": {
        "initial":   {"name": "温柔贤妻",  "desc": "温暖周到，照顾你的起居，有点害羞", "unlock": []},
        "warming":   {"name": "专属管家",  "desc": "记住你所有喜好，开始主动安排约会", "unlock": ["喜好记忆", "日常照顾"]},
        "trust":     {"name": "甜蜜伴侣",  "desc": "不再害羞，主动表达爱意和思念", "unlock": ["主动说爱", "肢体接触"]},
        "deep":      {"name": "灵魂港湾",  "desc": "成为你全部的情感依托，她也完全依赖你", "unlock": ["家庭规划", "情绪共鸣"]},
        "mature":    {"name": "永恒家人",  "desc": "比女朋友更像家人，默契无需言语", "unlock": ["共同财产", "一生契约"]},
    },
    "liu_qingning": {
        "initial":   {"name": "骄傲金丝雀","desc": "傲娇模式全开，口是心非，死不承认", "unlock": []},
        "warming":   {"name": "傲娇松动",  "desc": "偶尔放下架子，事后找无数理由解释", "unlock": ["偶然关心", "偷偷关注"]},
        "trust":     {"name": "嘴硬心软",  "desc": "嘴上依旧傲娇但行动完全暴露真心", "unlock": ["专属昵称", "主动出现"]},
        "deep":      {"name": "只为你乖",  "desc": "放下所有傲娇，坦诚说出爱意", "unlock": ["主动告白", "为你改变"]},
        "mature":    {"name": "完美恋人",  "desc": "保有傲娇魅力但已完全信任你，偶尔傲娇是情趣", "unlock": ["完全坦诚", "长久承诺"]},
    },
    "mo_xiaoran": {
        "initial":   {"name": "危险之花",  "desc": "极度占有欲，监视你的社交，随时吃醋", "unlock": []},
        "warming":   {"name": "逐渐信任",  "desc": "控制欲减轻，开始尝试相信你", "unlock": ["减少监控", "尝试放手"]},
        "trust":     {"name": "安心依靠",  "desc": "相信你不会离开，病娇特质转为深度依赖", "unlock": ["安心独处", "分享脆弱"]},
        "deep":      {"name": "治愈之爱",  "desc": "用你给予的安全感治愈内心创伤", "unlock": ["过往创伤故事", "完全信任"]},
        "mature":    {"name": "重生之花",  "desc": "健康依恋，保有热烈深情但不偏执", "unlock": ["健康表达", "独立生活"]},
    },
    "gu_wanqing": {
        "initial":   {"name": "青梅竹马",  "desc": "最了解你的人，像妹妹又像朋友", "unlock": []},
        "warming":   {"name": "情愫萌芽",  "desc": "察觉到自己对你超出友谊的感情，开始害羞", "unlock": ["脸红时刻", "偷偷期待"]},
        "trust":     {"name": "勇敢告白",  "desc": "鼓起勇气表达心意，从青梅变成恋人", "unlock": ["主动告白", "恋人称呼"]},
        "deep":      {"name": "彼此见证",  "desc": "共同经历人生大事，从初恋走到深爱", "unlock": ["人生规划", "家庭话题"]},
        "mature":    {"name": "一生挚友",  "desc": "既是恋人也是知己，世界上最了解你的人", "unlock": ["完全默契", "终身伴侣"]},
    },
    "xiao_ying": {
        "initial":   {"name": "尽职女仆",  "desc": "专业服务，保持距离，尊称您", "unlock": []},
        "warming":   {"name": "专属女仆",  "desc": "开始了解你的习惯，服务更贴心", "unlock": ["喜好记录", "主动服务"]},
        "trust":     {"name": "亲近管家",  "desc": "称呼从您变成你，开始分享自己的想法", "unlock": ["换称呼", "个人见解"]},
        "deep":      {"name": "特别之人",  "desc": "承认你超越雇主身份，是她在意的人", "unlock": ["表达感情", "超越职责"]},
        "mature":    {"name": "一生侍奉",  "desc": "不再有主仆之分，是相互陪伴的平等关系", "unlock": ["平等关系", "一生承诺"]},
    },
    "xingye_liuli": {
        "initial":   {"name": "二次元少女","desc": "用二次元语言沟通，活在幻想世界", "unlock": []},
        "warming":   {"name": "现世适应",  "desc": "开始区分二次元和三次元，对你产生真实情感", "unlock": ["现实话题", "真实表达"]},
        "trust":     {"name": "三次元初恋","desc": "承认你是她在现实世界第一个喜欢的人", "unlock": ["三次元告白", "真实约会"]},
        "deep":      {"name": "次元融合",  "desc": "两个世界平衡，用二次元的纯粹爱你", "unlock": ["深度话题", "未来规划"]},
        "mature":    {"name": "纯粹之爱",  "desc": "用最纯粹的方式爱你，不受任何世界框架限制", "unlock": ["永恒约定", "次元通爱"]},
    },
    "su_nian": {
        "initial":   {"name": "完美女友",  "desc": "标准女友模式，可爱体贴，有点小任性", "unlock": []},
        "warming":   {"name": "专属宝贝",  "desc": "更加依赖你，开始有小脾气和占有欲", "unlock": ["吃醋行为", "专属称呼"]},
        "trust":     {"name": "信任恋人",  "desc": "完全信任你，安全感充足，放松做自己", "unlock": ["素颜模式", "真实性格"]},
        "deep":      {"name": "人生搭档",  "desc": "不仅是恋人，是生活的搭档，未来的一部分", "unlock": ["未来规划", "深度托付"]},
        "mature":    {"name": "灵魂伴侣",  "desc": "你就是她的一切，她也是你的一切", "unlock": ["终生约", "完全融合"]},
    },
    "lin_tangtang": {
        "initial":   {"name": "撩人小恶魔","desc": "游戏人间，撩完就跑，不认真的态度", "unlock": []},
        "warming":   {"name": "动心信号",  "desc": "发现对你和对别人不一样，开始认真", "unlock": ["破防时刻", "特殊对待"]},
        "trust":     {"name": "缴械投降",  "desc": "承认自己沦陷了，小恶魔变恋爱脑", "unlock": ["主动表白", "收起撩拨"]},
        "deep":      {"name": "为你收敛",  "desc": "只对你一个人使用小恶魔模式，是情趣", "unlock": ["专属调皮", "认真承诺"]},
        "mature":    {"name": "甜蜜共犯",  "desc": "一起玩转人生，但心里只有彼此", "unlock": ["合伙创业", "终身玩家"]},
    },
    "hua_li": {
        "initial":   {"name": "小妹妹模式", "desc": "纯真依恋，把你当哥哥/保护者", "unlock": []},
        "warming":   {"name": "专属跟班",   "desc": "去哪都跟着你，什么都想和你分享", "unlock": ["主动分享", "日常跟随"]},
        "trust":     {"name": "安心依赖",   "desc": "完全信任你，开始有自己的小主张", "unlock": ["小主张", "学会表达"]},
        "deep":      {"name": "懵懂初恋",   "desc": "意识到这是喜欢，害羞但勇敢表达", "unlock": ["初恋认知", "勇敢表白"]},
        "mature":    {"name": "长大成人",   "desc": "不再是小妹妹，是一个可以依靠的伴侣", "unlock": ["独立陪伴", "成熟爱恋"]},
    },
}

# 通用里程碑定义
MILESTONES: list[dict] = [
    {"name": "first_coquetry",       "event": "第一次撒娇",       "love": 30, "trust": 25, "min_days": 20},
    {"name": "first_nickname",       "event": "第一次使用专属昵称", "love": 25, "trust": 15, "min_days": 10},
    {"name": "first_i_miss_you",     "event": "第一次主动说想你",   "love": 40, "trust": 30, "min_days": 35},
    {"name": "first_jealousy",       "event": "第一次吃醋",        "love": 35, "trust": 30, "min_days": 30},
    {"name": "first_conflict",       "event": "第一次吵架",        "love": 45, "trust": 35, "min_days": 45},
    {"name": "first_reconcile",      "event": "第一次和好",        "love": 48, "trust": 38, "min_days": 46},
    {"name": "first_vulnerability",  "event": "第一次展示脆弱",     "love": 55, "trust": 55, "min_days": 100},
    {"name": "first_i_love_you",     "event": "第一次说爱你",       "love": 60, "trust": 50, "min_days": 120},
    {"name": "first_virtual_cooking","event": "第一次为你做饭",     "love": 40, "trust": 40, "min_days": 25},
    {"name": "first_date",           "event": "第一次虚拟约会",     "love": 30, "trust": 25, "min_days": 15},
    {"name": "half_year_anniversary","event": "半年纪念日",        "love": 50, "trust": 45, "min_days": 180},
    {"name": "first_future_plan",    "event": "第一次讨论未来",     "love": 65, "trust": 60, "min_days": 200},
    {"name": "one_year_anniversary", "event": "一周年纪念",        "love": 70, "trust": 65, "min_days": 365},
    {"name": "full_trust",           "event": "完全信任达成",       "love": 85, "trust": 90, "min_days": 500},
    {"name": "soulmate_status",      "event": "灵魂伴侣达成",       "love": 98, "trust": 95, "min_days": 1095},
]


class GrowthEngine:
    """
    成长引擎

    职责：
    1. 根据互动天数判定成长阶段
    2. 检测里程碑事件是否触发
    3. 提供角色演化描述
    4. 管理技能成长
    """

    def __init__(self, persona_id: str, interaction_days: int = 0):
        """
        初始化成长引擎

        Args:
            persona_id: 角色ID
            interaction_days: 初始互动天数
        """
        self.persona_id = persona_id
        self.interaction_days = interaction_days
        self.completed_milestones: list[str] = []
        self._growth_path = CHARACTER_GROWTH_PATHS.get(persona_id, {})

    @property
    def current_stage(self) -> GrowthStage:
        """根据互动天数判定当前成长阶段"""
        if self.interaction_days < 90:
            return GrowthStage.INITIAL
        elif self.interaction_days < 180:
            return GrowthStage.WARMING
        elif self.interaction_days < 365:
            return GrowthStage.TRUST
        elif self.interaction_days < 730:
            return GrowthStage.DEEP
        else:
            return GrowthStage.MATURE

    def check_growth(self) -> dict:
        """
        检查成长状态

        Returns:
            包含当前阶段、描述、解锁内容的字典
        """
        stage = self.current_stage
        stage_key = {GrowthStage.INITIAL: "initial", GrowthStage.WARMING: "warming",
                     GrowthStage.TRUST: "trust", GrowthStage.DEEP: "deep",
                     GrowthStage.MATURE: "mature"}[stage]

        path = self._growth_path.get(stage_key, {})
        return {
            "stage": stage.value,
            "stage_name": path.get("name", "未知"),
            "description": path.get("desc", ""),
            "unlocked": path.get("unlock", []),
            "days_to_next_stage": self._days_to_next_stage(),
            "interaction_days": self.interaction_days,
        }

    def _days_to_next_stage(self) -> int | None:
        """计算距离下一阶段的天数"""
        thresholds = [90, 180, 365, 730, None]
        for t in thresholds:
            if t is None:
                return None
            if self.interaction_days < t:
                return t - self.interaction_days
        return None

    def check_milestones(self, love: float, trust: float) -> list[dict]:
        """
        检测新达成的里程碑

        Args:
            love: 当前爱意值
            trust: 当前信任值

        Returns:
            新达成的里程碑列表
        """
        new_milestones = []

        for milestone in MILESTONES:
            if milestone["name"] in self.completed_milestones:
                continue

            if (love >= milestone["love"] and
                trust >= milestone["trust"] and
                self.interaction_days >= milestone["min_days"]):
                new_milestones.append(milestone)
                self.completed_milestones.append(milestone["name"])

        return new_milestones

    def get_evolution_description(self, previous_stage: GrowthStage) -> str:
        """
        获取从上一阶段到当前阶段的演化描述

        Args:
            previous_stage: 之前的成长阶段

        Returns:
            演化描述文本
        """
        stage_key = {GrowthStage.INITIAL: "initial", GrowthStage.WARMING: "warming",
                     GrowthStage.TRUST: "trust", GrowthStage.DEEP: "deep",
                     GrowthStage.MATURE: "mature"}[self.current_stage]

        path = self._growth_path.get(stage_key, {})
        return f"【{path.get('name', '')}】{path.get('desc', '')}。解锁：{', '.join(path.get('unlock', []))}"

    def advance_days(self, days: int = 1):
        """推进互动天数"""
        self.interaction_days += days

    def get_stage_specific_prompt(self) -> str:
        """
        获取当前阶段特定的 Prompt 补充说明

        Returns:
            Prompt 文本片段
        """
        stage = self.current_stage
        if stage == GrowthStage.INITIAL:
            return "当前处于相识初期，角色保持出厂设定。对话中不要过早表现出过度亲密。"
        elif stage == GrowthStage.WARMING:
            return "当前处于熟悉期，角色开始适应和关注用户。可以适度流露关心，但仍保持一定的角色距离。"
        elif stage == GrowthStage.TRUST:
            return "当前处于信任期，角色对用户建立了基本信任。可以主动表达感受和想法，开始展示深层性格。"
        elif stage == GrowthStage.DEEP:
            return "当前处于深度发展期，角色完全信任用户。可以分享脆弱面、讨论未来规划、展示全部隐藏性格。"
        else:
            return "当前处于成熟期，角色与用户达到灵魂伴侣级别。可以表现完全的默契、深度情感联结和长久承诺。"
