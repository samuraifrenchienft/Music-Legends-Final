# cogs/admin_review_commands.py
"""
Admin Commands for Creator Pack Review
"""

from discord.ext import commands
import discord
from services.admin_review import admin_review
from models.creator_pack import CreatorPack

class AdminReviewCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command()
    @commands.has_permissions(manage_guild=True)  # Admin only
    async def review(self, ctx, pack_id: str, decision: str, *, note: str = ""):
        """
        Review a creator pack
        Usage: !review <pack_id> <approve|reject> [note]
        """
        try:
            # Parse decision
            approve = decision.lower() == "approve"
            
            # Validate pack exists
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                await ctx.send("❌ Pack not found")
                return
            
            # Check if pack is in reviewable state
            if pack.status not in ["pending", "rejected"]:
                await ctx.send(f"❌ Pack is not reviewable (current status: {pack.status})")
                return
            
            # Perform review
            result = admin_review.review_pack(
                pack_id=pack_id,
                admin_id=ctx.author.id,
                approve=approve,
                note=note
            )
            
            if result:
                # Create result embed
                color = discord.Color.green() if approve else discord.Color.red()
                title = "✅ Pack Approved" if approve else "❌ Pack Rejected"
                
                embed = discord.Embed(
                    title=title,
                    description=f"Pack '{pack.name}' has been {result}",
                    color=color
                )
                
                embed.add_field(name="📦 Pack ID", value=pack_id[:8], inline=True)
                embed.add_field(name="📦 Name", value=pack.name, inline=True)
                embed.add_field(name="👤 Owner", value=str(pack.owner_id), inline=True)
                embed.add_field(name="🎼 Genre", value=pack.genre, inline=True)
                
                if note:
                    embed.add_field(name="📝 Note", value=note, inline=False)
                
                if not approve:
                    embed.add_field(name="❌ Reason", value=pack.rejection_reason or "No reason provided", inline=False)
                
                embed.add_field(name="👤 Reviewed By", value=str(ctx.author.id), inline=True)
                embed.add_field(name="📅 Reviewed At", value=pack.reviewed_at.strftime('%Y-%m-%d %H:%M') if pack.reviewed_at else "N/A", inline=True)
                
                embed.set_footer(text=f"Pack ID: {pack_id[:8]}")
                await ctx.send(embed=embed)
                
                # Log the action
                from services.monitor.alerts import system_error
                
                if approve:
                    await system_error(
                        "Creator Pack Approved",
                        f"Admin {ctx.author.id} approved pack {pack_id}: {pack.name}"
                    )
                else:
                    await system_error(
                        "Creator Pack Rejected",
                        f"Admin {ctx.author.id} rejected pack {pack_id}: {pack.name} - {note}"
                    )
            else:
                await ctx.send("❌ Review failed")
                
        except Exception as e:
            await ctx.send(f"❌ Error reviewing pack: {e}")
    
    @commands.command()
    @commands.has_permissions(manage_guild=True)  # Admin only
    async def batch_review(self, ctx, action: str, limit: int = 10):
        """
        Batch review pending packs
        Usage: !batch_review <approve|reject> [limit]
        """
        try:
            approve = action.lower() == "approve"
            
            # Get pending packs
            pending_packs = CreatorPack.get_pending(limit)
            
            if not pending_packs:
                await ctx.send("No pending packs to review!")
                return
            
            results = {
                "approved": 0,
                "rejected": 0,
                "failed": 0
            }
            
            embed = discord.Embed(
                title=f"📋 Batch Review: {action.title()}",
                description=f"Processing {len(pending_packs)} pending packs",
                color=discord.Color.blue()
            )
            
            for pack in pending_packs:
                try:
                    result = admin_review.review_pack(
                        pack_id=str(pack.id),
                        admin_id=ctx.author.id,
                        approve=approve,
                        note=f"Batch {action}"
                    )
                    
                    if result == action:
                        results[action] += 1
                    else:
                        results["failed"] += 1
                        
                except Exception as e:
                    results["failed"] += 1
                    print(f"❌ Error reviewing pack {pack.id}: {e}")
            
            # Show results
            embed.add_field(name="✅ Approved", value=str(results["approved"]), inline=True)
            embed.add_field(name="❌ Rejected", value=str(results["rejected"]), inline=True)
            embed.add_field(name="❌ Failed", value=str(results["failed"]), inline=True)
            
            embed.set_footer(text=f"Batch review completed by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error in batch review: {e}")
    
    @commands.command()
    @commands.has_permissions(manage_guild=True)  # Admin only
    async def review_history(self, ctx, pack_id: str):
        """Show review history for a pack"""
        try:
            history = admin_review.get_review_history(pack_id)
            
            if not history:
                await ctx.send("❌ No review history found")
                return
            
            pack = history["pack"]
            
            embed = discord.Embed(
                title=f"📋 Review History: {pack['pack_name']}",
                description=f"Current status: {pack['current_status']}",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="🆔 Pack ID", value=history["pack_id"][:8], inline=True)
            embed.add_field(name="📦 Name", value=pack["pack_name"], inline=True)
            embed.add_field(name="📊 Status", value=pack["current_status"].title(), inline=True)
            
            # Show review history
            if history["review_history"]:
                for i, event in enumerate(history["review_history"][-5:], 1):  # Show last 5 events
                    event_type = event["event"]
                    timestamp = event["timestamp"]
                    user_id = event["user_id"]
                    payload = event["payload"]
                    
                    event_emoji = {
                        "creator_pack_submitted": "📤",
                        "creator_pack_approved": "✅",
                        "creator_pack_rejected": "❌",
                        "creator_pack_disabled": "🚫"
                    }.get(event_type, "📋")
                    
                    embed.add_field(
                        name=f"{i}. {event_emoji} {event_type.replace('_', ' ').title()}",
                        value=f"By: {user_id} | {timestamp[:19]}\n{payload.get('decision', payload.get('note', 'No details')[:50]}",
                        inline=False
                    )
            else:
                embed.add_field(name="📋 History", value="No review events found", inline=False)
            
            embed.set_footer(text=f"Pack ID: {pack_id[:8]}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting review history: {e}")
    
    @commands.command()
    @commands.has_permissions(manage_guild=True)  # Admin only
    async def admin_stats(self, ctx):
        """Show admin review statistics"""
        try:
            stats = admin_review.get_admin_stats(ctx.author.id)
            
            embed = discord.Embed(
                title="📊 Admin Review Statistics",
                color=discord.Color.purple()
            )
            
            embed.add_field(name="📋 Total Reviews", value=str(stats["total_reviews"]), inline=True)
            embed.add_field(name="✅ Approved", value=str(stats["approvals"]), inline=True)
            embed.add_field(name="❌ Rejected", value=str(stats["rejections"]), inline=True)
            embed.add_field(name="📈 Approval Rate", value=f"{(stats['approvals'] / max(stats['total_reviews'], 1) * 100):.1f}%", inline=True)
            
            # Show recent reviews
            if stats["recent_reviews"]:
                recent_text = []
                for review in stats["recent_reviews"][:5]:
                    recent_text.append(f"• {review['pack_name']} ({review['decision']})")
                
                embed.add_field(name="📋 Recent Reviews", value="\n".join(recent_text), inline=False)
            
            embed.set_footer(text=f"Requested by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting admin stats: {e}")
    
    @commands.command()
    @commands.has_permissions(manage_guild=True)  # Admin only
    async def queue_status(self, ctx):
        """Show review queue status"""
        try:
            stats = admin_review.get_queue_stats()
            
            embed = discord.Embed(
                title="📋 Review Queue Status",
                color=discord.Color.orange()
            )
            
            embed.add_field(name="⏳ Pending", value=str(stats["pending_count"]), inline=True)
            
            if stats["oldest_pending"]:
                oldest = stats["oldest_pending"]
                embed.add_field(name="📅 Oldest", value=oldest.strftime('%Y-%m-%d %H:%M'), inline=True)
            
            if stats["newest_pending"]:
                newest = stats["newest_pending"]
                embed.add_field(name="🆕 Newest", value=newest.strftime('%Y-%m-%d %H:%M'), inline=True)
            
            # Show genre breakdown
            if stats["pending_by_genre"]:
                genre_text = []
                for genre, count in list(stats["pending_by_genre"].items())[:5]:
                    genre_text.append(f"{genre}: {count}")
                
                embed.add_field(name="🎼 By Genre", value=" | ".join(genre_text), inline=False)
            
            embed.set_footer(text=f"Queue status as of now")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting queue status: {e}")


async def setup(bot):
    await bot.add_cog(AdminReviewCommands(bot))
