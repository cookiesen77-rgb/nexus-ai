"""
上下文工程工具 - Manus 风格的 3 文件持久化系统

基于 planning-with-files 原理实现:
- task_plan.md: 任务计划、进度追踪、当前步骤
- notes.md: 研究笔记、知识存储、重要发现
- [deliverable].md: 最终交付物

解决的核心问题:
1. 易失性记忆 (Volatile Memory) - 通过持久化文件保持状态
2. 目标漂移 (Goal Drift) - 通过定期读取 task_plan.md 保持专注
3. 隐藏错误 (Hidden Errors) - 通过记录进度及时发现问题
4. 上下文塞满 (Context Stuffing) - 通过结构化笔记管理信息
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional, List
from .base import BaseTool, ToolResult, ToolStatus


# 默认工作区路径
DEFAULT_WORKSPACE = os.environ.get("WORKSPACE_PATH", "/Users/mac/Desktop/manus")
CONTEXT_DIR = os.path.join(DEFAULT_WORKSPACE, ".nexus_context")


class ContextEngineeringTool(BaseTool):
    """
    上下文工程工具 - 实现 Manus 的 3 文件持久化模式
    
    核心循环:
    1. 创建 task_plan.md (分解任务)
    2. 研究并保存到 notes.md
    3. 更新 task_plan.md (标记进度)
    4. 读取 notes.md (获取知识)
    5. 创建交付物
    6. 更新 task_plan.md (完成任务)
    7. 输出最终结果
    """
    
    name: str = "context_engineering"
    description: str = """Manus-style context engineering tool for persistent planning and knowledge management.

Actions:
- init_context: Initialize context files for a new task
- read_plan: Read current task plan (call frequently to maintain focus!)
- update_plan: Update task plan with progress or new steps
- add_note: Add research notes or knowledge
- read_notes: Read all notes
- create_deliverable: Create or update deliverable file
- read_deliverable: Read deliverable content
- list_context: List all context files
- clear_context: Clear all context files for new task

Best Practice - The 3-File Pattern:
1. task_plan.md - Your mission control. Contains goals, steps, and progress.
2. notes.md - Your external brain. Store all research and findings here.
3. [deliverable].md - Your output. The final result of your work.

IMPORTANT: Read task_plan.md at the start of EVERY response to maintain goal focus!"""

    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["init_context", "read_plan", "update_plan", "add_note", 
                        "read_notes", "create_deliverable", "read_deliverable", 
                        "list_context", "clear_context"],
                "description": "Action to perform"
            },
            "task_goal": {
                "type": "string",
                "description": "Main goal for init_context"
            },
            "steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Task steps for init_context"
            },
            "step_index": {
                "type": "integer",
                "description": "Step index to update (0-based)"
            },
            "status": {
                "type": "string",
                "enum": ["pending", "in_progress", "completed", "blocked"],
                "description": "New status for step"
            },
            "note_title": {
                "type": "string",
                "description": "Title for the note"
            },
            "note_content": {
                "type": "string",
                "description": "Content of the note"
            },
            "deliverable_name": {
                "type": "string",
                "description": "Name of deliverable file (without .md)"
            },
            "deliverable_content": {
                "type": "string",
                "description": "Content of deliverable"
            },
            "progress_note": {
                "type": "string",
                "description": "Progress note to add when updating plan"
            }
        },
        "required": ["action"]
    }

    def __init__(self):
        """初始化工具"""
        super().__init__()
        self._ensure_context_dir()
    
    def _ensure_context_dir(self):
        """确保上下文目录存在"""
        Path(CONTEXT_DIR).mkdir(parents=True, exist_ok=True)
    
    def _get_plan_path(self) -> Path:
        """获取任务计划文件路径"""
        return Path(CONTEXT_DIR) / "task_plan.md"
    
    def _get_notes_path(self) -> Path:
        """获取笔记文件路径"""
        return Path(CONTEXT_DIR) / "notes.md"
    
    def _get_deliverable_path(self, name: str) -> Path:
        """获取交付物文件路径"""
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
        return Path(CONTEXT_DIR) / f"{safe_name}.md"
    
    async def execute(
        self,
        action: str,
        task_goal: str = "",
        task_name: str = "",  # 别名
        task_description: str = "",  # 别名
        steps: List[str] = None,
        initial_steps: List[str] = None,  # 别名
        step_index: int = -1,
        status: str = "",
        note_title: str = "",
        note_content: str = "",
        deliverable_name: str = "deliverable",
        deliverable_content: str = "",
        progress_note: str = "",
        **kwargs
    ) -> ToolResult:
        """执行上下文工程操作"""
        # 处理参数别名
        actual_goal = task_goal or task_name or task_description or ""
        actual_steps = steps or initial_steps or []
        
        try:
            if action == "init_context":
                return await self._init_context(actual_goal, actual_steps)
            elif action == "read_plan":
                return await self._read_plan()
            elif action == "update_plan":
                return await self._update_plan(step_index, status, progress_note)
            elif action == "add_note":
                return await self._add_note(note_title, note_content)
            elif action == "read_notes":
                return await self._read_notes()
            elif action == "create_deliverable":
                return await self._create_deliverable(deliverable_name, deliverable_content)
            elif action == "read_deliverable":
                return await self._read_deliverable(deliverable_name)
            elif action == "list_context":
                return await self._list_context()
            elif action == "clear_context":
                return await self._clear_context()
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error=f"Unknown action: {action}"
                )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Context engineering error: {str(e)}"
            )
    
    async def _init_context(self, goal: str, steps: List[str]) -> ToolResult:
        """初始化上下文 - 创建任务计划"""
        if not goal:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error="Task goal is required for init_context"
            )
        
        # 创建任务计划文件
        plan_content = f"""# 任务计划 (Task Plan)

