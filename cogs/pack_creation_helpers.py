# pack_creation_helpers.py
"""
Helper methods for pack creation in menu_system.py
Separated to keep menu_system.py cleaner
"""

import discord
from discord import Interaction
import random
import sqlite3
from music_api_manager import music_api
from views.song_selection import SongSelectionView
from cogs.pack_preview_integration import show_pack_preview_lastfm


async def show_song_selection_lastfm(
    interaction: Interaction,
    pack_name: str,
    artist_data: dict,
    tracks: list,
    pack_type: str,
    db,
    finalize_callback,
    use_smaller_image: bool = False
):
    """Show song selection UI using Last.fm data"""
    
    # Create selection embed
    selection_embed = discord.Embed(
        title=f"🎵 Select Songs for Your {pack_type.title()} Pack",
        description=(
            f"**{pack_name}** featuring **{artist_data['name']}**\n\n"
            f"✅ Using Last.fm images and data\n"
            f"Select up to 5 songs for your pack."
        ),
        color=discord.Color.gold() if pack_type == 'gold' else discord.Color.blue()
    )
    
    if artist_data.get('image_xlarge'):
        selection_embed.set_thumbnail(url=artist_data['image_xlarge'])
    
    selection_embed.add_field(
        name="📋 Instructions",
        value="1. Select songs from the dropdown menu\n"
              "2. Click 'Confirm Selection' to create your pack\n"
              "3. Cards will be generated with stats based on popularity",
        inline=False
    )
    
    # Add pack type info
    if pack_type == 'gold':
        selection_embed.add_field(
            name="💎 Gold Pack Bonus",
            value="Higher base stats (70-92) • Better rarity chances",
            inline=False
        )
    else:
        selection_embed.add_field(
            name="📦 Community Pack",
            value="Standard stats (50-85) • Normal rarity distribution",
            inline=False
        )
    
    # Format tracks for selection view
    formatted_tracks = []
    for track in tracks:
        # Choose image size based on user preference
        if use_smaller_image:
            # Try ALL available image sizes in order of preference
            thumbnail = (track.get('image_medium') or 
                        track.get('image_large') or 
                        track.get('image_xlarge') or
                        artist_data.get('image_medium') or 
                        artist_data.get('image_large') or 
                        artist_data.get('image_xlarge') or
                        track.get('image') or  # Fallback to any image
                        artist_data.get('image', ''))
            print(f"🔧 Using smaller image: {thumbnail[:50] if thumbnail else 'NO IMAGE'}")
        else:
            # Use largest available image with fallbacks
            thumbnail = (track.get('youtube_thumbnail') or 
                        track.get('image_xlarge') or 
                        track.get('image_large') or 
                        track.get('image_medium') or
                        artist_data.get('image_xlarge') or 
                        artist_data.get('image_large') or 
                        artist_data.get('image_medium') or
                        track.get('image') or
                        artist_data.get('image', ''))
        
        formatted_tracks.append({
            'title': f"{track['name']} ({track['playcount']:,} plays)",
            'track_data': track,
            'thumbnail_url': thumbnail
        })
    
    # Create callback for when songs are selected
    async def on_songs_selected(confirm_interaction: Interaction, selected_tracks_raw: list):
        # selected_tracks_raw are formatted track dicts from SongSelectionView
        # Extract the actual track_data from each formatted track
        selected_tracks = []
        for item in selected_tracks_raw:
            if isinstance(item, dict) and 'track_data' in item:
                selected_tracks.append(item['track_data'])
            else:
                selected_tracks.append(item)
        
        # Generate preview cards
        preview_cards = []
        for track in selected_tracks:
            card_data = music_api.format_track_for_card(
                track=track,
                artist_name=artist_data['name'],
                pack_type=pack_type,
                image_url=track.get('image_xlarge') or artist_data.get('image_xlarge'),
                video_url=track.get('url', '')
            )
            preview_cards.append(card_data)
        
        # Show pack preview
        await show_pack_preview_lastfm(
            confirm_interaction,
            pack_name,
            artist_data,
            selected_tracks,
            preview_cards,
            pack_type,
            db,
            interaction
        )
    
    # Show selection view
    view = SongSelectionView(formatted_tracks, max_selections=5, callback=on_songs_selected)
    await interaction.followup.send(
        embed=selection_embed,
        view=view,
        ephemeral=False
    )


