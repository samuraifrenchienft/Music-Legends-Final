"""
Purchase Commands

Discord slash commands for pack purchases.
Integrates with Stripe checkout for payment processing.
"""

import discord
from discord import app_commands, Interaction
from discord.ext import commands
import logging

from services.checkout import create_pack_checkout, get_pack_pricing, list_available_packs, format_pack_description

# Configure logging
logger = logging.getLogger(__name__)

class PurchaseCommands(commands.Cog):
    """Commands for purchasing packs through Stripe checkout."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="buypack", description="Purchase a pack through secure checkout")
    @app_commands.describe(pack="The pack type you want to purchase")
    async def buypack(self, interaction: Interaction, pack: str):
        """
        Purchase a pack through Stripe checkout.
        
        Args:
            interaction: Discord interaction
            pack: Pack type to purchase
        """
        try:
            # Validate pack type
            available_packs = list_available_packs()
            if pack not in available_packs:
                await interaction.response.send_message(
                    f"❌ Invalid pack type: `{pack}`\n\n"
                    f"Available packs: {', '.join(f'`{p}`' for p in available_packs)}",
                    ephemeral=True
                )
                return
            
            # Get pack information
            pricing = get_pack_pricing()
            pack_info = pricing[pack]
            
            # Create checkout session
            checkout_url = create_pack_checkout(
                user_id=interaction.user.id,
                pack=pack,
                success_url=f"https://your.site/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"https://your.site/cancel?user_id={interaction.user.id}"
            )
            
            # Create embed
            embed = discord.Embed(
                title=f"🛒 Purchase {pack_info['name']}",
                description=f"Complete your purchase through our secure checkout.",
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name="Pack Details",
                value=f"**Type:** {pack_info['name']}\n**Price:** ${pack_info['price_usd']:.2f}",
                inline=False
            )
            
            embed.add_field(
                name="🔗 Checkout Link",
                value=f"[Click here to complete purchase]({checkout_url})",
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Important",
                value="• This link is valid for 24 hours\n• Cards will be delivered after payment completion\n• Save your receipt for support",
                inline=False
            )
            
            embed.set_footer(text="Secure payment powered by Stripe")
            
            # Send embed with button
            view = PurchaseView(checkout_url)
            
            await interaction.response.send_message(
                embed=embed,
                view=view,
                ephemeral=True  # Only visible to purchaser
            )
            
            logger.info(f"Checkout created for user {interaction.user.id}, pack {pack}")
            
        except Exception as e:
            logger.error(f"Failed to create checkout for user {interaction.user.id}, pack {pack}: {e}")
            await interaction.response.send_message(
                "❌ Failed to create checkout session. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="packs", description="List available packs and pricing")
    async def packs(self, interaction: Interaction):
        """List all available packs with pricing."""
        try:
            pricing = get_pack_pricing()
            
            embed = discord.Embed(
                title="📦 Available Packs",
                description="Browse our collection of digital card packs",
                color=discord.Color.blue()
            )
            
            # Add each pack as a field
            for pack_type, info in pricing.items():
                embed.add_field(
                    name=f"{info['name']} - ${info['price_usd']:.2f}",
                    value=f"Use `/buypack {pack_type}` to purchase",
                    inline=True
                )
            
            embed.add_field(
                name="🛒 How to Purchase",
                value="1. Use `/buypack <pack>` to get checkout link\n"
                     "2. Complete payment through Stripe\n"
                     "3. Cards delivered automatically",
                inline=False
            )
            
            embed.set_footer(text="All purchases are final and non-refundable")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Failed to list packs: {e}")
            await interaction.response.send_message(
                "❌ Failed to load pack information. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="purchase_status", description="Check your recent purchase status")
    @app_commands.describe(session_id="Stripe checkout session ID (optional)")
    async def purchase_status(self, interaction: Interaction, session_id: str = None):
        """
        Check the status of a recent purchase.
        
        Args:
            interaction: Discord interaction
            session_id: Optional Stripe session ID to check
        """
        try:
            if session_id:
                # Check specific session
                from services.checkout import get_checkout_session
                
                try:
                    session = get_checkout_session(session_id)
                    
                    embed = discord.Embed(
                        title="📋 Purchase Status",
                        color=discord.Color.green()
                    )
                    
                    status = session.get("status", "unknown")
                    payment_status = session.get("payment_status", "unknown")
                    
                    embed.add_field(
                        name="Session Details",
                        value=f"**ID:** {session_id}\n"
                             f"**Status:** {status}\n"
                             f"**Payment:** {payment_status}",
                        inline=False
                    )
                    
                    if status == "complete" and payment_status == "paid":
                        embed.color = discord.Color.green()
                        embed.description = "✅ Purchase completed successfully!"
                    elif status == "expired":
                        embed.color = discord.Color.orange()
                        embed.description = "⏰ Checkout session expired"
                    else:
                        embed.color = discord.Color.red()
                        embed.description = "❌ Purchase not completed"
                    
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    
                except Exception as e:
                    logger.error(f"Failed to retrieve session {session_id}: {e}")
                    await interaction.response.send_message(
                        f"❌ Could not find session `{session_id}`",
                        ephemeral=True
                    )
            else:
                # Show general purchase information
                embed = discord.Embed(
                    title="📋 Purchase Information",
                    description="To check a specific purchase, provide the session ID from your checkout link.",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="🔍 How to Find Session ID",
                    value="Your checkout URL looks like:\n"
                         "`https://checkout.stripe.com/pay/cs_test_a1B2c3D4e5F6g7H8i9J0`\n"
                         "The session ID is the part after `/pay/`",
                    inline=False
                )
                
                embed.add_field(
                    name="📧 Support",
                    value="If you have issues with a purchase, contact support with your session ID.",
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Failed to check purchase status: {e}")
            await interaction.response.send_message(
                "❌ Failed to check purchase status. Please try again later.",
                ephemeral=True
            )

class PurchaseView(discord.ui.View):
    """View with purchase button and information."""
    
    def __init__(self, checkout_url: str):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.checkout_url = checkout_url
    
    @discord.ui.button(label="🛒 Complete Purchase", style=discord.ButtonStyle.primary, url=checkout_url)
    async def purchase_button(self, interaction: Interaction, button: discord.ui.Button):
        """Handle purchase button click."""
        # Button opens URL, no action needed
        await interaction.response.send_message(
            "🛒 Opening secure checkout in your browser...",
            ephemeral=True
        )
    
    @discord.ui.button(label="❓ Help", style=discord.ButtonStyle.secondary)
    async def help_button(self, interaction: Interaction, button: discord.ui.Button):
        """Handle help button click."""
        embed = discord.Embed(
            title="🛒 Purchase Help",
            description="Need help with your purchase?",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🔧 Common Issues",
            value="• **Payment declined**: Check with your bank\n"
                 "• **Link expired**: Use `/buypack` again\n"
                 "• **No cards delivered**: Wait a few minutes, then contact support",
            inline=False
        )
        
        embed.add_field(
            name="📧 Contact Support",
            value="If you continue having issues, please contact support with your session ID.",
            inline=False
        )
        
        embed.set_footer(text="All purchases are processed securely through Stripe")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Setup function
async def setup(bot: commands.Bot):
    """Setup purchase commands."""
    await bot.add_cog(PurchaseCommands(bot))
    logger.info("Purchase commands loaded")

# Error handling
class PurchaseCommandError(Exception):
    """Custom exception for purchase command errors."""
    pass

class InvalidPackError(PurchaseCommandError):
    """Exception for invalid pack types."""
    pass

class CheckoutCreationError(PurchaseCommandError):
    """Exception for checkout creation failures."""
    pass

# Utility functions

def format_pack_list() -> str:
    """Format pack list for display."""
    pricing = get_pack_pricing()
    
    lines = []
    for pack_type, info in pricing.items():
        lines.append(f"• **{info['name']}** - ${info['price_usd']:.2f}")
    
    return "\n".join(lines)

def validate_pack_type(pack: str) -> bool:
    """Validate pack type."""
    return pack in list_available_packs()

def get_pack_info(pack: str) -> dict:
    """Get pack information."""
    pricing = get_pack_pricing()
    return pricing.get(pack, {})

# Logging helpers

def log_purchase_initiated(user_id: int, pack: str, session_id: str):
    """Log purchase initiation."""
    logger.info(f"Purchase initiated: user {user_id}, pack {pack}, session {session_id}")

def log_purchase_completed(user_id: int, pack: str, session_id: str, amount: int):
    """Log successful purchase."""
    logger.info(f"Purchase completed: user {user_id}, pack {pack}, session {session_id}, amount ${amount/100:.2f}")

def log_purchase_failed(user_id: int, pack: str, error: str):
    """Log purchase failure."""
    logger.error(f"Purchase failed: user {user_id}, pack {pack}, error {error}")
