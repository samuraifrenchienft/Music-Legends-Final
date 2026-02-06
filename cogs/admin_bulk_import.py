# -*- coding: utf-8 -*-
"""
Admin Bulk Pack Import Cog
Provides commands for importing packs in bulk from JSON files
DEV-ONLY: Only available in TEST_SERVER
"""

import discord
from discord.ext import commands
from discord import Interaction, app_commands
from database import DatabaseManager
import json
import uuid
import os
from typing import List, Dict, Optional
import asyncio
from cogs.dev_helpers import check_and_respond

class AdminBulkImportCog(commands.Cog):
    """Dev-only commands for bulk pack creation (TEST_SERVER only)"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseManager()
        
        # Get TEST_SERVER_ID from environment - commands only available in this guild
        test_server_id = os.getenv('TEST_SERVER_ID')
        if test_server_id:
            try:
                self.test_guild_id = int(test_server_id)
                print(f"✅ Dev commands will be registered in TEST_SERVER: {self.test_guild_id}")
            except ValueError:
                self.test_guild_id = None
                print("⚠️  WARNING: TEST_SERVER_ID is not a valid integer")
        else:
            self.test_guild_id = None
            print("⚠️  WARNING: TEST_SERVER_ID not set - bulk import commands will not be registered")


    @app_commands.command(name="import_packs", description="[DEV] Import packs from JSON file")
    @app_commands.default_permissions(administrator=True)
    async def import_packs(self, interaction: Interaction, file: discord.Attachment):
        """Import multiple packs from a JSON file

        Args:
            file: JSON file containing pack data
        """
        print(f"\n{'='*60}")
        print(f"🔄 [IMPORT_PACKS] Command started")
        print(f"   User: {interaction.user.id}")
        print(f"   Guild: {interaction.guild_id}")
        print(f"   Channel: {interaction.channel_id}")
        print(f"   File: {file.filename}")
        print(f"{'='*60}\n")

        # Check authorization BEFORE defer (check_and_respond sends its own error via response)
        if not await check_and_respond(interaction):
            print(f"❌ [IMPORT_PACKS] Authorization failed")
            return

        print(f"✅ [IMPORT_PACKS] Authorization passed")

        # Defer after auth passes
        try:
            await interaction.response.defer(ephemeral=True)
            print(f"✅ [IMPORT_PACKS] Deferred interaction")
        except Exception as e:
            print(f"❌ [IMPORT_PACKS] Failed to defer: {e}")
            return

        # Validate file size (max 1MB)
        if file.size > 1_048_576:
            print(f"❌ [IMPORT_PACKS] File too large: {file.size} bytes")
            await interaction.followup.send(
                "❌ **Error:** File too large. Maximum size is 1MB.",
                ephemeral=True
            )
            return

        # Validate file type
        if not file.filename.endswith('.json'):
            print(f"❌ [IMPORT_PACKS] Invalid file type: {file.filename}")
            await interaction.followup.send(
                "❌ **Error:** File must be a JSON file (.json extension)",
                ephemeral=True
            )
            return
        
        print(f"✅ [IMPORT_PACKS] File type valid: {file.filename}")
        
        # Download and parse JSON
        try:
            print(f"📥 [IMPORT_PACKS] Reading file...")
            file_content = await file.read()
            print(f"✅ [IMPORT_PACKS] File read: {len(file_content)} bytes")
            
            data = json.loads(file_content.decode('utf-8'))
            print(f"✅ [IMPORT_PACKS] JSON parsed successfully")
        except json.JSONDecodeError as e:
            print(f"❌ [IMPORT_PACKS] JSON Parse Error: {e}")
            await interaction.followup.send(
                f"❌ **JSON Parse Error:** Invalid JSON format\n```{str(e)}```",
                ephemeral=True
            )
            return
        except Exception as e:
            print(f"❌ [IMPORT_PACKS] Read Error: {e}")
            await interaction.followup.send(
                f"❌ **Error:** Failed to read file\n```{str(e)}```",
                ephemeral=True
            )
            return
        
        print(f"📊 [IMPORT_PACKS] Validating JSON structure...")
        # Validate JSON structure
        validation_result = self._validate_json_structure(data)
        if not validation_result['valid']:
            error_msg = "\n".join([f"• {err}" for err in validation_result['errors']])
            print(f"❌ [IMPORT_PACKS] Validation failed:\n{error_msg}")
            await interaction.followup.send(
                f"❌ **Validation Failed:**\n{error_msg}",
                ephemeral=True
            )
            return
        
        print(f"✅ [IMPORT_PACKS] Validation passed")
        
        # Import packs
        print(f"📦 [IMPORT_PACKS] Starting pack creation...")
        packs_data = data.get('packs', [])
        results = {
            'success': [],
            'failed': []
        }
        
        for i, pack_data in enumerate(packs_data):
            try:
                print(f"  Creating pack {i+1}/{len(packs_data)}: {pack_data.get('name', 'Unknown')}")
                pack_id = await self._create_pack_from_data(pack_data, interaction.user.id)
                results['success'].append({
                    'name': pack_data['name'],
                    'pack_id': pack_id
                })
                print(f"  ✅ Created pack: {pack_id}")
                try:
                    from services.changelog_manager import log_pack_creation
                    log_pack_creation(pack_id, pack_data['name'], interaction.user.id, 'import')
                except Exception:
                    pass
            except Exception as e:
                print(f"  ❌ Error creating pack: {e}")
                import traceback
                traceback.print_exc()
                results['failed'].append({
                    'name': pack_data.get('name', 'Unknown'),
                    'error': str(e)
                })
        
        print(f"📊 [IMPORT_PACKS] Results: {len(results['success'])} success, {len(results['failed'])} failed")
        
        # Create response embed
        embed = discord.Embed(
            title="📦 Bulk Pack Import Results",
            color=discord.Color.green() if len(results['failed']) == 0 else discord.Color.orange()
        )
        
        if results['success']:
            success_text = "\n".join([f"✅ **{p['name']}** (`{p['pack_id'][:8]}...`)" for p in results['success']])
            embed.add_field(
                name=f"✅ Successfully Imported ({len(results['success'])})",
                value=success_text[:1024],  # Discord field limit
                inline=False
            )
        
        if results['failed']:
            failed_text = "\n".join([f"❌ **{p['name']}**: {p['error']}" for p in results['failed']])
            embed.add_field(
                name=f"❌ Failed ({len(results['failed'])})",
                value=failed_text[:1024],  # Discord field limit
                inline=False
            )
        
        embed.set_footer(text=f"Total: {len(packs_data)} packs processed")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        print(f"✅ [IMPORT_PACKS] Command completed\n")
    
    def _validate_json_structure(self, data: dict) -> Dict[str, any]:
        """Validate the JSON structure matches expected schema"""
        errors = []
        
        if not isinstance(data, dict):
            errors.append("Root must be a JSON object")
            return {'valid': False, 'errors': errors}
        
        if 'packs' not in data:
            errors.append("Missing 'packs' array in root object")
            return {'valid': False, 'errors': errors}
        
        if not isinstance(data['packs'], list):
            errors.append("'packs' must be an array")
            return {'valid': False, 'errors': errors}
        
        if len(data['packs']) == 0:
            errors.append("'packs' array is empty")
            return {'valid': False, 'errors': errors}
        
        # Validate each pack
        for i, pack in enumerate(data['packs']):
            pack_errors = self._validate_pack_data(pack, i)
            errors.extend(pack_errors)
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _validate_pack_data(self, pack: dict, index: int) -> List[str]:
        """Validate a single pack's data structure"""
        errors = []
        prefix = f"Pack {index + 1}"
        
        # Required fields
        if 'name' not in pack:
            errors.append(f"{prefix}: Missing 'name' field")
        elif not isinstance(pack['name'], str) or len(pack['name']) == 0:
            errors.append(f"{prefix}: 'name' must be a non-empty string")
        elif len(pack['name']) > 100:
            errors.append(f"{prefix}: 'name' too long (max 100 chars)")
        
        if 'cards' not in pack:
            errors.append(f"{prefix}: Missing 'cards' array")
            return errors  # Can't validate cards if missing
        
        if not isinstance(pack['cards'], list):
            errors.append(f"{prefix}: 'cards' must be an array")
            return errors
        
        if len(pack['cards']) < 1 or len(pack['cards']) > 25:
            errors.append(f"{prefix}: Must have 1-25 cards (has {len(pack['cards'])})")
        
        # Validate each card
        for j, card in enumerate(pack['cards']):
            card_errors = self._validate_card_data(card, index, j)
            errors.extend(card_errors)
        
        # Optional fields validation
        if 'creator_id' in pack and not isinstance(pack['creator_id'], int):
            errors.append(f"{prefix}: 'creator_id' must be an integer")
        
        if 'price_cents' in pack and not isinstance(pack['price_cents'], int):
            errors.append(f"{prefix}: 'price_cents' must be an integer")
        
        if 'pack_size' in pack and (pack['pack_size'] < 1 or pack['pack_size'] > 25):
            errors.append(f"{prefix}: 'pack_size' must be 1-25")
        
        return errors
    
    def _validate_card_data(self, card: dict, pack_index: int, card_index: int) -> List[str]:
        """Validate a single card's data structure"""
        errors = []
        prefix = f"Pack {pack_index + 1}, Card {card_index + 1}"
        
        # Required fields
        if 'name' not in card or not card['name']:
            errors.append(f"{prefix}: Missing 'name' field")
        
        if 'rarity' not in card:
            errors.append(f"{prefix}: Missing 'rarity' field")
        elif card['rarity'] not in ['common', 'rare', 'epic', 'legendary']:
            errors.append(f"{prefix}: Invalid rarity '{card['rarity']}' (must be: common, rare, epic, legendary)")
        
        # Validate stats (if provided)
        stats = ['impact', 'skill', 'longevity', 'culture', 'hype']
        for stat in stats:
            if stat in card:
                if not isinstance(card[stat], int):
                    errors.append(f"{prefix}: '{stat}' must be an integer")
                elif card[stat] < 0 or card[stat] > 92:
                    errors.append(f"{prefix}: '{stat}' must be between 0-92 (got {card[stat]})")
        
        return errors
    
    async def _create_pack_from_data(self, pack_data: dict, importer_user_id: int) -> str:
        """Create a pack from validated JSON data

        Args:
            pack_data: Validated pack data dictionary
            importer_user_id: Discord user ID who is importing

        Returns:
            pack_id: Created pack ID
        """
        import random as _rand

        # Generate pack ID
        pack_id = str(uuid.uuid4())

        # Get creator ID (default to importer)
        creator_id = pack_data.get('creator_id', importer_user_id)

        # Get pack details
        name = pack_data['name']
        description = pack_data.get('description', f"Imported pack - {name}")
        pack_size = len(pack_data['cards'])
        price_cents = pack_data.get('price_cents', 699)

        # Stat ranges by rarity (for auto-generation when not provided)
        RARITY_STAT_RANGES = {
            'common':    (15, 35),
            'rare':      (30, 50),
            'epic':      (45, 70),
            'legendary': (60, 90),
        }

        # Prepare cards: generate card_ids and stats BEFORE storing JSON
        for card_data in pack_data['cards']:
            if 'card_id' not in card_data:
                card_data['card_id'] = str(uuid.uuid4())

            card_data['pack_id'] = pack_id

            # Auto-generate stats if not provided
            rarity = card_data.get('rarity', 'common')
            lo, hi = RARITY_STAT_RANGES.get(rarity, (15, 35))
            for stat in ['impact', 'skill', 'longevity', 'culture', 'hype']:
                if stat not in card_data or card_data[stat] == 0:
                    card_data[stat] = _rand.randint(lo, hi)

        # Now serialize with card_ids and stats included
        cards_json = json.dumps(pack_data['cards'])

        # Create pack in LIVE status (skip payment for admin import)
        import sqlite3
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # Initialize creator if not exists
            cursor.execute("""
                INSERT OR IGNORE INTO creator_pack_limits (creator_id)
                VALUES (?)
            """, (creator_id,))

            cursor.execute("""
                INSERT INTO creator_packs
                (pack_id, creator_id, name, description, pack_size, status, cards_data,
                 published_at, price_cents, stripe_payment_id)
                VALUES (?, ?, ?, ?, ?, 'LIVE', ?, CURRENT_TIMESTAMP, ?, 'ADMIN_IMPORT')
            """, (pack_id, creator_id, name, description, pack_size, cards_json, price_cents))

            # Add cards to master card list
            for card_data in pack_data['cards']:
                self.db.add_card_to_master(card_data)

            # Update creator limits
            cursor.execute("""
                UPDATE creator_pack_limits
                SET packs_published = packs_published + 1,
                    last_pack_published = strftime('%s', 'now')
                WHERE creator_id = ?
            """, (creator_id,))

            conn.commit()

        return pack_id
    

async def setup(bot: commands.Bot):
    # IMPORT COMMAND REMOVED - Use CLI script instead
    # See cli_scripts/cli_import_packs.py
    #
    # This cog is disabled. Uncomment below to re-enable if needed.
    # await bot.add_cog(AdminBulkImportCog(bot))
    pass
