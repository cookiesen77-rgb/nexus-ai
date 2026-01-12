"""
计算器工具

支持基础数学运算和表达式计算
"""

import ast
import operator
import math
from typing import Any, Dict, Union

from .base import BaseTool, ToolResult, ToolStatus


class CalculatorTool(BaseTool):
    """计算器工具"""

    name = "calculator"
    description = "执行数学计算。支持基础运算(+,-,*,/,**,%)和数学函数(sqrt,sin,cos,tan,log,abs等)。"

    parameters = {
        "properties": {
            "expression": {
                "type": "string",
                "description": "要计算的数学表达式，例如: '2 + 3 * 4', 'sqrt(16)', 'sin(3.14/2)'"
            }
        },
        "required": ["expression"]
    }

    # 允许的操作符
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    # 允许的函数
    FUNCTIONS = {
        'sqrt': math.sqrt,
        'abs': abs,
        'round': round,
        'floor': math.floor,
        'ceil': math.ceil,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'asin': math.asin,
        'acos': math.acos,
        'atan': math.atan,
        'log': math.log,
        'log10': math.log10,
        'log2': math.log2,
        'exp': math.exp,
        'pow': pow,
        'max': max,
        'min': min,
    }

    # 允许的常量
    CONSTANTS = {
        'pi': math.pi,
        'e': math.e,
        'tau': math.tau,
        'inf': math.inf,
    }

    async def execute(self, expression: str) -> ToolResult:
        """
        执行数学计算

        Args:
            expression: 数学表达式

        Returns:
            ToolResult: 计算结果
        """
        try:
            # 清理表达式
            expression = expression.strip()

            # 解析并计算
            result = self._safe_eval(expression)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=result,
                metadata={"expression": expression}
            )

        except ZeroDivisionError:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error="Division by zero"
            )
        except ValueError as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=f"Invalid value: {e}"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=f"Calculation error: {e}"
            )

    def _safe_eval(self, expression: str) -> Union[int, float]:
        """
        安全地计算表达式

        Args:
            expression: 数学表达式

        Returns:
            计算结果
        """
        # 解析AST
        try:
            tree = ast.parse(expression, mode='eval')
        except SyntaxError as e:
            raise ValueError(f"Invalid expression syntax: {e}")

        return self._eval_node(tree.body)

    def _eval_node(self, node: ast.AST) -> Union[int, float]:
        """递归计算AST节点"""
        # 数字
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant type: {type(node.value)}")

        # 名称（常量）
        if isinstance(node, ast.Name):
            if node.id in self.CONSTANTS:
                return self.CONSTANTS[node.id]
            raise ValueError(f"Unknown constant: {node.id}")

        # 一元操作
        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type in self.OPERATORS:
                operand = self._eval_node(node.operand)
                return self.OPERATORS[op_type](operand)
            raise ValueError(f"Unsupported unary operator: {op_type}")

        # 二元操作
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type in self.OPERATORS:
                left = self._eval_node(node.left)
                right = self._eval_node(node.right)
                return self.OPERATORS[op_type](left, right)
            raise ValueError(f"Unsupported binary operator: {op_type}")

        # 函数调用
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in self.FUNCTIONS:
                    args = [self._eval_node(arg) for arg in node.args]
                    return self.FUNCTIONS[func_name](*args)
                raise ValueError(f"Unknown function: {func_name}")
            raise ValueError("Invalid function call")

        raise ValueError(f"Unsupported expression type: {type(node)}")


# 创建全局实例
calculator = CalculatorTool()

