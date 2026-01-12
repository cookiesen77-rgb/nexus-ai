"""
Agent 基类定义

定义所有Agent的通用接口和基础功能
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.llm import BaseLLM, LLMResponse
from src.core.state import AgentState


@dataclass
class AgentConfig:
    """Agent配置"""
    name: str
    model: str = "claude-sonnet-4-5-20250514"
    temperature: float = 0.7
    max_iterations: int = 10
    timeout: int = 300
    system_prompt: Optional[str] = None


@dataclass
class AgentResult:
    """Agent执行结果"""
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    state: Optional[AgentState] = None


class BaseAgent(ABC):
    """Agent基类"""

    def __init__(
        self,
        config: AgentConfig,
        llm: BaseLLM,
        tools: Optional[List[Dict[str, Any]]] = None
    ):
        """
        初始化Agent

        Args:
            config: Agent配置
            llm: LLM客户端
            tools: 可用工具列表
        """
        self.config = config
        self.name = config.name
        self.llm = llm
        self.tools = tools or []

    @abstractmethod
    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """
        执行任务

        Args:
            task: 任务描述
            context: 上下文信息

        Returns:
            AgentResult: 执行结果
        """
        pass

    @abstractmethod
    async def step(self, state: AgentState) -> AgentState:
        """
        执行单步

        Args:
            state: 当前状态

        Returns:
            AgentState: 更新后的状态
        """
        pass

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        if self.config.system_prompt:
            return self.config.system_prompt
        return self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        """默认系统提示词"""
        return f"""你是 {self.name}，一个智能AI助手。
请仔细分析用户的需求，并提供准确、有帮助的回答。"""

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """获取工具Schema列表"""
        return self.tools

    async def think(
        self,
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> LLMResponse:
        """
        调用LLM进行思考

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            LLMResponse: LLM响应
        """
        return await self.llm.complete(
            messages=messages,
            tools=self.tools if self.tools else None,
            temperature=self.config.temperature,
            **kwargs
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, model={self.config.model})"


class ConversationalAgent(BaseAgent):
    """对话型Agent"""

    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """执行对话任务"""
        messages = []

        # 添加系统提示词
        system_prompt = self.get_system_prompt()
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 添加上下文
        if context and "history" in context:
            messages.extend(context["history"])

        # 添加当前任务
        messages.append({"role": "user", "content": task})

        try:
            response = await self.think(messages)

            return AgentResult(
                success=True,
                output=response.content,
                metadata={
                    "usage": response.usage,
                    "model": response.model
                }
            )

        except Exception as e:
            return AgentResult(
                success=False,
                output=None,
                error=str(e)
            )

    async def step(self, state: AgentState) -> AgentState:
        """执行单步对话"""
        response = await self.think(state.messages)

        state.add_assistant_message(response.content)
        state.update_token_usage(
            response.usage.get("input_tokens", 0),
            response.usage.get("output_tokens", 0)
        )

        return state
