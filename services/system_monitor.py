"""
System Monitor - Track bot restarts, uptime, performance, and resource usage
Provides real-time monitoring with Discord alerts for critical conditions
"""

import json
import os
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import time

# Try to import psutil, but gracefully handle if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

logger = logging.getLogger(__name__)


class SystemMonitor:
    """
    Monitors Music Legends Bot system health, performance, and uptime
    Tracks: restarts, uptime, resource usage, memory, CPU, active servers
    """
    
    # Performance thresholds for alerts
    MEMORY_CRITICAL = 85  # Alert if memory usage exceeds this %
    CPU_CRITICAL = 85    # Alert if CPU usage exceeds this %
    RESTART_ALERT_THRESHOLD = 3  # Alert if 3+ restarts in 1 hour
    
    def __init__(self, bot=None, log_path: str = 'logs/system_restarts.log'):
        """
        Initialize system monitor
        
        Args:
            bot: Discord bot instance for alerts
            log_path: Path to system restart log file
        """
        self.bot = bot
        self.log_path = log_path
        self.start_time = datetime.now()
        self.restart_count = 0
        self.last_alert_time = {}
        self.pending_restart_alerts = []  # Queue for alerts when event loop isn't ready
        
        # Ensure log directory exists
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Performance metrics history
        self.metrics_history = []
        self.max_history = 1000  # Keep last 1000 measurements
    
    def log_restart(self, restart_type: str = 'manual', metadata: Optional[Dict] = None) -> bool:
        """
        Log a system restart event
        
        Args:
            restart_type: Type of restart (manual, crash, scheduled, deployment, etc.)
            metadata: Additional context about restart
            
        Returns:
            bool: Success status
        """
        try:
            restart_info = {
                'timestamp': datetime.now().isoformat(),
                'type': restart_type,
                'system': 'Music Legends Bot',
                'environment': os.getenv('ENVIRONMENT', 'Production'),
                'version': os.getenv('BOT_VERSION', 'Unknown'),
                'metadata': metadata or {}
            }
            
            # Log to file
            with open(self.log_path, 'a') as log_file:
                json.dump(restart_info, log_file)
                log_file.write('\n')
            
            self.restart_count += 1
            logger.info(f"[RESTART] {restart_type} restart logged")
            
            # Determine severity based on restart type
            severity = 'high' if restart_type == 'crash' else 'medium'
            
            # Send alert via webhook (only if event loop is running)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._send_restart_alert_webhook(restart_info, severity))
                else:
                    # Queue for later when bot is ready
                    self.pending_restart_alerts.append((restart_info, severity))
                    logger.debug(f"[RESTART] Event loop not running, queued webhook alert")
            except RuntimeError:
                # Queue for later when bot is ready
                self.pending_restart_alerts.append((restart_info, severity))
                logger.debug(f"[RESTART] No event loop available, queued webhook alert")
            
            # Check for restart storm
            self._check_restart_storm()
            
            return True
        
        except Exception as e:
            logger.error(f"Error logging restart: {e}")
            return False
    
    async def _send_restart_alert_webhook(self, restart_info: Dict, severity: str = 'medium') -> None:
        """Send restart alert to webhook channel"""
        try:
            from monitor.alerts import send_econ
            
            restart_msg = f"**Type:** {restart_info['type'].title()}\n"
            restart_msg += f"**Environment:** {restart_info['environment']}\n"
            restart_msg += f"**Time:** {restart_info['timestamp']}"
            
            if restart_info.get('metadata'):
                meta_str = ', '.join([f"{k}: {v}" for k, v in list(restart_info['metadata'].items())[:3]])
                restart_msg += f"\n**Details:** {meta_str}"
            
            level = 'red' if severity == 'high' else 'orange'
            await send_econ("🔄 System Restart", restart_msg, level)
        
        except Exception as e:
            logger.error(f"Error sending restart webhook alert: {e}")
    
    async def send_pending_alerts(self) -> None:
        """Send any pending restart alerts that were queued during startup"""
        try:
            if self.pending_restart_alerts:
                logger.info(f"[RESTART] Sending {len(self.pending_restart_alerts)} pending restart alerts")
                for restart_info, severity in self.pending_restart_alerts:
                    await self._send_restart_alert_webhook(restart_info, severity)
                self.pending_restart_alerts.clear()
        except Exception as e:
            logger.error(f"Error sending pending restart alerts: {e}")
    
    async def monitor_uptime(self) -> Dict[str, Any]:
        """
        Monitor system uptime and performance metrics
        
        Returns:
            Dict with uptime and performance metrics
        """
        try:
            current_time = datetime.now()
            uptime_delta = current_time - self.start_time
            
            # Get system metrics if psutil is available
            if PSUTIL_AVAILABLE:
                memory_usage = psutil.virtual_memory().percent
                memory_mb = psutil.virtual_memory().used / 1024 / 1024
                memory_total_mb = psutil.virtual_memory().total / 1024 / 1024
                cpu_usage = psutil.cpu_percent(interval=1)
                cpu_count = psutil.cpu_count()
                disk_usage = psutil.disk_usage('/').percent
            else:
                memory_usage = 0
                memory_mb = 0
                memory_total_mb = 0
                cpu_usage = 0
                cpu_count = 0
                disk_usage = 0
            
            uptime_info = {
                'start_time': self.start_time.isoformat(),
                'current_time': current_time.isoformat(),
                'uptime_seconds': uptime_delta.total_seconds(),
                'uptime_formatted': self._format_uptime(uptime_delta),
                'restart_count': self.restart_count,
                'memory_usage': memory_usage,
                'memory_mb': memory_mb,
                'memory_total_mb': memory_total_mb,
                'cpu_usage': cpu_usage,
                'cpu_count': cpu_count,
                'disk_usage': disk_usage,
                'active_servers': len(self.bot.guilds) if self.bot else 0,
                'active_users': self._count_active_users() if self.bot else 0,
            }
            
            # Store in history
            self.metrics_history.append({
                'timestamp': current_time.isoformat(),
                **{k: v for k, v in uptime_info.items() if k not in ['start_time', 'current_time']}
            })
            
            # Keep history size manageable
            if len(self.metrics_history) > self.max_history:
                self.metrics_history.pop(0)
            
            # Check for critical resource usage
            await self._check_resource_thresholds(uptime_info)
            
            logger.debug(f"[MONITOR] Memory: {uptime_info['memory_usage']:.1f}% | CPU: {uptime_info['cpu_usage']:.1f}%")
            
            return uptime_info
        
        except Exception as e:
            logger.error(f"Error monitoring uptime: {e}")
            return {}
    
    async def _check_resource_thresholds(self, uptime_info: Dict) -> None:
        """Check if resource usage exceeds critical thresholds"""
        try:
            alerts = []
            
            # Check memory
            if uptime_info['memory_usage'] > self.MEMORY_CRITICAL:
                alerts.append({
                    'type': 'memory',
                    'value': uptime_info['memory_usage'],
                    'threshold': self.MEMORY_CRITICAL
                })
            
            # Check CPU
            if uptime_info['cpu_usage'] > self.CPU_CRITICAL:
                alerts.append({
                    'type': 'cpu',
                    'value': uptime_info['cpu_usage'],
                    'threshold': self.CPU_CRITICAL
                })
            
            # Send alerts (throttle to once per 5 minutes per alert type)
            for alert in alerts:
                alert_key = f"resource_{alert['type']}"
                if self._should_send_alert(alert_key):
                    await self._send_resource_alert(uptime_info, alerts)
                    self.last_alert_time[alert_key] = datetime.now()
        
        except Exception as e:
            logger.error(f"Error checking resource thresholds: {e}")
    
    async def _send_resource_alert(self, uptime_info: Dict, alerts: list) -> None:
        """Send resource usage alert to Discord"""
        try:
            fields = {
                'Memory': f"{uptime_info['memory_usage']:.1f}% ({uptime_info['memory_mb']:.0f}MB/{uptime_info['memory_total_mb']:.0f}MB)",
                'CPU': f"{uptime_info['cpu_usage']:.1f}% ({uptime_info['cpu_count']} cores)",
                'Disk': f"{uptime_info['disk_usage']:.1f}%",
                'Servers': str(uptime_info['active_servers']),
                'Uptime': uptime_info['uptime_formatted'],
            }
            
            alert_types = [a['type'].upper() for a in alerts]
            
            await self._post_alert_to_channel(
                title="⚠️ High Resource Usage Detected",
                description=f"Critical thresholds exceeded: {', '.join(alert_types)}",
                fields=fields,
                color_name='orange'
            )
        
        except Exception as e:
            logger.error(f"Error sending resource alert: {e}")
    
    def _check_restart_storm(self) -> None:
        """Check if there's a restart storm (multiple restarts in short time)"""
        try:
            if not Path(self.log_path).exists():
                return
            
            # Get restarts from the last hour
            one_hour_ago = datetime.now() - timedelta(hours=1)
            recent_restarts = []
            
            with open(self.log_path, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        timestamp = datetime.fromisoformat(entry['timestamp'])
                        if timestamp > one_hour_ago:
                            recent_restarts.append(entry)
                    except:
                        continue
            
            # Alert if restart storm detected
            if len(recent_restarts) >= self.RESTART_ALERT_THRESHOLD:
                logger.warning(f"[ALERT] Restart storm detected: {len(recent_restarts)} restarts in last hour")
                
                if self.bot and self._should_send_alert('restart_storm'):
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(
                                self._post_alert_to_channel(
                                    title="🚨 Restart Storm Detected",
                                    description=f"{len(recent_restarts)} restarts in the last hour - possible loop detected",
                                    fields={
                                        'Time Period': 'Last 60 minutes',
                                        'Restart Count': str(len(recent_restarts)),
                                        'Threshold': str(self.RESTART_ALERT_THRESHOLD),
                                    },
                                    color_name='red'
                                )
                            )
                            self.last_alert_time['restart_storm'] = datetime.now()
                    except RuntimeError:
                        logger.debug(f"[ALERT] No event loop available for restart storm alert")
        
        except Exception as e:
            logger.error(f"Error checking restart storm: {e}")
    
    def _should_send_alert(self, alert_key: str, throttle_minutes: int = 5) -> bool:
        """Check if enough time has passed to send another alert of this type"""
        if alert_key not in self.last_alert_time:
            return True
        
        time_since_last = datetime.now() - self.last_alert_time[alert_key]
        return time_since_last.total_seconds() > (throttle_minutes * 60)
    
    async def _post_alert_to_channel(
        self,
        title: str,
        description: str,
        fields: Dict[str, str] = None,
        color_name: str = 'blue'
    ) -> None:
        """Post formatted alert to Discord channel"""
        try:
            import discord
            
            color_map = {
                'red': discord.Color.red(),
                'orange': discord.Color.orange(),
                'yellow': discord.Color.yellow(),
                'green': discord.Color.green(),
                'blue': discord.Color.blue(),
            }
            
            embed = discord.Embed(
                title=title,
                description=description,
                color=color_map.get(color_name, discord.Color.blue()),
                timestamp=datetime.now()
            )
            
            if fields:
                for field_name, field_value in fields.items():
                    embed.add_field(name=field_name, value=str(field_value), inline=True)
            
            embed.set_footer(text="Music Legends System Monitor")
            
            # Find dev/admin channel
            if self.bot:
                for guild in self.bot.guilds:
                    for channel in guild.channels:
                        if any(name in channel.name.lower() for name in 
                               ['dev-logs', 'admin-logs', 'system-logs', 'bot-logs']):
                            await channel.send(embed=embed)
                            return
        
        except Exception as e:
            logger.error(f"Error posting alert to channel: {e}")
    
    def _severity_to_color_name(self, severity: str) -> str:
        """Convert severity to color name"""
        return {
            'critical': 'red',
            'high': 'orange',
            'medium': 'yellow',
            'low': 'blue',
        }.get(severity, 'blue')
    
    def _format_uptime(self, uptime_delta: timedelta) -> str:
        """Format uptime as human-readable string"""
        total_seconds = int(uptime_delta.total_seconds())
        
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0:
            parts.append(f"{seconds}s")
        
        return ' '.join(parts) or '0s'
    
    def _count_active_users(self) -> int:
        """Count active users across all servers"""
        try:
            if not self.bot:
                return 0
            
            users = set()
            for guild in self.bot.guilds:
                for member in guild.members:
                    if not member.bot:
                        users.add(member.id)
            
            return len(users)
        except:
            return 0
    
    def get_restart_history(self, limit: int = 50) -> list:
        """Get recent restart history"""
        try:
            restarts = []
            
            if not Path(self.log_path).exists():
                return restarts
            
            with open(self.log_path, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        restarts.append(json.loads(line))
                    except:
                        continue
            
            return sorted(restarts, key=lambda x: x['timestamp'], reverse=True)[:limit]
        
        except Exception as e:
            logger.error(f"Error getting restart history: {e}")
            return []
    
    def get_metrics_stats(self) -> Dict[str, Any]:
        """Get statistics about collected metrics"""
        try:
            if not self.metrics_history:
                return {}
            
            memories = [m['memory_usage'] for m in self.metrics_history if 'memory_usage' in m]
            cpus = [m['cpu_usage'] for m in self.metrics_history if 'cpu_usage' in m]
            
            return {
                'total_measurements': len(self.metrics_history),
                'avg_memory': sum(memories) / len(memories) if memories else 0,
                'max_memory': max(memories) if memories else 0,
                'min_memory': min(memories) if memories else 0,
                'avg_cpu': sum(cpus) / len(cpus) if cpus else 0,
                'max_cpu': max(cpus) if cpus else 0,
                'min_cpu': min(cpus) if cpus else 0,
            }
        
        except Exception as e:
            logger.error(f"Error getting metrics stats: {e}")
            return {}


# Global instance
_system_monitor: Optional[SystemMonitor] = None


def get_system_monitor(bot=None) -> SystemMonitor:
    """Get or create global system monitor instance"""
    global _system_monitor
    
    if _system_monitor is None:
        _system_monitor = SystemMonitor(bot=bot)
    
    return _system_monitor


# Convenience functions
def log_bot_restart(restart_type: str = 'manual', metadata: Optional[Dict] = None):
    """Log a bot restart event"""
    monitor = get_system_monitor()
    return monitor.log_restart(restart_type, metadata)


def log_bot_crash(error: str = None, traceback_str: str = None):
    """Log a bot crash event"""
    monitor = get_system_monitor()
    return monitor.log_restart(
        restart_type='crash',
        metadata={
            'error': error,
            'traceback': traceback_str
        }
    )


def log_deployment(version: str = None, changelog: str = None):
    """Log a deployment event"""
    monitor = get_system_monitor()
    return monitor.log_restart(
        restart_type='deployment',
        metadata={
            'version': version,
            'changelog': changelog
        }
    )
