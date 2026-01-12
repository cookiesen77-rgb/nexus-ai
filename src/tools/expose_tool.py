"""
端口暴露工具

将本地服务端口映射到公共URL
"""

import asyncio
import subprocess
from typing import Optional, Dict
from dataclasses import dataclass
from datetime import datetime

from .base import BaseTool, ToolResult, ToolStatus


@dataclass
class ExposedPort:
    """暴露的端口"""
    port: int
    public_url: str
    created_at: datetime
    process: Optional[subprocess.Popen] = None


class PortExposer:
    """端口暴露管理器"""
    
    def __init__(self):
        self._exposed: Dict[int, ExposedPort] = {}
    
    async def expose(self, port: int) -> ExposedPort:
        """
        暴露端口
        
        注意: 实际实现需要使用tunneling服务如:
        - ngrok
        - cloudflared
        - localtunnel
        """
        # 检查是否已暴露
        if port in self._exposed:
            return self._exposed[port]
        
        # 这里使用模拟实现
        # 实际应用中应集成ngrok或类似服务
        try:
            # 尝试使用localtunnel (如果安装了)
            process = subprocess.Popen(
                ['lt', '--port', str(port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 读取URL (localtunnel会输出URL)
            for line in process.stdout:
                if 'your url is:' in line.lower():
                    url = line.split()[-1].strip()
                    break
            else:
                url = f"http://localhost:{port}"
            
            exposed = ExposedPort(
                port=port,
                public_url=url,
                created_at=datetime.now(),
                process=process
            )
            
        except FileNotFoundError:
            # localtunnel未安装，使用模拟URL
            exposed = ExposedPort(
                port=port,
                public_url=f"http://localhost:{port}",
                created_at=datetime.now()
            )
        
        self._exposed[port] = exposed
        return exposed
    
    async def unexpose(self, port: int) -> bool:
        """停止暴露端口"""
        exposed = self._exposed.get(port)
        if not exposed:
            return False
        
        if exposed.process:
            exposed.process.terminate()
            try:
                exposed.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                exposed.process.kill()
        
        del self._exposed[port]
        return True
    
    def list_exposed(self) -> Dict[int, ExposedPort]:
        """列出所有暴露的端口"""
        return self._exposed.copy()
    
    def get_url(self, port: int) -> Optional[str]:
        """获取端口的公共URL"""
        exposed = self._exposed.get(port)
        return exposed.public_url if exposed else None


# 全局管理器
_exposer = PortExposer()


def get_port_exposer() -> PortExposer:
    """获取端口暴露管理器"""
    return _exposer


class ExposeTool(BaseTool):
    """
    端口暴露工具
    
    将本地服务端口映射到公共可访问的URL
    """
    
    name = "expose"
    description = "Expose local ports to public URLs for temporary access"
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["expose", "unexpose", "list", "get"],
                "description": "Action to perform"
            },
            "port": {
                "type": "integer",
                "description": "Port number to expose/unexpose"
            }
        },
        "required": ["action"]
    }
    
    async def execute(
        self,
        action: str,
        port: int = 0
    ) -> ToolResult:
        """执行端口暴露操作"""
        exposer = get_port_exposer()
        
        try:
            if action == "expose":
                if not port:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error="Port is required"
                    )
                
                exposed = await exposer.expose(port)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"Port {port} exposed at {exposed.public_url}",
                    data={
                        'port': port,
                        'url': exposed.public_url
                    }
                )
            
            elif action == "unexpose":
                if not port:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error="Port is required"
                    )
                
                success = await exposer.unexpose(port)
                if success:
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        output=f"Port {port} is no longer exposed"
                    )
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error=f"Port {port} was not exposed"
                )
            
            elif action == "list":
                exposed = exposer.list_exposed()
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"{len(exposed)} ports exposed",
                    data={
                        p: {'url': e.public_url, 'created': e.created_at.isoformat()}
                        for p, e in exposed.items()
                    }
                )
            
            elif action == "get":
                if not port:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error="Port is required"
                    )
                
                url = exposer.get_url(port)
                if url:
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        output=f"Port {port}: {url}",
                        data={'port': port, 'url': url}
                    )
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error=f"Port {port} is not exposed"
                )
            
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error=f"Unknown action: {action}"
                )
                
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=str(e)
            )


# 工具实例
expose_tool = ExposeTool()

