"""
Fetch MCP 服务器

提供 HTTP 请求功能
"""

import logging
from typing import Any, Dict, Optional

from ..base import LocalMCPServer, MCPServerConfig, MCPTool

logger = logging.getLogger(__name__)


class FetchServer(LocalMCPServer):
    """HTTP 请求 MCP 服务器"""
    
    def __init__(self, config: MCPServerConfig):
        super().__init__(config)
        
        # 注册工具
        self.register_tool(MCPTool(
            name="fetch",
            description="发送 HTTP 请求获取网页或 API 数据",
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "请求 URL"
                    },
                    "method": {
                        "type": "string",
                        "description": "HTTP 方法: GET, POST, PUT, DELETE, PATCH",
                        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                        "default": "GET"
                    },
                    "headers": {
                        "type": "object",
                        "description": "请求头",
                        "additionalProperties": {"type": "string"}
                    },
                    "body": {
                        "type": "string",
                        "description": "请求体（POST/PUT/PATCH 时使用）"
                    },
                    "timeout": {
                        "type": "number",
                        "description": "超时时间（秒），默认30",
                        "default": 30
                    },
                    "follow_redirects": {
                        "type": "boolean",
                        "description": "是否跟随重定向，默认 true",
                        "default": True
                    }
                },
                "required": ["url"]
            }
        ))
        
        self.register_tool(MCPTool(
            name="fetch_json",
            description="发送 HTTP 请求并解析 JSON 响应",
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "请求 URL"
                    },
                    "method": {
                        "type": "string",
                        "description": "HTTP 方法",
                        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                        "default": "GET"
                    },
                    "headers": {
                        "type": "object",
                        "description": "请求头"
                    },
                    "json_body": {
                        "type": "object",
                        "description": "JSON 请求体"
                    }
                },
                "required": ["url"]
            }
        ))
        
        self.register_tool(MCPTool(
            name="download_file",
            description="下载文件到本地",
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "文件 URL"
                    },
                    "save_path": {
                        "type": "string",
                        "description": "保存路径"
                    }
                },
                "required": ["url", "save_path"]
            }
        ))
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用 HTTP 工具"""
        if tool_name == "fetch":
            return await self._fetch(**arguments)
        elif tool_name == "fetch_json":
            return await self._fetch_json(**arguments)
        elif tool_name == "download_file":
            return await self._download_file(**arguments)
        return {"error": f"未知工具: {tool_name}"}
    
    async def _fetch(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        timeout: float = 30,
        follow_redirects: bool = True
    ) -> Dict[str, Any]:
        """发送 HTTP 请求"""
        import httpx
        
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=follow_redirects
            ) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    content=body
                )
                
                # 尝试解析响应内容
                content_type = response.headers.get("content-type", "")
                
                if "application/json" in content_type:
                    try:
                        data = response.json()
                    except:
                        data = response.text
                else:
                    data = response.text
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "content": data,
                    "url": str(response.url)
                }
                
        except httpx.TimeoutException:
            return {"success": False, "error": "请求超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _fetch_json(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        json_body: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """发送 JSON 请求"""
        import httpx
        
        try:
            _headers = headers or {}
            _headers["Content-Type"] = "application/json"
            _headers["Accept"] = "application/json"
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=_headers,
                    json=json_body
                )
                
                try:
                    data = response.json()
                except:
                    data = response.text
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": data
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _download_file(self, url: str, save_path: str) -> Dict[str, Any]:
        """下载文件"""
        import httpx
        from pathlib import Path
        import os
        
        try:
            workspace = os.environ.get("WORKSPACE_PATH", os.getcwd())
            file_path = Path(save_path)
            if not file_path.is_absolute():
                file_path = Path(workspace) / file_path
            
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                with open(file_path, "wb") as f:
                    f.write(response.content)
                
                return {
                    "success": True,
                    "path": str(file_path),
                    "size": len(response.content),
                    "content_type": response.headers.get("content-type")
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}

