"""
代码执行工具 - 安全执行Python代码
"""

from typing import Any, Dict, Optional
from .base import BaseTool, ToolResult, ToolStatus
from ..sandbox import (
    create_sandbox, 
    ExecutionRequest, 
    ExecutionResult,
    SandboxConfig,
    ResultFormatter,
    ExecutionLogger
)


class CodeExecutorTool(BaseTool):
    """Python代码执行工具"""
    
    name: str = "code_executor"
    description: str = """Execute Python code in a secure sandbox environment.
Use this tool to run Python code for data analysis, calculations, or testing.

Features:
- Safe execution with security checks
- Support for common libraries (math, json, pandas, numpy)
- Timeout and memory limits
- Detailed error reporting

Limitations:
- No network access
- No file system access (except temp files)
- Limited to approved imports
"""
    
    parameters: Dict[str, Any] = {
        "code": {
            "type": "string",
            "description": "Python code to execute"
        },
        "timeout": {
            "type": "integer",
            "description": "Maximum execution time in seconds (default: 60, max: 300)",
            "default": 60
        }
    }
    
    # 配置
    sandbox_type: str = "local"
    sandbox_config: Optional[SandboxConfig] = None
    logger: Optional[ExecutionLogger] = None
    
    model_config = {"arbitrary_types_allowed": True}
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.logger is None:
            self.logger = ExecutionLogger()
    
    async def execute(self, code: str, timeout: int = 60, **kwargs) -> ToolResult:
        """
        执行Python代码
        
        Args:
            code: Python代码
            timeout: 超时时间（秒）
            
        Returns:
            ToolResult: 执行结果
        """
        # 验证参数
        if not code or not code.strip():
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error="Code cannot be empty"
            )
        
        timeout = min(max(timeout, 1), 300)  # 限制1-300秒
        
        # 创建请求ID
        import uuid
        request_id = str(uuid.uuid4())[:8]
        
        # 创建执行请求
        request = ExecutionRequest(
            code=code,
            timeout=timeout
        )
        
        # 记录请求
        self.logger.log_request(request, request_id)
        
        try:
            # 创建沙箱并执行
            sandbox = create_sandbox(self.sandbox_type, self.sandbox_config)
            
            async with sandbox:
                result = await sandbox.execute(request)
            
            # 记录结果
            self.logger.log_result(result, request_id)
            
            # 转换为ToolResult
            return self._convert_result(result)
            
        except Exception as e:
            self.logger.log_error(e, request_id)
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=f"Execution failed: {str(e)}"
            )
    
    def _convert_result(self, result: ExecutionResult) -> ToolResult:
        """转换执行结果为工具结果"""
        if result.is_success:
            output = result.output
            if result.return_value is not None:
                output += f"\n\nReturn value: {result.return_value}"
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=output,
                error=None
            )
        else:
            # 格式化错误信息
            error_msg = f"[{result.status.value}] {result.error or 'Unknown error'}"
            
            return ToolResult(
                status=ToolStatus.ERROR,
                output=result.output if result.output else None,
                error=error_msg
            )
    
    def get_execution_stats(self) -> dict:
        """获取执行统计"""
        metrics = self.logger.get_metrics()
        return {
            "total_executions": metrics.total_executions,
            "success_rate": (
                metrics.successful_executions / metrics.total_executions * 100
                if metrics.total_executions > 0 else 0
            ),
            "average_time": metrics.average_execution_time,
            "timeout_count": metrics.timeout_executions,
        }


class DataAnalysisTool(BaseTool):
    """数据分析工具 - 基于代码执行的高级工具"""
    
    name: str = "data_analysis"
    description: str = """Analyze data using Python with pandas and numpy.
Automatically handles data loading and provides statistical analysis.

Use this for:
- Statistical calculations
- Data transformations
- Generating summaries
"""
    
    parameters: Dict[str, Any] = {
        "data": {
            "type": "object",
            "description": "Data to analyze (dict, list, or JSON string)"
        },
        "analysis_type": {
            "type": "string",
            "description": "Type of analysis: describe, correlation, groupby, custom",
            "enum": ["describe", "correlation", "groupby", "value_counts", "custom"]
        },
        "custom_code": {
            "type": "string",
            "description": "Custom analysis code (only for analysis_type='custom')"
        },
        "group_by": {
            "type": "string",
            "description": "Column to group by (for groupby analysis)"
        }
    }
    
    _executor: CodeExecutorTool = None
    
    model_config = {"arbitrary_types_allowed": True}
    
    def __init__(self, **data):
        super().__init__(**data)
        self._executor = CodeExecutorTool()
    
    async def execute(
        self, 
        data: Any,
        analysis_type: str = "describe",
        custom_code: str = None,
        group_by: str = None,
        **kwargs
    ) -> ToolResult:
        """执行数据分析"""
        import json
        
        # 生成分析代码
        code = self._generate_analysis_code(data, analysis_type, custom_code, group_by)
        
        # 执行
        return await self._executor.execute(code=code)
    
    def _generate_analysis_code(
        self, 
        data: Any, 
        analysis_type: str,
        custom_code: str,
        group_by: str
    ) -> str:
        """生成分析代码"""
        import json
        
        # 数据序列化
        if isinstance(data, str):
            data_str = data
        else:
            data_str = json.dumps(data)
        
        code_parts = [
            "import pandas as pd",
            "import json",
            "",
            f"data = json.loads('''{data_str}''')",
            "df = pd.DataFrame(data)",
            ""
        ]
        
        if analysis_type == "describe":
            code_parts.append("print(df.describe().to_string())")
        
        elif analysis_type == "correlation":
            code_parts.append("numeric_df = df.select_dtypes(include=['number'])")
            code_parts.append("print(numeric_df.corr().to_string())")
        
        elif analysis_type == "groupby" and group_by:
            code_parts.append(f"grouped = df.groupby('{group_by}').agg(['mean', 'count', 'sum'])")
            code_parts.append("print(grouped.to_string())")
        
        elif analysis_type == "value_counts":
            code_parts.append("for col in df.columns:")
            code_parts.append("    print(f'\\n{col}:')")
            code_parts.append("    print(df[col].value_counts().head(10))")
        
        elif analysis_type == "custom" and custom_code:
            code_parts.append("# Custom analysis")
            code_parts.append(custom_code)
        
        else:
            code_parts.append("print(df.head(10).to_string())")
            code_parts.append("print(f'\\nShape: {df.shape}')")
            code_parts.append("print(f'Columns: {list(df.columns)}')")
        
        return '\n'.join(code_parts)

