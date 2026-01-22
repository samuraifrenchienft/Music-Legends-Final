"""
Permission Middleware

Provides decorators and middleware functions for role-based access control.
Integrates with Discord.py commands and UI components.
"""

import discord
from functools import wraps
from typing import Callable, Optional, List
from config.roles import ROLES, ROLE_HIERARCHY, has_permission, can_access_command
from services.audit_service import AuditLog

def require_role(role_name: str):
    """
    Decorator to require a specific Discord role for command access.
    
    Args:
        role_name: The role name required (from config.roles.ROLES)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            # Get the Discord role object
            required_role_name = ROLES.get(role_name)
            if not required_role_name:
                await ctx.respond(
                    "⚠️ Configuration error: Role not found.",
                    ephemeral=True
                )
                return
            
            role = discord.utils.get(ctx.author.roles, name=required_role_name)
            
            if not role:
                # Log permission denial
                AuditLog.record(
                    event="permission_denied",
                    user_id=ctx.author.id,
                    target_id=ctx.command.name,
                    details={
                        "required_role": role_name,
                        "command": ctx.command.name,
                        "channel_id": ctx.channel.id,
                        "guild_id": ctx.guild.id if ctx.guild else None
                    }
                )
                
                await ctx.respond(
                    f"🚫 You need the **{required_role_name}** role to use this command.",
                    ephemeral=True
                )
                return
            
            # Log successful permission check
            AuditLog.record(
                event="permission_granted",
                user_id=ctx.author.id,
                target_id=ctx.command.name,
                details={
                    "role": role_name,
                    "command": ctx.command.name
                }
            )
            
            return await func(ctx, *args, **kwargs)
        return wrapper
    return decorator

def require_permission(permission: str):
    """
    Decorator to require a specific permission for command access.
    
    Args:
        permission: The permission string required
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            # Get user's highest role
            user_role = None
            highest_level = -1
            
            for role_enum, role_name in ROLES.items():
                discord_role = discord.utils.get(ctx.author.roles, name=role_name)
                if discord_role:
                    level = ROLE_HIERARCHY.get(role_enum, -1)
                    if level > highest_level:
                        highest_level = level
                        user_role = role_enum
            
            if not user_role or not has_permission(user_role, permission):
                AuditLog.record(
                    event="permission_denied",
                    user_id=ctx.author.id,
                    target_id=ctx.command.name,
                    details={
                        "required_permission": permission,
                        "user_role": user_role,
                        "command": ctx.command.name
                    }
                )
                
                await ctx.respond(
                    f"🚫 You need the `{permission}` permission to use this command.",
                    ephemeral=True
                )
                return
            
            AuditLog.record(
                event="permission_granted",
                user_id=ctx.author.id,
                target_id=ctx.command.name,
                details={
                    "permission": permission,
                    "user_role": user_role,
                    "command": ctx.command.name
                }
            )
            
            return await func(ctx, *args, **kwargs)
        return wrapper
    return decorator

def require_any_role(roles: List[str]):
    """
    Decorator to require any of multiple roles for command access.
    
    Args:
        roles: List of role names (any one will grant access)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            user_has_role = False
            matched_role = None
            
            for role_name in roles:
                required_role_name = ROLES.get(role_name)
                if required_role_name:
                    role = discord.utils.get(ctx.author.roles, name=required_role_name)
                    if role:
                        user_has_role = True
                        matched_role = role_name
                        break
            
            if not user_has_role:
                required_role_names = [ROLES.get(r, r) for r in roles]
                AuditLog.record(
                    event="permission_denied",
                    user_id=ctx.author.id,
                    target_id=ctx.command.name,
                    details={
                        "required_roles": roles,
                        "command": ctx.command.name
                    }
                )
                
                await ctx.respond(
                    f"🚫 You need one of these roles: {', '.join(f'**{name}**' for name in required_role_names)}",
                    ephemeral=True
                )
                return
            
            AuditLog.record(
                event="permission_granted",
                user_id=ctx.author.id,
                target_id=ctx.command.name,
                details={
                    "matched_role": matched_role,
                    "command": ctx.command.name
                }
            )
            
            return await func(ctx, *args, **kwargs)
        return wrapper
    return decorator

def admin_only(func: Callable):
    """Shortcut decorator for admin-only commands."""
    return require_role("admin")(func)

def moderator_only(func: Callable):
    """Shortcut decorator for moderator-only commands."""
    return require_role("moderator")(func)

def creator_only(func: Callable):
    """Shortcut decorator for creator-only commands."""
    return require_role("creator")(func)

async def check_user_permissions(member: discord.Member) -> dict:
    """
    Check all permissions for a user and return their role info.
    
    Args:
        member: Discord member to check
        
    Returns:
        Dictionary with role information and permissions
    """
    user_role = None
    highest_level = -1
    user_permissions = []
    
    # Find highest role
    for role_enum, role_name in ROLES.items():
        discord_role = discord.utils.get(member.roles, name=role_name)
        if discord_role:
            level = ROLE_HIERARCHY.get(role_enum, -1)
            if level > highest_level:
                highest_level = level
                user_role = role_enum
    
    # Get permissions for that role
    if user_role:
        from config.roles import get_role_permissions
        user_permissions = get_role_permissions(user_role)
    
    return {
        "user_id": member.id,
        "username": str(member),
        "role": user_role or "player",
        "role_level": highest_level,
        "permissions": user_permissions,
        "has_admin_role": discord.utils.get(member.roles, name=ROLES.get("admin")) is not None,
        "has_moderator_role": discord.utils.get(member.roles, name=ROLES.get("moderator")) is not None,
        "has_creator_role": discord.utils.get(member.roles, name=ROLES.get("creator")) is not None
    }

class PermissionChecker:
    """Utility class for checking permissions in various contexts."""
    
    @staticmethod
    async def can_review_packs(member: discord.Member) -> bool:
        """Check if member can review creator packs."""
        role = discord.utils.get(member.roles, name=ROLES.get("moderator"))
        return role is not None
    
    @staticmethod
    async def can_submit_packs(member: discord.Member) -> bool:
        """Check if member can submit creator packs."""
        role = discord.utils.get(member.roles, name=ROLES.get("creator"))
        return role is not None
    
    @staticmethod
    async def can_manage_economy(member: discord.Member) -> bool:
        """Check if member can manage economy (admin)."""
        role = discord.utils.get(member.roles, name=ROLES.get("admin"))
        return role is not None
    
    @staticmethod
    async def can_ban_users(member: discord.Member) -> bool:
        """Check if member can ban users (admin)."""
        role = discord.utils.get(member.roles, name=ROLES.get("admin"))
        return role is not None
    
    @staticmethod
    async def get_user_role_level(member: discord.Member) -> int:
        """Get the permission level of a user."""
        highest_level = 0
        
        for role_enum, role_name in ROLES.items():
            discord_role = discord.utils.get(member.roles, name=role_name)
            if discord_role:
                level = ROLE_HIERARCHY.get(role_enum, 0)
                if level > highest_level:
                    highest_level = level
        
        return highest_level
