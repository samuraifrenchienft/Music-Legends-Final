# cogs/artist_commands.py
import discord
from discord.ext import commands
import asyncio
from services.artist_pipeline import artist_pipeline

class ArtistCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command()
    async def import_artist(self, ctx, *, artist_name: str):
        """Import a YouTube artist and create a card"""
        await ctx.trigger_typing()
        
        try:
            card = await artist_pipeline.import_artist_to_card(artist_name)
            
            if not card:
                await ctx.send(f"❌ No artist found for '{artist_name}'")
                return
            
            # Create beautiful embed
            embed = discord.Embed(
                title=f"🎵 Artist Imported: {card.artist.name}",
                description=f"Successfully imported from YouTube!",
                color=discord.Color.purple()
            )
            
            embed.set_thumbnail(url=card.artist.image_url)
            
            embed.add_field(name="🆔 Card Serial", value=card.serial, inline=True)
            embed.add_field(name="🏆 Tier", value=f"{card.tier.title()}", inline=True)
            embed.add_field(name="🎼 Genre", value=card.artist.genre.title(), inline=True)
            
            embed.add_field(name="💪 Power Level", value=str(card.power_level), inline=True)
            embed.add_field(name="👥 Popularity", value=f"{card.artist.popularity:,}", inline=True)
            embed.add_field(name="📊 Score", value=f"{card.artist.score:,}", inline=True)
            
            # Stats
            stats_text = f"⚔️ Attack: {card.stats['attack']}\n"
            stats_text += f"🛡️ Defense: {card.stats['defense']}\n"
            stats_text += f"⚡ Speed: {card.stats['speed']}\n"
            stats_text += f"❤️ Health: {card.stats['health']}"
            embed.add_field(name="📊 Card Stats", value=stats_text, inline=False)
            
            # Abilities
            if card.abilities:
                abilities_text = "\n".join([f"• {a['name']}: {a['description']}" for a in card.abilities[:3]])
                embed.add_field(name="⚡ Abilities", value=abilities_text, inline=False)
            
            embed.set_footer(text=f"Imported by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error importing artist: {e}")
    
    @commands.command()
    async def import_trending(self, ctx, region: str = "US", count: int = 5):
        """Import trending music artists"""
        await ctx.trigger_typing()
        
        try:
            if count > 10:
                await ctx.send("❌ Maximum 10 artists at a time")
                return
            
            cards = await artist_pipeline.import_trending_artists(region.upper(), count)
            
            if not cards:
                await ctx.send(f"❌ No trending artists found for {region}")
                return
            
            embed = discord.Embed(
                title=f"🔥 Trending Artists Imported ({region.upper()})",
                description=f"Successfully imported {len(cards)} trending artists!",
                color=discord.Color.orange()
            )
            
            for i, card in enumerate(cards, 1):
                embed.add_field(
                    name=f"{i}. {card.artist.name}",
                    value=f"🆔 {card.serial} | 🏆 {card.tier.title()} | 💪 {card.power_level}",
                    inline=False
                )
            
            embed.set_footer(text=f"Imported by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error importing trending artists: {e}")
    
    @commands.command()
    async def import_genre(self, ctx, genre: str, count: int = 3):
        """Import artists from a specific genre"""
        await ctx.trigger_typing()
        
        try:
            if count > 10:
                await ctx.send("❌ Maximum 10 artists at a time")
                return
            
            cards = await artist_pipeline.import_genre_artists(genre.title(), count)
            
            if not cards:
                await ctx.send(f"❌ No artists found for genre '{genre}'")
                return
            
            embed = discord.Embed(
                title=f"🎼 {genre.title()} Artists Imported",
                description=f"Successfully imported {len(cards)} {genre} artists!",
                color=discord.Color.blue()
            )
            
            for i, card in enumerate(cards, 1):
                embed.add_field(
                    name=f"{i}. {card.artist.name}",
                    value=f"🆔 {card.serial} | 🏆 {card.tier.title()} | 🎼 {card.artist.genre.title()}",
                    inline=False
                )
            
            embed.set_footer(text=f"Imported by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error importing genre artists: {e}")
    
    @commands.command()
    async def artist_info(self, ctx, *, artist_name: str):
        """Get information about an artist without importing"""
        await ctx.trigger_typing()
        
        try:
            # Search for channel without importing
            channel = await artist_pipeline.youtube_client.search_channel(artist_name)
            
            if not channel:
                await ctx.send(f"❌ No artist found for '{artist_name}'")
                return
            
            # Get stats
            stats = await artist_pipeline.youtube_client.channel_stats(channel["channel_id"])
            
            if not stats:
                await ctx.send(f"❌ No stats available for '{artist_name}'")
                return
            
            # Analyze for game
            from services.tier_mapper import analyze_channel_for_game
            analysis = analyze_channel_for_game(
                subs=stats["subs"],
                views=stats["views"],
                videos=stats.get("videos", 0),
                topics=stats.get("topics", []),
                description=channel.get("description", ""),
                channel_name=channel.get("name", "")
            )
            
            embed = discord.Embed(
                title=f"🎵 Artist Info: {channel['name']}",
                description=channel.get("description", "No description available")[:300],
                color=discord.Color.green(),
                url=f"https://youtube.com/channel/{channel['channel_id']}"
            )
            
            embed.set_thumbnail(url=channel.get("image", ""))
            
            embed.add_field(name="👥 Subscribers", value=f"{stats['subs']:,}", inline=True)
            embed.add_field(name="👁️ Total Views", value=f"{stats['views']:,}", inline=True)
            embed.add_field(name="📹 Videos", value=f"{stats.get('videos', 0):,}", inline=True)
            
            embed.add_field(name="🏆 Predicted Tier", value=f"{analysis['tier'].title()}", inline=True)
            embed.add_field(name="🎼 Genre", value=analysis['genre'].title(), inline=True)
            embed.add_field(name="💪 Power Level", value=str(analysis['game_data']['power_level']), inline=True)
            
            embed.add_field(name="📊 Score", value=f"{analysis['score']:,}", inline=True)
            
            embed.set_footer(text=f"Channel ID: {channel['channel_id']}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting artist info: {e}")
    
    @commands.command()
    @commands.is_owner()  # Restrict to bot owner
    async def update_artist(self, ctx, artist_id: str):
        """Update artist statistics (admin only)"""
        await ctx.trigger_typing()
        
        try:
            success = await artist_pipeline.update_artist_stats(artist_id)
            
            if success:
                await ctx.send("✅ Artist statistics updated successfully")
            else:
                await ctx.send("❌ Failed to update artist statistics")
                
        except Exception as e:
            await ctx.send(f"❌ Error updating artist: {e}")
    
    @commands.command()
    async def card_details(self, ctx, serial: str):
        """Get detailed information about a card"""
        await ctx.trigger_typing()
        
        try:
            # This would require a Card.get_by_serial method
            # For now, we'll show a placeholder
            embed = discord.Embed(
                title=f"🃏 Card Details: {serial}",
                description="Card details feature coming soon!",
                color=discord.Color.gold()
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting card details: {e}")


async def setup(bot):
    await bot.add_cog(ArtistCommands(bot))
