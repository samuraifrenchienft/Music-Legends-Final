#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Marketplace Seed Script
Automatically generate packs from artist lists using YouTube data

Usage:
    python seed_marketplace_packs.py --artists "Drake,The Weeknd,Beyonce" --count 1
    python seed_marketplace_packs.py --artists-file artists.txt --count 2
"""

import argparse
import sqlite3
import json
import uuid
import sys
import os
from typing import List, Dict

# Add project root to Python path
sys.path.insert(0, str(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))))

from config import settings

# Import project modules
from database import DatabaseManager
from youtube_integration import youtube_integration
from card_stats import WeightedCardPool

def generate_card_from_video(video_data: dict, rarity: str = None) -> dict:
    """Generate a card from YouTube video data
    
    Args:
        video_data: YouTube video data from search
        rarity: Optional rarity override, otherwise auto-determined by views
    
    Returns:
        Card dictionary
    """
    # Extract data
    video_id = video_data.get('id', {}).get('videoId', '')
    title = video_data.get('snippet', {}).get('title', 'Unknown')
    channel = video_data.get('snippet', {}).get('channelTitle', 'Unknown Artist')
    thumbnail = video_data.get('snippet', {}).get('thumbnails', {}).get('high', {}).get('url', '')
    
    # Parse view count if available (from video details)
    view_count = video_data.get('statistics', {}).get('viewCount', 0)
    if isinstance(view_count, str):
        view_count = int(view_count)
    
    # Generate battle stats using the WeightedCardPool system
    card_pool = WeightedCardPool()
    
    # Determine rarity if not provided
    if not rarity:
        rarity = card_pool.get_rarity_from_views(view_count)
    
    # Generate stats based on rarity
    stats = card_pool.generate_stats_for_rarity(rarity)
    
    # Create card data
    card = {
        "card_id": str(uuid.uuid4()),
        "name": channel,
        "title": title,
        "rarity": rarity.lower(),
        "youtube_url": f"https://youtube.com/watch?v={video_id}",
        "image_url": thumbnail,
        "view_count": view_count,
        "impact": stats['impact'],
        "skill": stats['skill'],
        "longevity": stats['longevity'],
        "culture": stats['culture'],
        "hype": stats['hype']
    }
    
    return card

def search_artist_videos(artist_name: str, max_results: int = 10) -> List[dict]:
    """Search YouTube for an artist's videos
    
    Args:
        artist_name: Name of the artist
        max_results: Maximum number of results to return
    
    Returns:
        List of video data dictionaries
    """
    try:
        # Search YouTube
        search_query = f"{artist_name} official music video"
        results = youtube_integration.search_music_videos(search_query, max_results=max_results)
        return results
    except Exception as e:
        print(f"❌ Error searching for {artist_name}: {e}")
        return []

def create_pack_from_artist(artist_name: str, db: DatabaseManager, creator_id: int = 0) -> dict:
    """Create a pack from an artist's top videos
    
    Args:
        artist_name: Name of the artist
        db: Database manager instance
        creator_id: Creator user ID (0 for system)
    
    Returns:
        Pack data dictionary or None if failed
    """
    print(f"🔍 Searching for {artist_name}...")
    
    # Search for videos
    videos = search_artist_videos(artist_name, max_results=10)
    if not videos or len(videos) < 5:
        print(f"❌ Not enough videos found for {artist_name} (need 5, found {len(videos)})")
        return None
    
    # Select 5 videos with variety in rarity
    # Distribution: 1 legendary, 2 epic, 1 rare, 1 common
    rarity_distribution = ['legendary', 'epic', 'epic', 'rare', 'common']
    
    cards = []
    for i in range(5):
        video = videos[i]
        rarity = rarity_distribution[i]
        card = generate_card_from_video(video, rarity=rarity)
        cards.append(card)
    
    # Create pack data
    pack_id = str(uuid.uuid4())
    pack_data = {
        "pack_id": pack_id,
        "name": f"{artist_name} Collection",
        "description": f"Top tracks from {artist_name}",
        "creator_id": creator_id,
        "pack_size": 5,
        "price_cents": 699,
        "cards": cards
    }
    
    # Insert into database
    try:
        result = db.bulk_create_packs([pack_data])
        if pack_id in result['success']:
            print(f"✅ Created pack: {pack_data['name']} (ID: {pack_id[:8]}...)")
            return pack_data
        else:
            print(f"❌ Failed to create pack for {artist_name}")
            return None
    except Exception as e:
        print(f"❌ Error creating pack: {e}")
        return None

def seed_marketplace(artists: List[str], packs_per_artist: int = 1):
    """Seed marketplace with packs from artist list
    
    Args:
        artists: List of artist names
        packs_per_artist: Number of packs to create per artist
    """
    db = DatabaseManager()
    
    print(f"\n🌱 Seeding marketplace with {len(artists)} artists...")
    print(f"📦 Creating {packs_per_artist} pack(s) per artist\n")
    
    success_count = 0
    failed_count = 0
    
    for artist in artists:
        artist = artist.strip()
        if not artist:
            continue
        
        for i in range(packs_per_artist):
            pack = create_pack_from_artist(artist, db, creator_id=0)
            if pack:
                success_count += 1
            else:
                failed_count += 1
    
    print(f"\n✅ Seeding complete!")
    print(f"📊 Successfully created: {success_count} packs")
    print(f"❌ Failed: {failed_count} packs")

def main():
    parser = argparse.ArgumentParser(
        description='Seed marketplace with packs from artist lists'
    )
    parser.add_argument(
        '--artists',
        type=str,
        help='Comma-separated list of artists (e.g., "Drake,The Weeknd,Beyonce")'
    )
    parser.add_argument(
        '--artists-file',
        type=str,
        help='Path to file with one artist per line'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=1,
        help='Number of packs to create per artist (default: 1)'
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.artists and not args.artists_file:
        print("❌ Error: Must provide either --artists or --artists-file")
        parser.print_help()
        sys.exit(1)
    
    # Check YouTube API key
    if not settings.YOUTUBE_API_KEY:
        print("❌ Error: YOUTUBE_API_KEY not found in environment")
        print("   Make sure .env.txt is configured correctly")
        sys.exit(1)
    
    # Get artist list
    artists = []
    if args.artists:
        artists = [a.strip() for a in args.artists.split(',')]
    elif args.artists_file:
        try:
            with open(args.artists_file, 'r', encoding='utf-8') as f:
                artists = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"❌ Error: File not found: {args.artists_file}")
            sys.exit(1)
    
    if not artists:
        print("❌ Error: No artists provided")
        sys.exit(1)
    
    # Seed the marketplace
    seed_marketplace(artists, args.count)

if __name__ == "__main__":
    main()
