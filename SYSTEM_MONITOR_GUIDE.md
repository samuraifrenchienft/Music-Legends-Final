# System Monitor - Bot Health & Performance Tracking

## Overview

The SystemMonitor provides comprehensive bot health monitoring including:

- **Restart Tracking**: Log and analyze all bot restarts (manual, crash, deployment)
- **Uptime Monitoring**: Continuous uptime tracking with human-readable formatting
- **Resource Monitoring**: Real-time CPU, memory, and disk usage tracking
- **Performance Metrics**: Historical performance data with statistics
- **Discord Alerts**: Automatic alerts for critical conditions
- **Restart Storm Detection**: Alerts if multiple restarts occur in short time period

## Architecture

### Components

1. **SystemMonitor** (`services/system_monitor.py`)
   - Core monitoring and logging logic
   - Resource threshold checking
   - Discord alert integration

2. **SystemMonitorCommandsCog** (`cogs/system_monitor_commands.py`)
   - Discord commands for viewing metrics
   - Real-time monitoring loop
   - Automatic background monitoring

3. **Restart Log** (`logs/system_restarts.log`)
   - Persistent storage of all restart events
   - JSON format, one entry per line

## Discord Commands

### /uptime
Check bot uptime and current system health

```
Shows:
- Total uptime
- Memory usage (with emoji status)
- CPU usage (with emoji status)
- Disk usage
- Active servers and unique users
- Overall health status
```

### /restarts
View recent restart history

```
/restarts [limit]  - Show up to 50 recent restarts
```

### /restart_stats
View restart statistics and trends

```
Shows:
- Total restart count
- Breakdowns by restart type
- Average restarts per day/month
```

### /performance
View collected performance metrics

```
Shows:
- Number of collected samples
- Average/peak/low memory usage
- Average/peak/low CPU usage
```

## Restart Types

| Type | Trigger |
|------|---------|
| `startup` | Bot initial startup |
| `manual` | Intentional restart |
| `crash` | Bot crash (exception) |
| `deployment` | Code deployment |
| `scheduled` | Scheduled maintenance |

## Resource Thresholds

| Resource | Critical | Alert Frequency |
|----------|----------|-----------------|
| Memory | 85% | Once per 5 minutes |
| CPU | 85% | Once per 5 minutes |
| Restart Storm | 3+ in 1 hour | Once per 5 minutes |

## Usage Examples

### Log a Bot Restart

```python
from services.system_monitor import log_bot_restart

# Manual restart
log_bot_restart('manual')

# Deployment
log_bot_restart(
    'deployment',
    {'version': '2.0.1', 'changelog': 'Fixed pack creation'}
)
```

### Log a Crash

```python
from services.system_monitor import log_bot_crash

try:
    # risky operation
    pass
except Exception as e:
    import traceback
    log_bot_crash(
        error=str(e),
        traceback_str=traceback.format_exc()
    )
```

### Log a Deployment

```python
from services.system_monitor import log_deployment

log_deployment(
    version='2.0.0',
    changelog='Added pack creation, fixed image rendering'
)
```

### Monitor Uptime Programmatically

```python
from services.system_monitor import get_system_monitor
import asyncio

monitor = get_system_monitor()
metrics = await monitor.monitor_uptime()

print(f"Uptime: {metrics['uptime_formatted']}")
print(f"Memory: {metrics['memory_usage']:.1f}%")
print(f"CPU: {metrics['cpu_usage']:.1f}%")
print(f"Servers: {metrics['active_servers']}")
```

## Alert Examples

### High Memory Usage Alert

```
⚠️ High Resource Usage Detected

Critical thresholds exceeded: MEMORY

Memory: 87.3% (2048MB/2355MB)
CPU: 45.2% (8 cores)
Disk: 62.1%
Servers: 5
Uptime: 2d 5h 30m
```

### Restart Storm Alert

