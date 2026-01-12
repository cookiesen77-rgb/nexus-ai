#!/bin/bash

# Manus AI Agent - 项目结构初始化脚本

echo "🚀 正在创建项目结构..."

# 创建主要目录
mkdir -p src/{agents,tools,execution,context,llm,utils}
mkdir -p tests/{unit,integration,e2e}
mkdir -p examples
mkdir -p docs
mkdir -p logs
mkdir -p data
mkdir -p scripts
mkdir -p config

echo "✅ 目录结构创建完成"

# 创建 __init__.py 文件
touch src/__init__.py
touch src/agents/__init__.py
touch src/tools/__init__.py
touch src/execution/__init__.py
touch src/context/__init__.py
touch src/llm/__init__.py
touch src/utils/__init__.py
touch tests/__init__.py

echo "✅ Python包初始化完成"

# 创建基础文件
cat > src/agents/base.py << 'EOF'
"""
Agent基类定义
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseAgent(ABC):
    """Agent基类"""

    def __init__(self, name: str, model: str = "claude-3-5-sonnet-20241022"):
        self.name = name
        self.model = model

    @abstractmethod
    async def execute(self, task: str, context: Dict[str, Any]) -> Any:
        """执行任务"""
        pass
EOF

cat > src/tools/base.py << 'EOF'
"""
工具基类定义
"""
from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel


class Tool(BaseModel):
    """工具基类"""
    name: str
    description: str
    parameters: Dict[str, Any]

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """执行工具"""
        pass
EOF

cat > src/llm/client.py << 'EOF'
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
EOF

cat > src/utils/config.py << 'EOF'
"""
配置加载工具
"""
import yaml
import os
from pathlib import Path


def load_config(config_path: str = "config.yaml") -> dict:
    """加载YAML配置"""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(path) as f:
        config = yaml.safe_load(f)

    # 环境变量替换
    return _replace_env_vars(config)


def _replace_env_vars(config: dict) -> dict:
    """替换环境变量"""
    if isinstance(config, dict):
        return {k: _replace_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_replace_env_vars(item) for item in config]
    elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
        env_var = config[2:-1]
        return os.getenv(env_var, config)
    return config
EOF

cat > tests/conftest.py << 'EOF'
"""
Pytest配置
"""
import pytest


@pytest.fixture
def mock_llm_client():
    """Mock LLM客户端"""
    pass
EOF

cat > examples/hello_agent.py << 'EOF'
"""
Hello World Agent示例
"""
import asyncio
from anthropic import Anthropic
import os


async def main():
    client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": "Hello! 请用一句话介绍你自己。"}
        ]
    )

    print(f"🤖 Claude: {response.content[0].text}")


if __name__ == "__main__":
    asyncio.run(main())
EOF

echo "✅ 基础文件创建完成"

# 显示目录树
echo ""
echo "📁 项目结构:"
tree -L 2 -I '__pycache__|*.pyc|venv|.git' || ls -R

echo ""
echo "🎉 项目初始化完成!"
echo ""
echo "下一步:"
echo "1. source venv/bin/activate"
echo "2. pip install -r requirements.txt"
echo "3. cp .env.example .env"
echo "4. 编辑 .env 添加API keys"
echo "5. python examples/hello_agent.py"
