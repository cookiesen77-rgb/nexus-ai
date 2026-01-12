"""
工具基类定义

定义所有工具的通用接口和基础功能
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum


class ToolStatus(Enum):
    """工具状态"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class ToolResult:
    """工具执行结果"""
    status: ToolStatus
    output: Any
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status == ToolStatus.SUCCESS

    def to_string(self) -> str:
        """转换为字符串格式"""
        if self.is_success:
            return str(self.output)
        return f"Error: {self.error}"


class BaseTool(ABC):
    """工具基类"""

    # 工具名称
    name: str = "base_tool"

    # 工具描述
    description: str = "A base tool"

    # 参数Schema
    parameters: Dict[str, Any] = {}

    def __init__(self):
        """初始化工具"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            ToolResult: 执行结果
        """
        pass

    def validate_parameters(self, **kwargs) -> Optional[str]:
        """
        验证参数

        Args:
            **kwargs: 待验证的参数

        Returns:
            Optional[str]: 错误信息，如果验证通过返回None
        """
        required = self.parameters.get("required", [])
        properties = self.parameters.get("properties", {})

        # 检查必需参数
        for param in required:
            if param not in kwargs:
                return f"Missing required parameter: {param}"

        # 检查参数类型
        for param, value in kwargs.items():
            if param in properties:
                expected_type = properties[param].get("type")
                if expected_type and not self._check_type(value, expected_type):
                    return f"Invalid type for parameter '{param}': expected {expected_type}"

        return None

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """检查参数类型"""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict
        }

        expected = type_map.get(expected_type)
        if expected is None:
            return True

        return isinstance(value, expected)

    async def run(self, **kwargs) -> ToolResult:
        """
        运行工具（带参数验证和计时）

        Args:
            **kwargs: 工具参数

        Returns:
            ToolResult: 执行结果
        """
        # 验证参数
        error = self.validate_parameters(**kwargs)
        if error:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=error
            )

        # 记录开始时间
        start_time = datetime.now()

        try:
            # 执行工具
            result = await self.execute(**kwargs)

            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            result.execution_time_ms = execution_time

            return result

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=str(e),
                execution_time_ms=execution_time
            )

    def to_schema(self) -> Dict[str, Any]:
        """
        转换为LLM工具调用Schema格式

        Returns:
            Dict: Claude/Anthropic格式的工具Schema
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                **self.parameters
            }
        }

    def to_openai_schema(self) -> Dict[str, Any]:
        """
        转换为OpenAI工具调用Schema格式

        Returns:
            Dict: OpenAI格式的工具Schema
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    **self.parameters
                }
            }
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"
