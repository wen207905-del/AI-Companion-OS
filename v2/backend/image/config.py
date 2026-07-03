"""Image engine configuration."""

from __future__ import annotations

import os

from config import PROJECT_ROOT

SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
SILICONFLOW_BASE_URL = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
IMAGE_CONTENT_MODE = os.getenv("IMAGE_CONTENT_MODE", "unrestricted").lower()
IMAGE_OUTPUT_DIR = os.getenv(
    "IMAGE_OUTPUT_DIR",
    str(PROJECT_ROOT / "data" / "albums"),
)
IMAGE_DEFAULT_STYLE = os.getenv("IMAGE_DEFAULT_STYLE", "cinematic_portrait")
IMAGE_JOB_TIMEOUT = int(os.getenv("IMAGE_JOB_TIMEOUT", "180"))

# Quality-first model presets — 以硅基流动.cn 账号实际可用模型为准
MODEL_PORTRAIT_REF = "Qwen/Qwen-Image-Edit"       # 有参考图：img2img 锁脸
MODEL_PORTRAIT_T2I = "Qwen/Qwen-Image"            # 无参考图：高质量文生图
MODEL_MULTI = "Qwen/Qwen-Image-Edit"              # 多人/多参考
MODEL_ULTRA = "Qwen/Qwen-Image-Edit"              # 全身/特殊场景 + 参考图
MODEL_FAST = "Qwen/Qwen-Image"                    # 快速（同 T2I，步数可降）

DEFAULT_NEGATIVE = (
    "deformed face, different person, wrong hair color, extra fingers, "
    "blurry face, watermark, text, logo, low quality, bad anatomy, "
    "duplicate face, cropped head"
)
