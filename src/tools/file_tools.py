"""
文件操作工具集 - 读写各类文件
"""

import os
import json
import csv
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from .base import BaseTool, ToolResult, ToolStatus


class FileReaderTool(BaseTool):
    """文件读取工具"""
    
    name: str = "file_reader"
    description: str = """Read content from various file types.
    
Supported formats:
- Text files (.txt, .md, .py, .js, etc.)
- JSON files (.json)
- CSV files (.csv)
- Configuration files (.yaml, .toml, .ini)

Returns file content as text or structured data."""

    parameters: Dict[str, Any] = {
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to read"
            },
            "encoding": {
                "type": "string",
                "description": "File encoding",
                "default": "utf-8"
            },
            "parse": {
                "type": "boolean",
                "description": "Parse structured files (JSON, CSV) into data",
                "default": True
            }
        },
        "required": ["path"]
    }
    
    # 允许的目录（安全限制）
    allowed_dirs: List[str] = ["/tmp", "data", "output", "uploads"]
    
    async def execute(
        self,
        path: str,
        encoding: str = "utf-8",
        parse: bool = True,
        **kwargs
    ) -> ToolResult:
        """读取文件"""
        try:
            file_path = Path(path)
            
            if not file_path.exists():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output=None,
                    error=f"File not found: {path}"
                )
            
            if not file_path.is_file():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output=None,
                    error=f"Not a file: {path}"
                )
            
            # 获取文件扩展名
            ext = file_path.suffix.lower()
            
            # 读取文件
            content = file_path.read_text(encoding=encoding)
            
            # 根据类型解析
            if parse:
                if ext == '.json':
                    content = json.loads(content)
                elif ext == '.csv':
                    content = self._parse_csv(content)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=content,
                metadata={
                    "path": str(file_path),
                    "size": file_path.stat().st_size,
                    "extension": ext
                }
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=f"Failed to read file: {str(e)}"
            )
    
    def _parse_csv(self, content: str) -> List[Dict]:
        """解析CSV内容"""
        import io
        reader = csv.DictReader(io.StringIO(content))
        return list(reader)


class FileWriterTool(BaseTool):
    """文件写入工具"""
    
    name: str = "file_writer"
    description: str = """Write content to files.
    
Supports:
- Text files
- JSON files (with formatting)
- CSV files
- Append or overwrite modes

Creates parent directories if needed."""

    parameters: Dict[str, Any] = {
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to write the file"
            },
            "content": {
                "type": ["string", "object", "array"],
                "description": "Content to write"
            },
            "mode": {
                "type": "string",
                "enum": ["write", "append"],
                "description": "Write mode",
                "default": "write"
            },
            "encoding": {
                "type": "string",
                "default": "utf-8"
            }
        },
        "required": ["path", "content"]
    }
    
    async def execute(
        self,
        path: str,
        content: Any,
        mode: str = "write",
        encoding: str = "utf-8",
        **kwargs
    ) -> ToolResult:
        """写入文件"""
        try:
            file_path = Path(path)
            
            # 创建父目录
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            ext = file_path.suffix.lower()
            
            # 序列化内容
            if ext == '.json' and not isinstance(content, str):
                content = json.dumps(content, indent=2, ensure_ascii=False)
            elif ext == '.csv' and isinstance(content, list):
                content = self._to_csv(content)
            elif not isinstance(content, str):
                content = str(content)
            
            # 写入文件
            file_mode = 'a' if mode == 'append' else 'w'
            with open(file_path, file_mode, encoding=encoding) as f:
                f.write(content)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"Successfully wrote to {path}",
                metadata={
                    "path": str(file_path),
                    "size": file_path.stat().st_size,
                    "mode": mode
                }
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=f"Failed to write file: {str(e)}"
            )
    
    def _to_csv(self, data: List[Dict]) -> str:
        """转换为CSV格式"""
        import io
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        return output.getvalue()


