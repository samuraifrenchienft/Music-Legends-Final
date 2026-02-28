# dev_authorization.py
"""
Secure developer authorization and access control system
- Strict authorization checks for dev-only commands
- Security event logging for audit trails
- Role-based access control
- Rate limiting on failed attempts
"""

import discord
from discord.ext import commands
from discord import app_commands, Interaction
from typing import Optional, Callable
from datetime import datetime, timedelta
from functools import wraps
import json
from pathlib import Path

from config import settings


# ==========================================
# SECURITY EVENT LOGGING
# ==========================================

class SecurityLogger:
    """Log security-related events for audit trails"""
    
    def __init__(self, log_file: str = "logs/security_audit.log"):
        self.log_file = log_file
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        print(f"🔐 [SECURITY] Security logger initialized: {log_file}")
    
    def log_event(self, event_type: str, user_id: int, details: dict = None, severity: str = "INFO"):
        """Log a security event"""
        timestamp = datetime.now().isoformat()
        details = details or {}
        
        log_entry = {
            "timestamp": timestamp,
            "severity": severity,
            "event_type": event_type,
            "user_id": str(user_id),
            "details": details
        }
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            # Also print to console for immediate visibility
            severity_emoji = {
                "INFO": "ℹ️",
                "WARNING": "⚠️",
                "CRITICAL": "🚨"
            }.get(severity, "ℹ️")
            
            print(f"{severity_emoji} [SECURITY] [{event_type}] User: {user_id} | {details}")
            
        except Exception as e:
            print(f"❌ [SECURITY] Failed to log security event: {e}")
    
    def get_audit_trail(self, user_id: int = None, hours: int = 24) -> list:
        """Get audit trail for a user or all users"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            events = []
            
            with open(self.log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        entry_time = datetime.fromisoformat(entry['timestamp'])
                        
                        if entry_time < cutoff_time:
                            continue
                        
                        if user_id is None or entry['user_id'] == str(user_id):
                            events.append(entry)
                    except json.JSONDecodeError:
                        continue
            
            return events
        except Exception as e:
            print(f"❌ [SECURITY] Failed to retrieve audit trail: {e}")
            return []


# Global security logger
security_logger = SecurityLogger()


# ==========================================
# DEV AUTHORIZATION
# ==========================================

class DevAuthorization:
    """Manage developer authorization with multiple verification methods"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.failed_attempts = {}  # Track failed authorization attempts
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
        print(f"🔐 [AUTH] Dev authorization system initialized")
    
    def is_user_locked_out(self, user_id: int) -> bool:
        """Check if user is locked out due to failed attempts"""
        if user_id not in self.failed_attempts:
            return False
        
        last_attempt, count = self.failed_attempts[user_id]
        
        # Reset if lockout period expired
        if datetime.now() - last_attempt > self.lockout_duration:
            del self.failed_attempts[user_id]
            return False
        
        # Check if exceeded max attempts
        if count >= self.max_failed_attempts:
            print(f"🚨 [AUTH] User {user_id} is locked out (failed attempts: {count})")
            return True
        
        return False
    
    def record_failed_attempt(self, user_id: int):
        """Record a failed authorization attempt"""
        if user_id not in self.failed_attempts:
            self.failed_attempts[user_id] = (datetime.now(), 0)
        
        last_attempt, count = self.failed_attempts[user_id]
        self.failed_attempts[user_id] = (datetime.now(), count + 1)
        
        security_logger.log_event(
            "FAILED_DEV_AUTH",
            user_id,
            {"attempt_count": count + 1},
            severity="WARNING"
        )
    
    def reset_failed_attempts(self, user_id: int):
        """Reset failed attempts counter for user"""
        if user_id in self.failed_attempts:
            del self.failed_attempts[user_id]
    
    def get_dev_user_ids(self) -> list[int]:
        """Get list of authorized dev user IDs from config"""
        dev_ids = settings.DEV_USER_IDS
        if not dev_ids:
            print("⚠️  [AUTH] DEV_USER_IDS environment variable not set or empty")
        else:
            print(f"✅ [AUTH] Loaded {len(dev_ids)} authorized dev IDs")
        return dev_ids
    
    async def is_authorized_dev(self, user_id: int, guild: discord.Guild = None) -> bool:
        """
        Comprehensive dev authorization check
        
        Verification methods (in order):
        1. Check against DEV_USER_IDS environment variable (primary)
        2. Check Discord server roles (Administrator, Owner)
        3. Check bot owner status
        
        Args:
            user_id: Discord user ID to check
            guild: Optional guild context for role checking
            
        Returns:
            True if user is authorized, False otherwise
        """
        
        # Check if user is locked out
        if self.is_user_locked_out(user_id):
            print(f"🚨 [AUTH] Rejecting {user_id} - user is locked out")
            security_logger.log_event(
                "LOCKED_OUT_ACCESS_ATTEMPT",
                user_id,
                {"reason": "Too many failed attempts"},
                severity="CRITICAL"
            )
            return False
        
        print(f"🔐 [AUTH] Checking authorization for user: {user_id}")
        
        try:
            # Method 1: Check DEV_USER_IDS environment variable
            dev_ids = self.get_dev_user_ids()
            if user_id in dev_ids:
                print(f"✅ [AUTH] User {user_id} authorized (DEV_USER_IDS)")
                self.reset_failed_attempts(user_id)
                security_logger.log_event(
                    "AUTHORIZED_DEV_ACCESS",
                    user_id,
                    {"method": "DEV_USER_IDS"},
                    severity="INFO"
                )
                return True
            
            # Method 2: Check Discord roles (if guild provided)
            if guild:
                member = guild.get_member(user_id)
                if member:
                    admin_roles = ['Owner', 'Administrator', 'Admin']
                    user_roles = [role.name for role in member.roles]
                    
                    if any(role in admin_roles for role in user_roles):
                        print(f"✅ [AUTH] User {user_id} authorized (Discord admin role)")
                        self.reset_failed_attempts(user_id)
                        security_logger.log_event(
                            "AUTHORIZED_DEV_ACCESS",
                            user_id,
                            {"method": "Discord_Roles", "roles": user_roles},
                            severity="INFO"
                        )
                        return True
            
            # Method 3: Check if bot owner
            app_info = await self.bot.application_info()
            if app_info.owner and user_id == app_info.owner.id:
                print(f"✅ [AUTH] User {user_id} authorized (bot owner)")
                self.reset_failed_attempts(user_id)
                security_logger.log_event(
                    "AUTHORIZED_DEV_ACCESS",
                    user_id,
                    {"method": "Bot_Owner"},
                    severity="INFO"
                )
                return True
            
            # Authorization failed
            print(f"❌ [AUTH] User {user_id} NOT authorized")
            self.record_failed_attempt(user_id)
            
            return False
            
        except Exception as e:
            print(f"❌ [AUTH] Authorization check error: {type(e).__name__}: {e}")
            security_logger.log_event(
                "AUTH_CHECK_ERROR",
                user_id,
                {"error": str(e)},
                severity="CRITICAL"
            )
            return False


