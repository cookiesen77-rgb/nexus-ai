"""
资源清理管理
"""

import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta


class TempFileManager:
    """临时文件管理器"""
    
    def __init__(self, base_dir: Optional[str] = None, max_age_hours: int = 24):
        self.base_dir = Path(base_dir) if base_dir else Path(tempfile.gettempdir()) / "sandbox"
        self.max_age = timedelta(hours=max_age_hours)
        self._tracked_paths: List[Path] = []
    
    def create_temp_dir(self, prefix: str = "exec_") -> Path:
        """创建临时目录"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix, dir=self.base_dir))
        self._tracked_paths.append(temp_dir)
        
        return temp_dir
    
    def cleanup_path(self, path: Path) -> bool:
        """清理指定路径"""
        try:
            if path.is_dir():
                shutil.rmtree(path)
            elif path.is_file():
                path.unlink()
            
            if path in self._tracked_paths:
                self._tracked_paths.remove(path)
            
            return True
        except Exception:
            return False
    
    def cleanup_tracked(self) -> int:
        """清理所有跟踪的路径"""
        cleaned = 0
        for path in self._tracked_paths.copy():
            if self.cleanup_path(path):
                cleaned += 1
        return cleaned
    
    def cleanup_old(self) -> int:
        """清理过期的临时文件"""
        if not self.base_dir.exists():
            return 0
        
        cleaned = 0
        cutoff_time = datetime.now() - self.max_age
        
        for item in self.base_dir.iterdir():
            try:
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                if mtime < cutoff_time:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    cleaned += 1
            except Exception:
                continue
        
        return cleaned
    
    def get_disk_usage(self) -> dict:
        """获取磁盘使用情况"""
        if not self.base_dir.exists():
            return {'total_size': 0, 'file_count': 0, 'dir_count': 0}
        
        total_size = 0
        file_count = 0
        dir_count = 0
        
        for item in self.base_dir.rglob('*'):
            if item.is_file():
                total_size += item.stat().st_size
                file_count += 1
            elif item.is_dir():
                dir_count += 1
        
        return {
            'total_size': total_size,
            'file_count': file_count,
            'dir_count': dir_count,
            'total_size_mb': total_size / (1024 * 1024),
        }


class ContainerCleaner:
    """Docker容器清理器"""
    
    def __init__(self, docker_client=None):
        self._docker_client = docker_client
    
    def _get_client(self):
        """获取Docker客户端"""
        if self._docker_client is None:
            try:
                import docker
                self._docker_client = docker.from_env()
            except:
                return None
        return self._docker_client
    
    def cleanup_stopped_containers(self, label: str = "sandbox") -> int:
        """清理停止的容器"""
        client = self._get_client()
        if not client:
            return 0
        
        cleaned = 0
        try:
            containers = client.containers.list(
                all=True,
                filters={'status': 'exited', 'label': label}
            )
            
            for container in containers:
                try:
                    container.remove(force=True)
                    cleaned += 1
                except:
                    continue
        except:
            pass
        
        return cleaned
    
    def cleanup_old_containers(self, max_age_hours: int = 1) -> int:
        """清理超时未清理的容器"""
        client = self._get_client()
        if not client:
            return 0
        
        cleaned = 0
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        try:
            containers = client.containers.list(all=True)
            
            for container in containers:
                try:
                    # 检查创建时间
                    created = container.attrs.get('Created', '')
                    if created:
                        created_time = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        if created_time.replace(tzinfo=None) < cutoff:
                            container.remove(force=True)
                            cleaned += 1
                except:
                    continue
        except:
            pass
        
        return cleaned
    
    def get_container_stats(self) -> dict:
        """获取容器统计"""
        client = self._get_client()
        if not client:
            return {'available': False}
        
        try:
            containers = client.containers.list(all=True)
            
            running = sum(1 for c in containers if c.status == 'running')
            stopped = sum(1 for c in containers if c.status == 'exited')
            
            return {
                'available': True,
                'total': len(containers),
                'running': running,
                'stopped': stopped,
            }
        except:
            return {'available': False}


class ResourceCleaner:
    """综合资源清理器"""
    
    def __init__(self, temp_manager: Optional[TempFileManager] = None):
        self.temp_manager = temp_manager or TempFileManager()
        self.container_cleaner = ContainerCleaner()
    
    async def cleanup_all(self) -> dict:
        """清理所有资源"""
        results = {
            'temp_files_cleaned': 0,
            'old_files_cleaned': 0,
            'containers_cleaned': 0,
        }
        
        # 清理临时文件
        results['temp_files_cleaned'] = self.temp_manager.cleanup_tracked()
        results['old_files_cleaned'] = self.temp_manager.cleanup_old()
        
        # 清理容器
        results['containers_cleaned'] = self.container_cleaner.cleanup_stopped_containers()
        
        return results
    
    async def periodic_cleanup(self, interval_minutes: int = 30):
        """定期清理"""
        while True:
            await asyncio.sleep(interval_minutes * 60)
            await self.cleanup_all()
    
    def get_resource_status(self) -> dict:
        """获取资源状态"""
        return {
            'disk': self.temp_manager.get_disk_usage(),
            'containers': self.container_cleaner.get_container_stats(),
        }

