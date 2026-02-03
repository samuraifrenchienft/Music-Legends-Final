"""
Bot Logger Commands - View system errors and health
"""

import discord
from discord import app_commands, Interaction
from discord.ext import commands
from services.bot_logger import get_bot_logger
from datetime import datetime


class BotLoggerCommandsCog(commands.Cog):
    """Commands for viewing system logs and health"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_bot_logger(bot=bot)
    
    @app_commands.command(name="errors", description="View recent system errors")
    @app_commands.describe(
        context="Filter by error context",
        limit="Number of errors to show (1-50)"
    )
    async def errors_command(
        self,
        interaction: Interaction,
        context: str = None,
        limit: int = 10
    ):
        """View recent system errors"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Limit to 50 max
        limit = min(max(limit, 1), 50)
        
        errors = self.logger.get_error_history(context=context, limit=limit)
        
        if not errors:
            await interaction.followup.send(
                "✅ No errors found!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="❌ Recent System Errors",
            description=f"Showing {len(errors)} error(s)",
            color=discord.Color.red()
        )
        
        if context:
            embed.description += f"\nFiltered by: **{context}**"
        
        # Add entries (max 25 fields)
        for i, error in enumerate(errors[:25], 1):
            timestamp = datetime.fromisoformat(error['timestamp']).strftime("%m/%d %H:%M")
            
            field_name = f"{i}. {error.get('error_type', 'Unknown')}"
            
            field_value = f"**{error['details'][:80]}**\n"
            field_value += f"*{timestamp}* | {error['context']}"
            
            if error.get('user_id'):
                field_value += f" | User: `{error['user_id']}`"
            
            embed.add_field(
                name=field_name,
                value=field_value,
                inline=False
            )
        
        embed.set_footer(text=f"Total errors: {len(errors)}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="error_stats", description="View error statistics")
    async def error_stats_command(self, interaction: Interaction):
        """View error statistics"""
        
        await interaction.response.defer(ephemeral=True)
        
        stats = self.logger.get_error_stats()
        
        embed = discord.Embed(
            title="📊 Error Statistics",
            color=discord.Color.red()
        )
        
        if not stats:
            embed.description = "No error statistics available yet"
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Show error contexts with counts
        sorted_stats = sorted(stats.items(), key=lambda x: x[1]['count'], reverse=True)
        
        stats_str = '\n'.join(
            [f"• **{ctx}**: {info['count']} error(s)" 
             for ctx, info in sorted_stats[:15]]
        )
        
        embed.add_field(
            name="Error Contexts",
            value=stats_str if stats_str else "No errors",
            inline=False
        )
        
        # Show most recent
        if sorted_stats:
            most_recent_ctx, most_recent_info = sorted_stats[0]
            embed.add_field(
                name="Most Common Error",
                value=f"**{most_recent_ctx}** ({most_recent_info['count']} occurrences)",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="system_health", description="View overall system health")
    async def system_health_command(self, interaction: Interaction):
        """View comprehensive system health"""
        
        await interaction.response.defer(ephemeral=True)
        
        health = self.logger.get_health_summary()
        
        if not health:
            await interaction.followup.send(
                "❌ Could not retrieve system health",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🏥 System Health Report",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        # Error stats
        embed.add_field(
            name="❌ Errors",
            value=f"**Total:** {health.get('total_errors', 0)}\n"
                  f"**Last Hour:** {health.get('errors_last_hour', 0)}",
            inline=False
        )
        
        # Resource usage
        memory_pct = health.get('memory_usage', 0)
        cpu_pct = health.get('cpu_usage', 0)
        
        memory_emoji = "🟢" if memory_pct < 70 else "🟡" if memory_pct < 85 else "🔴"
        cpu_emoji = "🟢" if cpu_pct < 70 else "🟡" if cpu_pct < 85 else "🔴"
        
        embed.add_field(
            name="💻 Resources",
            value=f"{memory_emoji} Memory: {memory_pct:.1f}%\n"
                  f"{cpu_emoji} CPU: {cpu_pct:.1f}%",
            inline=False
        )
        
        # Top error types
        error_types = health.get('error_types', {})
        if error_types:
            top_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5]
            errors_str = '\n'.join([f"• {etype}: {count}" for etype, count in top_errors])
            embed.add_field(
                name="🔝 Top Error Types",
                value=errors_str,
                inline=False
            )
        
        # Overall status
        if health.get('errors_last_hour', 0) > 10:
            status = "⚠️ Multiple errors detected"
        elif memory_pct > 85 or cpu_pct > 85:
            status = "⚠️ High resource usage"
        else:
            status = "✅ Healthy"
        
        embed.add_field(
            name="Status",
            value=status,
            inline=False
        )
        
        embed.set_footer(text="Music Legends System Health")
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(BotLoggerCommandsCog(bot))
