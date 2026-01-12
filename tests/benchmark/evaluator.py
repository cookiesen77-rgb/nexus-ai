"""
GAIA 评估器 - 评估Agent回答准确率
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .gaia_dataset import GAIATask, GAIALevel


@dataclass
class EvaluationResult:
    """评估结果"""
    task_id: str
    level: GAIALevel
    question: str
    expected: str
    predicted: str
    is_correct: bool
    match_type: str  # exact, numeric, contains, fuzzy
    confidence: float
    execution_time: float
    error: Optional[str] = None


@dataclass 
class BenchmarkReport:
    """基准测试报告"""
    timestamp: datetime = field(default_factory=datetime.now)
    total_tasks: int = 0
    completed_tasks: int = 0
    correct_tasks: int = 0
    
    # 按级别统计
    level_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # 详细结果
    results: List[EvaluationResult] = field(default_factory=list)
    
    # 性能指标
    total_time: float = 0.0
    avg_time: float = 0.0
    
    @property
    def accuracy(self) -> float:
        if self.completed_tasks == 0:
            return 0.0
        return self.correct_tasks / self.completed_tasks
    
    def get_level_accuracy(self, level: int) -> float:
        stats = self.level_stats.get(f"level_{level}", {})
        completed = stats.get("completed", 0)
        correct = stats.get("correct", 0)
        return correct / completed if completed > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "summary": {
                "total": self.total_tasks,
                "completed": self.completed_tasks,
                "correct": self.correct_tasks,
                "accuracy": f"{self.accuracy:.2%}",
            },
            "by_level": {
                "level_1": {
                    "accuracy": f"{self.get_level_accuracy(1):.2%}",
                    **self.level_stats.get("level_1", {})
                },
                "level_2": {
                    "accuracy": f"{self.get_level_accuracy(2):.2%}",
                    **self.level_stats.get("level_2", {})
                },
                "level_3": {
                    "accuracy": f"{self.get_level_accuracy(3):.2%}",
                    **self.level_stats.get("level_3", {})
                },
            },
            "performance": {
                "total_time_seconds": round(self.total_time, 2),
                "avg_time_seconds": round(self.avg_time, 2),
            },
            "results": [
                {
                    "task_id": r.task_id,
                    "level": r.level.value,
                    "correct": r.is_correct,
                    "match_type": r.match_type,
                    "time": round(r.execution_time, 2)
                }
                for r in self.results
            ]
        }
    
    def to_markdown(self) -> str:
        """生成Markdown格式报告"""
        lines = [
            "# GAIA Benchmark Report",
            f"\n**Date**: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## Summary",
            f"- Total Tasks: {self.total_tasks}",
            f"- Completed: {self.completed_tasks}",
            f"- Correct: {self.correct_tasks}",
            f"- **Overall Accuracy: {self.accuracy:.2%}**",
            "\n## By Level",
            f"| Level | Completed | Correct | Accuracy |",
            f"|-------|-----------|---------|----------|",
        ]
        
        for level in [1, 2, 3]:
            stats = self.level_stats.get(f"level_{level}", {})
            acc = self.get_level_accuracy(level)
            lines.append(
                f"| Level {level} | {stats.get('completed', 0)} | "
                f"{stats.get('correct', 0)} | {acc:.2%} |"
            )
        
        lines.extend([
            "\n## Performance",
            f"- Total Time: {self.total_time:.2f}s",
            f"- Avg Time per Task: {self.avg_time:.2f}s",
        ])
        
        return "\n".join(lines)


class GAIAEvaluator:
    """
    GAIA评估器
    
    评估Agent回答与期望答案的匹配程度
    """
    
    def __init__(self, strict: bool = False):
        """
        初始化评估器
        
        Args:
            strict: 是否严格匹配
        """
        self.strict = strict
    
    def evaluate(
        self,
        task: GAIATask,
        predicted: str,
        execution_time: float = 0.0
    ) -> EvaluationResult:
        """
        评估单个任务
        
        Args:
            task: 测试任务
            predicted: 预测答案
            execution_time: 执行时间
            
        Returns:
            EvaluationResult: 评估结果
        """
        expected = task.expected_answer.strip()
        predicted = predicted.strip() if predicted else ""
        
        # 尝试不同的匹配策略
        is_correct, match_type, confidence = self._match(expected, predicted)
        
        return EvaluationResult(
            task_id=task.id,
            level=task.level,
            question=task.question,
            expected=expected,
            predicted=predicted,
            is_correct=is_correct,
            match_type=match_type,
            confidence=confidence,
            execution_time=execution_time
        )
    
    def _match(
        self,
        expected: str,
        predicted: str
    ) -> Tuple[bool, str, float]:
        """
        匹配答案
        
        Returns:
            Tuple[bool, str, float]: (是否正确, 匹配类型, 置信度)
        """
        # 1. 精确匹配
        if expected.lower() == predicted.lower():
            return True, "exact", 1.0
        
        # 2. 数值匹配
        try:
            exp_num = self._extract_number(expected)
            pred_num = self._extract_number(predicted)
            if exp_num is not None and pred_num is not None:
                # 允许小误差
                if abs(exp_num - pred_num) < 0.01 * max(abs(exp_num), 1):
                    return True, "numeric", 0.95
        except:
            pass
        
        # 3. 包含匹配 (答案包含在响应中)
        if expected.lower() in predicted.lower():
            return True, "contains", 0.85
        
        # 4. 规范化匹配
        exp_norm = self._normalize(expected)
        pred_norm = self._normalize(predicted)
        if exp_norm == pred_norm:
            return True, "normalized", 0.9
        
        # 5. 模糊匹配 (如果非严格模式)
        if not self.strict:
            similarity = self._similarity(exp_norm, pred_norm)
            if similarity > 0.8:
                return True, "fuzzy", similarity
        
        return False, "no_match", 0.0
    
    def _extract_number(self, text: str) -> Optional[float]:
        """提取数字"""
        # 移除常见格式
        text = text.replace(",", "").replace("$", "").replace("%", "")
        
        # 查找数字
        match = re.search(r'-?\d+\.?\d*', text)
        if match:
            return float(match.group())
        return None
    
    def _normalize(self, text: str) -> str:
        """规范化文本"""
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)  # 移除标点
        text = ' '.join(text.split())  # 规范化空白
        return text
    
    def _similarity(self, a: str, b: str) -> float:
        """计算相似度 (简单的字符重叠)"""
        if not a or not b:
            return 0.0
        
        a_words = set(a.split())
        b_words = set(b.split())
        
        if not a_words or not b_words:
            return 0.0
        
        intersection = len(a_words & b_words)
        union = len(a_words | b_words)
        
        return intersection / union if union > 0 else 0.0
    
    def batch_evaluate(
        self,
        results: List[Tuple[GAIATask, str, float]]
    ) -> BenchmarkReport:
        """
        批量评估
        
        Args:
            results: [(task, predicted, time), ...]
            
        Returns:
            BenchmarkReport: 评估报告
        """
        report = BenchmarkReport()
        report.total_tasks = len(results)
        
        level_stats = {
            "level_1": {"total": 0, "completed": 0, "correct": 0},
            "level_2": {"total": 0, "completed": 0, "correct": 0},
            "level_3": {"total": 0, "completed": 0, "correct": 0},
        }
        
        for task, predicted, exec_time in results:
            level_key = f"level_{task.level.value}"
            level_stats[level_key]["total"] += 1
            
            if predicted:
                eval_result = self.evaluate(task, predicted, exec_time)
                report.results.append(eval_result)
                report.completed_tasks += 1
                report.total_time += exec_time
                
                level_stats[level_key]["completed"] += 1
                
                if eval_result.is_correct:
                    report.correct_tasks += 1
                    level_stats[level_key]["correct"] += 1
        
        report.level_stats = level_stats
        
        if report.completed_tasks > 0:
            report.avg_time = report.total_time / report.completed_tasks
        
        return report

