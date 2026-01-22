# commands/enhanced_admin_review.py
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
from discord import Embed, ButtonStyle
from services.creator_moderation import review_pack
from services.creator_preview import build_preview
from models.creator_pack import CreatorPack

class ReviewView(View):

    def __init__(self, pack_id):
        super().__init__(timeout=180)
        self.pack_id = pack_id

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, emoji="✅")
    async def approve(self, interaction, button):

        review_pack(self.pack_id, interaction.user.id, True)

        await interaction.response.send_message(
            "✅ Pack approved and captured.",
            ephemeral=True
        )

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject(self, interaction, button):

        review_pack(self.pack_id, interaction.user.id, False, "Rejected")

        await interaction.response.send_message(
            "❌ Pack rejected and voided.",
            ephemeral=True
        )

    @discord.ui.button(label="Message Creator", style=discord.ButtonStyle.secondary, emoji="💬")
    async def message_creator(self, interaction, button):
        await interaction.response.send_modal(MessageCreatorModal(self.pack_id))

    @discord.ui.button(label="Back to Queue", style=discord.ButtonStyle.secondary, emoji="◀️")
    async def back_to_queue(self, interaction, button):
        await show_queue_screen(interaction)


class MessageCreatorModal(Modal, title="Message Creator"):
    def __init__(self, pack_id):
        super().__init__()
        self.pack_id = pack_id
        
        self.message = TextInput(
            label="Message",
            placeholder="Enter your message to the pack creator...",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        # Get pack info
        pack = CreatorPack.get_by_id(self.pack_id)
        if not pack:
            await interaction.response.send_message("❌ Pack not found", ephemeral=True)
            return
        
        # Send message to creator (placeholder implementation)
        creator = interaction.client.get_user(pack.owner_id)
        if creator:
            embed = Embed(
                title="💬 Message from Admin",
                description=f"Regarding your pack '{pack.name}'",
                color=discord.Color.blue()
            )
            embed.add_field(name="📝 Message", value=self.message.value, inline=False)
            embed.add_field(name="👤 Sent By", value=f"<@{interaction.user.id}>", inline=True)
            
            try:
                await creator.send(embed=embed)
                await interaction.response.send_message("✅ Message sent to creator", ephemeral=True)
            except:
                await interaction.response.send_message("❌ Could not send message to creator", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Creator not found", ephemeral=True)


class QueueView(View):
    def __init__(self, admin_id, page=0):
        super().__init__(timeout=300)
        self.admin_id = admin_id
        self.page = page

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction, button):
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(
                embed=queue_embed(self.admin_id, self.page),
                view=self
            )
        else:
            await interaction.response.defer()

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction, button):
        self.page += 1
        await interaction.response.edit_message(
            embed=queue_embed(self.admin_id, self.page),
            view=self
        )

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh(self, interaction, button):
        await interaction.response.edit_message(
            embed=queue_embed(self.admin_id, self.page),
            view=self
        )

    # Dynamic review buttons for first few packs
    def __init__(self, admin_id, page=0):
        super().__init__(timeout=300)
        self.admin_id = admin_id
        self.page = page
        
        # Get pending packs for this page
        pending_packs = CreatorPack.get_pending(limit=50)
        start_idx = self.page * 10
        end_idx = min(start_idx + 10, len(pending_packs))
        page_packs = pending_packs[start_idx:end_idx]
        
        # Add review buttons for first 5 packs
        for i, pack in enumerate(page_packs[:5]):
            button = Button(
                label=f"Review #{i+1}",
                style=discord.ButtonStyle.primary,
                custom_id=f"review_{pack.id}"
            )
            button.callback = self.create_review_callback(pack)
            self.add_item(button)

    def create_review_callback(self, pack):
        async def review_callback(interaction):
            await show_pack_review(interaction, pack)
        return review_callback


