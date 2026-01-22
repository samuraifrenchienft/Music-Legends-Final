# cogs/creator_commands.py
import discord
from discord.ext import commands
import asyncio
from services.creator_service import creator_service

class CreatorCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command()
    async def create_pack(self, ctx, name: str, *, artists: str):
        """
        Create a creator pack
        Usage: !create_pack "Pack Name" artist1, artist2, artist3
        """
        await ctx.trigger_typing()
        
        try:
            # Parse artists
            artist_names = [a.strip() for a in artists.split(',')]
            
            if len(artist_names) < 1:
                await ctx.send("❌ Please provide at least 1 artist")
                return
            
            if len(artist_names) > 10:
                await ctx.send("❌ Maximum 10 artists per pack")
                return
            
            # Determine genre from first artist (or ask user)
            genre = "Mixed"  # Default
            
            # Create pack
            pack = await creator_service.create_creator_pack(
                user_id=ctx.author.id,
                name=name,
                artist_names=artist_names,
                genre=genre,
                description=f"Creator pack by {ctx.author.name}"
            )
            
            if pack:
                embed = discord.Embed(
                    title=f"📦 Creator Pack Created!",
                    description=f"Successfully created '{pack.name}'",
                    color=discord.Color.green()
                )
                
                embed.add_field(name="🆔 Pack ID", value=str(pack.id)[:8], inline=True)
                embed.add_field(name="🎼 Genre", value=pack.genre, inline=True)
                embed.add_field(name="💰 Price", value=f"${pack.price_cents / 100:.2f}", inline=True)
                embed.add_field(name="🎵 Artists", value=str(len(pack.artist_ids)), inline=True)
                
                embed.set_footer(text=f"Created by {ctx.author.name}")
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Failed to create pack")
                
        except Exception as e:
            await ctx.send(f"❌ Error creating pack: {e}")
    
    @commands.command()
    async def my_packs(self, ctx):
        """Show your creator packs"""
        await ctx.trigger_typing()
        
        try:
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
                    value=f"🎼 {pack.genre} | 💰 ${pack.price_cents / 100:.2f} | 🛒 {pack.purchase_count} purchases",
                    inline=False
                )
            
            embed.set_footer(text=f"Requested by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting your packs: {e}")
    
    @commands.command()
    async def featured_packs(self, ctx, limit: int = 5):
        """Show featured creator packs"""
        await ctx.trigger_typing()
        
        try:
            packs = creator_service.get_featured_packs(limit)
            
            if not packs:
                await ctx.send("No featured packs available!")
                return
            
            embed = discord.Embed(
                title=f"⭐ Featured Creator Packs",
                description=f"Top {len(packs)} featured packs",
                color=discord.Color.gold()
            )
            
            for pack in packs:
                embed.add_field(
                    name=f"📦 {pack.name}",
                    value=f"🎼 {pack.genre} | 💰 ${pack.price_cents / 100:.2f} | 🛒 {pack.purchase_count} purchases",
                    inline=False
                )
            
            embed.set_footer(text=f"Requested by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting featured packs: {e}")
    
    @commands.command()
    async def search_packs(self, ctx, *, query: str):
        """Search creator packs"""
        await ctx.trigger_typing()
        
        try:
            packs = creator_service.search_packs(query, limit=10)
            
            if not packs:
                await ctx.send(f"No packs found for '{query}'")
                return
            
            embed = discord.Embed(
                title=f"🔍 Search Results: {query}",
                description=f"Found {len(packs)} pack(s)",
                color=discord.Color.purple()
            )
            
            for pack in packs:
                embed.add_field(
                    name=f"📦 {pack.name}",
                    value=f"🎼 {pack.genre} | 💰 ${pack.price_cents / 100:.2f} | ⭐ {pack.rating}/5",
                    inline=False
                )
            
            embed.set_footer(text=f"Requested by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error searching packs: {e}")
    
    @commands.command()
    async def pack_details(self, ctx, pack_id: str):
        """Show detailed pack information"""
        await ctx.trigger_typing()
        
        try:
            details = creator_service.get_pack_details(pack_id)
            
            if not details:
                await ctx.send("❌ Pack not found")
                return
            
            embed = discord.Embed(
                title=f"📦 {details['name']}",
                description=details.get('description', 'No description'),
                color=discord.Color.blue()
            )
            
            embed.add_field(name="🆔 Pack ID", value=details['id'][:8], inline=True)
            embed.add_field(name="🎼 Genre", value=details['genre'], inline=True)
            embed.add_field(name="💰 Price", value=f"${details['price_cents'] / 100:.2f}", inline=True)
            embed.add_field(name="🛒 Purchases", value=details['purchase_count'], inline=True)
            embed.add_field(name="⭐ Rating", value=f"{details['rating']}/5", inline=True)
            embed.add_field(name="🎨 Branding", value=details['branding'], inline=True)
            
            # Show artists
            if details['artists']:
                artist_list = []
                for artist in details['artists'][:5]:  # Show first 5
                    artist_list.append(f"🎵 {artist['name']} ({artist['tier']})")
                
                artists_text = "\n".join(artist_list)
                if len(details['artists']) > 5:
                    artists_text += f"\n... and {len(details['artists']) - 5} more"
                
                embed.add_field(name=f"🎵 Artists ({len(details['artists'])})", value=artists_text, inline=False)
            
            embed.set_footer(text=f"Pack ID: {details['id'][:8]}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting pack details: {e}")
    
    @commands.command()
    async def genre_packs(self, ctx, genre: str, limit: int = 5):
        """Show packs by genre"""
        await ctx.trigger_typing()
        
        try:
            packs = creator_service.get_packs_by_genre(genre, limit)
            
            if not packs:
                await ctx.send(f"No packs found for genre '{genre}'")
                return
            
            embed = discord.Embed(
                title=f"🎼 {genre.title()} Packs",
                description=f"Found {len(packs)} pack(s)",
                color=discord.Color.green()
            )
            
            for pack in packs:
                embed.add_field(
                    name=f"📦 {pack.name}",
                    value=f"💰 ${pack.price_cents / 100:.2f} | 🛒 {pack.purchase_count} purchases",
                    inline=False
                )
            
            embed.set_footer(text=f"Requested by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting genre packs: {e}")
    
    @commands.command()
    @commands.is_owner()  # Admin only
    async def creator_stats(self, ctx):
        """Show creator pack statistics"""
        await ctx.trigger_typing()
        
        try:
            stats = creator_service.get_pack_statistics()
            
            embed = discord.Embed(
                title="📊 Creator Pack Statistics",
                color=discord.Color.gold()
            )
            
            embed.add_field(name="📦 Total Packs", value=stats['total_packs'], inline=True)
            embed.add_field(name="✅ Active Packs", value=stats['active_packs'], inline=True)
            embed.add_field(name="🛒 Total Purchases", value=stats['total_purchases'], inline=True)
            embed.add_field(name="💰 Average Price", value=f"${stats['average_price'] / 100:.2f}", inline=True)
            
            # Genre breakdown
            if stats['by_genre']:
                genre_text = []
                for genre, count in list(stats['by_genre'].items())[:5]:
                    genre_text.append(f"{genre}: {count}")
                
                embed.add_field(name="🎼 Top Genres", value="\n".join(genre_text), inline=False)
            
            # Branding breakdown
            if stats['by_branding']:
                branding_text = []
                for branding, count in list(stats['by_branding'].items())[:3]:
                    branding_text.append(f"{branding}: {count}")
                
                embed.add_field(name="🎨 Branding", value="\n".join(branding_text), inline=False)
            
            embed.set_footer(text=f"Requested by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting statistics: {e}")


async def setup(bot):
    await bot.add_cog(CreatorCommands(bot))
