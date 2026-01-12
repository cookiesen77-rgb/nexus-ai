"""
MCP 客户端

管理与 MCP 服务器的通信
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from .base import MCPServer, MCPTool, MCPResource, MCPServerStatus

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP 客户端 - 管理多个 MCP 服务器"""
    
    def __init__(self):
        self._servers: Dict[str, MCPServer] = {}
        self._tool_map: Dict[str, MCPServer] = {}  # tool_name -> server
    
    def add_server(self, server: MCPServer):
        """添加 MCP 服务器"""
        self._servers[server.name] = server
        # 更新工具映射
        for tool in server.tools:
            full_name = f"mcp_{server.name}_{tool.name}"
            self._tool_map[full_name] = server
    
    def remove_server(self, name: str):
        """移除 MCP 服务器"""
        if name in self._servers:
            server = self._servers[name]
            # 移除工具映射
            for tool in server.tools:
                full_name = f"mcp_{server.name}_{tool.name}"
                if full_name in self._tool_map:
                    del self._tool_map[full_name]
            del self._servers[name]
    
    def get_server(self, name: str) -> Optional[MCPServer]:
        """获取服务器"""
        return self._servers.get(name)
    
    @property
    def servers(self) -> List[MCPServer]:
        """获取所有服务器"""
        return list(self._servers.values())
    
    @property
    def connected_servers(self) -> List[MCPServer]:
        """获取已连接的服务器"""
        return [s for s in self._servers.values() if s.status == MCPServerStatus.CONNECTED]
    
    async def connect_all(self):
        """连接所有服务器"""
        tasks = [server.connect() for server in self._servers.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for server, result in zip(self._servers.values(), results):
            if isinstance(result, Exception):
                logger.error(f"连接服务器 {server.name} 失败: {result}")
            elif result:
                # 更新工具映射
                for tool in server.tools:
                    full_name = f"mcp_{server.name}_{tool.name}"
                    self._tool_map[full_name] = server
    
    async def disconnect_all(self):
        """断开所有服务器"""
        tasks = [server.disconnect() for server in self._servers.values()]
        await asyncio.gather(*tasks, return_exceptions=True)
        self._tool_map.clear()
    
    def get_all_tools(self) -> List[MCPTool]:
        """获取所有可用工具"""
        tools = []
        for server in self.connected_servers:
            tools.extend(server.tools)
        return tools
    
    def get_tools_schemas(self, format: str = "openai") -> List[Dict[str, Any]]:
        """获取所有工具的 schema"""
        schemas = []
        for tool in self.get_all_tools():
            if format == "openai":
                schemas.append(tool.to_openai_schema())
            elif format == "gemini":
                schemas.append(tool.to_gemini_schema())
        return schemas
    
    def get_all_resources(self) -> List[MCPResource]:
        """获取所有可用资源"""
        resources = []
        for server in self.connected_servers:
            resources.extend(server.resources)
        return resources
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        调用 MCP 工具
        
        Args:
            tool_name: 完整工具名 (mcp_{server}_{tool})
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        # 查找工具对应的服务器
        server = self._tool_map.get(tool_name)
        if not server:
            return {"error": f"工具 {tool_name} 未找到"}
        
        if server.status != MCPServerStatus.CONNECTED:
            return {"error": f"服务器 {server.name} 未连接"}
        
        # 解析实际的工具名
        # mcp_{server}_{tool} -> tool
        prefix = f"mcp_{server.name}_"
        if tool_name.startswith(prefix):
            actual_tool_name = tool_name[len(prefix):]
        else:
            actual_tool_name = tool_name
        
        logger.info(f"调用 MCP 工具: {server.name}.{actual_tool_name}")
        return await server.call_tool(actual_tool_name, arguments)
    
    async def read_resource(self, uri: str, server_name: Optional[str] = None) -> Any:
        """
        读取 MCP 资源
        
        Args:
            uri: 资源 URI
            server_name: 可选的服务器名称
            
        Returns:
            资源内容
        """
        if server_name:
            server = self._servers.get(server_name)
            if server and server.status == MCPServerStatus.CONNECTED:
                return await server.read_resource(uri)
            return {"error": f"服务器 {server_name} 不可用"}
        
        # 尝试所有服务器
        for server in self.connected_servers:
            try:
                result = await server.read_resource(uri)
                if not isinstance(result, dict) or "error" not in result:
                    return result
            except Exception:
                continue
        
        return {"error": f"无法读取资源 {uri}"}
    
    def is_mcp_tool(self, tool_name: str) -> bool:
        """检查是否是 MCP 工具"""
        return tool_name.startswith("mcp_") and tool_name in self._tool_map
    
    def __repr__(self):
        connected = len(self.connected_servers)
        total = len(self._servers)
        tools = len(self.get_all_tools())
        return f"MCPClient(servers={connected}/{total}, tools={tools})"

