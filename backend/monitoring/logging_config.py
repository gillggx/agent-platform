"""
Logging Configuration

Structured logging with JSON output for log aggregation
"""

import logging
import logging.config
import json
from datetime import datetime
from typing import Dict, Any, Optional
import sys


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging
    
    Formats logs as JSON for easy parsing and aggregation
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON
        
        Args:
            record: Log record
            
        Returns:
            JSON formatted log
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process': record.process,
            'thread': record.thread,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info),
            }
        
        # Add custom fields
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


class StructuredLogger:
    """
    Structured logging wrapper
    
    Provides convenient methods for structured logging
    """
    
    def __init__(self, name: str):
        """
        Initialize structured logger
        
        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)
    
    def _log(
        self,
        level: int,
        message: str,
        **extra_fields
    ) -> None:
        """
        Log with extra fields
        
        Args:
            level: Log level
            message: Log message
            **extra_fields: Extra fields to include
        """
        record = self.logger.makeRecord(
            self.logger.name,
            level,
            '(unknown file)',
            0,
            message,
            (),
            None
        )
        
        if extra_fields:
            record.extra_fields = extra_fields
        
        self.logger.handle(record)
    
    def debug(self, message: str, **extra_fields) -> None:
        """Log debug message"""
        self._log(logging.DEBUG, message, **extra_fields)
    
    def info(self, message: str, **extra_fields) -> None:
        """Log info message"""
        self._log(logging.INFO, message, **extra_fields)
    
    def warning(self, message: str, **extra_fields) -> None:
        """Log warning message"""
        self._log(logging.WARNING, message, **extra_fields)
    
    def error(self, message: str, **extra_fields) -> None:
        """Log error message"""
        self._log(logging.ERROR, message, **extra_fields)
    
    def critical(self, message: str, **extra_fields) -> None:
        """Log critical message"""
        self._log(logging.CRITICAL, message, **extra_fields)


def configure_logging(
    level: str = 'INFO',
    json_output: bool = True,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure application logging
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: Use JSON formatter
        log_file: Optional log file path
    """
    
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
            'json': {
                '()': JSONFormatter,
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': level,
                'formatter': 'json' if json_output else 'standard',
                'stream': 'ext://sys.stdout',
            },
        },
        'loggers': {
            '': {
                'level': level,
                'handlers': ['console'],
            },
        },
    }
    
    # Add file handler if specified
    if log_file:
        config['handlers']['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': level,
            'formatter': 'json' if json_output else 'standard',
            'filename': log_file,
            'maxBytes': 10485760,  # 10 MB
            'backupCount': 10,
        }
        config['loggers']['']['handlers'].append('file')
    
    logging.config.dictConfig(config)


class LogContext:
    """
    Context manager for adding context to logs
    
    Usage:
        with LogContext(workflow_id='123', user='admin'):
            logger.info('Processing workflow')  # Logs will include context
    """
    
    def __init__(self, **context_fields):
        """Initialize context"""
        self.context_fields = context_fields
    
    def __enter__(self):
        """Enter context"""
        # Store in thread-local storage
        import threading
        if not hasattr(threading.current_thread(), '_log_context'):
            threading.current_thread()._log_context = {}
        threading.current_thread()._log_context.update(self.context_fields)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context"""
        import threading
        if hasattr(threading.current_thread(), '_log_context'):
            for key in self.context_fields:
                threading.current_thread()._log_context.pop(key, None)


# Configure logging on module import
configure_logging()

# Create structured logger
structured_logger = StructuredLogger(__name__)
