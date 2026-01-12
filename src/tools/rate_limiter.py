"""
请求限流器 - 控制API调用频率
"""

import asyncio
import time
from typing import Dict, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class RateLimitConfig:
    """限流配置"""
    requests_per_second: float = 1.0
    requests_per_minute: int = 60
    burst_size: int = 5
    retry_after: float = 1.0


class TokenBucket:
    """令牌桶算法实现"""
    
    def __init__(self, rate: float, capacity: int):
        """
        Args:
            rate: 每秒添加的令牌数
            capacity: 桶容量
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        获取令牌
        
        Args:
            tokens: 需要的令牌数
            
        Returns:
            bool: 是否成功获取
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            
            # 添加新令牌
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    async def wait_for_token(self, tokens: int = 1, timeout: float = None) -> bool:
        """
        等待直到获取令牌
        
        Args:
            tokens: 需要的令牌数
            timeout: 最大等待时间
            
        Returns:
            bool: 是否成功获取
        """
        start = time.monotonic()
        
        while True:
            if await self.acquire(tokens):
                return True
            
            if timeout and (time.monotonic() - start) >= timeout:
                return False
            
            # 计算需要等待的时间
            wait_time = (tokens - self.tokens) / self.rate
            await asyncio.sleep(min(wait_time, 0.1))


class RateLimiter:
    """全局限流器"""
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self._buckets: Dict[str, TokenBucket] = {}
        self._request_counts: Dict[str, list] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    def _get_bucket(self, key: str) -> TokenBucket:
        """获取或创建令牌桶"""
        if key not in self._buckets:
            self._buckets[key] = TokenBucket(
                rate=self.config.requests_per_second,
                capacity=self.config.burst_size
            )
        return self._buckets[key]
    
    async def acquire(self, key: str = "default") -> bool:
        """
        获取请求许可
        
        Args:
            key: 限流键（如域名）
            
        Returns:
            bool: 是否允许请求
        """
        bucket = self._get_bucket(key)
        
        # 检查每分钟限制
        async with self._lock:
            now = time.time()
            # 清理过期记录
            self._request_counts[key] = [
                t for t in self._request_counts[key]
                if now - t < 60
            ]
            
            if len(self._request_counts[key]) >= self.config.requests_per_minute:
                return False
        
        # 检查令牌桶
        if await bucket.acquire():
            async with self._lock:
                self._request_counts[key].append(time.time())
            return True
        
        return False
    
    async def wait(self, key: str = "default", timeout: float = 30) -> bool:
        """
        等待直到获取许可
        
        Args:
            key: 限流键
            timeout: 最大等待时间
            
        Returns:
            bool: 是否成功获取
        """
        bucket = self._get_bucket(key)
        return await bucket.wait_for_token(timeout=timeout)
    
    def get_stats(self, key: str = "default") -> dict:
        """获取限流统计"""
        bucket = self._get_bucket(key)
        return {
            "available_tokens": bucket.tokens,
            "requests_last_minute": len(self._request_counts.get(key, [])),
            "rate_per_second": self.config.requests_per_second,
            "limit_per_minute": self.config.requests_per_minute,
        }


# 全局限流器实例
_global_limiter: Optional[RateLimiter] = None


def get_rate_limiter(config: RateLimitConfig = None) -> RateLimiter:
    """获取全局限流器"""
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RateLimiter(config)
    return _global_limiter


async def rate_limited(key: str = "default"):
    """限流装饰器使用的上下文管理器"""
    limiter = get_rate_limiter()
    await limiter.wait(key)

