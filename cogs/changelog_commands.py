"""
Changelog Command Cog - View system changes and statistics
"""

import discord
from discord import app_commands, Interaction
from discord.ext import commands
from services.changelog_manager import get_changelog_manager
from datetime import datetime


class ChangelogCommandsCog(commands.Cog):
    """Commands for viewing system changelog and statistics"""
    
    def __init__(self, bot):
        self.bot = bot
        self.changelog = get_changelog_manager(bot=bot)
    
    @app_commands.command(name="changelog", description="View recent system changes")
    @app_commands.describe(
        category="Filter by category (pack_creation, card_generation, etc.)",
        limit="Number of entries to show (1-50)"
    )
    async def changelog_command(
        self,
        interaction: Interaction,
        category: str = None,
        limit: int = 10
    ):
        """View system changelog"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Limit to 50 max
        limit = min(max(limit, 1), 50)
        
        # Get changes
        changes = self.changelog.get_changes(category=category, limit=limit)
        
        if not changes:
            await interaction.followup.send(
                "📭 No changelog entries found.",
                ephemeral=True
            )
            return
        
        # Create embed
        embed = discord.Embed(
            title="📋 System Changelog",
            description=f"Showing {len(changes)} recent changes",
            color=discord.Color.blue()
        )
        
        if category:
            embed.description += f"\nFiltered by: **{category}**"
        
        # Add entries (max 25 fields)
        for i, change in enumerate(changes[:25], 1):
            timestamp = datetime.fromisoformat(change['timestamp']).strftime("%m/%d %H:%M")
            severity_emoji = change.get('severity_emoji', '⚪')
            
            field_name = f"{i}. {severity_emoji} {change.get('category_name', change['category'])}"
            
            field_value = f"**{change['description']}**\n"
            field_value += f"*{timestamp}*"
            
            if change.get('user_id'):
                field_value += f" | User: `{change['user_id']}`"
            
            embed.add_field(
                name=field_name,
                value=field_value,
                inline=False
            )
        
        embed.set_footer(text=f"Total entries: {len(changes)}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="changelog_stats", description="View changelog statistics")
    async def changelog_stats_command(self, interaction: Interaction):
        """View changelog statistics"""
        
        await interaction.response.defer(ephemeral=True)
        
        stats = self.changelog.get_stats()
        
        embed = discord.Embed(
            title="📊 Changelog Statistics",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Total Entries",
            value=f"**{stats.get('total', 0):,}**",
            inline=False
        )
        
        # By category
        if stats.get('by_category'):
            category_str = '\n'.join(
                [f"• **{cat}**: {count}" 
                 for cat, count in sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True)]
            )
            embed.add_field(
                name="By Category",
                value=category_str[:1024],
                inline=True
            )
        
        # By severity
        if stats.get('by_severity'):
            severity_str = '\n'.join(
                [f"• **{sev}**: {count}" 
                 for sev, count in sorted(stats['by_severity'].items(), key=lambda x: x[1], reverse=True)]
            )
            embed.add_field(
                name="By Severity",
                value=severity_str[:1024],
                inline=True
            )
        
        if stats.get('first_change'):
            first = datetime.fromisoformat(stats['first_change']).strftime("%b %d, %Y")
            embed.add_field(
                name="First Entry",
                value=first,
                inline=True
            )
        
        if stats.get('last_change'):
            last = datetime.fromisoformat(stats['last_change']).strftime("%b %d, %Y %H:%M")
            embed.add_field(
                name="Most Recent",
                value=last,
                inline=True
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ChangelogCommandsCog(bot))
