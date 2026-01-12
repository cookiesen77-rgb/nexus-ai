"""
工具链编排器 - 组合多个工具执行复杂任务
"""

import asyncio
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from .base import BaseTool, ToolResult, ToolStatus
from .registry import get_global_registry


class ChainStepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ChainStep:
    """工具链步骤"""
    name: str
    tool: str
    params: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None  # 条件表达式
    on_failure: str = "stop"  # stop, continue, retry
    max_retries: int = 0
    output_key: str = None  # 存储输出的键名
    
    # 运行时状态
    status: ChainStepStatus = ChainStepStatus.PENDING
    result: Optional[ToolResult] = None
    retries: int = 0


@dataclass
class ChainContext:
    """工具链上下文"""
    variables: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, ToolResult] = field(default_factory=dict)
    current_step: int = 0
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取变量"""
        return self.variables.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置变量"""
        self.variables[key] = value
    
    def resolve_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """解析参数中的变量引用"""
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("$"):
                var_name = value[1:]
                resolved[key] = self.get(var_name, value)
            else:
                resolved[key] = value
        return resolved


class ToolChain:
    """工具链"""
    
    def __init__(self, name: str = "chain"):
        self.name = name
        self.steps: List[ChainStep] = []
        self.context = ChainContext()
        self._registry = get_global_registry()
    
    def add_step(
        self,
        name: str,
        tool: str,
        params: Dict[str, Any] = None,
        condition: str = None,
        on_failure: str = "stop",
        max_retries: int = 0,
        output_key: str = None
    ) -> "ToolChain":
        """添加步骤"""
        step = ChainStep(
            name=name,
            tool=tool,
            params=params or {},
            condition=condition,
            on_failure=on_failure,
            max_retries=max_retries,
            output_key=output_key or name
        )
        self.steps.append(step)
        return self
    
    def set_variable(self, key: str, value: Any) -> "ToolChain":
        """设置变量"""
        self.context.set(key, value)
        return self
    
    async def execute(self) -> Dict[str, Any]:
        """执行工具链"""
        results = []
        
        for i, step in enumerate(self.steps):
            self.context.current_step = i
            step.status = ChainStepStatus.RUNNING
            
            # 检查条件
            if step.condition and not self._evaluate_condition(step.condition):
                step.status = ChainStepStatus.SKIPPED
                results.append({
                    "step": step.name,
                    "status": "skipped",
                    "reason": f"Condition not met: {step.condition}"
                })
                continue
            
            # 执行步骤
            result = await self._execute_step(step)
            
            # 存储结果
            self.context.results[step.name] = result
            if step.output_key and result.is_success:
                self.context.set(step.output_key, result.output)
            
            results.append({
                "step": step.name,
                "status": step.status.value,
                "output": result.output if result.is_success else None,
                "error": result.error
            })
            
            # 处理失败
            if not result.is_success:
                if step.on_failure == "stop":
                    break
                elif step.on_failure == "retry" and step.retries < step.max_retries:
                    step.retries += 1
                    # 重试
                    result = await self._execute_step(step)
        
        return {
            "chain": self.name,
            "steps": results,
            "variables": self.context.variables,
            "success": all(r.get("status") in ["success", "skipped"] for r in results)
        }
    
    async def _execute_step(self, step: ChainStep) -> ToolResult:
        """执行单个步骤"""
        try:
            # 获取工具
            tool = self._registry.get(step.tool)
            if not tool:
                step.status = ChainStepStatus.FAILED
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output=None,
                    error=f"Tool not found: {step.tool}"
                )
            
            # 解析参数
            params = self.context.resolve_params(step.params)
            
            # 执行工具
            result = await tool.execute(**params)
            
            step.status = ChainStepStatus.SUCCESS if result.is_success else ChainStepStatus.FAILED
            step.result = result
            
            return result
            
        except Exception as e:
            step.status = ChainStepStatus.FAILED
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=str(e)
            )
    
    def _evaluate_condition(self, condition: str) -> bool:
        """评估条件表达式"""
        try:
            # 简单的条件评估
            # 支持: $var == value, $var != value, $var
            if "==" in condition:
                parts = condition.split("==")
                left = self._resolve_value(parts[0].strip())
                right = self._resolve_value(parts[1].strip())
                return left == right
            elif "!=" in condition:
                parts = condition.split("!=")
                left = self._resolve_value(parts[0].strip())
                right = self._resolve_value(parts[1].strip())
                return left != right
            else:
                return bool(self._resolve_value(condition.strip()))
        except:
            return False
    
    def _resolve_value(self, value: str) -> Any:
        """解析值"""
        if value.startswith("$"):
            return self.context.get(value[1:])
        elif value.lower() == "true":
            return True
        elif value.lower() == "false":
            return False
        elif value.isdigit():
            return int(value)
        else:
            return value.strip("'\"")


