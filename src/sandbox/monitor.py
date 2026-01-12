"""
资源监控
"""

import asyncio
import time
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ResourceSnapshot:
    """资源快照"""
    timestamp: datetime
    cpu_percent: float = 0.0
    memory_bytes: int = 0
    memory_percent: float = 0.0
    disk_read_bytes: int = 0
    disk_write_bytes: int = 0


@dataclass
class ExecutionMonitor:
    """执行监控器"""
    
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    timeout: int = 60
    memory_limit: int = 512 * 1024 * 1024
    
    snapshots: list = field(default_factory=list)
    peak_memory: int = 0
    
    _is_running: bool = False
    _cancelled: bool = False
    
    def start(self) -> None:
        """开始监控"""
        self.start_time = time.time()
        self._is_running = True
        self._cancelled = False
    
    def stop(self) -> None:
        """停止监控"""
        self.end_time = time.time()
        self._is_running = False
    
    def cancel(self) -> None:
        """取消执行"""
        self._cancelled = True
        self.stop()
    
    @property
    def elapsed_time(self) -> float:
        """已用时间"""
        if self.start_time is None:
            return 0.0
        
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def remaining_time(self) -> float:
        """剩余时间"""
        return max(0, self.timeout - self.elapsed_time)
    
    @property
    def is_timeout(self) -> bool:
        """是否超时"""
        return self.elapsed_time >= self.timeout
    
    @property
    def is_memory_exceeded(self) -> bool:
        """是否内存超限"""
        return self.peak_memory > self.memory_limit
    
    def record_memory(self, memory_bytes: int) -> None:
        """记录内存使用"""
        self.peak_memory = max(self.peak_memory, memory_bytes)
        
        self.snapshots.append(ResourceSnapshot(
            timestamp=datetime.now(),
            memory_bytes=memory_bytes
        ))
    
    def get_summary(self) -> dict:
        """获取监控摘要"""
        return {
            'elapsed_time': self.elapsed_time,
            'peak_memory': self.peak_memory,
            'is_timeout': self.is_timeout,
            'is_memory_exceeded': self.is_memory_exceeded,
            'is_cancelled': self._cancelled,
            'snapshot_count': len(self.snapshots),
        }


class TimeoutManager:
    """超时管理器"""
    
    @staticmethod
    async def run_with_timeout(
        coro: Awaitable,
        timeout: int,
        on_timeout: Optional[Callable] = None
    ):
        """
        带超时运行协程
        
        Args:
            coro: 协程
            timeout: 超时秒数
            on_timeout: 超时回调
            
        Returns:
            协程结果
            
        Raises:
            asyncio.TimeoutError: 超时
        """
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            if on_timeout:
                await on_timeout() if asyncio.iscoroutinefunction(on_timeout) else on_timeout()
            raise
    
    @staticmethod
    async def run_with_cancellation(
        coro: Awaitable,
        cancel_event: asyncio.Event,
        check_interval: float = 0.1
    ):
        """
        带取消支持运行协程
        
        Args:
            coro: 协程
            cancel_event: 取消事件
            check_interval: 检查间隔
            
        Returns:
            协程结果
        """
        task = asyncio.create_task(coro)
        
        while not task.done():
            if cancel_event.is_set():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                raise asyncio.CancelledError("Execution cancelled")
            
            await asyncio.sleep(check_interval)
        
        return task.result()


class HealthChecker:
    """健康检查器"""
    
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.last_check: Optional[datetime] = None
        self.is_healthy: bool = True
        self.error_count: int = 0
        self.max_errors: int = 3
    
    async def check(self, sandbox) -> bool:
        """执行健康检查"""
        try:
            is_healthy = await sandbox.health_check()
            
            if is_healthy:
                self.error_count = 0
            else:
                self.error_count += 1
            
            self.is_healthy = self.error_count < self.max_errors
            self.last_check = datetime.now()
            
            return self.is_healthy
            
        except Exception:
            self.error_count += 1
            self.is_healthy = self.error_count < self.max_errors
            return self.is_healthy
    
    def should_check(self) -> bool:
        """是否应该检查"""
        if self.last_check is None:
            return True
        
        elapsed = (datetime.now() - self.last_check).total_seconds()
        return elapsed >= self.check_interval

