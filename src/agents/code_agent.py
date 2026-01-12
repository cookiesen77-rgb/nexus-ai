"""
代码执行Agent - 专门处理代码生成和执行任务
"""

from typing import Any, Dict, List, Optional
from .base import BaseAgent
from ..llm.base import BaseLLM
from ..tools.code_executor import CodeExecutorTool
from ..prompts.code import (
    get_code_generation_prompt,
    get_code_fix_prompt,
    get_data_analysis_prompt
)


class CodeAgent(BaseAgent):
    """代码执行Agent"""
    
    def __init__(
        self, 
        llm: BaseLLM, 
        model: str = "claude-sonnet-4-5-20250929",
        max_fix_attempts: int = 3
    ):
        super().__init__(name="CodeAgent", llm=llm, model=model)
        self.executor = CodeExecutorTool()
        self.max_fix_attempts = max_fix_attempts
    
    async def execute(self, task: str, context: Dict[str, Any] = None) -> Any:
        """
        执行代码任务
        
        Args:
            task: 任务描述
            context: 上下文信息，可包含:
                - requirements: 代码要求列表
                - data: 要处理的数据
                - code: 直接提供的代码
                
        Returns:
            执行结果
        """
        context = context or {}
        
        # 如果直接提供代码，执行它
        if "code" in context:
            return await self._execute_code(context["code"])
        
        # 否则生成并执行代码
        return await self._generate_and_execute(task, context)
    
    async def _execute_code(self, code: str) -> Dict[str, Any]:
        """执行代码"""
        result = await self.executor.execute(code=code)
        
        return {
            "success": result.success,
            "output": result.output,
            "error": result.error
        }
    
    async def _generate_and_execute(
        self, 
        task: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成代码并执行"""
        # 1. 生成代码
        code = await self._generate_code(task, context)
        
        if not code:
            return {
                "success": False,
                "error": "Failed to generate code",
                "output": None
            }
        
        # 2. 执行代码
        result = await self.executor.execute(code=code)
        
        # 3. 如果失败，尝试修复
        if not result.success and self.max_fix_attempts > 0:
            result, code = await self._fix_and_retry(
                code, 
                result.error, 
                result.output,
                attempts=self.max_fix_attempts
            )
        
        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "code": code,
            "fixed": not result.success  # 标记是否经过修复
        }
    
    async def _generate_code(self, task: str, context: Dict[str, Any]) -> Optional[str]:
        """生成代码"""
        requirements = context.get("requirements", [])
        output_format = context.get("output_format", "printed output")
        
        prompt = get_code_generation_prompt(task, requirements, output_format)
        
        messages = [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]}
        ]
        
        response = await self.llm.complete(messages)
        
        # 提取代码
        code = self._extract_code(response.content)
        return code
    
    async def _fix_and_retry(
        self, 
        code: str, 
        error: str, 
        output: str,
        attempts: int
    ):
        """修复代码并重试"""
        current_code = code
        last_result = None
        
        for attempt in range(attempts):
            # 生成修复提示
            prompt = get_code_fix_prompt(current_code, error, output)
            
            messages = [
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]}
            ]
            
            response = await self.llm.complete(messages)
            
            # 提取修复后的代码
            fixed_code = self._extract_code(response.content)
            
            if not fixed_code or fixed_code == current_code:
                break
            
            # 执行修复后的代码
            result = await self.executor.execute(code=fixed_code)
            last_result = result
            
            if result.success:
                return result, fixed_code
            
            # 更新用于下一次修复
            current_code = fixed_code
            error = result.error
            output = result.output
        
        return last_result or result, current_code
    
    def _extract_code(self, content: str) -> Optional[str]:
        """从LLM响应中提取代码"""
        import re
        
        # 尝试提取代码块
        code_block_pattern = r'```(?:python)?\n(.*?)```'
        matches = re.findall(code_block_pattern, content, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # 如果没有代码块，检查是否整个响应就是代码
        lines = content.strip().split('\n')
        if lines and (
            lines[0].startswith('import ') or 
            lines[0].startswith('from ') or
            lines[0].startswith('def ') or
            lines[0].startswith('#')
        ):
            return content.strip()
        
        return None
    
    async def analyze_data(
        self, 
        data_description: str, 
        goals: List[str],
        output_requirements: str = ""
    ) -> Dict[str, Any]:
        """
        数据分析任务
        
        Args:
            data_description: 数据描述
            goals: 分析目标列表
            output_requirements: 输出要求
            
        Returns:
            分析结果
        """
        prompt = get_data_analysis_prompt(data_description, goals, output_requirements)
        
        messages = [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]}
        ]
        
        response = await self.llm.complete(messages)
        code = self._extract_code(response.content)
        
        if not code:
            return {
                "success": False,
                "error": "Failed to generate analysis code"
            }
        
        result = await self.executor.execute(code=code)
        
        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "code": code
        }
    
    async def run_with_data(
        self, 
        code_template: str, 
        data: Any
    ) -> Dict[str, Any]:
        """
        用数据运行代码模板
        
        Args:
            code_template: 代码模板（包含{data}占位符）
            data: 要处理的数据
            
        Returns:
            执行结果
        """
        import json
        
        # 序列化数据
        if isinstance(data, str):
            data_str = data
        else:
            data_str = json.dumps(data, ensure_ascii=False)
        
        # 替换模板中的数据
        code = code_template.replace("{data}", data_str)
        
        return await self._execute_code(code)

