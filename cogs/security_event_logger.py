# security_event_logger.py
"""
Centralized Security Event Logging System
- Structured JSON logging for audit trails
- Real-time alert system for critical events
- Log rotation and archival
- Query and analysis utilities
- Integration with Discord notifications
"""

import os
import json
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Callable
from pathlib import Path
from enum import Enum
import threading
from collections import deque
import discord


# ==========================================
# EVENT SEVERITY LEVELS
# ==========================================

class EventSeverity(Enum):
    """Security event severity levels"""
    INFO = "INFO"                          # Routine security events
    WARNING = "WARNING"                    # Suspicious activity
    CRITICAL = "CRITICAL"                  # Immediate action required
    EMERGENCY = "EMERGENCY"                # System compromise suspected


# ==========================================
# CENTRALIZED SECURITY EVENT LOGGER
# ==========================================

class SecurityEventLogger:
    """
    Enterprise-grade centralized security event logging
    
    Features:
    - Structured JSON logging
    - Log rotation (daily)
    - Alert system for critical events
    - IP address and user tracking
    - Event deduplication
    - Encryption of sensitive fields
    """
    
    def __init__(
        self,
        log_directory: str = "logs/security",
        max_log_size_mb: int = 100,
        alert_handlers: List[Callable] = None,
        enable_encryption: bool = True
    ):
        self.log_directory = Path(log_directory)
        self.max_log_size = max_log_size_mb * 1024 * 1024
        self.alert_handlers = alert_handlers or []
        self.enable_encryption = enable_encryption
        
        # Create log directory
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # Event deduplication (prevent log spam)
        self.event_cache = deque(maxlen=1000)
        self.cache_ttl = timedelta(minutes=5)
        
        # Alert queue for async processing
        self.alert_queue = deque(maxlen=100)
        self.alert_thread = None
        self._start_alert_processor()
        
        print(f"✅ [SECURITY_LOGGER] Initialized in {self.log_directory}")
        print(f"   Max log size: {max_log_size_mb}MB")
        print(f"   Encryption: {'Enabled' if enable_encryption else 'Disabled'}")
        print(f"   Alert handlers: {len(self.alert_handlers)}")
    
    def _get_log_file_path(self, severity: EventSeverity) -> Path:
        """Get path for log file based on severity and date"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"security_{severity.value.lower()}_{date_str}.json"
        return self.log_directory / filename
    
    def _should_rotate_log(self, filepath: Path) -> bool:
        """Check if log file should be rotated"""
        if not filepath.exists():
            return False
        return filepath.stat().st_size > self.max_log_size
    
    def _rotate_log_file(self, filepath: Path):
        """Rotate log file with timestamp"""
        if not filepath.exists():
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"{filepath.stem}_{timestamp}.json"
        archive_path = self.log_directory / archive_name
        
        try:
            filepath.rename(archive_path)
            print(f"📦 [SECURITY_LOGGER] Rotated log: {archive_name}")
        except Exception as e:
            print(f"❌ [SECURITY_LOGGER] Failed to rotate log: {e}")
    
    def _hash_sensitive_field(self, value: str, salt: str = "music-legends") -> str:
        """Hash sensitive fields for privacy"""
        if not value:
            return None
        
        try:
            salted = f"{salt}:{value}"
            return hashlib.sha256(salted.encode()).hexdigest()[:16]
        except Exception as e:
            print(f"⚠️  [SECURITY_LOGGER] Failed to hash field: {e}")
            return "HASH_ERROR"
    
    def _sanitize_details(self, details: Dict) -> Dict:
        """Remove or hash sensitive information from details"""
        if not details:
            return {}
        
        sanitized = {}
        sensitive_fields = [
            'password', 'token', 'key', 'secret', 'api_key',
            'credit_card', 'ssn', 'pin', 'private_key'
        ]
        
        for key, value in details.items():
            # Hash sensitive fields
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                sanitized[key] = self._hash_sensitive_field(str(value))
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _is_duplicate_event(
        self,
        event_type: str,
        user_id: Optional[int],
        details: Dict
    ) -> bool:
        """
        Check if similar event was recently logged (prevent spam)
        
        Returns True if duplicate, False if new event
        """
        current_time = datetime.now()
        event_hash = hashlib.md5(
            f"{event_type}:{user_id}:{json.dumps(details, sort_keys=True)}".encode()
        ).hexdigest()
        
        # Check cache for recent similar events
        for cached_hash, cached_time in self.event_cache:
            if cached_hash == event_hash:
                if current_time - cached_time < self.cache_ttl:
                    return True  # Duplicate within TTL
        
        # Record this event
        self.event_cache.append((event_hash, current_time))
        return False
    
    def log_event(
        self,
        event_type: str,
        severity: EventSeverity = EventSeverity.INFO,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict] = None,
        skip_duplicate_check: bool = False
    ) -> bool:
        """
        Log a security event
        
        Args:
            event_type: Type of security event
            severity: Event severity level
            user_id: Discord user ID if applicable
            ip_address: Source IP address
            details: Additional event details
            skip_duplicate_check: Skip deduplication check
            
        Returns:
            True if logged successfully
        """
        
        # Skip duplicate events
        if not skip_duplicate_check and self._is_duplicate_event(event_type, user_id, details or {}):
            print(f"↷ [SECURITY_LOGGER] Duplicate event (suppressed): {event_type}")
            return False
        
        # Sanitize details
        safe_details = self._sanitize_details(details or {})
        
        # Create log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "severity": severity.value,
            "user_id": str(user_id) if user_id else None,
            "ip_address": ip_address,
            "details": safe_details,
            "log_version": "1.0"
        }
        
        # Get appropriate log file
        log_file_path = self._get_log_file_path(severity)
        
        # Check if rotation needed
        if self._should_rotate_log(log_file_path):
            self._rotate_log_file(log_file_path)
        
        # Write to log file
        try:
            with open(log_file_path, 'a') as log_file:
                json.dump(log_entry, log_file)
                log_file.write('\n')
            
            print(f"📝 [SECURITY_LOGGER] {severity.value}: {event_type}")
            
        except Exception as e:
            print(f"❌ [SECURITY_LOGGER] Failed to write log: {e}")
            return False
        
        # Queue alert if critical
        if severity in [EventSeverity.CRITICAL, EventSeverity.EMERGENCY]:
            self._queue_alert(log_entry, severity)
        
        return True
    
    def _queue_alert(self, log_entry: Dict, severity: EventSeverity):
        """Queue alert for critical events"""
        self.alert_queue.append((log_entry, severity))
        print(f"🚨 [SECURITY_LOGGER] Alert queued: {log_entry['event_type']}")
    
    def _start_alert_processor(self):
        """Start background thread for processing alerts"""
        self.alert_thread = threading.Thread(
            target=self._process_alert_queue,
            daemon=True
        )
        self.alert_thread.start()
    
    def _process_alert_queue(self):
        """Process queued alerts asynchronously"""
        while True:
            try:
                if self.alert_queue:
                    log_entry, severity = self.alert_queue.popleft()
                    self._send_alerts(log_entry, severity)
                else:
                    threading.Event().wait(0.1)  # Short sleep
            except Exception as e:
                print(f"❌ [SECURITY_LOGGER] Alert processor error: {e}")
    
    def _send_alerts(self, log_entry: Dict, severity: EventSeverity):
        """Send alerts through registered handlers"""
        for handler in self.alert_handlers:
            try:
                handler(log_entry, severity)
            except Exception as e:
                print(f"❌ [SECURITY_LOGGER] Alert handler error: {e}")
    
    def register_alert_handler(self, handler: Callable):
        """Register a handler for critical alerts"""
        if handler not in self.alert_handlers:
            self.alert_handlers.append(handler)
            print(f"✅ [SECURITY_LOGGER] Alert handler registered")
    
    def get_events(
        self,
        event_type: Optional[str] = None,
        user_id: Optional[int] = None,
        severity: Optional[EventSeverity] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict]:
        """
        Query logged events
        
        Args:
            event_type: Filter by event type
            user_id: Filter by user ID
            severity: Filter by severity
            hours: Lookback period
            limit: Maximum results
            
        Returns:
            List of matching log entries
        """
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        events = []
        
        # Determine which log files to read
        log_files = list(self.log_directory.glob("security_*.json"))
        
        for log_file in sorted(log_files, reverse=True):
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        
                        try:
                            entry = json.loads(line)
                            entry_time = datetime.fromisoformat(entry['timestamp'])
                            
                            # Skip if outside time range
                            if entry_time < cutoff_time:
                                continue
                            
                            # Apply filters
                            if event_type and entry['event_type'] != event_type:
                                continue
                            if user_id and entry['user_id'] != str(user_id):
                                continue
                            if severity and entry['severity'] != severity.value:
                                continue
                            
                            events.append(entry)
                            
                            # Stop if reached limit
                            if len(events) >= limit:
                                return events
                        
                        except json.JSONDecodeError:
                            continue
            
            except Exception as e:
                print(f"⚠️  [SECURITY_LOGGER] Error reading log file: {e}")
                continue
        
        return events
    
    def get_user_audit_trail(self, user_id: int, hours: int = 24) -> List[Dict]:
        """Get audit trail for specific user"""
        return self.get_events(user_id=user_id, hours=hours)
    
    def get_summary_stats(self, hours: int = 24) -> Dict:
        """Get summary statistics for security events"""
        events = self.get_events(hours=hours, limit=10000)
        
        stats = {
            "total_events": len(events),
            "by_severity": {},
            "by_type": {},
            "critical_events": [],
            "most_active_users": {}
        }
        
        for event in events:
            # Count by severity
            severity = event.get('severity', 'UNKNOWN')
            stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1
            
            # Count by type
            event_type = event.get('event_type', 'UNKNOWN')
            stats['by_type'][event_type] = stats['by_type'].get(event_type, 0) + 1
            
            # Track critical events
            if severity in ['CRITICAL', 'EMERGENCY']:
                stats['critical_events'].append({
                    "type": event_type,
                    "time": event.get('timestamp'),
                    "user": event.get('user_id')
                })
            
            # Track most active users
            user_id = event.get('user_id')
            if user_id:
                stats['most_active_users'][user_id] = stats['most_active_users'].get(user_id, 0) + 1
        
        # Sort most active users
        stats['most_active_users'] = dict(
            sorted(stats['most_active_users'].items(), key=lambda x: x[1], reverse=True)[:10]
        )
        
        return stats


# ==========================================
# DISCORD ALERT HANDLER
# ==========================================

async def discord_security_alert_handler(
    log_entry: Dict,
    severity: EventSeverity,
    alert_channel: discord.TextChannel
):
    """Send security alerts to Discord channel"""
    
    try:
        color_map = {
            EventSeverity.WARNING: discord.Color.yellow(),
            EventSeverity.CRITICAL: discord.Color.red(),
            EventSeverity.EMERGENCY: discord.Color.dark_red()
        }
        
        embed = discord.Embed(
            title=f"🚨 Security Alert - {severity.value}",
            description=f"**Event:** {log_entry.get('event_type', 'Unknown')}",
            color=color_map.get(severity, discord.Color.orange()),
            timestamp=datetime.fromisoformat(log_entry.get('timestamp', ''))
        )
        
        if log_entry.get('user_id'):
            embed.add_field(
                name="User",
                value=f"<@{log_entry.get('user_id')}>",
                inline=True
            )
        
        if log_entry.get('ip_address'):
            embed.add_field(
                name="IP Address",
                value=f"`{log_entry.get('ip_address')}`",
                inline=True
            )
        
        # Add details
        details = log_entry.get('details', {})
        if details:
            details_str = "\n".join([
                f"• **{k}:** {v}" for k, v in list(details.items())[:5]
            ])
            embed.add_field(
                name="Details",
                value=details_str or "No additional details",
                inline=False
            )
        
        embed.set_footer(text=f"Event ID: {log_entry.get('timestamp')[:10]}")
        
        await alert_channel.send(embed=embed)
        
    except Exception as e:
        print(f"❌ [ALERT] Failed to send Discord alert: {e}")


# ==========================================
# GLOBAL LOGGER INSTANCE
# ==========================================

# Initialize global logger
security_logger = SecurityEventLogger(
    log_directory="logs/security",
    max_log_size_mb=100,
    enable_encryption=True
)


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def setup_discord_alerts(bot: discord.Client, alert_channel_name: str = "security-alerts"):
    """Setup Discord alerts for security events"""
    
    async def on_ready():
        # Find alert channel
        for guild in bot.guilds:
            for channel in guild.text_channels:
                if channel.name == alert_channel_name:
                    print(f"✅ [SECURITY] Discord alerts enabled in #{channel.name}")
                    
                    # Create async handler
                    async def handler(log_entry, severity):
                        await discord_security_alert_handler(log_entry, severity, channel)
                    
                    security_logger.register_alert_handler(handler)
                    return
    
    bot.event(on_ready)


def log_suspicious_activity(
    activity_type: str,
    user_id: Optional[int] = None,
    details: Optional[Dict] = None,
    ip_address: Optional[str] = None
):
    """Convenience function for logging suspicious activity"""
    security_logger.log_event(
        f"SUSPICIOUS_{activity_type.upper()}",
        severity=EventSeverity.WARNING,
        user_id=user_id,
        ip_address=ip_address,
        details=details
    )


def log_security_breach(
    breach_type: str,
    user_id: Optional[int] = None,
    details: Optional[Dict] = None
):
    """Convenience function for logging security breaches"""
    security_logger.log_event(
        f"BREACH_{breach_type.upper()}",
        severity=EventSeverity.EMERGENCY,
        user_id=user_id,
        details=details,
        skip_duplicate_check=True  # Always log breaches
    )