# ==========================================
# DECORATORS FOR DEV-ONLY COMMANDS
# ==========================================

def dev_only(dev_auth: DevAuthorization):
    """
    Decorator for dev-only slash commands
    
    Usage:
        @app_commands.command(name="admin_panel")
        @dev_only(dev_auth)
        async def admin_panel(interaction: Interaction):
            # Dev-only functionality
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(interaction: Interaction, *args, **kwargs):
            is_authorized = await dev_auth.is_authorized_dev(
                interaction.user.id,
                guild=interaction.guild
            )
            
            if not is_authorized:
                print(f"🚨 [AUTH] Unauthorized access attempt by {interaction.user.id}")
                security_logger.log_event(
                    "UNAUTHORIZED_DEV_COMMAND_ACCESS",
                    interaction.user.id,
                    {
                        "command": func.__name__,
                        "guild": interaction.guild.name if interaction.guild else "DM"
                    },
                    severity="CRITICAL"
                )
                
                await interaction.response.send_message(
                    "❌ **Unauthorized Access**\n\n"
                    "This command is only available to authorized developers.\n"
                    "Unauthorized access attempts are logged.",
                    ephemeral=True
                )
                return
            
            # User is authorized - execute command
            try:
                return await func(interaction, *args, **kwargs)
            except Exception as e:
                print(f"❌ [AUTH] Error in dev command: {e}")
                security_logger.log_event(
                    "DEV_COMMAND_ERROR",
                    interaction.user.id,
                    {"command": func.__name__, "error": str(e)},
                    severity="WARNING"
                )
                
                await interaction.response.send_message(
                    f"❌ Error executing command: `{str(e)[:100]}`",
                    ephemeral=True
                )
        
        return wrapper
    return decorator


# ==========================================
# HELPER FUNCTIONS FOR COMMANDS
# ==========================================

async def get_security_audit_report(
    user_id: int,
    hours: int = 24
) -> discord.Embed:
    """Generate a security audit report embed"""
    events = security_logger.get_audit_trail(user_id, hours)
    
    embed = discord.Embed(
        title="🔐 Security Audit Report",
        description=f"User: <@{user_id}> | Last {hours} hours",
        color=discord.Color.red()
    )
    
    if not events:
        embed.add_field(
            name="Events",
            value="No security events found",
            inline=False
        )
        return embed
    
    # Group events by type
    events_by_type = {}
    for event in events:
        event_type = event.get('event_type', 'Unknown')
        if event_type not in events_by_type:
            events_by_type[event_type] = []
        events_by_type[event_type].append(event)
    
    # Add to embed
    for event_type, type_events in events_by_type.items():
        embed.add_field(
            name=f"{event_type} ({len(type_events)})",
            value="\n".join([f"• {e.get('timestamp', 'Unknown')[:19]}" for e in type_events[:5]]),
            inline=False
        )
    
    return embed
