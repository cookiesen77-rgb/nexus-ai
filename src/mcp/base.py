"""
MCP 基础类定义

定义 MCP 服务器、工具和资源的基类
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union

logger = logging.getLogger(__name__)


class MCPServerStatus(Enum):
    """MCP 服务器状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]
    server_name: str = ""
    
    def to_openai_schema(self) -> Dict[str, Any]:
        """转换为 OpenAI 工具格式"""
        return {
            "type": "function",
            "function": {
                "name": f"mcp_{self.server_name}_{self.name}" if self.server_name else self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
    
    def to_gemini_schema(self) -> Dict[str, Any]:
        """转换为 Gemini 工具格式"""
        return {
            "name": f"mcp_{self.server_name}_{self.name}" if self.server_name else self.name,
            "description": self.description,
            "parameters": self.parameters
        }


@dataclass
class MCPResource:
    """MCP 资源定义"""
    uri: str
    name: str
    description: str = ""
    mime_type: str = "text/plain"
    server_name: str = ""


@dataclass
class MCPServerConfig:
    """MCP 服务器配置"""
    name: str
    type: str  # local, http, stdio 等
    command: Optional[str] = None  # stdio 类型使用
    args: List[str] = field(default_factory=list)
    url: Optional[str] = None  # http/websocket 类型使用
    api_key: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None
    enabled: bool = True


class MCPServer(ABC):
    """MCP 服务器基类"""
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.name = config.name
        self.status = MCPServerStatus.DISCONNECTED
        self._tools: List[MCPTool] = []
        self._resources: List[MCPResource] = []
        self._process = None
    
    @property
    def tools(self) -> List[MCPTool]:
        """获取服务器提供的工具列表"""
        return self._tools
    
    @property
    def resources(self) -> List[MCPResource]:
        """获取服务器提供的资源列表"""
        return self._resources
    
    @abstractmethod
    async def connect(self) -> bool:
        """连接到服务器"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """断开连接"""
        pass
    
    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用工具"""
        pass
    
    @abstractmethod
    async def read_resource(self, uri: str) -> Any:
        """读取资源"""
        pass
    
    def register_tool(self, tool: MCPTool):
        """注册工具"""
        tool.server_name = self.name
        self._tools.append(tool)
    
    def register_resource(self, resource: MCPResource):
        """注册资源"""
        resource.server_name = self.name
        self._resources.append(resource)
    
    def get_tool(self, name: str) -> Optional[MCPTool]:
        """获取指定工具"""
        for tool in self._tools:
            if tool.name == name:
                return tool
        return None
    
    def __repr__(self):
        return f"MCPServer(name={self.name}, status={self.status.value}, tools={len(self._tools)})"


class LocalMCPServer(MCPServer):
    """本地 MCP 服务器基类（不需要外部进程）"""
    
    async def connect(self) -> bool:
        """连接（本地服务器直接就绪）"""
        self.status = MCPServerStatus.CONNECTED
        logger.info(f"本地 MCP 服务器 {self.name} 已就绪")
        return True
    
    async def disconnect(self):
        """断开连接"""
        self.status = MCPServerStatus.DISCONNECTED
        logger.info(f"本地 MCP 服务器 {self.name} 已断开")
    
    async def read_resource(self, uri: str) -> Any:
        """读取资源（默认实现）"""
        return {"error": f"服务器 {self.name} 不支持资源读取"}


class HTTPMCPServer(MCPServer):
    """HTTP MCP 服务器"""
    
    def __init__(self, config: MCPServerConfig):
        super().__init__(config)
        self.base_url = config.url
        self.api_key = config.api_key
        self._client = None
    
    async def connect(self) -> bool:
        """连接到 HTTP 服务器"""
        import httpx
        
        try:
            self.status = MCPServerStatus.CONNECTING
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
                timeout=30.0
            )
            
            # 尝试获取工具列表
            response = await self._client.get("/tools")
            if response.status_code == 200:
                tools_data = response.json()
                for tool_data in tools_data.get("tools", []):
                    self.register_tool(MCPTool(
                        name=tool_data["name"],
                        description=tool_data.get("description", ""),
                        parameters=tool_data.get("parameters", {})
                    ))
            
            self.status = MCPServerStatus.CONNECTED
            logger.info(f"HTTP MCP 服务器 {self.name} 已连接，工具数: {len(self._tools)}")
            return True
            
        except Exception as e:
            self.status = MCPServerStatus.ERROR
            logger.error(f"连接 HTTP MCP 服务器 {self.name} 失败: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self._client:
            await self._client.aclose()
            self._client = None
        self.status = MCPServerStatus.DISCONNECTED
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用工具"""
        if not self._client:
            return {"error": "服务器未连接"}
        
        try:
            response = await self._client.post(
                f"/tools/{tool_name}",
                json=arguments
            )
            return response.json()
        except Exception as e:
            logger.error(f"调用工具 {tool_name} 失败: {e}")
            return {"error": str(e)}
    
    async def read_resource(self, uri: str) -> Any:
        """读取资源"""
        if not self._client:
            return {"error": "服务器未连接"}
        
        try:
            response = await self._client.get(f"/resources/{uri}")
            return response.json()
        except Exception as e:
            logger.error(f"读取资源 {uri} 失败: {e}")
            return {"error": str(e)}

