"""
文件操作路由
"""

import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/files", tags=["Files"])


class FileNode(BaseModel):
    """文件节点"""
    name: str
    path: str
    type: str  # 'file' or 'directory'
    children: Optional[list] = None
    language: Optional[str] = None


class FileContent(BaseModel):
    """文件内容"""
    content: str
    language: str


class WriteFileRequest(BaseModel):
    """写文件请求"""
    path: str
    content: str


class DeleteFileRequest(BaseModel):
    """删除文件请求"""
    path: str


def get_language(filename: str) -> str:
    """根据文件扩展名获取语言"""
    ext_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescriptreact',
        '.jsx': 'javascriptreact',
        '.json': 'json',
        '.html': 'html',
        '.css': 'css',
        '.md': 'markdown',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.xml': 'xml',
        '.sql': 'sql',
        '.sh': 'shell',
        '.bash': 'shell',
        '.txt': 'plaintext',
    }
    _, ext = os.path.splitext(filename)
    return ext_map.get(ext.lower(), 'plaintext')


def build_file_tree(path: str, base_path: str = '') -> FileNode:
    """构建文件树"""
    name = os.path.basename(path) or path
    rel_path = path if not base_path else os.path.relpath(path, base_path)
    
    if os.path.isfile(path):
        return FileNode(
            name=name,
            path=rel_path,
            type='file',
            language=get_language(name)
        )
    
    children = []
    try:
        entries = sorted(os.listdir(path))
        for entry in entries:
            # 跳过隐藏文件和常见忽略目录
            if entry.startswith('.') or entry in ['__pycache__', 'node_modules', 'venv', '.git']:
                continue
            
            full_path = os.path.join(path, entry)
            children.append(build_file_tree(full_path, base_path or path))
    except PermissionError:
        pass
    
    return FileNode(
        name=name,
        path=rel_path,
        type='directory',
        children=children
    )


@router.get("", response_model=FileNode)
async def list_files(path: str = Query(default="/", description="目录路径")):
    """
    列出目录内容
    """
    # 使用工作区根目录
    workspace = os.environ.get('WORKSPACE_PATH', os.getcwd())
    
    if path == '/':
        full_path = workspace
    else:
        full_path = os.path.join(workspace, path.lstrip('/'))
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Path not found")
    
    return build_file_tree(full_path)


@router.get("/read", response_model=FileContent)
async def read_file(path: str = Query(..., description="文件路径")):
    """
    读取文件内容
    """
    workspace = os.environ.get('WORKSPACE_PATH', os.getcwd())
    full_path = os.path.join(workspace, path.lstrip('/'))
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=400, detail="Not a file")
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return FileContent(
            content=content,
            language=get_language(os.path.basename(full_path))
        )
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Cannot read binary file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/write")
async def write_file(request: WriteFileRequest):
    """
    写入文件内容
    """
    workspace = os.environ.get('WORKSPACE_PATH', os.getcwd())
    full_path = os.path.join(workspace, request.path.lstrip('/'))
    
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(request.content)
        
        return {"success": True, "path": request.path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete")
async def delete_file(request: DeleteFileRequest):
    """
    删除文件
    """
    workspace = os.environ.get('WORKSPACE_PATH', os.getcwd())
    full_path = os.path.join(workspace, request.path.lstrip('/'))
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        if os.path.isfile(full_path):
            os.remove(full_path)
        else:
            import shutil
            shutil.rmtree(full_path)
        
        return {"success": True, "path": request.path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