class FileManagerTool(BaseTool):
    """文件管理工具 - 文件操作"""
    
    name: str = "file_manager"
    description: str = """Manage files and directories.
    
Operations:
- list: List files in directory
- info: Get file information
- copy: Copy file or directory
- move: Move file or directory
- delete: Delete file or directory
- mkdir: Create directory
- exists: Check if path exists"""

    parameters: Dict[str, Any] = {
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "info", "copy", "move", "delete", "mkdir", "exists"],
                "description": "Operation to perform"
            },
            "path": {
                "type": "string",
                "description": "Target path"
            },
            "destination": {
                "type": "string",
                "description": "Destination path (for copy/move)"
            },
            "pattern": {
                "type": "string",
                "description": "Glob pattern for filtering (for list)"
            }
        },
        "required": ["action", "path"]
    }
    
    async def execute(
        self,
        action: str,
        path: str,
        destination: str = None,
        pattern: str = "*",
        **kwargs
    ) -> ToolResult:
        """执行文件操作"""
        try:
            target = Path(path)
            
            if action == "list":
                return self._list_dir(target, pattern)
            elif action == "info":
                return self._get_info(target)
            elif action == "copy":
                return self._copy(target, Path(destination))
            elif action == "move":
                return self._move(target, Path(destination))
            elif action == "delete":
                return self._delete(target)
            elif action == "mkdir":
                return self._mkdir(target)
            elif action == "exists":
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=target.exists()
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
    
    def _list_dir(self, path: Path, pattern: str) -> ToolResult:
        """列出目录内容"""
        if not path.exists():
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=f"Directory not found: {path}"
            )
        
        files = []
        for item in path.glob(pattern):
            stat = item.stat()
            files.append({
                "name": item.name,
                "path": str(item),
                "type": "directory" if item.is_dir() else "file",
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=files,
            metadata={"count": len(files)}
        )
    
    def _get_info(self, path: Path) -> ToolResult:
        """获取文件信息"""
        if not path.exists():
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=f"Path not found: {path}"
            )
        
        stat = path.stat()
        info = {
            "name": path.name,
            "path": str(path.absolute()),
            "type": "directory" if path.is_dir() else "file",
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": path.suffix if path.is_file() else None
        }
        
        return ToolResult(status=ToolStatus.SUCCESS, output=info)
    
    def _copy(self, src: Path, dst: Path) -> ToolResult:
        """复制文件或目录"""
        if not src.exists():
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=f"Source not found: {src}"
            )
        
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=f"Copied {src} to {dst}"
        )
    
    def _move(self, src: Path, dst: Path) -> ToolResult:
        """移动文件或目录"""
        if not src.exists():
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=f"Source not found: {src}"
            )
        
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=f"Moved {src} to {dst}"
        )
    
    def _delete(self, path: Path) -> ToolResult:
        """删除文件或目录"""
        if not path.exists():
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"Path does not exist: {path}"
            )
        
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=f"Deleted {path}"
        )
    
    def _mkdir(self, path: Path) -> ToolResult:
        """创建目录"""
        path.mkdir(parents=True, exist_ok=True)
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=f"Created directory: {path}"
        )


