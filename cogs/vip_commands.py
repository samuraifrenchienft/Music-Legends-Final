# cogs/vip_commands.py
"""VIP Membership commands - subscribe, manage, view benefits"""

import discord
from discord import app_commands, Interaction
from discord.ext import commands
from database import DatabaseManager, get_db
from config.vip import VIPSubscription, VIPManager


class VIPCommands(commands.Cog):
    """VIP Membership commands"""

    def __init__(self, bot):
        self.bot = bot
        self.db = get_db()

    @app_commands.command(name="buy_vip", description="Subscribe to VIP Membership ($4.99/month)")
    async def buy_vip_command(self, interaction: Interaction):
        """Subscribe to VIP membership with recurring billing"""
        await interaction.response.defer(ephemeral=True)

        try:
            from stripe_payments import stripe_manager

            # Create Stripe subscription checkout
            result = stripe_manager.create_vip_subscription_checkout(
                user_id=interaction.user.id,
                username=interaction.user.display_name
            )

            if result.get('success'):
                checkout_url = result['checkout_url']

                embed = discord.Embed(
                    title="👑 VIP Membership Subscription",
                    description=(
                        f"**${VIPSubscription.MONTHLY_PRICE_USD}/month** recurring\n\n"
                        "**Benefits Include:**\n"
                        "💰 2x Daily Gold\n"
                        "🎫 +1 Ticket Daily\n"
                        "⚔️ +50% Battle Gold & XP\n"
                        "🛡️ 50% Wager Protection\n"
                        "🏪 0% Marketplace Fees\n"
                        "✨ Exclusive Cosmetics\n"
                        "🎯 VIP-Only Tournaments\n\n"
                        "[Click here to subscribe](" + checkout_url + ")\n\n"
                        "Cancel anytime • Auto-renews monthly"
                    ),
                    color=discord.Color.gold()
                )
                embed.set_footer(text="Estimated value: $27/month | Cancel anytime")
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                error_msg = result.get('error', 'Unknown error')
                await interaction.followup.send(
                    f"❌ Failed to create subscription checkout: {error_msg}",
                    ephemeral=True
                )
        except Exception as e:
            print(f"Error creating VIP checkout: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(
                "❌ Failed to create VIP subscription checkout. Please try again later.",
                ephemeral=True
            )

    @app_commands.command(name="vip", description="View VIP membership benefits and status")
    async def vip_command(self, interaction: Interaction):
        """View VIP benefits and check your membership status"""
        from config.vip import is_user_vip, get_vip_manager

        is_vip = is_user_vip(interaction.user.id)

        if is_vip:
            # User is VIP - show their status
            embed = discord.Embed(
                title="👑 Your VIP Membership",
                description="You are currently a **VIP Member**!",
                color=discord.Color.gold()
            )

            # TODO: Get actual expiry date from database
            embed.add_field(
                name="Status",
                value="✅ Active",
                inline=True
            )
            embed.add_field(
                name="Renewal",
                value="Auto-renews monthly",
                inline=True
            )

            embed.add_field(
                name="💰 Active Benefits",
                value=(
                    "• 2x Daily Gold Rewards\n"
                    "• +1 Ticket Every Day\n"
                    "• +50% Battle Gold & XP\n"
                    "• 50% Wager Protection\n"
                    "• 0% Marketplace Fees\n"
                    "• Gold Username Color\n"
                    "• Exclusive Monthly Card Back\n"
                    "• VIP-Only Tournaments"
                ),
                inline=False
            )

            embed.set_footer(text="Use /cancel_vip to cancel your subscription")
        else:
            # User is not VIP - show benefits and subscribe option
            manager = get_vip_manager()
            benefits_text = manager.format_benefits_display()

            embed = discord.Embed(
                title="👑 VIP Membership",
                description=(
                    f"**${VIPSubscription.MONTHLY_PRICE_USD}/month** recurring subscription\n\n"
                    "Unlock exclusive benefits, bonuses, and cosmetics!"
                ),
                color=discord.Color.gold()
            )

            embed.add_field(
                name="💰 DAILY BONUSES",
                value=(
                    "• 2x Daily Gold (200g vs 100g)\n"
                    "• +1 Ticket Daily (30/month)\n"
                    "• 1 Free Gold Pack/Month\n"
                    "• +50% XP from Everything"
                ),
                inline=False
            )

            embed.add_field(
                name="⚔️ BATTLE BONUSES",
                value=(
                    "• +50% Gold from Battles\n"
                    "• 50% Wager Protection\n"
                    "• Win Streak Bonuses"
                ),
                inline=False
            )

            embed.add_field(
                name="🏪 MARKETPLACE",
                value=(
                    "• 0% Marketplace Fees\n"
                    "• 20 Trades/Day (vs 5)\n"
                    "• Priority Listings"
                ),
                inline=False
            )

            embed.add_field(
                name="✨ COSMETICS & EXCLUSIVE",
                value=(
                    "• Gold Username Color\n"
                    "• Exclusive Monthly Card Back\n"
                    "• 5 VIP Emotes\n"
                    "• VIP-Only Tournaments\n"
                    "• 24h Early Pack Access"
                ),
                inline=False
            )

            embed.add_field(
                name="💎 VALUE",
                value=(
                    f"**Estimated Value:** $27/month\n"
                    f"**Price:** ${VIPSubscription.MONTHLY_PRICE_USD}/month\n"
                    f"**Value Ratio:** 5.4x your money"
                ),
                inline=False
            )

            embed.set_footer(text="Use /buy_vip to subscribe • Cancel anytime")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="cancel_vip", description="Cancel your VIP subscription")
    async def cancel_vip_command(self, interaction: Interaction):
        """Cancel VIP subscription (access remains until end of billing period)"""
        from config.vip import is_user_vip

        if not is_user_vip(interaction.user.id):
            await interaction.response.send_message(
                "❌ You don't have an active VIP subscription.",
                ephemeral=True
            )
            return

        # TODO: Implement Stripe subscription cancellation
        embed = discord.Embed(
            title="Cancel VIP Subscription",
            description=(
                "To cancel your VIP subscription, please contact support at:\n"
                "**support@musiclegends.gg**\n\n"
                "Your VIP benefits will remain active until the end of your current billing period."
            ),
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(VIPCommands(bot))
