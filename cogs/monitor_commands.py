# cogs/monitor_commands.py
import discord
from discord.ext import commands
from monitor.alerts import send_ops, send_econ
from monitor.health_checks import HealthChecker
import redis
import sqlite3


class MonitorCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command()
    @commands.is_owner()  # Restrict to bot owner
    async def test_ops(self, ctx):
        """Test operations webhook"""
        await send_ops("Test", "Operations webhook working")
        await ctx.send("✅ Sent ops test message")
        
    @commands.command()
    @commands.is_owner()
    async def test_econ(self, ctx):
        """Test economy webhook"""
        await send_econ("Test", "Economy webhook working")
        await ctx.send("✅ Sent econ test message")
        
    @commands.command()
    @commands.is_owner()
    async def test_alerts(self, ctx):
        """Test all alert types"""
        await send_ops("🔧 Test Alert", "This is a test operations alert", "info")
        await send_ops("⚠️ Test Warning", "This is a test warning", "orange")
        await send_ops("❌ Test Error", "This is a test error alert", "red")
        
        await send_econ("💰 Test Economy", "This is a test economy alert", "success")
        await send_econ("🏆 Test Legendary", "Test legendary creation alert", "success")
        
        await ctx.send("✅ Sent all test alerts")
        
    @commands.command()
    @commands.is_owner()
    async def health_check(self, ctx):
        """Run manual health check"""
        embed = discord.Embed(
            title="🔍 Health Check Results",
            color=discord.Color.blue()
        )
        
        # Check Redis
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            r = redis.from_url(redis_url, decode_responses=True)
            r.ping()
            embed.add_field(name="🔴 Redis", value="✅ Connected", inline=False)
        except:
            embed.add_field(name="🔴 Redis", value="❌ Disconnected", inline=False)
            
        # Check Database
        try:
            db_path = os.getenv("DATABASE_URL", "sqlite:///music_legends.db")
            if db_path.startswith("sqlite:///"):
                db_path = db_path[10:]
            conn = sqlite3.connect(db_path)
            conn.execute("SELECT 1")
            conn.close()
            embed.add_field(name="🗄️ Database", value="✅ Connected", inline=False)
        except:
            embed.add_field(name="🗄️ Database", value="❌ Disconnected", inline=False)
            
        # Check Webhooks
        from config.monitor import MONITOR
        ops_webhook = "✅ Configured" if MONITOR["WEBHOOK_OPS"] else "❌ Not configured"
        econ_webhook = "✅ Configured" if MONITOR["WEBHOOK_ECON"] else "❌ Not configured"
        
        embed.add_field(name="📡 Ops Webhook", value=ops_webhook, inline=True)
        embed.add_field(name="💰 Econ Webhook", value=econ_webhook, inline=True)
        
        embed.set_footer(text=f"Checked at {discord.utils.format_dt(discord.utils.utcnow(), style='R')}")
        await ctx.send(embed=embed)
        
    @commands.command()
    @commands.is_owner()
    async def system_status(self, ctx):
        """Show system status"""
        import psutil
        
        embed = discord.Embed(
            title="📊 System Status",
            color=discord.Color.green()
        )
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_color = discord.Color.green if cpu_percent < 80 else discord.Color.orange if cpu_percent < 95 else discord.Color.red
        embed.add_field(name="🖥️ CPU Usage", value=f"{cpu_percent}%", inline=True)
        
        # Memory
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_color = discord.Color.green if memory_percent < 80 else discord.Color.orange if memory_percent < 95 else discord.Color.red
        embed.add_field(name="💾 Memory Usage", value=f"{memory_percent}%", inline=True)
        
        # Disk
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        disk_color = discord.Color.green if disk_percent < 80 else discord.Color.orange if disk_percent < 95 else discord.Color.red
        embed.add_field(name="💿 Disk Usage", value=f"{disk_percent:.1f}%", inline=True)
        
        # Bot uptime
        uptime = discord.utils.utcnow() - self.bot.start_time
        embed.add_field(name="⏰ Bot Uptime", value=f"{uptime.days}d {uptime.seconds // 3600}h", inline=True)
        
        # Memory details
        embed.add_field(
            name="💾 Memory Details", 
            value=f"{memory.used / 1024 / 1024:.1f}MB / {memory.total / 1024 / 1024:.1f}MB",
            inline=False
        )
        
        # Disk details
        embed.add_field(
            name="💿 Disk Details",
            value=f"{disk.used / 1024 / 1024 / 1024:.1f}GB / {disk.total / 1024 / 1024 / 1024:.1f}GB",
            inline=False
        )
        
        embed.set_footer(text=f"Updated at {discord.utils.format_dt(discord.utils.utcnow(), style='R')}")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(MonitorCommands(bot))
