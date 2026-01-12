"""
执行错误定义和处理
"""

from typing import Optional
from .models import ExecutionStatus


class SandboxError(Exception):
    """沙箱基础异常"""
    
    def __init__(self, message: str, status: ExecutionStatus = ExecutionStatus.ERROR):
        super().__init__(message)
        self.status = status


class SecurityViolationError(SandboxError):
    """安全违规异常"""
    
    def __init__(self, message: str, violations: list = None):
        super().__init__(message, ExecutionStatus.SECURITY_VIOLATION)
        self.violations = violations or []


class TimeoutError(SandboxError):
    """执行超时异常"""
    
    def __init__(self, timeout: int):
        super().__init__(f"Execution timed out after {timeout} seconds", ExecutionStatus.TIMEOUT)
        self.timeout = timeout


class MemoryExceededError(SandboxError):
    """内存超限异常"""
    
    def __init__(self, limit: int):
        super().__init__(f"Memory limit exceeded: {limit} bytes", ExecutionStatus.MEMORY_EXCEEDED)
        self.limit = limit


class SandboxNotReadyError(SandboxError):
    """沙箱未就绪异常"""
    
    def __init__(self):
        super().__init__("Sandbox is not initialized")


class DockerNotAvailableError(SandboxError):
    """Docker不可用异常"""
    
    def __init__(self, reason: str = "Docker is not available"):
        super().__init__(reason)


class ErrorClassifier:
    """错误分类器"""
    
    # Python异常到执行状态的映射
    _exception_mappings = {
        'SyntaxError': ('syntax_error', 'Code syntax is invalid'),
        'IndentationError': ('indentation_error', 'Code indentation is incorrect'),
        'NameError': ('name_error', 'Variable or function not defined'),
        'TypeError': ('type_error', 'Type mismatch in operation'),
        'ValueError': ('value_error', 'Invalid value provided'),
        'KeyError': ('key_error', 'Key not found in dictionary'),
        'IndexError': ('index_error', 'Index out of range'),
        'AttributeError': ('attribute_error', 'Attribute not found'),
        'ImportError': ('import_error', 'Failed to import module'),
        'ModuleNotFoundError': ('module_not_found', 'Module not found'),
        'ZeroDivisionError': ('zero_division', 'Division by zero'),
        'FileNotFoundError': ('file_not_found', 'File not found'),
        'PermissionError': ('permission_denied', 'Permission denied'),
        'MemoryError': ('memory_error', 'Out of memory'),
        'RecursionError': ('recursion_error', 'Maximum recursion depth exceeded'),
        'RuntimeError': ('runtime_error', 'Runtime error occurred'),
    }
    
    @classmethod
    def classify(cls, error_message: str) -> tuple:
        """
        分类错误
        
        Returns:
            (error_type, description, suggestion)
        """
        for exc_name, (error_type, description) in cls._exception_mappings.items():
            if exc_name in error_message:
                suggestion = cls._get_suggestion(error_type, error_message)
                return error_type, description, suggestion
        
        return 'unknown_error', 'An unexpected error occurred', None
    
    @classmethod
    def _get_suggestion(cls, error_type: str, error_message: str) -> Optional[str]:
        """获取修复建议"""
        suggestions = {
            'syntax_error': 'Check for missing colons, parentheses, or quotation marks',
            'indentation_error': 'Ensure consistent use of spaces or tabs for indentation',
            'name_error': 'Check if the variable is defined before use',
            'type_error': 'Verify the types of operands match the operation',
            'import_error': 'Ensure the module is installed and the name is correct',
            'module_not_found': 'Install the required module with pip',
            'zero_division': 'Add a check for zero before division',
            'memory_error': 'Reduce data size or optimize memory usage',
            'recursion_error': 'Add a base case or convert to iteration',
        }
        
        return suggestions.get(error_type)
    
    @classmethod
    def format_error(cls, error_message: str, include_traceback: bool = False) -> dict:
        """格式化错误信息"""
        error_type, description, suggestion = cls.classify(error_message)
        
        result = {
            'type': error_type,
            'description': description,
            'message': error_message.split('\n')[0] if error_message else 'Unknown error',
        }
        
        if suggestion:
            result['suggestion'] = suggestion
        
        if include_traceback and '\n' in error_message:
            result['traceback'] = error_message
        
        return result

