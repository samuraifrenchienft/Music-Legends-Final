# cogs/nft_entitlement_commands.py
"""
NFT Entitlement Commands - Snapshot-Based Revenue Boost
Server owners link wallets and verify NFT ownership for revenue boosts
"""
import discord
from discord import app_commands, Interaction
from discord.ext import commands
from discord import ui

class WalletLinkModal(ui.Modal, title="Link Your Wallet"):
    """Modal for wallet linking with signature"""
    
    wallet_address = ui.TextInput(
        label="Ethereum Wallet Address",
        placeholder="0x...",
        required=True,
        min_length=42,
        max_length=42
    )
    
    signature = ui.TextInput(
        label="Signature",
        placeholder="Sign the message with your wallet",
        required=True,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, nonce: str, message: str):
        super().__init__()
        self.nonce = nonce
        self.message = message
    
    async def on_submit(self, interaction: Interaction):
        from nft_entitlement import nft_entitlement
        
        # Link wallet
        result = nft_entitlement.link_wallet(
            interaction.user.id,
            self.wallet_address.value,
            self.signature.value,
            self.nonce
        )
        
        if result['success']:
            embed = discord.Embed(
                title="✅ Wallet Linked Successfully!",
                description=f"Your wallet has been verified and linked.",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="📍 Wallet Address",
                value=f"`{result['wallet_address']}`",
                inline=False
            )
            
            embed.add_field(
                name="📊 Current Revenue Share",
                value="**10%** (base rate)\n\nNFT snapshot will run within 24 hours to check for boosts!",
                inline=False
            )
            
            embed.add_field(
                name="🔄 Next Steps",
                value="• Wait for automatic snapshot (24h)\n• Or use `/refresh_snapshot` to verify NFTs now\n• Check status with `/server_revenue`",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="❌ Wallet Linking Failed",
                description=result.get('error', 'Unknown error'),
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="💡 Common Issues",
                value="• Signature doesn't match wallet address\n• Wallet already linked to another account\n• Invalid signature format",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

class NFTEntitlementCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        from nft_entitlement import nft_entitlement
        from server_revenue import server_revenue
        self.entitlement = nft_entitlement
        self.revenue = server_revenue
    
    @app_commands.command(name="connect_wallet", description="Link your wallet to unlock NFT revenue boosts")
    async def connect_wallet(self, interaction: Interaction):
        """Start wallet linking process"""
        
        # Check if user is server owner
        if interaction.guild.owner_id != interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the server owner can link a wallet!",
                ephemeral=True
            )
            return
        
        # Generate nonce
        nonce = self.entitlement.generate_nonce()
        message = self.entitlement.create_signature_message(interaction.user.id, nonce)
        
        # Create instruction embed
        embed = discord.Embed(
            title="🔗 Link Your Wallet",
            description="Sign a message with your wallet to prove ownership.\n\n**This is FREE and requires NO gas fees.**",
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
                  "1. Copy the message above\n"
                  "2. Go to MetaMask → Settings → Advanced → Sign Message\n"
                  "3. Paste message and sign\n\n"
                  "**Option 2: Etherscan**\n"
                  "1. Go to etherscan.io/verifiedSignatures\n"
                  "2. Paste message and sign with your wallet\n\n"
                  "**Option 3: MyEtherWallet**\n"
                  "1. Go to myetherwallet.com/wallet/sign\n"
                  "2. Connect wallet and sign message",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ Important",
            value="• This is a signature, NOT a transaction\n"
                  "• No gas fees required\n"
                  "• No approvals or permissions granted\n"
                  "• Only proves you own the wallet",
            inline=False
        )
        
        embed.set_footer(text="Click the button below after signing")
        
        # Create button to open modal
        view = ui.View()
        button = ui.Button(label="Submit Signature", style=discord.ButtonStyle.primary)
        
        async def button_callback(button_interaction: Interaction):
            modal = WalletLinkModal(nonce, message)
            await button_interaction.response.send_modal(modal)
        
        button.callback = button_callback
        view.add_item(button)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="refresh_snapshot", description="Manually refresh your NFT snapshot")
    async def refresh_snapshot(self, interaction: Interaction):
        """Manually trigger NFT snapshot verification"""
        
        # Check if user is server owner
        if interaction.guild.owner_id != interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the server owner can refresh snapshots!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Run snapshot
        result = await self.entitlement.snapshot_nft_ownership(interaction.user.id)
        
        if result['success']:
            embed = discord.Embed(
                title="✅ NFT Snapshot Complete!",
                description="Your NFT ownership has been verified on-chain.",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="🎴 NFTs Found",
                value=f"**Total:** {result['total_nfts']} NFTs\n**Counted:** {result['eligible_nfts']} NFTs (max 2)",
                inline=True
            )
            
            embed.add_field(
                name="💰 Revenue Share",
                value=f"**{result['revenue_share_percent'] * 100:.0f}%**",
                inline=True
            )
            
            # Show breakdown
            if result['snapshots']:
                nft_list = "\n".join([
                    f"• {self.entitlement.ACCEPTED_COLLECTIONS[s['collection_key']]['name']}: {s['nft_count']} NFTs"
                    for s in result['snapshots']
                ])
                embed.add_field(
                    name="📊 Breakdown",
                    value=nft_list,
                    inline=False
                )
            else:
                embed.add_field(
                    name="📊 Breakdown",
                    value="No eligible NFTs found\nRevenue share: 10% (base rate)",
                    inline=False
                )
            
            embed.add_field(
                name="🔄 Next Refresh",
                value="Automatic refresh in 24 hours\nOr use this command again anytime",
                inline=False
            )
            
            embed.set_footer(text="Snapshot cached • Used for all purchases")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="❌ Snapshot Failed",
                description=result.get('error', 'Could not verify NFT ownership'),
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="💡 Troubleshooting",
                value="• Make sure you've linked your wallet with `/connect_wallet`\n"
                      "• Verify you own NFTs from accepted collections\n"
                      "• Check that your wallet address is correct",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="entitlement_status", description="Check your NFT entitlement status")
    async def entitlement_status(self, interaction: Interaction):
        """View current entitlement status"""
        
        # Check if user is server owner
        if interaction.guild.owner_id != interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the server owner can view entitlement status!",
                ephemeral=True
            )
            return
        
        # Get cached entitlement
        entitlement = self.entitlement.get_cached_entitlement(interaction.user.id)
        
        embed = discord.Embed(
            title="🎴 NFT Entitlement Status",
            description=f"**{interaction.guild.name}**",
            color=discord.Color.purple()
        )
        
        if not entitlement['has_entitlement']:
            embed.add_field(
                name="📊 Current Status",
                value="**No wallet linked**\n\nRevenue Share: 10% (base rate)",
                inline=False
            )
            
            embed.add_field(
                name="🚀 Get Started",
                value="Use `/connect_wallet` to link your wallet and unlock NFT boosts!",
                inline=False
            )
        else:
            # Show entitlement details
            status_icon = "✅" if not entitlement.get('frozen') and not entitlement.get('stale') else "⚠️"
            
            embed.add_field(
                name=f"{status_icon} Revenue Share",
                value=f"**{entitlement['revenue_share_percent'] * 100:.0f}%**",
                inline=True
            )
            
            embed.add_field(
                name="🎴 Eligible NFTs",
                value=f"**{entitlement['eligible_nfts']}** / 2 max",
                inline=True
            )
            
            # Last verified
            if 'last_verified' in entitlement:
                embed.add_field(
                    name="🕐 Last Verified",
                    value=entitlement['last_verified'][:10],
                    inline=True
                )
            
            # Warnings
            if entitlement.get('frozen'):
                embed.add_field(
                    name="⚠️ Frozen",
                    value=f"Reason: {entitlement.get('freeze_reason', 'Unknown')}\n"
                          f"Reverted to 10% base rate",
                    inline=False
                )
            elif entitlement.get('stale'):
                embed.add_field(
                    name="⚠️ Stale Verification",
                    value="Snapshot is older than 7 days\nUse `/refresh_snapshot` to update",
                    inline=False
                )
            
            # Breakdown
            embed.add_field(
                name="📊 Calculation",
                value=f"• Base: 10%\n"
                      f"• NFT Boost: +{entitlement['eligible_nfts'] * 10}% ({entitlement['eligible_nfts']} NFTs × 10%)\n"
                      f"• **Total: {entitlement['revenue_share_percent'] * 100:.0f}%**",
                inline=False
            )
        
        embed.add_field(
            name="ℹ️ How It Works",
            value="• NFTs are entitlement tokens (no gameplay impact)\n"
                  "• Snapshots run every 24 hours\n"
                  "• Max 2 NFTs counted (30% cap)\n"
                  "• Cached for instant purchase processing",
            inline=False
        )
        
        embed.set_footer(text="Entitlement Cache • Snapshot-Based")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(NFTEntitlementCommands(bot))
