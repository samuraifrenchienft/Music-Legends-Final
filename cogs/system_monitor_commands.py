"""
System Monitor Commands - View uptime, restarts, and performance metrics
"""

import discord
import asyncio
from discord import app_commands, Interaction
from discord.ext import commands
from services.system_monitor import get_system_monitor
from datetime import datetime


class SystemMonitorCommandsCog(commands.Cog):
    """Commands for viewing system health and performance"""
    
    def __init__(self, bot):
        self.bot = bot
        self.monitor = get_system_monitor(bot=bot)
        
        # Start background monitoring
        self.bot.loop.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """Background loop that monitors system continuously"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                await self.monitor.monitor_uptime()
                # Monitor every 60 seconds
                await asyncio.sleep(60)
            except Exception as e:
                print(f"[MONITOR] Error in monitoring loop: {e}")
                await asyncio.sleep(60)
    
    @app_commands.command(name="uptime", description="Check bot uptime and health")
    async def uptime_command(self, interaction: Interaction):
        """View current bot uptime and system health"""
        
        await interaction.response.defer(ephemeral=True)
        
        metrics = await self.monitor.monitor_uptime()
        
        if not metrics:
            await interaction.followup.send(
                "❌ Could not retrieve uptime metrics",
                ephemeral=True
            )
            return
        
        # Create embed
        embed = discord.Embed(
            title="⏱️ Bot Uptime & Health",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        # Uptime section
        embed.add_field(
            name="🕐 Uptime",
            value=f"**{metrics['uptime_formatted']}**\nStarted: {metrics['start_time'][:10]}",
            inline=False
        )
        
        # Resources section
        memory_pct = metrics['memory_usage']
        cpu_pct = metrics['cpu_usage']
        
        # Color code based on usage
        memory_emoji = "🟢" if memory_pct < 70 else "🟡" if memory_pct < 85 else "🔴"
        cpu_emoji = "🟢" if cpu_pct < 70 else "🟡" if cpu_pct < 85 else "🔴"
        
        embed.add_field(
            name="💾 Resources",
            value=f"{memory_emoji} Memory: {memory_pct:.1f}% ({metrics['memory_mb']:.0f}MB)\n"
                  f"{cpu_emoji} CPU: {cpu_pct:.1f}% ({metrics['cpu_count']} cores)\n"
                  f"💿 Disk: {metrics['disk_usage']:.1f}%",
            inline=False
        )
        
        # Activity section
        embed.add_field(
            name="👥 Activity",
            value=f"🖥️ Servers: {metrics['active_servers']}\n"
                  f"👤 Unique Users: {metrics['active_users']:,}\n"
                  f"🔄 Restarts: {metrics['restart_count']}",
            inline=False
        )
        
        # Status
        status = "✅ Healthy"
        if memory_pct > 85 or cpu_pct > 85:
            status = "⚠️ High Resource Usage"
        elif memory_pct > 95 or cpu_pct > 95:
            status = "🚨 Critical"
        
        embed.add_field(
            name="Status",
            value=status,
            inline=False
        )
        
        embed.set_footer(text="Music Legends System Monitor")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="restarts", description="View recent bot restarts")
    @app_commands.describe(limit="Number of restarts to show (1-50)")
    async def restarts_command(self, interaction: Interaction, limit: int = 10):
        """View recent restart history"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Limit to 50 max
        limit = min(max(limit, 1), 50)
        
        restarts = self.monitor.get_restart_history(limit=limit)
        
        if not restarts:
            await interaction.followup.send(
                "📭 No restart history found",
                ephemeral=True
            )
            return
        
        # Create embed
        embed = discord.Embed(
            title="🔄 Recent Bot Restarts",
            description=f"Showing {len(restarts)} restart(s)",
            color=discord.Color.blue()
        )
        
        for i, restart in enumerate(restarts[:25], 1):
            timestamp = datetime.fromisoformat(restart['timestamp']).strftime("%m/%d %H:%M")
            restart_type = restart.get('type', 'unknown').title()
            env = restart.get('environment', 'Unknown')
            
            field_name = f"{i}. {restart_type}"
            field_value = f"**Time:** {timestamp}\n**Env:** {env}"
            
            if restart.get('metadata'):
                metadata_str = ' | '.join(f"{k}={v}" for k, v in list(restart['metadata'].items())[:2])
                field_value += f"\n**Details:** {metadata_str}"
            
            embed.add_field(
                name=field_name,
                value=field_value,
                inline=False
            )
        
        embed.set_footer(text="Use /restart_stats for detailed statistics")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="restart_stats", description="View restart statistics")
    async def restart_stats_command(self, interaction: Interaction):
        """View restart statistics and trends"""
        
        await interaction.response.defer(ephemeral=True)
        
        restarts = self.monitor.get_restart_history(limit=1000)
        
        if not restarts:
            await interaction.followup.send(
                "📭 No restart history available",
                ephemeral=True
            )
            return
        
        # Analyze restart types
        restart_types = {}
        for restart in restarts:
            rtype = restart.get('type', 'unknown')
            restart_types[rtype] = restart_types.get(rtype, 0) + 1
        
        # Create embed
        embed = discord.Embed(
            title="📊 Restart Statistics",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="Total Restarts",
            value=f"**{len(restarts)}** total",
            inline=False
        )
        
        # By type
        types_str = '\n'.join(
            [f"• **{rtype.title()}**: {count}" 
             for rtype, count in sorted(restart_types.items(), key=lambda x: x[1], reverse=True)]
        )
        embed.add_field(
            name="By Type",
            value=types_str,
            inline=True
        )
        
        # Calculate average restarts per day
        if restarts:
            first_restart = datetime.fromisoformat(restarts[-1]['timestamp'])
            latest_restart = datetime.fromisoformat(restarts[0]['timestamp'])
            days_span = (latest_restart - first_restart).days or 1
            avg_per_day = len(restarts) / days_span
            
            embed.add_field(
                name="Frequency",
                value=f"**{avg_per_day:.1f}** per day\n**{len(restarts) / max(days_span / 30, 1):.1f}** per month",
                inline=True
            )
        
        embed.set_footer(text="Data based on available restart history")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="performance", description="View performance metrics")
    async def performance_command(self, interaction: Interaction):
        """View collected performance metrics"""
        
        await interaction.response.defer(ephemeral=True)
        
        stats = self.monitor.get_metrics_stats()
        
        if not stats or stats.get('total_measurements', 0) == 0:
            await interaction.followup.send(
                "📭 No performance metrics available yet. Wait a moment and try again.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="📈 Performance Metrics",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Measurements",
            value=f"**{stats['total_measurements']}** samples collected",
            inline=False
        )
        
        embed.add_field(
            name="💾 Memory Usage",
            value=f"**Average:** {stats['avg_memory']:.1f}%\n"
                  f"**Peak:** {stats['max_memory']:.1f}%\n"
                  f"**Low:** {stats['min_memory']:.1f}%",
            inline=True
        )
        
        embed.add_field(
            name="⚙️ CPU Usage",
            value=f"**Average:** {stats['avg_cpu']:.1f}%\n"
                  f"**Peak:** {stats['max_cpu']:.1f}%\n"
                  f"**Low:** {stats['min_cpu']:.1f}%",
            inline=True
        )
        
        embed.set_footer(text="Metrics updated every 60 seconds")
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(SystemMonitorCommandsCog(bot))
