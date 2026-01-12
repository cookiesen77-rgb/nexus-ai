"""
Gemini Chat 客户端 - 用于 PPT 大纲、文案、排版生成
使用 gemini-3-pro-preview 模型
"""

import asyncio
import json
import logging
import os
from typing import Optional, List, Dict, Any

import httpx

logger = logging.getLogger(__name__)


class GeminiChatClient:
    """
    Gemini Chat API 客户端
    
    专门用于 PPT 内容生成：
    - 大纲生成
    - 文案撰写
    - 排版设计指令
    """
    
    # Gemini 3 Pro Preview API
    API_URL = "https://nexusapi.cn/v1beta/models/gemini-3-pro-preview:generateContent"
    
    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        # 注意：现在可由 LSY 配置中心（ppt.text）动态提供 api_key/api_url，
        # 因此这里不强制要求环境变量一定存在（避免启动即崩溃）。
        self.api_key = api_key or os.getenv("ALLAPI_KEY", "")
        self.api_url = api_url or self.API_URL
        self.timeout = 120  # 较长的超时时间
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        调用 Gemini 生成文本响应
        
        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大输出 token 数
            
        Returns:
            {"content": "...", "success": True/False, "error": "..."}
        """
        api_key = self.api_key
        api_url = self.api_url
        timeout = self.timeout

        if not api_key:
            return {"content": "", "success": False, "error": "Missing ALLAPI_KEY."}
        if not api_url:
            return {"content": "", "success": False, "error": "Missing request_url."}

        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        # 将 OpenAI 格式转换为 Gemini 格式
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "text/plain"
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"调用 Gemini Chat API, 消息数: {len(messages)}")
                response = await client.post(
                    api_url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                return self._parse_response(result)
                
        except httpx.TimeoutException:
            logger.error("Gemini Chat API 调用超时")
            return {
                "content": "",
                "success": False,
                "error": "API 调用超时，请重试"
            }
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.text
            except:
                pass
            logger.error(f"Gemini Chat API HTTP 错误: {e.response.status_code}, {error_detail}")
            return {
                "content": "",
                "success": False,
                "error": f"API 错误: {e.response.status_code}"
            }
        except Exception as e:
            logger.error(f"Gemini Chat API 调用失败: {e}")
            return {
                "content": "",
                "success": False,
                "error": str(e)
            }
    
    def _parse_response(self, result: dict) -> Dict[str, Any]:
        """解析 Gemini API 响应"""
        try:
            if "candidates" in result and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                
                text_response = ""
                for part in parts:
                    if "text" in part:
                        text_response += part["text"]
                
                # 过滤掉可能的思考文本
                text_response = self._filter_thinking(text_response)
                
                return {
                    "content": text_response,
                    "success": True,
                    "error": ""
                }
            else:
                error_msg = "响应格式异常"
                if "error" in result:
                    error_msg = result["error"].get("message", error_msg)
                return {
                    "content": "",
                    "success": False,
                    "error": error_msg
                }
        except Exception as e:
            return {
                "content": "",
                "success": False,
                "error": f"解析响应失败: {e}"
            }
    
    def _filter_thinking(self, text: str) -> str:
        """过滤掉可能的思考文本"""
        import re
        
        # 思考标记模式 - 移除各种英文思考文本
        thinking_patterns = [
            r'<thinking>.*?</thinking>',
            r'\[thinking\].*?\[/thinking\]',
            r'Let me think.*?\n',
            r'I\'m considering.*?\n',
            r'My thought process.*?\n',
            r'\*\*[A-Z][a-z]+ [A-Za-z ]+\*\*',  # **Defining the JSON Structure**
            r'\*\*Formulating.*?\*\*',
            r'\*\*Defining.*?\*\*',
            r'\*\*Processing.*?\*\*',
            r'\*\*Analyzing.*?\*\*',
            r'I\'ve (now |)satisfied.*?\.',
            r'The next step is.*?\.',
            r'I have formatted.*?\.',
            r'I\'ve opted for.*?\.',
            r'I will move on to.*?\.',
            r'I\'m now satisfied.*?\.',
        ]
        
        result = text
        for pattern in thinking_patterns:
            result = re.sub(pattern, '', result, flags=re.DOTALL | re.IGNORECASE)
        
        # 如果结果是 JSON 格式，尝试只提取 JSON
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', result)
        if json_match:
            return json_match.group(0)  # 返回包含 ```json``` 的完整块
        
        # 清理多余的空行
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result.strip()
    
    async def generate_outline(
        self,
        topic: str,
        page_count: int = 8,
        requirements: str = "",
        language: str = "zh"
    ) -> List[Dict]:
        """
        生成 PPT 大纲
        
        Args:
            topic: PPT 主题
            page_count: 页数
            requirements: 额外要求
            language: 输出语言
            
        Returns:
            大纲列表
        """
        from src.services.ppt_prompts import get_outline_generation_prompt
        
        prompt = get_outline_generation_prompt(
            topic=topic,
            page_count=page_count,
            requirements=requirements,
            language=language
        )
        
        response = await self.complete([{"role": "user", "content": prompt}])
        
        if response["success"]:
            return self._parse_outline(response["content"], topic, page_count)
        else:
            logger.error(f"生成大纲失败: {response['error']}")
            return self._default_outline(topic, page_count)
    
    def _parse_outline(self, text: str, topic: str, page_count: int) -> List[Dict]:
        """解析大纲响应"""
        import re
        
        try:
            # 先清理掉所有思考文本
            text = self._deep_clean(text)
            
            # 清理 markdown 代码块
            text = text.strip()
            if text.startswith("```"):
                text = re.sub(r'^```\w*\n?', '', text)
                text = re.sub(r'\n?```$', '', text)
            
            # 尝试提取 JSON
            json_match = re.search(r'\[[\s\S]*\]', text)
            if json_match:
                outline = json.loads(json_match.group())
                return self._flatten_outline(outline)
        except json.JSONDecodeError as e:
            logger.warning(f"大纲 JSON 解析失败: {e}")
        
        return self._default_outline(topic, page_count)
    
    def _deep_clean(self, text: str) -> str:
        """深度清理文本，移除所有思考过程"""
        import re
        
        # 移除 **粗体思考标题**
        text = re.sub(r'\*\*[A-Z][^*]+\*\*\s*', '', text)
        
        # 移除所有英文句子开头的思考短语
        english_thinking = [
            r"I've (?:now |)(?:satisfied|opted|formatted|completed|finished|created).*?[.\n]",
            r"I (?:have|will|am) (?:now |)(?:move|moving|format|satisfied|opt|create).*?[.\n]",
            r"The (?:next step|final|output|result).*?[.\n]",
            r"Here's (?:the|my|a).*?[:\n]",
            r"Let me (?:now |)(?:create|generate|provide).*?[.\n]",
            r"(?:Now |)I(?:'m| am) (?:creating|generating|providing).*?[.\n]",
            r"^[A-Z][a-z]+ [a-z]+ [a-z]+.*?[.\n]",  # 简单英文句子
        ]
        
        for pattern in english_thinking:
            text = re.sub(pattern, '', text, flags=re.MULTILINE | re.IGNORECASE)
        
        # 清理连续的空行和空格
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r'^\s+', '', text)
        
        return text.strip()
    
    def _flatten_outline(self, outline: List[Dict]) -> List[Dict]:
        """展平大纲（支持 part-based 格式）"""
        pages = []
        for item in outline:
            if "part" in item and "pages" in item:
                for page in item["pages"]:
                    page_copy = page.copy()
                    page_copy["part"] = item["part"]
                    pages.append(page_copy)
            else:
                pages.append(item)
        return pages
    
    def _default_outline(self, topic: str, page_count: int) -> List[Dict]:
        """生成默认大纲"""
        outline = [
            {"title": topic, "points": ["演示文稿"], "layout": "title"}
        ]
        
        middle_pages = page_count - 2
        for i in range(middle_pages):
            if i == 0:
                outline.append({
                    "title": "目录",
                    "points": ["第一部分", "第二部分", "第三部分"],
                    "layout": "title_content"
                })
            else:
                outline.append({
                    "title": f"第{i}部分",
                    "points": [f"要点一", f"要点二", f"要点三"],
                    "layout": "title_content"
                })
        
        outline.append({
            "title": "总结",
            "points": [f"{topic}的核心要点", "行动建议", "感谢聆听"],
            "layout": "conclusion"
        })
        
        return outline
    
    async def generate_page_content(
        self,
        topic: str,
        page_title: str,
        page_points: List[str],
        page_index: int,
        total_pages: int,
        language: str = "zh"
    ) -> Dict[str, Any]:
        """
        为单个页面生成详细内容
        
        Args:
            topic: PPT 主题
            page_title: 页面标题
            page_points: 页面要点
            page_index: 页面索引
            total_pages: 总页数
            language: 输出语言
            
        Returns:
            {"title": str, "content": str, "layout_hints": dict}
        """
        is_cover = page_index == 1
        is_conclusion = page_index == total_pages
        
        if is_cover:
            prompt = f"""
