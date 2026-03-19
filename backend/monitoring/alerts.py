"""
Alerting Rules and Configuration

Prometheus alert rules for system monitoring
"""

from typing import Dict, List, Any
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class AlertRulesConfig:
    """
    Prometheus alert rules configuration
    """
    
    @staticmethod
    def get_alert_rules() -> str:
        """
        Get Prometheus alert rules in YAML format
        
        Returns:
            Alert rules YAML
        """
        return """
groups:
  - name: agent_platform_alerts
    interval: 30s
    rules:
      # Workflow errors
      - alert: WorkflowExecutionErrors
        expr: rate(workflow_operations_total{status="error"}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High workflow error rate"
          description: "Error rate is {{ $value }} errors/sec"
      
      # Slow workflow execution
      - alert: SlowWorkflowExecution
        expr: histogram_quantile(0.95, workflow_execution_duration_seconds) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow workflow execution"
          description: "P95 execution time is {{ $value }} seconds"
      
      # Database errors
      - alert: HighDatabaseErrorRate
        expr: rate(database_operations_total{table!=""}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High database error rate"
          description: "Error rate is {{ $value }} ops/sec"
      
      # Database connection pool exhaustion
      - alert: DatabaseConnectionPoolExhausted
        expr: active_connections / pool_connections > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool near exhaustion"
          description: "{{ $value | humanizePercentage }} of connections in use"
      
      # Cache hit rate too low
      - alert: LowCacheHitRate
        expr: cache_hit_rate < 30
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low cache hit rate"
          description: "Cache hit rate is {{ $value }}%"
      
      # HTTP error rate too high
      - alert: HighHTTPErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High HTTP error rate"
          description: "5xx error rate is {{ $value | humanizePercentage }}"
      
      # Slow HTTP requests
      - alert: SlowHTTPRequests
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow HTTP requests detected"
          description: "P95 request latency is {{ $value }} seconds"
      
      # High memory usage
      - alert: HighMemoryUsage
        expr: process_resident_memory_bytes / (1024 * 1024) > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value | humanize }}MB"
      
      # Queue size too large
      - alert: LargeQueueSize
        expr: queue_size > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Large job queue detected"
          description: "Queue size is {{ $value }}"
      
      # Too many validation errors
      - alert: HighValidationErrorRate
        expr: rate(validation_errors_total[5m]) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High validation error rate"
          description: "Validation error rate is {{ $value }} errors/sec"
"""
    
    @staticmethod
    def get_alert_rules_json() -> List[Dict[str, Any]]:
        """
        Get alert rules as JSON/dict
        
        Returns:
            List of alert rule dicts
        """
        return [
            {
                'name': 'WorkflowExecutionErrors',
                'expr': 'rate(workflow_operations_total{status="error"}[5m]) > 0.1',
                'duration': '5m',
                'severity': 'critical',
                'description': 'Error rate is too high',
            },
            {
                'name': 'SlowWorkflowExecution',
                'expr': 'histogram_quantile(0.95, workflow_execution_duration_seconds) > 10',
                'duration': '5m',
                'severity': 'warning',
                'description': 'P95 execution time exceeds 10 seconds',
            },
            {
                'name': 'HighDatabaseErrorRate',
                'expr': 'rate(database_operations_total{table!=""}[5m]) > 0.05',
                'duration': '5m',
                'severity': 'critical',
                'description': 'Database error rate is high',
            },
            {
                'name': 'DatabaseConnectionPoolExhausted',
                'expr': 'active_connections / pool_connections > 0.9',
                'duration': '5m',
                'severity': 'critical',
                'description': 'Connection pool usage above 90%',
            },
            {
                'name': 'LowCacheHitRate',
                'expr': 'cache_hit_rate < 30',
                'duration': '10m',
                'severity': 'warning',
                'description': 'Cache hit rate below 30%',
            },
            {
                'name': 'HighHTTPErrorRate',
                'expr': 'rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05',
                'duration': '5m',
                'severity': 'warning',
                'description': '5xx error rate above 5%',
            },
            {
                'name': 'SlowHTTPRequests',
                'expr': 'histogram_quantile(0.95, http_request_duration_seconds) > 5',
                'duration': '5m',
                'severity': 'warning',
                'description': 'P95 request latency above 5 seconds',
            },
            {
                'name': 'HighMemoryUsage',
                'expr': 'process_resident_memory_bytes / (1024 * 1024) > 1000',
                'duration': '5m',
                'severity': 'warning',
                'description': 'Memory usage above 1GB',
            },
            {
                'name': 'LargeQueueSize',
                'expr': 'queue_size > 1000',
                'duration': '5m',
                'severity': 'warning',
                'description': 'Job queue size exceeds 1000',
            },
            {
                'name': 'HighValidationErrorRate',
                'expr': 'rate(validation_errors_total[5m]) > 1',
                'duration': '5m',
                'severity': 'warning',
                'description': 'Validation error rate above 1/sec',
            },
        ]