## 🎯 主要目标 (Goal)
{goal}

## 📋 执行步骤 (Steps)
"""
        for i, step in enumerate(steps, 1):
            plan_content += f"\n### 步骤 {i}: {step}\n- **状态**: ⏳ pending\n- **进度**: 未开始\n"
        
        plan_content += f"""
## 📊 整体进度 (Progress)
- **开始时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **当前阶段**: 步骤 1
- **完成度**: 0/{len(steps)}

## 📝 进度记录 (Log)
- [{datetime.now().strftime('%H:%M:%S')}] 任务计划已创建
"""
        
        # 写入文件
        self._get_plan_path().write_text(plan_content, encoding='utf-8')
        
        # 初始化空笔记文件
        notes_content = f"""# 研究笔记 (Notes)

> 任务: {goal}
> 创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

"""
        self._get_notes_path().write_text(notes_content, encoding='utf-8')
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=f"✅ 上下文已初始化！\n\n目标: {goal}\n步骤数: {len(steps)}\n\n文件:\n- task_plan.md: 任务计划\n- notes.md: 研究笔记\n\n💡 提示: 每次回复开始时请先读取 task_plan.md 保持专注！",
            metadata={
                "goal": goal,
                "step_count": len(steps),
                "context_dir": CONTEXT_DIR
            }
        )
    
    async def _read_plan(self) -> ToolResult:
        """读取任务计划"""
        plan_path = self._get_plan_path()
        
        if not plan_path.exists():
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output="📋 暂无任务计划。使用 init_context 创建新任务。",
                metadata={"has_plan": False}
            )
        
        content = plan_path.read_text(encoding='utf-8')
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=content,
            metadata={"has_plan": True, "path": str(plan_path)}
        )
    
    async def _update_plan(self, step_index: int, status: str, progress_note: str) -> ToolResult:
        """更新任务计划进度"""
        plan_path = self._get_plan_path()
        
        if not plan_path.exists():
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error="No task plan found. Use init_context first."
            )
        
        content = plan_path.read_text(encoding='utf-8')
        
        # 状态映射
        status_emoji = {
            "pending": "⏳ pending",
            "in_progress": "🔄 in_progress",
            "completed": "✅ completed",
            "blocked": "🚫 blocked"
        }
        
        # 更新特定步骤状态
        if step_index >= 0 and status:
            lines = content.split('\n')
            step_count = 0
            new_lines = []
            
            for i, line in enumerate(lines):
                if line.startswith('### 步骤'):
                    if step_count == step_index:
                        new_lines.append(line)
                        # 查找并更新状态行
                        j = i + 1
                        while j < len(lines) and not lines[j].startswith('### 步骤'):
                            if '**状态**' in lines[j]:
                                lines[j] = f"- **状态**: {status_emoji.get(status, status)}"
                            j += 1
                    step_count += 1
                new_lines.append(line)
            
            content = '\n'.join(lines)
        
        # 添加进度记录
        if progress_note:
            timestamp = datetime.now().strftime('%H:%M:%S')
            log_entry = f"- [{timestamp}] {progress_note}"
            
            # 在进度记录部分添加
            if "## 📝 进度记录" in content:
                content = content.replace(
                    "## 📝 进度记录 (Log)\n",
                    f"## 📝 进度记录 (Log)\n{log_entry}\n"
                )
            else:
                content += f"\n## 📝 进度记录 (Log)\n{log_entry}\n"
        
        # 写回文件
        plan_path.write_text(content, encoding='utf-8')
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=f"✅ 任务计划已更新！\n{progress_note if progress_note else '状态已更新'}",
            metadata={"step_index": step_index, "status": status}
        )
    
    async def _add_note(self, title: str, content: str) -> ToolResult:
        """添加研究笔记"""
        if not title or not content:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error="Note title and content are required"
            )
        
        notes_path = self._get_notes_path()
        
        # 如果文件不存在，创建
        if not notes_path.exists():
            initial_content = "# 研究笔记 (Notes)\n\n---\n\n"
            notes_path.write_text(initial_content, encoding='utf-8')
        
        existing = notes_path.read_text(encoding='utf-8')
        
        # 添加新笔记
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_note = f"""
## 📌 {title}
> 记录时间: {timestamp}

