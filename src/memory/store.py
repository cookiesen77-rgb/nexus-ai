"""
记忆存储 - 持久化对话记忆
"""

import json
import uuid
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from .types import (
    Memory, MemoryType, MemoryPriority,
    MemoryQuery, MemorySearchResult, SessionSummary
)


class MemoryStore:
    """
    记忆存储
    
    支持短期/长期记忆的存储和检索
    """
    
    def __init__(
        self,
        storage_path: str = "data/memory",
        max_short_term: int = 100,
        max_long_term: int = 1000
    ):
        """
        初始化记忆存储
        
        Args:
            storage_path: 存储路径
            max_short_term: 最大短期记忆数
            max_long_term: 最大长期记忆数
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.max_short_term = max_short_term
        self.max_long_term = max_long_term
        
        # 内存索引
        self._memories: Dict[str, Memory] = {}
        self._by_session: Dict[str, List[str]] = defaultdict(list)
        self._by_type: Dict[MemoryType, List[str]] = defaultdict(list)
        self._by_tag: Dict[str, List[str]] = defaultdict(list)
        
        # 加载持久化数据
        self._load()
    
    def _load(self):
        """加载持久化数据"""
        memory_file = self.storage_path / "memories.json"
        if memory_file.exists():
            try:
                with open(memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for item in data:
                    memory = Memory.from_dict(item)
                    self._index_memory(memory)
            except Exception as e:
                print(f"Warning: Failed to load memories: {e}")
    
    def _save(self):
        """保存到文件"""
        memory_file = self.storage_path / "memories.json"
        data = [m.to_dict() for m in self._memories.values()]
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _index_memory(self, memory: Memory):
        """索引记忆"""
        self._memories[memory.id] = memory
        
        if memory.session_id:
            self._by_session[memory.session_id].append(memory.id)
        
        self._by_type[memory.memory_type].append(memory.id)
        
        for tag in memory.tags:
            self._by_tag[tag].append(memory.id)
    
    def _remove_from_index(self, memory_id: str):
        """从索引移除"""
        memory = self._memories.get(memory_id)
        if not memory:
            return
        
        if memory.session_id and memory_id in self._by_session[memory.session_id]:
            self._by_session[memory.session_id].remove(memory_id)
        
        if memory_id in self._by_type[memory.memory_type]:
            self._by_type[memory.memory_type].remove(memory_id)
        
        for tag in memory.tags:
            if memory_id in self._by_tag[tag]:
                self._by_tag[tag].remove(memory_id)
        
        del self._memories[memory_id]
    
    async def store(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        priority: MemoryPriority = MemoryPriority.NORMAL,
        metadata: Dict[str, Any] = None,
        tags: List[str] = None,
        session_id: str = None,
        ttl_seconds: int = None
    ) -> str:
        """
        存储记忆
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型
            priority: 优先级
            metadata: 元数据
            tags: 标签
            session_id: 会话ID
            ttl_seconds: 过期时间(秒)
            
        Returns:
            str: 记忆ID
        """
        memory_id = str(uuid.uuid4())
        
        expires_at = None
        if ttl_seconds:
            expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        
        memory = Memory(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            priority=priority,
            metadata=metadata or {},
            tags=tags or [],
            session_id=session_id,
            expires_at=expires_at
        )
        
        self._index_memory(memory)
        
        # 清理旧记忆
        await self._cleanup()
        
        # 保存
        self._save()
        
        return memory_id
    
    async def retrieve(
        self,
        memory_id: str
    ) -> Optional[Memory]:
        """
        检索单个记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            Memory: 记忆对象
        """
        memory = self._memories.get(memory_id)
        if memory and not memory.is_expired():
            memory.touch()
            return memory
        return None
    
    async def search(
        self,
        query: MemoryQuery
    ) -> List[MemorySearchResult]:
        """
        搜索记忆
        
        Args:
            query: 查询条件
            
        Returns:
            List[MemorySearchResult]: 搜索结果
        """
        results = []
        
        # 确定候选集
        candidates = set(self._memories.keys())
        
        # 按类型过滤
        if query.memory_types:
            type_ids = set()
            for mt in query.memory_types:
                type_ids.update(self._by_type.get(mt, []))
            candidates &= type_ids
        
        # 按会话过滤
        if query.session_id:
            session_ids = set(self._by_session.get(query.session_id, []))
            candidates &= session_ids
        
        # 按标签过滤
        if query.tags:
            tag_ids = set()
            for tag in query.tags:
                tag_ids.update(self._by_tag.get(tag, []))
            candidates &= tag_ids
        
        # 评分和排序
        for memory_id in candidates:
            memory = self._memories.get(memory_id)
            if not memory:
                continue
            
            if memory.is_expired() and not query.include_expired:
                continue
            
            # 计算相关性分数
            score = self._calculate_relevance(memory, query.query)
            
            if score >= query.threshold:
                results.append(MemorySearchResult(
                    memory=memory,
                    score=score,
                    match_type="keyword"
                ))
        
        # 排序
        results.sort(key=lambda x: x.score, reverse=True)
        
        # 限制数量
        return results[:query.limit]
    
    def _calculate_relevance(self, memory: Memory, query: str) -> float:
        """计算相关性分数"""
        if not query:
            return 0.5  # 默认分数
        
        query_lower = query.lower()
        content_lower = memory.content.lower()
        
        # 关键词匹配
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        
        if not query_words:
            return 0.0
        
        common = query_words & content_words
        keyword_score = len(common) / len(query_words)
        
        # 优先级加成
        priority_bonus = memory.priority.value * 0.1
        
        # 访问频率加成
        access_bonus = min(memory.access_count * 0.05, 0.2)
        
        return min(keyword_score + priority_bonus + access_bonus, 1.0)
    
    async def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        if memory_id in self._memories:
            self._remove_from_index(memory_id)
            self._save()
            return True
        return False
    
    async def _cleanup(self):
        """清理过期和超量记忆"""
        # 清理过期记忆
        expired = [
            mid for mid, m in self._memories.items()
            if m.is_expired()
        ]
        for mid in expired:
            self._remove_from_index(mid)
        
        # 清理超量短期记忆
        short_term = self._by_type.get(MemoryType.SHORT_TERM, [])
        if len(short_term) > self.max_short_term:
            # 按访问时间排序，删除最旧的
            to_remove = sorted(
                short_term,
                key=lambda x: self._memories[x].accessed_at
            )[:len(short_term) - self.max_short_term]
            
            for mid in to_remove:
                self._remove_from_index(mid)
    
    async def get_session_memories(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Memory]:
        """获取会话记忆"""
        memory_ids = self._by_session.get(session_id, [])
        memories = [
            self._memories[mid] 
            for mid in memory_ids 
            if mid in self._memories and not self._memories[mid].is_expired()
        ]
        
        # 按时间排序
        memories.sort(key=lambda x: x.created_at, reverse=True)
        
        return memories[:limit]
    
    async def summarize_session(
        self,
        session_id: str,
        llm=None
    ) -> SessionSummary:
        """
        总结会话
        
        Args:
            session_id: 会话ID
            llm: LLM客户端 (可选)
        """
        memories = await self.get_session_memories(session_id)
        
        if not memories:
            return SessionSummary(
                session_id=session_id,
                summary="No memories found for this session.",
                key_points=[],
                entities=[]
            )
        
        # 提取关键点
        key_points = []
        entities = set()
        
        for m in memories[:20]:  # 最多处理20条
            # 简单提取
            lines = m.content.split('\n')
            for line in lines[:2]:
                if line.strip() and len(line) < 200:
                    key_points.append(line.strip())
            
            # 提取实体 (简单的大写单词)
            import re
            words = re.findall(r'\b[A-Z][a-z]+\b', m.content)
            entities.update(words[:5])
        
        # 生成摘要
        summary = "; ".join(key_points[:5]) if key_points else "Session with various interactions."
        
        return SessionSummary(
            session_id=session_id,
            summary=summary[:500],
            key_points=key_points[:10],
            entities=list(entities)[:20],
            message_count=len(memories)
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_memories": len(self._memories),
            "by_type": {
                mt.value: len(ids) 
                for mt, ids in self._by_type.items()
            },
            "sessions": len(self._by_session),
            "tags": len(self._by_tag),
        }


# 全局记忆存储实例
_default_store: Optional[MemoryStore] = None


def get_memory_store(storage_path: str = None) -> MemoryStore:
    """获取全局记忆存储"""
    global _default_store
    if _default_store is None:
        _default_store = MemoryStore(storage_path or "data/memory")
    return _default_store


async def remember(
    content: str,
    tags: List[str] = None,
    session_id: str = None
) -> str:
    """快捷函数: 存储记忆"""
    store = get_memory_store()
    return await store.store(content, tags=tags, session_id=session_id)


async def recall(
    query: str,
    limit: int = 5
) -> List[Memory]:
    """快捷函数: 检索记忆"""
    store = get_memory_store()
    results = await store.search(MemoryQuery(query=query, limit=limit))
    return [r.memory for r in results]

