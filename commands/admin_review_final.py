# commands/admin_review.py
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
from discord import Embed, ButtonStyle
from services.creator_moderation import review_pack
from services.creator_preview import build_preview
from models.creator_pack import CreatorPack

class ReviewView(View):

    def __init__(self, pack_id):
        super().__init__(timeout=180)
        self.pack_id = pack_id

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success)
    async def approve(self, interaction, button):

        review_pack(self.pack_id, interaction.user.id, True)

        await interaction.response.send_message(
            "Pack approved and captured.",
            ephemeral=True
        )

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject(self, interaction, button):

        review_pack(self.pack_id, interaction.user.id, False, "Rejected")

        await interaction.response.send_message(
            "Pack rejected and voided.",
            ephemeral=True
        )


@bot.slash_command(name="review")
@discord.default_permissions(manage_guild=True)
async def review(ctx, pack_id: str):

    data = build_preview(pack_id)

    e = discord.Embed(title=f"Review – {data['name']}")
    e.add_field(name="Genre", value=data["genre"])
    e.add_field(name="Payment", value=data["payment"])

    for a in data["artists"]:
        e.add_field(
            name=a["name"],
            value=f"{a['genre']} – {a['estimated_tier']}",
            inline=False
        )

    await ctx.respond(embed=e, view=ReviewView(pack_id))
