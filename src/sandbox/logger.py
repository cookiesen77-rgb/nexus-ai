"""
执行日志记录
"""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from .models import ExecutionRequest, ExecutionResult, ExecutionMetrics


class ExecutionLogger:
    """执行日志记录器"""
    
    def __init__(
        self, 
        log_file: Optional[str] = None,
        log_level: int = logging.INFO,
        max_code_length: int = 1000
    ):
        self.log_file = log_file
        self.max_code_length = max_code_length
        self._entries: List[Dict] = []
        self.metrics = ExecutionMetrics()
        
        # 设置日志器
        self.logger = logging.getLogger("sandbox.execution")
        self.logger.setLevel(log_level)
        
        if log_file:
            handler = logging.FileHandler(log_file)
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(handler)
    
    def log_request(self, request: ExecutionRequest, request_id: str) -> None:
        """记录执行请求"""
        code_preview = request.code[:self.max_code_length]
        if len(request.code) > self.max_code_length:
            code_preview += "..."
        
        entry = {
            'type': 'request',
            'request_id': request_id,
            'timestamp': datetime.now().isoformat(),
            'code_length': len(request.code),
            'code_preview': code_preview,
            'timeout': request.timeout,
            'language': request.language,
        }
        
        self._entries.append(entry)
        self.logger.info(f"Execution request {request_id}: {len(request.code)} chars, timeout={request.timeout}s")
    
    def log_result(self, result: ExecutionResult, request_id: str) -> None:
        """记录执行结果"""
        entry = {
            'type': 'result',
            'request_id': request_id,
            'timestamp': datetime.now().isoformat(),
            'status': result.status.value,
            'execution_time': result.execution_time,
            'memory_used': result.memory_used,
            'exit_code': result.exit_code,
            'output_length': len(result.output),
            'has_error': result.error is not None,
            'sandbox_type': result.sandbox_type,
        }
        
        self._entries.append(entry)
        self.metrics.update(result)
        
        log_msg = f"Execution {request_id}: {result.status.value} in {result.execution_time:.3f}s"
        
        if result.is_success:
            self.logger.info(log_msg)
        else:
            self.logger.warning(f"{log_msg} - {result.error[:100] if result.error else 'Unknown error'}")
    
    def log_error(self, error: Exception, request_id: str) -> None:
        """记录执行错误"""
        entry = {
            'type': 'error',
            'request_id': request_id,
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
        }
        
        self._entries.append(entry)
        self.logger.error(f"Execution {request_id} error: {type(error).__name__}: {error}")
    
    def get_entries(
        self, 
        entry_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """获取日志条目"""
        entries = self._entries
        
        if entry_type:
            entries = [e for e in entries if e.get('type') == entry_type]
        
        return entries[-limit:]
    
    def get_metrics(self) -> ExecutionMetrics:
        """获取执行指标"""
        return self.metrics
    
    def export_json(self, filepath: str) -> None:
        """导出日志为JSON"""
        data = {
            'entries': self._entries,
            'metrics': self.metrics.model_dump(),
            'exported_at': datetime.now().isoformat(),
        }
        
        Path(filepath).write_text(json.dumps(data, indent=2, ensure_ascii=False))
    
    def clear(self) -> None:
        """清除日志"""
        self._entries.clear()
        self.metrics = ExecutionMetrics()


class ExecutionAuditLog:
    """执行审计日志 - 用于安全审计"""
    
    def __init__(self, audit_file: str):
        self.audit_file = Path(audit_file)
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)
    
    def log(
        self, 
        request: ExecutionRequest, 
        result: ExecutionResult,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> None:
        """记录审计日志"""
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'session_id': session_id,
            'code_hash': hash(request.code),
            'code_length': len(request.code),
            'status': result.status.value,
            'execution_time': result.execution_time,
            'sandbox_type': result.sandbox_type,
            'has_security_violation': result.status.value == 'security_violation',
        }
        
        with open(self.audit_file, 'a') as f:
            f.write(json.dumps(audit_entry) + '\n')

