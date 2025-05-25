"""Metrics collection and monitoring system."""

import time
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum

try:
    from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest
    from prometheus_client import CollectorRegistry
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Create dummy classes when prometheus is not available
    class CollectorRegistry:
        pass

from config.settings import Settings


class MetricType(str, Enum):
    """Metric type enumeration."""
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"
    INFO = "info"


@dataclass
class MetricData:
    """Individual metric data point."""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metric_type: MetricType = MetricType.COUNTER


class InMemoryMetricsStore:
    """In-memory metrics storage for when Prometheus is not available."""
    
    def __init__(self, max_points: int = 10000):
        self.max_points = max_points
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
    
    def record_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Record a counter metric."""
        key = self._make_key(name, labels or {})
        self.counters[key] += value
        self.metrics[key].append(MetricData(
            name=name,
            value=self.counters[key],
            labels=labels or {},
            metric_type=MetricType.COUNTER
        ))
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a histogram metric."""
        key = self._make_key(name, labels or {})
        self.metrics[key].append(MetricData(
            name=name,
            value=value,
            labels=labels or {},
            metric_type=MetricType.HISTOGRAM
        ))
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        key = self._make_key(name, labels or {})
        self.gauges[key] = value
        self.metrics[key].append(MetricData(
            name=name,
            value=value,
            labels=labels or {},
            metric_type=MetricType.GAUGE
        ))
    
    def get_metrics(self, name: Optional[str] = None) -> Dict[str, List[MetricData]]:
        """Get stored metrics."""
        if name:
            return {k: list(v) for k, v in self.metrics.items() if k.startswith(name)}
        return {k: list(v) for k, v in self.metrics.items()}
    
    def get_current_values(self) -> Dict[str, float]:
        """Get current values for all metrics."""
        result = {}
        result.update(self.counters)
        result.update(self.gauges)
        return result
    
    def _make_key(self, name: str, labels: Dict[str, str]) -> str:
        """Create a unique key for metric with labels."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


class PrometheusMetricsCollector:
    """Prometheus-based metrics collector."""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        if not PROMETHEUS_AVAILABLE:
            raise ImportError("Prometheus client not available")
        
        self.registry = registry or CollectorRegistry()
        self._metrics = {}
        self._initialize_metrics()
    
    def _initialize_metrics(self):
        """Initialize Prometheus metrics."""
        # HTTP Request metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # Database metrics
        self.database_connections_active = Gauge(
            'database_connections_active',
            'Active database connections',
            registry=self.registry
        )
        
        self.database_query_duration = Histogram(
            'database_query_duration_seconds',
            'Database query duration in seconds',
            ['operation'],
            registry=self.registry
        )
        
        # Mail processing metrics
        self.mail_messages_processed = Counter(
            'mail_messages_processed_total',
            'Total processed mail messages',
            ['account_id', 'operation'],
            registry=self.registry
        )
        
        self.mail_api_calls = Counter(
            'mail_api_calls_total',
            'Total Graph API calls',
            ['endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.mail_processing_duration = Histogram(
            'mail_processing_duration_seconds',
            'Mail processing duration in seconds',
            ['operation'],
            registry=self.registry
        )
        
        # Authentication metrics
        self.auth_attempts = Counter(
            'auth_attempts_total',
            'Total authentication attempts',
            ['flow_type', 'status'],
            registry=self.registry
        )
        
        self.token_refresh_attempts = Counter(
            'token_refresh_attempts_total',
            'Total token refresh attempts',
            ['status'],
            registry=self.registry
        )
        
        # System metrics
        self.background_tasks_active = Gauge(
            'background_tasks_active',
            'Active background tasks',
            ['task_type'],
            registry=self.registry
        )
        
        self.webhook_subscriptions_active = Gauge(
            'webhook_subscriptions_active',
            'Active webhook subscriptions',
            registry=self.registry
        )
        
        # Error metrics
        self.errors_total = Counter(
            'errors_total',
            'Total errors',
            ['error_type', 'component'],
            registry=self.registry
        )
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        self.http_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_database_query(self, operation: str, duration: float):
        """Record database query metrics."""
        self.database_query_duration.labels(operation=operation).observe(duration)
    
    def set_active_connections(self, count: int):
        """Set active database connections."""
        self.database_connections_active.set(count)
    
    def record_mail_processed(self, account_id: str, operation: str, count: int = 1):
        """Record mail processing metrics."""
        self.mail_messages_processed.labels(
            account_id=account_id,
            operation=operation
        ).inc(count)
    
    def record_mail_api_call(self, endpoint: str, status_code: int):
        """Record Graph API call metrics."""
        self.mail_api_calls.labels(
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
    
    def record_mail_processing_duration(self, operation: str, duration: float):
        """Record mail processing duration."""
        self.mail_processing_duration.labels(operation=operation).observe(duration)
    
    def record_auth_attempt(self, flow_type: str, status: str):
        """Record authentication attempt."""
        self.auth_attempts.labels(flow_type=flow_type, status=status).inc()
    
    def record_token_refresh(self, status: str):
        """Record token refresh attempt."""
        self.token_refresh_attempts.labels(status=status).inc()
    
    def set_background_tasks(self, task_type: str, count: int):
        """Set active background tasks count."""
        self.background_tasks_active.labels(task_type=task_type).set(count)
    
    def set_webhook_subscriptions(self, count: int):
        """Set active webhook subscriptions count."""
        self.webhook_subscriptions_active.set(count)
    
    def record_error(self, error_type: str, component: str):
        """Record error occurrence."""
        self.errors_total.labels(error_type=error_type, component=component).inc()
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry).decode('utf-8')


class MetricsCollector:
    """Main metrics collector that adapts to available backends."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.enabled = settings.METRICS_ENABLED
        
        if self.enabled and PROMETHEUS_AVAILABLE:
            try:
                self.backend = PrometheusMetricsCollector()
                self.backend_type = "prometheus"
            except ImportError:
                self.backend = InMemoryMetricsStore()
                self.backend_type = "memory"
        else:
            self.backend = InMemoryMetricsStore()
            self.backend_type = "memory"
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        if not self.enabled:
            return
        
        if self.backend_type == "prometheus":
            self.backend.record_http_request(method, endpoint, status_code, duration)
        else:
            self.backend.record_counter(
                "http_requests_total",
                labels={"method": method, "endpoint": endpoint, "status_code": str(status_code)}
            )
            self.backend.record_histogram(
                "http_request_duration_seconds",
                duration,
                labels={"method": method, "endpoint": endpoint}
            )
    
    def record_database_query(self, operation: str, duration: float):
        """Record database query metrics."""
        if not self.enabled:
            return
        
        if self.backend_type == "prometheus":
            self.backend.record_database_query(operation, duration)
        else:
            self.backend.record_histogram(
                "database_query_duration_seconds",
                duration,
                labels={"operation": operation}
            )
    
    def set_active_connections(self, count: int):
        """Set active database connections."""
        if not self.enabled:
            return
        
        if self.backend_type == "prometheus":
            self.backend.set_active_connections(count)
        else:
            self.backend.set_gauge("database_connections_active", count)
    
    def record_mail_processed(self, account_id: str, operation: str, count: int = 1):
        """Record mail processing metrics."""
        if not self.enabled:
            return
        
        if self.backend_type == "prometheus":
            self.backend.record_mail_processed(account_id, operation, count)
        else:
            self.backend.record_counter(
                "mail_messages_processed_total",
                count,
                labels={"account_id": account_id, "operation": operation}
            )
    
    def record_mail_api_call(self, endpoint: str, status_code: int):
        """Record Graph API call metrics."""
        if not self.enabled:
            return
        
        if self.backend_type == "prometheus":
            self.backend.record_mail_api_call(endpoint, status_code)
        else:
            self.backend.record_counter(
                "mail_api_calls_total",
                labels={"endpoint": endpoint, "status_code": str(status_code)}
            )
    
    def record_mail_processing_duration(self, operation: str, duration: float):
        """Record mail processing duration."""
        if not self.enabled:
            return
        
        if self.backend_type == "prometheus":
            self.backend.record_mail_processing_duration(operation, duration)
        else:
            self.backend.record_histogram(
                "mail_processing_duration_seconds",
                duration,
                labels={"operation": operation}
            )
    
    def record_auth_attempt(self, flow_type: str, status: str):
        """Record authentication attempt."""
        if not self.enabled:
            return
        
        if self.backend_type == "prometheus":
            self.backend.record_auth_attempt(flow_type, status)
        else:
            self.backend.record_counter(
                "auth_attempts_total",
                labels={"flow_type": flow_type, "status": status}
            )
    
    def record_token_refresh(self, status: str):
        """Record token refresh attempt."""
        if not self.enabled:
            return
        
        if self.backend_type == "prometheus":
            self.backend.record_token_refresh(status)
        else:
            self.backend.record_counter(
                "token_refresh_attempts_total",
                labels={"status": status}
            )
    
    def set_background_tasks(self, task_type: str, count: int):
        """Set active background tasks count."""
        if not self.enabled:
            return
        
        if self.backend_type == "prometheus":
            self.backend.set_background_tasks(task_type, count)
        else:
            self.backend.set_gauge(
                "background_tasks_active",
                count,
                labels={"task_type": task_type}
            )
    
    def set_webhook_subscriptions(self, count: int):
        """Set active webhook subscriptions count."""
        if not self.enabled:
            return
        
        if self.backend_type == "prometheus":
            self.backend.set_webhook_subscriptions(count)
        else:
            self.backend.set_gauge("webhook_subscriptions_active", count)
    
    def record_error(self, error_type: str, component: str):
        """Record error occurrence."""
        if not self.enabled:
            return
        
        if self.backend_type == "prometheus":
            self.backend.record_error(error_type, component)
        else:
            self.backend.record_counter(
                "errors_total",
                labels={"error_type": error_type, "component": component}
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics in appropriate format."""
        if not self.enabled:
            return {"enabled": False, "message": "Metrics collection disabled"}
        
        if self.backend_type == "prometheus":
            return {
                "backend": "prometheus",
                "format": "prometheus",
                "metrics": self.backend.get_metrics()
            }
        else:
            return {
                "backend": "memory",
                "format": "json",
                "metrics": self.backend.get_current_values(),
                "detailed_metrics": self.backend.get_metrics()
            }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        if not self.enabled:
            return {"enabled": False}
        
        if self.backend_type == "memory":
            current_values = self.backend.get_current_values()
            return {
                "enabled": True,
                "backend": self.backend_type,
                "total_metrics": len(current_values),
                "sample_metrics": dict(list(current_values.items())[:10])
            }
        else:
            return {
                "enabled": True,
                "backend": self.backend_type,
                "prometheus_available": True
            }


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector(settings: Optional[Settings] = None) -> Optional[MetricsCollector]:
    """Get or create global metrics collector instance."""
    global _metrics_collector
    
    if _metrics_collector is None and settings:
        _metrics_collector = MetricsCollector(settings)
    
    return _metrics_collector


def reset_metrics_collector():
    """Reset global metrics collector instance."""
    global _metrics_collector
    _metrics_collector = None


class MetricsMiddleware:
    """Middleware for automatic metrics collection."""
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
    
    async def __call__(self, request, call_next):
        """Process request and collect metrics."""
        start_time = time.time()
        
        # Extract endpoint pattern (remove query params and IDs)
        endpoint = self._normalize_endpoint(request.url.path)
        method = request.method
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Record successful request
            self.collector.record_http_request(
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
                duration=duration
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Record failed request
            self.collector.record_http_request(
                method=method,
                endpoint=endpoint,
                status_code=500,
                duration=duration
            )
            
            # Record error
            self.collector.record_error(
                error_type=type(e).__name__,
                component="api"
            )
            
            raise
    
    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for metrics."""
        # Remove UUIDs and other IDs
        import re
        
        # Replace UUIDs
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}', path)
        
        # Replace other numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)
        
        return path


def create_metrics_middleware(settings: Settings) -> MetricsMiddleware:
    """Create metrics middleware."""
    collector = get_metrics_collector(settings)
    if collector:
        return MetricsMiddleware(collector)
    else:
        # Return a no-op middleware if collector is not available
        class NoOpMiddleware:
            async def __call__(self, request, call_next):
                return await call_next(request)
        return NoOpMiddleware()
