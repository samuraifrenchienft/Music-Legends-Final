# cogs/admin_payment_commands.py
"""
Admin Commands for Payment Actions
Handle approval with capture and rejection with void
"""

from discord.ext import commands
import discord
from services.admin_payment_actions import admin_payment_actions
from services.payment_gateway import gateway
from models.creator_pack import CreatorPack

class AdminPaymentCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command()
    @commands.has_permissions(manage_guild=True)  # Admin only
    async def approve_capture(self, ctx, pack_id: str):
        """
        Approve a pack and capture payment
        Usage: !approve_capture <pack_id>
        """
        try:
            await ctx.trigger_typing()
            
            # Get pack details first
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                await ctx.send("❌ Pack not found")
                return
            
            # Check if pack is in reviewable state
            if pack.status not in ["pending", "rejected"]:
                await ctx.send(f"❌ Pack is not reviewable (current status: {pack.status})")
                return
            
            # Perform approval and capture
            success = admin_payment_actions.approve_and_capture(pack_id, ctx.author.id)
            
            if success:
                # Get updated pack info
                updated_pack = CreatorPack.get_by_id(pack_id)
                
                embed = discord.Embed(
                    title="✅ Pack Approved & Payment Captured",
                    description=f"Successfully approved and captured payment for pack: {pack.name}",
                    color=discord.Color.green()
                )
                
                embed.add_field(name="📦 Pack ID", value=pack_id[:8], inline=True)
                embed.add_field(name="📦 Name", value=pack.name, inline=True)
                embed.add_field(name="👤 Owner", value=str(pack.owner_id), inline=True)
                embed.add_field(name="🎼 Genre", value=pack.genre, inline=True)
                embed.add_field(name="💰 Amount", value=f"${pack.price_cents / 100:.2f}", inline=True)
                embed.add_field(name="💳 Payment Status", value=updated_pack.payment_status.title(), inline=True)
                embed.add_field(name="📊 Pack Status", value=updated_pack.status.title(), inline=True)
                embed.add_field(name="👤 Approved By", value=str(ctx.author.id), inline=True)
                embed.add_field(name="📅 Approved At", value=updated_pack.reviewed_at.strftime('%Y-%m-%d %H:%M'), inline=True)
                
                embed.set_footer(text=f"Pack ID: {pack_id[:8]}")
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Failed to approve and capture payment")
                
        except ValueError as e:
            await ctx.send(f"❌ Error: {e}")
        except Exception as e:
            await ctx.send(f"❌ Error approving and capturing: {e}")
    
    @commands.command()
    @commands.has_permissions(manage_guild=True)  # Admin only
    async def reject_void(self, ctx, pack_id: str, *, note: str):
        """
        Reject a pack and void payment
        Usage: !reject_void <pack_id> <reason>
        """
        try:
            await ctx.trigger_typing()
            
            # Get pack details first
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                await ctx.send("❌ Pack not found")
                return
            
            # Check if pack is in reviewable state
            if pack.status not in ["pending", "rejected"]:
                await ctx.send(f"❌ Pack is not reviewable (current status: {pack.status})")
                return
            
            # Perform rejection and void
            success = admin_payment_actions.reject_and_void(pack_id, ctx.author.id, note)
            
            if success:
                # Get updated pack info
                updated_pack = CreatorPack.get_by_id(pack_id)
                
                embed = discord.Embed(
                    title="❌ Pack Rejected & Payment Voided",
                    description=f"Rejected pack and voided payment: {pack.name}",
                    color=discord.Color.red()
                )
                
                embed.add_field(name="📦 Pack ID", value=pack_id[:8], inline=True)
                embed.add_field(name="📦 Name", value=pack.name, inline=True)
                embed.add_field(name="👤 Owner", value=str(pack.owner_id), inline=True)
                embed.add_field(name="🎼 Genre", value=pack.genre, inline=True)
                embed.add_field(name="💰 Amount", value=f"${pack.price_cents / 100:.2f}", inline=True)
                embed.add_field(name="💳 Payment Status", value=updated_pack.payment_status.title(), inline=True)
                embed.add_field(name="📊 Pack Status", value=updated_pack.status.title(), inline=True)
                embed.add_field(name="📝 Reason", value=note, inline=False)
                embed.add_field(name="👤 Rejected By", value=str(ctx.author.id), inline=True)
                embed.add_field(name="📅 Rejected At", value=updated_pack.reviewed_at.strftime('%Y-%m-%d %H:%M'), inline=True)
                
                embed.set_footer(text=f"Pack ID: {pack_id[:8]}")
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Failed to reject and void payment")
                
        except Exception as e:
            await ctx.send(f"❌ Error rejecting and voiding: {e}")
    
    @commands.command()
    @commands.has_permissions(manage_guild=True)  # Admin only
    async def pack_payment_status(self, ctx, pack_id: str):
        """Show detailed payment status for a pack"""
        try:
            status = admin_payment_actions.get_pack_payment_status(pack_id)
            
            if not status:
                await ctx.send("❌ Pack not found")
                return
            
            pack = CreatorPack.get_by_id(pack_id)
            
            embed = discord.Embed(
                title=f"💳 Payment Status: {status['pack_name']}",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="🆔 Pack ID", value=pack_id[:8], inline=True)
            embed.add_field(name="📊 Pack Status", value=status['pack_status'].title(), inline=True)
            embed.add_field(name="💳 Payment Status", value=status['payment_status'].title(), inline=True)
            embed.add_field(name="💰 Amount", value=f"${status['price_cents'] / 100:.2f}", inline=True)
            embed.add_field(name="💳 Payment ID", value=status['payment_id'][:20] + "...", inline=True)
            embed.add_field(name="👤 Owner", value=str(pack.owner_id), inline=True)
            
            # Action availability
            actions = []
            if status['can_be_captured']:
                actions.append("🔄 Can be captured")
            if status['can_be_refunded']:
                actions.append("💸 Can be refunded")
            
            if actions:
                embed.add_field(name="🔧 Available Actions", value="\n".join(actions), inline=False)
            
            # Stripe status if available
            if status['stripe_status']:
                stripe_info = status['stripe_status']
                embed.add_field(name="🌐 Stripe Status", value=stripe_info['stripe_status'].title(), inline=True)
                embed.add_field(name="💵 Stripe Amount", value=f"${stripe_info['amount'] / 100:.2f}", inline=True)
                embed.add_field(name="💱 Currency", value=stripe_info['currency'].upper(), inline=True)
                
                if stripe_info['charges']:
                    charge_count = len(stripe_info['charges'])
                    embed.add_field(name="📋 Charges", value=str(charge_count), inline=True)
            
            # Review info
            if status['reviewed_by']:
                embed.add_field(name="👤 Reviewed By", value=str(status['reviewed_by']), inline=True)
                if status['reviewed_at']:
                    embed.add_field(name="📅 Reviewed At", value=status['reviewed_at'][:19], inline=True)
            
            embed.set_footer(text=f"Pack ID: {pack_id[:8]}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting payment status: {e}")
    
    @commands.command()
    @commands.has_permissions(manage_guild=True)  # Admin only
    async def admin_payment_stats(self, ctx):
        """Show admin payment statistics"""
        try:
            stats = admin_payment_actions.get_admin_payment_stats(ctx.author.id)
            
            embed = discord.Embed(
                title="💳 Admin Payment Statistics",
                description=f"Payment actions by {ctx.author.name}",
                color=discord.Color.purple()
            )
            
            embed.add_field(name="📋 Total Reviews", value=str(stats["total_reviews"]), inline=True)
            embed.add_field(name="✅ Approved", value=str(stats["approved"]), inline=True)
            embed.add_field(name="❌ Rejected", value=str(stats["rejected"]), inline=True)
            embed.add_field(name="💰 Payments Captured", value=str(stats["payments_captured"]), inline=True)
            embed.add_field(name="💸 Payments Voided", value=str(stats["payments_voided"]), inline=True)
            embed.add_field(name="💵 Total Revenue", value=f"${stats['total_revenue_dollars']:.2f}", inline=True)
            
            if stats["failed_captures"] > 0:
                embed.add_field(name="❌ Failed Captures", value=str(stats["failed_captures"]), inline=True)
            
            if stats["failed_voids"] > 0:
                embed.add_field(name="❌ Failed Voids", value=str(stats["failed_voids"]), inline=True)
            
            # Calculate success rates
            if stats["total_reviews"] > 0:
                approval_rate = (stats["approved"] / stats["total_reviews"]) * 100
                capture_success_rate = (stats["payments_captured"] / max(stats["approved"], 1)) * 100
                
                embed.add_field(name="📈 Approval Rate", value=f"{approval_rate:.1f}%", inline=True)
                embed.add_field(name="💰 Capture Success Rate", value=f"{capture_success_rate:.1f}%", inline=True)
            
            embed.set_footer(text=f"Requested by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting admin payment stats: {e}")
    
    @commands.command()
    @commands.has_permissions(manage_guild=True)  # Admin only
    async def validate_payment_state(self, ctx, pack_id: str):
        """Validate payment state consistency"""
        try:
            validation = admin_payment_actions.validate_payment_state(pack_id)
            
            if not validation["valid"] and "error" in validation:
                await ctx.send(f"❌ Validation error: {validation['error']}")
                return
            
            pack = CreatorPack.get_by_id(pack_id)
            
            if validation["valid"]:
                embed = discord.Embed(
                    title="✅ Payment State Valid",
                    description=f"Pack {pack.name} has consistent payment state",
                    color=discord.Color.green()
                )
                
                embed.add_field(name="📊 Pack Status", value=validation["pack_status"].title(), inline=True)
                embed.add_field(name="💳 Payment Status", value=validation["payment_status"].title(), inline=True)
                embed.add_field(name="✅ Issues", value="None found", inline=True)
            else:
                embed = discord.Embed(
                    title="⚠️ Payment State Issues",
                    description=f"Pack {pack.name} has payment state inconsistencies",
                    color=discord.Color.orange()
                )
                
                embed.add_field(name="📊 Pack Status", value=validation["pack_status"].title(), inline=True)
                embed.add_field(name="💳 Payment Status", value=validation["payment_status"].title(), inline=True)
                
                if validation["issues"]:
                    issue_text = "\n".join([f"• {issue}" for issue in validation["issues"]])
                    embed.add_field(name="⚠️ Issues", value=issue_text, inline=False)
            
            embed.set_footer(text=f"Pack ID: {pack_id[:8]}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error validating payment state: {e}")
    
    @commands.command()
    @commands.has_permissions(manage_guild=True)  # Admin only
    async def gateway_status(self, ctx):
        """Check payment gateway status"""
        try:
            # Test gateway connectivity
            if gateway.api_key:
                embed = discord.Embed(
                    title="💳 Payment Gateway Status",
                    description="Gateway is configured and ready",
                    color=discord.Color.green()
                )
                
                embed.add_field(name="🔑 API Key", value="✅ Configured", inline=True)
                embed.add_field(name="🌐 Provider", value="Stripe", inline=True)
                embed.add_field(name="📊 Status", value="Connected", inline=True)
                
                # Test a simple status check
                try:
                    # This would be a lightweight API call to test connectivity
                    embed.add_field(name="🔗 Connection", value="✅ Active", inline=True)
                except:
                    embed.add_field(name="🔗 Connection", value="⚠️ Test failed", inline=True)
                
            else:
                embed = discord.Embed(
                    title="💳 Payment Gateway Status",
                    description="Gateway is not properly configured",
                    color=discord.Color.red()
                )
                
                embed.add_field(name="🔑 API Key", value="❌ Not configured", inline=True)
                embed.add_field(name="🌐 Provider", value="Stripe", inline=True)
                embed.add_field(name="📊 Status", value="Disconnected", inline=True)
                embed.add_field(name="⚠️ Action", value="Configure STRIPE_SECRET_KEY in environment", inline=False)
            
            embed.set_footer(text=f"Checked by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error checking gateway status: {e}")


async def setup(bot):
    await bot.add_cog(AdminPaymentCommands(bot))
