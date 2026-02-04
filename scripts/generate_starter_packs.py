"""
Starter Pack Generator - Create comprehensive pre-built packs across genres
Generates EDM, Rock, R&B, Pop, and Hip Hop category packs for the marketplace
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import uuid

from database import DatabaseManager
from services.changelog_manager import log_pack_creation
from services.bot_logger import log_event, log_pack
from music_api_manager import MusicAPIManager


class StarterPackGenerator:
    """Generate comprehensive starter packs across multiple genres"""
    
    PACK_CATEGORIES = {
        'EDM Bangers': [
            ['Calvin Harris', 'David Guetta', 'The Chainsmokers', 'Zedd', 'Kygo'],
            ['Marshmello', 'Martin Garrix', 'Tiësto', 'Diplo', 'Steve Aoki'],
            ['Avicii', 'Deadmau5', 'Skrillex', 'Major Lazer', 'Illenium'],
            ['Daft Punk', 'Alesso', 'Hardwell', 'Swedish House Mafia', 'Porter Robinson'],
            ['Armin van Buuren', 'Above & Beyond', 'Dash Berlin', 'Paul van Dyk', 'Infected Mushroom']
        ],
        'Rock Classics': [
            ['The Beatles', 'Led Zeppelin', 'Pink Floyd', 'Queen', 'The Rolling Stones'],
            ['Guns N\' Roses', 'Aerosmith', 'AC/DC', 'Bon Jovi', 'Journey'],
            ['Metallica', 'Nirvana', 'Pearl Jam', 'Red Hot Chili Peppers', 'Green Day'],
            ['U2', 'Radiohead', 'The Who', 'The Doors', 'Def Leppard'],
            ['David Bowie', 'Elton John', 'Bruce Springsteen', 'Tom Petty', 'Fleetwood Mac']
        ],
        'R&B Soul Pack': [
            ['Marvin Gaye', 'Stevie Wonder', 'Al Green', 'Luther Vandross', 'Aretha Franklin'],
            ['Usher', 'John Legend', 'Alicia Keys', 'Maxwell', 'Mary J. Blige'],
            ['Whitney Houston', 'Boyz II Men', 'R. Kelly', 'Babyface', 'Toni Braxton'],
            ['Sam Cooke', 'Ray Charles', 'Otis Redding', 'James Brown', 'Nina Simone'],
            ['Brandy', 'Monica', 'Jagged Edge', 'TLC', 'Boyz II Men']
        ],
        'Pop Hits': [
            ['Taylor Swift', 'The Weeknd', 'Dua Lipa', 'Billie Eilish', 'Harry Styles'],
            ['Bruno Mars', 'Ariana Grande', 'Ed Sheeran', 'Post Malone', 'Doja Cat'],
            ['Justin Bieber', 'Olivia Rodrigo', 'Shawn Mendes', 'Selena Gomez', 'Charlie Puth'],
            ['Drake', 'Bad Bunny', 'Halsey', 'Khalid', 'Camila Cabello'],
            ['Lady Gaga', 'Maroon 5', 'Coldplay', 'Sam Smith', 'Imagine Dragons']
        ],
        'Hip Hop Legends': [
            ['Tupac', 'The Notorious B.I.G.', 'Snoop Dogg', 'Dr. Dre', 'Ice Cube'],
            ['Jay-Z', 'Eminem', '50 Cent', 'Nas', 'Method Man'],
            ['Kanye West', 'Kendrick Lamar', 'Drake', 'J. Cole', 'Travis Scott'],
            ['LL Cool J', 'Run-DMC', 'Busta Rhymes', 'Missy Elliott', 'Wu-Tang Clan'],
            ['OutKast', 'Lauryn Hill', 'Chance the Rapper', 'A Tribe Called Quest', 'Common']
        ]
    }
    
    def __init__(self, db: DatabaseManager = None, api_manager: MusicAPIManager = None):
        """
        Initialize starter pack generator
        
        Args:
            db: Database manager instance
            api_manager: Music API manager instance
        """
        self.db = db or DatabaseManager()
        self.api_manager = api_manager or MusicAPIManager()
        
        self.created_packs = []
        self.failed_packs = []
        self.total_cards_created = 0
    
    async def generate_all_packs(self) -> Dict:
        """
        Generate all starter packs across all categories
        
        Returns:
            Dictionary with generation results
        """
        print("\n🎵 Starting Starter Pack Generation...")
        print(f"📊 Categories: {len(self.PACK_CATEGORIES)}")
        print(f"📦 Total Packs: {sum(len(groups) for groups in self.PACK_CATEGORIES.values())}\n")
        
        for genre, artist_groups in self.PACK_CATEGORIES.items():
            print(f"\n🎸 Generating {genre} packs...")
            
            for i, artist_group in enumerate(artist_groups, 1):
                pack_name = f"{genre} - Vol. {i}"
                primary_artist = artist_group[0]
                
                try:
                    pack_id = await self._create_starter_pack(
                        pack_name=pack_name,
                        primary_artist=primary_artist,
                        featured_artists=artist_group[1:],
                        genre=genre,
                        pack_number=i
                    )
                    
                    if pack_id:
                        self.created_packs.append({
                            'pack_id': pack_id,
                            'pack_name': pack_name,
                            'genre': genre,
                            'primary_artist': primary_artist
                        })
                        print(f"  ✅ {pack_name}: {primary_artist}")
                
                except Exception as e:
                    error_msg = f"{pack_name}: {str(e)}"
                    self.failed_packs.append(error_msg)
                    print(f"  ❌ {error_msg}")
        
        return self._generate_report()
    
    async def _create_starter_pack(
        self,
        pack_name: str,
        primary_artist: str,
        featured_artists: List[str],
        genre: str,
        pack_number: int
    ) -> Optional[str]:
        """
        Create a single starter pack
        
        Args:
            pack_name: Name of the pack
            primary_artist: Primary artist for the pack
            featured_artists: List of featured artists
            genre: Genre category
            pack_number: Pack number in series
            
        Returns:
            Pack ID if successful, None otherwise
        """
        try:
            # Create pack ID
            pack_id = f"starter_{genre.lower().replace(' ', '_')}_{pack_number}_{uuid.uuid4().hex[:8]}"
            
            # Create pack in database
            pack_created = self.db.create_creator_pack(
                creator_id=0,  # System creator
                name=pack_name,
                description=f"Curated {genre} collection featuring {primary_artist} and more",
                pack_size=5
            )
            
            if not pack_created:
                return None
            
            # Generate cards for all featured artists
            all_artists = [primary_artist] + featured_artists
            cards_created = 0
            
            for artist_name in all_artists[:5]:  # Limit to 5 artists per pack
                try:
                    # Get artist data
                    artist_data = await self.api_manager.get_artist_info(artist_name)
                    
                    if not artist_data:
                        continue
                    
                    # Create card for this artist
                    card_id = f"{pack_id}_{artist_name.lower().replace(' ', '_')}"
                    
                    card_data = {
                        'card_id': card_id,
                        'pack_id': pack_id,
                        'name': artist_name,
                        'title': f"{artist_name} - {genre}",
                        'rarity': self._assign_rarity(cards_created),
                        'image_url': artist_data.get('image_url', ''),
                        'genre': genre,
                        'impact': 50,
                        'skill': 50,
                        'longevity': 50,
                        'culture': 50,
                        'hype': 50,
                        'created_by_user_id': 0
                    }
                    
                    # Store card in database
                    self.db.add_card_to_collection(0, card_id, 'starter_pack')
                    cards_created += 1
                    self.total_cards_created += 1
                
                except Exception as e:
                    print(f"    ⚠️  Card creation error for {artist_name}: {e}")
                    continue
            
            # Log the pack creation
            log_pack(
                action='created',
                pack_id=pack_id,
                artist=primary_artist,
                creator_id=0,
                pack_type='starter'
            )
            
            return pack_created if cards_created > 0 else None
        
        except Exception as e:
            print(f"Error creating pack {pack_name}: {e}")
            return None
    
    def _assign_rarity(self, card_index: int) -> str:
        """
        Assign rarity based on card position
        
        Args:
            card_index: Index of card in pack (0-4)
            
        Returns:
            Rarity string (common, rare, epic, legendary)
        """
        if card_index == 0:
            return 'legendary'
        elif card_index == 1:
            return 'epic'
        elif card_index == 2:
            return 'rare'
        else:
            return 'common'
    
    def _generate_report(self) -> Dict:
        """Generate generation report"""
        total_attempted = len(self.created_packs) + len(self.failed_packs)
        success_rate = (len(self.created_packs) / total_attempted * 100) if total_attempted > 0 else 0
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_packs_attempted': total_attempted,
            'packs_created': len(self.created_packs),
            'packs_failed': len(self.failed_packs),
            'success_rate': f"{success_rate:.1f}%",
            'total_cards_created': self.total_cards_created,
            'created_packs': self.created_packs,
            'failed_packs': self.failed_packs,
        }
        
        return report
    
    def save_report(self, report: Dict, filepath: str = 'starter_packs_report.json') -> bool:
        """Save generation report to file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n📋 Report saved to {filepath}")
            return True
        except Exception as e:
            print(f"Error saving report: {e}")
            return False
    
    def print_report(self, report: Dict) -> None:
        """Print formatted generation report"""
        print("\n" + "="*60)
        print("📊 STARTER PACK GENERATION REPORT")
        print("="*60)
        
        print(f"\n✅ Packs Created: {report['packs_created']}")
        print(f"❌ Packs Failed: {report['packs_failed']}")
        print(f"📈 Success Rate: {report['success_rate']}")
        print(f"🎴 Total Cards Created: {report['total_cards_created']}")
        
        if report['created_packs']:
            print("\n✅ Successfully Created Packs:")
            for pack in report['created_packs'][:10]:  # Show first 10
                print(f"  • {pack['pack_name']} ({pack['primary_artist']})")
            
            if len(report['created_packs']) > 10:
                print(f"  ... and {len(report['created_packs']) - 10} more")
        
        if report['failed_packs']:
            print("\n❌ Failed Packs:")
            for error in report['failed_packs'][:5]:  # Show first 5
                print(f"  • {error}")
            
            if len(report['failed_packs']) > 5:
                print(f"  ... and {len(report['failed_packs']) - 5} more")
        
        print(f"\n📅 Generated: {report['timestamp']}")
        print("="*60 + "\n")


async def generate_starter_packs(save_report: bool = True) -> Dict:
    """
    Convenience function to generate all starter packs
    
    Args:
        save_report: Whether to save report to file
        
    Returns:
        Generation report dictionary
    """
    generator = StarterPackGenerator()
    report = await generator.generate_all_packs()
    
    generator.print_report(report)
    
    if save_report:
        generator.save_report(report)
    
    # Log to system
    log_event(
        'starter_packs_generated',
        f"Generated {report['packs_created']} starter packs ({report['success_rate']} success rate)",
        severity='high',
        send_alert=True
    )
    
    return report


if __name__ == "__main__":
    print("🎵 Music Legends Starter Pack Generator")
    print("Starting pack generation...\n")
    
    # Run generator
    asyncio.run(generate_starter_packs())
