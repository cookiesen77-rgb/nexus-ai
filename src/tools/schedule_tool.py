"""
任务调度工具

支持cron、间隔和定时任务调度
"""

import asyncio
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import threading

from .base import BaseTool, ToolResult, ToolStatus


class ScheduleType(str, Enum):
    """调度类型"""
    CRON = "cron"
    INTERVAL = "interval"
    ONCE = "once"


@dataclass
class ScheduledJob:
    """调度任务"""
    id: str
    name: str
    prompt: str
    schedule_type: ScheduleType
    schedule_value: str
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    run_count: int = 0
    status: str = "active"  # active, paused, completed
    created_at: datetime = field(default_factory=datetime.now)


class Scheduler:
    """任务调度器"""
    
    def __init__(self):
        self._jobs: Dict[str, ScheduledJob] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: Dict[str, Callable] = {}
    
    def add_job(
        self,
        job_id: str,
        name: str,
        prompt: str,
        schedule_type: ScheduleType,
        schedule_value: str,
        callback: Optional[Callable] = None
    ) -> ScheduledJob:
        """添加调度任务"""
        job = ScheduledJob(
            id=job_id,
            name=name,
            prompt=prompt,
            schedule_type=schedule_type,
            schedule_value=schedule_value
        )
        
        # 计算下次运行时间
        job.next_run = self._calculate_next_run(job)
        
        self._jobs[job_id] = job
        if callback:
            self._callbacks[job_id] = callback
        
        return job
    
    def remove_job(self, job_id: str) -> bool:
        """移除调度任务"""
        if job_id in self._jobs:
            del self._jobs[job_id]
            self._callbacks.pop(job_id, None)
            return True
        return False
    
    def pause_job(self, job_id: str) -> bool:
        """暂停任务"""
        job = self._jobs.get(job_id)
        if job:
            job.status = "paused"
            return True
        return False
    
    def resume_job(self, job_id: str) -> bool:
        """恢复任务"""
        job = self._jobs.get(job_id)
        if job:
            job.status = "active"
            job.next_run = self._calculate_next_run(job)
            return True
        return False
    
    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """获取任务"""
        return self._jobs.get(job_id)
    
    def list_jobs(self) -> List[ScheduledJob]:
        """列出所有任务"""
        return list(self._jobs.values())
    
    def _calculate_next_run(self, job: ScheduledJob) -> datetime:
        """计算下次运行时间"""
        now = datetime.now()
        
        if job.schedule_type == ScheduleType.ONCE:
            return datetime.fromisoformat(job.schedule_value)
        
        elif job.schedule_type == ScheduleType.INTERVAL:
            # 解析间隔 (e.g., "60s", "5m", "1h")
            value = job.schedule_value
            if value.endswith('s'):
                seconds = int(value[:-1])
            elif value.endswith('m'):
                seconds = int(value[:-1]) * 60
            elif value.endswith('h'):
                seconds = int(value[:-1]) * 3600
            else:
                seconds = int(value)
            
            return now + timedelta(seconds=seconds)
        
        elif job.schedule_type == ScheduleType.CRON:
            # 简化的cron解析 (只支持基本格式)
            # 实际应用中应使用croniter库
            return now + timedelta(minutes=1)  # 简化处理
        
        return now
    
    def start(self):
        """启动调度器"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """停止调度器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def _run_loop(self):
        """调度循环"""
        while self._running:
            now = datetime.now()
            
            for job_id, job in list(self._jobs.items()):
                if job.status != "active":
                    continue
                
                if job.next_run and job.next_run <= now:
                    # 执行任务
                    self._execute_job(job)
                    
                    # 更新状态
                    job.last_run = now
                    job.run_count += 1
                    
                    if job.schedule_type == ScheduleType.ONCE:
                        job.status = "completed"
                    else:
                        job.next_run = self._calculate_next_run(job)
            
            # 每秒检查一次
            threading.Event().wait(1)
    
    def _execute_job(self, job: ScheduledJob):
        """执行任务"""
        callback = self._callbacks.get(job.id)
        if callback:
            try:
                callback(job)
            except Exception as e:
                print(f"Job {job.id} execution error: {e}")


# 全局调度器
_scheduler: Optional[Scheduler] = None


def get_scheduler() -> Scheduler:
    """获取调度器"""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
        _scheduler.start()
    return _scheduler


