# Bot Logger - Comprehensive Logging System

## Overview

BotLogger provides a unified, centralized logging system that integrates:

- **Changelog Manager**: Track system changes and events
- **System Monitor**: Monitor restarts, uptime, and resources
- **Error Logger**: Comprehensive error tracking with context
- **Discord Alerts**: Automatic notifications for critical issues

## Features

### Integrated Logging
- **Single entry point** for all bot logging
- **Automatic Discord alerts** for critical issues
- **Persistent storage** in JSON format
- **Error statistics** and trending
- **Health summaries** and diagnostics

### Error Categories
- **Debug**: Diagnostic information (🔍)
- **Info**: Informational messages (ℹ️)
- **Warning**: Warning conditions (⚠️)
- **Error**: Error conditions (❌)
- **Critical**: Critical failures (🚨)

## Discord Commands

### /errors
View recent system errors

```
/errors [context] [limit]
- context: Filter by error context (optional)
- limit: Number of errors to show (1-50, default 10)
```

**Shows:**
- Error type and message
- Timestamp and context
- User ID (if applicable)
- Error count

### /error_stats
View error statistics

```
Shows:
- Error contexts and counts
- Most common errors
- Error frequency trends
```

### /system_health
View overall system health

```
Shows:
- Total errors and recent errors
- Memory and CPU usage
- Top error types
- Overall health status
```

## Usage Examples

### Log Major Events

```python
from services.bot_logger import log_event

log_event(
    event_type='feature_deployment',
    description='New feature X deployed',
    user_id=admin_id,
    severity='high',
    send_alert=True
)
```

### Log Pack Operations

```python
from services.bot_logger import log_pack

# Pack created
log_pack('created', 'pack_123', 'Drake', creator_id, 'community')

# Pack generation failed
log_pack('failed', 'pack_456', 'Unknown', creator_id, 'gold')
```

### Log User Actions

```python
from services.bot_logger import log_user

log_user('opened_pack', user_id, {'pack_id': 'pack_123', 'cards_received': 5})
```

### Log Errors

```python
from services.bot_logger import log_error

try:
    # risky operation
    pass
except Exception as e:
    log_error(
        context='pack_creation',
        error=e,
        user_id=user_id,
        severity='error',
        send_alert=True
    )
```

### Log Restarts

```python
from services.bot_logger import log_restart

log_restart('crash', {'error': 'Memory exceeded'})
```

### Log Deployments

```python
from services.bot_logger import log_deployment

log_deployment(
    version='2.0.1',
    changelog='Bug fixes and performance improvements'
)
```

## Error Log Format

```json
{
  "timestamp": "2026-02-03T15:30:45.123456",
  "context": "pack_creation",
  "error_type": "ValueError",
  "details": "Invalid artist name",
  "traceback": "Traceback...",
  "user_id": 12345,
  "severity": "error",
  "metadata": {"pack_id": "pack_123"}
}
```

## Health Summary Output

```python
{
  'total_errors': 42,
  'errors_last_hour': 3,
  'error_types': {
    'ValueError': 15,
    'TimeoutError': 12,
    'ConnectionError': 8,
    # ... more types
  },
  'memory_usage': 65.4,
  'cpu_usage': 28.7,
  'timestamp': '2026-02-03T15:30:45.123456'
}
```

## Programmatic Access

### Get Error History

```python
from services.bot_logger import get_bot_logger

logger = get_bot_logger()

# Get all errors
all_errors = logger.get_error_history(limit=100)

# Get errors by context
pack_errors = logger.get_error_history(context='pack_creation', limit=50)
```

### Get Statistics

```python
# Get error stats
stats = logger.get_error_stats()

# Get health summary
health = logger.get_health_summary()
```

### Maintenance

```python
# Clear old errors (older than 30 days)
removed = logger.clear_old_errors(days=30)
print(f"Removed {removed} old errors")
```

## Alert Channel Detection

Alerts automatically post to first matching channel:
- `error-logs`
- `dev-logs`
- `admin-logs`
- `system-logs`

## Error Severity Matrix

| Severity | Emoji | When to Use |
|----------|-------|------------|
| debug | 🔍 | Diagnostic info |
| info | ℹ️ | Informational |
| warning | ⚠️ | Potential issues |
| error | ❌ | Failed operations |
| critical | 🚨 | System failures |

## Color Coding

- **Green**: No issues
- **Yellow**: Elevated warnings
- **Red**: Errors
- **Dark Red**: Critical

## Integration Points

### On Startup

```python
from services.bot_logger import log_restart
log_restart('startup')
```

### On Error

```python
from services.bot_logger import log_error

try:
    # operation
except Exception as e:
    log_error('operation_context', e, send_alert=True)
```

### On Pack Creation

```python
from services.bot_logger import log_pack

log_pack('created', pack_id, artist_name, creator_id, pack_type)
```

## File Locations

| File | Purpose |
|------|---------|
| `logs/system_errors.log` | Error log file |
| `logs/change_log.json` | Changelog entries |
| `logs/system_restarts.log` | Restart events |

## Examples

### Log Pack Creation with Error Handling

```python
from services.bot_logger import log_pack, log_error

try:
    pack_id = create_new_pack(artist, creator_id)
    log_pack('created', pack_id, artist, creator_id, 'community')
except Exception as e:
    log_error(
        'pack_creation',
        e,
        user_id=creator_id,
        send_alert=True
    )
```

### Log Battle Results

```python
from services.bot_logger import log_user

# After battle completes
log_user('battle_completed', winner_id, {
    'opponent': loser_id,
    'winner_cards': 3,
    'reward': 100
})
```

### Log Admin Actions

```python
from services.bot_logger import log_event

log_event(
    'admin_action',
    f'Admin {admin_id} deleted pack {pack_id}',
    user_id=admin_id,
    severity='high',
    send_alert=True
)
```

## Performance Considerations

- **Error File Growth**: ~1KB per error entry
- **Cleanup**: Run `clear_old_errors()` monthly
- **Memory**: Minimal impact with rolling window history
- **Alert Throttling**: Once per 5 minutes per alert type

## Troubleshooting

### Alerts not appearing?
1. Check channel naming (error-logs, dev-logs, etc.)
2. Verify bot permissions
3. Check bot is connected to Discord

### Old errors cluttering log?
```python
logger.clear_old_errors(days=30)  # Clear older than 30 days
```

### High error count?
```python
health = logger.get_health_summary()
print(f"Errors in last hour: {health['errors_last_hour']}")
```

## Future Enhancements

- [ ] Database storage for better querying
- [ ] Error pattern detection and alerts
- [ ] Automatic error recovery suggestions
- [ ] Integration with external error tracking (Sentry)
- [ ] Advanced filtering and search
- [ ] Error correlation and clustering
