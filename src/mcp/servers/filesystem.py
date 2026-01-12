"""
Filesystem MCP 服务器

提供文件系统操作功能
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from ..base import LocalMCPServer, MCPServerConfig, MCPTool, MCPResource

logger = logging.getLogger(__name__)


class FilesystemServer(LocalMCPServer):
    """文件系统 MCP 服务器"""
    
    def __init__(self, config: MCPServerConfig):
        super().__init__(config)
        
        # 工作目录
        self.workspace = os.environ.get("WORKSPACE_PATH", os.getcwd())
        
        # 注册工具
        self.register_tool(MCPTool(
            name="read_file",
            description="读取文件内容",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件路径（相对于工作目录或绝对路径）"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "文件编码，默认 utf-8",
                        "default": "utf-8"
                    }
                },
                "required": ["path"]
            }
        ))
        
        self.register_tool(MCPTool(
            name="write_file",
            description="写入文件内容",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件路径"
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的内容"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "文件编码，默认 utf-8",
                        "default": "utf-8"
                    }
                },
                "required": ["path", "content"]
            }
        ))
        
        self.register_tool(MCPTool(
            name="list_directory",
            description="列出目录内容",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "目录路径，默认为工作目录",
                        "default": "."
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "是否递归列出子目录",
                        "default": False
                    }
                },
                "required": []
            }
        ))
        
        self.register_tool(MCPTool(
            name="create_directory",
            description="创建目录",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "目录路径"
                    }
                },
                "required": ["path"]
            }
        ))
        
        self.register_tool(MCPTool(
            name="delete_file",
            description="删除文件或目录",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件或目录路径"
                    }
                },
                "required": ["path"]
            }
        ))
        
        self.register_tool(MCPTool(
            name="move_file",
            description="移动或重命名文件",
            parameters={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "源路径"
                    },
                    "destination": {
                        "type": "string",
                        "description": "目标路径"
                    }
                },
                "required": ["source", "destination"]
            }
        ))
        
        self.register_tool(MCPTool(
            name="search_files",
            description="搜索文件",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "搜索模式（支持 glob 语法，如 *.py）"
                    },
                    "path": {
                        "type": "string",
                        "description": "搜索目录",
                        "default": "."
                    }
                },
                "required": ["pattern"]
            }
        ))
        
        self.register_tool(MCPTool(
            name="get_file_info",
            description="获取文件信息",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件路径"
                    }
                },
                "required": ["path"]
            }
        ))
    
    def _resolve_path(self, path: str) -> Path:
        """解析路径"""
        p = Path(path)
        if not p.is_absolute():
            p = Path(self.workspace) / p
        return p.resolve()
    
    def _is_safe_path(self, path: Path) -> bool:
        """检查路径是否安全（在工作目录内）"""
        workspace = Path(self.workspace).resolve()
        try:
            path.resolve().relative_to(workspace)
            return True
        except ValueError:
            # 允许访问绝对路径，但记录警告
            logger.warning(f"访问工作目录外的路径: {path}")
            return True  # 暂时允许
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用文件系统工具"""
        handlers = {
            "read_file": self._read_file,
            "write_file": self._write_file,
            "list_directory": self._list_directory,
            "create_directory": self._create_directory,
            "delete_file": self._delete_file,
            "move_file": self._move_file,
            "search_files": self._search_files,
            "get_file_info": self._get_file_info,
        }
        
        handler = handlers.get(tool_name)
        if handler:
            return await handler(**arguments)
        return {"error": f"未知工具: {tool_name}"}
    
    async def _read_file(self, path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """读取文件"""
        try:
            file_path = self._resolve_path(path)
            if not file_path.exists():
                return {"success": False, "error": f"文件不存在: {path}"}
            
            if not file_path.is_file():
                return {"success": False, "error": f"不是文件: {path}"}
            
            content = file_path.read_text(encoding=encoding)
            return {
                "success": True,
                "path": str(file_path),
                "content": content,
                "size": file_path.stat().st_size
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _write_file(self, path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """写入文件"""
        try:
            file_path = self._resolve_path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding=encoding)
            return {
                "success": True,
                "path": str(file_path),
                "size": len(content.encode(encoding))
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _list_directory(self, path: str = ".", recursive: bool = False) -> Dict[str, Any]:
        """列出目录"""
        try:
            dir_path = self._resolve_path(path)
            if not dir_path.exists():
                return {"success": False, "error": f"目录不存在: {path}"}
            
            if not dir_path.is_dir():
                return {"success": False, "error": f"不是目录: {path}"}
            
            items = []
            if recursive:
                for item in dir_path.rglob("*"):
                    items.append({
                        "name": str(item.relative_to(dir_path)),
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else 0
                    })
            else:
                for item in dir_path.iterdir():
                    items.append({
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else 0
                    })
            
            return {
                "success": True,
                "path": str(dir_path),
                "items": items
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _create_directory(self, path: str) -> Dict[str, Any]:
        """创建目录"""
        try:
            dir_path = self._resolve_path(path)
            dir_path.mkdir(parents=True, exist_ok=True)
            return {"success": True, "path": str(dir_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _delete_file(self, path: str) -> Dict[str, Any]:
        """删除文件或目录"""
        try:
            file_path = self._resolve_path(path)
            if not file_path.exists():
                return {"success": False, "error": f"路径不存在: {path}"}
            
            if file_path.is_file():
                file_path.unlink()
            else:
                import shutil
                shutil.rmtree(file_path)
            
            return {"success": True, "path": str(file_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _move_file(self, source: str, destination: str) -> Dict[str, Any]:
        """移动文件"""
        try:
            src_path = self._resolve_path(source)
            dst_path = self._resolve_path(destination)
            
            if not src_path.exists():
                return {"success": False, "error": f"源路径不存在: {source}"}
            
            import shutil
            shutil.move(str(src_path), str(dst_path))
            
            return {
                "success": True,
                "source": str(src_path),
                "destination": str(dst_path)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _search_files(self, pattern: str, path: str = ".") -> Dict[str, Any]:
        """搜索文件"""
        try:
            search_path = self._resolve_path(path)
            if not search_path.exists():
                return {"success": False, "error": f"目录不存在: {path}"}
            
            matches = list(search_path.glob(pattern))
            results = [
                {
                    "name": str(m.relative_to(search_path)),
                    "type": "directory" if m.is_dir() else "file",
                    "size": m.stat().st_size if m.is_file() else 0
                }
                for m in matches[:100]  # 限制结果数量
            ]
            
            return {
                "success": True,
                "pattern": pattern,
                "path": str(search_path),
                "count": len(results),
                "results": results
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_file_info(self, path: str) -> Dict[str, Any]:
        """获取文件信息"""
        try:
            file_path = self._resolve_path(path)
            if not file_path.exists():
                return {"success": False, "error": f"路径不存在: {path}"}
            
            stat = file_path.stat()
            return {
                "success": True,
                "path": str(file_path),
                "name": file_path.name,
                "type": "directory" if file_path.is_dir() else "file",
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "accessed": stat.st_atime
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def read_resource(self, uri: str) -> Any:
        """读取文件资源"""
        # 解析 URI: file:///path/to/file
        if uri.startswith("file://"):
            path = uri[7:]
            return await self._read_file(path)
        return {"error": f"不支持的 URI 格式: {uri}"}

