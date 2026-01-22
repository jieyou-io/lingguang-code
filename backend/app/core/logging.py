"""
结构化日志模块

使用 structlog 实现结构化日志
"""
import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict

from app.core.config import settings


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """添加应用上下文到日志"""
    event_dict["service"] = "anycode-backend"
    event_dict["version"] = settings.APP_VERSION
    return event_dict


def censor_sensitive_data(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """过滤敏感数据"""
    sensitive_keys = ["password", "api_key", "apiKey", "prompt", "token"]

    for key in sensitive_keys:
        if key in event_dict:
            event_dict[key] = "***REDACTED***"

    return event_dict


def setup_logging():
    """配置结构化日志"""

    # 配置 structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            add_app_context,
            censor_sensitive_data,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.LOG_JSON else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 配置标准 logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )
