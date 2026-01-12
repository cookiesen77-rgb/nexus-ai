"""
沙箱基类
"""

from abc import ABC, abstractmethod
from typing import Optional
from .models import ExecutionRequest, ExecutionResult, SandboxConfig


class BaseSandbox(ABC):
    """沙箱抽象基类"""
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self._is_initialized = False
    
    @property
    @abstractmethod
    def sandbox_type(self) -> str:
        """沙箱类型标识"""
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """初始化沙箱环境"""
        pass
    
    @abstractmethod
    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """执行代码"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """清理沙箱资源"""
        pass
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
    
    def is_ready(self) -> bool:
        """检查沙箱是否就绪"""
        return self._is_initialized
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 执行简单的测试代码
            test_request = ExecutionRequest(
                code="print('health check')",
                timeout=5
            )
            result = await self.execute(test_request)
            return result.is_success
        except Exception:
            return False

