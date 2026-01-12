"""
基准测试运行器 - 批量运行GAIA测试
"""

import asyncio
import time
import json
from typing import List, Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

from .gaia_dataset import GAIADataset, GAIATask, GAIALevel
from .evaluator import GAIAEvaluator, BenchmarkReport


@dataclass
class RunnerConfig:
    """运行器配置"""
    max_concurrent: int = 3  # 最大并发数
    timeout: int = 120  # 单任务超时(秒)
    levels: List[int] = None  # 要测试的级别 [1, 2, 3]
    max_tasks: int = None  # 最大任务数
    save_results: bool = True
    output_dir: str = "data/benchmark_results"
    
    def __post_init__(self):
        if self.levels is None:
            self.levels = [1, 2, 3]


class BenchmarkRunner:
    """
    基准测试运行器
    
    Usage:
        runner = BenchmarkRunner(agent_func)
        report = await runner.run(dataset)
    """
    
    def __init__(
        self,
        agent_func: Callable[[str], Awaitable[str]],
        config: RunnerConfig = None
    ):
        """
        初始化运行器
        
        Args:
            agent_func: Agent执行函数 async (question) -> answer
            config: 运行配置
        """
        self.agent_func = agent_func
        self.config = config or RunnerConfig()
        self.evaluator = GAIAEvaluator()
        
        # 确保输出目录存在
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
    
    async def run(
        self,
        dataset: GAIADataset,
        progress_callback: Callable[[int, int, str], None] = None
    ) -> BenchmarkReport:
        """
        运行基准测试
        
        Args:
            dataset: GAIA数据集
            progress_callback: 进度回调 (completed, total, task_id)
            
        Returns:
            BenchmarkReport: 测试报告
        """
        # 过滤任务
        tasks = self._filter_tasks(dataset)
        total = len(tasks)
        
        print(f"Starting benchmark with {total} tasks")
        print(f"Levels: {self.config.levels}")
        print(f"Max concurrent: {self.config.max_concurrent}")
        
        # 运行任务
        results = []
        semaphore = asyncio.Semaphore(self.config.max_concurrent)
        
        async def run_task(task: GAIATask, idx: int):
            async with semaphore:
                start = time.time()
                
                try:
                    answer = await asyncio.wait_for(
                        self.agent_func(task.question),
                        timeout=self.config.timeout
                    )
                except asyncio.TimeoutError:
                    answer = None
                    print(f"  Task {task.id} timed out")
                except Exception as e:
                    answer = None
                    print(f"  Task {task.id} error: {e}")
                
                exec_time = time.time() - start
                
                if progress_callback:
                    progress_callback(idx + 1, total, task.id)
                
                return (task, answer, exec_time)
        
        # 并发执行
        tasks_with_idx = [(task, i) for i, task in enumerate(tasks)]
        coroutines = [run_task(t, i) for t, i in tasks_with_idx]
        results = await asyncio.gather(*coroutines)
        
        # 评估结果
        report = self.evaluator.batch_evaluate(results)
        
        # 保存结果
        if self.config.save_results:
            self._save_results(report)
        
        return report
    
    def _filter_tasks(self, dataset: GAIADataset) -> List[GAIATask]:
        """过滤任务"""
        tasks = []
        
        for task in dataset:
            if task.level.value in self.config.levels:
                tasks.append(task)
        
        # 限制数量
        if self.config.max_tasks:
            tasks = tasks[:self.config.max_tasks]
        
        return tasks
    
    def _save_results(self, report: BenchmarkReport):
        """保存结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存JSON
        json_path = Path(self.config.output_dir) / f"report_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        
        # 保存Markdown
        md_path = Path(self.config.output_dir) / f"report_{timestamp}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(report.to_markdown())
        
        print(f"\nResults saved to:")
        print(f"  - {json_path}")
        print(f"  - {md_path}")
    
    async def run_single(self, task: GAIATask) -> Dict[str, Any]:
        """运行单个任务"""
        start = time.time()
        
        try:
            answer = await asyncio.wait_for(
                self.agent_func(task.question),
                timeout=self.config.timeout
            )
        except Exception as e:
            answer = None
        
        exec_time = time.time() - start
        
        result = self.evaluator.evaluate(task, answer, exec_time)
        
        return {
            "task_id": task.id,
            "question": task.question,
            "expected": task.expected_answer,
            "predicted": answer,
            "is_correct": result.is_correct,
            "match_type": result.match_type,
            "time": exec_time
        }


async def run_benchmark_demo():
    """运行基准测试演示"""
    import sys
    sys.path.insert(0, '.')
    
    # 创建示例数据集
    dataset = GAIADataset()
    dataset.add_sample_tasks()
    
    print(f"Dataset statistics: {dataset.get_statistics()}")
    
    # 简单的模拟Agent
    async def mock_agent(question: str) -> str:
        """模拟Agent响应"""
        await asyncio.sleep(0.1)
        
        # 简单的规则响应
        if "15 multiplied by 7" in question:
            return "105"
        elif "Fahrenheit to Celsius" in question:
            return "38"
        elif "capital of France" in question:
            return "Paris"
        elif "compound interest" in question:
            return "157.63"
        elif "kilometers" in question:
            return "241.35"
        elif "prime numbers" in question:
            return "328"
        else:
            return "I don't know"
    
    # 运行测试
    config = RunnerConfig(
        levels=[1, 2],
        max_concurrent=2,
        save_results=False
    )
    
    runner = BenchmarkRunner(mock_agent, config)
    
    def on_progress(completed, total, task_id):
        print(f"  Progress: {completed}/{total} - {task_id}")
    
    report = await runner.run(dataset, on_progress)
    
    # 打印报告
    print("\n" + "=" * 50)
    print(report.to_markdown())
    
    return report


if __name__ == "__main__":
    asyncio.run(run_benchmark_demo())

