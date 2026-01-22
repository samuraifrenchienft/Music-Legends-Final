"""
Role Management Commands

Commands for managing user roles and permissions.
Includes commands for granting roles, checking permissions, and role administration.
"""

import discord
from discord import SlashCommandOptionType
from discord.ext import commands
from discord.ui import View, Button, Modal, InputText
from middleware.permissions import require_role, admin_only, moderator_only
from services.role_service import RoleService
from services.audit_service import AuditLog
from config.roles import ROLES, get_role_permissions

class RoleGrantModal(Modal):
    """Modal for granting a role to a user."""
    
    def __init__(self, bot, target_user: discord.Member, role_name: str):
        super().__init__(title=f"Grant {role_name} Role")
        self.bot = bot
        self.target_user = target_user
        self.role_name = role_name
        
        self.add_item(InputText(
            label="Reason",
            placeholder="Enter reason for granting this role...",
            style=discord.InputTextStyle.long,
            required=True,
            max_length=500
        ))
    
    async def on_submit(self, interaction: discord.Interaction):
        reason = self.children[0].value
        
        # Grant the role
        role_service = RoleService(self.bot)
        success = await role_service.grant_role(self.target_user, self.role_name, reason)
        
        if success:
            await interaction.response.send_message(
                f"✅ Successfully granted **{self.role_name}** role to {self.target_user.mention}",
                ephemeral=True
            )
            
            AuditLog.record(
                event="role_granted",
                user_id=interaction.user.id,
                target_id=self.target_user.id,
                details={
                    "role_name": self.role_name,
                    "reason": reason,
                    "granted_by": interaction.user.id
                }
            )
        else:
            await interaction.response.send_message(
                f"❌ Failed to grant **{self.role_name}** role to {self.target_user.mention}",
                ephemeral=True
            )

class RoleRevokeModal(Modal):
    """Modal for revoking a role from a user."""
    
    def __init__(self, bot, target_user: discord.Member, role_name: str):
        super().__init__(title=f"Revoke {role_name} Role")
        self.bot = bot
        self.target_user = target_user
        self.role_name = role_name
        
        self.add_item(InputText(
            label="Reason",
            placeholder="Enter reason for revoking this role...",
            style=discord.InputTextStyle.long,
            required=True,
            max_length=500
        ))
    
    async def on_submit(self, interaction: discord.Interaction):
        reason = self.children[0].value
        
        # Revoke the role
        role_service = RoleService(self.bot)
        success = await role_service.revoke_role(self.target_user, self.role_name, reason)
        
        if success:
            await interaction.response.send_message(
                f"✅ Successfully revoked **{self.role_name}** role from {self.target_user.mention}",
                ephemeral=True
            )
            
            AuditLog.record(
                event="role_revoked",
                user_id=interaction.user.id,
                target_id=self.target_user.id,
                details={
                    "role_name": self.role_name,
                    "reason": reason,
                    "revoked_by": interaction.user.id
                }
            )
        else:
            await interaction.response.send_message(
                f"❌ Failed to revoke **{self.role_name}** role from {self.target_user.mention}",
                ephemeral=True
            )

