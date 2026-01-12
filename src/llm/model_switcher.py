"""
模型切换器 - 动态切换默认模型和思考模型

支持:
- 全局思考模式开关
- 上下文管理器临时切换
- Agent级别的模型配置
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from contextlib import contextmanager

from .base import LLMConfig


@dataclass
class ModelConfig:
    """模型配置"""
    default_model: str
    thinking_model: str
    base_url: str
    api_key: str
    temperature: float = 0.7
    max_tokens: int = 4096


class ModelSwitcher:
    """
    模型切换器
    
    管理默认模型和思考模型之间的切换
    
    Usage:
        switcher = ModelSwitcher.from_env()
        
        # 获取当前模型
        model = switcher.get_current_model()
        
        # 启用思考模式
        switcher.enable_thinking()
        
        # 临时切换
        with switcher.thinking():
            # 使用思考模型
            pass
    """
    
    def __init__(self, config: ModelConfig):
        """
        初始化模型切换器
        
        Args:
            config: 模型配置
        """
        self.config = config
        self._thinking_mode = False
    
    @classmethod
    def from_env(cls) -> "ModelSwitcher":
        """从环境变量创建切换器"""
        config = ModelConfig(
            default_model=os.getenv("LLM_DEFAULT_MODEL", "doubao-seed-1-8-251228"),
            thinking_model=os.getenv("LLM_THINKING_MODEL", "doubao-seed-1-8-251228-thinking"),
            base_url=os.getenv("ALLAPI_BASE_URL", "https://nexusapi.cn/v1"),
            api_key=os.getenv("ALLAPI_KEY", ""),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
        )
        return cls(config)
    
    @classmethod
    def from_yaml(cls, config_dict: Dict[str, Any]) -> "ModelSwitcher":
        """从YAML配置创建切换器"""
        llm_config = config_dict.get("llm", {})
        models = llm_config.get("models", {})
        
        config = ModelConfig(
            default_model=models.get("default", "doubao-seed-1-8-251228"),
            thinking_model=models.get("thinking", "doubao-seed-1-8-251228-thinking"),
            base_url=llm_config.get("base_url", "https://nexusapi.cn/v1"),
            api_key=llm_config.get("api_key", os.getenv("ALLAPI_KEY", "")),
            temperature=llm_config.get("temperature", 0.7),
            max_tokens=llm_config.get("max_tokens", 4096),
        )
        
        switcher = cls(config)
        switcher._thinking_mode = llm_config.get("thinking_mode", False)
        
        return switcher
    
    @property
    def thinking_mode(self) -> bool:
        """获取当前思考模式状态"""
        return self._thinking_mode
    
    @thinking_mode.setter
    def thinking_mode(self, value: bool):
        """设置思考模式"""
        self._thinking_mode = value
    
    def enable_thinking(self):
        """启用思考模式"""
        self._thinking_mode = True
    
    def disable_thinking(self):
        """禁用思考模式"""
        self._thinking_mode = False
    
    def toggle_thinking(self) -> bool:
        """切换思考模式，返回新状态"""
        self._thinking_mode = not self._thinking_mode
        return self._thinking_mode
    
    def get_current_model(self) -> str:
        """获取当前活跃模型名称"""
        if self._thinking_mode:
            return self.config.thinking_model
        return self.config.default_model
    
    def get_model_for_task(self, use_thinking: bool = None) -> str:
        """
        根据任务需求获取模型
        
        Args:
            use_thinking: 是否使用思考模型，None则使用全局设置
        """
        if use_thinking is None:
            use_thinking = self._thinking_mode
        
        if use_thinking:
            return self.config.thinking_model
        return self.config.default_model
    
    @contextmanager
    def thinking(self):
        """
        临时启用思考模式的上下文管理器
        
        Usage:
            with switcher.thinking():
                # 在这里使用思考模型
                response = llm.complete(messages)
        """
        previous_state = self._thinking_mode
        self._thinking_mode = True
        try:
            yield self
        finally:
            self._thinking_mode = previous_state
    
    @contextmanager
    def default(self):
        """
        临时使用默认模型的上下文管理器
        
        Usage:
            with switcher.default():
                # 在这里使用默认模型
                response = llm.complete(messages)
        """
        previous_state = self._thinking_mode
        self._thinking_mode = False
        try:
            yield self
        finally:
            self._thinking_mode = previous_state
    
    def create_llm_config(self, use_thinking: bool = None) -> LLMConfig:
        """
        创建LLM配置
        
        Args:
            use_thinking: 是否使用思考模型
            
        Returns:
            LLMConfig: LLM配置对象
        """
        model = self.get_model_for_task(use_thinking)
        
        return LLMConfig(
            model=model,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            thinking_model=self.config.thinking_model,
            thinking_mode=use_thinking if use_thinking is not None else self._thinking_mode
        )
    
    def get_status(self) -> Dict[str, Any]:
        """获取切换器状态"""
        return {
            "thinking_mode": self._thinking_mode,
            "current_model": self.get_current_model(),
            "default_model": self.config.default_model,
            "thinking_model": self.config.thinking_model,
            "base_url": self.config.base_url,
        }
    
    def __repr__(self) -> str:
        mode = "thinking" if self._thinking_mode else "default"
        return f"ModelSwitcher(mode={mode}, model={self.get_current_model()})"


# 全局切换器实例
_global_switcher: Optional[ModelSwitcher] = None


def get_model_switcher() -> ModelSwitcher:
    """获取全局模型切换器"""
    global _global_switcher
    if _global_switcher is None:
        _global_switcher = ModelSwitcher.from_env()
    return _global_switcher


def set_model_switcher(switcher: ModelSwitcher):
    """设置全局模型切换器"""
    global _global_switcher
    _global_switcher = switcher


def enable_thinking_mode():
    """启用全局思考模式"""
    get_model_switcher().enable_thinking()


def disable_thinking_mode():
    """禁用全局思考模式"""
    get_model_switcher().disable_thinking()


def get_current_model() -> str:
    """获取当前模型"""
    return get_model_switcher().get_current_model()

