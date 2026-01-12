"""
PPT 项目模型
"""

import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field


@dataclass
class PPTProject:
    """PPT 项目"""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "演示文稿"
    
    # 创建信息
    creation_type: str = "idea"  # idea, outline, description
    idea_prompt: Optional[str] = None
    outline_text: Optional[str] = None
    description_text: Optional[str] = None
    
    # 模板信息
    template_style: Optional[str] = None
    template_image_url: Optional[str] = None
    
    # 状态
    status: str = "draft"  # draft, generating, completed, failed
    
    # 页面（存储为 JSON）
    pages: List[Dict] = field(default_factory=list)
    outline: List[Dict] = field(default_factory=list)
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "project_id": self.id,  # 兼容
            "name": self.name,
            "creation_type": self.creation_type,
            "idea_prompt": self.idea_prompt,
            "outline_text": self.outline_text,
            "description_text": self.description_text,
            "template_style": self.template_style,
            "template_image_url": self.template_image_url,
            "status": self.status,
            "pages": self.pages,
            "outline": self.outline,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PPTProject":
        """从字典创建"""
        return cls(
            id=data.get("id") or data.get("project_id") or str(uuid.uuid4()),
            name=data.get("name", "演示文稿"),
            creation_type=data.get("creation_type", "idea"),
            idea_prompt=data.get("idea_prompt"),
            outline_text=data.get("outline_text"),
            description_text=data.get("description_text"),
            template_style=data.get("template_style"),
            template_image_url=data.get("template_image_url"),
            status=data.get("status", "draft"),
            pages=data.get("pages", []),
            outline=data.get("outline", []),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now()
        )
    
    def update(self, **kwargs):
        """更新属性"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()
    
    def add_page(self, page_data: Dict) -> Dict:
        """添加页面"""
        if "id" not in page_data:
            page_data["id"] = str(uuid.uuid4())
        page_data["order_index"] = len(self.pages)
        self.pages.append(page_data)
        self.updated_at = datetime.now()
        return page_data
    
    def update_page(self, page_id: str, page_data: Dict) -> Optional[Dict]:
        """更新页面"""
        for i, page in enumerate(self.pages):
            if page.get("id") == page_id:
                self.pages[i].update(page_data)
                self.updated_at = datetime.now()
                return self.pages[i]
        return None
    
    def delete_page(self, page_id: str) -> bool:
        """删除页面"""
        for i, page in enumerate(self.pages):
            if page.get("id") == page_id:
                self.pages.pop(i)
                # 重新排序
                for j, p in enumerate(self.pages):
                    p["order_index"] = j
                self.updated_at = datetime.now()
                return True
        return False
    
    def get_page(self, page_id: str) -> Optional[Dict]:
        """获取页面"""
        for page in self.pages:
            if page.get("id") == page_id:
                return page
        return None


# 内存存储（简化实现，实际可使用数据库）
_projects: Dict[str, PPTProject] = {}


def save_project(project: PPTProject) -> PPTProject:
    """保存项目"""
    _projects[project.id] = project
    return project


def get_project(project_id: str) -> Optional[PPTProject]:
    """获取项目"""
    return _projects.get(project_id)


def delete_project(project_id: str) -> bool:
    """删除项目"""
    if project_id in _projects:
        del _projects[project_id]
        return True
    return False


def list_projects(limit: int = 50, offset: int = 0) -> List[PPTProject]:
    """列出项目"""
    projects = sorted(
        _projects.values(),
        key=lambda p: p.updated_at,
        reverse=True
    )
    return projects[offset:offset + limit]

