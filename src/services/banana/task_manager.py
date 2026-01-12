"""
Nexus PPT 任务管理器
处理异步任务的创建、状态追踪和进度更新
"""

import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskType(str, Enum):
    """任务类型"""
    GENERATE_OUTLINE = "GENERATE_OUTLINE"
    GENERATE_DESCRIPTIONS = "GENERATE_DESCRIPTIONS"
    GENERATE_IMAGES = "GENERATE_IMAGES"
    EDIT_IMAGE = "EDIT_IMAGE"
    EXPORT_PPTX = "EXPORT_PPTX"
    EXPORT_PDF = "EXPORT_PDF"
    EXPORT_EDITABLE_PPTX = "EXPORT_EDITABLE_PPTX"


@dataclass
class Task:
    """任务数据类"""
    id: str
    task_type: TaskType
    status: TaskStatus = TaskStatus.PENDING
    progress: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "task_id": self.id,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "progress": self.progress,
            "result": self.result,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class TaskManager:
    """任务管理器"""
    
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._lock = asyncio.Lock()
    
    async def create_task(self, task_type: TaskType) -> Task:
        """创建新任务"""
        task_id = str(uuid.uuid4())
        task = Task(id=task_id, task_type=task_type)
        
        async with self._lock:
            self._tasks[task_id] = task
        
        logger.info(f"[TaskManager] 创建任务: {task_id}, 类型: {task_type.value}")
        return task
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    async def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[Dict] = None,
        result: Any = None,
        error_message: Optional[str] = None
    ) -> Optional[Task]:
        """更新任务状态"""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            
            if status:
                task.status = status
            if progress:
                task.progress.update(progress)
            if result is not None:
                task.result = result
            if error_message:
                task.error_message = error_message
            task.updated_at = datetime.now()
        
        logger.debug(f"[TaskManager] 更新任务 {task_id}: status={status}, progress={progress}")
        return task
    
    async def run_task(
        self,
        task: Task,
        coroutine: Callable,
        *args,
        **kwargs
    ) -> Task:
        """
        运行异步任务
        
        Args:
            task: 任务对象
            coroutine: 要执行的协程函数
            *args, **kwargs: 协程参数
        """
        try:
            await self.update_task(task.id, status=TaskStatus.PROCESSING)
            
            # 执行任务
            result = await coroutine(*args, **kwargs)
            
            await self.update_task(
                task.id,
                status=TaskStatus.COMPLETED,
                result=result
            )
            
            logger.info(f"[TaskManager] 任务完成: {task.id}")
            
        except asyncio.CancelledError:
            await self.update_task(
                task.id,
                status=TaskStatus.CANCELLED,
                error_message="任务已取消"
            )
            logger.warning(f"[TaskManager] 任务取消: {task.id}")
            
        except Exception as e:
            error_msg = str(e)
            await self.update_task(
                task.id,
                status=TaskStatus.FAILED,
                error_message=error_msg
            )
            logger.error(f"[TaskManager] 任务失败: {task.id}, 错误: {error_msg}")
        
        return task
    
    async def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        async with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
        return False
    
    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理过期任务"""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        to_delete = []
        
        async with self._lock:
            for task_id, task in self._tasks.items():
                if task.created_at < cutoff:
                    to_delete.append(task_id)
            
            for task_id in to_delete:
                del self._tasks[task_id]
        
        if to_delete:
            logger.info(f"[TaskManager] 清理了 {len(to_delete)} 个过期任务")


# 全局任务管理器实例
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """获取任务管理器单例"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager

