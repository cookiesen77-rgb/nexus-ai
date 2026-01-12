"""
记忆系统数据类型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class MemoryType(Enum):
    """记忆类型"""
    SHORT_TERM = "short_term"      # 短期记忆 (当前会话)
    LONG_TERM = "long_term"        # 长期记忆 (跨会话)
    EPISODIC = "episodic"          # 情景记忆 (具体事件)
    SEMANTIC = "semantic"          # 语义记忆 (知识/事实)
    PROCEDURAL = "procedural"      # 程序记忆 (技能/流程)


class MemoryPriority(Enum):
    """记忆优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Memory:
    """记忆条目"""
    id: str
    content: str
    memory_type: MemoryType = MemoryType.SHORT_TERM
    priority: MemoryPriority = MemoryPriority.NORMAL
    
    # 时间信息
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    # 关联
    session_id: Optional[str] = None
    related_ids: List[str] = field(default_factory=list)
    
    # 向量嵌入 (用于检索)
    embedding: Optional[List[float]] = None
    
    # 统计
    access_count: int = 0
    relevance_score: float = 0.0
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def touch(self):
        """更新访问时间"""
        self.accessed_at = datetime.now()
        self.access_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "content": self.content,
            "type": self.memory_type.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata,
            "tags": self.tags,
            "session_id": self.session_id,
            "access_count": self.access_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Memory":
        """从字典创建"""
        return cls(
            id=data["id"],
            content=data["content"],
            memory_type=MemoryType(data.get("type", "short_term")),
            priority=MemoryPriority(data.get("priority", 2)),
            created_at=datetime.fromisoformat(data["created_at"]),
            accessed_at=datetime.fromisoformat(data["accessed_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            session_id=data.get("session_id"),
            access_count=data.get("access_count", 0),
        )


@dataclass
class MemoryQuery:
    """记忆查询"""
    query: str
    memory_types: List[MemoryType] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    session_id: Optional[str] = None
    limit: int = 10
    threshold: float = 0.5
    include_expired: bool = False


@dataclass
class MemorySearchResult:
    """记忆搜索结果"""
    memory: Memory
    score: float
    match_type: str = "semantic"  # semantic, keyword, tag


@dataclass
class SessionSummary:
    """会话摘要"""
    session_id: str
    summary: str
    key_points: List[str]
    entities: List[str]
    created_at: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    duration_seconds: float = 0.0

