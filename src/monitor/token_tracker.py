"""
Token跟踪器 - Token使用和成本监控
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict


# 模型定价 (每1000 tokens)
# ALLAPI中转站定价可能与官方不同，请根据实际情况调整
MODEL_PRICING = {
    # Doubao (豆包) - ALLAPI
    "doubao-seed-1-8-251228": {"input": 0.001, "output": 0.002},
    "doubao-seed-1-8-251228-thinking": {"input": 0.002, "output": 0.004},
    
    # Claude 系列
    "claude-sonnet-4-5-20250929": {"input": 0.003, "output": 0.015},
    "claude-haiku-4-5-20251001": {"input": 0.00025, "output": 0.00125},
    
    # GPT 系列
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
}


@dataclass
class TokenUsageRecord:
    """Token使用记录"""
    model: str
    input_tokens: int
    output_tokens: int
    timestamp: datetime = field(default_factory=datetime.now)
    cached: bool = False
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "timestamp": self.timestamp.isoformat(),
            "cached": self.cached,
            "session_id": self.session_id,
            "task_id": self.task_id,
        }


@dataclass
class TokenUsageSummary:
    """Token使用摘要"""
    period: str
    start_time: datetime
    end_time: datetime
    
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    
    by_model: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    estimated_cost_usd: float = 0.0
    cached_tokens: int = 0
    cache_savings_usd: float = 0.0
    
    call_count: int = 0


@dataclass
class CostEstimate:
    """成本估算"""
    model: str
    input_cost: float
    output_cost: float
    total_cost: float
    currency: str = "USD"


class TokenTracker:
    """
    Token使用跟踪器
    
    跟踪Token使用量并估算成本
    """
    
    def __init__(
        self,
        storage_path: str = None,
        retention_days: int = 30
    ):
        """
        初始化Token跟踪器
        
        Args:
            storage_path: 存储路径
            retention_days: 数据保留天数
        """
        self.storage_path = Path(storage_path) if storage_path else None
        self.retention_days = retention_days
        
        self._records: List[TokenUsageRecord] = []
        self._by_model: Dict[str, Dict[str, int]] = defaultdict(lambda: {"input": 0, "output": 0})
        self._by_session: Dict[str, List[TokenUsageRecord]] = defaultdict(list)
        
        # 加载历史数据
        if self.storage_path:
            self._load()
    
    def _load(self):
        """加载历史数据"""
        if not self.storage_path:
            return
        
        history_file = self.storage_path / "token_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                for item in data:
                    record = TokenUsageRecord(
                        model=item["model"],
                        input_tokens=item["input_tokens"],
                        output_tokens=item["output_tokens"],
                        timestamp=datetime.fromisoformat(item["timestamp"]),
                        cached=item.get("cached", False),
                        session_id=item.get("session_id"),
                        task_id=item.get("task_id"),
                    )
                    self._records.append(record)
                    self._index_record(record)
            except Exception as e:
                print(f"Warning: Failed to load token history: {e}")
    
    def _save(self):
        """保存数据"""
        if not self.storage_path:
            return
        
        self.storage_path.mkdir(parents=True, exist_ok=True)
        history_file = self.storage_path / "token_history.json"
        
        # 只保存最近的数据
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        recent = [r for r in self._records if r.timestamp > cutoff]
        
        with open(history_file, 'w') as f:
            json.dump([r.to_dict() for r in recent], f, indent=2)
    
    def _index_record(self, record: TokenUsageRecord):
        """索引记录"""
        self._by_model[record.model]["input"] += record.input_tokens
        self._by_model[record.model]["output"] += record.output_tokens
        
        if record.session_id:
            self._by_session[record.session_id].append(record)
    
    def track(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached: bool = False,
        session_id: str = None,
        task_id: str = None
    ) -> TokenUsageRecord:
        """
        记录Token使用
        
        Args:
            model: 模型名
            input_tokens: 输入token数
            output_tokens: 输出token数
            cached: 是否缓存命中
            session_id: 会话ID
            task_id: 任务ID
            
        Returns:
            TokenUsageRecord: 使用记录
        """
        record = TokenUsageRecord(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached=cached,
            session_id=session_id,
            task_id=task_id
        )
        
        self._records.append(record)
        self._index_record(record)
        
        # 定期保存
        if len(self._records) % 100 == 0:
            self._save()
        
        return record
    
    def get_usage(self, period: str = "today") -> TokenUsageSummary:
        """
        获取使用量统计
        
        Args:
            period: 时间段 (today, week, month, all)
            
        Returns:
            TokenUsageSummary: 使用摘要
        """
        # 计算时间范围
        now = datetime.now()
        if period == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start = now - timedelta(days=7)
        elif period == "month":
            start = now - timedelta(days=30)
        else:
            start = datetime.min
        
        # 过滤记录
        filtered = [r for r in self._records if r.timestamp >= start]
        
        # 聚合
        summary = TokenUsageSummary(
            period=period,
            start_time=start,
            end_time=now,
            call_count=len(filtered)
        )
        
        by_model = defaultdict(lambda: {"input": 0, "output": 0})
        cached_tokens = 0
        
        for record in filtered:
            summary.total_input_tokens += record.input_tokens
            summary.total_output_tokens += record.output_tokens
            by_model[record.model]["input"] += record.input_tokens
            by_model[record.model]["output"] += record.output_tokens
            
            if record.cached:
                cached_tokens += record.input_tokens
        
        summary.total_tokens = summary.total_input_tokens + summary.total_output_tokens
        summary.by_model = dict(by_model)
        summary.cached_tokens = cached_tokens
        
        # 计算成本
        summary.estimated_cost_usd = self._calculate_cost(filtered)
        summary.cache_savings_usd = self._calculate_cache_savings(filtered)
        
        return summary
    
    def _calculate_cost(self, records: List[TokenUsageRecord]) -> float:
        """计算成本"""
        total = 0.0
        
        for record in records:
            pricing = MODEL_PRICING.get(record.model, {"input": 0.01, "output": 0.03})
            
            if not record.cached:
                input_cost = (record.input_tokens / 1000) * pricing["input"]
            else:
                input_cost = 0  # 缓存命中不计费
            
            output_cost = (record.output_tokens / 1000) * pricing["output"]
            total += input_cost + output_cost
        
        return round(total, 4)
    
    def _calculate_cache_savings(self, records: List[TokenUsageRecord]) -> float:
        """计算缓存节省的成本"""
        savings = 0.0
        
        for record in records:
            if record.cached:
                pricing = MODEL_PRICING.get(record.model, {"input": 0.01})
                savings += (record.input_tokens / 1000) * pricing["input"]
        
        return round(savings, 4)
    
    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> CostEstimate:
        """
        估算成本
        
        Args:
            model: 模型名
            input_tokens: 输入token数
            output_tokens: 输出token数
            
        Returns:
            CostEstimate: 成本估算
        """
        pricing = MODEL_PRICING.get(model, {"input": 0.01, "output": 0.03})
        
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        
        return CostEstimate(
            model=model,
            input_cost=round(input_cost, 6),
            output_cost=round(output_cost, 6),
            total_cost=round(input_cost + output_cost, 6)
        )
    
    def get_session_usage(self, session_id: str) -> TokenUsageSummary:
        """获取会话使用量"""
        records = self._by_session.get(session_id, [])
        
        summary = TokenUsageSummary(
            period=f"session:{session_id}",
            start_time=records[0].timestamp if records else datetime.now(),
            end_time=records[-1].timestamp if records else datetime.now(),
            call_count=len(records)
        )
        
        for record in records:
            summary.total_input_tokens += record.input_tokens
            summary.total_output_tokens += record.output_tokens
        
        summary.total_tokens = summary.total_input_tokens + summary.total_output_tokens
        summary.estimated_cost_usd = self._calculate_cost(records)
        
        return summary
    
    def reset(self):
        """重置跟踪器"""
        self._records.clear()
        self._by_model.clear()
        self._by_session.clear()


# 全局跟踪器实例
_default_tracker: Optional[TokenTracker] = None


def get_token_tracker(storage_path: str = None) -> TokenTracker:
    """获取全局Token跟踪器"""
    global _default_tracker
    if _default_tracker is None:
        _default_tracker = TokenTracker(storage_path or "data/metrics")
    return _default_tracker

