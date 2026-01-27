"""
Song selection view for pack creation
"""
import discord
from discord import ui, Interaction
from typing import List, Dict, Callable

class SongSelectionView(ui.View):
    """Interactive view for selecting songs for pack creation"""
    
    def __init__(self, tracks: List[Dict], max_selections: int = 10, callback: Callable = None):
        super().__init__(timeout=300)  # 5 minute timeout
        self.tracks = tracks
        self.max_selections = max_selections
        self.selected_tracks = []
        self.callback = callback
        
        # Add song selection dropdown
        self.add_item(SongSelectMenu(tracks, max_selections))
        
    async def on_timeout(self):
        """Handle view timeout"""
        for item in self.children:
            item.disabled = True

class SongSelectMenu(ui.Select):
    """Dropdown menu for selecting songs"""
    
    def __init__(self, tracks: List[Dict], max_selections: int):
        # Create options from tracks
        options = []
        for i, track in enumerate(tracks[:25]):  # Discord limit is 25 options
            # YouTube videos use 'title', not 'name'
            track_name = track.get('title', track.get('name', 'Unknown Song'))[:90]
            
            options.append(
                discord.SelectOption(
                    label=track_name,
                    description=f"{track.get('channel_title', track.get('artist_name', 'Unknown'))}"[:100],
                    value=str(i),
                    emoji="🎵"
                )
            )
        
        super().__init__(
            placeholder=f"Select up to {max_selections} songs for your pack...",
            min_values=1,
            max_values=min(max_selections, len(options)),
            options=options
        )
        
        self.tracks = tracks
        self.max_selections = max_selections
    
    async def callback(self, interaction: Interaction):
        """Handle song selection"""
        # Get selected tracks
        selected_indices = [int(val) for val in self.values]
        selected_tracks = [self.tracks[i] for i in selected_indices]
        
        # Store in view
        self.view.selected_tracks = selected_tracks
        
        # Create confirmation embed
        embed = discord.Embed(
            title="🎵 Songs Selected",
            description=f"You've selected **{len(selected_tracks)}** songs for your pack:",
            color=discord.Color.blue()
        )
        
        # List selected songs
        song_list = ""
        for i, track in enumerate(selected_tracks, 1):
            track_title = track.get('title', track.get('name', 'Unknown Song'))
            song_list += f"{i}. **{track_title}**\n"
        
        embed.add_field(name="Selected Songs", value=song_list, inline=False)
        embed.set_footer(text="Click 'Confirm Selection' to create your pack")
        
        # Add confirm button
        self.view.clear_items()
        self.view.add_item(ConfirmButton(selected_tracks, self.view.callback))
        self.view.add_item(CancelButton())
        
        await interaction.response.edit_message(embed=embed, view=self.view)

class ConfirmButton(ui.Button):
    """Confirm song selection button"""
    
    def __init__(self, selected_tracks: List[Dict], callback: Callable):
        super().__init__(
            label="Confirm Selection",
            style=discord.ButtonStyle.success,
            emoji="✅"
        )
        self.selected_tracks = selected_tracks
        self.pack_callback = callback
    
    async def callback(self, interaction: Interaction):
        """Handle confirmation"""
        # Defer the response immediately to prevent timeout
        await interaction.response.defer()
        
        # Disable all buttons
        for item in self.view.children:
            item.disabled = True
        
        await interaction.edit_original_response(view=self.view)
        
        # Call the pack creation callback
        if self.pack_callback:
            await self.pack_callback(interaction, self.selected_tracks)

class CancelButton(ui.Button):
    """Cancel selection button"""
    
    def __init__(self):
        super().__init__(
            label="Cancel",
            style=discord.ButtonStyle.danger,
            emoji="❌"
        )
    
    async def callback(self, interaction: Interaction):
        """Handle cancellation"""
        embed = discord.Embed(
            title="❌ Pack Creation Cancelled",
            description="You can start over with `/create_pack` anytime.",
            color=discord.Color.red()
        )
        
        # Disable all buttons
        for item in self.view.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self.view)
