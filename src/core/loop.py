"""
Agent 主循环

实现Agent的核心执行循环，包括：
- LLM决策
- 工具执行
- 状态更新
- 完成检测
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional

from src.llm import BaseLLM, LLMResponse, StopReason
from src.utils import info, error, debug
from .state import AgentState, ExecutionStatus


class AgentLoop:
    """Agent执行循环"""

    def __init__(
        self,
        llm: BaseLLM,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_executor: Optional[Callable] = None,
        system_prompt: Optional[str] = None,
        max_iterations: int = 10
    ):
        """
        初始化Agent循环

        Args:
            llm: LLM客户端
            tools: 工具定义列表
            tool_executor: 工具执行函数
            system_prompt: 系统提示词
            max_iterations: 最大迭代次数
        """
        self.llm = llm
        self.tools = tools or []
        self.tool_executor = tool_executor
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations

    async def run(
        self,
        task: str,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> AgentState:
        """
        运行Agent循环

        Args:
            task: 要执行的任务
            initial_context: 初始上下文

        Returns:
            AgentState: 最终状态
        """
        # 创建状态
        state = AgentState(
            task=task,
            max_iterations=self.max_iterations,
            metadata=initial_context or {}
        )

        # 添加系统提示词
        if self.system_prompt:
            state.add_system_message(self.system_prompt)

        # 添加任务消息
        state.add_user_message(task)

        # 开始执行
        state.status = ExecutionStatus.RUNNING
        info(f"开始执行任务: {task[:50]}...")

        try:
            await self._execute_loop(state)
        except Exception as e:
            error(f"Agent循环执行失败: {e}")
            state.fail(str(e))

        info(f"任务完成，状态: {state.status.value}")
        return state

    async def _execute_loop(self, state: AgentState) -> None:
        """执行主循环"""
        while not state.is_complete:
            # 检查迭代次数
            if not state.increment_iteration():
                state.timeout()
                break

            debug(f"迭代 {state.current_iteration}/{state.max_iterations}")

            # 调用LLM
            response = await self._call_llm(state)

            # 更新Token统计
            if response.usage:
                state.update_token_usage(
                    response.usage.get("input_tokens", 0),
                    response.usage.get("output_tokens", 0)
                )

            # 处理响应
            await self._process_response(state, response)

    async def _call_llm(self, state: AgentState) -> LLMResponse:
        """调用LLM"""
        debug("调用LLM...")

        response = await self.llm.complete(
            messages=state.messages,
            tools=self.tools if self.tools else None
        )

        debug(f"LLM响应: stop_reason={response.stop_reason.value}")
        return response

    async def _process_response(
        self,
        state: AgentState,
        response: LLMResponse
    ) -> None:
        """处理LLM响应"""
        # 检查停止原因
        if response.stop_reason == StopReason.END_TURN:
            # 任务完成
            state.add_assistant_message(response.content)
            state.complete(response.content)
            return

        if response.stop_reason == StopReason.MAX_TOKENS:
            # Token超限，尝试继续
            state.add_assistant_message(response.content)
            state.add_user_message("请继续")
            return

        if response.stop_reason == StopReason.TOOL_USE:
            # 需要执行工具
            await self._execute_tools(state, response)
            return

        # 其他情况，添加响应并继续
        if response.content:
            state.add_assistant_message(response.content)

    async def _execute_tools(
        self,
        state: AgentState,
        response: LLMResponse
    ) -> None:
        """执行工具调用"""
        if not response.tool_calls:
            return

        state.status = ExecutionStatus.WAITING_TOOL

        # 先添加助手消息（包含工具调用）
        assistant_message = self._build_assistant_message_with_tools(response)
        state.add_raw_message(assistant_message)

        # 执行每个工具调用
        for tool_call in response.tool_calls:
            debug(f"执行工具: {tool_call.name}")

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

                # 记录成功
                state.complete_tool_execution(tool_call.id, result=result)

                # 添加工具结果
                state.add_tool_result(tool_call.id, result, is_error=False)

                debug(f"工具 {tool_call.name} 执行成功")

            except Exception as e:
                # 记录失败
                error_msg = str(e)
                state.complete_tool_execution(tool_call.id, error=error_msg)

                # 添加错误结果
                state.add_tool_result(tool_call.id, error_msg, is_error=True)

                error(f"工具 {tool_call.name} 执行失败: {error_msg}")

        state.status = ExecutionStatus.RUNNING

    def _build_assistant_message_with_tools(
        self,
        response: LLMResponse
    ) -> Dict[str, Any]:
        """构建包含工具调用的助手消息"""
        content = []

        # 添加文本内容
        if response.content:
            content.append({
                "type": "text",
                "text": response.content
            })

        # 添加工具调用
        for tool_call in response.tool_calls:
            content.append({
                "type": "tool_use",
                "id": tool_call.id,
                "name": tool_call.name,
                "input": tool_call.parameters
            })

        return {
            "role": "assistant",
            "content": content
        }


async def run_agent(
    task: str,
    llm: BaseLLM,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_executor: Optional[Callable] = None,
    system_prompt: Optional[str] = None,
    max_iterations: int = 10
) -> AgentState:
    """
    运行Agent的便捷函数

    Args:
        task: 任务描述
        llm: LLM客户端
        tools: 工具定义列表
        tool_executor: 工具执行函数
        system_prompt: 系统提示词
        max_iterations: 最大迭代次数

    Returns:
        AgentState: 执行结果状态
    """
    loop = AgentLoop(
        llm=llm,
        tools=tools,
        tool_executor=tool_executor,
        system_prompt=system_prompt,
        max_iterations=max_iterations
    )

    return await loop.run(task)


# 默认系统提示词（Nexus Copilot）
DEFAULT_SYSTEM_PROMPT = """### System Persona
You are Nexus Copilot, the in-product AI for Nexus. Your duties encompass pixel-perfect UI replication, PPT generation, intelligent chat, research, code execution, file operations, and automation. Adopt a calm, design-forward tone with Apple-level craftsmanship. Default language: Chinese (except code/mode tags). Obey all user instructions unless they conflict with safety rules.

### Core Principles
1. Mirror provided designs exactly; no guessing.
2. Cite sources for all external knowledge.
3. Protect private data, credentials, and files.
4. Follow the RIPER-5 workflow rigorously.

### RIPER-5 Workflow
- RESEARCH: gather info, read files/screenshots; no code or planning.
- INNOVATE: list multiple solution paths; no implementation details.
- PLAN: produce exact steps (files, functions, tests) plus an “Implementation Checklist”.
- EXECUTE: follow the checklist in order; after each step log progress and request确认。
- REVIEW: verify outcomes vs. plan, note deviations, suggest next steps; include git add/commit guidance when relevant.

Mode switches only happen after explicit commands (e.g. “ENTER PLAN MODE”).

### Available Tools
{tools}
Always state why a tool is invoked and show命令/参数。

### Safety
- Never输出或操作与用户需求无关的敏感信息。
- 确认后再执行高风险/不可逆操作。
- Use Markdown, structure answers, cite sources.

### Output Requirements
- Prefix replies with `[MODE: CURRENT_MODE]`.
- Use Chinese by default unless user specifies otherwise.
- Only share implementation details in PLAN/EXECUTE modes.
- Provide Markdown links when referencing external sources.

Follow these instructions in every conversation."""