class JsonTool(BaseTool):
    """JSON处理工具"""
    
    name: str = "json_tool"
    description: str = """Process and query JSON data.
    
Operations:
- parse: Parse JSON string
- stringify: Convert to JSON string
- query: Query with JSONPath-like syntax
- merge: Merge multiple JSON objects
- validate: Validate JSON structure"""

    parameters: Dict[str, Any] = {
        "properties": {
            "action": {
                "type": "string",
                "enum": ["parse", "stringify", "query", "merge", "validate"],
                "description": "Operation to perform"
            },
            "data": {
                "type": ["string", "object", "array"],
                "description": "Input data"
            },
            "path": {
                "type": "string",
                "description": "JSON path for query (e.g., 'users[0].name')"
            }
        },
        "required": ["action", "data"]
    }
    
    async def execute(
        self,
        action: str,
        data: Any,
        path: str = None,
        **kwargs
    ) -> ToolResult:
        """处理JSON"""
        try:
            if action == "parse":
                result = json.loads(data) if isinstance(data, str) else data
            elif action == "stringify":
                result = json.dumps(data, indent=2, ensure_ascii=False)
            elif action == "query":
                result = self._query(data, path)
            elif action == "merge":
                result = self._merge(data)
            elif action == "validate":
                result = self._validate(data)
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output=None,
                    error=f"Unknown action: {action}"
                )
            
            return ToolResult(status=ToolStatus.SUCCESS, output=result)
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=str(e)
            )
    
    def _query(self, data: Any, path: str) -> Any:
        """简单的路径查询"""
        if isinstance(data, str):
            data = json.loads(data)
        
        parts = path.replace('[', '.').replace(']', '').split('.')
        result = data
        
        for part in parts:
            if not part:
                continue
            if isinstance(result, dict):
                result = result.get(part)
            elif isinstance(result, list):
                result = result[int(part)]
            else:
                return None
        
        return result
    
    def _merge(self, data: List[Dict]) -> Dict:
        """合并JSON对象"""
        result = {}
        for obj in data:
            if isinstance(obj, dict):
                result.update(obj)
        return result
    
    def _validate(self, data: Any) -> Dict:
        """验证JSON"""
        if isinstance(data, str):
            try:
                json.loads(data)
                return {"valid": True}
            except json.JSONDecodeError as e:
                return {"valid": False, "error": str(e)}
        return {"valid": True, "type": type(data).__name__}


class CsvTool(BaseTool):
    """CSV处理工具"""
    
    name: str = "csv_tool"
    description: str = """Process CSV data.
    
Operations:
- parse: Parse CSV string to list of dicts
- stringify: Convert data to CSV string
- filter: Filter rows by condition
- select: Select specific columns
- sort: Sort by column"""

    parameters: Dict[str, Any] = {
        "properties": {
            "action": {
                "type": "string",
                "enum": ["parse", "stringify", "filter", "select", "sort"],
                "description": "Operation to perform"
            },
            "data": {
                "type": ["string", "array"],
                "description": "Input CSV string or data"
            },
            "columns": {
                "type": "array",
                "description": "Column names (for select)"
            },
            "condition": {
                "type": "object",
                "description": "Filter condition {column: value}"
            },
            "sort_by": {
                "type": "string",
                "description": "Column to sort by"
            }
        },
        "required": ["action", "data"]
    }
    
    async def execute(
        self,
        action: str,
        data: Any,
        columns: List[str] = None,
        condition: Dict = None,
        sort_by: str = None,
        **kwargs
    ) -> ToolResult:
        """处理CSV"""
        import io
        
        try:
            # 解析输入
            if isinstance(data, str):
                reader = csv.DictReader(io.StringIO(data))
                rows = list(reader)
            else:
                rows = data
            
            if action == "parse":
                result = rows
            elif action == "stringify":
                result = self._to_csv(rows)
            elif action == "filter" and condition:
                result = [r for r in rows if all(r.get(k) == v for k, v in condition.items())]
            elif action == "select" and columns:
                result = [{k: r.get(k) for k in columns} for r in rows]
            elif action == "sort" and sort_by:
                result = sorted(rows, key=lambda x: x.get(sort_by, ''))
            else:
                result = rows
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=result,
                metadata={"row_count": len(result) if isinstance(result, list) else None}
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=str(e)
            )
    
    def _to_csv(self, data: List[Dict]) -> str:
        """转换为CSV字符串"""
        import io
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        return output.getvalue()


# 创建工具实例
file_reader = FileReaderTool()
file_writer = FileWriterTool()
file_manager = FileManagerTool()
json_tool = JsonTool()
csv_tool = CsvTool()

