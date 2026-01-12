"""
浏览器控制路由
"""

import base64
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/browser", tags=["Browser"])


class NavigateRequest(BaseModel):
    """导航请求"""
    url: str


class ClickRequest(BaseModel):
    """点击请求"""
    selector: str


class TypeRequest(BaseModel):
    """输入请求"""
    selector: str
    text: str


class NavigateResponse(BaseModel):
    """导航响应"""
    screenshot: str  # base64编码
    title: str
    url: str


class ScreenshotResponse(BaseModel):
    """截图响应"""
    screenshot: str


# 浏览器实例 (将在工具层实现)
_browser_instance = None


async def get_browser():
    """获取浏览器实例"""
    global _browser_instance
    if _browser_instance is None:
        try:
            from src.tools.browser_tool import get_browser_instance
            _browser_instance = await get_browser_instance()
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="Browser tool not available. Install playwright: pip install playwright && playwright install"
            )
    return _browser_instance


@router.post("/navigate", response_model=NavigateResponse)
async def navigate(request: NavigateRequest):
    """
    导航到URL
    """
    try:
        browser = await get_browser()
        result = await browser.navigate(request.url)
        
        return NavigateResponse(
            screenshot=result.get('screenshot', ''),
            title=result.get('title', ''),
            url=result.get('url', request.url)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screenshot", response_model=ScreenshotResponse)
async def screenshot():
    """
    获取当前页面截图
    """
    try:
        browser = await get_browser()
        result = await browser.screenshot()
        
        return ScreenshotResponse(screenshot=result.get('screenshot', ''))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/click")
async def click(request: ClickRequest):
    """
    点击元素
    """
    try:
        browser = await get_browser()
        await browser.click(request.selector)
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/type")
async def type_text(request: TypeRequest):
    """
    输入文本
    """
    try:
        browser = await get_browser()
        await browser.type(request.selector, request.text)
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content")
async def get_content():
    """
    获取页面内容
    """
    try:
        browser = await get_browser()
        result = await browser.get_content()
        return {
            "title": result.get('title', ''),
            "url": result.get('url', ''),
            "text": result.get('text', '')
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

