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
from cogs.dev_helpers import check_test_server

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
    @app_commands.check(check_test_server)
    async def import_packs(self, interaction: Interaction, file: discord.Attachment):
        """Import multiple packs from a JSON file
        
        Args:
            file: JSON file containing pack data
        """
        await interaction.response.defer(ephemeral=True)
        
        # Validate file type
        if not file.filename.endswith('.json'):
            await interaction.followup.send(
                "❌ **Error:** File must be a JSON file (.json extension)",
                ephemeral=True
            )
            return
        
        # Download and parse JSON
        try:
            file_content = await file.read()
            data = json.loads(file_content.decode('utf-8'))
        except json.JSONDecodeError as e:
            await interaction.followup.send(
                f"❌ **JSON Parse Error:** Invalid JSON format\n```{str(e)}```",
                ephemeral=True
            )
            return
        except Exception as e:
            await interaction.followup.send(
                f"❌ **Error:** Failed to read file\n```{str(e)}```",
                ephemeral=True
            )
            return
        
        # Validate JSON structure
        validation_result = self._validate_json_structure(data)
        if not validation_result['valid']:
            error_msg = "\n".join([f"• {err}" for err in validation_result['errors']])
            await interaction.followup.send(
                f"❌ **Validation Failed:**\n{error_msg}",
                ephemeral=True
            )
            return
        
        # Import packs
        packs_data = data.get('packs', [])
        results = {
            'success': [],
            'failed': []
        }
        
        for pack_data in packs_data:
            try:
                pack_id = await self._create_pack_from_data(pack_data, interaction.user.id)
                results['success'].append({
                    'name': pack_data['name'],
                    'pack_id': pack_id
                })
            except Exception as e:
                results['failed'].append({
                    'name': pack_data.get('name', 'Unknown'),
                    'error': str(e)
                })
        
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
    
    @app_commands.command(name="import_packs_help", description="[DEV] Show detailed help and examples for JSON pack import")
    @app_commands.check(check_test_server)
    async def import_packs_help(self, interaction: Interaction):
        """Show help and examples for JSON pack import"""
        await interaction.response.defer(ephemeral=True)
        
        embed = discord.Embed(
            title="📦 Pack Import Help",
            description="How to create and import packs using JSON files",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Step 1: Generate Template",
            value="`/create_pack_template num_packs:5`\nGenerates example packs to edit",
            inline=False
        )
        
        embed.add_field(
            name="Step 2: Edit Template",
            value="Download the file and customize pack names, cards, stats, etc.",
            inline=False
        )
        
        embed.add_field(
            name="Step 3: Import",
            value="`/import_packs file:[your_file.json]`\nAttach your edited JSON file",
            inline=False
        )
        
        embed.add_field(
            name="JSON Structure Example",
            value="""```json
{
  "packs": [
    {
      "name": "Pack Name",
      "description": "Optional pack description",
      "creator_id": 123456789,
      "price_cents": 699,
      "cards": [
        {
          "name": "Artist Name",
          "title": "Song Title",
          "rarity": "legendary",
          "impact": 90,
          "skill": 88,
          "longevity": 85,
          "culture": 92,
          "hype": 87
        }
        // ... 4 more cards (exactly 5 total)
      ]
    }
  ]
}
```""",
            inline=False
        )
        
        embed.add_field(
            name="Requirements",
            value="• Exactly 5 cards per pack\n• Valid rarities: `common`, `rare`, `epic`, `legendary`\n• Stats: 0-92",
            inline=False
        )
        
        embed.add_field(
            name="Optional Fields",
            value="• `description` - Pack description\n• `creator_id` - Discord user ID\n• `price_cents` - Price (default: 699 = $6.99)",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="create_pack_template", description="[DEV] Generate a template JSON file for pack creation")
    @app_commands.check(check_test_server)
    @app_commands.describe(num_packs="Number of example packs to generate (1-10)")
    async def create_pack_template(self, interaction: Interaction, num_packs: int = 5):
        """Generate a template JSON file with example packs"""
        await interaction.response.defer(ephemeral=True)
        
        # Validate input
        if num_packs < 1 or num_packs > 10:
            await interaction.followup.send(
                "❌ **Error:** num_packs must be between 1 and 10",
                ephemeral=True
            )
            return
        
        # Generate template
        template = {
            "packs": []
        }
        
        for i in range(num_packs):
            pack = {
                "name": f"Example Pack {i + 1}",
                "description": f"This is an example pack - edit this text",
                "creator_id": int(interaction.user.id),
                "price_cents": 699,
                "cards": [
                    {
                        "name": f"Artist {i + 1} - Card {j + 1}",
                        "title": f"Song Title {j + 1}",
                        "rarity": ["common", "rare", "epic", "legendary"][j % 4],
                        "impact": 50 + (j * 10),
                        "skill": 55 + (j * 8),
                        "longevity": 50 + (j * 10),
                        "culture": 60 + (j * 5),
                        "hype": 50 + (j * 10)
                    }
                    for j in range(5)
                ]
            }
            template["packs"].append(pack)
        
        # Save to file
        filename = f"pack_template_{num_packs}_packs.json"
        filepath = filename
        
        try:
            with open(filepath, 'w') as f:
                json.dump(template, f, indent=2)
            
            # Send file to user
            embed = discord.Embed(
                title="✅ Template Generated",
                description=f"Generated template with {num_packs} example pack(s)",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Next Steps",
                value="1. Download the file\n2. Edit pack and card details\n3. Run `/import_packs` to import",
                inline=False
            )
            
            await interaction.followup.send(
                embed=embed,
                file=discord.File(filepath),
                ephemeral=True
            )
            
            # Clean up
            import os as os_module
            if os_module.path.exists(filepath):
                os_module.remove(filepath)
            
        except Exception as e:
            print(f"❌ Error generating template: {e}")
            await interaction.followup.send(
                f"❌ **Error:** Failed to generate template\n```{str(e)}```",
                ephemeral=True
            )
    
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
        
        if len(pack['cards']) != 5:
            errors.append(f"{prefix}: Must have exactly 5 cards (has {len(pack['cards'])})")
        
        # Validate each card
        for j, card in enumerate(pack['cards']):
            card_errors = self._validate_card_data(card, index, j)
            errors.extend(card_errors)
        
        # Optional fields validation
        if 'creator_id' in pack and not isinstance(pack['creator_id'], int):
            errors.append(f"{prefix}: 'creator_id' must be an integer")
        
        if 'price_cents' in pack and not isinstance(pack['price_cents'], int):
            errors.append(f"{prefix}: 'price_cents' must be an integer")
        
        if 'pack_size' in pack and pack['pack_size'] != 5:
            errors.append(f"{prefix}: 'pack_size' must be 5 for this import")
        
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
        # Generate pack ID
        pack_id = str(uuid.uuid4())
        
        # Get creator ID (default to importer)
        creator_id = pack_data.get('creator_id', importer_user_id)
        
        # Get pack details
        name = pack_data['name']
        description = pack_data.get('description', f"Imported pack - {name}")
        pack_size = 5  # Fixed for this import
        price_cents = pack_data.get('price_cents', 699)
        
        # Create pack in LIVE status (skip payment for admin import)
        import sqlite3
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Initialize creator if not exists
            cursor.execute("""
                INSERT OR IGNORE INTO creator_pack_limits (creator_id)
                VALUES (?)
            """, (creator_id,))
            
            # Create pack with cards
            cards_json = json.dumps(pack_data['cards'])
            cursor.execute("""
                INSERT INTO creator_packs 
                (pack_id, creator_id, name, description, pack_size, status, cards_data, 
                 published_at, price_cents, stripe_payment_id)
                VALUES (?, ?, ?, ?, ?, 'LIVE', ?, CURRENT_TIMESTAMP, ?, 'ADMIN_IMPORT')
            """, (pack_id, creator_id, name, description, pack_size, cards_json, price_cents))
            
            # Add cards to master card list
            for card_data in pack_data['cards']:
                # Generate card ID if not provided
                if 'card_id' not in card_data:
                    card_data['card_id'] = str(uuid.uuid4())
                
                # Set pack_id
                card_data['pack_id'] = pack_id
                
                # Add to cards table
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
    await bot.add_cog(AdminBulkImportCog(bot))
