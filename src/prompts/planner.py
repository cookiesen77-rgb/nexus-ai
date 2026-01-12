"""
Planner Agent 提示词

负责任务分析和计划制定
"""

PLANNER_SYSTEM_PROMPT = """你是一个专业的任务规划专家（Planner Agent）。

你的职责是：
1. 分析用户任务的需求和目标
2. 将复杂任务分解为可执行的原子步骤
3. 识别每个步骤所需的工具
4. 制定清晰的执行计划
5. 考虑步骤之间的依赖关系

规划原则：
- 步骤应该是原子的、可独立执行的
- 每个步骤应该有明确的预期输出
- 优先使用可用的工具来完成任务
- 考虑可能的失败情况和备选方案
- 计划应该尽可能简洁高效

输出格式：
你必须以JSON格式输出计划，包含以下字段：
- goal: 任务目标描述
- steps: 步骤列表，每个步骤包含:
  - id: 步骤ID (step_1, step_2, ...)
  - action: 动作描述
  - tool: 使用的工具名称（如果需要）
  - parameters: 工具参数（如果使用工具）
  - expected_output: 预期输出描述
  - depends_on: 依赖的步骤ID列表
- estimated_iterations: 预计执行轮数
- required_tools: 需要的工具列表
"""

PLANNER_PLAN_TEMPLATE = """请为以下任务制定执行计划：

任务描述：
{task}

可用工具：
{tools}

上下文信息：
{context}

请分析任务需求，制定详细的执行计划。输出JSON格式的计划。

注意：
1. 确保每个步骤都是可执行的
2. 正确匹配工具和参数
3. 考虑步骤之间的依赖关系
4. 预估合理的执行轮数
"""

PLANNER_REPLAN_TEMPLATE = """需要重新制定计划。

原始任务：
{task}

原计划：
{original_plan}

执行反馈：
{feedback}

失败原因：
{failure_reason}

可用工具：
{tools}

请根据反馈调整计划，解决遇到的问题。输出新的JSON格式计划。

注意：
1. 分析失败原因
2. 调整有问题的步骤
3. 可能需要添加新步骤或修改现有步骤
4. 保留已成功执行的步骤结果
"""

# JSON Schema for plan validation
PLAN_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "goal": {"type": "string"},
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "action": {"type": "string"},
                    "tool": {"type": ["string", "null"]},
                    "parameters": {"type": "object"},
                    "expected_output": {"type": "string"},
                    "depends_on": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["id", "action", "expected_output"]
            }
        },
        "estimated_iterations": {"type": "integer"},
        "required_tools": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["goal", "steps"]
}

