# cogs/admin_review_panel.py
"""
Admin Review Panel Cog
Complete admin review workflow with queue management
"""

from discord.ext import commands
import discord
from discord.ui import Button, Modal, InputText, View, Select
from discord import Interaction, Embed, ButtonStyle
from typing import List, Optional, Dict, Any
from models.creator_pack import CreatorPack
from services.admin_payment_actions import admin_payment_actions
from services.creator_preview import creator_preview
from services.admin_review import admin_review
from services.payment_gateway import gateway

class AdminReviewPanel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_page = {}  # admin_id -> page
        self.selected_pack = {}  # admin_id -> pack_id
    
    @commands.hybrid_command(name="admin_review", description="Open admin review panel")
    @commands.has_permissions(manage_guild=True)
    async def admin_review(self, ctx: Interaction):
        """Open admin review panel"""
        try:
            await ctx.defer()
            
            # Get pending packs
            pending_packs = CreatorPack.get_pending(limit=50)
            
            if not pending_packs:
                embed = Embed(
                    title="🛡️ Admin Review Panel",
                    description="No packs pending review!",
                    color=discord.Color.green()
                )
                embed.add_field(name="📊 Status", value="All caught up! No packs require review.", inline=False)
                await ctx.respond(embed=embed, ephemeral=True)
                return
            
            # Create queue screen
            await self.show_queue_screen(ctx, pending_packs)
            
        except Exception as e:
            await ctx.respond(f"❌ Error loading review panel: {e}", ephemeral=True)
    
    async def show_queue_screen(self, interaction: Interaction, pending_packs: List[CreatorPack], page: int = 0):
        """Show queue screen with pending packs"""
        try:
            admin_id = interaction.user.id
            
            # Pagination
            packs_per_page = 10
            total_pages = (len(pending_packs) + packs_per_page - 1) // packs_per_page
            
            if page >= total_pages:
                page = max(0, total_pages - 1)
            
            start_idx = page * packs_per_page
            end_idx = min(start_idx + packs_per_page, len(pending_packs))
            page_packs = pending_packs[start_idx:end_idx]
            
            # Create queue embed
            embed = Embed(
                title="🛡️ Admin Review Panel",
                description=f"**Pending Packs:** {len(pending_packs)} total (Page {page + 1}/{total_pages})",
                color=discord.Color.orange()
            )
            
            # Add pack fields
            for i, pack in enumerate(page_packs, start=start_idx + 1):
                payment_emoji = {
                    "authorized": "💳",
                    "captured": "💰",
                    "failed": "❌",
                    "refunded": "💸"
                }.get(pack.payment_status, "❓")
                
                # Get quality score if available
                quality_text = ""
                preview = creator_preview.build_preview(str(pack.id))
                if preview:
                    quality_text = f" | ⭐ {preview['quality_score']}/100"
                
                field_value = f"🎼 {pack.genre} | 🎵 {len(pack.artist_ids) if pack.artist_ids else 0} artists{quality_text}\n"
                field_value += f"{payment_emoji} {pack.payment_status.title()} | 💰 ${pack.price_cents / 100:.2f}\n"
                field_value += f"📅 Created: {pack.created_at.strftime('%Y-%m-%d') if pack.created_at else 'Unknown'}"
                
                embed.add_field(
                    name=f"{i}. {pack.name}",
                    value=field_value,
                    inline=False
                )
            
            # Store current page
            self.current_page[admin_id] = page
            
            # Create preview buttons for first few packs
            view = QueueScreenView(admin_id, page_packs, page, total_pages)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error showing queue: {e}", ephemeral=True)
    
    async def show_preview_screen(self, interaction: Interaction, pack: CreatorPack):
        """Show detailed pack preview for review"""
        try:
            admin_id = interaction.user.id
            
            # Store selected pack
            self.selected_pack[admin_id] = str(pack.id)
            
            # Get comprehensive preview
            preview = creator_preview.build_preview(str(pack.id))
            
            if not preview:
                await interaction.response.send_message("❌ Could not generate preview", ephemeral=True)
                return
            
            # Create preview embed
            embed = Embed(
                title=f"🔍 Pack Preview: {pack.name}",
                description=f"Pack ID: {str(pack.id)[:8]} | Owner: {pack.owner_id}",
                color=discord.Color.blue()
            )
            
            # Basic info
            embed.add_field(name="📦 Pack Info", value=f"🎼 Genre: {pack.genre}\n💰 Price: ${pack.price_cents / 100:.2f}\n🎵 Artists: {len(pack.artist_ids) if pack.artist_ids else 0}", inline=False)
            embed.add_field(name="📊 Status", value=f"📋 Pack: {pack.status.title()}\n💳 Payment: {pack.payment_status.title()}", inline=False)
            
            # Quality assessment
            if preview.get('quality_score'):
                quality_color = {
                    "Excellent": discord.Color.green(),
                    "Good": discord.Color.blue(),
                    "Fair": discord.Color.gold(),
                    "Poor": discord.Color.orange(),
                    "Very Poor": discord.Color.red()
                }.get(preview['quality_rating'], discord.Color.grey())
                
                embed.color = quality_color
                embed.add_field(name="⭐ Quality", value=f"{preview['quality_score']}/100 ({preview['quality_rating']})", inline=True)
            
            # Tier distribution
            tier_dist = preview.get('tier_distribution', {})
            if any(tier_dist.values()):
                tier_text = []
                for tier, count in tier_dist.items():
                    if count > 0:
                        tier_emoji = {
                            "legendary": "🏆",
                            "platinum": "💎",
                            "gold": "🥇",
                            "silver": "🥈",
                            "bronze": "🥉",
                            "community": "👥"
                        }.get(tier, "❓")
                        tier_text.append(f"{tier_emoji}{count}")
                
                embed.add_field(name="🎯 Tiers", value=" ".join(tier_text), inline=True)
            
            # Artist preview (first 5)
            artists = preview.get('artists', [])
            if artists:
                artist_text = ""
                for i, artist in enumerate(artists[:5], 1):
                    tier_emoji = {
                        "legendary": "🏆",
                        "platinum": "💎",
                        "gold": "🥇",
                        "silver": "🥈",
                        "bronze": "🥉",
                        "community": "👥"
                    }.get(artist['estimated_tier'], "❓")
                    
                    artist_text += f"{i}. {tier_emoji} **{artist['name']}** ({artist['estimated_tier']})\n"
                    artist_text += f"   🎼 {artist['genre']} | 👥 {artist['popularity']}\n"
                
                if len(artists) > 5:
                    artist_text += f"... and {len(artists) - 5} more artists"
                
                embed.add_field(name="🎵 Artist Preview", value=artist_text, inline=False)
            
            # Safety checks
            from services.safety_checks import safety_checks
            safe, safety_message = safety_checks.safe_images(preview)
            
            safety_emoji = "✅" if safe else "❌"
            embed.add_field(name="🛡️ Safety Check", value=f"{safety_emoji} {safety_message}", inline=False)
            
            # Create action buttons
            view = PreviewScreenView(pack, admin_id)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error showing preview: {e}", ephemeral=True)