async def register_task(task: Any):
    """注册任务到调度器"""
    scheduler = get_scheduler()
    
    if task.schedule_type == 'cron':
        schedule_type = ScheduleType.CRON
    elif task.schedule_type == 'interval':
        schedule_type = ScheduleType.INTERVAL
    else:
        schedule_type = ScheduleType.ONCE
    
    scheduler.add_job(
        job_id=task.id,
        name=task.name,
        prompt=task.prompt,
        schedule_type=schedule_type,
        schedule_value=task.schedule_value
    )


async def unregister_task(task_id: str):
    """从调度器移除任务"""
    scheduler = get_scheduler()
    scheduler.remove_job(task_id)


class ScheduleTool(BaseTool):
    """
    任务调度工具
    
    支持创建定时、间隔和cron调度任务
    """
    
    name = "schedule"
    description = "Task scheduling tool for cron, interval, and one-time tasks"
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "list", "get", "pause", "resume", "delete"],
                "description": "Action to perform"
            },
            "name": {
                "type": "string",
                "description": "Task name"
            },
            "prompt": {
                "type": "string",
                "description": "Task prompt to execute"
            },
            "cron": {
                "type": "string",
                "description": "Cron expression (e.g., '0 9 * * *')"
            },
            "interval": {
                "type": "string",
                "description": "Interval (e.g., '60s', '5m', '1h')"
            },
            "run_at": {
                "type": "string",
                "description": "ISO datetime for one-time execution"
            },
            "job_id": {
                "type": "string",
                "description": "Job ID for get/pause/resume/delete"
            }
        },
        "required": ["action"]
    }
    
    async def execute(
        self,
        action: str,
        name: str = "",
        prompt: str = "",
        cron: str = "",
        interval: str = "",
        run_at: str = "",
        job_id: str = ""
    ) -> ToolResult:
        """执行调度操作"""
        import uuid
        
        scheduler = get_scheduler()
        
        try:
            if action == "create":
                if not name or not prompt:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error="Name and prompt are required"
                    )
                
                if cron:
                    schedule_type = ScheduleType.CRON
                    schedule_value = cron
                elif interval:
                    schedule_type = ScheduleType.INTERVAL
                    schedule_value = interval
                elif run_at:
                    schedule_type = ScheduleType.ONCE
                    schedule_value = run_at
                else:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error="Must specify cron, interval, or run_at"
                    )
                
                new_id = str(uuid.uuid4())[:8]
                job = scheduler.add_job(
                    job_id=new_id,
                    name=name,
                    prompt=prompt,
                    schedule_type=schedule_type,
                    schedule_value=schedule_value
                )
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"Created scheduled job '{job.name}' ({job.id})",
                    data={
                        'id': job.id,
                        'name': job.name,
                        'next_run': job.next_run.isoformat() if job.next_run else None
                    }
                )
            
            elif action == "list":
                jobs = scheduler.list_jobs()
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"Found {len(jobs)} scheduled jobs",
                    data=[
                        {
                            'id': j.id,
                            'name': j.name,
                            'status': j.status,
                            'next_run': j.next_run.isoformat() if j.next_run else None,
                            'run_count': j.run_count
                        }
                        for j in jobs
                    ]
                )
            
            elif action == "get":
                if not job_id:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error="Job ID is required"
                    )
                job = scheduler.get_job(job_id)
                if not job:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error="Job not found"
                    )
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"Job '{job.name}'",
                    data={
                        'id': job.id,
                        'name': job.name,
                        'prompt': job.prompt,
                        'status': job.status,
                        'next_run': job.next_run.isoformat() if job.next_run else None,
                        'last_run': job.last_run.isoformat() if job.last_run else None,
                        'run_count': job.run_count
                    }
                )
            
            elif action == "pause":
                if scheduler.pause_job(job_id):
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        output=f"Paused job {job_id}"
                    )
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error="Job not found"
                )
            
            elif action == "resume":
                if scheduler.resume_job(job_id):
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        output=f"Resumed job {job_id}"
                    )
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error="Job not found"
                )
            
            elif action == "delete":
                if scheduler.remove_job(job_id):
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        output=f"Deleted job {job_id}"
                    )
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error="Job not found"
                )
            
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error=f"Unknown action: {action}"
                )
                
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=str(e)
            )


# 工具实例
schedule_tool = ScheduleTool()