为 PPT 封面页生成内容。

主题：{topic}
标题：{page_title}

要求：
- 封面保持简洁
- 只包含主标题和可能的副标题
- 可以包含演讲人信息或日期

输出 JSON 格式：
{{"title": "主标题", "subtitle": "副标题（可选）", "author": "演讲人（可选）"}}
"""
        elif is_conclusion:
            prompt = f"""
为 PPT 结尾页生成内容。

主题：{topic}
标题：{page_title}
原始要点：{json.dumps(page_points, ensure_ascii=False)}

要求：
- 总结全文核心要点
- 简洁有力
- 可以包含行动号召或感谢语

输出 JSON 格式：
{{"title": "标题", "content": "总结内容（每行一个要点，用换行符分隔）"}}
"""
        else:
            prompt = f"""
为 PPT 内容页生成详细文案。

主题：{topic}
页面标题：{page_title}
原始要点：{json.dumps(page_points, ensure_ascii=False)}
页码：{page_index}/{total_pages}

要求：
1. 每个要点控制在 15-25 字以内
2. 内容简洁精炼，适合演示
3. 条理清晰，使用列表形式
4. 3-5 个要点最佳
5. 可以为每个要点添加简短说明

输出 JSON 格式：
{{"title": "页面标题", "content": "- 要点一\\n- 要点二\\n- 要点三", "needs_illustration": true/false, "illustration_theme": "配图主题描述"}}