class QueueScreenView(View):
    def __init__(self, admin_id: int, packs: List[CreatorPack], current_page: int, total_pages: int):
        super().__init__(timeout=300)
        self.admin_id = admin_id
        self.packs = packs
        self.current_page = current_page
        self.total_pages = total_pages
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.admin_id and interaction.user.guild_permissions.manage_guild
    
    @discord.ui.button(label="◀", style=ButtonStyle.secondary)
    async def previous_page(self, interaction: Interaction, button: Button):
        if self.current_page > 0:
            # Get all pending packs again
            pending_packs = CreatorPack.get_pending(limit=50)
            await admin_review_panel.show_queue_screen(interaction, pending_packs, self.current_page - 1)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="▶", style=ButtonStyle.secondary)
    async def next_page(self, interaction: Interaction, button: Button):
        if self.current_page < self.total_pages - 1:
            # Get all pending packs again
            pending_packs = CreatorPack.get_pending(limit=50)
            await admin_review_panel.show_queue_screen(interaction, pending_packs, self.current_page + 1)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="Refresh", style=ButtonStyle.secondary, emoji="🔄")
    async def refresh(self, interaction: Interaction, button: Button):
        # Get updated pending packs
        pending_packs = CreatorPack.get_pending(limit=50)
        await admin_review_panel.show_queue_screen(interaction, pending_packs, self.current_page)
    
    # Dynamic preview buttons for first few packs
    def __init__(self, admin_id: int, packs: List[CreatorPack], current_page: int, total_pages: int):
        super().__init__(timeout=300)
        self.admin_id = admin_id
        self.packs = packs
        self.current_page = current_page
        self.total_pages = total_pages
        
        # Add preview buttons for first 5 packs
        for i, pack in enumerate(packs[:5]):
            button = Button(
                label=f"Preview #{i+1}",
                style=ButtonStyle.primary,
                custom_id=f"preview_{pack.id}"
            )
            button.callback = self.create_preview_callback(pack)
            self.add_item(button)
    
    def create_preview_callback(self, pack: CreatorPack):
        async def preview_callback(interaction: Interaction):
            await admin_review_panel.show_preview_screen(interaction, pack)
        return preview_callback


