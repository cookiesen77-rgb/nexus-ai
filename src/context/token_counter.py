"""
Token计数器 - 精确计算Token数量
"""

import re
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass
class TokenUsage:
    """Token使用统计"""
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0
    
    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens


@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    max_tokens: int
    cost_per_1k_input: float
    cost_per_1k_output: float
    encoding: str = "cl100k_base"


# 模型配置表
MODEL_CONFIGS = {
    # Doubao (豆包) - ALLAPI 主要模型
    "doubao-seed-1-8-251228": ModelConfig(
        name="Doubao Seed 1.8 (默认)",
        max_tokens=128000,
        cost_per_1k_input=0.001,
        cost_per_1k_output=0.002,
        encoding="cl100k_base"
    ),
    "doubao-seed-1-8-251228-thinking": ModelConfig(
        name="Doubao Seed 1.8 (思考)",
        max_tokens=128000,
        cost_per_1k_input=0.002,
        cost_per_1k_output=0.004,
        encoding="cl100k_base"
    ),
    
    # Claude 系列 (备用)
    "claude-sonnet-4-5-20250929": ModelConfig(
        name="Claude 4.5 Sonnet",
        max_tokens=200000,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        encoding="cl100k_base"
    ),
    "claude-haiku-4-5-20251001": ModelConfig(
        name="Claude 4.5 Haiku",
        max_tokens=200000,
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125,
        encoding="cl100k_base"
    ),
    
    # GPT 系列 (备用)
    "gpt-4": ModelConfig(
        name="GPT-4",
        max_tokens=128000,
        cost_per_1k_input=0.03,
        cost_per_1k_output=0.06,
        encoding="cl100k_base"
    ),
    "gpt-4o": ModelConfig(
        name="GPT-4o",
        max_tokens=128000,
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.015,
        encoding="cl100k_base"
    ),
}


class TokenCounter:
    """Token计数器"""
    
    def __init__(self, model: str = "claude-sonnet-4-5-20250929"):
        """
        初始化Token计数器
        
        Args:
            model: 模型名称
        """
        self.model = model
        self.config = MODEL_CONFIGS.get(model, MODEL_CONFIGS["claude-sonnet-4-5-20250929"])
        self._encoder = None
    
    def _get_encoder(self):
        """获取tiktoken编码器"""
        if self._encoder is None:
            try:
                import tiktoken
                self._encoder = tiktoken.get_encoding(self.config.encoding)
            except ImportError:
                # 如果没有tiktoken，使用估算
                self._encoder = None
        return self._encoder
    
    def count(self, text: str) -> int:
        """
        计算文本的Token数量
        
        Args:
            text: 输入文本
            
        Returns:
            int: Token数量
        """
        if not text:
            return 0
        
        encoder = self._get_encoder()
        if encoder:
            return len(encoder.encode(text))
        else:
            # 粗略估算: 英文约4字符/token, 中文约2字符/token
            return self._estimate_tokens(text)
    
    def _estimate_tokens(self, text: str) -> int:
        """估算Token数量"""
        # 分离中英文
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_chars = len(text) - chinese_chars
        
        # 中文约1.5个字符一个token，英文约4个字符一个token
        estimated = (chinese_chars / 1.5) + (other_chars / 4)
        return int(estimated) + 1
    
    def count_messages(self, messages: List[Dict[str, str]]) -> int:
        """
        计算消息列表的Token数量
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            
        Returns:
            int: 总Token数
        """
        total = 0
        for msg in messages:
            # 每条消息有额外开销 (角色标记等)
            total += 4  # 消息格式开销
            total += self.count(msg.get("role", ""))
            total += self.count(msg.get("content", ""))
        
        total += 2  # 会话开始/结束标记
        return total
    
    def get_max_tokens(self) -> int:
        """获取模型最大Token数"""
        return self.config.max_tokens
    
    def estimate_cost(self, usage: TokenUsage) -> float:
        """
        估算API调用成本
        
        Args:
            usage: Token使用统计
            
        Returns:
            float: 预估成本(美元)
        """
        input_cost = (usage.input_tokens / 1000) * self.config.cost_per_1k_input
        output_cost = (usage.output_tokens / 1000) * self.config.cost_per_1k_output
        return input_cost + output_cost
    
    def truncate_to_fit(
        self,
        text: str,
        max_tokens: int,
        suffix: str = "..."
    ) -> str:
        """
        截断文本以适应Token限制
        
        Args:
            text: 输入文本
            max_tokens: 最大Token数
            suffix: 截断后缀
            
        Returns:
            str: 截断后的文本
        """
        if self.count(text) <= max_tokens:
            return text
        
        encoder = self._get_encoder()
        if encoder:
            tokens = encoder.encode(text)
            suffix_tokens = encoder.encode(suffix)
            truncated_tokens = tokens[:max_tokens - len(suffix_tokens)]
            return encoder.decode(truncated_tokens) + suffix
        else:
            # 估算截断位置
            ratio = max_tokens / self.count(text)
            cut_pos = int(len(text) * ratio * 0.9)  # 留10%余量
            return text[:cut_pos] + suffix


class ConversationTokenTracker:
    """对话Token跟踪器"""
    
    def __init__(self, model: str = "claude-sonnet-4-5-20250929"):
        self.counter = TokenCounter(model)
        self.history: List[TokenUsage] = []
        self.session_total = TokenUsage()
    
    def track(
        self,
        input_tokens: int,
        output_tokens: int,
        cached: bool = False
    ) -> TokenUsage:
        """
        记录一次API调用的Token使用
        
        Args:
            input_tokens: 输入Token数
            output_tokens: 输出Token数
            cached: 是否使用缓存
        """
        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=input_tokens if cached else 0
        )
        
        self.history.append(usage)
        
        # 更新会话总计
        self.session_total.input_tokens += input_tokens
        self.session_total.output_tokens += output_tokens
        self.session_total.cached_tokens += usage.cached_tokens
        self.session_total.total_tokens = (
            self.session_total.input_tokens + self.session_total.output_tokens
        )
        
        return usage
    
    def get_session_usage(self) -> TokenUsage:
        """获取会话总使用量"""
        return self.session_total
    
    def get_session_cost(self) -> float:
        """获取会话总成本"""
        return self.counter.estimate_cost(self.session_total)
    
    def reset(self):
        """重置跟踪器"""
        self.history = []
        self.session_total = TokenUsage()


# 全局计数器实例
_default_counter: Optional[TokenCounter] = None


def get_token_counter(model: str = None) -> TokenCounter:
    """获取全局Token计数器"""
    global _default_counter
    if _default_counter is None or (model and model != _default_counter.model):
        _default_counter = TokenCounter(model or "claude-sonnet-4-5-20250929")
    return _default_counter


def count_tokens(text: str, model: str = None) -> int:
    """快捷函数: 计算Token数"""
    return get_token_counter(model).count(text)


def count_message_tokens(messages: List[Dict], model: str = None) -> int:
    """快捷函数: 计算消息Token数"""
    return get_token_counter(model).count_messages(messages)

