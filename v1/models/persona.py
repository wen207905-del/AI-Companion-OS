"""
角色数据模型 (Pydantic v2)
对应 config/personas/*.yaml 的完整结构
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
import yaml


class Measurements(BaseModel):
    """三围数据"""
    bust_cm: int = Field(ge=60, le=130, description="胸围(cm)")
    waist_cm: int = Field(ge=40, le=100, description="腰围(cm)")
    hip_cm: int = Field(ge=50, le=120, description="臀围(cm)")
    cup: str = Field(description="罩杯")


class BaseInfo(BaseModel):
    """角色基础信息"""
    age: int
    birthday: str
    zodiac: str
    height_cm: int
    weight_kg: int
    measurements: Measurements
    blood_type: str
    occupation: str
    education: str
    birth_place: str
    residence: str


class Appearance(BaseModel):
    """外貌详细描述"""
    face: str
    hair: str
    eyes: str
    nose: str
    lips: str
    skin: str
    body: str
    style: str
    accessories: str = ""
    makeup: str = ""
    overall: str = ""


class Personality(BaseModel):
    """性格深度描写"""
    core: str
    yandere: Optional[Any] = None
    normal: Optional[Any] = None
    genki: Optional[Any] = None
    chuuni: Optional[Any] = None
    sweetness: Optional[Any] = None
    clingy_levels: Optional[Any] = None
    devil_mode: Optional[Any] = None
    real_mode: Optional[Any] = None
    emotional_expression: str
    strengths: list[str]
    weaknesses: list[str]
    hidden: Any = None
    with_you: Optional[Any] = None
    attachment: Optional[Any] = None
    healing: Optional[Any] = None


class SpeechStyle(BaseModel):
    """说话风格"""
    speed: str
    vocabulary: str
    catchphrases: list[str]
    address: Any = None
    emotional_habits: list[str]


class LoveView(BaseModel):
    """恋爱观"""
    core: Optional[str] = None
    philosophy: str = ""
    expression: Optional[str] = None
    intimacy: Optional[str] = None
    reality: Optional[str] = None
    ideal: Optional[str] = None
    romance: Optional[str] = None
    transformation: Optional[str] = None
    aspiration: Optional[str] = None
    giving: Optional[str] = None


class Values(BaseModel):
    """价值观"""
    core: Optional[str] = None
    creed: Optional[str] = None
    details: Optional[str] = None
    business: Optional[str] = None
    money: Optional[str] = None
    career: Optional[str] = None
    family: Optional[str] = None
    creation: Optional[str] = None
    morality: str = ""
    happiness: Optional[str] = None
    philosophy: Optional[str] = None
    current: Optional[str] = None
    only: Optional[str] = None


class WorldView(BaseModel):
    """世界观"""
    nature: Optional[str] = None
    scope: Optional[str] = None
    attitude: Optional[str] = None
    philosophy: Optional[str] = None
    handling: Optional[str] = None


class Hobby(BaseModel):
    """兴趣爱好列表 - 直接用字符串列表"""
    pass


class DailyRoutine(BaseModel):
    """日常行为模式"""
    pass


class Taboos(BaseModel):
    """底线和禁忌"""
    red: list[str]
    yellow: list[str]


class Persona(BaseModel):
    """完整角色设定模型"""
    id: str = Field(description="角色唯一标识，如 ye_ruxue")
    name: str = Field(description="角色名称")
    type: str = Field(description="角色类型：御姐/老婆/傲娇/病娇/青梅竹马/女仆/二次元/女朋友/小恶魔/萝莉")
    base_info: BaseInfo
    appearance: Appearance
    personality: Personality
    speech_style: SpeechStyle
    love_view: LoveView
    values: Values
    worldview: WorldView
    hobbies: list[str]
    daily_routine: list[str]
    taboos: Taboos

    @classmethod
    def from_yaml(cls, file_path: str) -> "Persona":
        """
        从 YAML 文件加载角色设定

        Args:
            file_path: YAML 配置文件的绝对路径

        Returns:
            Persona 实例
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def get_prompt_snippet(self) -> str:
        """
        生成用于 System Prompt 的角色设定摘要

        Returns:
            格式化的角色描述文本
        """
        bi = self.base_info
        ps = self.personality

        lines = [
            f"你是{self.name}，{bi.age}岁，{bi.occupation}。",
            f"类型：{self.type}。",
            f"外貌：{self.appearance.overall or f'{bi.height_cm}cm, {bi.weight_kg}kg, {self.appearance.hair}, {self.appearance.eyes}'}",
            f"性格核心：{ps.core}",
            f"说话风格：{self.speech_style.speed}，{self.speech_style.vocabulary}",
            f"口头禅示例：{' / '.join(self.speech_style.catchphrases[:4])}",
            f"恋爱观：{self.love_view.core}",
            f"底线：{'、'.join(self.taboos.red[:3])}",
        ]
        return "\n".join(lines)
