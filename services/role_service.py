"""
Role Management Service

Provides utilities for managing Discord roles, granting permissions,
and handling role-related operations.
"""

import discord
from typing import Optional, List
from config.roles import ROLES, ROLE_HIERARCHY
from services.audit_service import AuditLog

class RoleService:
    """Service for managing Discord roles and permissions."""
    
    def __init__(self, bot: discord.Client):
        self.bot = bot
    
    async def ensure_roles_exist(self, guild: discord.Guild) -> dict:
        """
        Ensure all required roles exist in the guild.
        
        Args:
            guild: Discord guild to check roles in
            
        Returns:
            Dictionary with role creation results
        """
        results = {
            "created": [],
            "existing": [],
            "errors": []
        }
        
        for role_key, role_name in ROLES.items():
            try:
                # Check if role exists
                existing_role = discord.utils.get(guild.roles, name=role_name)
                
                if existing_role:
                    results["existing"].append(role_name)
                else:
                    # Create role with appropriate permissions
                    if role_key == "admin":
                        # Admin role gets all permissions
                        permissions = discord.Permissions.all()
                        role = await guild.create_role(
                            name=role_name,
                            permissions=permissions,
                            reason="Auto-created admin role"
                        )
                    elif role_key == "moderator":
                        # Moderator role gets moderation permissions
                        permissions = discord.Permissions(
                            manage_messages=True,
                            kick_members=True,
                            ban_members=True,
                            read_message_history=True,
                            send_messages=True,
                            embed_links=True,
                            attach_files=True,
                            read_messages=True,
                            manage_channels=False,
                            manage_guild=False
                        )
                        role = await guild.create_role(
                            name=role_name,
                            permissions=permissions,
                            reason="Auto-created moderator role"
                        )
                    else:
                        # Basic role with no special permissions
                        permissions = discord.Permissions(
                            read_messages=True,
                            send_messages=True,
                            embed_links=True,
                            attach_files=True,
                            read_message_history=True
                        )
                        role = await guild.create_role(
                            name=role_name,
                            permissions=permissions,
                            reason=f"Auto-created {role_key} role"
                        )
                    
                    results["created"].append(role_name)
                    
                    AuditLog.record(
                        event="role_created",
                        user_id=self.bot.user.id,
                        target_id=role.id,
                        details={
                            "role_name": role_name,
                            "role_key": role_key,
                            "guild_id": guild.id
                        }
                    )
                    
            except discord.Forbidden:
                results["errors"].append(f"Missing permissions to create {role_name}")
            except Exception as e:
                results["errors"].append(f"Error creating {role_name}: {str(e)}")
        
        return results
    
    async def grant_role(self, member: discord.Member, role_name: str, reason: str = "Role assignment") -> bool:
        """
        Grant a role to a member.
        
        Args:
            member: Discord member to grant role to
            role_name: Name of the role to grant
            reason: Reason for the role grant
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the role
            role = discord.utils.get(member.guild.roles, name=role_name)
            if not role:
                return False
            
            # Check if member already has role
            if role in member.roles:
                return True
            
            # Grant the role
            await member.add_roles(role, reason=reason)
            
            AuditLog.record(
                event="role_granted",
                user_id=member.id,
                target_id=role.id,
                details={
                    "role_name": role_name,
                    "reason": reason,
                    "granted_by": self.bot.user.id
                }
            )
            
            return True
            
        except discord.Forbidden:
            return False
        except Exception as e:
            print(f"Error granting role {role_name} to {member}: {e}")
            return False
    
    async def revoke_role(self, member: discord.Member, role_name: str, reason: str = "Role removal") -> bool:
        """
        Revoke a role from a member.
        
        Args:
            member: Discord member to revoke role from
            role_name: Name of the role to revoke
            reason: Reason for the role removal
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the role
            role = discord.utils.get(member.guild.roles, name=role_name)
            if not role:
                return False
            
            # Check if member has the role
            if role not in member.roles:
                return True
            
            # Revoke the role
            await member.remove_roles(role, reason=reason)
            
            AuditLog.record(
                event="role_revoked",
                user_id=member.id,
                target_id=role.id,
                details={
                    "role_name": role_name,
                    "reason": reason,
                    "revoked_by": self.bot.user.id
                }
            )
            
            return True
            
        except discord.Forbidden:
            return False
        except Exception as e:
            print(f"Error revoking role {role_name} from {member}: {e}")
            return False
    
    async def grant_creator_role(self, member: discord.Member) -> bool:
        """
        Grant creator role to a member.
        
        Args:
            member: Discord member to grant creator role to
            
        Returns:
            True if successful, False otherwise
        """
        return await self.grant_role(member, ROLES["creator"], "Creator role assignment")
    
    async def grant_moderator_role(self, member: discord.Member) -> bool:
        """
        Grant moderator role to a member.
        
        Args:
            member: Discord member to grant moderator role to
            
        Returns:
            True if successful, False otherwise
        """
        return await self.grant_role(member, ROLES["moderator"], "Moderator role assignment")
    
    async def grant_admin_role(self, member: discord.Member) -> bool:
        """
        Grant admin role to a member.
        
        Args:
            member: Discord member to grant admin role to
            
        Returns:
            True if successful, False otherwise
        """
        return await self.grant_role(member, ROLES["admin"], "Admin role assignment")
    
    async def get_members_with_role(self, guild: discord.Guild, role_name: str) -> List[discord.Member]:
        """
        Get all members with a specific role.
        
        Args:
            guild: Discord guild to search in
            role_name: Name of the role to search for
            
        Returns:
            List of members with the role
        """
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            return []
        
        return [member for member in guild.members if role in member.roles]
    
    async def get_role_statistics(self, guild: discord.Guild) -> dict:
        """
        Get statistics about role distribution in the guild.
        
        Args:
            guild: Discord guild to get statistics for
            
        Returns:
            Dictionary with role statistics
        """
        stats = {}
        total_members = len(guild.members)
        
        for role_key, role_name in ROLES.items():
            members = await self.get_members_with_role(guild, role_name)
            stats[role_key] = {
                "name": role_name,
                "count": len(members),
                "percentage": round((len(members) / total_members) * 100, 2) if total_members > 0 else 0,
                "members": [str(member) for member in members[:10]]  # Limit to first 10 for display
            }
        
        stats["total_members"] = total_members
        stats["unassigned"] = total_members - sum(
            len(await self.get_members_with_role(guild, ROLES[role_key]))
            for role_key in ROLES.keys()
        )
        
        return stats
    
    async def cleanup_duplicate_roles(self, guild: discord.Guild) -> dict:
        """
        Clean up duplicate roles (same name, different case/formatting).
        
        Args:
            guild: Discord guild to clean up roles in
            
        Returns:
            Dictionary with cleanup results
        """
        results = {
            "merged": [],
            "deleted": [],
            "errors": []
        }
        
        # Group roles by lowercase name
        role_groups = {}
        for role in guild.roles:
            if role.name == "@everyone":
                continue
            
            lower_name = role.name.lower()
            if lower_name not in role_groups:
                role_groups[lower_name] = []
            role_groups[lower_name].append(role)
        
        # Process groups with duplicates
        for group_name, roles in role_groups.items():
            if len(roles) <= 1:
                continue
            
            # Keep the role with highest position (most powerful)
            main_role = max(roles, key=lambda r: r.position)
            duplicate_roles = [r for r in roles if r != main_role]
            
            # Move members from duplicates to main role
            for duplicate_role in duplicate_roles:
                try:
                    members_with_role = await self.get_members_with_role(guild, duplicate_role.name)
                    
                    for member in members_with_role:
                        await self.grant_role(member, main_role.name, "Role cleanup - duplicate merge")
                    
                    # Delete the duplicate role
                    await duplicate_role.delete(reason="Role cleanup - duplicate")
                    
                    results["merged"].append({
                        "from": duplicate_role.name,
                        "to": main_role.name,
                        "members_moved": len(members_with_role)
                    })
                    
                except Exception as e:
                    results["errors"].append(f"Error merging {duplicate_role.name}: {str(e)}")
        
        return results

# Convenience functions for common role operations
async def grant_creator(member: discord.Member) -> bool:
    """Convenience function to grant creator role."""
    # This would need bot instance, so it's a simplified version
    # In practice, you'd use RoleService instance
    role = discord.utils.get(member.guild.roles, name=ROLES["creator"])
    if role:
        try:
            await member.add_roles(role, reason="Creator role assignment")
            return True
        except:
            return False
    return False

async def grant_moderator(member: discord.Member) -> bool:
    """Convenience function to grant moderator role."""
    role = discord.utils.get(member.guild.roles, name=ROLES["moderator"])
    if role:
        try:
            await member.add_roles(role, reason="Moderator role assignment")
            return True
        except:
            return False
    return False

async def grant_admin(member: discord.Member) -> bool:
    """Convenience function to grant admin role."""
    role = discord.utils.get(member.guild.roles, name=ROLES["admin"])
    if role:
        try:
            await member.add_roles(role, reason="Admin role assignment")
            return True
        except:
            return False
    return False