class ToolChainTool(BaseTool):
    """工具链工具 - 执行预定义的工具链"""
    
    name: str = "tool_chain"
    description: str = """Execute a chain of tools in sequence.
    
Define a workflow with multiple tool calls, passing outputs between steps.
Supports conditions, error handling, and retries."""

    parameters: Dict[str, Any] = {
        "properties": {
            "steps": {
                "type": "array",
                "description": "List of steps to execute",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "tool": {"type": "string"},
                        "params": {"type": "object"},
                        "condition": {"type": "string"},
                        "on_failure": {"type": "string"}
                    }
                }
            },
            "variables": {
                "type": "object",
                "description": "Initial variables"
            }
        },
        "required": ["steps"]
    }
    
    async def execute(
        self,
        steps: List[Dict],
        variables: Dict[str, Any] = None,
        **kwargs
    ) -> ToolResult:
        """执行工具链"""
        try:
            chain = ToolChain()
            
            # 设置初始变量
            if variables:
                for key, value in variables.items():
                    chain.set_variable(key, value)
            
            # 添加步骤
            for step_config in steps:
                chain.add_step(
                    name=step_config.get("name", f"step_{len(chain.steps)}"),
                    tool=step_config["tool"],
                    params=step_config.get("params", {}),
                    condition=step_config.get("condition"),
                    on_failure=step_config.get("on_failure", "stop"),
                    max_retries=step_config.get("max_retries", 0),
                    output_key=step_config.get("output_key")
                )
            
            # 执行
            result = await chain.execute()
            
            return ToolResult(
                status=ToolStatus.SUCCESS if result["success"] else ToolStatus.ERROR,
                output=result
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=str(e)
            )


# 预定义的工具链模板
class ToolChainTemplates:
    """常用工具链模板"""
    
    @staticmethod
    def web_research(url: str, output_file: str = None) -> ToolChain:
        """网络研究工具链"""
        chain = ToolChain("web_research")
        chain.set_variable("url", url)
        
        chain.add_step(
            name="scrape",
            tool="web_scraper",
            params={"url": "$url", "extract_type": "text"}
        )
        
        chain.add_step(
            name="extract",
            tool="content_extractor",
            params={"url": "$url"}
        )
        
        if output_file:
            chain.set_variable("output_file", output_file)
            chain.add_step(
                name="save",
                tool="file_writer",
                params={"path": "$output_file", "content": "$extract"}
            )
        
        return chain
    
    @staticmethod
    def data_pipeline(
        input_file: str,
        output_file: str,
        transform_code: str
    ) -> ToolChain:
        """数据处理管道"""
        chain = ToolChain("data_pipeline")
        chain.set_variable("input", input_file)
        chain.set_variable("output", output_file)
        chain.set_variable("code", transform_code)
        
        chain.add_step(
            name="read",
            tool="file_reader",
            params={"path": "$input"}
        )
        
        chain.add_step(
            name="transform",
            tool="code_executor",
            params={"code": "$code"}
        )
        
        chain.add_step(
            name="write",
            tool="file_writer",
            params={"path": "$output", "content": "$transform"}
        )
        
        return chain


# 创建工具实例
tool_chain = ToolChainTool()

