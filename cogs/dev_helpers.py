# -*- coding: utf-8 -*-
"""
Dev Helpers - Shared functions for dev-only commands
Provides consistent TEST_SERVER_ID checking across all dev commands
"""

import os
from discord import Interaction


def check_test_server(interaction: Interaction) -> bool:
    """
    Check if command is being used in test server (TEST_SERVER_ID)
    Used with @app_commands.check decorator
    """
    test_server_id = os.getenv('TEST_SERVER_ID')
    if not test_server_id:
        return False
    
    try:
        test_guild_id = int(test_server_id)
        return interaction.guild_id == test_guild_id
    except (ValueError, TypeError):
        return False


async def check_and_respond(interaction: Interaction) -> bool:
    """
    Check test server and send custom error message if needed
    Use this inside command functions (not as decorator)
    Returns True if in dev server, False otherwise
    """
    test_server_id = os.getenv('TEST_SERVER_ID')
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
    return True
