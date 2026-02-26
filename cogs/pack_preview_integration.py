# cogs/pack_preview_integration.py
"""
Pack Preview Integration Functions
Handles the preview step between song selection and pack finalization
"""

import discord
from discord import Interaction
import random
import sqlite3
from music_api_manager import music_api
from views.pack_preview import PackPreviewView, reroll_all_cards


async def show_pack_preview_lastfm(
    confirm_interaction: Interaction,
    pack_name: str,
    artist_data: dict,
    selected_tracks: list,
    preview_cards: list,
    pack_type: str,
    db,
    original_interaction: Interaction
):
    """Show pack preview with re-roll and confirmation options"""
    
    try:
        # Interaction is already deferred from song selection button
        # Use followup.send directly
        
        # Define callbacks for preview view
        async def on_confirm(preview_interaction: Interaction, final_cards: list):
            """Finalize pack creation with confirmed cards"""
            await finalize_pack_with_cards(
                preview_interaction,
                pack_name,
                artist_data,
                selected_tracks,
                final_cards,
                confirm_interaction.user.id,
                pack_type,
                db
            )
        
        async def on_reroll(cards: list):
            """Re-roll card stats"""
            return await reroll_all_cards(cards, pack_type)
        
        async def on_change_songs(change_interaction: Interaction):
            """Go back to song selection"""
            await change_interaction.followup.send(
                "🔄 To change songs, please start the pack creation process again.",
                ephemeral=True
            )
        
        # Create preview view
        preview_view = PackPreviewView(
            pack_name=pack_name,
            artist_name=artist_data['name'],
            cards_preview=preview_cards,
            pack_type=pack_type,
            on_confirm=on_confirm,
            on_reroll=on_reroll,
            on_change_songs=on_change_songs
        )
        
        # Create preview embed
        preview_embed = preview_view.create_preview_embed()
        
        # Show preview
        await confirm_interaction.followup.send(
            embed=preview_embed,
            view=preview_view,
            ephemeral=True
        )
        
    except Exception as e:
        print(f"❌ Error showing pack preview: {e}")
        import traceback
        traceback.print_exc()
        await confirm_interaction.followup.send(
            "❌ Something went wrong showing the preview. Please try again.",
            ephemeral=True
        )


async def finalize_pack_with_cards(
    interaction: Interaction,
    pack_name: str,
    artist_data: dict,
    selected_tracks: list,
    final_cards: list,
    creator_id: int,
    pack_type: str,
    db
):
    """Finalize pack creation with confirmed cards"""
    
    try:
        # Create pack in database
        pack_id = db.create_creator_pack(
            creator_id=creator_id,
            name=pack_name,
            description=f"{pack_type.title()} pack featuring {artist_data['name']}",
            pack_size=len(final_cards)
        )
        
        if not pack_id:
            await interaction.followup.send("❌ Failed to create pack in database", ephemeral=True)
            return
        
        # Add cards to database
        cards_created = []
        
        for i, card in enumerate(final_cards):
            try:
                # Create card ID
                track = selected_tracks[i]
                card_id = f"{pack_id}_{track['name'].lower().replace(' ', '_')[:20]}_{random.randint(1000, 9999)}"
                
                # Prepare card data for database with defaults
                db_card_data = {
                    'card_id': card_id,
                    'name': artist_data['name'],
                    'title': card.get('name', track['name'])[:100],
                    'rarity': card.get('rarity', 'common'),
                    'image_url': card.get('image_url', ''),
                    'youtube_url': card.get('video_url', ''),
                    'impact': card.get('attack', 50),
                    'skill': card.get('defense', 50),
                    'longevity': card.get('speed', 50),
                    'culture': card.get('attack', 50),
                    'hype': card.get('defense', 50),
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
                print(f"❌ Error creating card: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Publish pack
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE creator_packs 
                SET status = 'LIVE', published_at = CURRENT_TIMESTAMP
                WHERE pack_id = ?
            """, (pack_id,))
            conn.commit()
        db.add_to_dev_supply(pack_id)
        
        # Trigger backup after pack is published to marketplace
        try:
            from services.backup_service import backup_service
            backup_path = await backup_service.backup_critical('pack_published', pack_id)
            if backup_path:
                print(f"💾 Critical backup created after pack publication: {backup_path}")
        except Exception as e:
            print(f"⚠️ Backup trigger failed (non-critical): {e}")
        
        # Create success embed
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
        print(f"❌ Error finalizing pack: {e}")
        import traceback
        traceback.print_exc()
        await interaction.followup.send("❌ Something went wrong finalizing the pack. Please try again.", ephemeral=True)
