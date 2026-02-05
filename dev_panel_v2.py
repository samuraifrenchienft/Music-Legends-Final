# dev_panel_v2.py
"""
Complete Rewrite of Dev Panel - Better Error Handling & Logging
Every button now has detailed error logging to debug issues
"""

import discord
from discord import Interaction, app_commands, ui
from discord.ext import commands
import traceback
import sqlite3
import os
from database import DatabaseManager
from datetime import datetime


def _is_dev_user(user_id: int) -> bool:
    """Check if user is an authorized dev"""
    dev_ids = os.getenv('DEV_USER_IDS', '').split(',')
    return str(user_id) in [uid.strip() for uid in dev_ids if uid.strip()]

class GiveCardsModal(discord.ui.Modal, title="Give Card"):
    """Modal for giving cards with detailed error handling"""
    
    def __init__(self, rarity: str, db: DatabaseManager):
        super().__init__()
        self.rarity = rarity
        self.db = db
        print(f"✅ [GiveCardsModal] Initialized with rarity: {rarity}")
    
    user_id = discord.ui.TextInput(
        label="User ID",
        placeholder="Enter user ID...",
        required=True,
        max_length=20
    )
    
    card_name = discord.ui.TextInput(
        label="Card Name",
        placeholder="Artist name...",
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: Interaction):
        print(f"\n{'='*60}")
        print(f"🔧 [GiveCardsModal.on_submit] STARTING")
        print(f"   User: {interaction.user.id}")
        print(f"   Rarity: {self.rarity}")
        print(f"   Card Name: {self.card_name.value}")
        print(f"{'='*60}\n")
        
        try:
            await interaction.response.defer(ephemeral=True)
            print(f"✅ [GiveCardsModal] Response deferred")
            
            # Parse user ID
            user_input = self.user_id.value.strip()
            print(f"📝 [GiveCardsModal] User input: {user_input}")
            
            target_id = int(user_input.replace('<@', '').replace('>', '').replace('!', ''))
            print(f"✅ [GiveCardsModal] Parsed target user ID: {target_id}")
            
            # Get or create user
            user = interaction.guild.get_member(target_id)
            if not user:
                await interaction.followup.send(f"❌ Could not find user with ID {target_id}", ephemeral=True)
                print(f"❌ [GiveCardsModal] User not found: {target_id}")
                return
            
            print(f"✅ [GiveCardsModal] Found user: {user.name} ({user.id})")
            
            # Get or create user in database
            print(f"🔄 [GiveCardsModal] Getting/creating user in database...")
            self.db.get_or_create_user(target_id, user.name, user.discriminator)
            print(f"✅ [GiveCardsModal] User in database")
            
            # Create card
            card_id = f"dev_gift_{interaction.user.id}_{target_id}_{self.card_name.value.lower().replace(' ', '_')}"
            print(f"📦 [GiveCardsModal] Creating card with ID: {card_id}")
            
            card_data = {
                'card_id': card_id,
                'name': self.card_name.value,
                'title': 'Dev Gift',
                'rarity': self.rarity,
                'impact': 50,
                'skill': 50,
                'longevity': 50,
                'culture': 50,
                'hype': 50,
            }
            
            # Add to database
            self.db.add_card_to_master(card_data)
            print(f"✅ [GiveCardsModal] Added card to master")
            
            self.db.add_card_to_collection(target_id, card_id, 'dev_gift')
            print(f"✅ [GiveCardsModal] Added card to user collection")
            
            # Send confirmation
            embed = discord.Embed(
                title="✅ Card Given",
                description=f"Gave **{self.rarity.upper()}** card to {user.mention}",
                color=discord.Color.green()
            )
            embed.add_field(name="Card Name", value=self.card_name.value, inline=False)
            embed.add_field(name="User", value=f"{user.name} ({target_id})", inline=False)
            embed.add_field(name="Rarity", value=self.rarity.upper(), inline=False)
            embed.add_field(name="Timestamp", value=datetime.now().isoformat(), inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            print(f"✅ [GiveCardsModal] Success - Card given!")
            
        except ValueError as e:
            print(f"❌ [GiveCardsModal] ValueError: {e}")
            traceback.print_exc()
            await interaction.followup.send(f"❌ Invalid user ID format: {e}", ephemeral=True)
        except Exception as e:
            print(f"❌ [GiveCardsModal] Exception: {e}")
            traceback.print_exc()
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


class GiveCardsView(discord.ui.View):
    """Rarity selection for giving cards"""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(timeout=180)
        self.db = db
        print(f"✅ [GiveCardsView] Initialized")
    
    @discord.ui.select(
        placeholder="Choose card rarity...",
        options=[
            discord.SelectOption(label="Common", value="common", emoji="⚪"),
            discord.SelectOption(label="Rare", value="rare", emoji="🔵"),
            discord.SelectOption(label="Epic", value="epic", emoji="🟣"),
            discord.SelectOption(label="Legendary", value="legendary", emoji="⭐"),
            discord.SelectOption(label="Mythic", value="mythic", emoji="🔴"),
        ],
    )
    async def rarity_select(self, interaction: Interaction, select: discord.ui.Select):
        print(f"\n{'='*60}")
        print(f"🔧 [GiveCardsView.rarity_select] STARTING")
        print(f"   Selected: {select.values[0]}")
        print(f"{'='*60}\n")
        
        try:
            rarity = select.values[0]
            print(f"✅ [GiveCardsView] Rarity selected: {rarity}")
            
            modal = GiveCardsModal(rarity, self.db)
            print(f"✅ [GiveCardsView] Modal created")
            
            await interaction.response.send_modal(modal)
            print(f"✅ [GiveCardsView] Modal shown to user")
            
        except Exception as e:
            print(f"❌ [GiveCardsView] Exception: {e}")
            traceback.print_exc()
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class AnnouncementModal(discord.ui.Modal, title="Send Announcement"):
    """Announcement modal with detailed logging"""
    
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        print(f"✅ [AnnouncementModal] Initialized")
    
    message = discord.ui.TextInput(
        label="Announcement Message",
        style=discord.TextStyle.paragraph,
        placeholder="Type your announcement...",
        required=True,
        max_length=2000
    )
    
    async def on_submit(self, interaction: Interaction):
        print(f"\n{'='*60}")
        print(f"🔧 [AnnouncementModal.on_submit] STARTING")
        print(f"   User: {interaction.user.id}")
        print(f"   Message length: {len(self.message.value)}")
        print(f"{'='*60}\n")
        
        try:
            await interaction.response.defer(ephemeral=True)
            print(f"✅ [AnnouncementModal] Response deferred")
            
            print(f"📝 [AnnouncementModal] Message: {self.message.value[:100]}...")
            
            # Create announcement embed
            embed = discord.Embed(
                title="📢 Announcement",
                description=self.message.value,
                color=discord.Color.gold()
            )
            embed.set_footer(text=f"From: {interaction.user.display_name} • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            print(f"✅ [AnnouncementModal] Embed created")
            
            # Send to current channel
            if interaction.channel:
                message = await interaction.channel.send(embed=embed)
                print(f"✅ [AnnouncementModal] Message sent to channel: {message.id}")
            else:
                print(f"❌ [AnnouncementModal] No channel found")
            
            # Confirm to user
            await interaction.followup.send("✅ Announcement sent!", ephemeral=True)
            print(f"✅ [AnnouncementModal] Confirmation sent to user")
            
        except Exception as e:
            print(f"❌ [AnnouncementModal] Exception: {e}")
            traceback.print_exc()
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


# Updated DevPanelView buttons with detailed logging

class DevPanelView(discord.ui.View):
    """Dev panel with enhanced error logging"""
    
    def __init__(self, db: DatabaseManager = None):
        super().__init__(timeout=None)
        self.db = db or DatabaseManager()
        print(f"✅ [DevPanelView] Initialized")
    
    @discord.ui.button(
        label="🎁 Give Cards",
        style=discord.ButtonStyle.secondary,
        custom_id="dev_panel:give_cards_v2",
        row=0
    )
    async def give_cards_button(self, interaction: Interaction, button: discord.ui.Button):
        """Give cards to users"""
        print(f"\n{'='*60}")
        print(f"🔧 [DevPanelView.give_cards_button] CLICKED")
        print(f"   User: {interaction.user.id}")
        print(f"   Guild: {interaction.guild_id}")
        print(f"{'='*60}\n")

        if not _is_dev_user(interaction.user.id):
            await interaction.response.send_message("❌ Unauthorized. Dev-only feature.", ephemeral=True)
            return

        try:
            print(f"✅ [DevPanelView] Creating GiveCardsView...")
            view = GiveCardsView(self.db)
            
            print(f"✅ [DevPanelView] Sending response...")
            await interaction.response.send_message(
                "🎁 **Give Cards to Users**\n\nSelect card rarity:",
                view=view,
                ephemeral=True
            )
            print(f"✅ [DevPanelView] Give Cards view sent successfully")
            
        except Exception as e:
            print(f"❌ [DevPanelView.give_cards_button] Exception: {e}")
            traceback.print_exc()
            try:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
            except:
                try:
                    await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
                except Exception as fe:
                    print(f"❌ [DevPanelView] Could not send error message: {fe}")
    
    @discord.ui.button(
        label="📢 Announcement",
        style=discord.ButtonStyle.primary,
        custom_id="dev_panel:announcement_v2",
        row=0
    )
    async def announcement_button(self, interaction: Interaction, button: discord.ui.Button):
        """Send announcement"""
        print(f"\n{'='*60}")
        print(f"🔧 [DevPanelView.announcement_button] CLICKED")
        print(f"   User: {interaction.user.id}")
        print(f"   Guild: {interaction.guild_id}")
        print(f"{'='*60}\n")

        if not _is_dev_user(interaction.user.id):
            await interaction.response.send_message("❌ Unauthorized. Dev-only feature.", ephemeral=True)
            return

        try:
            print(f"✅ [DevPanelView] Creating AnnouncementModal...")
            modal = AnnouncementModal(self.db)
            
            print(f"✅ [DevPanelView] Sending modal...")
            await interaction.response.send_modal(modal)
            print(f"✅ [DevPanelView] Announcement modal sent successfully")
            
        except Exception as e:
            print(f"❌ [DevPanelView.announcement_button] Exception: {e}")
            traceback.print_exc()
            try:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
            except:
                try:
                    await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
                except Exception as fe:
                    print(f"❌ [DevPanelView] Could not send error message: {fe}")
