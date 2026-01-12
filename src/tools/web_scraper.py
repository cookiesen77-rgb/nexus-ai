"""
网页抓取工具 - 抓取和解析网页内容
"""

import asyncio
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
from .base import BaseTool, ToolResult, ToolStatus
from .rate_limiter import get_rate_limiter


class WebScraperTool(BaseTool):
    """网页抓取工具"""
    
    name: str = "web_scraper"
    description: str = """Scrape and extract content from web pages.
    
Use this tool to:
- Fetch web page content
- Extract text, links, or images
- Parse HTML with CSS selectors
- Get structured data from websites

Supports rate limiting to avoid being blocked."""

    parameters: Dict[str, Any] = {
        "properties": {
            "url": {
                "type": "string",
                "description": "URL of the web page to scrape"
            },
            "extract_type": {
                "type": "string",
                "enum": ["text", "html", "links", "images", "tables", "metadata"],
                "description": "Type of content to extract",
                "default": "text"
            },
            "selector": {
                "type": "string",
                "description": "CSS selector to target specific elements (optional)"
            },
            "timeout": {
                "type": "integer",
                "description": "Request timeout in seconds",
                "default": 30
            }
        },
        "required": ["url"]
    }
    
    def __init__(self):
        super().__init__()
        self._session = None
    
    async def _get_session(self):
        """获取或创建HTTP会话"""
        if self._session is None:
            try:
                import httpx
                self._session = httpx.AsyncClient(
                    timeout=30,
                    follow_redirects=True,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                    }
                )
            except ImportError:
                raise RuntimeError("httpx not installed. Run: pip install httpx")
        return self._session
    
    async def execute(
        self,
        url: str,
        extract_type: str = "text",
        selector: str = None,
        timeout: int = 30,
        **kwargs
    ) -> ToolResult:
        """
        抓取网页内容
        
        Args:
            url: 网页URL
            extract_type: 提取类型 (text/html/links/images/tables/metadata)
            selector: CSS选择器
            timeout: 超时时间
        """
        # 限流检查
        domain = urlparse(url).netloc
        limiter = get_rate_limiter()
        await limiter.wait(domain)
        
        try:
            # 获取页面
            session = await self._get_session()
            response = await session.get(url, timeout=timeout)
            response.raise_for_status()
            
            html = response.text
            
            # 解析HTML
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
            except ImportError:
                # 简单的正则解析作为后备
                return await self._extract_without_bs4(html, extract_type, url)
            
            # 如果有选择器，先过滤
            if selector:
                elements = soup.select(selector)
                if not elements:
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        output=f"No elements found matching selector: {selector}",
                    )
                # 为后续处理创建新的soup
                from bs4 import BeautifulSoup
                new_html = ''.join(str(el) for el in elements)
                soup = BeautifulSoup(new_html, 'html.parser')
            
            # 根据类型提取内容
            if extract_type == "text":
                output = self._extract_text(soup)
            elif extract_type == "html":
                output = soup.prettify()
            elif extract_type == "links":
                output = self._extract_links(soup, url)
            elif extract_type == "images":
                output = self._extract_images(soup, url)
            elif extract_type == "tables":
                output = self._extract_tables(soup)
            elif extract_type == "metadata":
                output = self._extract_metadata(soup, url)
            else:
                output = self._extract_text(soup)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=output,
                metadata={"url": url, "extract_type": extract_type}
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=f"Failed to scrape {url}: {str(e)}"
            )
    
    def _extract_text(self, soup) -> str:
        """提取纯文本"""
        # 移除script和style
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        
        text = soup.get_text(separator='\n', strip=True)
        # 清理多余空行
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)
    
    def _extract_links(self, soup, base_url: str) -> List[Dict]:
        """提取链接"""
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            # 转换相对URL
            full_url = urljoin(base_url, href)
            links.append({
                "text": a.get_text(strip=True),
                "url": full_url
            })
        return links
    
    def _extract_images(self, soup, base_url: str) -> List[Dict]:
        """提取图片"""
        images = []
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src')
            if src:
                images.append({
                    "src": urljoin(base_url, src),
                    "alt": img.get('alt', ''),
                    "title": img.get('title', '')
                })
        return images
    
    def _extract_tables(self, soup) -> List[List[List[str]]]:
        """提取表格"""
        tables = []
        for table in soup.find_all('table'):
            rows = []
            for tr in table.find_all('tr'):
                cells = []
                for td in tr.find_all(['td', 'th']):
                    cells.append(td.get_text(strip=True))
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(rows)
        return tables
    
    def _extract_metadata(self, soup, url: str) -> Dict:
        """提取页面元数据"""
        metadata = {"url": url}
        
        # 标题
        title = soup.find('title')
        metadata['title'] = title.get_text(strip=True) if title else None
        
        # Meta标签
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            if name and content:
                metadata[name] = content
        
        # 统计
        metadata['links_count'] = len(soup.find_all('a'))
        metadata['images_count'] = len(soup.find_all('img'))
        metadata['text_length'] = len(soup.get_text())
        
        return metadata
    
    async def _extract_without_bs4(
        self, 
        html: str, 
        extract_type: str,
        url: str
    ) -> ToolResult:
        """没有BeautifulSoup时的简单提取"""
        if extract_type == "html":
            return ToolResult(status=ToolStatus.SUCCESS, output=html)
        
        # 简单的文本提取
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=text,
            metadata={"url": url, "note": "Basic extraction (beautifulsoup not available)"}
        )
    
    async def close(self):
        """关闭HTTP会话"""
        if self._session:
            await self._session.aclose()
            self._session = None


class ContentExtractorTool(BaseTool):
    """内容提取工具 - 智能提取网页正文"""
    
    name: str = "content_extractor"
    description: str = """Extract main content from web articles.
    
Intelligently identifies and extracts:
- Article title
- Main body text
- Author information
- Publication date
- Summary/description

Best for news articles, blog posts, and documentation pages."""

    parameters: Dict[str, Any] = {
        "properties": {
            "url": {
                "type": "string",
                "description": "URL of the article to extract"
            },
            "include_html": {
                "type": "boolean",
                "description": "Include HTML formatting",
                "default": False
            }
        },
        "required": ["url"]
    }
    
    async def execute(
        self,
        url: str,
        include_html: bool = False,
        **kwargs
    ) -> ToolResult:
        """提取文章内容"""
        scraper = WebScraperTool()
        
        try:
            # 获取元数据
            meta_result = await scraper.execute(url, extract_type="metadata")
            metadata = meta_result.output if meta_result.is_success else {}
            
            # 获取文本
            text_result = await scraper.execute(url, extract_type="text")
            
            if not text_result.is_success:
                return text_result
            
            # 构建结果
            content = {
                "title": metadata.get('title') or metadata.get('og:title'),
                "description": metadata.get('description') or metadata.get('og:description'),
                "author": metadata.get('author'),
                "url": url,
                "content": text_result.output,
                "word_count": len(text_result.output.split())
            }
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=content
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=str(e)
            )
        finally:
            await scraper.close()


# 创建工具实例
web_scraper = WebScraperTool()
content_extractor = ContentExtractorTool()

