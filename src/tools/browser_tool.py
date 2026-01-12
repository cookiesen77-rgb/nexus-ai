"""
浏览器自动化工具

基于Playwright实现网页交互
"""

import asyncio
import base64
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .base import BaseTool, ToolResult, ToolStatus


@dataclass
class BrowserState:
    """浏览器状态"""
    url: str = ""
    title: str = ""
    content: str = ""


class BrowserManager:
    """浏览器管理器"""
    
    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._state = BrowserState()
    
    async def _ensure_browser(self):
        """确保浏览器已启动"""
        if self._page is not None:
            return
        
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )
        
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        self._context = await self._browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        self._page = await self._context.new_page()
    
    async def navigate(self, url: str) -> Dict[str, Any]:
        """导航到URL"""
        await self._ensure_browser()
        
        await self._page.goto(url, wait_until='networkidle', timeout=30000)
        
        self._state.url = self._page.url
        self._state.title = await self._page.title()
        
        screenshot = await self._page.screenshot(type='png')
        screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
        
        return {
            'url': self._state.url,
            'title': self._state.title,
            'screenshot': screenshot_b64
        }
    
    async def screenshot(self) -> Dict[str, Any]:
        """获取当前页面截图"""
        await self._ensure_browser()
        
        screenshot = await self._page.screenshot(type='png')
        screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
        
        return {
            'screenshot': screenshot_b64,
            'url': self._page.url,
            'title': await self._page.title()
        }
    
    async def click(self, selector: str) -> Dict[str, Any]:
        """点击元素"""
        await self._ensure_browser()
        
        await self._page.click(selector, timeout=10000)
        await self._page.wait_for_load_state('networkidle')
        
        return {'success': True, 'selector': selector}
    
    async def type(self, selector: str, text: str) -> Dict[str, Any]:
        """输入文本"""
        await self._ensure_browser()
        
        await self._page.fill(selector, text, timeout=10000)
        
        return {'success': True, 'selector': selector, 'text': text}
    
    async def get_content(self) -> Dict[str, Any]:
        """获取页面内容"""
        await self._ensure_browser()
        
        text = await self._page.inner_text('body')
        
        return {
            'url': self._page.url,
            'title': await self._page.title(),
            'text': text[:10000]  # 限制长度
        }
    
    async def evaluate(self, script: str) -> Any:
        """执行JavaScript"""
        await self._ensure_browser()
        
        return await self._page.evaluate(script)
    
    async def close(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._page = None
        self._context = None


# 全局浏览器实例
_browser_manager: Optional[BrowserManager] = None


async def get_browser_instance() -> BrowserManager:
    """获取浏览器实例"""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
    return _browser_manager


class BrowserTool(BaseTool):
    """
    浏览器工具
    
    支持网页导航、点击、输入、截图等操作
    """
    
    name = "browser"
    description = "Browser automation tool for web navigation and interaction"
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["navigate", "click", "type", "screenshot", "get_content", "evaluate"],
                "description": "Action to perform"
            },
            "url": {
                "type": "string",
                "description": "URL for navigate action"
            },
            "selector": {
                "type": "string",
                "description": "CSS selector for click/type actions"
            },
            "text": {
                "type": "string",
                "description": "Text for type action"
            },
            "script": {
                "type": "string",
                "description": "JavaScript for evaluate action"
            }
        },
        "required": ["action"]
    }
    
    async def execute(
        self,
        action: str,
        url: str = "",
        selector: str = "",
        text: str = "",
        script: str = ""
    ) -> ToolResult:
        """执行浏览器操作"""
        try:
            browser = await get_browser_instance()
            
            if action == "navigate":
                if not url:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error="URL is required for navigate action"
                    )
                result = await browser.navigate(url)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"Navigated to {result['title']} ({result['url']})",
                    data=result
                )
            
            elif action == "click":
                if not selector:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error="Selector is required for click action"
                    )
                result = await browser.click(selector)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"Clicked on {selector}",
                    data=result
                )
            
            elif action == "type":
                if not selector or not text:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error="Selector and text are required for type action"
                    )
                result = await browser.type(selector, text)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"Typed '{text}' into {selector}",
                    data=result
                )
            
            elif action == "screenshot":
                result = await browser.screenshot()
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"Screenshot taken of {result['title']}",
                    data=result
                )
            
            elif action == "get_content":
                result = await browser.get_content()
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=result['text'],
                    data=result
                )
            
            elif action == "evaluate":
                if not script:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error="Script is required for evaluate action"
                    )
                result = await browser.evaluate(script)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=str(result),
                    data={'result': result}
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
browser_tool = BrowserTool()

