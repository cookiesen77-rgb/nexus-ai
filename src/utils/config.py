"""
配置加载工具

支持：
- YAML配置文件加载
- 环境变量替换
- 配置验证
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field


class LLMProviderConfig(BaseModel):
    """LLM提供者配置"""
    provider: str
    model: str
    api_key: str = ""
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096


class LLMConfig(BaseModel):
    """LLM配置"""
    primary: LLMProviderConfig
    fallback: Optional[LLMProviderConfig] = None


class AgentConfig(BaseModel):
    """Agent配置"""
    enabled: bool = True
    max_iterations: int = 10
    timeout: int = 300
    model: str = "claude-sonnet-4-5-20250514"
    temperature: float = 0.7


class AgentsConfig(BaseModel):
    """Agents配置集合"""
    planner: AgentConfig = Field(default_factory=AgentConfig)
    executor: AgentConfig = Field(default_factory=AgentConfig)
    verifier: AgentConfig = Field(default_factory=AgentConfig)


class ToolsConfig(BaseModel):
    """工具配置"""
    enabled: list = Field(default_factory=list)
    web_search: Dict[str, Any] = Field(default_factory=dict)
    file_operations: Dict[str, Any] = Field(default_factory=dict)


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = "INFO"
    format: str = "json"
    output: str = "stdout"
    file: Dict[str, Any] = Field(default_factory=dict)


class AppConfig(BaseModel):
    """应用配置"""
    llm: LLMConfig
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    加载YAML配置文件

    Args:
        config_path: 配置文件路径

    Returns:
        Dict: 配置字典
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 替换环境变量
    return _replace_env_vars(config)


def _replace_env_vars(config: Any) -> Any:
    """
    递归替换配置中的环境变量

    支持格式: ${ENV_VAR_NAME}
    """
    if isinstance(config, dict):
        return {k: _replace_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_replace_env_vars(item) for item in config]
    elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
        env_var = config[2:-1]
        return os.getenv(env_var, "")
    return config


def get_config(config_path: str = "config.yaml") -> AppConfig:
    """
    获取类型化的配置对象

    Args:
        config_path: 配置文件路径

    Returns:
        AppConfig: 配置对象
    """
    raw_config = load_config(config_path)
    return AppConfig(**raw_config)


# 全局配置实例
_config: Optional[AppConfig] = None


def init_config(config_path: str = "config.yaml") -> AppConfig:
    """初始化全局配置"""
    global _config
    _config = get_config(config_path)
    return _config


def get_global_config() -> Optional[AppConfig]:
    """获取全局配置实例"""
    return _config
