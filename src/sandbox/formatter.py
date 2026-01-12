"""
执行结果格式化
"""

from typing import Optional
from .models import ExecutionResult, ExecutionStatus
from .errors import ErrorClassifier


class ResultFormatter:
    """执行结果格式化器"""
    
    @staticmethod
    def to_text(result: ExecutionResult, verbose: bool = False) -> str:
        """
        格式化为纯文本
        
        Args:
            result: 执行结果
            verbose: 是否包含详细信息
            
        Returns:
            str: 格式化的文本
        """
        lines = []
        
        # 状态行
        status_emoji = {
            ExecutionStatus.SUCCESS: '✅',
            ExecutionStatus.ERROR: '❌',
            ExecutionStatus.TIMEOUT: '⏱️',
            ExecutionStatus.MEMORY_EXCEEDED: '💾',
            ExecutionStatus.SECURITY_VIOLATION: '🔒',
            ExecutionStatus.CANCELLED: '🚫',
        }
        
        emoji = status_emoji.get(result.status, '❓')
        lines.append(f"{emoji} Status: {result.status.value}")
        
        # 输出
        if result.output:
            lines.append("\n📤 Output:")
            lines.append(result.output)
        
        # 错误
        if result.error:
            lines.append("\n⚠️ Error:")
            lines.append(result.error)
        
        # 返回值
        if result.return_value is not None:
            lines.append(f"\n📦 Return Value: {result.return_value}")
        
        # 详细信息
        if verbose:
            lines.append("\n📊 Metrics:")
            lines.append(f"  - Execution Time: {result.execution_time:.3f}s")
            lines.append(f"  - Memory Used: {result.memory_used / 1024:.1f} KB")
            lines.append(f"  - Exit Code: {result.exit_code}")
            lines.append(f"  - Sandbox: {result.sandbox_type}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def to_markdown(result: ExecutionResult) -> str:
        """
        格式化为Markdown
        
        Returns:
            str: Markdown格式文本
        """
        lines = []
        
        # 标题
        status_text = "Success" if result.is_success else result.status.value.title()
        lines.append(f"### Execution Result: {status_text}")
        lines.append("")
        
        # 输出代码块
        if result.output:
            lines.append("**Output:**")
            lines.append("```")
            lines.append(result.output)
            lines.append("```")
            lines.append("")
        
        # 错误
        if result.error:
            lines.append("**Error:**")
            lines.append("```")
            lines.append(result.error)
            lines.append("```")
            lines.append("")
        
        # 指标表格
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Status | {result.status.value} |")
        lines.append(f"| Execution Time | {result.execution_time:.3f}s |")
        lines.append(f"| Exit Code | {result.exit_code} |")
        lines.append(f"| Sandbox | {result.sandbox_type} |")
        
        return '\n'.join(lines)
    
    @staticmethod
    def to_json(result: ExecutionResult) -> dict:
        """
        格式化为JSON字典
        
        Returns:
            dict: JSON可序列化的字典
        """
        return {
            'success': result.is_success,
            'status': result.status.value,
            'output': result.output,
            'error': result.error,
            'return_value': result.return_value,
            'metrics': {
                'execution_time': result.execution_time,
                'memory_used': result.memory_used,
                'exit_code': result.exit_code,
            },
            'sandbox_type': result.sandbox_type,
            'timestamps': {
                'started_at': result.started_at.isoformat() if result.started_at else None,
                'finished_at': result.finished_at.isoformat() if result.finished_at else None,
            }
        }
    
    @staticmethod
    def to_llm_context(result: ExecutionResult) -> str:
        """
        格式化为LLM上下文
        
        Returns:
            str: 适合作为LLM上下文的格式
        """
        if result.is_success:
            context = f"Code executed successfully.\n\nOutput:\n{result.output}"
            if result.return_value is not None:
                context += f"\n\nReturn value: {result.return_value}"
        else:
            error_info = ErrorClassifier.format_error(result.error or "Unknown error")
            context = f"Code execution failed with {error_info['type']}.\n\n"
            context += f"Error: {error_info['message']}\n"
            if error_info.get('suggestion'):
                context += f"Suggestion: {error_info['suggestion']}\n"
            if result.output:
                context += f"\nPartial output:\n{result.output}"
        
        return context


class OutputTruncator:
    """输出截断器"""
    
    @staticmethod
    def truncate(
        text: str, 
        max_length: int = 5000,
        max_lines: int = 100,
        indicator: str = "\n... [truncated]"
    ) -> str:
        """
        截断输出
        
        Args:
            text: 原始文本
            max_length: 最大字符数
            max_lines: 最大行数
            indicator: 截断指示符
            
        Returns:
            str: 截断后的文本
        """
        # 按行数截断
        lines = text.split('\n')
        if len(lines) > max_lines:
            text = '\n'.join(lines[:max_lines]) + indicator
        
        # 按长度截断
        if len(text) > max_length:
            text = text[:max_length] + indicator
        
        return text
    
    @staticmethod
    def smart_truncate(
        text: str,
        max_length: int = 5000,
        keep_start: int = 2000,
        keep_end: int = 1000
    ) -> str:
        """
        智能截断，保留开头和结尾
        
        Args:
            text: 原始文本
            max_length: 最大长度
            keep_start: 保留开头字符数
            keep_end: 保留结尾字符数
            
        Returns:
            str: 截断后的文本
        """
        if len(text) <= max_length:
            return text
        
        middle = f"\n\n... [{len(text) - keep_start - keep_end} characters omitted] ...\n\n"
        
        return text[:keep_start] + middle + text[-keep_end:]

