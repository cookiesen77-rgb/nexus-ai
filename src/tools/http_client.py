"""
HTTP客户端工具 - REST API调用
"""

import json
from typing import Any, Dict, Optional, Union
from .base import BaseTool, ToolResult, ToolStatus
from .rate_limiter import get_rate_limiter
from urllib.parse import urlparse


class HttpClientTool(BaseTool):
    """HTTP客户端工具"""
    
    name: str = "http_client"
    description: str = """Make HTTP requests to APIs and web services.
    
Supports:
- GET, POST, PUT, DELETE, PATCH methods
- JSON and form data
- Custom headers
- Authentication (Bearer token, Basic auth)
- Rate limiting per domain

Returns response with status, headers, and body."""

    parameters: Dict[str, Any] = {
        "properties": {
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"],
                "description": "HTTP method",
                "default": "GET"
            },
            "url": {
                "type": "string",
                "description": "Request URL"
            },
            "headers": {
                "type": "object",
                "description": "Request headers"
            },
            "body": {
                "type": ["object", "string"],
                "description": "Request body (for POST/PUT/PATCH)"
            },
            "params": {
                "type": "object",
                "description": "URL query parameters"
            },
            "timeout": {
                "type": "integer",
                "description": "Request timeout in seconds",
                "default": 30
            },
            "auth_token": {
                "type": "string",
                "description": "Bearer token for authentication"
            }
        },
        "required": ["url"]
    }
    
    def __init__(self):
        super().__init__()
        self._session = None
    
    async def _get_session(self):
        """获取或创建HTTP会话"""
        if self._session is None:
            try:
                import httpx
                self._session = httpx.AsyncClient(
                    timeout=30,
                    follow_redirects=True
                )
            except ImportError:
                raise RuntimeError("httpx not installed. Run: pip install httpx")
        return self._session
    
    async def execute(
        self,
        url: str,
        method: str = "GET",
        headers: Dict[str, str] = None,
        body: Any = None,
        params: Dict[str, str] = None,
        timeout: int = 30,
        auth_token: str = None,
        **kwargs
    ) -> ToolResult:
        """发送HTTP请求"""
        # 限流
        domain = urlparse(url).netloc
        limiter = get_rate_limiter()
        await limiter.wait(domain)
        
        try:
            session = await self._get_session()
            
            # 构建请求头
            request_headers = headers or {}
            if auth_token:
                request_headers["Authorization"] = f"Bearer {auth_token}"
            if body and isinstance(body, dict):
                request_headers.setdefault("Content-Type", "application/json")
            
            # 处理请求体
            request_body = None
            json_body = None
            if body:
                if isinstance(body, dict):
                    json_body = body
                else:
                    request_body = body
            
            # 发送请求
            response = await session.request(
                method=method.upper(),
                url=url,
                headers=request_headers,
                params=params,
                json=json_body,
                content=request_body,
                timeout=timeout
            )
            
            # 解析响应
            content_type = response.headers.get("content-type", "")
            
            if "application/json" in content_type:
                try:
                    response_body = response.json()
                except:
                    response_body = response.text
            else:
                response_body = response.text
            
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_body,
                "url": str(response.url)
            }
            
            # 判断成功/失败
            if 200 <= response.status_code < 300:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=result
                )
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output=result,
                    error=f"HTTP {response.status_code}: {response.reason_phrase}"
                )
                
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=f"Request failed: {str(e)}"
            )
    
    async def get(self, url: str, **kwargs) -> ToolResult:
        """GET请求快捷方法"""
        return await self.execute(url, method="GET", **kwargs)
    
    async def post(self, url: str, body: Any = None, **kwargs) -> ToolResult:
        """POST请求快捷方法"""
        return await self.execute(url, method="POST", body=body, **kwargs)
    
    async def put(self, url: str, body: Any = None, **kwargs) -> ToolResult:
        """PUT请求快捷方法"""
        return await self.execute(url, method="PUT", body=body, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> ToolResult:
        """DELETE请求快捷方法"""
        return await self.execute(url, method="DELETE", **kwargs)
    
    async def close(self):
        """关闭HTTP会话"""
        if self._session:
            await self._session.aclose()
            self._session = None


class ApiClientTool(BaseTool):
    """API客户端工具 - 预配置的API调用"""
    
    name: str = "api_client"
    description: str = """Make API calls with pre-configured settings.
    
Features:
- Base URL configuration
- Default headers and authentication
- Response transformation
- Error handling and retries"""

    parameters: Dict[str, Any] = {
        "properties": {
            "endpoint": {
                "type": "string",
                "description": "API endpoint path"
            },
            "method": {
                "type": "string",
                "default": "GET"
            },
            "data": {
                "type": "object",
                "description": "Request data"
            },
            "params": {
                "type": "object",
                "description": "Query parameters"
            }
        },
        "required": ["endpoint"]
    }
    
    def __init__(
        self,
        base_url: str = "",
        default_headers: Dict[str, str] = None,
        auth_token: str = None
    ):
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.default_headers = default_headers or {}
        self.auth_token = auth_token
        self._http = HttpClientTool()
    
    async def execute(
        self,
        endpoint: str,
        method: str = "GET",
        data: Dict = None,
        params: Dict = None,
        **kwargs
    ) -> ToolResult:
        """调用API"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        headers = {**self.default_headers}
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))
        
        return await self._http.execute(
            url=url,
            method=method,
            headers=headers,
            body=data,
            params=params,
            auth_token=self.auth_token,
            **kwargs
        )
    
    async def close(self):
        """关闭连接"""
        await self._http.close()


# 创建工具实例
http_client = HttpClientTool()

