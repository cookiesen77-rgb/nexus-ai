# Manus AI Agent - 快速开始

本指南帮助你快速启动Manus AI Agent项目开发。

## 前置要求

- Python 3.11+
- Docker (可选，用于代码执行沙箱)
- Redis (可选，用于缓存)
- Git

## 安装步骤

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd manus
```

### 2. 创建虚拟环境

```bash
python -m venv venv

# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，添加你的API keys:

```env
CLAUDE_API_KEY=YOUR_CLAUDE_API_KEY
OPENAI_API_KEY=YOUR_OPENAI_API_KEY  # 可选
TAVILY_API_KEY=YOUR_TAVILY_API_KEY  # 可选
```

### 5. 测试安装

```bash
python -c "import anthropic; print('✅ Anthropic installed')"
```

## 快速示例

### 示例1: 简单对话

```python
# examples/simple_chat.py
from anthropic import Anthropic

client = Anthropic()

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello, Claude!"}
    ]
)

print(response.content[0].text)
```

运行:
```bash
python examples/simple_chat.py
```

### 示例2: 工具调用

```python
# examples/tool_use.py
from anthropic import Anthropic

client = Anthropic()

# 定义工具
tools = [
    {
        "name": "get_weather",
        "description": "获取指定城市的天气信息",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称"
                }
            },
            "required": ["city"]
        }
    }
]

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=tools,
    messages=[
        {"role": "user", "content": "北京今天天气怎么样?"}
    ]
)

print(response.content)
```

### 示例3: 基础Agent循环

```python
# examples/basic_agent.py

def agent_loop(task: str, max_iterations: int = 5):
    """基础Agent循环"""
    client = Anthropic()
    messages = []

    for i in range(max_iterations):
        # 发送消息
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            messages=messages + [
                {"role": "user", "content": task}
            ]
        )

        # 检查是否完成
        if response.stop_reason == "end_turn":
            return response.content[0].text

        # 继续循环
        messages.append({
            "role": "assistant",
            "content": response.content
        })

    return "超过最大迭代次数"

# 测试
result = agent_loop("计算1+1等于多少?")
print(result)
```

## 项目结构创建

运行以下命令创建项目基础结构:

```bash
mkdir -p src/{agents,tools,execution,context,llm,utils}
mkdir -p tests/{unit,integration,e2e}
mkdir -p examples
mkdir -p docs
mkdir -p logs
mkdir -p data
```

或使用提供的脚本:

```bash
chmod +x scripts/setup_project.sh
./scripts/setup_project.sh
```

## 开发工作流

### 1. 创建新分支

```bash
git checkout -b feature/your-feature-name
```

### 2. 开发与测试

```bash
# 运行测试
pytest tests/

# 检查代码风格
ruff check src/

# 格式化代码
black src/
```

### 3. 提交代码

```bash
git add .
git commit -m "feat: your feature description"
git push origin feature/your-feature-name
```

## 下一步

1. 阅读 [README.md](README.md) 了解项目架构
2. 查看 [ROADMAP.md](ROADMAP.md) 了解开发计划
3. 开始 Phase 1 开发任务

## 常见问题

### Q: API Key如何获取?

**Claude API**:
1. 访问 https://console.anthropic.com/
2. 创建账号并充值
3. 创建API Key

**Tavily API** (搜索工具):
1. 访问 https://tavily.com/
2. 免费套餐提供1000次/月

### Q: Docker是必需的吗?

不是必需的。你可以选择:
- 使用E2B托管服务 (需要API Key)
- 使用Docker本地运行
- 暂时跳过代码执行功能

### Q: 如何调试?

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 或使用loguru
from loguru import logger
logger.add("debug.log", level="DEBUG")
```

### Q: 成本如何控制?

- 使用缓存减少重复调用
- 限制max_tokens
- 监控token使用量
- 本地开发时使用较小的模型

## 资源链接

- [Claude API文档](https://docs.anthropic.com/)
- [Tool Use指南](https://docs.anthropic.com/claude/docs/tool-use)
- [项目GitHub](https://github.com/your-repo)
- [问题追踪](https://github.com/your-repo/issues)

## 获取帮助

- 查看文档: `docs/`
- 提交Issue: GitHub Issues
- 讨论区: GitHub Discussions

---

**祝开发顺利!** 🚀
