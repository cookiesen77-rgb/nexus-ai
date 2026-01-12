"""
Agent相关路由
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse

from ..schemas import (
    ChatRequest, ChatResponse, TaskRequest, TaskResponse,
    TaskResultResponse, TaskStatus, ToolCallInfo, ErrorResponse
)

router = APIRouter(prefix="/agents", tags=["Agents"])

# 任务存储 (生产环境应使用Redis或数据库)
_tasks = {}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    单轮对话
    
    使用Agent进行对话，支持工具调用
    """
    try:
        from src.llm import create_allapi_client
        
        # 创建客户端
        client = create_allapi_client(thinking_mode=request.thinking_mode)
        
        # 转换消息格式
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        
        # 调用LLM
        response = await client.complete(
            messages=messages,
            tools=request.tools,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        # 构建响应
        tool_calls = None
        if response.has_tool_calls:
            tool_calls = [
                ToolCallInfo(
                    id=tc.id,
                    name=tc.name,
                    parameters=tc.parameters
                )
                for tc in response.tool_calls
            ]
        
        return ChatResponse(
            content=response.content,
            model=response.model,
            tool_calls=tool_calls,
            usage=response.usage,
            thinking_mode=request.thinking_mode
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    流式对话
    
    使用Server-Sent Events进行流式响应
    """
    try:
        from src.llm import create_allapi_client
        
        client = create_allapi_client(thinking_mode=request.thinking_mode)
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        
        async def generate():
            async for chunk in client.complete_stream(messages):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks", response_model=TaskResponse)
async def create_task(request: TaskRequest, background_tasks: BackgroundTasks):
    """
    创建任务
    
    异步执行复杂任务，返回任务ID
    """
    import uuid
    from datetime import datetime
    
    task_id = str(uuid.uuid4())[:8]
    
    # 初始化任务状态
    _tasks[task_id] = {
        "id": task_id,
        "status": TaskStatus.PENDING,
        "task": request.task,
        "created_at": datetime.now(),
        "result": None,
        "error": None,
        "steps": [],
        "tokens": 0
    }
    
    # 后台执行任务
    background_tasks.add_task(execute_task, task_id, request)
    
    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="Task created and queued for execution"
    )


async def execute_task(task_id: str, request: TaskRequest):
    """后台执行任务"""
    import time
    
    task_data = _tasks.get(task_id)
    if not task_data:
        return
    
    task_data["status"] = TaskStatus.RUNNING
    start_time = time.time()
    
    try:
        from src.llm import create_allapi_client
        from src.agents import PlannerAgent, ExecutorAgent
        from src.tools import setup_default_tools, get_global_registry
        
        # 设置工具
        setup_default_tools()
        registry = get_global_registry()
        
        # 创建Agent
        llm = create_allapi_client(thinking_mode=request.thinking_mode)
        planner = PlannerAgent(llm)
        
        # 规划
        plan = await planner.create_plan(request.task)
        task_data["steps"].append({"type": "plan", "content": str(plan)})
        
        # 执行 (简化版)
        executor = ExecutorAgent(llm, registry)
        
        results = []
        for step in plan.steps[:request.max_iterations]:
            result = await executor.execute_step(step, {})
            results.append(result)
            task_data["steps"].append({
                "type": "execute",
                "step": step.description,
                "result": str(result)[:200]
            })
        
        task_data["status"] = TaskStatus.COMPLETED
        task_data["result"] = "\n".join(str(r) for r in results)
        
    except Exception as e:
        task_data["status"] = TaskStatus.FAILED
        task_data["error"] = str(e)
    
    finally:
        task_data["execution_time"] = time.time() - start_time


@router.get("/tasks/{task_id}", response_model=TaskResultResponse)
async def get_task(task_id: str):
    """
    获取任务状态和结果
    """
    task_data = _tasks.get(task_id)
    
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResultResponse(
        task_id=task_id,
        status=task_data["status"],
        result=task_data.get("result"),
        steps=task_data.get("steps", []),
        total_tokens=task_data.get("tokens", 0),
        execution_time=task_data.get("execution_time", 0.0),
        error=task_data.get("error")
    )


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """
    取消任务
    """
    task_data = _tasks.get(task_id)
    
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task_data["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
        raise HTTPException(status_code=400, detail="Task already finished")
    
    task_data["status"] = TaskStatus.CANCELLED
    
    return {"message": "Task cancelled", "task_id": task_id}