```
🚨 Restart Storm Detected

3 restarts in the last hour - possible loop detected

Time Period: Last 60 minutes
Restart Count: 3
Threshold: 3
```

## Restart Log Format

```json
{"timestamp": "2026-02-03T15:30:45.123456", "type": "startup", "system": "Music Legends Bot", "environment": "Production", "version": "2.0.0", "metadata": {}}
{"timestamp": "2026-02-03T18:15:20.654321", "type": "deployment", "system": "Music Legends Bot", "environment": "Production", "version": "2.0.1", "metadata": {"version": "2.0.1", "changelog": "Fixed image rendering"}}
```

## Background Monitoring

The SystemMonitor runs continuous background monitoring:

```
Every 60 seconds:
1. Collect memory, CPU, disk metrics
2. Count active servers and users
3. Check resource thresholds
4. Send alerts if needed
5. Store metrics in history (keep last 1000)
```

## Channel Detection

Alerts are posted to the first matching channel:
- `dev-logs`
- `admin-logs`
- `system-logs`
- `bot-logs`

### Setting Up Alert Channel

1. Create a channel: `dev-logs`
2. Give bot permission to send messages
3. Alerts will automatically post there

## Performance Metrics History

The monitor keeps a rolling window of the last 1000 measurements:

```python
monitor.metrics_history  # List of metric snapshots
monitor.get_metrics_stats()  # Aggregated statistics
```

## Thresholds & Configuration

Customize thresholds in `SystemMonitor` class:

```python
class SystemMonitor:
    MEMORY_CRITICAL = 85    # Alert if > 85%
    CPU_CRITICAL = 85       # Alert if > 85%
    RESTART_ALERT_THRESHOLD = 3  # Alert if 3+ restarts in 1 hour
```

## Color Coding in Uptime Command

Memory/CPU usage indicators:
- 🟢 Green: Normal (<70%)
- 🟡 Yellow: Elevated (70-85%)
- 🔴 Red: Critical (>85%)

## Maintenance

### Clean Old Logs

```python
import os
from pathlib import Path

# Manually clean old restart logs
log_file = Path('logs/system_restarts.log')
if log_file.exists():
    log_file.unlink()
```

### Monitor Active Restarts

```python
monitor = get_system_monitor()

# Get recent restarts
restarts = monitor.get_restart_history(limit=100)

# Get current statistics
stats = monitor.get_metrics_stats()
```

## Integration Points

### On Bot Startup

```python
# In run_bot.py
from services.system_monitor import log_bot_restart
log_bot_restart('startup')
```

### On Crash

```python
# In run_bot.py exception handler
from services.system_monitor import log_bot_crash
log_bot_crash(error=str(e), traceback_str=traceback.format_exc())
```

### On Deployment

```python
# In deployment scripts
from services.system_monitor import log_deployment
log_deployment(version='2.0.1', changelog='Bug fixes and improvements')
```

## Performance Considerations

- **Metrics History**: Stores last 1000 measurements (~1MB memory)
- **Restart Log**: Grows ~1KB per restart event
- **Monitoring Loop**: Runs every 60 seconds (minimal CPU impact)
- **Background Task**: Non-blocking, doesn't affect bot responsiveness

## Troubleshooting

### Alerts not appearing in Discord?
1. Check channel name matches (dev-logs, admin-logs, etc.)
2. Verify bot has permission to send messages
3. Check firewall/proxy isn't blocking Discord API

### Memory usage rising rapidly?
1. Check for memory leaks in packs or cards
2. Run `/performance` to see trend
3. Check memory stats over time

### Restart storm alerts firing?
1. Check bot logs for crash causes
2. Review `/restarts` for patterns
3. Check system resources (`/uptime`)

## Future Enhancements

- [ ] Database storage for historical metrics
- [ ] Grafana/Prometheus integration
- [ ] Custom alert thresholds per server
- [ ] Automatic restart recovery
- [ ] Memory profiling tools
- [ ] Log archival and compression
