"""
上下文压缩器 - 压缩长对话历史
"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .token_counter import count_tokens


@dataclass
class CompressionResult:
    """压缩结果"""
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    summary: str
    preserved_count: int


class ContextCompressor:
    """
    上下文压缩器
    
    将长对话历史压缩为简洁摘要
    """
    
    def __init__(
        self,
        llm=None,
        max_summary_tokens: int = 500,
        preserve_recent: int = 2
    ):
        """
        初始化压缩器
        
        Args:
            llm: LLM客户端 (可选，用于智能压缩)
            max_summary_tokens: 摘要最大Token数
            preserve_recent: 保留最近的消息数
        """
        self._llm = llm
        self.max_summary_tokens = max_summary_tokens
        self.preserve_recent = preserve_recent
    
    async def compress(
        self,
        messages: List[Any],
        context: str = None
    ) -> str:
        """
        压缩消息列表
        
        Args:
            messages: 消息列表
            context: 上下文信息
            
        Returns:
            str: 压缩后的摘要
        """
        if not messages:
            return ""
        
        # 计算原始Token数
        original_tokens = sum(
            msg.token_count if hasattr(msg, 'token_count') else count_tokens(str(msg))
            for msg in messages
        )
        
        # 如果有LLM，使用智能压缩
        if self._llm:
            return await self._llm_compress(messages, context)
        
        # 否则使用规则压缩
        return self._rule_based_compress(messages)
    
    async def _llm_compress(
        self,
        messages: List[Any],
        context: str = None
    ) -> str:
        """使用LLM进行智能压缩"""
        # 构建压缩提示
        conversation_text = self._format_messages(messages)
        
        prompt = f"""请将以下对话历史压缩为简洁的摘要，保留关键信息：

对话历史：
{conversation_text}

要求：
1. 保留重要的决策和结论
2. 保留关键的数据和事实
3. 压缩冗余的讨论过程
4. 摘要长度不超过{self.max_summary_tokens}个token

摘要："""

        try:
            response = await self._llm.complete(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_summary_tokens
            )
            return response.content
        except Exception:
            # 回退到规则压缩
            return self._rule_based_compress(messages)
    
    def _rule_based_compress(self, messages: List[Any]) -> str:
        """规则压缩"""
        if not messages:
            return ""
        
        # 提取关键信息
        key_points = []
        
        for msg in messages:
            content = msg.content if hasattr(msg, 'content') else str(msg)
            role = msg.role if hasattr(msg, 'role') else 'unknown'
            
            # 提取要点
            if role == "assistant":
                # 提取助手的结论/答案
                lines = content.split('\n')
                for line in lines[:3]:  # 只取前几行
                    if line.strip():
                        key_points.append(f"- {line.strip()[:100]}")
            elif role == "user":
                # 提取用户的问题/请求
                first_line = content.split('\n')[0][:100]
                key_points.append(f"Q: {first_line}")
        
        # 限制摘要长度
        summary_parts = []
        current_tokens = 0
        
        for point in key_points:
            point_tokens = count_tokens(point)
            if current_tokens + point_tokens > self.max_summary_tokens:
                break
            summary_parts.append(point)
            current_tokens += point_tokens
        
        return '\n'.join(summary_parts) if summary_parts else "Previous conversation context."
    
    def _format_messages(self, messages: List[Any]) -> str:
        """格式化消息为文本"""
        formatted = []
        for msg in messages:
            role = msg.role if hasattr(msg, 'role') else 'unknown'
            content = msg.content if hasattr(msg, 'content') else str(msg)
            formatted.append(f"{role}: {content[:500]}")
        return '\n\n'.join(formatted)
    
    def compress_sync(self, messages: List[Any]) -> str:
        """同步压缩 (仅规则压缩)"""
        return self._rule_based_compress(messages)


class IncrementalCompressor:
    """
    增量压缩器
    
    随着对话进行，增量更新摘要
    """
    
    def __init__(self, base_compressor: ContextCompressor = None):
        self.compressor = base_compressor or ContextCompressor()
        self.current_summary: str = ""
        self.processed_count: int = 0
    
    async def update(
        self,
        new_messages: List[Any],
        force: bool = False
    ) -> str:
        """
        增量更新摘要
        
        Args:
            new_messages: 新消息
            force: 强制更新
            
        Returns:
            str: 更新后的摘要
        """
        if not new_messages and not force:
            return self.current_summary
        
        # 合并现有摘要和新消息
        combined = []
        if self.current_summary:
            combined.append(type('Summary', (), {
                'role': 'system',
                'content': f"Previous summary: {self.current_summary}"
            })())
        combined.extend(new_messages)
        
        # 压缩
        self.current_summary = await self.compressor.compress(combined)
        self.processed_count += len(new_messages)
        
        return self.current_summary
    
    def get_summary(self) -> str:
        """获取当前摘要"""
        return self.current_summary
    
    def reset(self):
        """重置压缩器"""
        self.current_summary = ""
        self.processed_count = 0


def compress_text(text: str, max_tokens: int = 500) -> str:
    """
    快捷函数: 压缩文本
    
    Args:
        text: 输入文本
        max_tokens: 最大Token数
        
    Returns:
        str: 压缩后的文本
    """
    current_tokens = count_tokens(text)
    
    if current_tokens <= max_tokens:
        return text
    
    # 简单截断
    ratio = max_tokens / current_tokens
    cut_pos = int(len(text) * ratio * 0.9)
    
    # 在句子边界截断
    sentence_ends = ['.', '。', '!', '?', '\n']
    for i in range(cut_pos, max(0, cut_pos - 100), -1):
        if text[i] in sentence_ends:
            return text[:i+1] + "\n[...]"
    
    return text[:cut_pos] + "..."

