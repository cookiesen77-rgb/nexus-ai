"""
WebSocket处理器

提供实时双向通信支持
"""

import asyncio
import json
from typing import Dict, Set, Optional, Callable, Any
from dataclasses import dataclass, field
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime


@dataclass
class WSClient:
    """WebSocket客户端"""
    websocket: WebSocket
    client_id: str
    connected_at: datetime = field(default_factory=datetime.now)
    subscriptions: Set[str] = field(default_factory=set)


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, WSClient] = {}
        self.message_handlers: Dict[str, Callable] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str) -> WSClient:
        """接受新连接"""
        await websocket.accept()
        client = WSClient(websocket=websocket, client_id=client_id)
        self.active_connections[client_id] = client
        return client
    
    def disconnect(self, client_id: str):
        """断开连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def send_personal(self, client_id: str, message: dict):
        """发送消息给指定客户端"""
        client = self.active_connections.get(client_id)
        if client:
            try:
                await client.websocket.send_json(message)
            except Exception:
                self.disconnect(client_id)
    
    async def broadcast(self, message: dict, exclude: Optional[Set[str]] = None):
        """广播消息给所有客户端"""
        exclude = exclude or set()
        for client_id, client in list(self.active_connections.items()):
            if client_id not in exclude:
                try:
                    await client.websocket.send_json(message)
                except Exception:
                    self.disconnect(client_id)
    
    async def broadcast_to_subscribed(self, channel: str, message: dict):
        """广播消息给订阅了特定频道的客户端"""
        for client_id, client in list(self.active_connections.items()):
            if channel in client.subscriptions:
                try:
                    await client.websocket.send_json(message)
                except Exception:
                    self.disconnect(client_id)
    
    def subscribe(self, client_id: str, channel: str):
        """订阅频道"""
        client = self.active_connections.get(client_id)
        if client:
            client.subscriptions.add(channel)
    
    def unsubscribe(self, client_id: str, channel: str):
        """取消订阅"""
        client = self.active_connections.get(client_id)
        if client:
            client.subscriptions.discard(channel)
    
    def register_handler(self, message_type: str, handler: Callable):
        """注册消息处理器"""
        self.message_handlers[message_type] = handler
    
    async def handle_message(self, client_id: str, message: dict) -> Optional[dict]:
        """处理收到的消息"""
        msg_type = message.get('type')
        action = message.get('action')
        payload = message.get('payload')
        msg_id = message.get('id')
        
        handler = self.message_handlers.get(msg_type)
        if handler:
            try:
                result = await handler(client_id, action, payload)
                return {
                    'type': msg_type,
                    'action': f'{action}_response',
                    'payload': result,
                    'id': msg_id,
                    'success': True
                }
            except Exception as e:
                return {
                    'type': msg_type,
                    'action': f'{action}_error',
                    'payload': {'error': str(e)},
                    'id': msg_id,
                    'success': False
                }
        return None
    
    @property
    def connection_count(self) -> int:
        """当前连接数"""
        return len(self.active_connections)


# 全局连接管理器
manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """获取连接管理器"""
    return manager


# 消息处理器注册
async def handle_chat_message(client_id: str, action: str, payload: Any) -> Any:
    """处理聊天消息"""
    if action == 'send':
        from src.llm import create_allapi_client
        
        client = create_allapi_client()
        messages = payload.get('messages', [])
        
        response = await client.complete(messages=messages)
        return {
            'content': response.content,
            'model': response.model
        }
    return None


async def handle_task_message(client_id: str, action: str, payload: Any) -> Any:
    """处理任务消息"""
    if action == 'create':
        # 创建任务逻辑
        return {'status': 'created'}
    elif action == 'status':
        # 获取任务状态
        return {'status': 'running'}
    return None


async def handle_file_message(client_id: str, action: str, payload: Any) -> Any:
    """处理文件消息"""
    if action == 'list':
        from src.tools import file_manager
        result = await file_manager.execute(action='list', path=payload.get('path', '/'))
        return {'files': result.output if result.is_success else []}
    elif action == 'read':
        from src.tools import file_reader
        result = await file_reader.execute(path=payload.get('path'))
        return {'content': result.output if result.is_success else ''}
    return None


async def handle_terminal_message(client_id: str, action: str, payload: Any) -> Any:
    """处理终端消息"""
    if action == 'execute':
        from src.tools import shell
        result = await shell.execute(command=payload.get('command', ''))
        return {
            'output': result.output if result.is_success else result.error,
            'success': result.is_success
        }
    return None


async def handle_browser_message(client_id: str, action: str, payload: Any) -> Any:
    """处理浏览器消息"""
    # 浏览器工具将在Phase 5实现
    return {'status': 'not_implemented'}


# 注册处理器
manager.register_handler('chat', handle_chat_message)
manager.register_handler('task', handle_task_message)
manager.register_handler('file', handle_file_message)
manager.register_handler('terminal', handle_terminal_message)
manager.register_handler('browser', handle_browser_message)

