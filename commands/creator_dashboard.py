# commands/creator_dashboard.py
# NOTE: This is a template/scaffold file — not loaded as a cog in main.py
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
try:
    from services.creator_service import create_creator_pack
except ImportError:
    create_creator_pack = None
try:
    from services.creator_preview import build_preview
except ImportError:
    build_preview = None
try:
    from models.creator_pack import CreatorPack
except ImportError:
    CreatorPack = None

# ---------- MODAL FOR NEW PACK ----------

class CreatePackModal(Modal, title="Create Creator Pack"):

    artist_name = TextInput(label="Artist Name", max_length=100, placeholder="Enter artist name (e.g. Drake)")

    async def on_submit(self, interaction: discord.Interaction):
        # Artist name becomes the pack name
        pack_name = self.artist_name.value
        artist_list = [self.artist_name.value.strip()]

        pack = create_creator_pack(
            interaction.user.id,
            pack_name,
            artist_list,
            "Music"  # Default genre
        )

        await interaction.response.send_message(
            f"Pack **{pack_name}** submitted for review.",
            ephemeral=True
        )


# ---------- DASHBOARD VIEW ----------

class DashboardView(View):

    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id

    @discord.ui.button(label="Create New Pack", style=discord.ButtonStyle.primary)
    async def create(self, interaction, button):
        await interaction.response.send_modal(CreatePackModal())

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary)
    async def refresh(self, interaction, button):
        await interaction.response.edit_message(
            embed=dashboard_embed(self.user_id),
            view=self
        )


def dashboard_embed(user_id):

    packs = CreatorPack.where(owner_id=user_id)

    e = discord.Embed(title="Your Creator Packs")

    for p in packs:
        icon = {
            "pending": "🟡",
            "approved": "🟢",
            "rejected": "🔴"
        }.get(p.status, "⚪")

        e.add_field(
            name=f"{icon} {p.name}",
            value=f"{p.genre} – {p.status}",
            inline=False
        )

    return e


# ---------- COMMAND ----------

# To register as a command, load this as a cog or call from an existing cog:
# await interaction.response.send_message(
#     embed=dashboard_embed(interaction.user.id),
#     view=DashboardView(interaction.user.id)
# )