{content}

---
"""
        
        updated = existing + new_note
        notes_path.write_text(updated, encoding='utf-8')
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=f"✅ 笔记已添加: {title}",
            metadata={"title": title, "timestamp": timestamp}
        )
    
    async def _read_notes(self) -> ToolResult:
        """读取所有笔记"""
        notes_path = self._get_notes_path()
        
        if not notes_path.exists():
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output="📝 暂无笔记。使用 add_note 添加研究笔记。",
                metadata={"has_notes": False}
            )
        
        content = notes_path.read_text(encoding='utf-8')
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=content,
            metadata={"has_notes": True, "path": str(notes_path)}
        )
    
    async def _create_deliverable(self, name: str, content: str) -> ToolResult:
        """创建或更新交付物"""
        if not content:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error="Deliverable content is required"
            )
        
        deliverable_path = self._get_deliverable_path(name)
        
        # 添加元数据头
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        full_content = f"""# {name}

> 创建/更新时间: {timestamp}
> 类型: 交付物 (Deliverable)

---

{content}
"""
        
        deliverable_path.write_text(full_content, encoding='utf-8')
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=f"✅ 交付物已创建: {name}.md",
            metadata={"name": name, "path": str(deliverable_path)}
        )
    
    async def _read_deliverable(self, name: str) -> ToolResult:
        """读取交付物"""
        deliverable_path = self._get_deliverable_path(name)
        
        if not deliverable_path.exists():
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"📄 交付物 {name}.md 不存在。",
                metadata={"exists": False}
            )
        
        content = deliverable_path.read_text(encoding='utf-8')
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=content,
            metadata={"exists": True, "path": str(deliverable_path)}
        )
    
    async def _list_context(self) -> ToolResult:
        """列出所有上下文文件"""
        context_dir = Path(CONTEXT_DIR)
        
        if not context_dir.exists():
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output="📁 上下文目录为空",
                metadata={"files": []}
            )
        
        files = []
        for f in context_dir.glob("*.md"):
            stat = f.stat()
            files.append({
                "name": f.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
        
        output = "📁 上下文文件列表:\n\n"
        for f in files:
            output += f"- **{f['name']}** ({f['size']} bytes, 更新于 {f['modified']})\n"
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=output if files else "📁 上下文目录为空",
            metadata={"files": files}
        )
    
    async def _clear_context(self) -> ToolResult:
        """清除所有上下文文件"""
        context_dir = Path(CONTEXT_DIR)
        
        if not context_dir.exists():
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output="📁 上下文目录已经为空",
                metadata={"cleared": 0}
            )
        
        cleared = 0
        for f in context_dir.glob("*.md"):
            f.unlink()
            cleared += 1
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=f"🗑️ 已清除 {cleared} 个上下文文件",
            metadata={"cleared": cleared}
        )


# 创建工具实例
context_engineering_tool = ContextEngineeringTool()


# 便捷函数
def get_context_dir() -> str:
    """获取上下文目录路径"""
    return CONTEXT_DIR


def init_task_context(goal: str, steps: List[str]) -> Dict:
    """快速初始化任务上下文"""
    import asyncio
    result = asyncio.run(context_engineering_tool.execute(
        action="init_context",
        task_goal=goal,
        steps=steps
    ))
    return {"success": result.is_success, "output": result.output}


def read_task_plan() -> str:
    """读取当前任务计划"""
    plan_path = Path(CONTEXT_DIR) / "task_plan.md"
    if plan_path.exists():
        return plan_path.read_text(encoding='utf-8')
    return ""


def add_research_note(title: str, content: str) -> bool:
    """添加研究笔记"""
    import asyncio
    result = asyncio.run(context_engineering_tool.execute(
        action="add_note",
        note_title=title,
        note_content=content
    ))
    return result.is_success

