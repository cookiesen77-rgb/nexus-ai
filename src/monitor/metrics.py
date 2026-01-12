"""
指标收集 - 性能监控
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"      # 计数器
    GAUGE = "gauge"          # 仪表
    HISTOGRAM = "histogram"  # 直方图
    SUMMARY = "summary"      # 摘要


@dataclass
class MetricPoint:
    """指标数据点"""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class MetricsSummary:
    """指标摘要"""
    period: str
    start_time: datetime
    end_time: datetime
    
    # LLM指标
    llm_calls: int = 0
    llm_errors: int = 0
    llm_avg_latency_ms: float = 0.0
    llm_total_input_tokens: int = 0
    llm_total_output_tokens: int = 0
    
    # 工具指标
    tool_calls: int = 0
    tool_errors: int = 0
    tool_avg_latency_ms: float = 0.0
    
    # 任务指标
    tasks_submitted: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    
    # 缓存指标
    cache_hits: int = 0
    cache_misses: int = 0
    
    @property
    def llm_success_rate(self) -> float:
        total = self.llm_calls
        return (total - self.llm_errors) / total if total > 0 else 1.0
    
    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0


class MetricsCollector:
    """
    指标收集器
    
    收集和聚合系统性能指标
    """
    
    def __init__(self, retention_hours: int = 24):
        """
        初始化指标收集器
        
        Args:
            retention_hours: 数据保留时间(小时)
        """
        self.retention_hours = retention_hours
        self._metrics: List[MetricPoint] = []
        
        # 聚合计数器
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
    
    def record(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Dict[str, str] = None
    ):
        """
        记录指标
        
        Args:
            name: 指标名
            value: 值
            metric_type: 类型
            labels: 标签
        """
        point = MetricPoint(
            name=name,
            value=value,
            metric_type=metric_type,
            labels=labels or {}
        )
        self._metrics.append(point)
        
        # 更新聚合
        if metric_type == MetricType.COUNTER:
            self._counters[name] += int(value)
        elif metric_type == MetricType.GAUGE:
            self._gauges[name] = value
        elif metric_type == MetricType.HISTOGRAM:
            self._histograms[name].append(value)
        
        # 清理过期数据
        self._cleanup()
    
    def increment(self, name: str, value: int = 1, labels: Dict[str, str] = None):
        """增加计数器"""
        self.record(name, value, MetricType.COUNTER, labels)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """设置仪表值"""
        self.record(name, value, MetricType.GAUGE, labels)
    
    def observe(self, name: str, value: float, labels: Dict[str, str] = None):
        """观察值 (用于直方图)"""
        self.record(name, value, MetricType.HISTOGRAM, labels)
    
    def record_llm_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        success: bool,
        cached: bool = False
    ):
        """
        记录LLM调用
        
        Args:
            model: 模型名
            input_tokens: 输入token数
            output_tokens: 输出token数
            latency_ms: 延迟(毫秒)
            success: 是否成功
            cached: 是否缓存命中
        """
        labels = {"model": model}
        
        self.increment("llm_calls_total", 1, labels)
        
        if not success:
            self.increment("llm_errors_total", 1, labels)
        
        self.observe("llm_latency_ms", latency_ms, labels)
        self.increment("llm_input_tokens_total", input_tokens, labels)
        self.increment("llm_output_tokens_total", output_tokens, labels)
        
        if cached:
            self.increment("llm_cache_hits_total", 1, labels)
        else:
            self.increment("llm_cache_misses_total", 1, labels)
    
    def record_tool_call(
        self,
        tool: str,
        latency_ms: float,
        success: bool
    ):
        """
        记录工具调用
        
        Args:
            tool: 工具名
            latency_ms: 延迟
            success: 是否成功
        """
        labels = {"tool": tool}
        
        self.increment("tool_calls_total", 1, labels)
        
        if not success:
            self.increment("tool_errors_total", 1, labels)
        
        self.observe("tool_latency_ms", latency_ms, labels)
    
    def record_task(self, status: str):
        """记录任务状态"""
        self.increment(f"tasks_{status}_total", 1)
    
    def _cleanup(self):
        """清理过期数据"""
        cutoff = time.time() - (self.retention_hours * 3600)
        self._metrics = [m for m in self._metrics if m.timestamp > cutoff]
        
        # 限制直方图大小
        for name in self._histograms:
            if len(self._histograms[name]) > 10000:
                self._histograms[name] = self._histograms[name][-5000:]
    
    def get_summary(self, period: str = "1h") -> MetricsSummary:
        """
        获取指标摘要
        
        Args:
            period: 时间段 (1h, 24h, 7d)
            
        Returns:
            MetricsSummary: 摘要
        """
        # 解析时间段
        hours = {"1h": 1, "24h": 24, "7d": 168}.get(period, 1)
        cutoff = time.time() - (hours * 3600)
        
        # 过滤数据
        recent = [m for m in self._metrics if m.timestamp > cutoff]
        
        # 聚合
        llm_calls = sum(1 for m in recent if m.name == "llm_calls_total")
        llm_errors = sum(1 for m in recent if m.name == "llm_errors_total")
        llm_latencies = [m.value for m in recent if m.name == "llm_latency_ms"]
        
        tool_calls = sum(1 for m in recent if m.name == "tool_calls_total")
        tool_errors = sum(1 for m in recent if m.name == "tool_errors_total")
        tool_latencies = [m.value for m in recent if m.name == "tool_latency_ms"]
        
        return MetricsSummary(
            period=period,
            start_time=datetime.fromtimestamp(cutoff),
            end_time=datetime.now(),
            llm_calls=llm_calls,
            llm_errors=llm_errors,
            llm_avg_latency_ms=sum(llm_latencies) / len(llm_latencies) if llm_latencies else 0,
            llm_total_input_tokens=self._counters.get("llm_input_tokens_total", 0),
            llm_total_output_tokens=self._counters.get("llm_output_tokens_total", 0),
            tool_calls=tool_calls,
            tool_errors=tool_errors,
            tool_avg_latency_ms=sum(tool_latencies) / len(tool_latencies) if tool_latencies else 0,
            cache_hits=self._counters.get("llm_cache_hits_total", 0),
            cache_misses=self._counters.get("llm_cache_misses_total", 0),
        )
    
    def export_prometheus(self) -> str:
        """
        导出Prometheus格式
        
        Returns:
            str: Prometheus文本格式
        """
        lines = []
        
        # 导出计数器
        for name, value in self._counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        
        # 导出仪表
        for name, value in self._gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        
        # 导出直方图摘要
        for name, values in self._histograms.items():
            if values:
                lines.append(f"# TYPE {name} summary")
                lines.append(f"{name}_count {len(values)}")
                lines.append(f"{name}_sum {sum(values)}")
                
                sorted_vals = sorted(values)
                lines.append(f'{name}{{quantile="0.5"}} {sorted_vals[len(sorted_vals)//2]}')
                lines.append(f'{name}{{quantile="0.9"}} {sorted_vals[int(len(sorted_vals)*0.9)]}')
                lines.append(f'{name}{{quantile="0.99"}} {sorted_vals[int(len(sorted_vals)*0.99)]}')
        
        return '\n'.join(lines)
    
    def reset(self):
        """重置所有指标"""
        self._metrics.clear()
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()


# 全局收集器实例
_default_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器"""
    global _default_collector
    if _default_collector is None:
        _default_collector = MetricsCollector()
    return _default_collector

