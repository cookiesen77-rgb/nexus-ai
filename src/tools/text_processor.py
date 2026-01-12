"""
文本处理工具

提供文本分析和处理功能
"""

import re
import json
from typing import Any, Dict, List
from collections import Counter

from .base import BaseTool, ToolResult, ToolStatus


class TextProcessorTool(BaseTool):
    """文本处理工具"""

    name = "text_processor"
    description = """文本处理工具，支持多种操作：
- count_words: 统计单词数量
- count_chars: 统计字符数量
- count_lines: 统计行数
- to_upper: 转换为大写
- to_lower: 转换为小写
- find_replace: 查找替换
- extract_emails: 提取邮箱
- extract_urls: 提取URL
- word_frequency: 词频统计
- summary_stats: 文本统计摘要
"""

    parameters = {
        "properties": {
            "text": {
                "type": "string",
                "description": "要处理的文本"
            },
            "operation": {
                "type": "string",
                "description": "操作类型: count_words, count_chars, count_lines, to_upper, to_lower, find_replace, extract_emails, extract_urls, word_frequency, summary_stats",
                "enum": [
                    "count_words", "count_chars", "count_lines",
                    "to_upper", "to_lower", "find_replace",
                    "extract_emails", "extract_urls", "word_frequency", "summary_stats"
                ]
            },
            "find": {
                "type": "string",
                "description": "查找的文本（仅用于find_replace操作）"
            },
            "replace": {
                "type": "string",
                "description": "替换的文本（仅用于find_replace操作）"
            }
        },
        "required": ["text", "operation"]
    }

    async def execute(
        self,
        text: str,
        operation: str,
        find: str = None,
        replace: str = None
    ) -> ToolResult:
        """
        执行文本处理操作

        Args:
            text: 要处理的文本
            operation: 操作类型
            find: 查找文本（可选）
            replace: 替换文本（可选）

        Returns:
            ToolResult: 处理结果
        """
        try:
            result = None

            if operation == "count_words":
                result = self._count_words(text)

            elif operation == "count_chars":
                result = self._count_chars(text)

            elif operation == "count_lines":
                result = self._count_lines(text)

            elif operation == "to_upper":
                result = text.upper()

            elif operation == "to_lower":
                result = text.lower()

            elif operation == "find_replace":
                if find is None:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output=None,
                        error="Parameter 'find' is required for find_replace operation"
                    )
                result = self._find_replace(text, find, replace or "")

            elif operation == "extract_emails":
                result = self._extract_emails(text)

            elif operation == "extract_urls":
                result = self._extract_urls(text)

            elif operation == "word_frequency":
                result = self._word_frequency(text)

            elif operation == "summary_stats":
                result = self._summary_stats(text)

            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output=None,
                    error=f"Unknown operation: {operation}"
                )

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=result,
                metadata={"operation": operation}
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=str(e)
            )

    def _count_words(self, text: str) -> Dict[str, int]:
        """统计单词数量"""
        words = text.split()
        return {
            "total_words": len(words),
            "unique_words": len(set(words))
        }

    def _count_chars(self, text: str) -> Dict[str, int]:
        """统计字符数量"""
        return {
            "total_chars": len(text),
            "chars_no_spaces": len(text.replace(" ", "")),
            "spaces": text.count(" ")
        }

    def _count_lines(self, text: str) -> Dict[str, int]:
        """统计行数"""
        lines = text.split("\n")
        non_empty = [l for l in lines if l.strip()]
        return {
            "total_lines": len(lines),
            "non_empty_lines": len(non_empty),
            "empty_lines": len(lines) - len(non_empty)
        }

    def _find_replace(self, text: str, find: str, replace: str) -> Dict[str, Any]:
        """查找替换"""
        count = text.count(find)
        result = text.replace(find, replace)
        return {
            "result": result,
            "replacements": count
        }

    def _extract_emails(self, text: str) -> List[str]:
        """提取邮箱地址"""
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return re.findall(pattern, text)

    def _extract_urls(self, text: str) -> List[str]:
        """提取URL"""
        pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return re.findall(pattern, text)

    def _word_frequency(self, text: str, top_n: int = 10) -> Dict[str, int]:
        """词频统计"""
        # 清理文本
        words = re.findall(r'\b\w+\b', text.lower())
        counter = Counter(words)
        return dict(counter.most_common(top_n))

    def _summary_stats(self, text: str) -> Dict[str, Any]:
        """文本统计摘要"""
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        paragraphs = text.split("\n\n")
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        return {
            "characters": len(text),
            "words": len(words),
            "sentences": len(sentences),
            "paragraphs": len(paragraphs),
            "avg_word_length": round(sum(len(w) for w in words) / len(words), 2) if words else 0,
            "avg_sentence_length": round(len(words) / len(sentences), 2) if sentences else 0
        }


# 创建全局实例
text_processor = TextProcessorTool()

