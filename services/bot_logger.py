"""
Bot Logger - Centralized logging that integrates changelog, system monitoring, and error tracking
Provides unified interface for all bot logging and alerting
"""

import json
import os
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import traceback

from services.changelog_manager import get_changelog_manager
from services.system_monitor import get_system_monitor

logger = logging.getLogger(__name__)


class BotLogger:
    """
    Centralized logging system that integrates:
    - Changelog Manager (system changes)
    - System Monitor (restarts, uptime, resources)
    - Error Logger (exceptions and failures)
    Provides unified Discord alerting
    """
    
    # Error severity levels
    ERROR_LEVELS = {
        'debug': {'emoji': '🔍', 'severity': 'low'},
        'info': {'emoji': 'ℹ️', 'severity': 'low'},
        'warning': {'emoji': '⚠️', 'severity': 'medium'},
        'error': {'emoji': '❌', 'severity': 'high'},
        'critical': {'emoji': '🚨', 'severity': 'critical'},
    }
    
    def __init__(self, bot=None, error_log_path: str = 'logs/system_errors.log'):
        """
        Initialize Bot Logger
        
        Args:
            bot: Discord bot instance for alerts
            error_log_path: Path to error log file
        """
        self.bot = bot
        self.error_log_path = error_log_path
        
        # Initialize subsystems
        self.changelog = get_changelog_manager(bot=bot)
        self.system_monitor = get_system_monitor(bot=bot)
        
        # Ensure log directory exists
        Path(error_log_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Track error stats
        self.error_stats = {}
        self.last_alert_time = {}
    
    # ==================== MAJOR EVENT LOGGING ====================
    
    def log_major_event(
        self,
        event_type: str,
        description: str,
        user_id: Optional[int] = None,
        severity: str = 'medium',
        metadata: Optional[Dict] = None,
        send_alert: bool = False
    ) -> bool:
        """
        Log major system events through changelog
        
        Args:
            event_type: Type of event
            description: Event description
            user_id: Optional user ID
            severity: Event severity (low, medium, high, critical)
            metadata: Additional context
            send_alert: Whether to send Discord alert
            
        Returns:
            bool: Success status
        """
        try:
            self.changelog.log_change(
                category='system_event',
                description=description,
                user_id=user_id,
                severity=severity,
                metadata=metadata or {},
                send_alert=send_alert
            )
            logger.info(f"[EVENT] {event_type}: {description}")
            return True
        
        except Exception as e:
            logger.error(f"Error logging major event: {e}")
            return False
    
    def log_pack_event(
        self,
        action: str,
        pack_id: str,
        artist_name: str,
        creator_id: int,
        pack_type: str = 'community',
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Log pack-related events
        
        Args:
            action: Action (created, generated, published, failed, etc.)
            pack_id: Pack ID
            artist_name: Artist name
            creator_id: Creator user ID
            pack_type: Pack type (community, gold, etc.)
            metadata: Additional metadata
            
        Returns:
            bool: Success status
        """
        try:
            description = f"Pack {action}: {artist_name} ({pack_type})"
            
            full_metadata = {
                'pack_id': pack_id,
                'artist': artist_name,
                'type': pack_type,
                **(metadata or {})
            }
            
            self.changelog.log_change(
                category='pack_creation' if action == 'created' else 'system_event',
                description=description,
                user_id=creator_id,
                severity='high',
                metadata=full_metadata,
                send_alert=action in ['failed', 'error']
            )
            
            logger.info(f"[PACK] {description}")
            return True
        
        except Exception as e:
            logger.error(f"Error logging pack event: {e}")
            return False
    
    def log_user_action(
        self,
        action: str,
        user_id: int,
        details: Optional[Dict] = None
    ) -> bool:
        """
        Log user actions
        
        Args:
            action: Action type (opened_pack, battle, trade, etc.)
            user_id: User ID
            details: Additional details
            
        Returns:
            bool: Success status
        """
        try:
            self.changelog.log_change(
                category='user_action',
                description=f"User action: {action}",
                user_id=user_id,
                severity='low',
                metadata=details or {}
            )
            logger.debug(f"[USER] {action} by {user_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error logging user action: {e}")
            return False
    
    # ==================== RESTART LOGGING ====================
    
    def log_restart(
        self,
        restart_type: str = 'manual',
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Log system restart
        
        Args:
            restart_type: Type of restart (manual, crash, scheduled, deployment)
            metadata: Additional context
            
        Returns:
            bool: Success status
        """
        try:
            self.system_monitor.log_restart(restart_type, metadata)
            logger.info(f"[RESTART] {restart_type} restart logged")
            return True
        
        except Exception as e:
            logger.error(f"Error logging restart: {e}")
            return False
    
    def log_deployment(
        self,
        version: str,
        changelog: str = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Log deployment event
        
        Args:
            version: New version number
            changelog: Deployment changelog
            metadata: Additional context
            
        Returns:
            bool: Success status
        """
        try:
            full_metadata = {'version': version, **(metadata or {})}
            if changelog:
                full_metadata['changelog'] = changelog
            
            self.system_monitor.log_restart('deployment', full_metadata)
            self.log_major_event(
                'deployment',
                f"Deployment: v{version}",
                severity='high',
                metadata=full_metadata,
                send_alert=True
            )
            
            logger.info(f"[DEPLOYMENT] v{version} deployed")
            return True
        
        except Exception as e:
            logger.error(f"Error logging deployment: {e}")
            return False
    
    # ==================== ERROR LOGGING ====================
    
    def log_error(
        self,
        error_context: str,
        error_details: Exception = None,
        user_id: Optional[int] = None,
        severity: str = 'error',
        metadata: Optional[Dict] = None,
        send_alert: bool = True
    ) -> bool:
        """
        Log system errors with full context
        
        Args:
            error_context: Context where error occurred (e.g., "pack_creation")
            error_details: Exception object
            user_id: Optional user ID involved
            severity: Error severity (warning, error, critical)
            metadata: Additional context
            send_alert: Whether to send Discord alert
            
        Returns:
            bool: Success status
        """
        try:
            error_str = str(error_details) if error_details else "Unknown error"
            traceback_str = ""
            
            if error_details:
                traceback_str = traceback.format_exc()
            
            error_entry = {
                'timestamp': datetime.now().isoformat(),
                'context': error_context,
                'error_type': type(error_details).__name__ if error_details else 'Unknown',
                'details': error_str,
                'traceback': traceback_str,
                'user_id': user_id,
                'severity': severity,
                'metadata': metadata or {}
            }
            
            # Write to error log file
            with open(self.error_log_path, 'a') as error_file:
                json.dump(error_entry, error_file)
                error_file.write('\n')
            
            # Update stats
            self._update_error_stats(error_context)
            
            # Log through changelog
            self.changelog.log_change(
                category='error',
                description=f"{error_context}: {error_str[:100]}",
                user_id=user_id,
                severity=severity,
                metadata={
                    'error_type': type(error_details).__name__ if error_details else 'Unknown',
                    'context': error_context,
                    **(metadata or {})
                },
                send_alert=send_alert
            )
            
            # Send Discord alert
            if send_alert and self.bot:
                asyncio.create_task(
                    self._send_error_alert(error_entry)
                )
            
            logger.error(f"[ERROR] {error_context}: {error_str}")
            if traceback_str:
                logger.debug(f"Traceback:\n{traceback_str}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error logging error: {e}")
            return False
    
    def log_warning(
        self,
        warning_context: str,
        warning_message: str,
        metadata: Optional[Dict] = None,
        send_alert: bool = False
    ) -> bool:
        """
        Log warning events
        
        Args:
            warning_context: Context (e.g., "high_memory_usage")
            warning_message: Warning message
            metadata: Additional context
            send_alert: Whether to send Discord alert
            
        Returns:
            bool: Success status
        """
        try:
            self.changelog.log_change(
                category='system_event',
                description=f"Warning: {warning_message}",
                severity='medium',
                metadata={'context': warning_context, **(metadata or {})},
                send_alert=send_alert
            )
            
            logger.warning(f"[WARNING] {warning_context}: {warning_message}")
            return True
        
        except Exception as e:
            logger.error(f"Error logging warning: {e}")
            return False
    
    async def _send_error_alert(self, error_entry: Dict) -> None:
        """Send error alert to Discord"""
        try:
            if not self.bot or not self.bot.user:
                return
            
            severity = error_entry.get('severity', 'error')
            level_info = self.ERROR_LEVELS.get(severity, self.ERROR_LEVELS['error'])
            emoji = level_info['emoji']
            
            import discord
            
            # Determine color based on severity
            color_map = {
                'debug': discord.Color.grey(),
                'info': discord.Color.blue(),
                'warning': discord.Color.orange(),
                'error': discord.Color.red(),
                'critical': discord.Color.dark_red(),
            }
            
            embed = discord.Embed(
                title=f"{emoji} Error Alert - {error_entry['error_type']}",
                description=error_entry['details'][:100],
                color=color_map.get(severity, discord.Color.red()),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="Context",
                value=error_entry['context'],
                inline=True
            )
            
            embed.add_field(
                name="Severity",
                value=severity.upper(),
                inline=True
            )
            
            if error_entry.get('user_id'):
                embed.add_field(
                    name="User",
                    value=f"`{error_entry['user_id']}`",
                    inline=True
                )
            
            if error_entry.get('metadata'):
                meta_str = '\n'.join(
                    [f"• {k}: {v}" for k, v in list(error_entry['metadata'].items())[:3]]
                )
                embed.add_field(
                    name="Details",
                    value=meta_str[:1024],
                    inline=False
                )
            
            embed.set_footer(text="Music Legends Bot Logger")
            
            # Find error channel
            for guild in self.bot.guilds:
                for channel in guild.channels:
                    if any(name in channel.name.lower() for name in 
                           ['error-logs', 'dev-logs', 'admin-logs', 'system-logs']):
                        try:
                            await channel.send(embed=embed)
                            return
                        except:
                            continue
        
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    # ==================== STATISTICS & RETRIEVAL ====================
    
    def _update_error_stats(self, error_context: str) -> None:
        """Update error statistics"""
        if error_context not in self.error_stats:
            self.error_stats[error_context] = {
                'count': 0,
                'first_occurrence': datetime.now().isoformat(),
                'last_occurrence': None,
            }
        
        self.error_stats[error_context]['count'] += 1
        self.error_stats[error_context]['last_occurrence'] = datetime.now().isoformat()
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return self.error_stats.copy()
    
    def get_error_history(self, context: Optional[str] = None, limit: int = 100) -> list:
        """Get error history"""
        try:
            errors = []
            
            if not Path(self.error_log_path).exists():
                return errors
            
            with open(self.error_log_path, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        if context and entry.get('context') != context:
                            continue
                        errors.append(entry)
                    except:
                        continue
            
            return sorted(errors, key=lambda x: x['timestamp'], reverse=True)[:limit]
        
        except Exception as e:
            logger.error(f"Error retrieving error history: {e}")
            return []
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall system health summary"""
        try:
            import psutil
            
            errors = self.get_error_history(limit=1000)
            recent_errors = [
                e for e in errors
                if (datetime.now() - datetime.fromisoformat(e['timestamp'])).total_seconds() < 3600
            ]
            
            error_types = {}
            for error in errors[-100:]:  # Last 100 errors
                etype = error.get('error_type', 'Unknown')
                error_types[etype] = error_types.get(etype, 0) + 1
            
            return {
                'total_errors': len(errors),
                'errors_last_hour': len(recent_errors),
                'error_types': error_types,
                'memory_usage': psutil.virtual_memory().percent,
                'cpu_usage': psutil.cpu_percent(interval=0.1),
                'timestamp': datetime.now().isoformat(),
            }
        
        except Exception as e:
            logger.error(f"Error getting health summary: {e}")
            return {}
    
    def clear_old_errors(self, days: int = 30) -> int:
        """Clear error logs older than specified days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            errors = self.get_error_history(limit=10000)
            
            kept_errors = [
                e for e in errors
                if datetime.fromisoformat(e['timestamp']) > cutoff_date
            ]
            
            removed_count = len(errors) - len(kept_errors)
            
            # Rewrite log file
            with open(self.error_log_path, 'w') as f:
                for error in kept_errors:
                    json.dump(error, f)
                    f.write('\n')
            
            logger.info(f"Cleared {removed_count} old error entries")
            return removed_count
        
        except Exception as e:
            logger.error(f"Error clearing old errors: {e}")
            return 0


# Global instance
_bot_logger: Optional[BotLogger] = None


def get_bot_logger(bot=None) -> BotLogger:
    """Get or create global bot logger instance"""
    global _bot_logger
    
    if _bot_logger is None:
        _bot_logger = BotLogger(bot=bot)
    
    return _bot_logger


# Convenience functions
def log_event(event_type: str, description: str, user_id: Optional[int] = None, severity: str = 'medium', send_alert: bool = False):
    """Log a major event"""
    logger = get_bot_logger()
    return logger.log_major_event(event_type, description, user_id, severity, send_alert=send_alert)


def log_pack(action: str, pack_id: str, artist: str, creator_id: int, pack_type: str = 'community'):
    """Log pack event"""
    logger = get_bot_logger()
    return logger.log_pack_event(action, pack_id, artist, creator_id, pack_type)


def log_user(action: str, user_id: int, details: Optional[Dict] = None):
    """Log user action"""
    logger = get_bot_logger()
    return logger.log_user_action(action, user_id, details)


def log_restart(restart_type: str = 'manual', metadata: Optional[Dict] = None):
    """Log restart"""
    logger = get_bot_logger()
    return logger.log_restart(restart_type, metadata)


def log_error(context: str, error: Exception = None, user_id: Optional[int] = None, severity: str = 'error', send_alert: bool = True):
    """Log error"""
    logger = get_bot_logger()
    return logger.log_error(context, error, user_id, severity, send_alert=send_alert)


def log_warning(context: str, message: str, send_alert: bool = False):
    """Log warning"""
    logger = get_bot_logger()
    return logger.log_warning(context, message, send_alert=send_alert)


def log_deployment(version: str, changelog: str = None):
    """Log deployment"""
    logger = get_bot_logger()
    return logger.log_deployment(version, changelog)
