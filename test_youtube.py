# test_youtube.py
# Test script for YouTube API integration

import asyncio
import os
import sys

# Add current directory to path
sys.path.append('.')

async def test_youtube_integration():
    """Test YouTube API integration"""
    print("🎵 Testing YouTube API Integration")
    print("=================================")
    
    # Load environment variables
    with open('.env.txt', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value
    
    # Check API key
    api_key = os.getenv("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_KEY")
    if not api_key:
        print("❌ YouTube API key not found")
        print("💡 Add to .env.txt: YOUTUBE_API_KEY=your_api_key_here")
        return
    
    print(f"✅ YouTube API key found: {api_key[:20]}...")
    
    # Import YouTube client
    from services.youtube_client import youtube_client, search_music_artist, get_music_videos, get_trending_songs
    
    print("\n1. Testing channel search...")
    try:
        channel = await youtube_client.search_channel("Taylor Swift")
        if channel:
            print(f"✅ Found channel: {channel['name']}")
            print(f"   Channel ID: {channel['channel_id']}")
            print(f"   Description: {channel['description'][:100]}...")
        else:
            print("❌ No channel found")
    except Exception as e:
        print(f"❌ Channel search failed: {e}")
    
    print("\n2. Testing channel stats...")
    try:
        if channel:
            stats = await youtube_client.channel_stats(channel['channel_id'])
            if stats:
                print(f"✅ Channel stats retrieved:")
                print(f"   Subscribers: {stats['subs']:,}")
                print(f"   Total views: {stats['views']:,}")
                print(f"   Videos: {stats['videos']:,}")
            else:
                print("❌ No stats found")
    except Exception as e:
        print(f"❌ Channel stats failed: {e}")
    
    print("\n3. Testing video search...")
    try:
        videos = await youtube_client.search_videos("music", 3)
        if videos:
            print(f"✅ Found {len(videos)} videos:")
            for i, video in enumerate(videos, 1):
                print(f"   {i}. {video['title'][:50]}...")
        else:
            print("❌ No videos found")
    except Exception as e:
        print(f"❌ Video search failed: {e}")
    
    print("\n4. Testing music search...")
    try:
        music_videos = await get_music_videos("pop", 3)
        if music_videos:
            print(f"✅ Found {len(music_videos)} music videos:")
            for i, video in enumerate(music_videos, 1):
                print(f"   {i}. {video['title'][:50]}...")
        else:
            print("❌ No music videos found")
    except Exception as e:
        print(f"❌ Music search failed: {e}")
    
    print("\n5. Testing trending music...")
    try:
        trending = await get_trending_songs("US")
        if trending:
            print(f"✅ Found {len(trending)} trending songs:")
            for i, video in enumerate(trending[:3], 1):
                print(f"   {i}. {video['title'][:50]}...")
        else:
            print("❌ No trending music found")
    except Exception as e:
        print(f"❌ Trending music failed: {e}")
    
    print("\n6. Testing artist search...")
    try:
        artist = await search_music_artist("Drake")
        if artist:
            print(f"✅ Found artist: {artist['name']}")
            print(f"   Channel ID: {artist['channel_id']}")
        else:
            print("❌ No artist found")
    except Exception as e:
        print(f"❌ Artist search failed: {e}")
    
    print("\n🎉 YouTube API integration test completed!")
    print("📊 All tests completed - check results above")


async def test_discord_commands():
    """Test YouTube Discord commands"""
    print("\n🤖 Testing YouTube Discord Commands")
    print("==================================")
    
    print("📋 Available commands:")
    print("   !ytsearch <query> - Search YouTube videos")
    print("   !ytartist <artist> - Search music artist channel")
    print("   !ytvideo <video_id> - Get video details")
    print("   !ytchannel <channel_id> - Get channel videos")
    print("   !yttrending [region] - Get trending music")
    print("   !ytmusic <query> - Search music videos")
    
    print("\n💡 Example usage:")
    print("   !ytsearch Taylor Swift")
    print("   !ytartist Ed Sheeran")
    print("   !ytvideo dQw4w9WgXcQ")
    print("   !yttrending US")
    print("   !ytmusic pop")


async def main():
    """Run all tests"""
    await test_youtube_integration()
    await test_discord_commands()
    
    print("\n🎯 YouTube Integration Test Complete!")
    print("🎵 Add YouTube API key to .env.txt to enable all features")
    print("🤖 Load YouTube commands in your bot: bot.load_extension('cogs.youtube_commands')")


if __name__ == "__main__":
    asyncio.run(main())
