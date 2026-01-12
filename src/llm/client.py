"""
LLM客户端封装
"""
from anthropic import Anthropic
import os


class LLMClient:
    """LLM客户端"""

    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

    async def complete(self, messages: list, model: str = "claude-3-5-sonnet-20241022", **kwargs):
        """生成补全"""
        response = self.client.messages.create(
            model=model,
            messages=messages,
            **kwargs
        )
        return response
