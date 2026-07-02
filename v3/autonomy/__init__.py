"""
自主行为模块 (Phase 2)

负责角色自主行为决策、因子收集、行为策略、调度和反馈闭环。
"""

from .autonomy_engine import AutonomyEngine
from .decision_factors import DecisionFactors
from .action_policy import ActionPolicy
from .action_dispatcher import ActionDispatcher

try:
    from .feedback_loop import FeedbackLoop
except ImportError:
    FeedbackLoop = None

__all__ = [
    "AutonomyEngine",
    "DecisionFactors",
    "ActionPolicy",
    "ActionDispatcher",
    "FeedbackLoop",
]
