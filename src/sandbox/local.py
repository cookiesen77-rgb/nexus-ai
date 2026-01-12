"""
本地沙箱实现 - 用于开发测试
警告: 安全性有限，不建议在生产环境使用
"""

import asyncio
import sys
import io
import traceback
import resource
import signal
from datetime import datetime
from typing import Optional, Any
from contextlib import redirect_stdout, redirect_stderr

from .base import BaseSandbox
from .models import (
    ExecutionRequest, ExecutionResult, ExecutionStatus, SandboxConfig
)
from .security import SecurityChecker


class LocalSandbox(BaseSandbox):
    """本地Python执行沙箱"""
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        super().__init__(config)
        self.security_checker = SecurityChecker(config)
    
    @property
    def sandbox_type(self) -> str:
        return "local"
    
    async def initialize(self) -> None:
        """初始化本地沙箱"""
        self._is_initialized = True
    
    async def cleanup(self) -> None:
        """清理资源"""
        self._is_initialized = False
    
    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """执行Python代码"""
        started_at = datetime.now()
        
        # 安全检查
        is_safe, violations = self.security_checker.check_code(request.code)
        if not is_safe:
            return ExecutionResult(
                status=ExecutionStatus.SECURITY_VIOLATION,
                error=f"Security violations: {'; '.join(violations)}",
                started_at=started_at,
                finished_at=datetime.now(),
                sandbox_type=self.sandbox_type
            )
        
        # 在线程池中执行以支持超时
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, 
                    self._execute_sync, 
                    request
                ),
                timeout=request.timeout
            )
            result.started_at = started_at
            result.finished_at = datetime.now()
            result.execution_time = (result.finished_at - started_at).total_seconds()
            return result
            
        except asyncio.TimeoutError:
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                error=f"Execution timed out after {request.timeout} seconds",
                started_at=started_at,
                finished_at=datetime.now(),
                execution_time=request.timeout,
                sandbox_type=self.sandbox_type
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                error=str(e),
                started_at=started_at,
                finished_at=datetime.now(),
                sandbox_type=self.sandbox_type
            )
    
    def _execute_sync(self, request: ExecutionRequest) -> ExecutionResult:
        """同步执行代码"""
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        # 创建受限的全局命名空间
        safe_globals = self._create_safe_globals()
        local_vars = {}
        
        return_value = None
        exit_code = 0
        status = ExecutionStatus.SUCCESS
        error_msg = None
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # 编译代码
                compiled = compile(request.code, '<sandbox>', 'exec')
                
                # 执行代码
                exec(compiled, safe_globals, local_vars)
                
                # 尝试获取返回值（如果最后一行是表达式）
                if '_result_' in local_vars:
                    return_value = local_vars['_result_']
                    
        except SyntaxError as e:
            status = ExecutionStatus.ERROR
            error_msg = f"SyntaxError: {e}"
            exit_code = 1
        except MemoryError:
            status = ExecutionStatus.MEMORY_EXCEEDED
            error_msg = "Memory limit exceeded"
            exit_code = 137
        except Exception as e:
            status = ExecutionStatus.ERROR
            error_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            exit_code = 1
        
        output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()
        
        if stderr_output and not error_msg:
            error_msg = stderr_output
        
        # 清理输出
        output = self.security_checker.sanitize_output(output)
        
        return ExecutionResult(
            status=status,
            output=output,
            error=error_msg,
            return_value=self._serialize_return_value(return_value),
            exit_code=exit_code,
            sandbox_type=self.sandbox_type
        )
    
    def _create_safe_globals(self) -> dict:
        """创建安全的全局命名空间"""
        import math
        import json
        import re
        import datetime
        import collections
        import itertools
        import functools
        import operator
        import string
        import random
        import hashlib
        import base64
        import statistics
        
        safe_builtins = {
            # 基本类型
            'True': True,
            'False': False,
            'None': None,
            
            # 类型转换
            'int': int,
            'float': float,
            'str': str,
            'bool': bool,
            'list': list,
            'dict': dict,
            'set': set,
            'tuple': tuple,
            'frozenset': frozenset,
            'bytes': bytes,
            'bytearray': bytearray,
            
            # 内置函数
            'abs': abs,
            'all': all,
            'any': any,
            'ascii': ascii,
            'bin': bin,
            'callable': callable,
            'chr': chr,
            'divmod': divmod,
            'enumerate': enumerate,
            'filter': filter,
            'format': format,
            'hash': hash,
            'hex': hex,
            'id': id,
            'isinstance': isinstance,
            'issubclass': issubclass,
            'iter': iter,
            'len': len,
            'map': map,
            'max': max,
            'min': min,
            'next': next,
            'oct': oct,
            'ord': ord,
            'pow': pow,
            'print': print,
            'range': range,
            'repr': repr,
            'reversed': reversed,
            'round': round,
            'slice': slice,
            'sorted': sorted,
            'sum': sum,
            'type': type,
            'zip': zip,
            
            # 异常类
            'Exception': Exception,
            'ValueError': ValueError,
            'TypeError': TypeError,
            'KeyError': KeyError,
            'IndexError': IndexError,
            'AttributeError': AttributeError,
            'ZeroDivisionError': ZeroDivisionError,
        }
        
        # 预导入random模块以避免需要__import__
        import random as random_module
        
        return {
            '__builtins__': safe_builtins,
            'math': math,
            'json': json,
            're': re,
            'datetime': datetime,
            'collections': collections,
            'itertools': itertools,
            'functools': functools,
            'operator': operator,
            'string': string,
            'random': random_module,
            'hashlib': hashlib,
            'base64': base64,
            'statistics': statistics,
        }
    
    def _serialize_return_value(self, value: Any) -> Any:
        """序列化返回值"""
        if value is None:
            return None
        
        # 基本类型直接返回
        if isinstance(value, (bool, int, float, str)):
            return value
        
        # 容器类型尝试转换
        try:
            if isinstance(value, (list, tuple)):
                return [self._serialize_return_value(v) for v in value]
            if isinstance(value, dict):
                return {str(k): self._serialize_return_value(v) for k, v in value.items()}
            if isinstance(value, set):
                return list(value)
            
            # 其他类型转字符串
            return str(value)
        except:
            return str(value)

