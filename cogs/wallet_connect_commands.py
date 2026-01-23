# cogs/wallet_connect_commands.py
"""
Wallet Connect Commands - Exact UX Copy
NFT entitlement system with legal-safe messaging
"""
import discord
from discord import app_commands, Interaction, ui
from discord.ext import commands

# Legal-safe footer (use everywhere)
LEGAL_FOOTER = "NFT ownership provides revenue share boosts only.\nNFTs do not influence gameplay, odds, or card rarity."

class LearnMoreView(ui.View):
    """Learn More button view"""
    def __init__(self):
        super().__init__(timeout=300)
    
    @ui.button(label="🔗 Connect Wallet", style=discord.ButtonStyle.primary)
    async def connect_button(self, interaction: Interaction, button: ui.Button):
        # Start wallet connection flow
        await start_wallet_connection(interaction)
    
    @ui.button(label="❓ Learn More", style=discord.ButtonStyle.secondary)
    async def learn_more_button(self, interaction: Interaction, button: ui.Button):
        embed = discord.Embed(
            title="How Wallet Verification Works",
            description="• We verify NFT ownership using a read-only check\n"
                       "• We never access funds or request approvals\n"
                       "• Verification is snapshot-based, not live\n"
                       "• Revenue share updates automatically after verification\n\n"
                       "If you don't connect a wallet, your server still earns 10%.",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"You can disconnect your wallet at any time.\n\n{LEGAL_FOOTER}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class WalletSignatureModal(ui.Modal, title="Verify Wallet Ownership"):
    """Modal for wallet signature submission"""
    
    wallet_address = ui.TextInput(
        label="Wallet Address",
        placeholder="0x...",
        required=True,
        min_length=42,
        max_length=42
    )
    
    signature = ui.TextInput(
        label="Signature",
        placeholder="Paste your wallet signature here",
        required=True,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, nonce: str, message: str):
        super().__init__()
        self.nonce = nonce
        self.message = message
    
    async def on_submit(self, interaction: Interaction):
        from nft_entitlement import nft_entitlement
        
        await interaction.response.defer(ephemeral=True)
        
        # Link wallet
        result = nft_entitlement.link_wallet(
            interaction.user.id,
            self.wallet_address.value,
            self.signature.value,
            self.nonce
        )
        
        if result['success']:
            # Wallet verified - run snapshot
            snapshot_result = await nft_entitlement.snapshot_nft_ownership(interaction.user.id)
            
            # Show appropriate result embed
            if snapshot_result['success']:
                nft_count = snapshot_result['total_nfts']
                
                if nft_count == 0:
                    # Case A: No NFTs Found
                    embed = discord.Embed(
                        title="Wallet Linked — Base Revenue Share Active",
                        description="No eligible NFTs were detected in this wallet.\n\n"
                                   "**Your server earns:**\n10% revenue share",
                        color=discord.Color.blue()
                    )
                    embed.add_field(
                        name="💡 Tip",
                        value="You can add NFTs later to increase your share.",
                        inline=False
                    )
                elif nft_count == 1:
                    # Case B: 1 NFT Found (but boosts disabled, so still 10%)
                    embed = discord.Embed(
                        title="Wallet Linked — NFT Detected 🎉",
                        description="1 eligible NFT detected.\n\n"
                                   "**Your server earns:**\n10% revenue share\n\n"
                                   "⚠️ **NFT boosts coming soon!**\n"
                                   "When enabled, this will increase to 20%.",
                        color=discord.Color.gold()
                    )
                else:
                    # Case C: 2+ NFTs Found (but boosts disabled, so still 10%)
                    embed = discord.Embed(
                        title="Wallet Linked — Multiple NFTs Detected 🚀",
                        description=f"{nft_count} eligible NFTs detected.\n\n"
                                   "**Your server earns:**\n10% revenue share\n\n"
                                   "⚠️ **NFT boosts coming soon!**\n"
                                   "When enabled, this will increase to 30% (maximum).",
                        color=discord.Color.gold()
                    )
                    embed.add_field(
                        name="ℹ️ Note",
                        value="Additional NFTs won't increase the percentage further (30% cap).",
                        inline=False
                    )
            else:
                # Verification scheduled
                embed = discord.Embed(
                    title="Verification Scheduled",
                    description="Your wallet is linked, but verification is pending.\n\n"
                               "Revenue share will update automatically before your next payout.",
                    color=discord.Color.blue()
                )
            
            embed.set_footer(text=LEGAL_FOOTER)
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            # Verification failed
            embed = discord.Embed(
                title="Verification Failed",
                description="We couldn't verify this wallet right now.\n\n"
                           "This may be due to:\n"
                           "• Temporary network issues\n"
                           "• Wallet signature mismatch\n\n"
                           "Please try again later.",
                color=discord.Color.red()
            )
            embed.set_footer(text=LEGAL_FOOTER)
            await interaction.followup.send(embed=embed, ephemeral=True)

async def start_wallet_connection(interaction: Interaction):
    """Start the wallet connection flow"""
    from nft_entitlement import nft_entitlement
    
    # Generate nonce
    nonce = nft_entitlement.generate_nonce()
    message = nft_entitlement.create_signature_message(interaction.user.id, nonce)
    
    # Show signing instructions
    embed = discord.Embed(
        title="Verify Wallet Ownership",
        description="To verify ownership, you'll be asked to sign a message with your wallet.\n\n"
                   "**This does not create a transaction and costs no gas.**",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="📝 Message to Sign",
        value=f"```\n{message}\n```",
        inline=False
    )
    
    embed.add_field(
        name="🛠️ How to Sign",
        value="**Option 1: MetaMask**\n"
              "Settings → Advanced → Sign Message\n\n"
              "**Option 2: Etherscan**\n"
              "etherscan.io/verifiedSignatures\n\n"
              "**Option 3: MyEtherWallet**\n"
              "myetherwallet.com/wallet/sign",
        inline=False
    )
    
    embed.set_footer(text=f"Click the button below after signing.\n\n{LEGAL_FOOTER}")
    
    # Create button to open modal
    view = ui.View()
    button = ui.Button(label="✍️ Submit Signature", style=discord.ButtonStyle.primary)
    
    async def button_callback(button_interaction: Interaction):
        modal = WalletSignatureModal(nonce, message)
        await button_interaction.response.send_modal(modal)
    
    button.callback = button_callback
    view.add_item(button)
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class DisconnectConfirmView(ui.View):
    """Confirmation view for wallet disconnect"""
    def __init__(self):
        super().__init__(timeout=60)
    
    @ui.button(label="🔌 Disconnect", style=discord.ButtonStyle.danger)
    async def disconnect_button(self, interaction: Interaction, button: ui.Button):
        from nft_entitlement import nft_entitlement
        
        # Disconnect wallet
        with nft_entitlement.db_path as db_path:
            import sqlite3
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE wallet_links
                    SET status = 'disconnected'
                    WHERE discord_user_id = ?
                """, (interaction.user.id,))
                
                cursor.execute("""
                    UPDATE entitlement_cache
                    SET eligible_nfts = 0,
                        revenue_share_percent = 0.10,
                        verification_status = 'disconnected'
                    WHERE discord_user_id = ?
                """, (interaction.user.id,))
                
                conn.commit()
        
        embed = discord.Embed(
            title="✅ Wallet Disconnected",
            description="Your wallet has been disconnected.\n\n"
                       "Revenue share reset to 10% (base rate).\n\n"
                       "You can reconnect at any time with `/connect_wallet`.",
            color=discord.Color.green()
        )
        embed.set_footer(text=LEGAL_FOOTER)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message("Cancelled. Wallet remains connected.", ephemeral=True)

class WalletConnectCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="connect_wallet", description="Link a wallet to unlock revenue share boosts")
    async def connect_wallet(self, interaction: Interaction):
        """Connect wallet - Entry point"""
        
        # Check if user is server owner
        if interaction.guild.owner_id != interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the server owner can connect a wallet!",
                ephemeral=True
            )
            return
        
        # Show intro embed
        embed = discord.Embed(
            title="Connect Wallet for Revenue Share Boosts",
            description="Linking a wallet lets us verify ownership of Music Legends or Samurai Frenchie NFTs.\n\n"
                       "NFT ownership can increase your server's revenue share from 10% up to 30%.\n\n"
                       "**Important:**\n"
                       "• NFTs do not affect gameplay\n"
                       "• NFTs do not affect pack odds\n"
                       "• This is optional — all servers earn at least 10%",
            color=discord.Color.gold()
        )
        
        embed.set_footer(text=LEGAL_FOOTER)
        
        view = LearnMoreView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="disconnect_wallet", description="Disconnect your linked wallet")
    async def disconnect_wallet(self, interaction: Interaction):
        """Disconnect wallet"""
        
        # Check if user is server owner
        if interaction.guild.owner_id != interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the server owner can disconnect the wallet!",
                ephemeral=True
            )
            return
        
        # Show confirmation
        embed = discord.Embed(
            title="Disconnect Wallet?",
            description="Disconnecting your wallet will:\n"
                       "• Remove NFT-based boosts\n"
                       "• Reset revenue share to 10%\n\n"
                       "You can reconnect at any time.",
            color=discord.Color.orange()
        )
        embed.set_footer(text=LEGAL_FOOTER)
        
        view = DisconnectConfirmView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(WalletConnectCommands(bot))
