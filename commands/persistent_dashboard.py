# commands/persistent_dashboard.py
"""
Persistent Creator Dashboard with State Management
Handles dashboard state across bot restarts
"""

import time
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from discord import Interaction, Embed, ButtonStyle
from ui.state import save_state, load_state, update_state
from services.creator_service import create_creator_pack, get_user_packs
from services.creator_preview import build_preview
from models.creator_pack import CreatorPack

class PersistentDashboardView(View):
    """
    Dashboard View with persistent state
    Maintains user's dashboard state across restarts
    """

    def __init__(self, user_id, state_id=None):
        super().__init__(timeout=None)  # No timeout for persistence
        self.user_id = user_id
        self.state_id = state_id or f"dashboard:{user_id}:{int(time.time())}"
        
        # Load existing state or create new
        existing_state = load_state(self.state_id)
        if existing_state:
            self.page = existing_state.get("page", 0)
            self.selected_pack_id = existing_state.get("selected_pack_id")
            self.filters = existing_state.get("filters", {})
            self.sort_by = existing_state.get("sort_by", "newest")
        else:
            self.page = 0
            self.selected_pack_id = None
            self.filters = {}
            self.sort_by = "newest"
            
            # Save initial state
            self.save_state()

    def save_state(self):
        """Save current dashboard state"""
        state_data = {
            "user": self.user_id,
            "page": self.page,
            "pack_id": self.selected_pack_id,
            "filters": self.filters,
            "sort_by": self.sort_by,
            "last_updated": int(time.time())
        }
        
        save_state(self.state_id, state_data)

    async def interaction_check(self, interaction: Interaction) -> bool:
        """Enhanced interaction check with state validation"""
        try:
            # Load current state
            current_state = load_state(self.state_id)
            
            # Verify user ownership
            if not current_state or current_state.get("user") != self.user_id:
                print(f"❌ Interaction check failed: User mismatch (expected {self.user_id}, got {current_state.get('user')})")
                return False
            
            # Verify state integrity
            if current_state.get("state_id") != self.state_id:
                print(f"❌ Interaction check failed: State ID mismatch (expected {self.state_id}, got {current_state.get('state_id')})")
                return False
            
            # Verify timestamp (optional - for debugging)
            last_updated = current_state.get("last_updated", 0)
            current_time = int(time.time())
            if current_time - last_updated > 86400:  # 24 hours
                print(f"⚠️ State expired for user {self.user_id} (last updated {last_updated})")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Interaction check error: {e}")
            return False

    @discord.ui.button(label="Create New Pack", style=discord.ButtonStyle.primary, emoji="➕")
    async def create(self, interaction: Interaction, button):
        from commands.creator_dashboard import CreatePackModal
        
        await interaction.response.send_modal(CreatePackModal())

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh(self, interaction: Interaction, button):
        await interaction.response.edit_message(
            embed=self.get_dashboard_embed(),
            view=self
        )
        self.save_state()

    @discord.ui.button(label="Previous Page", style=discord.ButtonStyle.secondary, emoji="◀")
    async def previous_page(self, interaction: Interaction, button):
        if self.page > 0:
            self.page -= 1
            self.save_state()
            await interaction.response.edit_message(
                embed=self.get_dashboard_embed(),
                view=self
            )
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Next Page", style=discord.ButtonStyle.secondary, emoji="▶")
    async def next_page(self, interaction: Interaction, button):
        packs = get_user_packs(self.user_id)
        total_pages = (len(packs) + 9) // 10  # 10 packs per page
        
        if self.page < total_pages - 1:
            self.page += 1
            self.save_state()
            await interaction.response.edit_message(
                embed=self.get_dashboard_embed(),
                view=self
            )
        else:
            await interaction.response.defer()

    @discord.ui.select(
        placeholder="Select a pack to manage...",
        custom_id="pack_select"
    )
    async def pack_select(self, interaction: Interaction, select):
        pack_id = select.values[0]
        pack = CreatorPack.get_by_id(pack_id)
        
        if not pack or pack.owner_id != self.user_id:
            await interaction.response.send_message("❌ Pack not found", ephemeral=True)
            return
        
        self.selected_pack_id = pack_id
        self.save_state()
        
        await self.show_pack_details(interaction, pack)

    async def show_pack_details(self, interaction: Interaction, pack):
        """Show detailed pack information"""
        try:
            status_emoji = {
                "pending": "🟡",
                "approved": "🟢",
                "rejected": "🔴",
                "disabled": "⚫"
            }.get(pack.status, "⚪")
            
            embed = Embed(
                title=f"{status_emoji} {pack.name}",
                description=f"Pack ID: {str(pack.id)[:8]}",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="🎼 Genre", value=pack.genre, inline=True)
            embed.add_field(name="📊 Status", value=f"{status_emoji} {pack.status.title()}", inline=True)
            embed.add_field(name="💳 Payment", value=pack.payment_status.title(), inline=True)
            embed.add_field(name="🎵 Artists", value=str(len(pack.artist_ids) if pack.artist_ids else 0), inline=True)
            embed.add_field(name="💰 Price", value=f"${pack.price_cents / 100:.2f}", inline=True)
            embed.add_field(name="📦 Purchases", value=str(pack.purchase_count), inline=True)
            
            # Add quality score if available
            try:
                preview = build_preview(str(pack.id))
                if preview and preview.get('quality_score'):
                    quality_color = {
                        "Excellent": discord.Color.green(),
                        "Good": discord.Color.blue(),
                        "Fair": discord.Color.gold(),
                        "Poor": discord.Color.orange(),
                        "Very Poor": discord.Color.red()
                    }.get(preview['quality_rating'], discord.Color.grey())
                    
                    embed.color = quality_color
                    embed.add_field(name="⭐ Quality", value=f"{preview['quality_score']}/100 ({preview['quality_rating']})", inline=True)
            except:
                pass
            
            # Add timestamps
            if pack.created_at:
                embed.add_field(name="📅 Created", value=pack.created_at.strftime("%Y-%m-%d"), inline=True)
            
            if pack.reviewed_at:
                embed.add_field(name="📅 Reviewed", value=pack.reviewed_at.strftime("%Y-%m-%d"), inline=True)
            
            # Add notes if any
            if pack.notes:
                embed.add_field(name="📝 Notes", value=pack.notes, inline=False)
            
            if pack.rejection_reason:
                embed.add_field(name="❌ Rejection Reason", value=pack.rejection_reason, inline=False)
            
            # Create action buttons
            view = PackActionsView(pack, self.user_id, self.state_id)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error showing pack details: {e}", ephemeral=True)

    def get_dashboard_embed(self):
        """Generate dashboard embed with current state"""
        packs = get_user_packs(self.user_id)
        
        # Apply filters and sorting
        filtered_packs = self.apply_filters(packs)
        sorted_packs = self.apply_sorting(filtered_packs)
        
        # Pagination
        packs_per_page = 10
        start_idx = self.page * packs_per_page
        end_idx = min(start_idx + packs_per_page, len(sorted_packs))
        page_packs = sorted_packs[start_idx:end_idx]
        
        embed = Embed(
            title="🎨 Your Creator Packs",
            description=f"Total packs: {len(packs)} | Page {self.page + 1}/{(len(packs) + 9) // 10 if packs else 1}",
            color=discord.Color.blue()
        )
        
        if not packs:
            embed.description = "You haven't created any packs yet!\nClick **Create New Pack** to get started."
            return embed
        
        # Add pack fields
        for pack in page_packs:
            status_emoji = {
                "pending": "🟡",
                "approved": "🟢",
                "rejected": "🔴",
                "disabled": "⚫"
            }.get(pack.status, "⚪")
            
            payment_emoji = {
                "authorized": "💳",
                "captured": "💰",
                "failed": "❌",
                "refunded": "💸"
            }.get(pack.payment_status, "❓")
            
            value = f"🎼 {pack.genre} | 🎵 {len(pack.artist_ids) if pack.artist_ids else 0} artists\n"
            value += f"📊 {status_emoji} {pack.status.title()} | {payment_emoji} {pack.payment_status.title()}\n"
            value += f"💰 ${pack.price_cents / 100:.2f} | 📦 {pack.purchase_count} purchases"
            
            embed.add_field(
                name=f"{status_emoji} {pack.name}",
                value=value,
                inline=False
            )
        
        # Add filter/sort info if applied
        filter_info = []
        if self.filters:
            for key, value in self.filters.items():
                if value:
                    filter_info.append(f"{key}: {value}")
        
        if self.sort_by != "newest":
            filter_info.append(f"sort: {self.sort_by}")
        
        if filter_info:
            embed.set_footer(text(" | ".join(filter_info))
        
        return embed

    def apply_filters(self, packs):
        """Apply filters to pack list"""
        filtered = packs.copy()
        
        # Apply status filter
        if self.filters.get("status"):
            filtered = [p for p in filtered if p.status == self.filters["status"]]
        
        # Apply genre filter
        if self.filters.get("genre"):
            filtered = [p for p in filtered if p.genre.lower() == self.filters["genre"].lower()]
        
        # Apply payment status filter
        if self.filters.get("payment_status"):
            filtered = [p for p in filtered if p.payment_status == self.filters["payment_status"]]
        
        return filtered

    def apply_sorting(self, packs):
        """Apply sorting to pack list"""
        if self.sort_by == "newest":
            return sorted(packs, key=lambda x: x.created_at or 0, reverse=True)
        elif self.sort_by == "oldest":
            return sorted(packs, key=lambda x: x.created_at or 0)
        elif self.sort_by == "name":
            return sorted(packs, key=lambda x: x.name.lower())
        elif self.sort_by == "genre":
            return sorted(packs, key=lambda x: x.genre.lower())
        elif self.sort_by == "price":
            return sorted(packs, key=lambda x: x.price_cents)
        elif self.sort_by == "purchases":
            return sorted(packs, key=lambda x: x.purchase_count, reverse=True)
        else:
            return packs


class PackActionsView(View):
    """Actions for individual packs in dashboard"""
    
    def __init__(self, pack: CreatorPack, user_id: int, state_id: str):
        super().__init__(timeout=300)
        self.pack = pack
        self.user_id = user_id
        self.state_id = state_id
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @discord.ui.button(label="Preview", style=discord.ButtonStyle.primary, emoji="👁️")
    async def preview(self, interaction: Interaction, button):
        try:
            preview = build_preview(str(self.pack.id))
            
            if not preview:
                await interaction.response.send_message("❌ Could not generate preview", ephemeral=True)
                return
            
            embed = Embed(
                title=f"👁️ Preview: {self.pack.name}",
                description=f"Quality: {preview['quality_score']}/100 ({preview['quality_rating']})",
                color=discord.Color.blue()
            )
            
            # Show artists (first 5)
            artists = preview.get('artists', [])
            if artists:
                for i, artist in enumerate(artists[:5], 1):
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
    async def edit(self, interaction: Interaction, button):
        if self.pack.status not in ["pending", "rejected"]:
            await interaction.response.send_message("❌ Can only edit pending or rejected packs", ephemeral=True)
            return
        
        from commands.creator_dashboard import EditPackModal
        await interaction.response.send_modal(EditPackModal(self.pack))
    
    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete(self, interaction: Interaction, button):
        if self.pack.status == "approved":
            await interaction.response.send_message("❌ Cannot delete approved packs", ephemeral=True)
            return
        
        # Confirmation
        embed = Embed(
            title="🗑️ Delete Pack",
            description=f"Are you sure you want to delete **{self.pack.name}**?",
            color=discord.Color.red()
        )
        
        embed.add_field(name="⚠️ Warning", value="This action cannot be undone!", inline=False)
        
        view = DeleteConfirmView(self.pack, self.user_id, self.state_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class DeleteConfirmView(View):
    def __init__(self, pack: CreatorPack, user_id: int, state_id: str):
        super().__init__(timeout=60)
        self.pack = pack
        self.user_id = user_id
        self.state_id = state_id
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm_delete(self, interaction: Interaction, button):
        try:
            from services.creator_service import delete_pack
            
            success = delete_pack(str(self.pack.id))
            
            if success:
                # Remove from state
                from ui.state import delete_state
                delete_state(self.state_id)
                
                await interaction.response.send_message(
                    f"✅ Pack **{self.pack.name}** deleted successfully!",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message("❌ Failed to delete pack", ephemeral=True)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Error deleting pack: {e}", ephemeral=True)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button):
        await interaction.response.send_message("Pack deletion cancelled", ephemeral=True)


@bot.slash_command(name="dashboard")
async def dashboard(ctx):
    """Persistent creator dashboard command"""
    
    # Try to restore existing state
    from ui.loader import restore_all_user_states
    
    user_id = ctx.author.id
    restored_states = restore_all_user_states(user_id)
    
    # Find dashboard state
    dashboard_state_id = None
    dashboard_view = None
    
    for state_id, view in restored_states.items():
        if isinstance(view, PersistentDashboardView):
            dashboard_state_id = state_id
            dashboard_view = view
            break
    
    if dashboard_view:
        # Restore existing dashboard
        await ctx.respond(
            embed=dashboard_view.get_dashboard_embed(),
            view=dashboard_view,
            ephemeral=True
        )
    else:
        # Create new dashboard
        dashboard_view = PersistentDashboardView(user_id)
        await ctx.respond(
            embed=dashboard_view.get_dashboard_embed(),
            view=dashboard_view,
            ephemeral=True
        )


@bot.event
async def on_ready():
    """Bot startup - restore user states"""
    print("🔄 Bot starting - checking for saved states...")
    
    # Clean up expired states
    from ui.loader import cleanup_expired_states
    cleanup_expired_states()
    
    # Register views for all online users (placeholder)
    # In a real implementation, you'd need to track online users
    print("🤖 Bot ready - state management system active")
