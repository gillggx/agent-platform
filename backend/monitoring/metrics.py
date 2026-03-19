"""
Prometheus Metrics Integration

Comprehensive metrics collection for monitoring system health
"""

from prometheus_client import Counter, Histogram, Gauge, Summary, generate_latest
from prometheus_client import CollectorRegistry, REGISTRY
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# Define metrics
workflow_operations = Counter(
    'workflow_operations_total',
    'Total workflow operations',
    ['operation', 'status'],
    registry=REGISTRY
)

workflow_execution_duration = Histogram(
    'workflow_execution_duration_seconds',
    'Workflow execution duration in seconds',
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
    registry=REGISTRY
)

database_operations = Counter(
    'database_operations_total',
    'Total database operations',
    ['operation', 'table'],
    registry=REGISTRY
)

database_operation_duration = Histogram(
    'database_operation_duration_seconds',
    'Database operation duration in seconds',
    buckets=(0.001, 0.01, 0.1, 0.5, 1.0),
    registry=REGISTRY
)

cache_operations = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'status'],
    registry=REGISTRY
)

cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Cache hit rate percentage',
    registry=REGISTRY
)

http_requests = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=REGISTRY
)

http_request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
    registry=REGISTRY
)

active_connections = Gauge(
    'active_connections',
    'Number of active database connections',
    registry=REGISTRY
)

pool_connections = Gauge(
    'pool_connections',
    'Total connections in pool',
    registry=REGISTRY
)

errors_total = Counter(
    'errors_total',
    'Total errors',
    ['error_type', 'module'],
    registry=REGISTRY
)

queue_size = Gauge(
    'queue_size',
    'Message queue size',
    registry=REGISTRY
)

validation_errors = Counter(
    'validation_errors_total',
    'Total validation errors',
    ['error_type'],
    registry=REGISTRY
)


class MetricsCollector:
    """
    Main metrics collector
    
    Manages metrics collection and reporting
    """
    
    @staticmethod
    def record_workflow_operation(operation: str, success: bool) -> None:
        """
        Record workflow operation
        
        Args:
            operation: Operation name (create, update, delete, run)
            success: Whether operation succeeded
        """
        status = 'success' if success else 'error'
        workflow_operations.labels(operation=operation, status=status).inc()
        logger.debug(f"Recorded workflow operation: {operation} - {status}")
    
    @staticmethod
    def record_workflow_execution(duration: float) -> None:
        """
        Record workflow execution
        
        Args:
            duration: Execution duration in seconds
        """
        workflow_execution_duration.observe(duration)
    
    @staticmethod
    def record_database_operation(operation: str, table: str, duration: float, success: bool) -> None:
        """
        Record database operation
        
        Args:
            operation: Operation type (select, insert, update, delete)
            table: Table name
            duration: Operation duration in seconds
            success: Whether operation succeeded
        """
        database_operations.labels(operation=operation, table=table).inc()
        database_operation_duration.observe(duration)
    
    @staticmethod
    def record_cache_hit(hit: bool, key: str = '') -> None:
        """
        Record cache operation
        
        Args:
            hit: Whether it was a cache hit
            key: Cache key
        """
        status = 'hit' if hit else 'miss'
        cache_operations.labels(operation='lookup', status=status).inc()
    
    @staticmethod
    def update_cache_hit_rate(hit_rate: float) -> None:
        """
        Update cache hit rate gauge
        
        Args:
            hit_rate: Hit rate as percentage (0-100)
        """
        cache_hit_rate.set(hit_rate)
    
    @staticmethod
    def record_http_request(method: str, endpoint: str, status_code: int, duration: float) -> None:
        """
        Record HTTP request
        
        Args:
            method: HTTP method
            endpoint: Request endpoint
            status_code: Response status code
            duration: Request duration in seconds
        """
        http_requests.labels(
            method=method,
            endpoint=endpoint,
            status=status_code
        ).inc()
        http_request_duration.observe(duration)
    
    @staticmethod
    def update_active_connections(count: int) -> None:
        """
        Update active connections gauge
        
        Args:
            count: Number of active connections
        """
        active_connections.set(count)
    
    @staticmethod
    def update_pool_connections(total: int) -> None:
        """
        Update pool connections gauge
        
        Args:
            total: Total connections in pool
        """
        pool_connections.set(total)
    
    @staticmethod
    def record_error(error_type: str, module: str) -> None:
        """
        Record error
        
        Args:
            error_type: Type of error
            module: Module where error occurred
        """
        errors_total.labels(error_type=error_type, module=module).inc()
    
    @staticmethod
    def update_queue_size(size: int) -> None:
        """
        Update queue size
        
        Args:
            size: Queue size
        """
        queue_size.set(size)
    
    @staticmethod
    def record_validation_error(error_type: str) -> None:
        """
        Record validation error
        
        Args:
            error_type: Validation error type
        """
        validation_errors.labels(error_type=error_type).inc()
    
    @staticmethod
    def get_metrics() -> str:
        """
        Get all metrics in Prometheus format
        
        Returns:
            Metrics in text format
        """
        return generate_latest(REGISTRY).decode('utf-8')


def track_metrics(operation: str, table: str = ''):
    """
    Decorator to track operation metrics
    
    Usage:
        @track_metrics('select', 'workflows')
        async def get_workflow(session, workflow_id):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = datetime.now()
            
            try:
                result = await func(*args, **kwargs)
                duration = (datetime.now() - start).total_seconds()
                
                MetricsCollector.record_database_operation(
                    operation=operation,
                    table=table,
                    duration=duration,
                    success=True
                )
                
                return result
            except Exception as e:
                duration = (datetime.now() - start).total_seconds()
                
                MetricsCollector.record_database_operation(
                    operation=operation,
                    table=table,
                    duration=duration,
                    success=False
                )
                
                MetricsCollector.record_error(
                    error_type=type(e).__name__,
                    module=func.__module__
                )
                
                raise
        
        return wrapper
    return decorator


def track_http(method: str, endpoint: str):
    """
    Decorator to track HTTP requests
    
    Usage:
        @track_http('POST', '/api/workflows')
        async def create_workflow(request):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = datetime.now()
            status_code = 500  # Default to error
            
            try:
                result = await func(*args, **kwargs)
                status_code = getattr(result, 'status_code', 200)
                return result
            except Exception as e:
                raise
            finally:
                duration = (datetime.now() - start).total_seconds()
                MetricsCollector.record_http_request(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                    duration=duration
                )
        
        return wrapper
    return decorator


class MetricsEndpoint:
    """
    HTTP endpoint for metrics
    """
    
    @staticmethod
    def get_metrics() -> str:
        """
        Get metrics in Prometheus format
        
        Returns:
            Metrics text
        """
        return MetricsCollector.get_metrics()


# Global metrics instance
_metrics = MetricsCollector()
