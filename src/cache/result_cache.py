"""
结果缓存 - LLM响应缓存
"""

import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict
from pathlib import Path


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    def touch(self):
        """更新访问信息"""
        self.last_accessed = time.time()
        self.access_count += 1


@dataclass
class CacheStats:
    """缓存统计"""
    hits: int = 0
    misses: int = 0
    size: int = 0
    max_size: int = 0
    evictions: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class LRUCache:
    """
    LRU缓存实现
    
    最近最少使用的条目会被淘汰
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        max_memory_mb: int = 100,
        default_ttl: int = 3600
    ):
        """
        初始化LRU缓存
        
        Args:
            max_size: 最大条目数
            max_memory_mb: 最大内存(MB)
            default_ttl: 默认TTL(秒)
        """
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl
        
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._current_memory = 0
        self._stats = CacheStats(max_size=max_size)
    
    def _generate_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]
    
    def _estimate_size(self, value: Any) -> int:
        """估算值的大小"""
        try:
            return len(json.dumps(value).encode())
        except:
            return len(str(value).encode())
    
    def get(self, key: str) -> Tuple[bool, Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            Tuple[bool, Any]: (是否命中, 值)
        """
        entry = self._cache.get(key)
        
        if entry is None:
            self._stats.misses += 1
            return False, None
        
        if entry.is_expired():
            self._remove(key)
            self._stats.misses += 1
            return False, None
        
        # 移到最后 (最近访问)
        self._cache.move_to_end(key)
        entry.touch()
        
        self._stats.hits += 1
        return True, entry.value
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: int = None,
        metadata: Dict[str, Any] = None
    ):
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: TTL(秒)
            metadata: 元数据
        """
        size = self._estimate_size(value)
        
        # 检查单个值是否超过限制
        if size > self.max_memory_bytes:
            return
        
        # 淘汰直到有空间
        while (
            len(self._cache) >= self.max_size or
            self._current_memory + size > self.max_memory_bytes
        ):
            if not self._evict():
                break
        
        # 计算过期时间
        expires_at = None
        if ttl is not None:
            expires_at = time.time() + ttl
        elif self.default_ttl:
            expires_at = time.time() + self.default_ttl
        
        entry = CacheEntry(
            key=key,
            value=value,
            expires_at=expires_at,
            size_bytes=size,
            metadata=metadata or {}
        )
        
        # 如果已存在，先移除旧的
        if key in self._cache:
            self._remove(key)
        
        self._cache[key] = entry
        self._current_memory += size
        self._stats.size = len(self._cache)
    
    def _remove(self, key: str):
        """移除条目"""
        entry = self._cache.pop(key, None)
        if entry:
            self._current_memory -= entry.size_bytes
            self._stats.size = len(self._cache)
    
    def _evict(self) -> bool:
        """淘汰最旧的条目"""
        if not self._cache:
            return False
        
        # 先尝试淘汰过期的
        for key, entry in list(self._cache.items()):
            if entry.is_expired():
                self._remove(key)
                self._stats.evictions += 1
                return True
        
        # 淘汰最旧的 (OrderedDict的第一个)
        key = next(iter(self._cache))
        self._remove(key)
        self._stats.evictions += 1
        return True
    
    def delete(self, key: str) -> bool:
        """删除条目"""
        if key in self._cache:
            self._remove(key)
            return True
        return False
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._current_memory = 0
        self._stats.size = 0
    
    def get_stats(self) -> CacheStats:
        """获取统计"""
        return self._stats


class LLMResponseCache:
    """
    LLM响应缓存
    
    专门用于缓存LLM API响应
    """
    
    def __init__(
        self,
        cache: LRUCache = None,
        enabled: bool = True,
        cache_similar: bool = True
    ):
        """
        初始化LLM响应缓存
        
        Args:
            cache: 底层缓存
            enabled: 是否启用
            cache_similar: 是否缓存相似请求
        """
        self._cache = cache or LRUCache()
        self.enabled = enabled
        self.cache_similar = cache_similar
    
    def _make_key(
        self,
        model: str,
        messages: List[Dict],
        temperature: float = None,
        **kwargs
    ) -> str:
        """生成缓存键"""
        # 只有temperature=0时才缓存确定性响应
        if temperature is not None and temperature > 0 and not self.cache_similar:
            return None
        
        key_parts = {
            "model": model,
            "messages": messages,
            "temperature": temperature or 0
        }
        
        key_str = json.dumps(key_parts, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:24]
    
    def get(
        self,
        model: str,
        messages: List[Dict],
        **kwargs
    ) -> Tuple[bool, Any]:
        """
        获取缓存的响应
        
        Args:
            model: 模型名
            messages: 消息列表
            
        Returns:
            Tuple[bool, Any]: (是否命中, 响应)
        """
        if not self.enabled:
            return False, None
        
        key = self._make_key(model, messages, **kwargs)
        if key is None:
            return False, None
        
        return self._cache.get(key)
    
    def set(
        self,
        model: str,
        messages: List[Dict],
        response: Any,
        ttl: int = None,
        **kwargs
    ):
        """
        缓存响应
        
        Args:
            model: 模型名
            messages: 消息列表
            response: 响应
            ttl: TTL
        """
        if not self.enabled:
            return
        
        key = self._make_key(model, messages, **kwargs)
        if key is None:
            return
        
        self._cache.set(
            key=key,
            value=response,
            ttl=ttl,
            metadata={"model": model, "message_count": len(messages)}
        )
    
    def invalidate(self, model: str = None):
        """使缓存失效"""
        if model is None:
            self._cache.clear()
        # TODO: 支持按模型清除
    
    def get_stats(self) -> CacheStats:
        """获取统计"""
        return self._cache.get_stats()


# 全局缓存实例
_default_cache: Optional[LLMResponseCache] = None


def get_response_cache() -> LLMResponseCache:
    """获取全局响应缓存"""
    global _default_cache
    if _default_cache is None:
        _default_cache = LLMResponseCache()
    return _default_cache

