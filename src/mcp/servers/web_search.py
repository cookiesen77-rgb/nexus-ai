"""
Web Search MCP 服务器

提供网络搜索功能
"""

import logging
import os
from typing import Any, Dict

from ..base import LocalMCPServer, MCPServerConfig, MCPTool

logger = logging.getLogger(__name__)


class WebSearchServer(LocalMCPServer):
    """网络搜索 MCP 服务器"""
    
    def __init__(self, config: MCPServerConfig):
        super().__init__(config)
        
        # 注册工具
        self.register_tool(MCPTool(
            name="search",
            description="搜索网络获取信息。支持各种查询，返回相关网页结果。",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询词"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "返回结果数量，默认10",
                        "default": 10
                    },
                    "language": {
                        "type": "string",
                        "description": "搜索语言，如 'zh-CN', 'en'",
                        "default": "zh-CN"
                    }
                },
                "required": ["query"]
            }
        ))
        
        self.register_tool(MCPTool(
            name="search_news",
            description="搜索最新新闻资讯",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "新闻搜索关键词"
                    },
                    "days": {
                        "type": "integer",
                        "description": "搜索最近几天的新闻，默认7天",
                        "default": 7
                    }
                },
                "required": ["query"]
            }
        ))
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用搜索工具"""
        if tool_name == "search":
            return await self._search(
                query=arguments.get("query", ""),
                num_results=arguments.get("num_results", 10),
                language=arguments.get("language", "zh-CN")
            )
        elif tool_name == "search_news":
            return await self._search_news(
                query=arguments.get("query", ""),
                days=arguments.get("days", 7)
            )
        else:
            return {"error": f"未知工具: {tool_name}"}
    
    async def _search(self, query: str, num_results: int = 10, language: str = "zh-CN") -> Dict[str, Any]:
        """执行网络搜索"""
        try:
            normalized = query.replace(" ", "").lower()
            if ("北京时间" in query) or ("beijing" in normalized and "time" in normalized):
                return await self._get_beijing_time()

            # 尝试使用已有的 web_search 工具
            from src.tools import get_global_registry
            
            registry = get_global_registry()
            web_search = registry.get("web_search")
            
            if web_search:
                tool_kwargs = {
                    "query": query,
                    "max_results": num_results
                }
                result = await web_search.execute(
                    **tool_kwargs
                )
                return {
                    "success": result.is_success,
                    "results": result.output if result.is_success else [],
                    "error": result.error if not result.is_success else None
                }
            
            # 如果没有 web_search 工具，使用简单的 HTTP 搜索
            import httpx
            
            # 使用 DuckDuckGo Instant Answer API (免费，无需 API key)
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_html": 1,
                        "skip_disambig": 1
                    },
                    timeout=10.0
                )
                data = response.json()
                
                results = []
                
                # 解析即时答案
                if data.get("AbstractText"):
                    results.append({
                        "title": data.get("Heading", query),
                        "snippet": data.get("AbstractText"),
                        "url": data.get("AbstractURL", "")
                    })
                
                # 解析相关主题
                for topic in data.get("RelatedTopics", [])[:num_results]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append({
                            "title": topic.get("Text", "")[:100],
                            "snippet": topic.get("Text", ""),
                            "url": topic.get("FirstURL", "")
                        })
                
                return {
                    "success": True,
                    "query": query,
                    "results": results[:num_results]
                }
                
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    async def _get_beijing_time(self) -> Dict[str, Any]:
        """调用权威时间源获取北京时间，必要时切换备用方案"""
        import httpx
        from datetime import datetime, timezone
        from zoneinfo import ZoneInfo

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get("https://worldtimeapi.org/api/timezone/Asia/Shanghai")
                resp.raise_for_status()
                data = resp.json()
                datetime_str = data.get("datetime")
                if datetime_str:
                    current = datetime.fromisoformat(datetime_str.rstrip("Z"))
                    formatted = current.strftime("%Y年%m月%d日 %H:%M:%S")
                else:
                    formatted = data.get("timezone", "Asia/Shanghai")

                return {
                    "success": True,
                    "results": [
                        {
                            "title": "当前北京时间",
                            "snippet": formatted,
                            "raw": data
                        }
                    ]
                }
            except Exception as primary_error:
                logger.warning(f"worldtimeapi 获取北京时间失败，尝试备用方案: {primary_error}")
                try:
                    fallback_resp = await client.get(
                        "https://www.baidu.com",
                        headers={"Cache-Control": "no-cache"}
                    )
                    fallback_resp.raise_for_status()
                    date_header = fallback_resp.headers.get("Date")
                    if not date_header:
                        raise ValueError("Baidu 响应缺少 Date 头")
                    gmt_time = datetime.strptime(date_header, "%a, %d %b %Y %H:%M:%S GMT").replace(
                        tzinfo=timezone.utc
                    )
                    beijing_time = gmt_time.astimezone(ZoneInfo("Asia/Shanghai"))
                    formatted = beijing_time.strftime("%Y年%m月%d日 %H:%M:%S")
                    return {
                        "success": True,
                        "results": [
                            {
                                "title": "当前北京时间（Baidu Date 头推算）",
                                "snippet": formatted,
                                "raw": {
                                    "source": "https://www.baidu.com",
                                    "date_header": date_header
                                }
                            }
                        ]
                    }
                except Exception as fallback_error:
                    logger.error(f"获取北京时间失败: {fallback_error}")
                    return {
                        "success": False,
                        "error": f"获取北京时间失败: {fallback_error}",
                        "results": []
                    }
    
    async def _search_news(self, query: str, days: int = 7) -> Dict[str, Any]:
        """搜索新闻"""
        # 在搜索查询中添加时间限制
        enhanced_query = f"{query} news"
        return await self._search(enhanced_query, num_results=10)

