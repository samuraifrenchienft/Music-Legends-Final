# commands/creator_dashboard.py
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from services.creator_service import create_creator_pack
from services.creator_preview import build_preview
from models.creator_pack import CreatorPack

# ---------- MODAL FOR NEW PACK ----------

class CreatePackModal(Modal, title="Create Creator Pack"):

    name = TextInput(label="Pack Name", max_length=40)
    genre = TextInput(label="Genre", max_length=20)
    artists = TextInput(
        label="Artists (comma separated)",
        style=discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):

        artist_list = [a.strip() for a in self.artists.value.split(",")]

        pack = create_creator_pack(
            interaction.user.id,
            self.name.value,
            artist_list,
            self.genre.value
        )

        await interaction.response.send_message(
            f"Pack **{pack.name}** submitted for review.",
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

@bot.slash_command(name="creator")
async def creator(ctx):

    await ctx.respond(
        embed=dashboard_embed(ctx.author.id),
        view=DashboardView(ctx.author.id)
    )
