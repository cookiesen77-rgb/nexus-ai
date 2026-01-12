"""
Admin REST API

提供工具、MCP、Skills 的管理接口
"""

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from src.admin import get_config_manager, verify_admin_password, get_admin_password_hash
from src.admin.auth import verify_admin_token, create_admin_token

router = APIRouter(prefix="/admin", tags=["admin"])


# ==================== 认证依赖 ====================

async def verify_admin(x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")):
    """验证 Admin Token"""
    if not x_admin_token:
        raise HTTPException(status_code=401, detail="Missing X-Admin-Token header")
    if not verify_admin_token(x_admin_token):
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return True


# ==================== 请求模型 ====================

class AuthRequest(BaseModel):
    password: str


class ToolUpdate(BaseModel):
    enabled: Optional[bool] = None
    category: Optional[str] = None
    description: Optional[str] = None


class MCPServerConfig(BaseModel):
    name: str
    type: str = "stdio"
    command: Optional[str] = None
    args: List[str] = []
    env: Dict[str, str] = {}
    cwd: Optional[str] = None
    url: Optional[str] = None
    api_key: Optional[str] = None
    enabled: bool = True


class MCPUpdate(BaseModel):
    enabled: Optional[bool] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    cwd: Optional[str] = None


class SkillConfig(BaseModel):
    name: str
    description: str = ""
    tools: List[str] = []
    enabled: bool = True


class SkillUpdate(BaseModel):
    enabled: Optional[bool] = None
    description: Optional[str] = None
    tools: Optional[List[str]] = None


# ==================== 认证接口 ====================

@router.post("/auth")
async def authenticate(request: AuthRequest):
    """验证 Admin 密码并返回 Token"""
    token = create_admin_token(request.password)
    if token:
        return {"success": True, "token": token}
    raise HTTPException(status_code=401, detail="Invalid password")


# ==================== 工具管理 ====================

@router.get("/tools")
async def get_tools(admin: bool = Depends(verify_admin)):
    """获取所有工具配置"""
    config_manager = get_config_manager()
    return config_manager.get_tools_config()


@router.get("/tools/enabled")
async def get_enabled_tools(admin: bool = Depends(verify_admin)):
    """获取所有启用的工具名称"""
    config_manager = get_config_manager()
    return {"enabled_tools": config_manager.get_enabled_tools()}


@router.get("/tools/{name}")
async def get_tool(name: str, admin: bool = Depends(verify_admin)):
    """获取单个工具配置"""
    config_manager = get_config_manager()
    config = config_manager.get_tool_config(name)
    if config is None:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    return {"name": name, **config}


@router.put("/tools/{name}")
async def update_tool(name: str, updates: ToolUpdate, admin: bool = Depends(verify_admin)):
    """更新工具配置"""
    config_manager = get_config_manager()
    update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}
    if config_manager.update_tool(name, update_dict):
        return {"success": True, "message": f"Tool '{name}' updated"}
    raise HTTPException(status_code=500, detail="Failed to update tool")


@router.put("/tools/{name}/enable")
async def enable_tool(name: str, admin: bool = Depends(verify_admin)):
    """启用工具"""
    config_manager = get_config_manager()
    if config_manager.set_tool_enabled(name, True):
        return {"success": True, "message": f"Tool '{name}' enabled"}
    raise HTTPException(status_code=500, detail="Failed to enable tool")


@router.put("/tools/{name}/disable")
async def disable_tool(name: str, admin: bool = Depends(verify_admin)):
    """禁用工具"""
    config_manager = get_config_manager()
    if config_manager.set_tool_enabled(name, False):
        return {"success": True, "message": f"Tool '{name}' disabled"}
    raise HTTPException(status_code=500, detail="Failed to disable tool")


# ==================== MCP 管理 ====================

@router.get("/mcp")
async def get_mcp_servers(admin: bool = Depends(verify_admin)):
    """获取所有 MCP 服务器配置"""
    config_manager = get_config_manager()
    return config_manager.get_mcp_config()


@router.get("/mcp/enabled")
async def get_enabled_mcp_servers(admin: bool = Depends(verify_admin)):
    """获取所有启用的 MCP 服务器"""
    config_manager = get_config_manager()
    return {"enabled_servers": config_manager.get_enabled_mcp_servers()}


@router.get("/mcp/{name}")
async def get_mcp_server(name: str, admin: bool = Depends(verify_admin)):
    """获取单个 MCP 服务器配置"""
    config_manager = get_config_manager()
    config = config_manager.get_mcp_server(name)
    if config is None:
        raise HTTPException(status_code=404, detail=f"MCP server '{name}' not found")
    return config


@router.put("/mcp/{name}")
async def update_mcp_server(name: str, updates: MCPUpdate, admin: bool = Depends(verify_admin)):
    """更新 MCP 服务器配置"""
    config_manager = get_config_manager()
    update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}
    if config_manager.update_mcp_server(name, update_dict):
        return {"success": True, "message": f"MCP server '{name}' updated"}
    raise HTTPException(status_code=404, detail=f"MCP server '{name}' not found")


