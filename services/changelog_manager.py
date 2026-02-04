"""
Changelog Manager - Track significant system changes and events
Provides audit trail, change logging, and system alerting
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import asyncio
import logging

logger = logging.getLogger(__name__)


class ChangeLogManager:
    """
    Manages system change logging with Discord notifications
    Tracks: pack creation, card updates, system events, user actions
    """
    
    def __init__(self, log_path: str = 'logs/change_log.json', bot=None):
        """
        Initialize changelog manager
        
        Args:
            log_path: Path to changelog JSON file
            bot: Discord bot instance for sending alerts
        """
        self.log_path = log_path
        self.bot = bot
        
        # Ensure log directory exists
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Category severity levels
        self.SEVERITY_LEVELS = {
            'critical': '🔴',    # System failures, security issues
            'high': '🟠',        # Major changes, pack creation
            'medium': '🟡',      # Moderate changes, user actions
            'low': '⚪',         # Minor changes, info logs
        }
        
        # Change categories
        self.CATEGORIES = {
            'pack_creation': 'Pack Creation',
            'card_generation': 'Card Generation',
            'user_action': 'User Action',
            'system_event': 'System Event',
            'error': 'Error',
            'security': 'Security Event',
            'payment': 'Payment',
            'admin_action': 'Admin Action',
            'deployment': 'Deployment',
            'database': 'Database',
        }
    
    def log_change(
        self,
        category: str,
        description: str,
        user_id: Optional[int] = None,
        severity: str = 'medium',
        metadata: Optional[Dict[str, Any]] = None,
        send_alert: bool = False
    ) -> bool:
        """
        Log significant changes to the system
        
        Args:
            category: Category of change (pack_creation, card_generation, etc.)
            description: Human-readable description
            user_id: Optional user ID who triggered change
            severity: Severity level (critical, high, medium, low)
            metadata: Additional context/data
            send_alert: Whether to send Discord alert
            
        Returns:
            bool: Success status
        """
        try:
            change_entry = {
                'timestamp': datetime.now().isoformat(),
                'category': category,
                'category_name': self.CATEGORIES.get(category, category),
                'description': description,
                'user_id': user_id,
                'severity': severity,
                'severity_emoji': self.SEVERITY_LEVELS.get(severity, '⚪'),
                'metadata': metadata or {}
            }
            
            # Append to change log file
            with open(self.log_path, 'a') as log_file:
                json.dump(change_entry, log_file)
                log_file.write('\n')
            
            logger.info(f"[CHANGELOG] {category}: {description}")
            
            # Send alert via webhook if requested
            if send_alert:
                asyncio.create_task(self._send_webhook_alert(change_entry))
            
            return True
            
        except Exception as e:
            logger.error(f"Error logging change: {e}")
            return False
    
    async def _send_webhook_alert(self, change_entry: Dict[str, Any]) -> None:
        """
        Send changelog alert to webhook channel
        
        Args:
            change_entry: Change log entry to alert about
        """
        try:
            from monitor.alerts import send_econ
            
            severity_emoji = change_entry['severity_emoji']
            
            changelog_msg = f"{severity_emoji} **{change_entry['category_name']}**\n"
            changelog_msg += f"{change_entry['description']}\n"
            
            if change_entry['user_id']:
                changelog_msg += f"**User:** `{change_entry['user_id']}`\n"
            
            if change_entry['metadata']:
                meta_items = list(change_entry['metadata'].items())[:3]
                meta_str = ', '.join([f"{k}: {v}" for k, v in meta_items])
                changelog_msg += f"**Details:** {meta_str}"
            
            # Map severity to alert level
            level_map = {
                'critical': 'red',
                'high': 'orange',
                'medium': 'yellow',
                'low': 'info'
            }
            
            await send_econ(
                f"{severity_emoji} Changelog",
                changelog_msg,
                level_map.get(change_entry['severity'], 'info')
            )
        
        except Exception as e:
            logger.error(f"Error sending webhook alert: {e}")
    
    def _severity_to_color(self, severity: str) -> int:
        """Convert severity to Discord embed color"""
        import discord
        
        colors = {
            'critical': discord.Color.red(),
            'high': discord.Color.orange(),
            'medium': discord.Color.yellow(),
            'low': discord.Color.grey(),
        }
        return colors.get(severity, discord.Color.grey())
    
    def get_changes(
        self,
        category: Optional[str] = None,
        user_id: Optional[int] = None,
        limit: int = 100,
        severity: Optional[str] = None
    ) -> list:
        """
        Retrieve changes from log file
        
        Args:
            category: Filter by category
            user_id: Filter by user
            limit: Maximum entries to return
            severity: Filter by severity level
            
        Returns:
            List of change entries
        """
        try:
            changes = []
            
            if not Path(self.log_path).exists():
                return changes
            
            with open(self.log_path, 'r') as log_file:
                for line in log_file:
                    if not line.strip():
                        continue
                    
                    try:
                        entry = json.loads(line)
                        
                        # Apply filters
                        if category and entry.get('category') != category:
                            continue
                        if user_id and entry.get('user_id') != user_id:
                            continue
                        if severity and entry.get('severity') != severity:
                            continue
                        
                        changes.append(entry)
                    
                    except json.JSONDecodeError:
                        continue
            
            # Return most recent entries
            return sorted(changes, key=lambda x: x['timestamp'], reverse=True)[:limit]
        
        except Exception as e:
            logger.error(f"Error reading changes: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about logged changes"""
        try:
            changes = self.get_changes(limit=10000)
            
            if not changes:
                return {'total': 0, 'by_category': {}, 'by_severity': {}}
            
            stats = {
                'total': len(changes),
                'by_category': {},
                'by_severity': {},
                'last_change': changes[0]['timestamp'] if changes else None,
                'first_change': changes[-1]['timestamp'] if changes else None,
            }
            
            for change in changes:
                cat = change.get('category', 'unknown')
                sev = change.get('severity', 'medium')
                
                stats['by_category'][cat] = stats['by_category'].get(cat, 0) + 1
                stats['by_severity'][sev] = stats['by_severity'].get(sev, 0) + 1
            
            return stats
        
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'total': 0}
    
    def clear_old_entries(self, days: int = 90) -> int:
        """
        Remove changelog entries older than specified days
        
        Args:
            days: Delete entries older than this many days
            
        Returns:
            Number of entries removed
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days)
            changes = self.get_changes(limit=10000)
            
            kept_entries = [
                c for c in changes
                if datetime.fromisoformat(c['timestamp']) > cutoff_date
            ]
            
            removed_count = len(changes) - len(kept_entries)
            
            # Rewrite log file with kept entries
            with open(self.log_path, 'w') as log_file:
                for entry in kept_entries:
                    json.dump(entry, log_file)
                    log_file.write('\n')
            
            logger.info(f"Removed {removed_count} old changelog entries")
            return removed_count
        
        except Exception as e:
            logger.error(f"Error clearing old entries: {e}")
            return 0


# Global instance
_changelog_manager: Optional[ChangeLogManager] = None


def get_changelog_manager(bot=None) -> ChangeLogManager:
    """Get or create global changelog manager instance"""
    global _changelog_manager
    
    if _changelog_manager is None:
        _changelog_manager = ChangeLogManager(bot=bot)
    
    return _changelog_manager


# Convenience functions
def log_pack_creation(pack_id: str, artist_name: str, creator_id: int, pack_type: str = 'community'):
    """Log pack creation event"""
    manager = get_changelog_manager()
    manager.log_change(
        category='pack_creation',
        description=f"Pack created: {artist_name} ({pack_type})",
        user_id=creator_id,
        severity='high',
        metadata={
            'pack_id': pack_id,
            'artist': artist_name,
            'type': pack_type,
        },
        send_alert=True
    )


def log_card_generation(pack_id: str, card_count: int, creator_id: int):
    """Log card generation event"""
    manager = get_changelog_manager()
    manager.log_change(
        category='card_generation',
        description=f"Generated {card_count} cards for pack",
        user_id=creator_id,
        severity='high',
        metadata={
            'pack_id': pack_id,
            'card_count': card_count,
        },
        send_alert=True
    )


def log_user_action(action: str, user_id: int, details: Optional[Dict] = None):
    """Log user action"""
    manager = get_changelog_manager()
    manager.log_change(
        category='user_action',
        description=f"User action: {action}",
        user_id=user_id,
        severity='low',
        metadata=details or {},
    )


def log_system_event(event_type: str, description: str, severity: str = 'medium', metadata: Optional[Dict] = None):
    """Log system event"""
    manager = get_changelog_manager()
    manager.log_change(
        category='system_event',
        description=description,
        severity=severity,
        metadata=metadata or {},
        send_alert=severity in ['critical', 'high']
    )


def log_error(error_type: str, error_message: str, severity: str = 'high', metadata: Optional[Dict] = None):
    """Log system error"""
    manager = get_changelog_manager()
    manager.log_change(
        category='error',
        description=f"{error_type}: {error_message}",
        severity=severity,
        metadata=metadata or {},
        send_alert=True
    )
