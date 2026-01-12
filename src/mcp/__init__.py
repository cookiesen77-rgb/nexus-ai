"""
MCP (Model Context Protocol) 模块

提供 MCP 服务器集成功能，允许 Nexus AI 连接到各种外部工具和服务。

支持的 MCP 服务器类型：
- web_search: 网络搜索 (Brave Search, Google)
- filesystem: 文件系统操作
- fetch: HTTP 请求
- memory: 记忆存储
- browser: 浏览器自动化
- database: 数据库操作
"""

from .base import MCPServer, MCPTool, MCPResource
from .client import MCPClient
from .registry import MCPRegistry, get_mcp_registry

__all__ = [
    "MCPServer",
    "MCPTool",
    "MCPResource",
    "MCPClient",
    "MCPRegistry",
    "get_mcp_registry",
]

