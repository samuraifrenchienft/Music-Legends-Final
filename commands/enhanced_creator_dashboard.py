# commands/enhanced_creator_dashboard.py
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
from services.creator_service import create_creator_pack, get_user_packs, update_pack, delete_pack
from services.creator_preview import build_preview
from models.creator_pack import CreatorPack

# ---------- MODAL FOR NEW PACK ----------

class CreatePackModal(Modal, title="Create Creator Pack"):

    name = TextInput(label="Pack Name", max_length=40, placeholder="Enter pack name...")
    genre = TextInput(label="Genre", max_length=20, placeholder="e.g., Rock, Pop, Jazz...")
    artists = TextInput(
        label="Artists (comma separated)",
        style=discord.TextStyle.paragraph,
        placeholder="Artist 1, Artist 2, Artist 3..."
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            artist_list = [a.strip() for a in self.artists.value.split(",")]
            
            pack = create_creator_pack(
                interaction.user.id,
                self.name.value,
                artist_list,
                self.genre.value
            )

            await interaction.response.send_message(
                f"✅ Pack **{pack.name}** submitted for review!\n"
                f"🎼 Genre: {pack.genre}\n"
                f"🎵 Artists: {len(artist_list)}\n"
                f"📊 Status: {pack.status}",
                ephemeral=True
            )
        except ValueError as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to create pack: {e}", ephemeral=True)


# ---------- EDIT PACK MODAL ----------

class EditPackModal(Modal, title="Edit Creator Pack"):

    def __init__(self, pack: CreatorPack):
        super().__init__()
        self.pack = pack
        
        self.name = TextInput(
            label="Pack Name", 
            max_length=40, 
            default=pack.name,
            placeholder="Enter pack name..."
        )
        self.genre = TextInput(
            label="Genre", 
            max_length=20, 
            default=pack.genre,
            placeholder="e.g., Rock, Pop, Jazz..."
        )
        self.artists = TextInput(
            label="Artists (comma separated)",
            style=discord.TextStyle.paragraph,
            default=", ".join(pack.artist_ids) if pack.artist_ids else "",
            placeholder="Artist 1, Artist 2, Artist 3..."
        )
        
        self.add_item(self.name)
        self.add_item(self.genre)
        self.add_item(self.artists)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            artist_list = [a.strip() for a in self.artists.value.split(",")]
            
            updated_pack = update_pack(
                pack_id=str(self.pack.id),
                name=self.name.value,
                artists=artist_list,
                genre=self.genre.value
            )

            if updated_pack:
                await interaction.response.send_message(
                    f"✅ Pack **{updated_pack.name}** updated successfully!",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message("❌ Failed to update pack", ephemeral=True)
                
        except ValueError as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to update pack: {e}", ephemeral=True)


# ---------- ENHANCED DASHBOARD VIEW ----------

class EnhancedDashboardView(View):

    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.button(label="Create New Pack", style=discord.ButtonStyle.primary, emoji="➕")
    async def create(self, interaction, button):
        await interaction.response.send_modal(CreatePackModal())

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh(self, interaction, button):
        await interaction.response.edit_message(
            embed=dashboard_embed(self.user_id),
            view=self
        )

    @discord.ui.select(
        placeholder="Select a pack to manage...",
        custom_id="pack_select"
    )
    async def pack_select(self, interaction, select):
        pack_id = select.values[0]
        pack = CreatorPack.get_by_id(pack_id)
        
        if not pack or pack.owner_id != self.user_id:
            await interaction.response.send_message("❌ Pack not found", ephemeral=True)
            return
        
        await self.show_pack_actions(interaction, pack)
    
    async def show_pack_actions(self, interaction, pack):
        """Show pack-specific actions"""
        status_emoji = {
            "pending": "🟡",
            "approved": "🟢",
            "rejected": "🔴",
            "disabled": "⚫"
        }.get(pack.status, "⚪")
        
        embed = discord.Embed(
            title=f"{status_emoji} {pack.name}",
            description=f"Pack ID: {str(pack.id)[:8]}",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="🎼 Genre", value=pack.genre, inline=True)
        embed.add_field(name="📊 Status", value=f"{status_emoji} {pack.status.title()}", inline=True)
        embed.add_field(name="🎵 Artists", value=str(len(pack.artist_ids) if pack.artist_ids else 0), inline=True)
        embed.add_field(name="💰 Price", value=f"${pack.price_cents / 100:.2f}", inline=True)
        embed.add_field(name="📦 Purchases", value=str(pack.purchase_count), inline=True)
        
        if pack.created_at:
            embed.add_field(name="📅 Created", value=pack.created_at.strftime("%Y-%m-%d"), inline=True)
        
        if pack.notes:
            embed.add_field(name="📝 Notes", value=pack.notes, inline=False)
        
        if pack.rejection_reason:
            embed.add_field(name="❌ Rejection Reason", value=pack.rejection_reason, inline=False)
        
        # Create action buttons based on status
        view = PackActionsView(pack, self.user_id)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class PackActionsView(View):
    def __init__(self, pack: CreatorPack, user_id: int):
        super().__init__(timeout=300)
        self.pack = pack
        self.user_id = user_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @discord.ui.button(label="Preview", style=discord.ButtonStyle.primary, emoji="👁️")
    async def preview(self, interaction, button):
        try:
            preview = build_preview(str(self.pack.id))
            
            if not preview:
                await interaction.response.send_message("❌ Could not generate preview", ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"👁️ Preview: {self.pack.name}",
                description=f"Quality: {preview['quality_score']}/100 ({preview['quality_rating']})",
                color=discord.Color.blue()
            )
            
            # Show artists
            for i, artist in enumerate(preview['artists'][:5], 1):
                tier_emoji = {
                    "legendary": "🏆",
                    "platinum": "💎",
                    "gold": "🥇",
                    "silver": "🥈",
                    "bronze": "🥉",
                    "community": "👥"
                }.get(artist['estimated_tier'], "❓")
                
                embed.add_field(
                    name=f"{i}. {tier_emoji} {artist['name']}",
                    value=f"Genre: {artist['genre']} | Tier: {artist['estimated_tier']}",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error generating preview: {e}", ephemeral=True)
    
    @discord.ui.button(label="Edit", style=discord.ButtonStyle.secondary, emoji="✏️")
    async def edit(self, interaction, button):
        if self.pack.status not in ["pending", "rejected"]:
            await interaction.response.send_message("❌ Can only edit pending or rejected packs", ephemeral=True)
            return
        
        await interaction.response.send_modal(EditPackModal(self.pack))
    
    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete(self, interaction, button):
        if self.pack.status == "approved":
            await interaction.response.send_message("❌ Cannot delete approved packs", ephemeral=True)
            return
        
        # Confirmation
        embed = discord.Embed(
            title="🗑️ Delete Pack",
            description=f"Are you sure you want to delete **{self.pack.name}**?",
            color=discord.Color.red()
        )
        
        embed.add_field(name="⚠️ Warning", value="This action cannot be undone!", inline=False)
        
        view = DeleteConfirmView(self.pack, self.user_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class DeleteConfirmView(View):
    def __init__(self, pack: CreatorPack, user_id: int):
        super().__init__(timeout=60)
        self.pack = pack
        self.user_id = user_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm_delete(self, interaction, button):
        try:
            success = delete_pack(str(self.pack.id))
            
            if success:
                await interaction.response.send_message(
                    f"✅ Pack **{self.pack.name}** deleted successfully!",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message("❌ Failed to delete pack", ephemeral=True)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Error deleting pack: {e}", ephemeral=True)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        await interaction.response.send_message("Pack deletion cancelled", ephemeral=True)


def dashboard_embed(user_id):

    packs = get_user_packs(user_id)

    e = discord.Embed(title="🎨 Your Creator Packs", color=discord.Color.blue())

    if not packs:
        e.description = "You haven't created any packs yet!\nClick **Create New Pack** to get started."
        return e

    for p in packs:
        icon = {
            "pending": "🟡",
            "approved": "🟢",
            "rejected": "🔴",
            "disabled": "⚫"
        }.get(p.status, "⚪")

        payment_emoji = {
            "authorized": "💳",
            "captured": "💰",
            "failed": "❌",
            "refunded": "💸"
        }.get(p.payment_status, "❓")

        value = f"🎼 {p.genre} | 🎵 {len(p.artist_ids) if p.artist_ids else 0} artists\n"
        value += f"📊 {icon} {p.status.title()} | {payment_emoji} {p.payment_status.title()}\n"
        value += f"💰 ${p.price_cents / 100:.2f} | 📦 {p.purchase_count} purchases"

        e.add_field(
            name=f"{icon} {p.name}",
            value=value,
            inline=False
        )

    e.set_footer(text=f"Total packs: {len(packs)}")
    return e


# ---------- ENHANCED COMMAND ----------

@bot.slash_command(name="creator")
async def creator(ctx):
    """Enhanced creator dashboard command"""
    
    packs = get_user_packs(ctx.author.id)
    
    # Create view with pack selection if user has packs
    if packs:
        view = EnhancedDashboardView(ctx.author.id)
        
        # Add pack options to select menu
        pack_options = []
        for pack in packs:
            status_emoji = {
                "pending": "🟡",
                "approved": "🟢",
                "rejected": "🔴",
                "disabled": "⚫"
            }.get(pack.status, "⚪")
            
            option = discord.SelectOption(
                label=f"{pack.name}",
                description=f"{status_emoji} {pack.status} | {len(pack.artist_ids) if pack.artist_ids else 0} artists",
                value=str(pack.id),
                emoji=status_emoji
            )
            pack_options.append(option)
        
        # Add select menu to view
        pack_select = discord.ui.Select(
            placeholder="Select a pack to manage...",
            options=pack_options[:25],  # Discord limit
            custom_id="pack_select"
        )
        pack_select.callback = view.pack_select
        view.add_item(pack_select)
        
        await ctx.respond(
            embed=dashboard_embed(ctx.author.id),
            view=view,
            ephemeral=True
        )
    else:
        # No packs, show simple view
        view = View()
        view.add_item(Button(label="Create New Pack", style=discord.ButtonStyle.primary, emoji="➕"))
        view.children[0].callback = lambda interaction: interaction.response.send_modal(CreatePackModal())
        
        await ctx.respond(
            embed=dashboard_embed(ctx.author.id),
            view=view,
            ephemeral=True
        )
