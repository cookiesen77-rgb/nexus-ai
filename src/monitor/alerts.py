"""
告警系统 - 监控告警
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class AlertSeverity(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警状态"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class Alert:
    """告警"""
    id: str
    name: str
    message: str
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.ACTIVE
    
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    
    count: int = 1  # 重复次数
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "message": self.message,
            "severity": self.severity.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "labels": self.labels,
            "count": self.count,
        }


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    severity: AlertSeverity = AlertSeverity.WARNING
    message_template: str = "{name} triggered"
    cooldown_seconds: int = 300  # 冷却时间，避免重复告警
    labels: Dict[str, str] = field(default_factory=dict)
    
    # 状态
    last_triggered: Optional[datetime] = None
    enabled: bool = True


class AlertManager:
    """
    告警管理器
    
    管理告警规则和告警状态
    """
    
    def __init__(self):
        """初始化告警管理器"""
        self._rules: Dict[str, AlertRule] = {}
        self._alerts: Dict[str, Alert] = {}
        self._handlers: List[Callable[[Alert], Awaitable[None]]] = []
        
        # 注册默认规则
        self._register_default_rules()
    
    def _register_default_rules(self):
        """注册默认告警规则"""
        # 高错误率
        self.add_rule(AlertRule(
            name="high_error_rate",
            condition=lambda m: m.get("error_rate", 0) > 0.1,
            severity=AlertSeverity.ERROR,
            message_template="Error rate is {error_rate:.1%}, above threshold 10%",
        ))
        
        # 高延迟
        self.add_rule(AlertRule(
            name="high_latency",
            condition=lambda m: m.get("avg_latency_ms", 0) > 5000,
            severity=AlertSeverity.WARNING,
            message_template="Average latency is {avg_latency_ms:.0f}ms, above threshold 5000ms",
        ))
        
        # 高Token消耗
        self.add_rule(AlertRule(
            name="high_token_usage",
            condition=lambda m: m.get("tokens_per_hour", 0) > 100000,
            severity=AlertSeverity.WARNING,
            message_template="Token usage is {tokens_per_hour} tokens/hour, above threshold 100k",
        ))
        
        # 成本告警
        self.add_rule(AlertRule(
            name="high_cost",
            condition=lambda m: m.get("cost_usd_today", 0) > 10,
            severity=AlertSeverity.WARNING,
            message_template="Today's cost is ${cost_usd_today:.2f}, above threshold $10",
        ))
    
    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self._rules[rule.name] = rule
    
    def remove_rule(self, name: str):
        """移除告警规则"""
        self._rules.pop(name, None)
    
    def add_handler(self, handler: Callable[[Alert], Awaitable[None]]):
        """添加告警处理器"""
        self._handlers.append(handler)
    
    async def check_rules(self, metrics: Dict[str, Any]) -> List[Alert]:
        """
        检查所有规则
        
        Args:
            metrics: 指标数据
            
        Returns:
            List[Alert]: 触发的告警
        """
        triggered = []
        
        for name, rule in self._rules.items():
            if not rule.enabled:
                continue
            
            # 检查冷却
            if rule.last_triggered:
                cooldown_until = rule.last_triggered + timedelta(seconds=rule.cooldown_seconds)
                if datetime.now() < cooldown_until:
                    continue
            
            try:
                if rule.condition(metrics):
                    alert = await self._create_alert(rule, metrics)
                    triggered.append(alert)
                    rule.last_triggered = datetime.now()
            except Exception as e:
                print(f"Error checking rule {name}: {e}")
        
        return triggered
    
    async def _create_alert(self, rule: AlertRule, metrics: Dict[str, Any]) -> Alert:
        """创建告警"""
        import uuid
        
        # 检查是否已存在同名活跃告警
        existing = None
        for alert in self._alerts.values():
            if alert.name == rule.name and alert.status == AlertStatus.ACTIVE:
                existing = alert
                break
        
        if existing:
            existing.count += 1
            return existing
        
        # 格式化消息
        try:
            message = rule.message_template.format(**metrics)
        except:
            message = rule.message_template
        
        alert = Alert(
            id=str(uuid.uuid4())[:8],
            name=rule.name,
            message=message,
            severity=rule.severity,
            labels=rule.labels.copy()
        )
        
        self._alerts[alert.id] = alert
        
        # 调用处理器
        for handler in self._handlers:
            try:
                await handler(alert)
            except Exception as e:
                print(f"Error in alert handler: {e}")
        
        return alert
    
    def acknowledge(self, alert_id: str) -> bool:
        """确认告警"""
        alert = self._alerts.get(alert_id)
        if alert and alert.status == AlertStatus.ACTIVE:
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.now()
            return True
        return False
    
    def resolve(self, alert_id: str) -> bool:
        """解决告警"""
        alert = self._alerts.get(alert_id)
        if alert and alert.status != AlertStatus.RESOLVED:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now()
            return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return [
            a for a in self._alerts.values()
            if a.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]
        ]
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """获取告警"""
        return self._alerts.get(alert_id)
    
    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        """按级别获取告警"""
        return [a for a in self._alerts.values() if a.severity == severity]
    
    def clear_resolved(self, older_than_hours: int = 24):
        """清理已解决的告警"""
        cutoff = datetime.now() - timedelta(hours=older_than_hours)
        to_remove = [
            aid for aid, a in self._alerts.items()
            if a.status == AlertStatus.RESOLVED and a.resolved_at and a.resolved_at < cutoff
        ]
        for aid in to_remove:
            del self._alerts[aid]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取告警统计"""
        active = len([a for a in self._alerts.values() if a.status == AlertStatus.ACTIVE])
        acknowledged = len([a for a in self._alerts.values() if a.status == AlertStatus.ACKNOWLEDGED])
        resolved = len([a for a in self._alerts.values() if a.status == AlertStatus.RESOLVED])
        
        by_severity = {}
        for s in AlertSeverity:
            by_severity[s.value] = len([a for a in self._alerts.values() if a.severity == s])
        
        return {
            "total": len(self._alerts),
            "active": active,
            "acknowledged": acknowledged,
            "resolved": resolved,
            "by_severity": by_severity,
            "rules_count": len(self._rules),
        }


# 全局告警管理器
_default_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """获取全局告警管理器"""
    global _default_manager
    if _default_manager is None:
        _default_manager = AlertManager()
    return _default_manager


async def check_alerts(metrics: Dict[str, Any]) -> List[Alert]:
    """快捷函数: 检查告警"""
    return await get_alert_manager().check_rules(metrics)