class RoleManagementView(View):
    """View for role management actions."""
    
    def __init__(self, bot, target_user: discord.Member):
        super().__init__(timeout=None)
        self.bot = bot
        self.target_user = target_user
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow admins to use role management."""
        role = discord.utils.get(interaction.user.roles, name=ROLES.get("admin"))
        if not role:
            await interaction.response.send_message(
                "🚫 Only admins can manage roles.",
                ephemeral=True
            )
            return False
        return True
    
    @discord.ui.button(label="Grant Creator", style=discord.ButtonStyle.green)
    async def grant_creator(self, interaction: discord.Interaction, button: Button):
        modal = RoleGrantModal(self.bot, self.target_user, ROLES["creator"])
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Grant Moderator", style=discord.ButtonStyle.green)
    async def grant_moderator(self, interaction: discord.Interaction, button: Button):
        modal = RoleGrantModal(self.bot, self.target_user, ROLES["moderator"])
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Grant Admin", style=discord.ButtonStyle.green)
    async def grant_admin(self, interaction: discord.Interaction, button: Button):
        modal = RoleGrantModal(self.bot, self.target_user, ROLES["admin"])
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Revoke Creator", style=discord.ButtonStyle.red)
    async def revoke_creator(self, interaction: discord.Interaction, button: Button):
        modal = RoleRevokeModal(self.bot, self.target_user, ROLES["creator"])
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Revoke Moderator", style=discord.ButtonStyle.red)
    async def revoke_moderator(self, interaction: discord.Interaction, button: Button):
        modal = RoleRevokeModal(self.bot, self.target_user, ROLES["moderator"])
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Revoke Admin", style=discord.ButtonStyle.red)
    async def revoke_admin(self, interaction: discord.Interaction, button: Button):
        modal = RoleRevokeModal(self.bot, self.target_user, ROLES["admin"])
        await interaction.response.send_modal(modal)

class RoleCommands(commands.Cog):
    """Role management commands."""
    
    def __init__(self, bot):
        self.bot = bot
        self.role_service = RoleService(bot)
    
    @commands.slash_command(name="myroles", description="Check your current roles and permissions")
    async def my_roles(self, ctx: discord.ApplicationContext):
        """Show user's current roles and permissions."""
        from middleware.permissions import check_user_permissions
        
        perms = await check_user_permissions(ctx.author)
        
        embed = discord.Embed(
            title="🔐 Your Roles & Permissions",
            color=discord.Color.blue()
        )
        
        # Current role
        embed.add_field(
            name="Current Role",
            value=f"**{perms['role'].title()}** (Level {perms['role_level']})",
            inline=False
        )
        
        # Permissions list
        if perms['permissions']:
            perm_text = "\n".join(f"• `{perm}`" for perm in perms['permissions'])
            embed.add_field(
                name="Permissions",
                value=perm_text,
                inline=False
            )
        else:
            embed.add_field(
                name="Permissions",
                value="No special permissions",
                inline=False
            )
        
        # Role status
        role_status = []
        if perms['has_creator_role']:
            role_status.append("✅ Creator")
        if perms['has_moderator_role']:
            role_status.append("✅ Moderator")
        if perms['has_admin_role']:
            role_status.append("✅ Admin")
        
        if role_status:
            embed.add_field(
                name="Role Status",
                value="\n".join(role_status),
                inline=False
            )
        
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.respond(embed=embed, ephemeral=True)
    
    @commands.slash_command(name="checkroles", description="Check roles and permissions for a user")
    @require_role("moderator")
    async def check_roles(
        self, 
        ctx: discord.ApplicationContext,
        user: discord.Option(discord.Member, description="User to check")
    ):
        """Check roles and permissions for a specific user."""
        from middleware.permissions import check_user_permissions
        
        perms = await check_user_permissions(user)
        
        embed = discord.Embed(
            title=f"🔐 {user.display_name}'s Roles & Permissions",
            color=discord.Color.blue()
        )
        
        # Current role
        embed.add_field(
            name="Current Role",
            value=f"**{perms['role'].title()}** (Level {perms['role_level']})",
            inline=False
        )
        
        # Permissions list
        if perms['permissions']:
            perm_text = "\n".join(f"• `{perm}`" for perm in perms['permissions'])
            embed.add_field(
                name="Permissions",
                value=perm_text,
                inline=False
            )
        else:
            embed.add_field(
                name="Permissions",
                value="No special permissions",
                inline=False
            )
        
        # Role status
        role_status = []
        if perms['has_creator_role']:
            role_status.append("✅ Creator")
        if perms['has_moderator_role']:
            role_status.append("✅ Moderator")
        if perms['has_admin_role']:
            role_status.append("✅ Admin")
        
        if role_status:
            embed.add_field(
                name="Role Status",
                value="\n".join(role_status),
                inline=False
            )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        await ctx.respond(embed=embed, ephemeral=True)
    
    @commands.slash_command(name="manageroles", description="Manage roles for a user")
    @admin_only
    async def manage_roles(
        self, 
        ctx: discord.ApplicationContext,
        user: discord.Option(discord.Member, description="User to manage roles for")
    ):
        """Open role management interface for a user."""
        view = RoleManagementView(self.bot, user)
        
        embed = discord.Embed(
            title=f"🔧 Role Management: {user.display_name}",
            description="Use the buttons below to grant or revoke roles for this user.",
            color=discord.Color.orange()
        )
        
        # Show current roles
        current_roles = []
        for role_name in ROLES.values():
            role = discord.utils.get(user.roles, name=role_name)
            if role:
                current_roles.append(f"✅ {role_name}")
        
        if current_roles:
            embed.add_field(
                name="Current Roles",
                value="\n".join(current_roles),
                inline=False
            )
        else:
            embed.add_field(
                name="Current Roles",
                value="No special roles",
                inline=False
            )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        await ctx.respond(embed=embed, view=view, ephemeral=True)
    
    @commands.slash_command(name="rolestats", description="Show role distribution statistics")
    @require_role("moderator")
    async def role_stats(self, ctx: discord.ApplicationContext):
        """Show statistics about role distribution."""
        stats = await self.role_service.get_role_statistics(ctx.guild)
        
        embed = discord.Embed(
            title="📊 Role Statistics",
            description=f"Total members: {stats['total_members']}",
            color=discord.Color.purple()
        )
        
        for role_key, role_data in stats.items():
            if role_key == "total_members" or role_key == "unassigned":
                continue
            
            embed.add_field(
                name=role_data['name'],
                value=f"{role_data['count']} members ({role_data['percentage']}%)",
                inline=True
            )
        
        if stats['unassigned'] > 0:
            embed.add_field(
                name="Unassigned",
                value=f"{stats['unassigned']} members",
                inline=True
            )
        
        await ctx.respond(embed=embed, ephemeral=True)
    
    @commands.slash_command(name="grantcreator", description="Grant creator role to a user")
    @moderator_only
    async def grant_creator(
        self, 
        ctx: discord.ApplicationContext,
        user: discord.Option(discord.Member, description="User to grant creator role to"),
        reason: discord.Option(str, description="Reason for granting the role", required=False, default="Role assignment")
    ):
        """Grant creator role to a user."""
        success = await self.role_service.grant_creator_role(user)
        
        if success:
            await ctx.respond(
                f"✅ Granted **Creator** role to {user.mention}",
                ephemeral=True
            )
            
            AuditLog.record(
                event="role_granted",
                user_id=ctx.author.id,
                target_id=user.id,
                details={
                    "role_name": ROLES["creator"],
                    "reason": reason,
                    "granted_by": ctx.author.id
                }
            )
        else:
            await ctx.respond(
                f"❌ Failed to grant **Creator** role to {user.mention}",
                ephemeral=True
            )
    
    @commands.slash_command(name="setuproles", description="Set up all required roles in the server")
    @admin_only
    async def setup_roles(self, ctx: discord.ApplicationContext):
        """Create all required roles if they don't exist."""
        await ctx.defer(ephemeral=True)
        
        results = await self.role_service.ensure_roles_exist(ctx.guild)
        
        embed = discord.Embed(
            title="🔧 Role Setup Results",
            color=discord.Color.green()
        )
        
        if results["created"]:
            embed.add_field(
                name="Created Roles",
                value="\n".join(f"✅ {role}" for role in results["created"]),
                inline=False
            )
        
        if results["existing"]:
            embed.add_field(
                name="Existing Roles",
                value="\n".join(f"✅ {role}" for role in results["existing"]),
                inline=False
            )
        
        if results["errors"]:
            embed.add_field(
                name="Errors",
                value="\n".join(f"❌ {error}" for error in results["errors"]),
                inline=False
            )
            embed.color = discord.Color.red
        
        await ctx.respond(embed=embed, ephemeral=True)

def setup(bot):
    """Add the role commands cog to the bot."""
    bot.add_cog(RoleCommands(bot))
