"""
Shell执行工具 - 安全执行Shell命令
"""

import asyncio
import os
import shlex
from typing import Any, Dict, List, Optional
from pathlib import Path
from .base import BaseTool, ToolResult, ToolStatus


class ShellExecutorTool(BaseTool):
    """Shell命令执行工具"""
    
    name: str = "shell"
    description: str = """Execute shell commands safely.
    
Features:
- Run shell commands with timeout
- Capture stdout and stderr
- Set working directory
- Environment variable support
- Command allowlist for security

Note: Some dangerous commands are blocked for safety."""

    parameters: Dict[str, Any] = {
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to execute"
            },
            "cwd": {
                "type": "string",
                "description": "Working directory"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 60
            },
            "env": {
                "type": "object",
                "description": "Additional environment variables"
            }
        },
        "required": ["command"]
    }
    
    # 允许的命令前缀
    allowed_commands: List[str] = [
        "ls", "cat", "head", "tail", "grep", "find", "wc",
        "echo", "pwd", "date", "whoami",
        "python", "python3", "pip", "pip3",
        "node", "npm", "npx",
        "git", "curl", "wget",
        "mkdir", "cp", "mv", "touch",
        "tar", "zip", "unzip", "gzip",
        "sort", "uniq", "cut", "awk", "sed",
        "jq", "yq",
    ]
    
    # 禁止的命令模式
    blocked_patterns: List[str] = [
        "rm -rf /", "rm -rf ~", "rm -rf .",
        ":(){ :|:& };:",  # Fork bomb
        "> /dev/sd",
        "mkfs",
        "dd if=",
        "chmod 777 /",
        "sudo",
        "su ",
    ]
    
    def _is_safe_command(self, command: str) -> tuple:
        """检查命令是否安全"""
        # 检查禁止模式
        for pattern in self.blocked_patterns:
            if pattern in command:
                return False, f"Blocked pattern detected: {pattern}"
        
        # 检查命令是否在允许列表
        cmd_parts = shlex.split(command)
        if not cmd_parts:
            return False, "Empty command"
        
        base_cmd = cmd_parts[0]
        # 移除路径，只保留命令名
        base_cmd = os.path.basename(base_cmd)
        
        if base_cmd not in self.allowed_commands:
            return False, f"Command not in allowlist: {base_cmd}"
        
        return True, None
    
    async def execute(
        self,
        command: str,
        cwd: str = None,
        timeout: int = 60,
        env: Dict[str, str] = None,
        **kwargs
    ) -> ToolResult:
        """执行Shell命令"""
        # 安全检查
        is_safe, error = self._is_safe_command(command)
        if not is_safe:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=f"Security check failed: {error}"
            )
        
        try:
            # 准备环境变量
            process_env = os.environ.copy()
            if env:
                process_env.update(env)
            
            # 准备工作目录
            working_dir = cwd or os.getcwd()
            if not Path(working_dir).exists():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output=None,
                    error=f"Working directory not found: {working_dir}"
                )
            
            # 执行命令
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env=process_env
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ToolResult(
                    status=ToolStatus.TIMEOUT,
                    output=None,
                    error=f"Command timed out after {timeout} seconds"
                )
            
            stdout_text = stdout.decode('utf-8', errors='replace').strip()
            stderr_text = stderr.decode('utf-8', errors='replace').strip()
            
            if process.returncode == 0:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=stdout_text,
                    metadata={
                        "exit_code": process.returncode,
                        "stderr": stderr_text if stderr_text else None
                    }
                )
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output=stdout_text if stdout_text else None,
                    error=stderr_text or f"Exit code: {process.returncode}",
                    metadata={"exit_code": process.returncode}
                )
                
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=f"Failed to execute command: {str(e)}"
            )


class EnvironmentTool(BaseTool):
    """环境变量管理工具"""
    
    name: str = "environment"
    description: str = """Manage environment variables.
    
Operations:
- get: Get environment variable value
- set: Set environment variable (current process only)
- list: List all environment variables
- has: Check if variable exists"""

    parameters: Dict[str, Any] = {
        "properties": {
            "action": {
                "type": "string",
                "enum": ["get", "set", "list", "has"],
                "description": "Operation to perform"
            },
            "name": {
                "type": "string",
                "description": "Variable name"
            },
            "value": {
                "type": "string",
                "description": "Variable value (for set)"
            },
            "default": {
                "type": "string",
                "description": "Default value if not found"
            }
        },
        "required": ["action"]
    }
    
    # 敏感变量名（不在list中显示）
    sensitive_vars: List[str] = [
        "API_KEY", "SECRET", "PASSWORD", "TOKEN", "CREDENTIAL",
        "AWS_", "AZURE_", "GCP_", "OPENAI_", "CLAUDE_"
    ]
    
    def _is_sensitive(self, name: str) -> bool:
        """检查是否为敏感变量"""
        name_upper = name.upper()
        for pattern in self.sensitive_vars:
            if pattern in name_upper:
                return True
        return False
    
    async def execute(
        self,
        action: str,
        name: str = None,
        value: str = None,
        default: str = None,
        **kwargs
    ) -> ToolResult:
        """执行环境变量操作"""
        try:
            if action == "get":
                result = os.environ.get(name, default)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=result
                )
            
            elif action == "set":
                os.environ[name] = value
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"Set {name}"
                )
            
            elif action == "list":
                # 过滤敏感变量
                env_vars = {}
                for key, val in os.environ.items():
                    if self._is_sensitive(key):
                        env_vars[key] = "[REDACTED]"
                    else:
                        env_vars[key] = val
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=env_vars
                )
            
            elif action == "has":
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=name in os.environ
                )
            
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output=None,
                    error=f"Unknown action: {action}"
                )
                
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=str(e)
            )


# 创建工具实例
shell = ShellExecutorTool()
environment = EnvironmentTool()

