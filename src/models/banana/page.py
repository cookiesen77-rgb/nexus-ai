"""
PPT 页面模型
"""

import uuid
from datetime import datetime
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field


@dataclass
class PPTPage:
    """PPT 页面"""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    order_index: int = 0
    
    # 大纲
    outline_content: Dict = field(default_factory=lambda: {"title": "", "points": []})
    
    # 描述
    description_content: Optional[str] = None
    
    # 图片
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    
    # 状态
    status: str = "draft"  # draft, generating, completed, failed
    
    # 章节信息
    part: Optional[str] = None
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def title(self) -> str:
        """获取标题"""
        if isinstance(self.outline_content, dict):
            return self.outline_content.get("title", "")
        return ""
    
    @property
    def points(self) -> List[str]:
        """获取要点"""
        if isinstance(self.outline_content, dict):
            return self.outline_content.get("points", [])
        return []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "order_index": self.order_index,
            "outline_content": self.outline_content,
            "description_content": self.description_content,
            "image_url": self.image_url,
            "image_base64": self.image_base64,
            "status": self.status,
            "part": self.part,
            "title": self.title,
            "points": self.points,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PPTPage":
        """从字典创建"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            project_id=data.get("project_id", ""),
            order_index=data.get("order_index", 0),
            outline_content=data.get("outline_content", {"title": "", "points": []}),
            description_content=data.get("description_content"),
            image_url=data.get("image_url"),
            image_base64=data.get("image_base64"),
            status=data.get("status", "draft"),
            part=data.get("part"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now()
        )
    
    @classmethod
    def from_outline(cls, outline: Dict, project_id: str, index: int) -> "PPTPage":
        """从大纲创建页面"""
        return cls(
            project_id=project_id,
            order_index=index,
            outline_content={
                "title": outline.get("title", ""),
                "points": outline.get("points", [])
            },
            part=outline.get("part")
        )

