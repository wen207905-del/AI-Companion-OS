"""
LLM 抽象基类
定义统一的 chat 接口，所有 LLM 实现继承此类。
"""

from abc import ABC, abstractmethod
from typing import Optional


class LLMBase(ABC):
    """
    LLM 抽象基类

    所有 LLM 实现必须实现 chat 方法，支持标准的 messages 格式。
    """

    @abstractmethod
    def chat(self, messages: list[dict], **kwargs) -> str:
        """
        发送对话请求

        Args:
            messages: OpenAI 格式的消息列表 [{"role": "system/user/assistant", "content": "..."}]
            **kwargs: 额外参数（temperature, max_tokens 等）

        Returns:
            模型回复文本
        """
        ...

    @abstractmethod
    def set_temperature(self, temperature: float):
        """设置采样温度"""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """检查 LLM 是否可用"""
        ...