async def finalize_pack_creation_lastfm(
    interaction: Interaction,
    pack_name: str,
    artist_data: dict,
    selected_tracks: list,
    creator_id: int,
    pack_type: str,
    db
):
    """Finalize pack creation with Last.fm data"""
    
    try:
        await interaction.response.defer(ephemeral=True)
        
        # Create pack in database
        pack_id = db.create_creator_pack(
            creator_id=creator_id,
            name=pack_name,
            description=f"{pack_type.title()} pack featuring {artist_data['name']}",
            pack_size=len(selected_tracks)
        )
        
        if not pack_id:
            await interaction.followup.send("❌ Failed to create pack in database", ephemeral=True)
            return
        
        # Generate cards for each selected track
        cards_created = []
        
        for track in selected_tracks:
            try:
                # Calculate stats from Last.fm play count
                card_data = music_api.format_track_for_card(
                    track=track,
                    artist_name=artist_data['name'],
                    pack_type=pack_type,
                    image_url=track.get('image_xlarge') or artist_data.get('image_xlarge'),
                    video_url=track.get('url', '')
                )
                
                # Create card ID
                card_id = f"{pack_id}_{track['name'].lower().replace(' ', '_')[:20]}_{random.randint(1000, 9999)}"
                
                # Prepare card data for database - ensure all required fields are present
                db_card_data = {
                    'card_id': card_id,
                    'name': artist_data['name'],
                    'title': card_data.get('name', track['name'])[:100],
                    'rarity': card_data.get('rarity', 'common'),
                    'image_url': card_data.get('image_url', ''),
                    'youtube_url': card_data.get('video_url', ''),
                    'impact': card_data.get('attack', 50),
                    'skill': card_data.get('defense', 50),
                    'longevity': card_data.get('speed', 50),
                    'culture': card_data.get('attack', 50),  # Fallback to attack
                    'hype': card_data.get('defense', 50),    # Fallback to defense
                    'pack_id': pack_id,
                    'created_by_user_id': creator_id
                }
                
                print(f"📦 Creating card: {db_card_data['title']} (Rarity: {db_card_data['rarity']})")
                
                # Add card to master list
                success = db.add_card_to_master(db_card_data)
                if success:
                    db.add_card_to_pack(pack_id, db_card_data)
                    # Give creator a copy
                    db.add_card_to_collection(creator_id, card_id, 'pack_creation')
                    cards_created.append(db_card_data)
                    print(f"✅ Card created successfully: {card_id}")
                else:
                    print(f"❌ Failed to add card to database: {card_id}")
                
            except Exception as e:
                print(f"❌ Error creating card for track {track.get('name', 'Unknown')}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Publish pack
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE creator_packs 
                SET status = 'LIVE', published_at = CURRENT_TIMESTAMP
                WHERE pack_id = ?
            """, (pack_id,))
            conn.commit()
        
        # Create confirmation embed
        embed = discord.Embed(
            title="✅ Pack Created Successfully!",
            description=f"**{pack_name}** is now live in the marketplace!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📦 Pack Details",
            value=f"**Pack ID:** {pack_id}\n"
                  f"**Artist:** {artist_data['name']}\n"
                  f"**Cards:** {len(cards_created)}\n"
                  f"**Type:** {pack_type.title()}",
            inline=False
        )
        
        # Show card list with stats
        if cards_created:
            card_list = []
            rarity_counts = {'common': 0, 'rare': 0, 'epic': 0, 'legendary': 0, 'mythic': 0}
            
            for card in cards_created:
                rarity = card['rarity']
                rarity_counts[rarity] += 1
                power = (card['impact'] + card['skill'] + card['longevity']) // 3
                
                rarity_emoji = {
                    'common': '⚪',
                    'rare': '🔵',
                    'epic': '🟣',
                    'legendary': '🟡',
                    'mythic': '🔴'
                }.get(rarity, '⚪')
                
                card_list.append(f"{rarity_emoji} **{card['title']}** ({power} power)")
            
            embed.add_field(
                name="🎴 Cards Created",
                value="\n".join(card_list[:5]) + (f"\n...and {len(card_list) - 5} more" if len(card_list) > 5 else ""),
                inline=False
            )
            
            # Rarity distribution
            rarity_text = " • ".join([
                f"{count} {rarity.title()}" 
                for rarity, count in rarity_counts.items() if count > 0
            ])
            embed.add_field(
                name="📊 Rarity Distribution",
                value=rarity_text,
                inline=False
            )
        
        if artist_data.get('image_xlarge'):
            embed.set_thumbnail(url=artist_data['image_xlarge'])
        
        embed.set_footer(text=f"✨ All {len(cards_created)} cards have been added to your collection!")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        print(f"❌ Error finalizing Last.fm pack: {e}")
        import traceback
        traceback.print_exc()
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