class GrafanaDashboardConfig:
    """
    Grafana dashboard configuration
    """
    
    @staticmethod
    def get_dashboard_json() -> Dict[str, Any]:
        """
        Get Grafana dashboard configuration
        
        Returns:
            Dashboard JSON config
        """
        return {
            'dashboard': {
                'title': 'Agent Platform Monitoring',
                'panels': [
                    {
                        'title': 'Workflow Operations',
                        'targets': [
                            {
                                'expr': 'rate(workflow_operations_total[5m])',
                                'legendFormat': '{{ operation }}/{{ status }}',
                            }
                        ],
                    },
                    {
                        'title': 'Workflow Execution Duration',
                        'targets': [
                            {
                                'expr': 'histogram_quantile(0.95, workflow_execution_duration_seconds)',
                                'legendFormat': 'P95',
                            }
                        ],
                    },
                    {
                        'title': 'Database Operations',
                        'targets': [
                            {
                                'expr': 'rate(database_operations_total[5m])',
                                'legendFormat': '{{ operation }}/{{ table }}',
                            }
                        ],
                    },
                    {
                        'title': 'Active Connections',
                        'targets': [
                            {
                                'expr': 'active_connections',
                                'legendFormat': 'Active',
                            },
                            {
                                'expr': 'pool_connections',
                                'legendFormat': 'Total Pool',
                            }
                        ],
                    },
                    {
                        'title': 'Cache Hit Rate',
                        'targets': [
                            {
                                'expr': 'cache_hit_rate',
                                'legendFormat': 'Hit Rate %',
                            }
                        ],
                    },
                    {
                        'title': 'HTTP Requests',
                        'targets': [
                            {
                                'expr': 'rate(http_requests_total[5m])',
                                'legendFormat': '{{ method }}/{{ status }}',
                            }
                        ],
                    },
                    {
                        'title': 'HTTP Request Duration',
                        'targets': [
                            {
                                'expr': 'histogram_quantile(0.95, http_request_duration_seconds)',
                                'legendFormat': 'P95',
                            }
                        ],
                    },
                    {
                        'title': 'Error Rate',
                        'targets': [
                            {
                                'expr': 'rate(errors_total[5m])',
                                'legendFormat': '{{ error_type }}/{{ module }}',
                            }
                        ],
                    },
                ],
            }
        }


class HealthCheckRules:
    """
    Health check rules
    """
    
    @staticmethod
    def get_health_checks() -> Dict[str, Dict[str, Any]]:
        """
        Get health check configuration
        
        Returns:
            Health check rules
        """
        return {
            'database': {
                'name': 'Database Connectivity',
                'check': 'SELECT 1',
                'timeout': 5,
                'interval': 30,
            },
            'cache': {
                'name': 'Cache Connectivity',
                'check': 'PING',
                'timeout': 5,
                'interval': 30,
            },
            'api': {
                'name': 'API Health',
                'check': 'GET /api/health',
                'timeout': 10,
                'interval': 30,
            },
            'metrics': {
                'name': 'Metrics Endpoint',
                'check': 'GET /metrics',
                'timeout': 5,
                'interval': 30,
            },
        }
