"""
GAIA 基准测试数据集

GAIA (General AI Assistants) 是一个评估AI助手通用能力的基准测试
https://huggingface.co/datasets/gaia-benchmark/GAIA
"""

import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class GAIALevel(Enum):
    """GAIA难度级别"""
    LEVEL_1 = 1  # 简单任务，通常1-2步
    LEVEL_2 = 2  # 中等任务，需要多步推理
    LEVEL_3 = 3  # 困难任务，需要复杂推理和工具使用


@dataclass
class GAIATask:
    """GAIA测试任务"""
    id: str
    question: str
    level: GAIALevel
    expected_answer: str
    
    # 可选字段
    file_path: Optional[str] = None  # 附带文件
    file_content: Optional[str] = None
    annotator_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 评估结果
    predicted_answer: Optional[str] = None
    is_correct: Optional[bool] = None
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "level": self.level.value,
            "expected_answer": self.expected_answer,
            "file_path": self.file_path,
            "predicted_answer": self.predicted_answer,
            "is_correct": self.is_correct,
            "execution_time": self.execution_time
        }


class GAIADataset:
    """
    GAIA数据集加载器
    
    支持从本地文件或HuggingFace加载
    """
    
    def __init__(self, data_dir: str = "data/gaia"):
        """
        初始化数据集
        
        Args:
            data_dir: 数据目录
        """
        self.data_dir = Path(data_dir)
        self.tasks: List[GAIATask] = []
        self._by_level: Dict[GAIALevel, List[GAIATask]] = {
            GAIALevel.LEVEL_1: [],
            GAIALevel.LEVEL_2: [],
            GAIALevel.LEVEL_3: []
        }
    
    def load_from_file(self, file_path: str) -> int:
        """
        从JSON文件加载数据集
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            int: 加载的任务数
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for item in data:
            task = self._parse_task(item)
            self.tasks.append(task)
            self._by_level[task.level].append(task)
        
        return len(self.tasks)
    
    def load_from_jsonl(self, file_path: str) -> int:
        """从JSONL文件加载"""
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    task = self._parse_task(item)
                    self.tasks.append(task)
                    self._by_level[task.level].append(task)
                    count += 1
        return count
    
    def _parse_task(self, item: Dict[str, Any]) -> GAIATask:
        """解析任务数据"""
        level_map = {1: GAIALevel.LEVEL_1, 2: GAIALevel.LEVEL_2, 3: GAIALevel.LEVEL_3}
        level = level_map.get(item.get("Level", 1), GAIALevel.LEVEL_1)
        
        return GAIATask(
            id=item.get("task_id", item.get("id", "")),
            question=item.get("Question", item.get("question", "")),
            level=level,
            expected_answer=item.get("Final answer", item.get("answer", "")),
            file_path=item.get("file_path"),
            annotator_metadata=item.get("Annotator Metadata", {})
        )
    
    def add_sample_tasks(self):
        """添加示例测试任务 (用于演示)"""
        samples = [
            # Level 1: 简单任务
            GAIATask(
                id="sample_1",
                question="What is 15 multiplied by 7?",
                level=GAIALevel.LEVEL_1,
                expected_answer="105"
            ),
            GAIATask(
                id="sample_2",
                question="Convert 100 degrees Fahrenheit to Celsius. Round to the nearest integer.",
                level=GAIALevel.LEVEL_1,
                expected_answer="38"
            ),
            GAIATask(
                id="sample_3",
                question="What is the capital of France?",
                level=GAIALevel.LEVEL_1,
                expected_answer="Paris"
            ),
            
            # Level 2: 中等任务
            GAIATask(
                id="sample_4",
                question="Calculate the compound interest on $1000 at 5% annual rate for 3 years. Round to 2 decimal places.",
                level=GAIALevel.LEVEL_2,
                expected_answer="157.63"
            ),
            GAIATask(
                id="sample_5",
                question="If a train travels at 60 mph for 2.5 hours, how many kilometers does it travel? (1 mile = 1.609 km)",
                level=GAIALevel.LEVEL_2,
                expected_answer="241.35"
            ),
            
            # Level 3: 复杂任务
            GAIATask(
                id="sample_6",
                question="Write a Python function to check if a number is prime, then use it to find the sum of all prime numbers less than 50.",
                level=GAIALevel.LEVEL_3,
                expected_answer="328"
            ),
        ]
        
        for task in samples:
            self.tasks.append(task)
            self._by_level[task.level].append(task)
    
    def get_by_level(self, level: GAIALevel) -> List[GAIATask]:
        """按难度级别获取任务"""
        return self._by_level[level]
    
    def get_task(self, task_id: str) -> Optional[GAIATask]:
        """根据ID获取任务"""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取数据集统计"""
        return {
            "total": len(self.tasks),
            "level_1": len(self._by_level[GAIALevel.LEVEL_1]),
            "level_2": len(self._by_level[GAIALevel.LEVEL_2]),
            "level_3": len(self._by_level[GAIALevel.LEVEL_3]),
        }
    
    def __len__(self) -> int:
        return len(self.tasks)
    
    def __iter__(self):
        return iter(self.tasks)

