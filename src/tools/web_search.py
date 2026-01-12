"""
网络搜索工具

支持通过Tavily API进行网络搜索
"""

import os
from typing import Any, Dict, List, Optional

import httpx

from .base import BaseTool, ToolResult, ToolStatus


class WebSearchTool(BaseTool):
    """网络搜索工具"""

    name = "web_search"
    description = "搜索互联网获取最新信息。返回相关网页的标题、摘要和URL。"

    parameters = {
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词或问题"
            },
            "max_results": {
                "type": "integer",
                "description": "返回结果数量，默认为5，最大为10"
            }
        },
        "required": ["query"]
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化搜索工具

        Args:
            api_key: Tavily API密钥，默认从环境变量读取
        """
        super().__init__()
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.base_url = "https://api.tavily.com"

    async def execute(
        self,
        query: str,
        max_results: int = 5
    ) -> ToolResult:
        """
        执行网络搜索

        Args:
            query: 搜索查询
            max_results: 最大结果数

        Returns:
            ToolResult: 搜索结果
        """
        # 检查API密钥
        if not self.api_key:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error="Tavily API key not configured. Set TAVILY_API_KEY environment variable."
            )

        # 限制结果数量
        max_results = min(max_results, 10)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "max_results": max_results,
                        "include_answer": True,
                        "include_raw_content": False,
                        "include_images": False
                    }
                )

                if response.status_code != 200:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output=None,
                        error=f"Search API error: {response.status_code} - {response.text}"
                    )

                data = response.json()

                # 格式化结果
                results = self._format_results(data)

                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=results,
                    metadata={
                        "query": query,
                        "result_count": len(results.get("results", []))
                    }
                )

        except httpx.TimeoutException:
            return ToolResult(
                status=ToolStatus.TIMEOUT,
                output=None,
                error="Search request timed out"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=f"Search error: {e}"
            )

    def _format_results(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化搜索结果"""
        results = []

        # 处理搜索结果
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
                "score": item.get("score", 0)
            })

        return {
            "answer": data.get("answer", ""),
            "results": results,
            "query": data.get("query", "")
        }


class MockWebSearchTool(BaseTool):
    """
    模拟网络搜索工具（用于测试）

    当没有API密钥时，返回模拟数据
    """

    name = "web_search"
    description = "搜索互联网获取最新信息（模拟模式）"

    parameters = {
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词"
            },
            "max_results": {
                "type": "integer",
                "description": "返回结果数量"
            }
        },
        "required": ["query"]
    }

    async def execute(
        self,
        query: str,
        max_results: int = 5
    ) -> ToolResult:
        """返回模拟搜索结果"""
        mock_results = {
            "answer": f"这是关于 '{query}' 的模拟搜索答案。",
            "results": [
                {
                    "title": f"关于 {query} 的文章 1",
                    "url": "https://example.com/article1",
                    "content": f"这是关于 {query} 的第一篇文章的摘要内容...",
                    "score": 0.95
                },
                {
                    "title": f"关于 {query} 的文章 2",
                    "url": "https://example.com/article2",
                    "content": f"这是关于 {query} 的第二篇文章的摘要内容...",
                    "score": 0.90
                },
                {
                    "title": f"{query} 相关信息",
                    "url": "https://example.com/info",
                    "content": f"这里有更多关于 {query} 的相关信息...",
                    "score": 0.85
                }
            ][:max_results],
            "query": query
        }

        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=mock_results,
            metadata={
                "query": query,
                "mode": "mock",
                "result_count": len(mock_results["results"])
            }
        )


def create_web_search_tool(api_key: Optional[str] = None) -> BaseTool:
    """
    创建网络搜索工具

    如果有API密钥，返回真实搜索工具；否则返回模拟工具

    Args:
        api_key: Tavily API密钥

    Returns:
        BaseTool: 搜索工具实例
    """
    key = api_key or os.getenv("TAVILY_API_KEY")
    if key:
        return WebSearchTool(api_key=key)
    return MockWebSearchTool()


# 创建全局实例
web_search = create_web_search_tool()