class PreviewScreenView(View):
    def __init__(self, pack: CreatorPack, admin_id: int):
        super().__init__(timeout=300)
        self.pack = pack
        self.admin_id = admin_id
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.admin_id and interaction.user.guild_permissions.manage_guild
    
    @discord.ui.button(label="Approve", style=ButtonStyle.success, emoji="✅")
    async def approve_button(self, interaction: Interaction, button: Button):
        # Check if payment is authorized
        if self.pack.payment_status != "authorized":
            await interaction.response.send_message("❌ Payment is not authorized for this pack", ephemeral=True)
            return
        
        # Show confirmation dialog
        embed = Embed(
            title="✅ Approve Pack",
            description=f"Are you sure you want to approve '{self.pack.name}'?",
            color=discord.Color.green()
        )
        
        embed.add_field(name="📦 Pack Details", value=f"Name: {self.pack.name}\nGenre: {self.pack.genre}\nArtists: {len(self.pack.artist_ids) if self.pack.artist_ids else 0}", inline=False)
        embed.add_field(name="💰 Payment Action", value="Capture payment and activate pack", inline=False)
        embed.add_field(name="⚠️ Warning", value="This will capture the $9.99 payment and make the pack available for opening", inline=False)
        
        view = ApproveConfirmView(self.pack, self.admin_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Reject", style=ButtonStyle.danger, emoji="❌")
    async def reject_button(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(RejectModal(self.pack, self.admin_id))
    
    @discord.ui.button(label="Message Creator", style=ButtonStyle.secondary, emoji="💬")
    async def message_creator_button(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(MessageCreatorModal(self.pack, self.admin_id))
    
    @discord.ui.button(label="Back to Queue", style=ButtonStyle.secondary, emoji="◀️")
    async def back_button(self, interaction: Interaction, button: Button):
        # Get pending packs again
        pending_packs = CreatorPack.get_pending(limit=50)
        await admin_review_panel.show_queue_screen(interaction, pending_packs)


class ApproveConfirmView(View):
    def __init__(self, pack: CreatorPack, admin_id: int):
        super().__init__(timeout=60)
        self.pack = pack
        self.admin_id = admin_id
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.admin_id and interaction.user.guild_permissions.manage_guild
    
    @discord.ui.button(label="Confirm Capture", style=ButtonStyle.success, emoji="💰")
    async def confirm_capture(self, interaction: Interaction, button: Button):
        try:
            # Approve and capture payment
            success = admin_payment_actions.approve_and_capture(str(self.pack.id), self.admin_id)
            
            if success:
                # Get updated pack info
                updated_pack = CreatorPack.get_by_id(str(self.pack.id))
                
                embed = Embed(
                    title="✅ Pack Approved!",
                    description=f"'{self.pack.name}' has been approved and payment captured.",
                    color=discord.Color.green()
                )
                
                embed.add_field(name="📦 Pack Status", value="✅ Approved & Active", inline=True)
                embed.add_field(name="💳 Payment Status", value="💰 Captured", inline=True)
                embed.add_field(name="💰 Amount", value=f"${self.pack.price_cents / 100:.2f}", inline=True)
                
                # Notify admin channel
                await self._notify_admin_channel(updated_pack)
                
                # Notify creator
                await self._notify_creator(updated_pack)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("❌ Failed to approve and capture payment", ephemeral=True)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Error approving pack: {e}", ephemeral=True)
    
    @discord.ui.button(label="Cancel", style=ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("Approval cancelled", ephemeral=True)
    
    async def _notify_admin_channel(self, pack: CreatorPack):
        """Notify admin channel about approval"""
        try:
            # Find admin notification channel
            guild = self.bot.get_guild(pack.owner_id)  # This would need to be adjusted
            if guild:
                # Look for a channel named "admin-log" or similar
                admin_channel = discord.utils.get(guild.text_channels, name="admin-log")
                if not admin_channel:
                    admin_channel = discord.utils.get(guild.text_channels, name="admin-logs")
                
                if admin_channel:
                    embed = Embed(
                        title="📦 Pack Approved",
                        description=f"Creator pack has been approved and activated",
                        color=discord.Color.green()
                    )
                    
                    embed.add_field(name="Pack Name", value=pack.name, inline=True)
                    embed.add_field(name="Pack ID", value=str(pack.id)[:8], inline=True)
                    embed.add_field(name="Approved By", value=str(self.admin_id), inline=True)
                    embed.add_field(name="Payment Captured", value=f"${pack.price_cents / 100:.2f}", inline=True)
                    
                    await admin_channel.send(embed=embed)
        except Exception as e:
            print(f"Error notifying admin channel: {e}")
    
    async def _notify_creator(self, pack: CreatorPack):
        """Notify creator about approval"""
        try:
            # Get creator user
            creator = self.bot.get_user(pack.owner_id)
            if creator:
                embed = Embed(
                    title="✅ Your Pack Was Approved!",
                    description=f"Your creator pack '{pack.name}' has been approved and is now live!",
                    color=discord.Color.green()
                )
                
                embed.add_field(name="📦 Pack Name", value=pack.name, inline=True)
                embed.add_field(name="🎼 Genre", value=pack.genre, inline=True)
                embed.add_field(name="💰 Price", value=f"${pack.price_cents / 100:.2f}", inline=True)
                embed.add_field(name="📊 Status", value="✅ Approved & Available", inline=False)
                embed.add_field(name="🎮 Next Steps", value="You can now open your pack to collect cards! Use `/creator_dashboard` to manage your packs.", inline=False)
                
                await creator.send(embed=embed)
        except Exception as e:
            print(f"Error notifying creator: {e}")


class RejectModal(Modal):
    def __init__(self, pack: CreatorPack, admin_id: int):
        super().__init__(title="Reject Pack")
        self.pack = pack
        self.admin_id = admin_id
        
        self.add_item(InputText(
            label="Rejection Reason",
            placeholder="Provide a clear reason for rejection...",
            style=discord.InputTextStyle.long,
            required=True
        ))
    
    async def callback(self, interaction: Interaction):
        try:
            reason = self.children[0].value.strip()
            
            if not reason:
                await interaction.response.send_message("❌ Rejection reason is required", ephemeral=True)
                return
            
            # Reject and void payment
            success = admin_payment_actions.reject_and_void(str(self.pack.id), self.admin_id, reason)
            
            if success:
                embed = Embed(
                    title="❌ Pack Rejected",
                    description=f"'{self.pack.name}' has been rejected and payment voided.",
                    color=discord.Color.red()
                )
                
                embed.add_field(name="📦 Pack Status", value="❌ Rejected", inline=True)
                embed.add_field(name="💳 Payment Status", value="💸 Voided", inline=True)
                embed.add_field(name="📝 Reason", value=reason, inline=False)
                
                # Notify creator
                await self._notify_creator(reason)
                
                # Log to audit
                await self._log_rejection(reason)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("❌ Failed to reject and void payment", ephemeral=True)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Error rejecting pack: {e}", ephemeral=True)
    
    async def _notify_creator(self, reason: str):
        """Notify creator about rejection"""
        try:
            creator = self.bot.get_user(self.pack.owner_id)
            if creator:
                embed = Embed(
                    title="❌ Your Pack Was Rejected",
                    description=f"Your creator pack '{self.pack.name}' was not approved.",
                    color=discord.Color.red()
                )
                
                embed.add_field(name="📦 Pack Name", value=self.pack.name, inline=True)
                embed.add_field(name="🎼 Genre", value=self.pack.genre, inline=True)
                embed.add_field(name="📝 Reason", value=reason, inline=False)
                embed.add_field(name="💰 Payment", value="Your payment has been refunded", inline=True)
                embed.add_field(name="🔄 Next Steps", value="You can edit your pack and resubmit for review. Use `/creator_dashboard` to manage your packs.", inline=False)
                
                await creator.send(embed=embed)
        except Exception as e:
            print(f"Error notifying creator about rejection: {e}")
    
    async def _log_rejection(self, reason: str):
        """Log rejection to audit"""
        try:
            # This would log to your audit system
            print(f"AUDIT: Pack {self.pack.id} rejected by admin {self.admin_id}. Reason: {reason}")
        except Exception as e:
            print(f"Error logging rejection: {e}")


class MessageCreatorModal(Modal):
    def __init__(self, pack: CreatorPack, admin_id: int):
        super().__init__(title="Message Creator")
        self.pack = pack
        self.admin_id = admin_id
        
        self.add_item(InputText(
            label="Message",
            placeholder="Enter your message to the pack creator...",
            style=discord.InputTextStyle.long,
            required=True
        ))
    
    async def callback(self, interaction: Interaction):
        try:
            message = self.children[0].value.strip()
            
            if not message:
                await interaction.response.send_message("❌ Message is required", ephemeral=True)
                return
            
            # Send message to creator
            creator = self.bot.get_user(self.pack.owner_id)
            if creator:
                embed = Embed(
                    title="💬 Message from Admin",
                    description=f"Regarding your pack '{self.pack.name}'",
                    color=discord.Color.blue()
                )
                
                embed.add_field(name="📝 Message", value=message, inline=False)
                embed.add_field(name="👤 Sent By", value=f"Admin ID: {self.admin_id}", inline=True)
                
                await creator.send(embed=embed)
                
                await interaction.response.send_message("✅ Message sent to creator", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Could not find creator user", ephemeral=True)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Error sending message: {e}", ephemeral=True)


# Global instance for access
admin_review_panel = AdminReviewPanel(None)


async def setup(bot):
    await bot.add_cog(AdminReviewPanel(bot))
