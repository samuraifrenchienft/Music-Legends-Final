# cogs/creator_commands_simple.py
"""
Simple Creator Commands - Direct implementation as requested
"""

from discord.ext import commands
import discord
from services.creator_service import create_creator_pack
from models.creator_pack import CreatorPack
from services.open_creator import open_creator_pack
from services.monitor.alerts import purchase_completed, legendary_created

class CreatorCommandsSimple(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command()
    async def makepack(self, ctx, name: str, genre: str, *artists: str):
        """
        Create a creator pack
        Usage: !makepack "Pack Name" "Genre" artist1 artist2 artist3
        """
        try:
            # Validate inputs
            if not name or len(name) > 60:
                await ctx.send("❌ Pack name must be 1-60 characters")
                return
            
            if not genre or len(genre) > 20:
                await ctx.send("❌ Genre must be 1-20 characters")
                return
            
            if not artists or len(artists) > 10:
                await ctx.send("❌ Please provide 1-10 artists")
                return
            
            # Convert tuple to list
            artist_list = list(artists)
            
            await ctx.trigger_typing()
            
            # Create the pack
            pack = await create_creator_pack(
                ctx.author.id,
                name,
                artist_list,
                genre
            )
            
            if pack:
                # Send success message
                embed = discord.Embed(
                    title="📦 Creator Pack Created!",
                    description=f"Your pack is ready for opening",
                    color=discord.Color.green()
                )
                
                embed.add_field(name="🆔 Pack ID", value=str(pack.id)[:8], inline=True)
                embed.add_field(name="📦 Name", value=pack.name, inline=True)
                embed.add_field(name="🎼 Genre", value=pack.genre, inline=True)
                embed.add_field(name="🎵 Artists", value=str(len(pack.artist_ids)), inline=True)
                embed.add_field(name="💰 Price", value=f"${pack.price_cents / 100:.2f}", inline=True)
                embed.add_field(name="📊 Status", value=pack.status.title(), inline=True)
                
                embed.set_footer(text=f"Created by {ctx.author.name}")
                await ctx.send(embed=embed)
                
                # Log pack creation
                await purchase_completed(
                    user_id=ctx.author.id,
                    purchase_id=str(pack.id),
                    amount=pack.price_cents,
                    pack_type="creator_created"
                )
                
            else:
                await ctx.send("❌ Failed to create creator pack")
                
        except Exception as e:
            await ctx.send(f"❌ Error creating pack: {e}")
    
    @commands.command()
    async def opencreator(self, ctx, pack_id: str):
        """
        Open a creator pack
        Usage: !opencreator pack_id
        """
        try:
            await ctx.trigger_typing()
            
            # Get the pack
            pack = CreatorPack.get_by_id(pack_id)
            
            if not pack:
                await ctx.send("❌ Pack not found")
                return
            
            # Check if pack is approved
            if pack.status != "approved":
                await ctx.send(f"❌ Pack is not approved (status: {pack.status})")
                return
            
            # Open the pack
            try:
                cards = open_creator_pack(pack)
                
                if not cards:
                    await ctx.send("❌ Failed to open pack")
                    return
                
                # Calculate pack value
                from services.open_creator import calculate_pack_value
                value = calculate_pack_value(cards)
                
                # Create result embed
                embed = discord.Embed(
                    title=f"📦 Pack Opened!",
                    description=f"You opened {len(cards)} cards worth ${value['total_value_dollars']:.2f}",
                    color=discord.Color.gold()
                )
                
                # Show pack info
                embed.add_field(name="📦 Pack", value=pack.name, inline=True)
                embed.add_field(name="🎼 Genre", value=pack.genre, inline=True)
                embed.add_field(name="💰 Value", value=f"${value['total_value_dollars']:.2f}", inline=True)
                
                # Show cards
                card_serials = [c.serial for c in cards]
                if len(card_serials) <= 10:
                    embed.add_field(name="🃏 Cards", value="\n".join(card_serials), inline=False)
                else:
                    embed.add_field(
                        name="🃏 Cards", 
                        value="\n".join(card_serials[:10]) + f"\n... and {len(card_serials) - 10} more",
                        inline=False
                    )
                
                # Show tier breakdown
                tier_counts = value['tier_counts']
                if tier_counts:
                    tier_text = []
                    for tier, count in tier_counts.items():
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
                    
                    embed.add_field(name="🎯 Breakdown", value=" | ".join(tier_text), inline=False)
                
                embed.set_footer(text=f"Pack ID: {pack_id[:8]} | Opened by {ctx.author.name}")
                await ctx.send(embed=embed)
                
            except ValueError as e:
                await ctx.send(f"❌ Cannot open pack: {e}")
                
            
            # Log pack opening
            await purchase_completed(
                user_id=ctx.author.id,
                purchase_id=pack_id,
                amount=pack.price_cents,
                pack_type="creator_opened"
            )
            
        except Exception as e:
            await ctx.send(f"❌ Error opening pack: {e}")
    
    @commands.command()
    async def mycreatorpacks(self, ctx):
        """Show your creator packs"""
        try:
            from services.creator_service import creator_service
            
            packs = creator_service.get_user_packs(ctx.author.id)
            
            if not packs:
                await ctx.send("You haven't created any packs yet!")
                return
            
            embed = discord.Embed(
                title=f"📦 Your Creator Packs",
                description=f"You have {len(packs)} pack(s)",
                color=discord.Color.blue()
            )
            
            for pack in packs:
                status_emoji = "✅" if pack.status == "active" else "❌"
                embed.add_field(
                    name=f"{status_emoji} {pack.name}",
                    value=f"ID: {str(pack.id)[:8]} | 🎼 {pack.genre} | 💰 ${pack.price_cents / 100:.2f} | 🛒 {pack.purchase_count} purchases",
                    inline=False
                )
            
            embed.set_footer(text=f"Requested by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting your packs: {e}")
    
    @commands.command()
    async def creatorinfo(self, ctx, pack_id: str):
        """Show detailed creator pack information"""
        try:
            from services.creator_service import creator_service
            
            details = creator_service.get_pack_details(pack_id)
            
            if not details:
                await ctx.send("❌ Pack not found")
                return
            
            embed = discord.Embed(
                title=f"📦 {details['name']}",
                description=details.get('description', 'No description'),
                color=discord.Color.purple()
            )
            
            embed.add_field(name="🆔 Pack ID", value=details['id'][:8], inline=True)
            embed.add_field(name="🎼 Genre", value=details['genre'], inline=True)
            embed.add_field(name="💰 Price", value=f"${details['price_cents'] / 100:.2f}", inline=True)
            embed.add_field(name="🛒 Purchases", value=details['purchase_count'], inline=True)
            embed.add_field(name="⭐ Rating", value=f"{details['rating']}/5", inline=True)
            embed.add_field(name="🎨 Branding", value=details['branding'], inline=True)
            embed.add_field(name="📊 Status", value=details['status'].title(), inline=True)
            
            # Show artists
            if details['artists']:
                artist_list = []
                for artist in details['artists'][:5]:
                    artist_list.append(f"🎵 {artist['name']} ({artist['tier']})")
                
                if len(details['artists']) > 5:
                    artist_list.append(f"... and {len(details['artists']) - 5} more")
                
                embed.add_field(name=f"🎵 Artists ({len(details['artists']})", value="\n".join(artist_list), inline=False)
            
            embed.set_footer(text=f"Pack ID: {details['id'][:8]}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting pack info: {e}")


async def setup(bot):
    await bot.add_cog(CreatorCommandsSimple(bot))
