"""
生活模拟器 (Daily Life Simulator)
模拟角色的24小时时间线、每周循环、自主活动和主动打扰判定。
"""

from datetime import datetime, time
from typing import Optional
import random


class LifeSimulator:
    """
    生活模拟器

    职责：
    1. 生成和管理24小时时间线
    2. 根据当前时间查询角色活动
    3. 判定是否应该主动打扰用户
    4. 区分工作日/周末/季节的行为差异
    """

    # 工作日时间线
    WEEKDAY_TIMELINE: list[tuple[str, str]] = [
        ("06:00", "睡眠中"),
        ("07:00", "起床洗漱"),
        ("07:30", "早餐 / 晨间准备"),
        ("08:10", "通勤 / 处理个人事务"),
        ("09:00", "工作中"),
        ("11:30", "午间休息"),
        ("12:30", "午餐时间"),
        ("13:10", "下午工作"),
        ("16:00", "下午茶歇"),
        ("16:30", "工作收尾"),
        ("17:30", "下班通勤"),
        ("18:20", "准备晚餐 / 晚餐中"),
        ("19:30", "晚间自由活动"),
        ("21:30", "放松时间（追剧 / 看书 / 画画）"),
        ("23:00", "睡前准备"),
        ("23:30", "入睡"),
    ]

    # 周末时间线
    WEEKEND_TIMELINE: list[tuple[str, str]] = [
        ("08:00", "睡眠中（赖床模式）"),
        ("09:00", "悠闲起床"),
        ("09:30", "早午餐"),
        ("10:10", "自由活动（兴趣爱好）"),
        ("12:00", "午餐"),
        ("12:40", "外出 / 社交 / 购物"),
        ("15:30", "下午茶 / 休息"),
        ("16:00", "个人时光（创作 / 学习 / 放松）"),
        ("17:30", "晚餐准备 / 晚餐"),
        ("18:30", "晚间活动（电影 / 游戏 / 聊天）"),
        ("20:30", "深度放松"),
        ("23:00", "睡前准备"),
        ("23:30", "入睡"),
    ]

    # 自主活动列表
    AUTONOMOUS_ACTIVITIES: list[str] = [
        "在画画",
        "在弹钢琴",
        "在做甜点",
        "在逛超市",
        "在看书",
        "在追番",
        "在练瑜伽",
        "在写日记",
        "在学新技能",
        "在和朋友聊天",
        "在逛街",
        "在做手工",
        "在给阳台的花浇水",
        "在听音乐",
        "在泡澡",
        "在烘焙",
        "在打游戏",
        "在整理房间",
        "在拍照",
        "在发呆想事情",
        "在泡咖啡",
        "在练习插花",
    ]

    # 主动打扰模板
    CONTACT_TEMPLATES: dict[str, list[str]] = {
        "missing_user": [
            "在干嘛呀～突然想你了",
            "好安静哦……你在忙吗？",
            "偷偷来看你一眼，不要告诉别人我来过～",
        ],
        "interesting_find": [
            "你快看这个！太有意思了！",
            "猜猜我刚才看到了什么？",
            "天哪我发现了一个宝藏！",
        ],
        "nightmare": [
            "我做了一个不太好的梦……可以陪我说说话吗？",
            "有点害怕……你在吗？",
            "刚做了一个好真实的梦，吓醒的那种。",
        ],
        "good_news": [
            "告诉你一个好消息！猜猜看～",
            "今天运气好好！分享给你！",
            "有个事想第一时间告诉你！",
        ],
        "feeling_lonely": [
            "想你了……你在忙吗？",
            "今天莫名有点想你……",
            "没什么事，就是特别想跟你说说话。",
        ],
        "saw_something_reminded": [
            "刚才看到XXX，一下子想到你了",
            "你知道吗，刚刚路过之前我们去过的地方……",
            "看到这个，立刻就想到要发给你",
        ],
        "worry_about_user": [
            "你今天还好吗？总觉得你状态不太对",
            "在忙吗？要不要喝点水休息一下",
            "别太累了哦，适当歇一歇",
        ],
        "share_mood": [
            "今天莫名心情超好，想分你一半",
            "今天有点小情绪，但看到你就好了",
            "此刻正在发呆，想你了。",
        ],
        "remind_user": [
            "你今天的日程看了吗？别忘了XX哦",
            "天气要变凉了，记得加衣服",
            "你昨天说今天要做XX的，做了吗？",
        ],
        "random_check_in": [
            "滴——您有一条来自女朋友的消息",
            "在吗在吗在吗？不重要就是想叫你一下",
            "✨ 没有什么事，就是给你发个星星",
        ],
    }

    def __init__(self, persona_id: str = "default"):
        """
        初始化生活模拟器

        Args:
            persona_id: 角色ID，用于获取角色特定的活动偏好
        """
        self.persona_id = persona_id
        self._last_contact_time: Optional[datetime] = None
        self._contact_count_today: int = 0
        self._current_date: Optional[str] = None
        self._random = random.Random()

    def _get_character_activity_bonus(self, default_activity: str) -> str:
        """
        根据角色ID添加特定活动偏好

        Args:
            default_activity: 默认活动

        Returns:
            角色特定的活动描述
        """
        persona_activities = {
            "ye_ruxue": ["在品红酒", "在批阅文件", "在练习书法", "在听古典乐"],
            "bai_rou": ["在做手工甜点", "在整理家里", "在织围巾", "在煲汤"],
            "liu_qingning": ["在练小提琴", "在看商业杂志", "在喝咖啡发呆"],
            "mo_xiaoran": ["在写代码", "在看心理类书籍", "在暗处观察"],
            "gu_wanqing": ["在照料阳台植物", "在泡花茶", "在写日记", "在做瑜伽"],
            "xiao_ying": ["在打扫卫生", "在准备食材", "在熨衣服", "在学做新菜"],
            "xingye_liuli": ["在打游戏", "在追新番", "在cosplay试装", "在看同人"],
            "su_nian": ["在和年糕玩", "在看电影", "在画画"],
            "lin_tangtang": ["在研究新品咖啡", "在调试鸡尾酒配方", "在听爵士"],
            "hua_li": ["在画水彩", "在折纸", "在看动画片", "在校园里看猫"],
        }
        char_activities = persona_activities.get(self.persona_id, [])
        if char_activities and self._random.random() < 0.4:
            return self._random.choice(char_activities)
        return default_activity

    def get_current_activity(self, current_time: datetime | None = None) -> dict:
        """
        获取当前时间的角色活动

        Args:
            current_time: 当前时间，不传则使用系统时间

        Returns:
            包含时间和活动的字典
        """
        now = current_time or datetime.now()
        now_str = now.strftime("%H:%M")
        is_weekend = now.weekday() >= 5

        # 季节性调整
        season = self._get_season(now)
        if season == "summer":
            wake_offset = -30  # 夏天早起
            sleep_offset = +30  # 夏天晚睡
        elif season == "winter":
            wake_offset = +30  # 冬天晚起
            sleep_offset = -30  # 冬天早睡
        else:
            wake_offset = 0
            sleep_offset = 0

        # 选择时间线
        timeline = self.WEEKEND_TIMELINE if is_weekend else self.WEEKDAY_TIMELINE

        # 查找当前时间段的活动
        current_activity = "未知活动"
        for t, activity in reversed(timeline):
            if t <= now_str:
                current_activity = self._get_character_activity_bonus(activity)
                break

        return {
            "time": now_str,
            "activity": current_activity,
            "is_workday": not is_weekend,
            "is_weekend": is_weekend,
            "season": season,
        }

    def should_initiate_contact(self, current_time: datetime | None = None) -> dict:
        """
        判定是否应该主动发起联系以及发什么内容

        Args:
            current_time: 当前时间

        Returns:
            包含是否联系、消息内容和原因
        """
        now = current_time or datetime.now()
        now_str = now.strftime("%H:%M")
        is_weekend = now.weekday() >= 5

        # 重置每日计数
        today = now.strftime("%Y-%m-%d")
        if self._current_date != today:
            self._contact_count_today = 0
            self._current_date = today

        # 硬限制
        if self._contact_count_today >= 3:
            return {"should_contact": False, "reason": "今日已达上限"}

        # 时间限制：不在睡觉时间打扰
        hour = now.hour
        if hour < 7 or hour >= 23:
            return {"should_contact": False, "reason": "不在活跃时间"}

        # 间隔限制
        if self._last_contact_time:
            minutes_since = (now - self._last_contact_time).total_seconds() / 60
            if minutes_since < 120:
                return {"should_contact": False, "reason": f"距上次联系仅{int(minutes_since)}分钟"}

        # 各类打扰场景的概率判定
        scenarios = [
            ("feeling_lonely", 0.25, "孤独感触发"),
            ("missing_user", 0.20, "想念触发"),
            ("saw_something_reminded", 0.15, "联想触发"),
            ("good_news", 0.10, "好消息分享"),
            ("random_check_in", 0.10, "随机问候"),
        ]

        for scenario, probability, reason in scenarios:
            if self._random.random() < probability:
                templates = self.CONTACT_TEMPLATES.get(scenario, ["在干嘛呀～"])
                message = self._random.choice(templates)
                self._last_contact_time = now
                self._contact_count_today += 1
                return {
                    "should_contact": True,
                    "message": message,
                    "reason": reason,
                    "time": now_str,
                }

        return {"should_contact": False, "reason": "无触发条件"}

    def get_daily_timeline(self, is_weekend: bool = False) -> list[dict]:
        """
        获取完整的一天时间线

        Args:
            is_weekend: 是否周末

        Returns:
            时间线列表
        """
        timeline = self.WEEKEND_TIMELINE if is_weekend else self.WEEKDAY_TIMELINE
        return [
            {"time": t, "activity": self._get_character_activity_bonus(a)}
            for t, a in timeline
        ]

    @staticmethod
    def _get_season(dt: datetime) -> str:
        """根据日期判断季节"""
        month = dt.month
        if 3 <= month <= 5:
            return "spring"
        elif 6 <= month <= 8:
            return "summer"
        elif 9 <= month <= 11:
            return "autumn"
        else:
            return "winter"
