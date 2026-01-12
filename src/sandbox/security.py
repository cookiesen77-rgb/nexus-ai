"""
安全策略和代码检查
"""

import re
import ast
from typing import List, Optional, Tuple
from .models import SandboxConfig


class SecurityChecker:
    """代码安全检查器"""
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        
        # 危险模式正则表达式
        self._dangerous_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.config.blocked_patterns
        ]
        
        # 危险AST节点类型
        self._dangerous_ast_nodes = {
            'Import': self._check_import,
            'ImportFrom': self._check_import_from,
            'Call': self._check_call,
        }
    
    def check_code(self, code: str) -> Tuple[bool, List[str]]:
        """
        检查代码安全性
        
        Returns:
            (is_safe, violations): 是否安全，违规列表
        """
        violations = []
        
        # 1. 模式匹配检查
        pattern_violations = self._check_patterns(code)
        violations.extend(pattern_violations)
        
        # 2. AST分析检查
        ast_violations = self._check_ast(code)
        violations.extend(ast_violations)
        
        return len(violations) == 0, violations
    
    def _check_patterns(self, code: str) -> List[str]:
        """检查危险模式"""
        violations = []
        
        for pattern in self._dangerous_patterns:
            if pattern.search(code):
                violations.append(f"Dangerous pattern detected: {pattern.pattern}")
        
        return violations
    
    def _check_ast(self, code: str) -> List[str]:
        """AST级别的安全检查"""
        violations = []
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            # 语法错误不是安全问题，让执行器处理
            return []
        
        for node in ast.walk(tree):
            node_type = type(node).__name__
            if node_type in self._dangerous_ast_nodes:
                check_func = self._dangerous_ast_nodes[node_type]
                violation = check_func(node)
                if violation:
                    violations.append(violation)
        
        return violations
    
    def _check_import(self, node: ast.Import) -> Optional[str]:
        """检查import语句"""
        for alias in node.names:
            module = alias.name.split('.')[0]
            if not self._is_allowed_import(module):
                return f"Import not allowed: {alias.name}"
        return None
    
    def _check_import_from(self, node: ast.ImportFrom) -> Optional[str]:
        """检查from ... import语句"""
        if node.module:
            module = node.module.split('.')[0]
            if not self._is_allowed_import(module):
                return f"Import not allowed: {node.module}"
        return None
    
    def _check_call(self, node: ast.Call) -> Optional[str]:
        """检查函数调用"""
        # 检查危险的内置函数
        dangerous_builtins = {'eval', 'exec', 'compile', '__import__', 'open', 'input'}
        
        if isinstance(node.func, ast.Name):
            if node.func.id in dangerous_builtins:
                return f"Dangerous builtin function: {node.func.id}"
        
        # 检查危险的方法调用
        if isinstance(node.func, ast.Attribute):
            dangerous_methods = {'system', 'popen', 'spawn', 'fork'}
            if node.func.attr in dangerous_methods:
                return f"Dangerous method call: {node.func.attr}"
        
        return None
    
    def _is_allowed_import(self, module: str) -> bool:
        """检查模块是否允许导入"""
        # 标准安全模块
        safe_stdlib = {
            'math', 'json', 're', 'datetime', 'time',
            'collections', 'itertools', 'functools', 'operator',
            'string', 'random', 'hashlib', 'base64',
            'decimal', 'fractions', 'statistics',
            'typing', 'dataclasses', 'enum', 'copy',
            'textwrap', 'difflib', 'unicodedata'
        }
        
        # 允许的数据处理库
        safe_data = {'pandas', 'numpy', 'scipy'}
        
        allowed = safe_stdlib | safe_data | set(self.config.allowed_imports)
        
        return module in allowed
    
    def sanitize_output(self, output: str, max_length: int = 10000) -> str:
        """清理输出内容"""
        if len(output) > max_length:
            output = output[:max_length] + f"\n... (truncated, total {len(output)} chars)"
        
        # 移除潜在的敏感信息
        sensitive_patterns = [
            (r'api[_-]?key["\']?\s*[:=]\s*["\']?[\w-]+', '[API_KEY_REDACTED]'),
            (r'password["\']?\s*[:=]\s*["\']?[\w-]+', '[PASSWORD_REDACTED]'),
            (r'secret["\']?\s*[:=]\s*["\']?[\w-]+', '[SECRET_REDACTED]'),
            (r'token["\']?\s*[:=]\s*["\']?[\w-]+', '[TOKEN_REDACTED]'),
        ]
        
        for pattern, replacement in sensitive_patterns:
            output = re.sub(pattern, replacement, output, flags=re.IGNORECASE)
        
        return output


class ResourceLimiter:
    """资源限制器"""
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
    
    def get_docker_limits(self) -> dict:
        """获取Docker资源限制配置"""
        return {
            'mem_limit': f"{self.config.default_memory_limit}",
            'memswap_limit': f"{self.config.default_memory_limit}",  # 禁用swap
            'cpu_period': 100000,
            'cpu_quota': int(100000 * self.config.default_cpu_limit),
            'network_mode': self.config.docker_network,
            'pids_limit': 100,  # 限制进程数
            'read_only': False,  # 允许写入temp目录
        }
    
    def get_ulimits(self) -> list:
        """获取ulimit配置"""
        return [
            {'name': 'nofile', 'soft': 1024, 'hard': 1024},  # 文件描述符
            {'name': 'nproc', 'soft': 100, 'hard': 100},     # 进程数
            {'name': 'fsize', 'soft': 10485760, 'hard': 10485760},  # 文件大小10MB
        ]

