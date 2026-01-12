"""
执行结果数据模型
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class ExecutionStatus(str, Enum):
    """执行状态"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    MEMORY_EXCEEDED = "memory_exceeded"
    SECURITY_VIOLATION = "security_violation"
    CANCELLED = "cancelled"


class ExecutionResult(BaseModel):
    """代码执行结果"""
    status: ExecutionStatus
    output: str = ""
    error: Optional[str] = None
    return_value: Optional[Any] = None
    execution_time: float = 0.0  # 秒
    memory_used: int = 0  # 字节
    exit_code: int = 0
    
    # 元数据
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    sandbox_type: str = "unknown"
    
    @property
    def is_success(self) -> bool:
        return self.status == ExecutionStatus.SUCCESS
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "return_value": self.return_value,
            "execution_time": self.execution_time,
            "memory_used": self.memory_used,
            "exit_code": self.exit_code,
            "sandbox_type": self.sandbox_type
        }


class ExecutionRequest(BaseModel):
    """代码执行请求"""
    code: str
    language: str = "python"
    timeout: int = Field(default=60, ge=1, le=300)  # 1-300秒
    memory_limit: int = Field(default=512 * 1024 * 1024, ge=0)  # 字节，默认512MB
    
    # 可选参数
    working_dir: Optional[str] = None
    env_vars: Dict[str, str] = Field(default_factory=dict)
    input_data: Optional[str] = None  # stdin输入
    
    # 安全选项
    network_enabled: bool = False
    filesystem_access: str = "restricted"  # none, restricted, full


class SandboxConfig(BaseModel):
    """沙箱配置"""
    sandbox_type: str = "local"  # local, docker, e2b
    
    # Docker配置
    docker_image: str = "python:3.11-slim"
    docker_network: str = "none"
    
    # 资源限制
    default_timeout: int = 60
    default_memory_limit: int = 512 * 1024 * 1024
    default_cpu_limit: float = 1.0
    
    # 安全配置
    allowed_imports: List[str] = Field(default_factory=lambda: [
        "math", "json", "re", "datetime", "time",
        "collections", "itertools", "functools", "operator",
        "string", "random", "hashlib", "base64",
        "pandas", "numpy", "statistics"
    ])
    
    blocked_patterns: List[str] = Field(default_factory=lambda: [
        r"subprocess", r"os\.system", r"os\.popen",
        r"eval\s*\(", r"exec\s*\(", r"compile\s*\(",
        r"__import__", r"importlib",
        r"open\s*\(", r"file\s*\(",
        r"socket", r"urllib", r"requests", r"httpx"
    ])
    
    # 文件系统
    temp_dir: str = "/tmp/sandbox"
    max_file_size: int = 10 * 1024 * 1024  # 10MB


class ExecutionMetrics(BaseModel):
    """执行指标"""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    timeout_executions: int = 0
    
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    max_execution_time: float = 0.0
    
    total_memory_used: int = 0
    average_memory_used: int = 0
    max_memory_used: int = 0
    
    def update(self, result: ExecutionResult):
        """更新指标"""
        self.total_executions += 1
        self.total_execution_time += result.execution_time
        self.total_memory_used += result.memory_used
        
        if result.is_success:
            self.successful_executions += 1
        elif result.status == ExecutionStatus.TIMEOUT:
            self.timeout_executions += 1
        else:
            self.failed_executions += 1
        
        # 更新平均值
        if self.total_executions > 0:
            self.average_execution_time = self.total_execution_time / self.total_executions
            self.average_memory_used = self.total_memory_used // self.total_executions
        
        # 更新最大值
        self.max_execution_time = max(self.max_execution_time, result.execution_time)
        self.max_memory_used = max(self.max_memory_used, result.memory_used)

