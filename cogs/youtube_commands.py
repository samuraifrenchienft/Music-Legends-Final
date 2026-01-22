# cogs/youtube_commands.py
import discord
from discord.ext import commands
import asyncio
from services.youtube_client import (
    youtube_client, search_music_artist, get_music_videos, get_trending_songs
)

class YouTubeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command()
    async def ytsearch(self, ctx, *, query: str):
        """Search for YouTube videos"""
        await ctx.trigger_typing()
        
        try:
            videos = await youtube_client.search_videos(query, 5)
            
            if not videos:
                await ctx.send("❌ No videos found for that query.")
                return
            
            embed = discord.Embed(
                title=f"🔍 YouTube Search: {query}",
                color=discord.Color.red()
            )
            
            for i, video in enumerate(videos, 1):
                embed.add_field(
                    name=f"{i}. {video['title']}",
                    value=f"📺 [{video['channel']}]({video['thumbnail']})\n"
                          f"🔗 [Watch](https://youtube.com/watch?v={video['video_id']})",
                    inline=False
                )
            
            embed.set_footer(text=f"Found {len(videos)} videos")
            await ctx.send(embed=embed)
            
        except ValueError as e:
            await ctx.send(f"❌ {str(e)}")
        except Exception as e:
            await ctx.send(f"❌ Error searching videos: {e}")
    
    @commands.command()
    async def ytartist(self, ctx, *, artist: str):
        """Search for a music artist's channel"""
        await ctx.trigger_typing()
        
        try:
            channel = await search_music_artist(artist)
            
            if not channel:
                await ctx.send(f"❌ No artist channel found for '{artist}'")
                return
            
            # Get channel stats
            stats = await youtube_client.channel_stats(channel['channel_id'])
            
            embed = discord.Embed(
                title=f"🎵 Artist: {channel['name']}",
                description=channel['description'][:300] + "..." if len(channel['description']) > 300 else channel['description'],
                color=discord.Color.purple(),
                url=f"https://youtube.com/channel/{channel['channel_id']}"
            )
            
            embed.set_thumbnail(url=channel['image'])
            
            if stats:
                embed.add_field(name="👥 Subscribers", value=f"{stats['subs']:,}", inline=True)
                embed.add_field(name="👁️ Total Views", value=f"{stats['views']:,}", inline=True)
                embed.add_field(name="📹 Videos", value=f"{stats['videos']:,}", inline=True)
                
                if stats['topics']:
                    topics_text = ", ".join([topic.split('/')[-1] for topic in stats['topics'][:3]])
                    embed.add_field(name="🏷️ Topics", value=topics_text, inline=False)
            
            await ctx.send(embed=embed)
            
        except ValueError as e:
            await ctx.send(f"❌ {str(e)}")
        except Exception as e:
            await ctx.send(f"❌ Error finding artist: {e}")
    
    @commands.command()
    async def ytvideo(self, ctx, video_id: str):
        """Get detailed information about a YouTube video"""
        await ctx.trigger_typing()
        
        try:
            video = await youtube_client.get_video_details(video_id)
            
            if not video:
                await ctx.send("❌ Video not found or invalid ID.")
                return
            
            embed = discord.Embed(
                title=video['title'],
                description=video['description'][:500] + "..." if len(video['description']) > 500 else video['description'],
                color=discord.Color.red(),
                url=f"https://youtube.com/watch?v={video_id}"
            )
            
            embed.add_field(name="📺 Channel", value=video['channel'], inline=True)
            embed.add_field(name="👁️ Views", value=f"{video['views']:,}", inline=True)
            embed.add_field(name="👍 Likes", value=f"{video['likes']:,}", inline=True)
            embed.add_field(name="💬 Comments", value=f"{video['comments']:,}", inline=True)
            embed.add_field(name="⏱️ Duration", value=video['duration'], inline=True)
            embed.add_field(name="📅 Published", value=video['published_at'][:10], inline=True)
            
            if video['tags']:
                tags_text = ", ".join(video['tags'][:5])
                if len(video['tags']) > 5:
                    tags_text += "..."
                embed.add_field(name="🏷️ Tags", value=tags_text, inline=False)
            
            await ctx.send(embed=embed)
            
        except ValueError as e:
            await ctx.send(f"❌ {str(e)}")
        except Exception as e:
            await ctx.send(f"❌ Error getting video details: {e}")
    
    @commands.command()
    async def ytchannel(self, ctx, channel_id: str):
        """Get recent videos from a YouTube channel"""
        await ctx.trigger_typing()
        
        try:
            # Get channel info first
            channel = await youtube_client.search_channel(channel_id)
            if not channel:
                # Try to get stats directly
                stats = await youtube_client.channel_stats(channel_id)
                if stats:
                    channel = {
                        'name': 'Unknown Channel',
                        'channel_id': channel_id,
                        'description': 'No description available'
                    }
                else:
                    await ctx.send("❌ Channel not found.")
                    return
            
            # Get recent videos
            videos = await youtube_client.get_channel_videos(channel['channel_id'], 5)
            
            embed = discord.Embed(
                title=f"📺 {channel['name']}",
                description=channel['description'][:300] + "..." if len(channel['description']) > 300 else channel['description'],
                color=discord.Color.blue(),
                url=f"https://youtube.com/channel/{channel['channel_id']}"
            )
            
            if videos:
                video_list = []
                for video in videos:
                    video_list.append(f"📹 [{video['title']}]({video['thumbnail']})")
                
                embed.add_field(
                    name=f"Recent Videos ({len(videos)})",
                    value="\n".join(video_list),
                    inline=False
                )
            else:
                embed.add_field(name="Recent Videos", value="No videos found", inline=False)
            
            await ctx.send(embed=embed)
            
        except ValueError as e:
            await ctx.send(f"❌ {str(e)}")
        except Exception as e:
            await ctx.send(f"❌ Error getting channel: {e}")
    
    @commands.command()
    async def yttrending(self, ctx, region: str = "US"):
        """Get trending music videos"""
        await ctx.trigger_typing()
        
        try:
            videos = await get_trending_songs(region.upper())
            
            if not videos:
                await ctx.send("❌ No trending music found.")
                return
            
            embed = discord.Embed(
                title=f"🔥 Trending Music ({region.upper()})",
                color=discord.Color.orange()
            )
            
            for i, video in enumerate(videos, 1):
                embed.add_field(
                    name=f"{i}. {video['title']}",
                    value=f"📺 {video['channel']} | 👁️ {video['views']:,} views\n"
                          f"🔗 [Watch](https://youtube.com/watch?v={video['video_id']})",
                    inline=False
                )
            
            embed.set_footer(text=f"Top {len(videos)} trending songs")
            await ctx.send(embed=embed)
            
        except ValueError as e:
            await ctx.send(f"❌ {str(e)}")
        except Exception as e:
            await ctx.send(f"❌ Error getting trending music: {e}")
    
    @commands.command()
    async def ytmusic(self, ctx, *, query: str):
        """Search specifically for music videos"""
        await ctx.trigger_typing()
        
        try:
            videos = await get_music_videos(query, 5)
            
            if not videos:
                await ctx.send("❌ No music videos found for that query.")
                return
            
            embed = discord.Embed(
                title=f"🎵 Music Search: {query}",
                color=discord.Color.purple()
            )
            
            for i, video in enumerate(videos, 1):
                embed.add_field(
                    name=f"{i}. {video['title']}",
                    value=f"📺 {video['channel']}\n"
                          f"🔗 [Watch](https://youtube.com/watch?v={video['video_id']})",
                    inline=False
                )
            
            embed.set_footer(text=f"Found {len(videos)} music videos")
            await ctx.send(embed=embed)
            
        except ValueError as e:
            await ctx.send(f"❌ {str(e)}")
        except Exception as e:
            await ctx.send(f"❌ Error searching music: {e}")


async def setup(bot):
    await bot.add_cog(YouTubeCommands(bot))
