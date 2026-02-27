# config/monitor.py
from ..config import settings

MONITOR = {
    # Webhooks
    "WEBHOOK_OPS": settings.WEBHOOK_OPS,
    "WEBHOOK_ECON": settings.WEBHOOK_ECON or settings.DEV_WEBHOOK_URL,  # Falls back to DEV_WEBHOOK_URL

    # Thresholds
    "CHECK_INTERVAL": 60,

    "QUEUE_WARN": 20,
    "FAIL_WARN": 1,

    "WORKER_TIMEOUT": 120,
}

# Health check thresholds
HEALTH_CHECKS = {
    "redis_ping_timeout": 5,
    "db_connection_timeout": 5,
    "queue_size_critical": 50,
    "memory_usage_warning": 80,  # percentage
    "cpu_usage_warning": 90,     # percentage
}

# Alert colors (Discord embed colors)
ALERT_COLORS = {
    "red": 15158332,      # Error/Critical
    "orange": 15105370,   # Warning
    "yellow": 16776960,   # Info
    "green": 3066993,     # Success
    "blue": 3447003,      # Information
}
