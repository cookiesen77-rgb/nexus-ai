"""
简单Agent实现

一个功能完整的单Agent实现，支持：
- 工具调用
- 多轮对话
- 任务执行
"""

from typing import Any, Callable, Dict, List, Optional

from src.llm import BaseLLM, StopReason
from src.core.state import AgentState, ExecutionStatus
from src.utils import info, error, debug
from .base import BaseAgent, AgentConfig, AgentResult


class SimpleAgent(BaseAgent):
    """简单Agent"""

    def __init__(
        self,
        config: AgentConfig,
        llm: BaseLLM,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_executor: Optional[Callable] = None
    ):
        """
        初始化SimpleAgent

        Args:
            config: Agent配置
            llm: LLM客户端
            tools: 工具定义列表
            tool_executor: 工具执行函数
        """
        super().__init__(config, llm, tools)
        self.tool_executor = tool_executor

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
        # 创建状态
        state = AgentState(
            task=task,
            max_iterations=self.config.max_iterations,
            metadata=context or {}
        )

        # 初始化消息
        system_prompt = self.get_system_prompt()
        if system_prompt:
            state.add_system_message(system_prompt)

        # 添加历史上下文
        if context and "history" in context:
            for msg in context["history"]:
                state.add_raw_message(msg)

        # 添加任务
        state.add_user_message(task)

        info(f"[{self.name}] 开始执行任务: {task[:50]}...")
        state.status = ExecutionStatus.RUNNING

        try:
            # 执行循环
            while not state.is_complete:
                state = await self.step(state)

            # 返回结果
            return AgentResult(
                success=state.is_success,
                output=state.final_result,
                error=state.error,
                state=state,
                metadata={
                    "iterations": state.current_iteration,
                    "input_tokens": state.total_input_tokens,
                    "output_tokens": state.total_output_tokens,
                    "tool_calls": len(state.tool_executions)
                }
            )

        except Exception as e:
            error(f"[{self.name}] 执行失败: {e}")
            return AgentResult(
                success=False,
                output=None,
                error=str(e),
                state=state
            )

    async def step(self, state: AgentState) -> AgentState:
        """
        执行单步

        Args:
            state: 当前状态

        Returns:
            AgentState: 更新后的状态
        """
        # 检查迭代次数
        if not state.increment_iteration():
            state.timeout()
            return state

        debug(f"[{self.name}] 迭代 {state.current_iteration}/{state.max_iterations}")

        # 调用LLM
        response = await self.think(state.messages)

        # 更新Token统计
        if response.usage:
            state.update_token_usage(
                response.usage.get("input_tokens", 0),
                response.usage.get("output_tokens", 0)
            )

        # 处理响应
        if response.stop_reason == StopReason.END_TURN:
            # 任务完成
            state.add_assistant_message(response.content)
            state.complete(response.content)

        elif response.stop_reason == StopReason.TOOL_USE:
            # 执行工具
            await self._handle_tool_calls(state, response)

        elif response.stop_reason == StopReason.MAX_TOKENS:
            # Token超限
            state.add_assistant_message(response.content)
            state.add_user_message("请继续")

        else:
            # 其他情况
            if response.content:
                state.add_assistant_message(response.content)

        return state

    async def _handle_tool_calls(self, state: AgentState, response) -> None:
        """处理工具调用"""
        if not response.tool_calls:
            return

        state.status = ExecutionStatus.WAITING_TOOL

        # 添加助手消息
        assistant_content = []
        if response.content:
            assistant_content.append({"type": "text", "text": response.content})

        for tool_call in response.tool_calls:
            assistant_content.append({
                "type": "tool_use",
                "id": tool_call.id,
                "name": tool_call.name,
                "input": tool_call.parameters
            })

        state.add_raw_message({
            "role": "assistant",
            "content": assistant_content
        })

        # 执行工具
        for tool_call in response.tool_calls:
            debug(f"[{self.name}] 执行工具: {tool_call.name}")

            # 记录执行
            execution = state.record_tool_execution(
                tool_id=tool_call.id,
                name=tool_call.name,
                parameters=tool_call.parameters
            )

            try:
                # 执行工具
                if self.tool_executor:
                    result = await self.tool_executor(
                        tool_call.name,
                        tool_call.parameters
                    )
                else:
                    result = f"Tool '{tool_call.name}' not implemented"

                state.complete_tool_execution(tool_call.id, result=result)
                state.add_tool_result(tool_call.id, result, is_error=False)

                info(f"[{self.name}] 工具 {tool_call.name} 执行成功")

            except Exception as e:
                error_msg = str(e)
                state.complete_tool_execution(tool_call.id, error=error_msg)
                state.add_tool_result(tool_call.id, error_msg, is_error=True)

                error(f"[{self.name}] 工具 {tool_call.name} 执行失败: {error_msg}")

        state.status = ExecutionStatus.RUNNING

    def _default_system_prompt(self) -> str:
        """默认系统提示词"""
        tools_desc = ""
        if self.tools:
            tools_desc = "\n可用工具:\n"
            for tool in self.tools:
                tools_desc += f"- {tool['name']}: {tool.get('description', '')}\n"

        return f"""你是 {self.name}，一个能够使用工具完成任务的智能助手。
{tools_desc}
执行规则:
1. 仔细分析用户需求
2. 选择合适的工具执行任务
3. 根据工具结果调整策略
4. 完成任务后给出清晰总结

请始终保持专业和准确。"""


def create_simple_agent(
    name: str = "SimpleAgent",
    llm: BaseLLM = None,
    tools: List[Dict[str, Any]] = None,
    tool_executor: Callable = None,
    max_iterations: int = 10,
    temperature: float = 0.7,
    system_prompt: str = None
) -> SimpleAgent:
    """
    创建SimpleAgent的便捷函数

    Args:
        name: Agent名称
        llm: LLM客户端
        tools: 工具列表
        tool_executor: 工具执行函数
        max_iterations: 最大迭代次数
        temperature: 温度参数
        system_prompt: 系统提示词

    Returns:
        SimpleAgent: Agent实例
    """
    config = AgentConfig(
        name=name,
        max_iterations=max_iterations,
        temperature=temperature,
        system_prompt=system_prompt
    )

    return SimpleAgent(
        config=config,
        llm=llm,
        tools=tools,
        tool_executor=tool_executor
    )

