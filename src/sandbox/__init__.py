"""
Manus AI Agent - 代码执行沙箱

提供安全的Python代码执行环境。

使用示例:
    >>> from src.sandbox import create_sandbox, ExecutionRequest
    >>> 
    >>> # 创建沙箱
    >>> sandbox = create_sandbox("local")
    >>> 
    >>> # 执行代码
    >>> async with sandbox:
    ...     request = ExecutionRequest(code="print('Hello')", timeout=30)
    ...     result = await sandbox.execute(request)
    ...     print(result.output)
    Hello

支持的沙箱类型:
    - local: 本地Python执行（开发测试用）
    - docker: Docker容器隔离（生产环境推荐）
"""

from .models import (
    ExecutionStatus,
    ExecutionResult,
    ExecutionRequest,
    SandboxConfig,
    ExecutionMetrics,
)

from .base import BaseSandbox
from .local import LocalSandbox
from .docker import DockerSandbox
from .factory import SandboxFactory, create_sandbox, quick_execute

from .security import SecurityChecker, ResourceLimiter
from .errors import (
    SandboxError,
    SecurityViolationError,
    TimeoutError,
    MemoryExceededError,
    SandboxNotReadyError,
    DockerNotAvailableError,
    ErrorClassifier,
)

from .formatter import ResultFormatter, OutputTruncator
from .logger import ExecutionLogger, ExecutionAuditLog
from .monitor import ExecutionMonitor, TimeoutManager, HealthChecker, ResourceSnapshot
from .cleanup import TempFileManager, ContainerCleaner, ResourceCleaner


__all__ = [
    # 数据模型
    'ExecutionStatus',
    'ExecutionResult',
    'ExecutionRequest',
    'SandboxConfig',
    'ExecutionMetrics',
    'ResourceSnapshot',
    
    # 沙箱类
    'BaseSandbox',
    'LocalSandbox',
    'DockerSandbox',
    
    # 工厂和快捷函数
    'SandboxFactory',
    'create_sandbox',
    'quick_execute',
    
    # 安全
    'SecurityChecker',
    'ResourceLimiter',
    
    # 错误
    'SandboxError',
    'SecurityViolationError',
    'TimeoutError',
    'MemoryExceededError',
    'SandboxNotReadyError',
    'DockerNotAvailableError',
    'ErrorClassifier',
    
    # 格式化
    'ResultFormatter',
    'OutputTruncator',
    
    # 日志
    'ExecutionLogger',
    'ExecutionAuditLog',
    
    # 监控
    'ExecutionMonitor',
    'TimeoutManager',
    'HealthChecker',
    
    # 清理
    'TempFileManager',
    'ContainerCleaner',
    'ResourceCleaner',
]

