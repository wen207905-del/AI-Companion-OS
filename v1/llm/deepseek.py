"""
DeepSeek API 实现
兼容 OpenAI 格式，通过环境变量 DEEPSEEK_API_KEY 驱动。
"""

import os
import sys
from typing import Optional

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from .base import LLMBase


def _get_api_key() -> str:
    """获取 DeepSeek API Key，优先级：参数 > 环境变量 > Windows 注册表"""
    key = os.getenv("DEEPSEEK_API_KEY", "")
    if key:
        return key

    # Windows 下从注册表读取用户环境变量
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Environment"
            ) as reg_key:
                key, _ = winreg.QueryValueEx(reg_key, "DEEPSEEK_API_KEY")
                if key:
                    os.environ["DEEPSEEK_API_KEY"] = key  # 注入当前进程
                    return key
        except Exception:
            pass

    return ""


class DeepSeekChat(LLMBase):
    """
    DeepSeek API 封装

    端点: https://api.deepseek.com/v1
    环境变量: DEEPSEEK_API_KEY
    默认模型: deepseek-chat
    """

    API_BASE = "https://api.deepseek.com/v1"
    DEFAULT_MODEL = "deepseek-chat"
    DEFAULT_TEMPERATURE = 0.9
    DEFAULT_MAX_TOKENS = 2048

    def __init__(self, api_key: str | None = None, model: str | None = None):
        """
        初始化 DeepSeek 客户端

        Args:
            api_key: API Key，为空则从环境变量 DEEPSEEK_API_KEY 读取
            model: 模型名，默认 deepseek-chat
        """
        self.api_key = api_key or _get_api_key()
        self.model = model or os.getenv("DEEPSEEK_MODEL", self.DEFAULT_MODEL)
        self.temperature = self.DEFAULT_TEMPERATURE
        self.max_tokens = self.DEFAULT_MAX_TOKENS
        self._client: Optional[OpenAI] = None

        if self.api_key and HAS_OPENAI:
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.API_BASE,
            )

    @property
    def is_available(self) -> bool:
        """检查 API 是否可用"""
        return bool(self._client and self.api_key)

    def chat(self, messages: list[dict], **kwargs) -> str:
        """
        调用 DeepSeek API 进行对话

        Args:
            messages: OpenAI 格式消息列表
            **kwargs: temperature, max_tokens, model

        Returns:
            模型回复文本
        """
        if not self.is_available:
            return "[错误] DeepSeek API 不可用。请设置 DEEPSEEK_API_KEY 环境变量并安装 openai 包。"

        try:
            response = self._client.chat.completions.create(
                model=kwargs.get("model", self.model),
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                stream=False,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[DeepSeek API 错误] {str(e)}"

    def set_temperature(self, temperature: float):
        """设置采样温度 (0.0 ~ 2.0)"""
        self.temperature = max(0.0, min(2.0, temperature))

    def set_model(self, model: str):
        """切换模型"""
        self.model = model
