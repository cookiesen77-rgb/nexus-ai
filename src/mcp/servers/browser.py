"""
Browser MCP 服务器

提供浏览器自动化功能
"""

import logging
from typing import Any, Dict, Optional

from ..base import LocalMCPServer, MCPServerConfig, MCPTool

logger = logging.getLogger(__name__)


class BrowserServer(LocalMCPServer):
    """浏览器自动化 MCP 服务器"""
    
    def __init__(self, config: MCPServerConfig):
        super().__init__(config)
        self._browser = None
        self._page = None
        
        # 注册工具
        self.register_tool(MCPTool(
            name="navigate",
            description="导航到指定 URL",
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "目标 URL"
                    },
                    "wait_until": {
                        "type": "string",
                        "description": "等待条件: load, domcontentloaded, networkidle",
                        "enum": ["load", "domcontentloaded", "networkidle"],
                        "default": "load"
                    }
                },
                "required": ["url"]
            }
        ))
        
        self.register_tool(MCPTool(
            name="screenshot",
            description="截取当前页面截图",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "保存路径"
                    },
                    "full_page": {
                        "type": "boolean",
                        "description": "是否截取完整页面",
                        "default": False
                    }
                },
                "required": []
            }
        ))
        
        self.register_tool(MCPTool(
            name="click",
            description="点击页面元素",
            parameters={
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS 选择器"
                    }
                },
                "required": ["selector"]
            }
        ))
        
        self.register_tool(MCPTool(
            name="type_text",
            description="在输入框中输入文本",
            parameters={
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS 选择器"
                    },
                    "text": {
                        "type": "string",
                        "description": "要输入的文本"
                    },
                    "clear": {
                        "type": "boolean",
                        "description": "是否先清空输入框",
                        "default": True
                    }
                },
                "required": ["selector", "text"]
            }
        ))
        
        self.register_tool(MCPTool(
            name="get_content",
            description="获取页面内容",
            parameters={
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS 选择器（可选，默认获取整个页面）"
                    },
                    "type": {
                        "type": "string",
                        "description": "内容类型: text, html, attribute",
                        "enum": ["text", "html", "attribute"],
                        "default": "text"
                    },
                    "attribute": {
                        "type": "string",
                        "description": "属性名（当 type 为 attribute 时使用）"
                    }
                },
                "required": []
            }
        ))
        
        self.register_tool(MCPTool(
            name="wait_for",
            description="等待页面元素或条件",
            parameters={
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS 选择器"
                    },
                    "state": {
                        "type": "string",
                        "description": "等待状态: visible, hidden, attached, detached",
                        "enum": ["visible", "hidden", "attached", "detached"],
                        "default": "visible"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "超时时间（毫秒）",
                        "default": 30000
                    }
                },
                "required": ["selector"]
            }
        ))
        
        self.register_tool(MCPTool(
            name="evaluate",
            description="在页面中执行 JavaScript 代码",
            parameters={
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "JavaScript 代码"
                    }
                },
                "required": ["script"]
            }
        ))
        
        self.register_tool(MCPTool(
            name="scroll",
            description="滚动页面",
            parameters={
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "description": "滚动方向: up, down, left, right",
                        "enum": ["up", "down", "left", "right"],
                        "default": "down"
                    },
                    "amount": {
                        "type": "integer",
                        "description": "滚动像素数",
                        "default": 500
                    }
                },
                "required": []
            }
        ))
    
    async def _ensure_browser(self):
        """确保浏览器已启动"""
        if self._browser is None:
            try:
                from playwright.async_api import async_playwright
                
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(headless=True)
                self._context = await self._browser.new_context()
                self._page = await self._context.new_page()
                logger.info("浏览器已启动")
            except Exception as e:
                logger.error(f"启动浏览器失败: {e}")
                raise
    
    async def disconnect(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if hasattr(self, '_playwright') and self._playwright:
            await self._playwright.stop()
            self._playwright = None
        await super().disconnect()
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用浏览器工具"""
        try:
            await self._ensure_browser()
        except Exception as e:
            return {"error": f"浏览器初始化失败: {e}"}
        
        handlers = {
            "navigate": self._navigate,
            "screenshot": self._screenshot,
            "click": self._click,
            "type_text": self._type_text,
            "get_content": self._get_content,
            "wait_for": self._wait_for,
            "evaluate": self._evaluate,
            "scroll": self._scroll,
        }
        
        handler = handlers.get(tool_name)
        if handler:
            try:
                return await handler(**arguments)
            except Exception as e:
                logger.error(f"浏览器操作失败: {e}")
                return {"success": False, "error": str(e)}
        return {"error": f"未知工具: {tool_name}"}
    
    async def _navigate(self, url: str, wait_until: str = "load") -> Dict[str, Any]:
        """导航到 URL"""
        try:
            await self._page.goto(url, wait_until=wait_until)
            return {
                "success": True,
                "url": self._page.url,
                "title": await self._page.title()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _screenshot(
        self,
        path: Optional[str] = None,
        full_page: bool = False
    ) -> Dict[str, Any]:
        """截取截图"""
        import os
        import base64
        from pathlib import Path
        
        try:
            if path:
                workspace = os.environ.get("WORKSPACE_PATH", os.getcwd())
                file_path = Path(path)
                if not file_path.is_absolute():
                    file_path = Path(workspace) / file_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                await self._page.screenshot(path=str(file_path), full_page=full_page)
                return {
                    "success": True,
                    "path": str(file_path)
                }
            else:
                # 返回 base64
                screenshot_bytes = await self._page.screenshot(full_page=full_page)
                return {
                    "success": True,
                    "base64": base64.b64encode(screenshot_bytes).decode()
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _click(self, selector: str) -> Dict[str, Any]:
        """点击元素"""
        try:
            await self._page.click(selector)
            return {"success": True, "selector": selector}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _type_text(
        self,
        selector: str,
        text: str,
        clear: bool = True
    ) -> Dict[str, Any]:
        """输入文本"""
        try:
            if clear:
                await self._page.fill(selector, text)
            else:
                await self._page.type(selector, text)
            return {"success": True, "selector": selector}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_content(
        self,
        selector: Optional[str] = None,
        type: str = "text",
        attribute: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取内容"""
        try:
            if selector:
                element = await self._page.query_selector(selector)
                if not element:
                    return {"success": False, "error": f"未找到元素: {selector}"}
                
                if type == "text":
                    content = await element.text_content()
                elif type == "html":
                    content = await element.inner_html()
                elif type == "attribute" and attribute:
                    content = await element.get_attribute(attribute)
                else:
                    content = await element.text_content()
            else:
                if type == "html":
                    content = await self._page.content()
                else:
                    content = await self._page.evaluate("document.body.innerText")
            
            return {
                "success": True,
                "content": content
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _wait_for(
        self,
        selector: str,
        state: str = "visible",
        timeout: int = 30000
    ) -> Dict[str, Any]:
        """等待元素"""
        try:
            await self._page.wait_for_selector(selector, state=state, timeout=timeout)
            return {"success": True, "selector": selector, "state": state}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _evaluate(self, script: str) -> Dict[str, Any]:
        """执行 JavaScript"""
        try:
            result = await self._page.evaluate(script)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _scroll(
        self,
        direction: str = "down",
        amount: int = 500
    ) -> Dict[str, Any]:
        """滚动页面"""
        try:
            if direction == "down":
                await self._page.evaluate(f"window.scrollBy(0, {amount})")
            elif direction == "up":
                await self._page.evaluate(f"window.scrollBy(0, -{amount})")
            elif direction == "right":
                await self._page.evaluate(f"window.scrollBy({amount}, 0)")
            elif direction == "left":
                await self._page.evaluate(f"window.scrollBy(-{amount}, 0)")
            
            return {"success": True, "direction": direction, "amount": amount}
        except Exception as e:
            return {"success": False, "error": str(e)}

