"""
MCP 服务器注册表

管理所有 MCP 服务器的注册和初始化
"""

import logging
from typing import Dict, List, Optional, Type

from .base import MCPServer, MCPServerConfig, LocalMCPServer, HTTPMCPServer
from .client import MCPClient

logger = logging.getLogger(__name__)


class MCPRegistry:
    """MCP 服务器注册表"""
    
    _instance: Optional["MCPRegistry"] = None
    
    def __init__(self):
        self._server_classes: Dict[str, Type[MCPServer]] = {}
        self._client = MCPClient()
        self._initialized = False
    
    @classmethod
    def get_instance(cls) -> "MCPRegistry":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = MCPRegistry()
        return cls._instance
    
    def register_server_class(self, name: str, server_class: Type[MCPServer]):
        """注册服务器类"""
        self._server_classes[name] = server_class
        logger.debug(f"注册 MCP 服务器类: {name}")
    
    def create_server(self, config: MCPServerConfig) -> Optional[MCPServer]:
        """根据配置创建服务器实例"""
        server_class = self._server_classes.get(config.type)
        if not server_class:
            logger.warning(f"未知的 MCP 服务器类型: {config.type}")
            return None
        
        try:
            server = server_class(config)
            return server
        except Exception as e:
            logger.error(f"创建 MCP 服务器 {config.name} 失败: {e}")
            return None
    
    async def initialize_servers(self, configs: List[MCPServerConfig]):
        """初始化所有服务器"""
        if self._initialized:
            logger.warning("MCP 服务器已初始化")
            return
        
        for config in configs:
            if not config.enabled:
                logger.info(f"跳过禁用的 MCP 服务器: {config.name}")
                continue
            
            server = self.create_server(config)
            if server:
                self._client.add_server(server)
        
        # 连接所有服务器
        await self._client.connect_all()
        self._initialized = True
        
        logger.info(f"MCP 初始化完成: {self._client}")
    
    async def shutdown(self):
        """关闭所有服务器"""
        await self._client.disconnect_all()
        self._initialized = False
    
    @property
    def client(self) -> MCPClient:
        """获取 MCP 客户端"""
        return self._client
    
    def get_all_tools(self):
        """获取所有 MCP 工具"""
        return self._client.get_all_tools()
    
    def get_tools_schemas(self, format: str = "openai"):
        """获取所有工具 schema"""
        return self._client.get_tools_schemas(format)
    
    async def call_tool(self, tool_name: str, arguments: dict):
        """调用 MCP 工具"""
        return await self._client.call_tool(tool_name, arguments)
    
    def is_mcp_tool(self, tool_name: str) -> bool:
        """检查是否是 MCP 工具"""
        return self._client.is_mcp_tool(tool_name)


# 全局注册表实例
_registry: Optional[MCPRegistry] = None


def get_mcp_registry() -> MCPRegistry:
    """获取全局 MCP 注册表"""
    global _registry
    if _registry is None:
        _registry = MCPRegistry.get_instance()
    return _registry


def setup_default_mcp_servers():
    """设置默认的 MCP 服务器"""
    registry = get_mcp_registry()
    
    # 注册服务器类型
    registry.register_server_class("local", LocalMCPServer)
    registry.register_server_class("http", HTTPMCPServer)
    
    # 注册内置服务器
    from .servers import (
        WebSearchServer,
        FilesystemServer,
        FetchServer,
        MemoryServer,
        BrowserServer,
        StdIOMCPServer,
    )
    
    registry.register_server_class("web_search", WebSearchServer)
    registry.register_server_class("filesystem", FilesystemServer)
    registry.register_server_class("fetch", FetchServer)
    registry.register_server_class("memory", MemoryServer)
    registry.register_server_class("browser", BrowserServer)
    registry.register_server_class("stdio", StdIOMCPServer)
    
    return registry

