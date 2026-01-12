"""
任务调度路由
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/schedule", tags=["Schedule"])


class ScheduleRequest(BaseModel):
    """调度请求"""
    name: str
    prompt: str
    cron: Optional[str] = None  # cron表达式
    interval: Optional[int] = None  # 秒数
    run_at: Optional[datetime] = None  # 指定时间运行


class ScheduledTask(BaseModel):
    """调度任务"""
    id: str
    name: str
    prompt: str
    schedule_type: str  # 'cron', 'interval', 'once'
    schedule_value: str
    next_run: Optional[datetime]
    last_run: Optional[datetime]
    status: str  # 'active', 'paused', 'completed'
    created_at: datetime


# 任务存储 (生产环境应使用数据库)
_scheduled_tasks: dict = {}


@router.post("/create", response_model=ScheduledTask)
async def create_schedule(request: ScheduleRequest):
    """
    创建调度任务
    """
    import uuid
    
    task_id = str(uuid.uuid4())[:8]
    
    if request.cron:
        schedule_type = 'cron'
        schedule_value = request.cron
    elif request.interval:
        schedule_type = 'interval'
        schedule_value = f'{request.interval}s'
    elif request.run_at:
        schedule_type = 'once'
        schedule_value = request.run_at.isoformat()
    else:
        raise HTTPException(
            status_code=400,
            detail="Must specify one of: cron, interval, or run_at"
        )
    
    task = ScheduledTask(
        id=task_id,
        name=request.name,
        prompt=request.prompt,
        schedule_type=schedule_type,
        schedule_value=schedule_value,
        next_run=request.run_at,
        last_run=None,
        status='active',
        created_at=datetime.now()
    )
    
    _scheduled_tasks[task_id] = task
    
    # 注册到调度器 (将在工具层实现)
    try:
        from src.tools.schedule_tool import register_task
        await register_task(task)
    except ImportError:
        pass  # 调度工具未实现
    
    return task


@router.get("/list", response_model=List[ScheduledTask])
async def list_schedules():
    """
    列出所有调度任务
    """
    return list(_scheduled_tasks.values())


@router.get("/{task_id}", response_model=ScheduledTask)
async def get_schedule(task_id: str):
    """
    获取调度任务详情
    """
    task = _scheduled_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{task_id}/pause")
async def pause_schedule(task_id: str):
    """
    暂停调度任务
    """
    task = _scheduled_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.status = 'paused'
    return {"success": True, "status": "paused"}


@router.post("/{task_id}/resume")
async def resume_schedule(task_id: str):
    """
    恢复调度任务
    """
    task = _scheduled_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.status = 'active'
    return {"success": True, "status": "active"}


@router.delete("/{task_id}")
async def delete_schedule(task_id: str):
    """
    删除调度任务
    """
    if task_id not in _scheduled_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    del _scheduled_tasks[task_id]
    
    # 从调度器移除
    try:
        from src.tools.schedule_tool import unregister_task
        await unregister_task(task_id)
    except ImportError:
        pass
    
    return {"success": True}

