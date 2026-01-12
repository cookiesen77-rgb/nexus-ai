"""
任务队列 - 异步任务调度
"""

import asyncio
import uuid
from typing import Any, Callable, Dict, List, Optional, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class TaskHandle:
    """任务句柄"""
    id: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None


@dataclass
class TaskItem:
    """任务项"""
    id: str
    func: Callable[..., Awaitable[Any]]
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: int = 300
    retries: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    
    def __lt__(self, other):
        # 用于优先级队列排序
        return self.priority.value > other.priority.value


@dataclass
class QueueStats:
    """队列统计"""
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    total_submitted: int = 0
    avg_wait_time_ms: float = 0.0
    avg_execution_time_ms: float = 0.0


class TaskQueue:
    """
    异步任务队列
    
    支持优先级、超时、重试等特性
    """
    
    def __init__(
        self,
        max_workers: int = 5,
        max_queue_size: int = 100,
        default_timeout: int = 300
    ):
        """
        初始化任务队列
        
        Args:
            max_workers: 最大并发工作者数
            max_queue_size: 最大队列大小
            default_timeout: 默认超时时间(秒)
        """
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.default_timeout = default_timeout
        
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self._handles: Dict[str, TaskHandle] = {}
        self._tasks: Dict[str, TaskItem] = {}
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._stats = QueueStats()
        
        # 等待时间记录
        self._wait_times: List[float] = []
        self._execution_times: List[float] = []
    
    async def start(self):
        """启动队列"""
        if self._running:
            return
        
        self._running = True
        
        # 启动工作者
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)
    
    async def stop(self, wait: bool = True):
        """
        停止队列
        
        Args:
            wait: 是否等待当前任务完成
        """
        self._running = False
        
        if wait:
            # 等待队列清空
            await self._queue.join()
        
        # 取消工作者
        for worker in self._workers:
            worker.cancel()
        
        self._workers.clear()
    
    async def submit(
        self,
        func: Callable[..., Awaitable[Any]],
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: int = None,
        max_retries: int = 3,
        **kwargs
    ) -> TaskHandle:
        """
        提交任务
        
        Args:
            func: 异步函数
            *args: 位置参数
            priority: 优先级
            timeout: 超时时间
            max_retries: 最大重试次数
            **kwargs: 关键字参数
            
        Returns:
            TaskHandle: 任务句柄
        """
        task_id = str(uuid.uuid4())
        
        task = TaskItem(
            id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout or self.default_timeout,
            max_retries=max_retries
        )
        
        handle = TaskHandle(id=task_id)
        
        self._tasks[task_id] = task
        self._handles[task_id] = handle
        
        # 加入队列
        await self._queue.put((priority.value * -1, task))  # 负数使高优先级在前
        
        self._stats.total_submitted += 1
        self._stats.pending += 1
        
        return handle
    
    async def get_result(
        self,
        handle: TaskHandle,
        timeout: float = None
    ) -> Any:
        """
        获取任务结果
        
        Args:
            handle: 任务句柄
            timeout: 等待超时
            
        Returns:
            Any: 任务结果
        """
        start = datetime.now()
        
        while True:
            current_handle = self._handles.get(handle.id)
            if not current_handle:
                raise ValueError(f"Task {handle.id} not found")
            
            if current_handle.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                if current_handle.error:
                    raise RuntimeError(current_handle.error)
                return current_handle.result
            
            # 检查超时
            if timeout:
                elapsed = (datetime.now() - start).total_seconds()
                if elapsed > timeout:
                    raise TimeoutError(f"Timeout waiting for task {handle.id}")
            
            await asyncio.sleep(0.1)
    
    async def cancel(self, handle: TaskHandle) -> bool:
        """取消任务"""
        current_handle = self._handles.get(handle.id)
        if not current_handle:
            return False
        
        if current_handle.status == TaskStatus.PENDING:
            current_handle.status = TaskStatus.CANCELLED
            self._stats.pending -= 1
            return True
        
        return False
    
    async def _worker(self, worker_id: int):
        """工作者协程"""
        while self._running:
            try:
                # 获取任务
                priority, task = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            
            handle = self._handles.get(task.id)
            if not handle or handle.status == TaskStatus.CANCELLED:
                self._queue.task_done()
                continue
            
            # 记录等待时间
            wait_time = (datetime.now() - task.created_at).total_seconds() * 1000
            self._wait_times.append(wait_time)
            
            # 更新状态
            handle.status = TaskStatus.RUNNING
            handle.started_at = datetime.now()
            self._stats.pending -= 1
            self._stats.running += 1
            
            try:
                # 执行任务
                result = await asyncio.wait_for(
                    task.func(*task.args, **task.kwargs),
                    timeout=task.timeout
                )
                
                handle.result = result
                handle.status = TaskStatus.COMPLETED
                self._stats.completed += 1
                
            except asyncio.TimeoutError:
                handle.status = TaskStatus.TIMEOUT
                handle.error = f"Task timeout after {task.timeout}s"
                self._stats.failed += 1
                
            except Exception as e:
                # 重试逻辑
                if task.retries < task.max_retries:
                    task.retries += 1
                    await self._queue.put((priority, task))
                    handle.status = TaskStatus.PENDING
                    self._stats.pending += 1
                else:
                    handle.status = TaskStatus.FAILED
                    handle.error = str(e)
                    self._stats.failed += 1
            
            finally:
                handle.completed_at = datetime.now()
                self._stats.running -= 1
                
                # 记录执行时间
                if handle.started_at:
                    exec_time = (handle.completed_at - handle.started_at).total_seconds() * 1000
                    self._execution_times.append(exec_time)
                
                self._queue.task_done()
    
    def get_stats(self) -> QueueStats:
        """获取队列统计"""
        stats = self._stats
        
        if self._wait_times:
            stats.avg_wait_time_ms = sum(self._wait_times) / len(self._wait_times)
        
        if self._execution_times:
            stats.avg_execution_time_ms = sum(self._execution_times) / len(self._execution_times)
        
        return stats
    
    def get_handle(self, task_id: str) -> Optional[TaskHandle]:
        """获取任务句柄"""
        return self._handles.get(task_id)
    
    @property
    def is_running(self) -> bool:
        """是否运行中"""
        return self._running
    
    @property
    def queue_size(self) -> int:
        """当前队列大小"""
        return self._queue.qsize()


# 全局任务队列
_default_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """获取全局任务队列"""
    global _default_queue
    if _default_queue is None:
        _default_queue = TaskQueue()
    return _default_queue


async def submit_task(
    func: Callable[..., Awaitable[Any]],
    *args,
    **kwargs
) -> TaskHandle:
    """快捷函数: 提交任务"""
    queue = get_task_queue()
    if not queue.is_running:
        await queue.start()
    return await queue.submit(func, *args, **kwargs)

