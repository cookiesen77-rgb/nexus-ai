# Nexus 上下文工程 - 3文件持久化系统

## 概述

基于 [Manus planning-with-files](https://github.com/OthmanAdi/planning-with-files) 技术实现的上下文工程系统，解决 AI Agent 的四大核心问题：

1. **易失性记忆 (Volatile Memory)** - 通过持久化文件保持状态
2. **目标漂移 (Goal Drift)** - 通过定期读取计划文件保持专注
3. **隐藏错误 (Hidden Errors)** - 通过记录进度及时发现问题
4. **上下文塞满 (Context Stuffing)** - 通过结构化笔记管理信息

## 3文件模式

### 1. task_plan.md - 任务计划

任务的"指挥中心"，包含：
- 主要目标 (Goal)
- 执行步骤 (Steps)
- 当前进度 (Progress)
- 进度记录 (Log)

### 2. notes.md - 研究笔记

你的"外部大脑"，存储：
- 研究发现
- 重要信息
- 知识片段
- 参考资料

### 3. [deliverable].md - 交付物

最终工作成果文件。

## 使用方法

### 工具调用

```json
// 初始化上下文
{
  "action": "init_context",
  "task_goal": "创建一个用户管理系统",
  "steps": ["设计数据库", "实现 API", "编写前端", "测试"]
}

// 读取当前计划（每次回复开始时调用）
{
  "action": "read_plan"
}

// 更新进度
{
  "action": "update_plan",
  "step_index": 0,
  "status": "completed",
  "progress_note": "数据库设计完成"
}

// 添加研究笔记
{
  "action": "add_note",
  "note_title": "数据库设计方案",
  "note_content": "使用 PostgreSQL，主要表：users, roles, permissions..."
}

// 读取笔记
{
  "action": "read_notes"
}

// 创建交付物
{
  "action": "create_deliverable",
  "deliverable_name": "用户管理系统设计文档",
  "deliverable_content": "# 用户管理系统\n\n## 架构..."
}

// 列出所有上下文文件
{
  "action": "list_context"
}

// 清除上下文（开始新任务前）
{
  "action": "clear_context"
}
```

## 核心工作循环

```
1. 收到复杂任务
   ↓
2. init_context - 创建计划和步骤分解
   ↓
3. 循环执行每个步骤:
   a. read_plan - 保持目标专注（每次回复开始！）
   b. 执行当前步骤
   c. add_note - 保存重要发现
   d. update_plan - 更新进度
   ↓
4. create_deliverable - 生成最终交付物
   ↓
5. 完成任务
```

## 关键原则

1. **频繁读取计划** - 每次回复开始时读取 task_plan.md，防止目标漂移
2. **及时保存笔记** - 发现任何重要信息立即保存到 notes.md
3. **持续更新进度** - 完成每个步骤后更新状态，避免重复工作
4. **结构化存储** - 使用清晰的标题和格式组织信息

## 文件位置

上下文文件存储在：`$WORKSPACE_PATH/.nexus_context/`

## 系统提示词集成

系统提示词已包含上下文工程指南，对于超过3步骤的复杂任务，Nexus 会自动启用3文件模式。

## 参考

- [planning-with-files](https://github.com/OthmanAdi/planning-with-files) - 原始 Manus 技术
- 核心思想：用持久化文件对抗 LLM 的"遗忘"特性

