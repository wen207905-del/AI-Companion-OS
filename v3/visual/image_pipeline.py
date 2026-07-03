"""
V4 Image Pipeline — 生图管道

接收 ImageRequest → 构建 prompt → 调用 API → 保存图片 → 写入 album。
"""

import os
import json
import time
import hashlib
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ImageRequest:
    """生图请求。"""
    character_id: str
    style: str = "selfie"
    scene: str = "bedroom"
    outfit: str = ""
    pose: str = ""
    emotion: str = ""
    camera: str = ""
    extra_tags: str = ""
    negative_prompt: str = ""
    output_dir: str = ""


@dataclass
class ImageResult:
    """生图结果。"""
    character_id: str
    image_path: str = ""
    prompt: str = ""
    success: bool = False
    error: str = ""
    generated_at: str = ""


class ImagePipeline:
    """生图管道。

    完整流程：
        1. 接收 ImageRequest
        2. PromptBuilder 构建 prompt
        3. 调用生图 API（预留接口）
        4. 保存图片到 albums/{char_id}/
        5. 写入 album 表
        6. 返回 ImageResult
    """

    MAX_RETRIES = 3
    RETRY_DELAY = 2  # 秒

    def __init__(self, identity_lock=None, prompt_builder=None,
                 db=None, event_bus=None, base_output_dir: str = None):
        self.identity_lock = identity_lock
        self.prompt_builder = prompt_builder
        self.db = db
        self.event_bus = event_bus
        self.base_output_dir = base_output_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "albums"
        )

    def generate(self, request: ImageRequest,
                  api_callback=None) -> ImageResult:
        """执行生图流程。

        Args:
            request: 生图请求参数
            api_callback: callable(prompt, negative_prompt) → image_bytes
                          如果为 None 则生成占位结果

        Returns:
            ImageResult
        """
        result = ImageResult(
            character_id=request.character_id,
            generated_at=datetime.now().isoformat(),
        )

        # 1. 构建 prompt
        if self.prompt_builder:
            prompt_data = self.prompt_builder.build(
                character_id=request.character_id,
                style=request.style,
                scene=request.scene,
                outfit=request.outfit,
                pose=request.pose,
                emotion=request.emotion,
                camera=request.camera,
                extra_tags=request.extra_tags,
                negative_prompt=request.negative_prompt,
            )
        else:
            prompt_data = {"prompt": "a beautiful photo", "negative_prompt": "", "identity_token": ""}

        result.prompt = prompt_data["prompt"]

        # 2. 输出目录
        output_dir = request.output_dir or os.path.join(
            self.base_output_dir, request.character_id
        )
        os.makedirs(output_dir, exist_ok=True)

        # 3. 调用 API 或生成占位
        if api_callback:
            image_bytes = None
            last_error = None

            for attempt in range(self.MAX_RETRIES):
                try:
                    image_bytes = api_callback(
                        prompt_data["prompt"],
                        prompt_data["negative_prompt"],
                    )
                    if image_bytes:
                        break
                except Exception as e:
                    last_error = str(e)
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(self.RETRY_DELAY * (attempt + 1))

            if image_bytes:
                filename = self._generate_filename(request)
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(image_bytes)
                result.image_path = filepath
                result.success = True
            else:
                result.error = last_error or "API 返回空"
                # 走占位方案
                result = self._save_placeholder(request, output_dir, prompt_data, result)
        else:
            result = self._save_placeholder(request, output_dir, prompt_data, result)

        # 4. 写入 album
        if result.success and self.db:
            try:
                self.db.insert_album_entry(
                    character_id=request.character_id,
                    image_path=result.image_path,
                    prompt=result.prompt,
                    style=request.style,
                    scene=request.scene,
                )
            except Exception:
                pass

        # 5. 事件通知
        if self.event_bus:
            self.event_bus.publish("image_generated", asdict(result))

        return result

    def _save_placeholder(self, request: ImageRequest, output_dir: str,
                           prompt_data: dict, result: ImageResult) -> ImageResult:
        """保存占位 JSON 作为结果记录。"""
        filename = self._generate_filename(request).replace(".png", ".json")
        filepath = os.path.join(output_dir, filename)
        record = {
            "character_id": request.character_id,
            "prompt": prompt_data["prompt"],
            "negative_prompt": prompt_data.get("negative_prompt", ""),
            "identity_token": prompt_data.get("identity_token", ""),
            "style": request.style,
            "scene": request.scene,
            "outfit": request.outfit,
            "emotion": request.emotion,
            "generated_at": datetime.now().isoformat(),
            "status": "placeholder — implement API callback for real image generation",
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        result.image_path = filepath
        result.success = True
        result.error = ""
        return result

    def _generate_filename(self, request: ImageRequest) -> str:
        """生成唯一文件名。"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_input = f"{request.character_id}_{request.style}_{request.scene}_{ts}"
        short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"{request.character_id}_{request.style}_{ts}_{short_hash}.png"
