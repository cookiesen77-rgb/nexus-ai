"""
工具注册器

管理和调度所有可用工具
"""

from typing import Any, Callable, Dict, List, Optional

from src.utils import info, warning, error
from .base import BaseTool, ToolResult, ToolStatus


class ToolRegistry:
    """工具注册器"""

    def __init__(self):
        """初始化注册器"""
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """
        注册工具

        Args:
            tool: 工具实例
        """
        if tool.name in self._tools:
            warning(f"工具 '{tool.name}' 已存在，将被覆盖")

        self._tools[tool.name] = tool
        info(f"注册工具: {tool.name}")

    def unregister(self, name: str) -> bool:
        """
        注销工具

        Args:
            name: 工具名称

        Returns:
            bool: 是否成功注销
        """
        if name in self._tools:
            del self._tools[name]
            info(f"注销工具: {name}")
            return True
        return False

    def get(self, name: str) -> Optional[BaseTool]:
        """
        获取工具

        Args:
            name: 工具名称

        Returns:
            Optional[BaseTool]: 工具实例
        """
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """
        检查工具是否存在

        Args:
            name: 工具名称

        Returns:
            bool: 是否存在
        """
        return name in self._tools

    def list_all(self) -> List[BaseTool]:
        """
        列出所有工具

        Returns:
            List[BaseTool]: 工具列表
        """
        return list(self._tools.values())

    def list_names(self) -> List[str]:
        """
        列出所有工具名称

        Returns:
            List[str]: 工具名称列表
        """
        return list(self._tools.keys())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """
        获取所有工具的Schema

        Returns:
            List[Dict]: Schema列表（Claude格式）
        """
        return [tool.to_schema() for tool in self._tools.values()]

    def get_openai_schemas(self) -> List[Dict[str, Any]]:
        """
        获取所有工具的OpenAI格式Schema

        Returns:
            List[Dict]: Schema列表（OpenAI格式）
        """
        return [tool.to_openai_schema() for tool in self._tools.values()]

    async def execute(self, name: str, **kwargs) -> ToolResult:
        """
        执行工具

        Args:
            name: 工具名称
            **kwargs: 工具参数

        Returns:
            ToolResult: 执行结果
        """
        tool = self.get(name)
        if tool is None:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=f"Tool '{name}' not found"
            )

        return await tool.run(**kwargs)

    def create_executor(self) -> Callable:
        """
        创建工具执行器函数

        Returns:
            Callable: 异步执行器函数
        """
        async def executor(name: str, params: Dict[str, Any]) -> Any:
            result = await self.execute(name, **params)
            if result.is_success:
                return result.output
            raise Exception(result.error)

        return executor

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __iter__(self):
        return iter(self._tools.values())


# 全局工具注册器实例
_global_registry: Optional[ToolRegistry] = None


def get_global_registry() -> ToolRegistry:
    """获取全局工具注册器"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def register_tool(tool: BaseTool) -> None:
    """注册工具到全局注册器"""
    get_global_registry().register(tool)


def get_tool(name: str) -> Optional[BaseTool]:
    """从全局注册器获取工具"""
    return get_global_registry().get(name)


def list_tools() -> List[str]:
    """列出全局注册器中的所有工具"""
    return get_global_registry().list_names()


async def execute_tool(name: str, **kwargs) -> ToolResult:
    """使用全局注册器执行工具"""
    return await get_global_registry().execute(name, **kwargs)

