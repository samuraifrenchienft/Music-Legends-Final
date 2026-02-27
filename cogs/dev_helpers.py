# -*- coding: utf-8 -*-
"""
Dev Helpers - Shared functions for dev-only commands
Provides consistent TEST_SERVER_ID checking across all dev commands
"""

from discord import Interaction

from ..config import settings


def check_test_server(interaction: Interaction) -> bool:
    """
    Check if command is being used in test server and dev channel (TEST_SERVER_ID, DEV_CHANNEL_ID)
    Used with @app_commands.check decorator
    """
    test_server_id = settings.TEST_SERVER_ID
    if not test_server_id:
        return False
    
    try:
        test_guild_id = int(test_server_id)
        if interaction.guild_id != test_guild_id:
            return False
    except (ValueError, TypeError):
        return False
    
    # Check dev channel if configured
    dev_channel_id = settings.DEV_CHANNEL_ID
    if dev_channel_id:
        try:
            dev_channel_int = int(dev_channel_id)
            return interaction.channel_id == dev_channel_int
        except ValueError:
            return False
    
    return True


async def check_and_respond(interaction: Interaction) -> bool:
    """
    Check test server and dev channel, send custom error message if needed
    Use this inside command functions (not as decorator)
    Returns True if in dev server/channel, False otherwise
    """
    test_server_id = settings.TEST_SERVER_ID
    if not test_server_id:
        try:
            await interaction.response.send_message(
                "❌ Dev commands are not configured on this bot. `TEST_SERVER_ID` is not set.",
                ephemeral=True
            )
        except:
            pass
        return False
    
    try:
        test_guild_id = int(test_server_id)
    except ValueError:
        try:
            await interaction.response.send_message(
                "❌ `TEST_SERVER_ID` in environment variables is not a valid integer.",
                ephemeral=True
            )
        except:
            pass
        return False

    if interaction.guild_id != test_guild_id:
        try:
            await interaction.response.send_message(
                "❌ This command is only available in the development server.",
                ephemeral=True
            )
        except:
            pass
        return False
    
    # Check dev channel if configured
    dev_channel_id = settings.DEV_CHANNEL_ID
    if dev_channel_id:
        try:
            dev_channel_int = int(dev_channel_id)
            if interaction.channel_id != dev_channel_int:
                try:
                    await interaction.response.send_message(
                        "❌ This command is only available in the designated dev channel.",
                        ephemeral=True
                    )
                except:
                    pass
                return False
        except ValueError:
            print(f"⚠️  WARNING: DEV_CHANNEL_ID is not a valid integer: {dev_channel_id}")
    
    return True
