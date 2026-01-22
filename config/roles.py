"""
Role Configuration System

Defines the permission hierarchy and role mappings for the Discord bot.
This system ensures proper access control across different user types.
"""

from typing import Dict, List
from enum import Enum

class UserRole(Enum):
    """User role enumeration for type safety and clarity."""
    PLAYER = "player"
    CREATOR = "creator"
    MODERATOR = "moderator"
    ADMIN = "admin"

# Discord role name mappings
ROLES = {
    UserRole.PLAYER.value: "Player",
    UserRole.CREATOR.value: "Creator", 
    UserRole.MODERATOR.value: "Mod",
    UserRole.ADMIN.value: "Admin"
}

# Role hierarchy for permission inheritance
ROLE_HIERARCHY = {
    UserRole.PLAYER.value: 0,
    UserRole.CREATOR.value: 1,
    UserRole.MODERATOR.value: 2,
    UserRole.ADMIN.value: 3
}

# Permission sets for each role
PERMISSIONS = {
    UserRole.PLAYER.value: [
        "pack_open",
        "trade", 
        "collect",
        "view_collection",
        "view_dashboard"
    ],
    UserRole.CREATOR.value: [
        "pack_open",
        "trade",
        "collect", 
        "view_collection",
        "view_dashboard",
        "submit_pack",
        "edit_own_pack",
        "delete_own_pack"
    ],
    UserRole.MODERATOR.value: [
        "pack_open",
        "trade",
        "collect",
        "view_collection", 
        "view_dashboard",
        "submit_pack",
        "edit_own_pack",
        "delete_own_pack",
        "review_pack",
        "approve_pack",
        "reject_pack",
        "view_audit_log"
    ],
    UserRole.ADMIN.value: [
        "pack_open",
        "trade", 
        "collect",
        "view_collection",
        "view_dashboard",
        "submit_pack", 
        "edit_own_pack",
        "delete_own_pack",
        "review_pack",
        "approve_pack",
        "reject_pack",
        "view_audit_log",
        "refund_payment",
        "ban_user",
        "manage_economy",
        "manage_roles",
        "system_admin"
    ]
}

# Command role mappings
COMMAND_ROLES = {
    # Creator commands
    "creator": UserRole.CREATOR.value,
    "submit_pack": UserRole.CREATOR.value,
    "edit_pack": UserRole.CREATOR.value,
    
    # Moderator commands  
    "review": UserRole.MODERATOR.value,
    "approve": UserRole.MODERATOR.value,
    "reject": UserRole.MODERATOR.value,
    "audit_log": UserRole.MODERATOR.value,
    
    # Admin commands
    "refund": UserRole.ADMIN.value,
    "ban": UserRole.ADMIN.value,
    "unban": UserRole.ADMIN.value,
    "economy": UserRole.ADMIN.value,
    "admin_panel": UserRole.ADMIN.value,
    "manage_roles": UserRole.ADMIN.value,
    
    # Player commands (default access)
    "packs": UserRole.PLAYER.value,
    "collection": UserRole.PLAYER.value,
    "dashboard": UserRole.PLAYER.value,
    "trade": UserRole.PLAYER.value
}

def get_role_permissions(role_name: str) -> List[str]:
    """Get permission list for a role."""
    return PERMISSIONS.get(role_name, [])

def has_permission(user_role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    return permission in get_role_permissions(user_role)

def can_access_command(user_role: str, command_name: str) -> bool:
    """Check if a role can access a specific command."""
    required_role = COMMAND_ROLES.get(command_name, UserRole.PLAYER.value)
    return ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get(required_role, 0)

def get_higher_role(role1: str, role2: str) -> str:
    """Get the higher of two roles based on hierarchy."""
    level1 = ROLE_HIERARCHY.get(role1, 0)
    level2 = ROLE_HIERARCHY.get(role2, 0)
    return role1 if level1 >= level2 else role2

def is_admin(role_name: str) -> bool:
    """Check if role is admin level."""
    return ROLE_HIERARCHY.get(role_name, 0) >= ROLE_HIERARCHY[UserRole.ADMIN.value]

def is_moderator(role_name: str) -> bool:
    """Check if role is moderator level or higher."""
    return ROLE_HIERARCHY.get(role_name, 0) >= ROLE_HIERARCHY[UserRole.MODERATOR.value]

def is_creator(role_name: str) -> bool:
    """Check if role is creator level or higher."""
    return ROLE_HIERARCHY.get(role_name, 0) >= ROLE_HIERARCHY[UserRole.CREATOR.value]