@router.put("/mcp/{name}/enable")
async def enable_mcp_server(name: str, admin: bool = Depends(verify_admin)):
    """启用 MCP 服务器"""
    config_manager = get_config_manager()
    if config_manager.set_mcp_enabled(name, True):
        return {"success": True, "message": f"MCP server '{name}' enabled"}
    raise HTTPException(status_code=404, detail=f"MCP server '{name}' not found")


@router.put("/mcp/{name}/disable")
async def disable_mcp_server(name: str, admin: bool = Depends(verify_admin)):
    """禁用 MCP 服务器"""
    config_manager = get_config_manager()
    if config_manager.set_mcp_enabled(name, False):
        return {"success": True, "message": f"MCP server '{name}' disabled"}
    raise HTTPException(status_code=404, detail=f"MCP server '{name}' not found")


@router.post("/mcp")
async def add_mcp_server(config: MCPServerConfig, admin: bool = Depends(verify_admin)):
    """添加新 MCP 服务器"""
    config_manager = get_config_manager()
    if config_manager.add_mcp_server(config.model_dump()):
        return {"success": True, "message": f"MCP server '{config.name}' added"}
    raise HTTPException(status_code=400, detail=f"MCP server '{config.name}' already exists")


@router.delete("/mcp/{name}")
async def delete_mcp_server(name: str, admin: bool = Depends(verify_admin)):
    """删除 MCP 服务器"""
    config_manager = get_config_manager()
    if config_manager.delete_mcp_server(name):
        return {"success": True, "message": f"MCP server '{name}' deleted"}
    raise HTTPException(status_code=404, detail=f"MCP server '{name}' not found")


# ==================== Skills 管理 ====================

@router.get("/skills")
async def get_skills(admin: bool = Depends(verify_admin)):
    """获取所有 Skills 配置"""
    config_manager = get_config_manager()
    return config_manager.get_skills_config()


@router.get("/skills/enabled")
async def get_enabled_skills(admin: bool = Depends(verify_admin)):
    """获取所有启用的 Skills"""
    config_manager = get_config_manager()
    return {"enabled_skills": config_manager.get_enabled_skills()}


@router.put("/skills/{name}")
async def update_skill(name: str, updates: SkillUpdate, admin: bool = Depends(verify_admin)):
    """更新 Skill 配置"""
    config_manager = get_config_manager()
    update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}
    if config_manager.update_skill(name, update_dict):
        return {"success": True, "message": f"Skill '{name}' updated"}
    raise HTTPException(status_code=500, detail="Failed to update skill")


@router.post("/skills")
async def add_skill(config: SkillConfig, admin: bool = Depends(verify_admin)):
    """添加新 Skill"""
    config_manager = get_config_manager()
    skill_config = config.model_dump()
    name = skill_config.pop("name")
    if config_manager.add_skill(name, skill_config):
        return {"success": True, "message": f"Skill '{name}' added"}
    raise HTTPException(status_code=400, detail=f"Skill '{name}' already exists")


@router.delete("/skills/{name}")
async def delete_skill(name: str, admin: bool = Depends(verify_admin)):
    """删除 Skill"""
    config_manager = get_config_manager()
    if config_manager.delete_skill(name):
        return {"success": True, "message": f"Skill '{name}' deleted"}
    raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")


# ==================== 热重载 ====================

@router.post("/reload")
async def reload_configs(admin: bool = Depends(verify_admin)):
    """重新加载所有配置"""
    config_manager = get_config_manager()
    config_manager.reload_all()
    return {"success": True, "message": "All configurations reloaded"}


@router.post("/reload/tools")
async def reload_tools(admin: bool = Depends(verify_admin)):
    """重新加载工具配置"""
    config_manager = get_config_manager()
    config_manager.reload_tools()
    return {"success": True, "message": "Tools configuration reloaded"}


@router.post("/reload/mcp")
async def reload_mcp(admin: bool = Depends(verify_admin)):
    """重新加载 MCP 配置"""
    config_manager = get_config_manager()
    config_manager.reload_mcp()
    return {"success": True, "message": "MCP configuration reloaded"}


# ==================== 状态概览 ====================

@router.get("/status")
async def get_status(admin: bool = Depends(verify_admin)):
    """获取管理状态概览"""
    config_manager = get_config_manager()
    
    tools_config = config_manager.get_tools_config()
    tools = tools_config.get("tools", {})
    enabled_tools = [name for name, cfg in tools.items() if cfg.get("enabled", True)]
    disabled_tools = [name for name, cfg in tools.items() if not cfg.get("enabled", True)]
    
    mcp_servers = config_manager.get_mcp_servers()
    enabled_mcp = [s["name"] for s in mcp_servers if s.get("enabled", True)]
    disabled_mcp = [s["name"] for s in mcp_servers if not s.get("enabled", True)]
    
    return {
        "tools": {
            "total": len(tools),
            "enabled": len(enabled_tools),
            "disabled": len(disabled_tools),
            "enabled_list": enabled_tools,
            "disabled_list": disabled_tools,
        },
        "mcp": {
            "total": len(mcp_servers),
            "enabled": len(enabled_mcp),
            "disabled": len(disabled_mcp),
            "enabled_list": enabled_mcp,
            "disabled_list": disabled_mcp,
        },
        "skills": {
            "total": len(config_manager.get_skills_config().get("skills", {})),
            "enabled": len(config_manager.get_enabled_skills()),
        }
    }

