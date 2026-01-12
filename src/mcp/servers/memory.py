"""
Memory MCP 服务器

提供记忆存储功能，用于保存和检索对话上下文、用户偏好等信息
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import LocalMCPServer, MCPServerConfig, MCPTool

logger = logging.getLogger(__name__)


class MemoryServer(LocalMCPServer):
    """记忆存储 MCP 服务器"""
    
    def __init__(self, config: MCPServerConfig):
        super().__init__(config)
        
        # 存储路径
        workspace = os.environ.get("WORKSPACE_PATH", os.getcwd())
        self.memory_dir = Path(workspace) / ".nexus" / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # 内存缓存
        self._memories: Dict[str, Dict[str, Any]] = {}
        self._load_memories()
        
        # 注册工具
        self.register_tool(MCPTool(
            name="store_memory",
            description="存储一条记忆，可用于保存重要信息、用户偏好或对话上下文",
            parameters={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "记忆的唯一标识符"
                    },
                    "content": {
                        "type": "string",
                        "description": "要存储的内容"
                    },
                    "category": {
                        "type": "string",
                        "description": "记忆类别，如 'preference', 'fact', 'task', 'context'",
                        "default": "general"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "标签列表，用于检索"
                    },
                    "expires_in": {
                        "type": "integer",
                        "description": "过期时间（秒），0 表示永不过期",
                        "default": 0
                    }
                },
                "required": ["key", "content"]
            }
        ))
        
        self.register_tool(MCPTool(
            name="retrieve_memory",
            description="检索记忆",
            parameters={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "记忆的唯一标识符"
                    }
                },
                "required": ["key"]
            }
        ))
        
        self.register_tool(MCPTool(
            name="search_memories",
            description="搜索记忆",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "category": {
                        "type": "string",
                        "description": "限制在特定类别中搜索"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "按标签过滤"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回结果数量限制",
                        "default": 10
                    }
                },
                "required": []
            }
        ))
        
        self.register_tool(MCPTool(
            name="delete_memory",
            description="删除记忆",
            parameters={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "记忆的唯一标识符"
                    }
                },
                "required": ["key"]
            }
        ))
        
        self.register_tool(MCPTool(
            name="list_memories",
            description="列出所有记忆",
            parameters={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "按类别过滤"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量限制",
                        "default": 50
                    }
                },
                "required": []
            }
        ))
    
    def _load_memories(self):
        """加载已保存的记忆"""
        memory_file = self.memory_dir / "memories.json"
        if memory_file.exists():
            try:
                with open(memory_file, "r", encoding="utf-8") as f:
                    self._memories = json.load(f)
                logger.info(f"加载了 {len(self._memories)} 条记忆")
            except Exception as e:
                logger.error(f"加载记忆失败: {e}")
                self._memories = {}
    
    def _save_memories(self):
        """保存记忆到文件"""
        memory_file = self.memory_dir / "memories.json"
        try:
            with open(memory_file, "w", encoding="utf-8") as f:
                json.dump(self._memories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存记忆失败: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用记忆工具"""
        handlers = {
            "store_memory": self._store_memory,
            "retrieve_memory": self._retrieve_memory,
            "search_memories": self._search_memories,
            "delete_memory": self._delete_memory,
            "list_memories": self._list_memories,
        }
        
        handler = handlers.get(tool_name)
        if handler:
            return await handler(**arguments)
        return {"error": f"未知工具: {tool_name}"}
    
    async def _store_memory(
        self,
        key: str,
        content: str,
        category: str = "general",
        tags: Optional[List[str]] = None,
        expires_in: int = 0
    ) -> Dict[str, Any]:
        """存储记忆"""
        now = datetime.now().isoformat()
        
        memory = {
            "key": key,
            "content": content,
            "category": category,
            "tags": tags or [],
            "created_at": now,
            "updated_at": now,
            "expires_at": None
        }
        
        if expires_in > 0:
            from datetime import timedelta
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            memory["expires_at"] = expires_at.isoformat()
        
        self._memories[key] = memory
        self._save_memories()
        
        return {
            "success": True,
            "key": key,
            "message": f"记忆已保存: {key}"
        }
    
    async def _retrieve_memory(self, key: str) -> Dict[str, Any]:
        """检索记忆"""
        memory = self._memories.get(key)
        
        if not memory:
            return {
                "success": False,
                "error": f"未找到记忆: {key}"
            }
        
        # 检查是否过期
        if memory.get("expires_at"):
            expires_at = datetime.fromisoformat(memory["expires_at"])
            if datetime.now() > expires_at:
                del self._memories[key]
                self._save_memories()
                return {
                    "success": False,
                    "error": f"记忆已过期: {key}"
                }
        
        return {
            "success": True,
            "memory": memory
        }
    
    async def _search_memories(
        self,
        query: str = "",
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """搜索记忆"""
        results = []
        
        for key, memory in self._memories.items():
            # 检查过期
            if memory.get("expires_at"):
                expires_at = datetime.fromisoformat(memory["expires_at"])
                if datetime.now() > expires_at:
                    continue
            
            # 类别过滤
            if category and memory.get("category") != category:
                continue
            
            # 标签过滤
            if tags:
                memory_tags = memory.get("tags", [])
                if not any(tag in memory_tags for tag in tags):
                    continue
            
            # 内容搜索
            if query:
                content = memory.get("content", "").lower()
                key_lower = key.lower()
                if query.lower() not in content and query.lower() not in key_lower:
                    continue
            
            results.append(memory)
            
            if len(results) >= limit:
                break
        
        return {
            "success": True,
            "count": len(results),
            "memories": results
        }
    
    async def _delete_memory(self, key: str) -> Dict[str, Any]:
        """删除记忆"""
        if key in self._memories:
            del self._memories[key]
            self._save_memories()
            return {
                "success": True,
                "message": f"记忆已删除: {key}"
            }
        return {
            "success": False,
            "error": f"未找到记忆: {key}"
        }
    
    async def _list_memories(
        self,
        category: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """列出记忆"""
        results = []
        
        for key, memory in self._memories.items():
            # 检查过期
            if memory.get("expires_at"):
                expires_at = datetime.fromisoformat(memory["expires_at"])
                if datetime.now() > expires_at:
                    continue
            
            # 类别过滤
            if category and memory.get("category") != category:
                continue
            
            results.append({
                "key": key,
                "category": memory.get("category"),
                "tags": memory.get("tags", []),
                "created_at": memory.get("created_at"),
                "content_preview": memory.get("content", "")[:100]
            })
            
            if len(results) >= limit:
                break
        
        return {
            "success": True,
            "count": len(results),
            "memories": results
        }

