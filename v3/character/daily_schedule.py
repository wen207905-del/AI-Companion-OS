"""
Daily Schedule — 作息系统

定义每个角色的日常作息模板。
不同类型角色有不同的作息偏好。
"""


# 预设作息模板
SCHEDULE_TEMPLATES = {
    "default": {
        "wake_up": 7,
        "sleep": 23,
        "meal_times": [8, 12, 18],
        "work_hours": [9, 17],
        "free_hours": [17, 23],
    },
    "student": {
        "wake_up": 7,
        "sleep": 24,
        "meal_times": [8, 12, 18],
        "work_hours": [8, 17],
        "free_hours": [17, 24],
    },
    "night_owl": {
        "wake_up": 10,
        "sleep": 2,
        "meal_times": [10, 14, 20],
        "work_hours": [14, 23],
        "free_hours": [23, 26],  # 跨天
    },
    "early_bird": {
        "wake_up": 5,
        "sleep": 21,
        "meal_times": [6, 12, 17],
        "work_hours": [6, 15],
        "free_hours": [15, 21],
    },
    "artist": {
        "wake_up": 9,
        "sleep": 1,
        "meal_times": [9, 13, 20],
        "work_hours": [10, 18],
        "free_hours": [18, 25],
    },
}

# 活动 → 自然语言描述
ACTIVITY_DESCRIPTIONS = {
    "sleeping":     "在睡觉",
    "waking_up":    "刚起床，有点迷糊",
    "breakfast":    "在吃早餐",
    "working":      "在工作",
    "studying":     "在学习",
    "drawing":      "在画画",
    "cooking":      "在做饭",
    "watching_movie": "在看电影",
    "taking_bath":  "在泡澡",
    "thinking":     "在想事情",
    "missing_user": "在想你",
    "writing_diary": "在写日记",
    "reading":      "在看书",
    "shopping":     "在逛街",
    "exercising":   "在运动",
    "idle":         "在发呆",
}


class DailySchedule:
    """作息系统 — 管理角色的日常作息。"""

    def __init__(self, character_id: str = None, template: str = "default"):
        self.character_id = character_id
        self.template_name = template
        self.schedule = dict(SCHEDULE_TEMPLATES.get(template, SCHEDULE_TEMPLATES["default"]))

    def get_period(self, hour: int) -> str:
        """根据当前小时判断时间段。"""
        if self.schedule["sleep"] <= hour or hour < self.schedule["wake_up"]:
            return "late_night"
        elif hour < self.schedule["wake_up"] + 1:
            return "morning"
        elif hour < 12:
            return "morning"
        elif hour < 18:
            return "afternoon"
        elif hour < self.schedule["sleep"] - 1:
            return "evening"
        return "night"

    def is_sleeping(self, hour: int) -> bool:
        """判断当前是否在睡觉时间。"""
        if self.schedule["sleep"] <= 24 and self.schedule["wake_up"] >= 0:
            # 正常作息
            return hour >= self.schedule["sleep"] or hour < self.schedule["wake_up"]
        return hour >= self.schedule["sleep"] or hour < self.schedule["wake_up"]

    def is_meal_time(self, hour: int) -> bool:
        return hour in self.schedule["meal_times"]

    def is_work_time(self, hour: int) -> bool:
        return self.schedule["work_hours"][0] <= hour < self.schedule["work_hours"][1]

    def get_description(self, activity: str) -> str:
        """获取活动的自然语言描述。"""
        return ACTIVITY_DESCRIPTIONS.get(activity, "在做自己的事")

    def get_status(self) -> dict:
        return {
            "character_id": self.character_id,
            "template": self.template_name,
            "wake_up": self.schedule["wake_up"],
            "sleep": self.schedule["sleep"],
            "meal_times": self.schedule["meal_times"],
        }
