# cogs/cosmetic_shop.py
"""
Cosmetic Shop and Customization Commands
"""

import discord
from discord.ext import commands
from discord import app_commands, Interaction
from database import DatabaseManager
from services.cosmetic_manager import get_cosmetic_manager
from typing import List, Dict


class CosmeticShopView(discord.ui.View):
    """View for browsing and purchasing cosmetics"""
    
    def __init__(self, user_id: int, cosmetics: List[Dict], page: int = 0):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.cosmetics = cosmetics
        self.page = page
        self.per_page = 5
    
    def get_page_cosmetics(self) -> List[Dict]:
        """Get cosmetics for current page"""
        start = self.page * self.per_page
        end = start + self.per_page
        return self.cosmetics[start:end]
    
    def create_embed(self) -> discord.Embed:
        """Create embed for current page"""
        embed = discord.Embed(
            title="🎨 Cosmetic Shop",
            description="Browse and purchase cosmetics for your cards!",
            color=discord.Color.purple()
        )
        
        page_cosmetics = self.get_page_cosmetics()
        
        for cosmetic in page_cosmetics:
            # Price info
            price_text = ""
            if cosmetic['price_gold']:
                price_text = f"💰 {cosmetic['price_gold']} Gold"
            elif cosmetic['price_tickets']:
                price_text = f"🎫 {cosmetic['price_tickets']} Tickets"
            elif cosmetic['unlock_method'] == 'vip_only':
                price_text = "👑 VIP Only"
            else:
                price_text = "Free"
            
            # Rarity emoji
            rarity_emoji = {
                'common': '⚪',
                'rare': '🔵',
                'epic': '🟣',
                'legendary': '🟡'
            }.get(cosmetic['rarity'], '⚪')
            
            embed.add_field(
                name=f"{rarity_emoji} {cosmetic['name']}",
                value=f"{cosmetic['description']}\n**Price:** {price_text}\n**ID:** `{cosmetic['cosmetic_id']}`",
                inline=False
            )
        
        # Page info
        total_pages = (len(self.cosmetics) - 1) // self.per_page + 1
        embed.set_footer(text=f"Page {self.page + 1}/{total_pages} • Use /purchase_cosmetic to buy")
        
        return embed
    
    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your shop!", ephemeral=True)
            return
        
        if self.page > 0:
            self.page -= 1
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your shop!", ephemeral=True)
            return
        
        total_pages = (len(self.cosmetics) - 1) // self.per_page + 1
        if self.page < total_pages - 1:
            self.page += 1
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()


class CustomizeCardView(discord.ui.View):
    """View for customizing a specific card"""
    
    def __init__(self, user_id: int, card_id: str, user_cosmetics: List[Dict]):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.card_id = card_id
        self.user_cosmetics = user_cosmetics
        
        # Add select menus for frames and effects
        self.add_frame_select()
        self.add_effect_select()
    
    def add_frame_select(self):
        """Add frame selection dropdown"""
        frames = [c for c in self.user_cosmetics if c['cosmetic_type'] == 'frame']
        
        if not frames:
            return
        
        options = [
            discord.SelectOption(
                label=frame['name'],
                description=frame['description'][:100],
                value=frame['cosmetic_id']
            )
            for frame in frames[:25]  # Discord limit
        ]
        
        if options:
            select = discord.ui.Select(
                placeholder="Select Frame Style",
                options=options,
                custom_id="frame_select"
            )
            select.callback = self.frame_selected
            self.add_item(select)
    
    def add_effect_select(self):
        """Add effect selection dropdown"""
        effects = [c for c in self.user_cosmetics if c['cosmetic_type'] == 'effect']
        
        if not effects:
            return
        
        options = [
            discord.SelectOption(
                label=effect['name'],
                description=effect['description'][:100],
                value=effect['cosmetic_id']
            )
            for effect in effects[:25]  # Discord limit
        ]
        
        if options:
            select = discord.ui.Select(
                placeholder="Select Foil Effect",
                options=options,
                custom_id="effect_select"
            )
            select.callback = self.effect_selected
            self.add_item(select)
    
    async def frame_selected(self, interaction: discord.Interaction):
        """Handle frame selection"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your customization!", ephemeral=True)
            return
        
        cosmetic_id = interaction.data['values'][0]
        
        # Extract frame style name from cosmetic_id (e.g., "frame_holographic" -> "holographic")
        frame_style = cosmetic_id.replace('frame_', '')
        
        # Apply cosmetic
        manager = get_cosmetic_manager()
        success = manager.apply_cosmetic_to_card(
            str(self.user_id),
            self.card_id,
            {'frame_style': frame_style}
        )
        
        if success:
            await interaction.response.send_message(
                f"✅ Applied **{frame_style.title()}** frame to your card!",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Failed to apply cosmetic. Please try again.",
                ephemeral=True
            )
    
    async def effect_selected(self, interaction: discord.Interaction):
        """Handle effect selection"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your customization!", ephemeral=True)
            return
        
        cosmetic_id = interaction.data['values'][0]
        
        # Extract foil effect name from cosmetic_id (e.g., "foil_rainbow" -> "rainbow")
        foil_effect = cosmetic_id.replace('foil_', '')
        
        # Apply cosmetic
        manager = get_cosmetic_manager()
        success = manager.apply_cosmetic_to_card(
            str(self.user_id),
            self.card_id,
            {'foil_effect': foil_effect}
        )
        
        if success:
            await interaction.response.send_message(
                f"✅ Applied **{foil_effect.title()}** foil effect to your card!",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Failed to apply cosmetic. Please try again.",
                ephemeral=True
            )


