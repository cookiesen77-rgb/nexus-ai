"""
MCP API 路由

提供 MCP 相关的 REST API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter(prefix="/mcp", tags=["MCP"])


class MCPToolCallRequest(BaseModel):
    """MCP 工具调用请求"""
    tool_name: str
    arguments: Dict[str, Any] = {}


class MCPResourceReadRequest(BaseModel):
    """MCP 资源读取请求"""
    uri: str
    server_name: Optional[str] = None


@router.get("/servers")
async def list_servers():
    """列出所有 MCP 服务器"""
    from src.mcp import get_mcp_registry
    
    registry = get_mcp_registry()
    servers = []
    
    for server in registry.client.servers:
        servers.append({
            "name": server.name,
            "status": server.status.value,
            "tools_count": len(server.tools),
            "resources_count": len(server.resources)
        })
    
    return {
        "servers": servers,
        "connected": len(registry.client.connected_servers),
        "total": len(registry.client.servers)
    }


@router.get("/tools")
async def list_tools(format: str = "openai"):
    """列出所有可用的 MCP 工具"""
    from src.mcp import get_mcp_registry
    
    registry = get_mcp_registry()
    tools = registry.get_all_tools()
    
    tool_list = []
    for tool in tools:
        tool_list.append({
            "name": f"mcp_{tool.server_name}_{tool.name}",
            "description": tool.description,
            "server": tool.server_name,
            "parameters": tool.parameters
        })
    
    return {
        "tools": tool_list,
        "schemas": registry.get_tools_schemas(format),
        "count": len(tool_list)
    }


@router.get("/resources")
async def list_resources():
    """列出所有可用的 MCP 资源"""
    from src.mcp import get_mcp_registry
    
    registry = get_mcp_registry()
    resources = registry.client.get_all_resources()
    
    resource_list = []
    for resource in resources:
        resource_list.append({
            "uri": resource.uri,
            "name": resource.name,
            "description": resource.description,
            "mime_type": resource.mime_type,
            "server": resource.server_name
        })
    
    return {
        "resources": resource_list,
        "count": len(resource_list)
    }


@router.post("/call")
async def call_tool(request: MCPToolCallRequest):
    """调用 MCP 工具"""
    from src.mcp import get_mcp_registry
    
    registry = get_mcp_registry()
    
    # 检查工具是否存在
    if not registry.is_mcp_tool(request.tool_name):
        raise HTTPException(
            status_code=404,
            detail=f"MCP 工具 '{request.tool_name}' 未找到"
        )
    
    try:
        result = await registry.call_tool(request.tool_name, request.arguments)
        return {
            "success": True,
            "tool": request.tool_name,
            "result": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"工具执行失败: {str(e)}"
        )


@router.post("/resource")
async def read_resource(request: MCPResourceReadRequest):
    """读取 MCP 资源"""
    from src.mcp import get_mcp_registry
    
    registry = get_mcp_registry()
    
    try:
        result = await registry.client.read_resource(
            request.uri,
            request.server_name
        )
        return {
            "success": True,
            "uri": request.uri,
            "content": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"资源读取失败: {str(e)}"
        )


@router.get("/server/{server_name}")
async def get_server_info(server_name: str):
    """获取服务器详细信息"""
    from src.mcp import get_mcp_registry
    
    registry = get_mcp_registry()
    server = registry.client.get_server(server_name)
    
    if not server:
        raise HTTPException(
            status_code=404,
            detail=f"服务器 '{server_name}' 未找到"
        )
    
    return {
        "name": server.name,
        "status": server.status.value,
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
            for tool in server.tools
        ],
        "resources": [
            {
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description
            }
            for resource in server.resources
        ]
    }


@router.post("/server/{server_name}/reconnect")
async def reconnect_server(server_name: str):
    """重新连接服务器"""
    from src.mcp import get_mcp_registry
    
    registry = get_mcp_registry()
    server = registry.client.get_server(server_name)
    
    if not server:
        raise HTTPException(
            status_code=404,
            detail=f"服务器 '{server_name}' 未找到"
        )
    
    try:
        await server.disconnect()
        success = await server.connect()
        return {
            "success": success,
            "status": server.status.value
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"重新连接失败: {str(e)}"
        )