needs_illustration: 该页面是否需要配图（封面、目录、纯文字页可能不需要）
illustration_theme: 如果需要配图，描述配图的主题（如"人工智能"、"数据增长"、"团队协作"等）
"""
        
        response = await self.complete([{"role": "user", "content": prompt}])
        
        if response["success"]:
            try:
                # 深度清理思考文本
                content = self._deep_clean(response["content"])
                
                # 尝试解析 JSON
                content = content.strip()
                if content.startswith("```"):
                    import re
                    content = re.sub(r'^```\w*\n?', '', content)
                    content = re.sub(r'\n?```$', '', content)
                
                result = json.loads(content)
                
                # 再次清理结果中可能存在的思考文本
                if "title" in result:
                    result["title"] = self._clean_content_field(result["title"])
                if "content" in result:
                    result["content"] = self._clean_content_field(result["content"])
                if "subtitle" in result:
                    result["subtitle"] = self._clean_content_field(result.get("subtitle", ""))
                
                return result
            except json.JSONDecodeError:
                # 回退：直接使用文本
                return {
                    "title": page_title,
                    "content": self._clean_content_field(response["content"]),
                    "needs_illustration": not is_cover and not is_conclusion,
                    "illustration_theme": topic
                }
        else:
            # 回退：使用原始要点
            return {
                "title": page_title,
                "content": "\n".join([f"- {p}" for p in page_points]),
                "needs_illustration": not is_cover and not is_conclusion,
                "illustration_theme": topic
            }
    
    def _clean_content_field(self, text: str) -> str:
        """清理内容字段中的思考文本"""
        import re
        if not text:
            return text
        
        # 移除常见的 Gemini 思考输出
        patterns_to_remove = [
            r'\*\*[A-Z][^*]+\*\*',  # **Formulating the Output**
            r"I've (?:now |)(?:satisfied|opted|formatted).*?[.\n]",
            r"Defining the JSON.*?[.\n]",
            r"Formulating.*?[.\n]",
            r"I'm now satisfied.*?[.\n]",
            r"Let me.*?[.\n]",
            r"Here is the.*?[:\n]",
            r"^The final.*?[:\n]",
        ]
        
        result = text
        for pattern in patterns_to_remove:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE | re.MULTILINE)
        
        return result.strip()


# 全局实例
_gemini_chat_client: Optional[GeminiChatClient] = None


def get_gemini_chat_client() -> GeminiChatClient:
    """获取 Gemini Chat 客户端单例"""
    global _gemini_chat_client
    if _gemini_chat_client is None:
        _gemini_chat_client = GeminiChatClient()
    return _gemini_chat_client

