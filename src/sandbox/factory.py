"""
沙箱工厂 - 创建不同类型的沙箱实例
"""

from typing import Optional
from .base import BaseSandbox
from .models import SandboxConfig
from .local import LocalSandbox
from .docker import DockerSandbox


class SandboxFactory:
    """沙箱工厂"""
    
    _sandbox_types = {
        'local': LocalSandbox,
        'docker': DockerSandbox,
    }
    
    @classmethod
    def create(
        cls, 
        sandbox_type: str = "local",
        config: Optional[SandboxConfig] = None
    ) -> BaseSandbox:
        """
        创建沙箱实例
        
        Args:
            sandbox_type: 沙箱类型 (local, docker)
            config: 沙箱配置
            
        Returns:
            BaseSandbox: 沙箱实例
        """
        if sandbox_type not in cls._sandbox_types:
            available = ', '.join(cls._sandbox_types.keys())
            raise ValueError(f"Unknown sandbox type: {sandbox_type}. Available: {available}")
        
        sandbox_class = cls._sandbox_types[sandbox_type]
        return sandbox_class(config)
    
    @classmethod
    def register(cls, name: str, sandbox_class: type) -> None:
        """注册新的沙箱类型"""
        if not issubclass(sandbox_class, BaseSandbox):
            raise TypeError(f"{sandbox_class} must be a subclass of BaseSandbox")
        cls._sandbox_types[name] = sandbox_class
    
    @classmethod
    def available_types(cls) -> list:
        """获取可用的沙箱类型"""
        return list(cls._sandbox_types.keys())


def create_sandbox(
    sandbox_type: str = "local",
    config: Optional[SandboxConfig] = None
) -> BaseSandbox:
    """
    便捷函数：创建沙箱实例
    
    Args:
        sandbox_type: 沙箱类型
        config: 沙箱配置
        
    Returns:
        BaseSandbox: 沙箱实例
        
    Example:
        >>> sandbox = create_sandbox("docker")
        >>> async with sandbox:
        ...     result = await sandbox.execute(request)
    """
    return SandboxFactory.create(sandbox_type, config)


async def quick_execute(
    code: str,
    sandbox_type: str = "local",
    timeout: int = 60
) -> str:
    """
    快速执行代码
    
    Args:
        code: Python代码
        sandbox_type: 沙箱类型
        timeout: 超时时间
        
    Returns:
        str: 执行输出或错误信息
        
    Example:
        >>> output = await quick_execute("print('Hello')")
        >>> print(output)
        Hello
    """
    from .models import ExecutionRequest
    
    sandbox = create_sandbox(sandbox_type)
    
    async with sandbox:
        request = ExecutionRequest(code=code, timeout=timeout)
        result = await sandbox.execute(request)
        
        if result.is_success:
            return result.output
        else:
            return f"Error ({result.status.value}): {result.error}"

