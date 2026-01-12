"""
Docker沙箱实现 - 生产环境推荐
"""

import asyncio
import tempfile
import os
import json
from datetime import datetime
from typing import Optional
from pathlib import Path

from .base import BaseSandbox
from .models import (
    ExecutionRequest, ExecutionResult, ExecutionStatus, SandboxConfig
)
from .security import SecurityChecker, ResourceLimiter


class DockerSandbox(BaseSandbox):
    """Docker容器沙箱"""
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        super().__init__(config)
        self.security_checker = SecurityChecker(config)
        self.resource_limiter = ResourceLimiter(config)
        self._docker_client = None
        self._container = None
    
    @property
    def sandbox_type(self) -> str:
        return "docker"
    
    async def initialize(self) -> None:
        """初始化Docker环境"""
        try:
            import docker
            self._docker_client = docker.from_env()
            
            # 检查Docker是否可用
            self._docker_client.ping()
            
            # 确保镜像存在
            await self._ensure_image()
            
            self._is_initialized = True
            
        except ImportError:
            raise RuntimeError("Docker SDK not installed. Run: pip install docker")
        except Exception as e:
            raise RuntimeError(f"Docker initialization failed: {e}")
    
    async def _ensure_image(self) -> None:
        """确保Docker镜像存在"""
        image_name = self.config.docker_image
        
        try:
            self._docker_client.images.get(image_name)
        except:
            # 拉取镜像
            print(f"Pulling Docker image: {image_name}")
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._docker_client.images.pull,
                image_name
            )
    
    async def cleanup(self) -> None:
        """清理Docker资源"""
        if self._container:
            try:
                self._container.stop(timeout=1)
                self._container.remove(force=True)
            except:
                pass
            self._container = None
        
        self._is_initialized = False
    
    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """在Docker容器中执行代码"""
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
        
        try:
            result = await asyncio.wait_for(
                self._execute_in_container(request),
                timeout=request.timeout + 5  # 额外5秒用于容器操作
            )
            result.started_at = started_at
            result.finished_at = datetime.now()
            result.execution_time = (result.finished_at - started_at).total_seconds()
            return result
            
        except asyncio.TimeoutError:
            await self._kill_container()
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
    
    async def _execute_in_container(self, request: ExecutionRequest) -> ExecutionResult:
        """在容器中执行"""
        # 创建临时目录存放代码
        with tempfile.TemporaryDirectory() as temp_dir:
            # 写入代码文件
            code_file = Path(temp_dir) / "main.py"
            wrapper_code = self._wrap_code(request.code)
            code_file.write_text(wrapper_code)
            
            # 容器配置
            container_config = {
                'image': self.config.docker_image,
                'command': ['python', '/code/main.py'],
                'volumes': {
                    temp_dir: {'bind': '/code', 'mode': 'ro'}
                },
                'working_dir': '/code',
                'detach': True,
                'remove': False,  # 我们手动删除以获取日志
                **self.resource_limiter.get_docker_limits()
            }
            
            # 添加环境变量
            if request.env_vars:
                container_config['environment'] = request.env_vars
            
            # 运行容器
            loop = asyncio.get_event_loop()
            container = await loop.run_in_executor(
                None,
                lambda: self._docker_client.containers.run(**container_config)
            )
            
            self._container = container
            
            try:
                # 等待容器完成
                exit_result = await loop.run_in_executor(
                    None,
                    lambda: container.wait(timeout=request.timeout)
                )
                
                exit_code = exit_result.get('StatusCode', 1)
                
                # 获取日志
                logs = await loop.run_in_executor(
                    None,
                    lambda: container.logs(stdout=True, stderr=True).decode('utf-8', errors='replace')
                )
                
                # 解析输出
                return self._parse_output(logs, exit_code)
                
            finally:
                # 清理容器
                try:
                    container.remove(force=True)
                except:
                    pass
                self._container = None
    
    def _wrap_code(self, code: str) -> str:
        """包装用户代码以捕获输出和异常"""
        return f'''
import sys
import json
import traceback

def main():
    try:
{self._indent_code(code, 8)}
    except Exception as e:
        print(f"ERROR: {{type(e).__name__}}: {{e}}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    
    def _indent_code(self, code: str, spaces: int) -> str:
        """缩进代码"""
        indent = ' ' * spaces
        lines = code.split('\n')
        return '\n'.join(indent + line if line.strip() else line for line in lines)
    
    def _parse_output(self, logs: str, exit_code: int) -> ExecutionResult:
        """解析容器输出"""
        # 分离stdout和stderr
        output_lines = []
        error_lines = []
        
        for line in logs.split('\n'):
            if line.startswith('ERROR:'):
                error_lines.append(line[6:].strip())
            else:
                output_lines.append(line)
        
        output = '\n'.join(output_lines).strip()
        error = '\n'.join(error_lines).strip() if error_lines else None
        
        # 清理输出
        output = self.security_checker.sanitize_output(output)
        
        if exit_code == 0:
            status = ExecutionStatus.SUCCESS
        elif exit_code == 137:
            status = ExecutionStatus.MEMORY_EXCEEDED
            error = error or "Container killed - memory limit exceeded"
        else:
            status = ExecutionStatus.ERROR
        
        return ExecutionResult(
            status=status,
            output=output,
            error=error,
            exit_code=exit_code,
            sandbox_type=self.sandbox_type
        )
    
    async def _kill_container(self) -> None:
        """强制停止容器"""
        if self._container:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self._container.kill()
                )
                await loop.run_in_executor(
                    None,
                    lambda: self._container.remove(force=True)
                )
            except:
                pass
            self._container = None

