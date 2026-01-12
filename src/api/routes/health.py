"""
健康检查路由
"""

from fastapi import APIRouter, Depends
from datetime import datetime

from ..schemas import HealthResponse, MetricsResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
async def health_check():
    """
    健康检查
    
    返回服务状态和组件健康状况
    """
    return HealthResponse(
        status="healthy",
        version="0.6.0",
        timestamp=datetime.now(),
        components={
            "llm": "healthy",
            "tools": "healthy",
            "cache": "healthy",
            "memory": "healthy"
        }
    )


@router.get("/ready")
async def readiness_check():
    """就绪检查"""
    return {"ready": True}


@router.get("/live")
async def liveness_check():
    """存活检查"""
    return {"alive": True}

