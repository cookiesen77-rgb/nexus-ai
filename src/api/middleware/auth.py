"""
认证中间件
"""

import os
from typing import Optional
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware


class APIKeyAuth(HTTPBearer):
    """API Key认证"""
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.api_key = os.getenv("MANUS_API_KEY")
    
    async def __call__(self, request: Request) -> Optional[str]:
        # 如果没有配置API Key，跳过认证
        if not self.api_key:
            return None
        
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if credentials:
            if credentials.credentials != self.api_key:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid API key"
                )
            return credentials.credentials
        
        raise HTTPException(
            status_code=401,
            detail="API key required"
        )


class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件"""
    
    # 不需要认证的路径
    PUBLIC_PATHS = [
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/health",
        "/api/v1/health/ready",
        "/api/v1/health/live",
    ]
    
    def __init__(self, app, api_key: str = None):
        super().__init__(app)
        self.api_key = api_key or os.getenv("MANUS_API_KEY")
    
    async def dispatch(self, request: Request, call_next):
        # 公开路径不需要认证
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)
        
        # 如果没有配置API Key，跳过认证
        if not self.api_key:
            return await call_next(request)
        
        # 检查Authorization头
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            raise HTTPException(
                status_code=401,
                detail="Authorization header required"
            )
        
        # 支持 "Bearer <key>" 或直接 "<key>"
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            token = auth_header
        
        if token != self.api_key:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
        
        return await call_next(request)


# 依赖注入
api_key_auth = APIKeyAuth(auto_error=False)


async def get_api_key(
    credentials: HTTPAuthorizationCredentials = None
) -> Optional[str]:
    """获取API Key (用于依赖注入)"""
    if credentials:
        return credentials.credentials
    return None