class CosmeticShopCog(commands.Cog):
    """Cog for cosmetic shop and customization"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.manager = get_cosmetic_manager(self.db)
    
    @app_commands.command(name="cosmetic_shop", description="Browse and purchase card cosmetics")
    async def cosmetic_shop(self, interaction: Interaction):
        """Show the cosmetic shop"""
        await interaction.response.defer()
        
        try:
            # Get available cosmetics (not yet unlocked)
            cosmetics = self.manager.get_available_cosmetics(
                user_id=str(interaction.user.id),
                filter_unlocked=True
            )
            
            if not cosmetics:
                embed = discord.Embed(
                    title="🎨 Cosmetic Shop",
                    description="You've unlocked all available cosmetics! 🎉",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create shop view
            view = CosmeticShopView(interaction.user.id, cosmetics)
            embed = view.create_embed()
            
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"Error in cosmetic_shop: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send("❌ Error loading shop. Please try again later.", ephemeral=True)
    
    @app_commands.command(name="purchase_cosmetic", description="Purchase a cosmetic")
    @app_commands.describe(cosmetic_id="The ID of the cosmetic to purchase")
    async def purchase_cosmetic(self, interaction: Interaction, cosmetic_id: str):
        """Purchase a specific cosmetic"""
        await interaction.response.defer()
        
        try:
            success, message = self.manager.purchase_cosmetic(str(interaction.user.id), cosmetic_id)
            
            if success:
                embed = discord.Embed(
                    title="✅ Purchase Successful!",
                    description=message,
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="❌ Purchase Failed",
                    description=message,
                    color=discord.Color.red()
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            print(f"Error in purchase_cosmetic: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send("❌ Error processing purchase. Please try again.", ephemeral=True)
    
    @app_commands.command(name="customize_card", description="Customize a card's appearance")
    @app_commands.describe(card_id="The ID of the card to customize")
    async def customize_card(self, interaction: Interaction, card_id: str):
        """Customize a specific card"""
        await interaction.response.defer()
        
        try:
            # Get user's unlocked cosmetics
            user_cosmetics = self.manager.get_user_cosmetics(str(interaction.user.id))
            
            if not user_cosmetics:
                embed = discord.Embed(
                    title="🎨 No Cosmetics",
                    description="You haven't unlocked any cosmetics yet!\nUse `/cosmetic_shop` to browse available options.",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create customization view
            view = CustomizeCardView(interaction.user.id, card_id, user_cosmetics)
            
            embed = discord.Embed(
                title=f"🎨 Customize Card",
                description=f"**Card ID:** `{card_id}`\n\nSelect cosmetics to apply to this card!",
                color=discord.Color.purple()
            )
            
            embed.add_field(
                name="📋 Your Unlocked Cosmetics",
                value=f"**Frames:** {len([c for c in user_cosmetics if c['cosmetic_type'] == 'frame'])}\n"
                      f"**Effects:** {len([c for c in user_cosmetics if c['cosmetic_type'] == 'effect'])}",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"Error in customize_card: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send("❌ Error loading customization. Please try again.", ephemeral=True)
    
    @app_commands.command(name="my_cosmetics", description="View your unlocked cosmetics")
    async def my_cosmetics(self, interaction: Interaction):
        """Show user's unlocked cosmetics"""
        await interaction.response.defer()
        
        try:
            cosmetics = self.manager.get_user_cosmetics(str(interaction.user.id))
            
            if not cosmetics:
                embed = discord.Embed(
                    title="🎨 Your Cosmetics",
                    description="You haven't unlocked any cosmetics yet!\nUse `/cosmetic_shop` to browse available options.",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Group by type
            frames = [c for c in cosmetics if c['cosmetic_type'] == 'frame']
            effects = [c for c in cosmetics if c['cosmetic_type'] == 'effect']
            
            embed = discord.Embed(
                title="🎨 Your Unlocked Cosmetics",
                description=f"Total: {len(cosmetics)} cosmetics",
                color=discord.Color.purple()
            )
            
            if frames:
                frame_list = "\n".join([f"• **{f['name']}** - {f['description']}" for f in frames[:10]])
                embed.add_field(name="🖼️ Frames", value=frame_list, inline=False)
            
            if effects:
                effect_list = "\n".join([f"• **{e['name']}** - {e['description']}" for e in effects[:10]])
                embed.add_field(name="✨ Effects", value=effect_list, inline=False)
            
            embed.set_footer(text="Use /customize_card to apply these to your cards!")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            print(f"Error in my_cosmetics: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send("❌ Error loading cosmetics. Please try again.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(CosmeticShopCog(bot))
