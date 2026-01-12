"""
External MCP servers (stdio-based)

Allows Nexus to connect to official Model Context Protocol stdio servers by
spawning their processes (typically `npx ...`) and speaking the MCP protocol
over stdin/stdout.
"""

from __future__ import annotations

import logging
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

import anyio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from ..base import (
    MCPResource,
    MCPServer,
    MCPServerConfig,
    MCPServerStatus,
    MCPTool,
)


logger = logging.getLogger(__name__)


class StdIOMCPServer(MCPServer):
    """Spawn an external MCP stdio server via subprocess and proxy its tools."""

    def __init__(self, config: MCPServerConfig):
        super().__init__(config)
        self._session: Optional[ClientSession] = None
        self._exit_stack: Optional[AsyncExitStack] = None

    async def connect(self) -> bool:
        if not self.config.command:
            logger.error("StdIO MCP server %s missing command", self.name)
            self.status = MCPServerStatus.ERROR
            return False

        self.status = MCPServerStatus.CONNECTING
        self._exit_stack = AsyncExitStack()

        try:
            params = StdioServerParameters(
                command=self.config.command,
                args=self.config.args,
                env=self.config.env or None,
                cwd=self.config.cwd,
            )
            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(params)
            )
            session = ClientSession(read_stream, write_stream)
            self._session = await self._exit_stack.enter_async_context(session)

            await self._session.initialize()
            await self._refresh_tools()
            await self._refresh_resources()

            self.status = MCPServerStatus.CONNECTED
            logger.info("StdIO MCP server %s connected", self.name)
            return True
        except Exception as exc:
            logger.error("连接外部 MCP 服务器 %s 失败: %s", self.name, exc, exc_info=True)
            self.status = MCPServerStatus.ERROR
            await self._cleanup()
            return False

    async def disconnect(self):
        await self._cleanup()
        self.status = MCPServerStatus.DISCONNECTED
        logger.info("StdIO MCP server %s disconnected", self.name)

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not self._session:
            return {"success": False, "error": "服务器未连接"}

        try:
            result = await self._session.call_tool(tool_name, arguments or {})
            return {
                "success": not result.isError,
                "content": [block.model_dump() for block in result.content],
                "structured": result.structuredContent,
            }
        except Exception as exc:
            logger.error("MCP 工具 %s 调用失败: %s", tool_name, exc)
            return {"success": False, "error": str(exc)}

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        if not self._session:
            return {"error": "服务器未连接"}

        try:
            result = await self._session.read_resource(uri)
            return result.model_dump()
        except Exception as exc:
            logger.error("读取 MCP 资源 %s 失败: %s", uri, exc)
            return {"error": str(exc)}

    async def _refresh_tools(self):
        if not self._session:
            return

        self._tools.clear()
        cursor: Optional[str] = None

        while True:
            result = await self._session.list_tools(cursor=cursor)
            for tool in result.tools:
                self.register_tool(
                    MCPTool(
                        name=tool.name,
                        description=tool.description or "",
                        parameters=tool.inputSchema or {"type": "object", "properties": {}},
                    )
                )
            cursor = result.nextCursor
            if not cursor:
                break

    async def _refresh_resources(self):
        if not self._session:
            return

        self._resources.clear()
        cursor: Optional[str] = None

        while True:
            try:
                result = await self._session.list_resources(cursor=cursor)
            except Exception as exc:
                logger.debug("服务器 %s 不支持资源列表: %s", self.name, exc)
                return

            for resource in result.resources:
                self.register_resource(
                    MCPResource(
                        uri=str(resource.uri),
                        name=resource.name or str(resource.uri),
                        description=resource.description or "",
                        mime_type=resource.mimeType or "text/plain",
                    )
                )
            cursor = result.nextCursor
            if not cursor:
                break

    async def _cleanup(self):
        if self._exit_stack:
            with anyio.CancelScope(shield=True):
                await self._exit_stack.aclose()
            self._exit_stack = None
        self._session = None

