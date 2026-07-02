"""
相册管理（骨架）

负责角色照片的分类存储、检索和照片记忆绑定。
"""

from ..config import ALBUM_CATEGORIES


class AlbumManager:
    """相册管理器 — 管理角色的所有生成照片。

    职责：
    - 按分类存储照片
    - 将照片与事件/记忆绑定
    - 支持按时间/分类/情绪检索照片
    - 为未来对话引用照片提供检索接口

    TODO Phase 3: 完整实现照片存储和检索
    """

    def __init__(self, db):
        """
        Args:
            db: V3Database 实例
        """
        self.db = db
        self.categories = ALBUM_CATEGORIES

    def add_photo(self, character_id: str, file_path: str,
                  category: str = "generated_archive",
                  caption: str = "", scene_type: str = "",
                  emotion_tag: str = "", event_id: str = "") -> int:
        """向相册添加一张照片。

        Args:
            character_id: 角色 ID
            file_path: 照片文件路径
            category: 相册分类
            caption: 照片说明
            scene_type: 场景类型
            emotion_tag: 情绪标签
            event_id: 关联事件 ID

        Returns:
            照片记录 ID

        TODO Phase 3: 完整实现数据库写入
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO image_assets
                (character_id, file_path, album_category, caption, scene_type, emotion_tag, event_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (character_id, file_path, category, caption, scene_type, emotion_tag, event_id))
        self.db.conn.commit()
        return cursor.lastrowid

    def get_photos_by_category(self, character_id: str, category: str,
                                limit: int = 20) -> list:
        """按分类获取角色的照片列表。

        Args:
            character_id: 角色 ID
            category: 相册分类
            limit: 返回数量上限

        Returns:
            照片记录列表

        TODO Phase 3: 实现
        """
        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT * FROM image_assets WHERE character_id = ? AND album_category = ? ORDER BY created_at DESC LIMIT ?",
            (character_id, category, limit)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_photos_by_event(self, event_id: str) -> list:
        """根据事件 ID 获取关联照片。

        Args:
            event_id: 事件 ID

        Returns:
            照片记录列表

        TODO Phase 3: 实现
        """
        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT * FROM image_assets WHERE event_id = ? ORDER BY created_at DESC",
            (event_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_recent_photos(self, character_id: str, limit: int = 10) -> list:
        """获取角色最近的照片。

        Args:
            character_id: 角色 ID
            limit: 返回数量上限

        Returns:
            照片记录列表
        """
        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT * FROM image_assets WHERE character_id = ? ORDER BY created_at DESC LIMIT ?",
            (character_id, limit)
        )
        return [dict(row) for row in cursor.fetchall()]
