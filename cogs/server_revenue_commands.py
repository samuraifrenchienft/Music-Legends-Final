# cogs/server_revenue_commands.py
"""
Server Revenue Management Commands
For server owners to manage revenue sharing and NFT boosts
"""
import discord
from discord import app_commands, Interaction
from discord.ext import commands
import os

class ServerRevenueCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        from server_revenue import server_revenue
        from nft_verification import nft_verifier
        self.revenue = server_revenue
        self.nft_verifier = nft_verifier
    
    @app_commands.command(name="server_revenue", description="View your server's revenue status and earnings")
    async def server_revenue_status(self, interaction: Interaction):
        """View server revenue status"""
        
        # Check if user is server owner
        if interaction.guild.owner_id != interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the server owner can view revenue status!",
                ephemeral=True
            )
            return
        
        server_id = interaction.guild.id
        status = self.revenue.get_server_revenue_status(server_id)
        
        if not status:
            # Register server if not exists
            self.revenue.register_server_owner(
                server_id,
                interaction.user.id,
                str(interaction.user)
            )
            status = self.revenue.get_server_revenue_status(server_id)
        
        embed = discord.Embed(
            title="💰 Server Revenue Status",
            description=f"**{interaction.guild.name}**",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="📊 Revenue Share",
            value=f"**{status['revenue_share_display']}** of all pack sales in this server",
            inline=False
        )
        
        embed.add_field(
            name="🎨 NFT Boosts",
            value=f"**{status['nft_count']}** NFTs registered\n"
                  f"• Base: 10%\n"
                  f"• +10% per NFT (max 2)\n"
                  f"• Current: {status['revenue_share_display']}",
            inline=True
        )
        
        embed.add_field(
            name="💵 Earnings",
            value=f"**Total:** ${status['total_earned']:.2f}\n"
                  f"**Pending:** ${status['pending_payout']:.2f}\n"
                  f"**Transactions:** {status['total_transactions']}",
            inline=True
        )
        
        # Stripe Connect status
        stripe_status = "✅ Connected" if status['stripe_connected'] else "⚠️ Not Connected"
        embed.add_field(
            name="🔗 Stripe Connect",
            value=f"{stripe_status}\n"
                  f"Use `/connect_stripe` to set up automatic payouts",
            inline=False
        )
        
        # Get NFT list
        nfts = self.nft_verifier.get_server_nfts(server_id)
        if nfts:
            nft_list = "\n".join([f"• {nft['collection']} (Token #{nft['token_id'][:8]}...)" for nft in nfts[:2]])
            embed.add_field(
                name="🎴 Registered NFTs",
                value=nft_list,
                inline=False
            )
        else:
            embed.add_field(
                name="🎴 Registered NFTs",
                value="No NFTs registered yet\nUse `/register_nft` to add NFTs for +10% boost!",
                inline=False
            )
        
        embed.set_footer(text="Revenue Share • Season 1")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="register_nft", description="Register an NFT for +10% revenue boost")
    @app_commands.describe(
        wallet_address="Your Ethereum wallet address (0x...)",
        collection="NFT collection to verify"
    )
    @app_commands.choices(collection=[
        app_commands.Choice(name="Music Legends NFT", value="music_legends"),
        app_commands.Choice(name="Samurai Frenchie NFT", value="samurai_frenchie")
    ])
    async def register_nft(self, interaction: Interaction, wallet_address: str, collection: str):
        """Register an NFT for revenue boost"""
        
        # Check if user is server owner
        if interaction.guild.owner_id != interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the server owner can register NFTs!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Verify and register NFT
        result = await self.nft_verifier.register_nft_for_server(
            interaction.guild.id,
            interaction.user.id,
            wallet_address,
            collection
        )
        
        if result['success']:
            embed = discord.Embed(
                title="✅ NFT Registered!",
                description=f"Your {result['collection']} has been verified and registered!",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="💰 New Revenue Share",
                value=f"**{result['new_revenue_share']}** of all pack sales",
                inline=False
            )
            
            embed.add_field(
                name="🔍 Verification",
                value=f"• Wallet: `{wallet_address[:10]}...`\n"
                      f"• Method: {result.get('verification_method', 'blockchain')}\n"
                      f"• Boost: +10%",
                inline=False
            )
            
            embed.set_footer(text="You can register up to 2 NFTs for 30% total share")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="❌ NFT Verification Failed",
                description=result.get('error', 'Could not verify NFT ownership'),
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="💡 Tips",
                value="• Make sure wallet address is correct (starts with 0x)\n"
                      "• Ensure you own an NFT from the selected collection\n"
                      "• NFT must not be registered to another server",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="my_nfts", description="View your registered NFTs and boosts")
    async def view_nfts(self, interaction: Interaction):
        """View registered NFTs"""
        
        # Check if user is server owner
        if interaction.guild.owner_id != interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the server owner can view NFTs!",
                ephemeral=True
            )
            return
        
        nfts = self.nft_verifier.get_server_nfts(interaction.guild.id)
        
        embed = discord.Embed(
            title="🎴 Your Registered NFTs",
            description=f"NFTs registered for **{interaction.guild.name}**",
            color=discord.Color.purple()
        )
        
        if nfts:
            for i, nft in enumerate(nfts, 1):
                embed.add_field(
                    name=f"{i}. {nft['collection']}",
                    value=f"• Token ID: `{nft['token_id']}`\n"
                          f"• Wallet: `{nft['wallet_address'][:10]}...`\n"
                          f"• Boost: {nft['boost_value']}\n"
                          f"• Verified: {nft['verified_at'][:10]}",
                    inline=False
                )
            
            # Show total boost
            total_boost = min(len(nfts) * 10, 20)  # Max 20% from NFTs
            embed.add_field(
                name="💰 Total Revenue Share",
                value=f"**{10 + total_boost}%** (10% base + {total_boost}% NFT boost)",
                inline=False
            )
        else:
            embed.description = "No NFTs registered yet"
            embed.add_field(
                name="📝 How to Register",
                value="Use `/register_nft` with your wallet address to add NFTs!\n\n"
                      "**Accepted Collections:**\n"
                      "• Music Legends NFT (+10%)\n"
                      "• Samurai Frenchie NFT (+10%)\n\n"
                      "Max 2 NFTs = 30% total revenue share",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="connect_stripe", description="Connect Stripe for automatic payouts")
    async def connect_stripe(self, interaction: Interaction):
        """Connect Stripe account for payouts"""
        
        # Check if user is server owner
        if interaction.guild.owner_id != interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the server owner can connect Stripe!",
                ephemeral=True
            )
            return
        
        # This would create Stripe Connect onboarding link
        # For now, show placeholder
        embed = discord.Embed(
            title="🔗 Connect Stripe Account",
            description="Set up automatic payouts for your server revenue!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="💰 What You'll Earn",
            value="• 10-30% of all pack sales in your server\n"
                  "• Automatic weekly payouts\n"
                  "• Full transaction history",
            inline=False
        )
        
        embed.add_field(
            name="📋 Requirements",
            value="• Valid bank account\n"
                  "• Government ID for verification\n"
                  "• Business or personal account",
            inline=False
        )
        
        # In production, this would be a real Stripe Connect link
        connect_url = "https://connect.stripe.com/express/oauth/authorize?..."
        
        embed.add_field(
            name="🚀 Next Steps",
            value=f"[Click here to connect Stripe]({connect_url})\n\n"
                  f"After connecting, payouts will be automatic!",
            inline=False
        )
        
        embed.set_footer(text="Secure payment processing via Stripe")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ServerRevenueCommands(bot))
