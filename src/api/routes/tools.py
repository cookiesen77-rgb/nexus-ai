"""
工具相关路由
"""

from fastapi import APIRouter, HTTPException

from ..schemas import (
    ToolCallRequest, ToolListResponse, ToolResultResponse,
    CodeExecutionRequest
)

router = APIRouter(prefix="/tools", tags=["Tools"])


@router.get("", response_model=ToolListResponse)
async def list_tools():
    """
    列出所有可用工具
    """
    from src.tools import setup_default_tools, get_global_registry
    
    setup_default_tools()
    registry = get_global_registry()
    
    tools = []
    for name in registry.list_names():
        tool = registry.get(name)
        if tool:
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            })
    
    return ToolListResponse(tools=tools, count=len(tools))


@router.post("/call", response_model=ToolResultResponse)
async def call_tool(request: ToolCallRequest):
    """
    调用指定工具
    """
    from src.tools import setup_default_tools, get_global_registry
    
    setup_default_tools()
    registry = get_global_registry()
    
    tool = registry.get(request.tool_name)
    
    if not tool:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{request.tool_name}' not found"
        )
    
    try:
        result = await tool.execute(**request.parameters)
        
        return ToolResultResponse(
            tool_name=request.tool_name,
            status=result.status.value,
            output=result.output,
            error=result.error,
            execution_time_ms=result.execution_time_ms
        )
        
    except Exception as e:
        return ToolResultResponse(
            tool_name=request.tool_name,
            status="error",
            output=None,
            error=str(e)
        )


@router.post("/execute", response_model=ToolResultResponse)
async def execute_code(request: CodeExecutionRequest):
    """
    执行Python代码
    """
    from src.tools import code_executor
    
    try:
        result = await code_executor.execute(
            code=request.code,
            timeout=request.timeout
        )
        
        return ToolResultResponse(
            tool_name="code_executor",
            status=result.status.value,
            output=result.output,
            error=result.error,
            execution_time_ms=result.execution_time_ms
        )
        
    except Exception as e:
        return ToolResultResponse(
            tool_name="code_executor",
            status="error",
            output=None,
            error=str(e)
        )

