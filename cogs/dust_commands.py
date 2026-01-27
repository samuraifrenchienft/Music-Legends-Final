# cogs/dust_commands.py
"""
Dust Economy Commands
/dust, /craft, /boost, /reroll, /buy_pack_dust
"""

import discord
from discord import app_commands, Interaction
from discord.ext import commands
from typing import Optional
from services.dust_economy import dust_economy
from services.duplicate_manager import duplicate_manager


class DustCommandsCog(commands.Cog):
    """Commands for the dust economy system"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="dust", description="Check your dust balance and statistics")
    async def dust_balance(self, interaction: Interaction):
        """Check dust balance"""
        
        stats = dust_economy.get_dust_stats(interaction.user.id)
        dupe_stats = duplicate_manager.get_duplicate_stats(interaction.user.id)
        
        embed = discord.Embed(
            title="💎 Your Dust Balance",
            description=f"**{stats['current']:,}** dust available",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="📊 Lifetime Stats",
            value=f"**Earned:** {stats['total_earned']:,}\n"
                  f"**Spent:** {stats['total_spent']:,}\n"
                  f"**Net:** {stats['net_earned']:,}",
            inline=True
        )
        
        embed.add_field(
            name="🎴 Collection Stats",
            value=f"**Unique Cards:** {dupe_stats['unique_cards']}\n"
                  f"**Total Cards:** {dupe_stats['total_cards']}\n"
                  f"**Duplicates:** {dupe_stats['duplicate_count']}",
            inline=True
        )
        
        # Show what you can afford
        affordable = []
        if stats['current'] >= 50:
            affordable.append("✅ Craft Common (50)")
        if stats['current'] >= 100:
            affordable.append("✅ Craft Rare (100) / Boost +5 (100)")
        if stats['current'] >= 500:
            affordable.append("✅ Buy Community Pack (500)")
        if stats['current'] >= 1000:
            affordable.append("✅ Buy Gold Pack (1,000)")
        
        if affordable:
            embed.add_field(
                name="💰 You Can Afford",
                value="\n".join(affordable[:5]),
                inline=False
            )
        
        embed.set_footer(text="💡 Use /craft, /boost, or /buy_pack_dust to spend dust")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="craft", description="Craft a specific card using dust")
    @app_commands.describe(
        artist="Artist name",
        song="Song title (optional)",
        rarity="Card rarity to craft"
    )
    async def craft_card(
        self,
        interaction: Interaction,
        artist: str,
        rarity: str,
        song: Optional[str] = None
    ):
        """Craft a card with dust"""
        
        rarity = rarity.lower()
        if rarity not in ['common', 'rare', 'epic', 'legendary', 'mythic']:
            await interaction.response.send_message(
                "❌ Invalid rarity! Choose: common, rare, epic, legendary, mythic",
                ephemeral=True
            )
            return
        
        cost = dust_economy.CRAFT_COSTS[rarity]
        current_dust = dust_economy.get_dust_balance(interaction.user.id)
        
        # Create card data
        card_id = f"crafted_{artist.lower().replace(' ', '_')}_{rarity}"
        if song:
            card_id += f"_{song.lower().replace(' ', '_')}"
        
        card_data = {
            'name': artist,
            'title': song or f"{artist} Card",
            'rarity': rarity,
            'image_url': '',
            'youtube_url': '',
            'impact': 50,
            'skill': 50,
            'longevity': 50,
            'culture': 50,
            'hype': 50
        }
        
        # Show confirmation
        embed = discord.Embed(
            title="🔨 Craft Card",
            description=f"**{artist}** - {song or 'Artist Card'}\n**Rarity:** {rarity.title()}",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="💎 Cost",
            value=f"{cost} dust",
            inline=True
        )
        
        embed.add_field(
            name="💰 Your Balance",
            value=f"{current_dust:,} dust",
            inline=True
        )
        
        if current_dust < cost:
            embed.add_field(
                name="❌ Insufficient Dust",
                value=f"Need {cost - current_dust} more dust",
                inline=False
            )
            embed.color = discord.Color.red()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Craft the card
        success, message = dust_economy.craft_card(
            interaction.user.id,
            card_id,
            rarity,
            card_data
        )
        
        if success:
            embed.color = discord.Color.green()
            embed.title = "✅ Card Crafted!"
            embed.add_field(
                name="Success",
                value=message,
                inline=False
            )
        else:
            embed.color = discord.Color.red()
            embed.title = "❌ Crafting Failed"
            embed.add_field(
                name="Error",
                value=message,
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="boost", description="Boost a card's stat using dust")
    @app_commands.describe(
        card_id="Card ID to boost",
        stat="Stat to boost (impact, skill, longevity, culture, hype)",
        level="Boost level: small (+5, 100 dust), medium (+10, 250 dust), large (+15, 500 dust)"
    )
    async def boost_card(
        self,
        interaction: Interaction,
        card_id: str,
        stat: str,
        level: str = "small"
    ):
        """Boost a card's stat"""
        
        valid_stats = ['impact', 'skill', 'longevity', 'culture', 'hype']
        if stat.lower() not in valid_stats:
            await interaction.response.send_message(
                f"❌ Invalid stat! Choose: {', '.join(valid_stats)}",
                ephemeral=True
            )
            return
        
        level = level.lower()
        if level not in ['small', 'medium', 'large']:
            await interaction.response.send_message(
                "❌ Invalid level! Choose: small, medium, large",
                ephemeral=True
            )
            return
        
        success, message = dust_economy.boost_card_stat(
            interaction.user.id,
            card_id,
            stat.lower(),
            level
        )
        
        if success:
            embed = discord.Embed(
                title="⚡ Card Boosted!",
                description=message,
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Boost Failed",
                description=message,
                color=discord.Color.red()
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="reroll", description="Reroll all stats on a card using dust")
    @app_commands.describe(
        card_id="Card ID to reroll",
        rarity="Card's current rarity"
    )
    async def reroll_card(
        self,
        interaction: Interaction,
        card_id: str,
        rarity: str
    ):
        """Reroll card stats"""
        
        rarity = rarity.lower()
        if rarity not in ['common', 'rare', 'epic', 'legendary', 'mythic']:
            await interaction.response.send_message(
                "❌ Invalid rarity! Choose: common, rare, epic, legendary, mythic",
                ephemeral=True
            )
            return
        
        success, message, new_stats = dust_economy.reroll_card_stats(
            interaction.user.id,
            card_id,
            rarity
        )
        
        if success:
            embed = discord.Embed(
                title="🎲 Stats Rerolled!",
                description=message,
                color=discord.Color.green()
            )
            
            if new_stats:
                stats_text = "\n".join([
                    f"**{stat.title()}:** {value}"
                    for stat, value in new_stats.items()
                ])
                embed.add_field(
                    name="📊 New Stats",
                    value=stats_text,
                    inline=False
                )
        else:
            embed = discord.Embed(
                title="❌ Reroll Failed",
                description=message,
                color=discord.Color.red()
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="buy_pack_dust", description="Buy a pack using dust")
    @app_commands.describe(
        pack_type="Pack type: community (500), gold (1000), premium (2000)"
    )
    async def buy_pack_with_dust(
        self,
        interaction: Interaction,
        pack_type: str
    ):
        """Buy pack with dust"""
        
        pack_type = pack_type.lower()
        if pack_type not in ['community', 'gold', 'premium']:
            await interaction.response.send_message(
                "❌ Invalid pack type! Choose: community, gold, premium",
                ephemeral=True
            )
            return
        
        cost = dust_economy.PACK_COSTS[pack_type]
        current_dust = dust_economy.get_dust_balance(interaction.user.id)
        
        if current_dust < cost:
            await interaction.response.send_message(
                f"❌ Insufficient dust! Need {cost:,}, you have {current_dust:,}",
                ephemeral=True
            )
            return
        
        success, message, pack_id = dust_economy.buy_pack_with_dust(
            interaction.user.id,
            pack_type
        )
        
        if success:
            embed = discord.Embed(
                title="🎁 Pack Purchased!",
                description=f"{message}\n\n**Pack ID:** {pack_id}",
                color=discord.Color.green()
            )
            embed.add_field(
                name="💎 Remaining Dust",
                value=f"{dust_economy.get_dust_balance(interaction.user.id):,}",
                inline=False
            )
            embed.set_footer(text="Use /open_pack to open your new pack!")
        else:
            embed = discord.Embed(
                title="❌ Purchase Failed",
                description=message,
                color=discord.Color.red()
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="dust_shop", description="View the dust shop with all available purchases")
    async def dust_shop(self, interaction: Interaction):
        """Show dust shop"""
        
        current_dust = dust_economy.get_dust_balance(interaction.user.id)
        
        embed = discord.Embed(
            title="💎 Dust Shop",
            description=f"**Your Balance:** {current_dust:,} dust\n\n"
                       "Spend your dust on crafting, packs, boosts, and cosmetics!",
            color=discord.Color.gold()
        )
        
        # Crafting
        craft_text = "\n".join([
            f"**{rarity.title()}:** {cost} dust"
            for rarity, cost in dust_economy.CRAFT_COSTS.items()
        ])
        embed.add_field(
            name="🔨 Card Crafting",
            value=craft_text,
            inline=True
        )
        
        # Packs
        pack_text = "\n".join([
            f"**{pack.title()}:** {cost} dust"
            for pack, cost in dust_economy.PACK_COSTS.items()
        ])
        embed.add_field(
            name="📦 Pack Purchase",
            value=pack_text,
            inline=True
        )
        
        # Boosts
        boost_text = (
            "**Small (+5):** 100 dust\n"
            "**Medium (+10):** 250 dust\n"
            "**Large (+15):** 500 dust\n"
            "**Reroll All:** 150 dust"
        )
        embed.add_field(
            name="⚡ Stat Boosting",
            value=boost_text,
            inline=True
        )
        
        # Cosmetics
        cosmetic_text = "\n".join([
            f"**{name.replace('_', ' ').title()}:** {cost} dust"
            for name, cost in list(dust_economy.COSMETIC_COSTS.items())[:4]
        ])
        embed.add_field(
            name="✨ Cosmetics",
            value=cosmetic_text,
            inline=True
        )
        
        embed.set_footer(text="Use /craft, /boost, /reroll, or /buy_pack_dust to purchase")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(DustCommandsCog(bot))