def queue_embed(admin_id, page):
    """Generate queue embed for admin review"""
    
    pending_packs = CreatorPack.get_pending(limit=50)
    
    if not pending_packs:
        embed = Embed(
            title="🛡️ Admin Review Queue",
            description="No packs pending review!",
            color=discord.Color.green()
        )
        embed.add_field(name="📊 Status", value="All caught up! No packs require review.", inline=False)
        return embed
    
    # Pagination
    start_idx = page * 10
    end_idx = min(start_idx + 10, len(pending_packs))
    page_packs = pending_packs[start_idx:end_idx]
    total_pages = (len(pending_packs) + 9) // 10
    
    embed = Embed(
        title="🛡️ Admin Review Queue",
        description=f"**Pending Packs:** {len(pending_packs)} total (Page {page + 1}/{total_pages})",
        color=discord.Color.orange()
    )
    
    for i, pack in enumerate(page_packs, start=start_idx + 1):
        # Get basic info
        artist_count = len(pack.artist_ids) if pack.artist_ids else 0
        
        # Try to get quality score
        quality_text = ""
        try:
            preview = build_preview(str(pack.id))
            if preview and preview.get('quality_score'):
                quality_text = f" | ⭐ {preview['quality_score']}/100"
        except:
            pass
        
        field_value = f"🎼 {pack.genre} | 🎵 {artist_count} artists{quality_text}\n"
        field_value += f"💳 {pack.payment_status.title()} | 💰 ${pack.price_cents / 100:.2f}\n"
        field_value += f"📅 Created: {pack.created_at.strftime('%Y-%m-%d') if pack.created_at else 'Unknown'}"
        
        embed.add_field(
            name=f"{i}. {pack.name}",
            value=field_value,
            inline=False
        )
    
    embed.set_footer(text=f"Use /review <pack_id> to review a specific pack")
    return embed


async def show_queue_screen(interaction):
    """Show admin review queue"""
    await interaction.response.edit_message(
        embed=queue_embed(interaction.user.id, 0),
        view=QueueView(interaction.user.id)
    )


async def show_pack_review(interaction, pack):
    """Show pack review interface"""
    
    data = build_preview(str(pack.id))
    
    if not data:
        await interaction.response.send_message("❌ Could not generate preview", ephemeral=True)
        return
    
    # Create review embed
    e = Embed(title=f"🔍 Review – {data['name']}", color=discord.Color.blue())
    e.add_field(name="🆔 Pack ID", value=str(pack.id)[:8], inline=True)
    e.add_field(name="🎼 Genre", value=data["genre"], inline=True)
    e.add_field(name="💳 Payment", value=data["payment"], inline=True)
    e.add_field(name="🎵 Artists", value=str(len(data.get("artists", []))), inline=True)
    
    # Add quality score if available
    if data.get('quality_score'):
        e.add_field(name="⭐ Quality", value=f"{data['quality_score']}/100 ({data.get('quality_rating', 'Unknown')})", inline=True)
    
    # Add tier distribution
    tier_dist = data.get('tier_distribution', {})
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
        
        e.add_field(name="🎯 Tiers", value=" ".join(tier_text), inline=True)
    
    # Add artists (first 5)
    artists = data.get("artists", [])
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
            }.get(artist.get('estimated_tier', ''), "❓")
            
            artist_text += f"{i}. {tier_emoji} **{artist['name']}** ({artist.get('estimated_tier', 'Unknown')})\n"
            artist_text += f"   🎼 {artist['genre']} | 👥 {artist.get('popularity', 0)}\n"
        
        if len(artists) > 5:
            artist_text += f"... and {len(artists) - 5} more artists"
        
        e.add_field(name="🎵 Artist Preview", value=artist_text, inline=False)
    
    # Add safety check
    try:
        from services.safety_checks import safety_checks
        safe, safety_message = safety_checks.safe_images(data)
        
        safety_emoji = "✅" if safe else "❌"
        e.add_field(name="🛡️ Safety Check", value=f"{safety_emoji} {safety_message}", inline=True)
    except:
        pass
    
    await interaction.response.send_message(embed=e, view=ReviewView(str(pack.id)), ephemeral=True)


@bot.slash_command(name="review")
@discord.default_permissions(manage_guild=True)
async def review(ctx, pack_id: str = None):
    """Review a creator pack or show queue"""
    
    if pack_id:
        # Review specific pack
        pack = CreatorPack.get_by_id(pack_id)
        if not pack:
            await ctx.respond(f"❌ Pack not found: {pack_id}", ephemeral=True)
            return
        
        if pack.status != "pending":
            await ctx.respond(f"❌ Pack is not pending review: {pack.status}", ephemeral=True)
            return
        
        await show_pack_review(ctx, pack)
    else:
        # Show review queue
        await ctx.respond(
            embed=queue_embed(ctx.author.id, 0),
            view=QueueView(ctx.author.id),
            ephemeral=True
        )


@bot.slash_command(name="admin_queue")
@discord.default_permissions(manage_guild=True)
async def admin_queue(ctx):
    """Show admin review queue"""
    
    await ctx.respond(
        embed=queue_embed(ctx.author.id, 0),
        view=QueueView(ctx.author.id),
        ephemeral=True
    )
