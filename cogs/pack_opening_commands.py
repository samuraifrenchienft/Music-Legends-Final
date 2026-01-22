# cogs/pack_opening_commands.py
import discord
from discord.ext import commands
import asyncio
from services.open_creator import (
    open_creator_pack, open_premium_creator_pack, open_genre_focused_pack,
    calculate_pack_value, simulate_pack_opening
)
from services.creator_service import creator_service

class PackOpeningCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command()
    async def open_pack(self, ctx, pack_id: str):
        """Open a creator pack"""
        await ctx.trigger_typing()
        
        try:
            # Get pack details
            pack_details = creator_service.get_pack_details(pack_id)
            
            if not pack_details:
                await ctx.send("❌ Pack not found")
                return
            
            # Check if pack is active
            if pack_details['status'] != 'active':
                await ctx.send("❌ This pack is not available for opening")
                return
            
            # Open the pack
            cards = open_creator_pack(pack_id)
            
            if not cards:
                await ctx.send("❌ Failed to open pack")
                return
            
            # Calculate value
            value = calculate_pack_value(cards)
            
            # Create beautiful embed
            embed = discord.Embed(
                title=f"📦 Pack Opened: {pack_details['name']}",
                description=f"You opened {len(cards)} cards worth ${value['total_value_dollars']:.2f}!",
                color=discord.Color.green()
            )
            
            # Show tier breakdown
            tier_text = []
            for tier, count in value['tier_counts'].items():
                if count > 0:
                    tier_emoji = {
                        "legendary": "🏆",
                        "platinum": "💎",
                        "gold": "🥇",
                        "silver": "🥈",
                        "bronze": "🥉",
                        "community": "👥"
                    }.get(tier, "❓")
                    tier_text.append(f"{tier_emoji} {tier.title()}: {count}")
            
            if tier_text:
                embed.add_field(name="🎯 Card Breakdown", value="\n".join(tier_text), inline=False)
            
            # Show cards
            card_list = []
            for i, card in enumerate(cards, 1):
                card_list.append(f"{i}. {card.serial} - {card.artist.name} ({card.tier})")
            
            # Show first 5 cards, then mention total
            display_cards = card_list[:5]
            if len(cards) > 5:
                display_cards.append(f"... and {len(cards) - 5} more cards")
            
            embed.add_field(name=f"🃏 Cards ({len(cards)})", value="\n".join(display_cards), inline=False)
            
            embed.set_footer(text=f"Pack ID: {pack_id[:8]} | Opened by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error opening pack: {e}")
    
    @commands.command()
    async def premium_open(self, ctx, pack_id: str):
        """Open a premium creator pack with guaranteed tiers"""
        await ctx.trigger_typing()
        
        try:
            # Get pack details
            pack_details = creator_service.get_pack_details(pack_id)
            
            if not pack_details:
                await ctx.send("❌ Pack not found")
                return
            
            # Open premium pack
            cards = open_premium_creator_pack(pack_id, guaranteed_tiers=["gold"])
            
            if not cards:
                await ctx.send("❌ Failed to open premium pack")
                return
            
            # Calculate value
            value = calculate_pack_value(cards)
            
            embed = discord.Embed(
                title=f"✨ Premium Pack Opened: {pack_details['name']}",
                description=f"You opened {len(cards)} premium cards worth ${value['total_value_dollars']:.2f}!",
                color=discord.Color.gold()
            )
            
            # Show guaranteed tiers
            embed.add_field(name="🎯 Guaranteed", value="⭐ Gold Card", inline=True)
            embed.add_field(name="💰 Value", value=f"${value['total_value_dollars']:.2f}", inline=True)
            embed.add_field(name="🃏 Cards", value=str(len(cards)), inline=True)
            
            # Show top cards
            top_cards = sorted(cards, key=lambda c: {
                "legendary": 6, "platinum": 5, "gold": 4, "silver": 3, "bronze": 2, "community": 1
            }.get(c.tier, 0), reverse=True)[:3]
            
            card_text = []
            for card in top_cards:
                tier_emoji = {
                    "legendary": "🏆", "platinum": "💎", "gold": "🥇",
                    "silver": "🥈", "bronze": "🥉", "community": "👥"
                }.get(card.tier, "❓")
                card_text.append(f"{tier_emoji} {card.artist.name} ({card.tier})")
            
            embed.add_field(name="🌟 Top Cards", value="\n".join(card_text), inline=False)
            
            embed.set_footer(text=f"Premium Pack ID: {pack_id[:8]} | Opened by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error opening premium pack: {e}")
    
    @commands.command()
    async def simulate_pack(self, ctx, pack_id: str, simulations: int = 100):
        """Simulate pack openings to analyze odds"""
        await ctx.trigger_typing()
        
        try:
            # Get pack details
            pack_details = creator_service.get_pack_details(pack_id)
            
            if not pack_details:
                await ctx.send("❌ Pack not found")
                return
            
            if simulations > 1000:
                await ctx.send("❌ Maximum 1000 simulations at a time")
                return
            
            await ctx.send(f"🎲 Running {simulations} simulations... This may take a moment.")
            
            # Run simulation
            results = simulate_pack_opening(pack_details, simulations)
            
            embed = discord.Embed(
                title=f"🎲 Pack Simulation: {pack_details['name']}",
                description=f"Analyzed {simulations} pack openings",
                color=discord.Color.purple()
            )
            
            embed.add_field(name="💰 Average Value", value=f"${results['average_value_dollars']:.2f}", inline=True)
            embed.add_field(name="📊 Min Value", value=f"${results['min_value_cents'] / 100:.2f}", inline=True)
            embed.add_field(name="📈 Max Value", value=f"${results['max_value_cents'] / 100:.2f}", inline=True)
            
            # Hit rates
            hit_rates = results['hit_rates']
            embed.add_field(
                name="🎯 Hit Rates",
                value=f"🏆 Legendary: {hit_rates['legendary']:.1f}%\n"
                      f"💎 Platinum: {hit_rates['platinum']:.1f}%\n"
                      f"🥇 Gold: {hit_rates['gold']:.1f}%",
                inline=False
            )
            
            # Tier distribution
            dist = results['tier_distribution']
            total_cards = sum(dist.values())
            
            if total_cards > 0:
                dist_text = []
                for tier, count in dist.items():
                    if count > 0:
                        percentage = (count / total_cards) * 100
                        tier_emoji = {
                            "legendary": "🏆", "platinum": "💎", "gold": "🥇",
                            "silver": "🥈", "bronze": "🥉", "community": "👥"
                        }.get(tier, "❓")
                        dist_text.append(f"{tier_emoji} {tier.title()}: {percentage:.1f}%")
                
                embed.add_field(name="📊 Distribution", value="\n".join(dist_text), inline=False)
            
            embed.set_footer(text=f"Pack ID: {pack_id[:8]} | Simulated by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error simulating pack: {e}")
    
    @commands.command()
    async def pack_value(self, ctx, pack_id: str):
        """Show estimated value and odds for a pack"""
        await ctx.trigger_typing()
        
        try:
            # Get pack details
            pack_details = creator_service.get_pack_details(pack_id)
            
            if not pack_details:
                await ctx.send("❌ Pack not found")
                return
            
            # Quick simulation for value estimation
            results = simulate_pack_opening(pack_details, 50)
            
            embed = discord.Embed(
                title=f"💰 Pack Analysis: {pack_details['name']}",
                description=f"Price: ${pack_details['price_cents'] / 100:.2f}",
                color=discord.Color.green()
            )
            
            # Value analysis
            avg_value = results['average_value_dollars']
            pack_price = pack_details['price_cents'] / 100
            roi = ((avg_value - pack_price) / pack_price) * 100 if pack_price > 0 else 0
            
            embed.add_field(name="💰 Expected Value", value=f"${avg_value:.2f}", inline=True)
            embed.add_field(name="📈 ROI", value=f"{roi:+.1f}%", inline=True)
            embed.add_field(name="🎯 Hit Rate", value=f"{results['hit_rates']['gold']:.1f}% Gold+", inline=True)
            
            # Artist information
            artist_count = len(pack_details['artists'])
            embed.add_field(name="🎵 Artists", value=str(artist_count), inline=True)
            embed.add_field(name="🎼 Genre", value=pack_details['genre'], inline=True)
            embed.add_field(name="🛒 Purchases", value=str(pack_details['purchase_count']), inline=True)
            
            # Recommendation
            if roi > 20:
                recommendation = "🟢 Great Value!"
                color = discord.Color.green()
            elif roi > 0:
                recommendation = "🟡 Fair Value"
                color = discord.Color.gold()
            else:
                recommendation = "🔴 Below Value"
                color = discord.Color.red()
            
            embed.add_field(name="💡 Recommendation", value=recommendation, inline=False)
            
            embed.set_footer(text=f"Pack ID: {pack_id[:8]} | Analysis by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error analyzing pack: {e}")


async def setup(bot):
    await bot.add_cog(PackOpeningCommands(bot))
