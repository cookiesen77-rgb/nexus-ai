"""
监控模块测试
"""

import pytest
import asyncio


class TestMetricsCollector:
    """指标收集器测试"""
    
    def test_increment(self):
        """测试计数器递增"""
        from src.monitor import MetricsCollector
        
        collector = MetricsCollector()
        collector.increment("test_counter", 1)
        collector.increment("test_counter", 2)
        
        assert collector._counters["test_counter"] == 3
    
    def test_record_llm_call(self):
        """测试LLM调用记录"""
        from src.monitor import MetricsCollector
        
        collector = MetricsCollector()
        collector.record_llm_call(
            model="claude-sonnet-4-5-20250929",
            input_tokens=100,
            output_tokens=50,
            latency_ms=500,
            success=True
        )
        
        summary = collector.get_summary("1h")
        assert summary.llm_calls >= 1
    
    def test_record_tool_call(self):
        """测试工具调用记录"""
        from src.monitor import MetricsCollector
        
        collector = MetricsCollector()
        collector.record_tool_call(
            tool="calculator",
            latency_ms=10,
            success=True
        )
        
        summary = collector.get_summary("1h")
        assert summary.tool_calls >= 1
    
    def test_export_prometheus(self):
        """测试Prometheus导出"""
        from src.monitor import MetricsCollector
        
        collector = MetricsCollector()
        collector.increment("requests_total", 10)
        collector.observe("latency_ms", 100)
        
        output = collector.export_prometheus()
        
        assert "requests_total" in output
        assert "latency_ms" in output


class TestTokenTracker:
    """Token跟踪器测试"""
    
    def test_track(self):
        """测试跟踪记录"""
        from src.monitor import TokenTracker
        
        tracker = TokenTracker()
        tracker.track(
            model="claude-sonnet-4-5-20250929",
            input_tokens=100,
            output_tokens=50
        )
        
        usage = tracker.get_usage("today")
        assert usage.total_input_tokens == 100
        assert usage.total_output_tokens == 50
    
    def test_estimate_cost(self):
        """测试成本估算"""
        from src.monitor import TokenTracker
        import pytest
        
        tracker = TokenTracker()
        estimate = tracker.estimate_cost(
            model="claude-sonnet-4-5-20250929",
            input_tokens=1000,
            output_tokens=500
        )
        
        assert estimate.input_cost > 0
        assert estimate.output_cost > 0
        # 使用近似比较避免浮点精度问题
        assert estimate.total_cost == pytest.approx(estimate.input_cost + estimate.output_cost, rel=1e-9)
    
    def test_usage_summary(self):
        """测试使用摘要"""
        from src.monitor import TokenTracker
        
        tracker = TokenTracker()
        
        # 添加一些记录
        for i in range(5):
            tracker.track(
                model="claude-sonnet-4-5-20250929",
                input_tokens=100 * (i + 1),
                output_tokens=50 * (i + 1)
            )
        
        usage = tracker.get_usage("today")
        
        assert usage.call_count == 5
        assert usage.total_tokens > 0
        assert usage.estimated_cost_usd > 0


class TestAlertManager:
    """告警管理器测试"""
    
    @pytest.mark.asyncio
    async def test_check_rules(self):
        """测试规则检查"""
        from src.monitor import AlertManager, AlertSeverity
        
        manager = AlertManager()
        
        # 触发高错误率告警
        alerts = await manager.check_rules({"error_rate": 0.15})
        
        high_error_alerts = [a for a in alerts if a.name == "high_error_rate"]
        assert len(high_error_alerts) > 0
    
    @pytest.mark.asyncio
    async def test_no_alert_below_threshold(self):
        """测试阈值以下不告警"""
        from src.monitor import AlertManager
        
        manager = AlertManager()
        
        # 错误率低于阈值
        alerts = await manager.check_rules({"error_rate": 0.05})
        
        high_error_alerts = [a for a in alerts if a.name == "high_error_rate"]
        assert len(high_error_alerts) == 0
    
    def test_acknowledge(self):
        """测试确认告警"""
        from src.monitor import AlertManager, Alert, AlertSeverity, AlertStatus
        
        manager = AlertManager()
        
        # 手动添加告警
        alert = Alert(
            id="test-1",
            name="test_alert",
            message="Test message",
            severity=AlertSeverity.WARNING
        )
        manager._alerts["test-1"] = alert
        
        result = manager.acknowledge("test-1")
        
        assert result is True
        assert alert.status == AlertStatus.ACKNOWLEDGED
    
    def test_resolve(self):
        """测试解决告警"""
        from src.monitor import AlertManager, Alert, AlertSeverity, AlertStatus
        
        manager = AlertManager()
        
        alert = Alert(
            id="test-2",
            name="test_alert",
            message="Test message",
            severity=AlertSeverity.WARNING
        )
        manager._alerts["test-2"] = alert
        
        result = manager.resolve("test-2")
        
        assert result is True
        assert alert.status == AlertStatus.RESOLVED
    
    def test_get_stats(self):
        """测试获取统计"""
        from src.monitor import AlertManager
        
        manager = AlertManager()
        stats = manager.get_stats()
        
        assert "total" in stats
        assert "active" in stats
        assert "by_severity" in stats


class TestCacheStats:
    """缓存统计测试"""
    
    def test_lru_cache(self):
        """测试LRU缓存"""
        from src.cache import LRUCache
        
        cache = LRUCache(max_size=3)
        
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        
        hit, val = cache.get("a")
        assert hit is True
        assert val == 1
        
        # 添加第4个，应该淘汰最旧的
        cache.set("d", 4)
        
        # b应该被淘汰
        hit, _ = cache.get("b")
        assert hit is False
    
    def test_cache_hit_rate(self):
        """测试命中率"""
        from src.cache import LRUCache
        
        cache = LRUCache(max_size=10)
        
        cache.set("key", "value")
        
        cache.get("key")  # hit
        cache.get("key")  # hit
        cache.get("nonexistent")  # miss
        
        stats = cache.get_stats()
        assert stats.hits == 2
        assert stats.misses == 1
        assert stats.hit_rate == 2/3

