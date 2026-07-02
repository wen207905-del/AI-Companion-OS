"""
LLM 路由器
支持主模型 + fallback 模型切换，失败自动降级。
"""

from typing import Optional

from .base import LLMBase
from .deepseek import DeepSeekChat


class LLMRouter:
    """
    LLM 路由器

    职责：
    1. 管理主模型和备用模型
    2. 失败时自动 fallback 到备用模型
    3. 记录失败次数和熔断逻辑
    """

    def __init__(self):
        # 主模型：DeepSeek
        self.primary: LLMBase = DeepSeekChat()

        # Fallback 模型：也是 DeepSeek（可以用不同模型名）
        self.fallback: Optional[LLMBase] = None

        # 故障计数
        self.primary_fail_count: int = 0
        self.max_primary_fails: int = 3

        # 熔断状态
        self.primary_circuit_open: bool = False
        self.circuit_cooldown_seconds: int = 60

    def set_fallback(self, llm: LLMBase):
        """设置备用 LLM"""
        self.fallback = llm

    def chat(self, messages: list[dict], **kwargs) -> str:
        """
        路由对话请求

        优先使用主模型，失败时自动切换到 fallback

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            模型回复
        """
        # 如果主模型熔断，直接用 fallback
        if self.primary_circuit_open and self.fallback:
            result = self._try_chat(self.fallback, messages, kwargs)
            if not result.startswith("[错误]"):
                return result
            return "[错误] 所有 LLM 均不可用"

        # 主模型正常
        result = self._try_chat(self.primary, messages, kwargs)
        if not result.startswith("[错误]"):
            self.primary_fail_count = 0
            return result

        # 主模型失败
        self.primary_fail_count += 1

        # 连续失败 N 次，熔断
        if self.primary_fail_count >= self.max_primary_fails:
            self.primary_circuit_open = True

        # 尝试 fallback
        if self.fallback:
            fallback_result = self._try_chat(self.fallback, messages, kwargs)
            if not fallback_result.startswith("[错误]"):
                return fallback_result
            return f"[Fallback 也失败了] 主模型错误: {result} | Fallback错误: {fallback_result}"

        return result

    def _try_chat(self, llm: LLMBase, messages: list[dict], kwargs: dict) -> str:
        """安全调用 chat，捕获异常"""
        try:
            return llm.chat(messages, **kwargs)
        except Exception as e:
            return f"[错误] LLM 调用异常: {str(e)}"

    def reset_circuit(self):
        """重置熔断状态"""
        self.primary_circuit_open = False
        self.primary_fail_count = 0

    @property
    def is_available(self) -> bool:
        """检查是否有任何可用模型"""
        return self.primary.is_available or (self.fallback is not None and self.fallback.is_available)
