# Example: Integrating Rate Limiting into Dev Panel

```python
# In cogs/menu_system.py, add to imports:

from cogs.rate_limiting_system import (
    rate_limited, 
    rate_limiter,
    get_rate_limit_status
)
from cogs.security_event_logger import log_suspicious_activity
```

## Integration Points

### 1. Pack Creation with Rate Limiting

```python
@app_commands.command(name="create_community_pack")
@rate_limited("pack_create")
async def create_community_pack_cmd(self, interaction: Interaction):
    """Create a community pack (rate limited - 5 per hour)"""
    
    try:
        await interaction.response.defer(ephemeral=False)
        
        # Show pack creation mode view
        view = PackCreationModeView(
            interaction=interaction,
            pack_type="community",
            db_manager=self.db_manager
        )
        
        embed = discord.Embed(
            title="📦 Create Community Pack",
            description="Choose pack creation mode:",
            color=discord.Color.blue()
        )
        
        await interaction.followup.send(embed=embed, view=view)
    
    except Exception as e:
        await interaction.followup.send(
            f"❌ Error: {str(e)}",
            ephemeral=True
        )
```

### 2. Purchase with Rate Limiting

```python
@app_commands.command(name="purchase_pack")
@rate_limited("pack_purchase")
async def purchase_pack_cmd(self, interaction: Interaction, pack_id: str):
    """Purchase a pack (rate limited - 10 per day)"""
    
    await interaction.response.defer(ephemeral=False)
    
    try:
        # Check if user already purchased this pack today
        # (Additional business logic)
        
        # Process purchase
        await self.process_pack_purchase(
            user_id=interaction.user.id,
            pack_id=pack_id
        )
        
        await interaction.followup.send(
            "✅ Pack purchased successfully!"
        )
    
    except Exception as e:
        await interaction.followup.send(
            f"❌ Purchase failed: {str(e)}",
            ephemeral=True
        )
```

### 3. Admin Rate Limit Bypass

```python
@app_commands.command(name="dev_create_pack")
async def dev_create_pack(self, interaction: Interaction, artist_name: str):
    """Developer/Admin pack creation (no rate limit)"""
    
    # Check authorization
    if not await self.is_dev_authorized(interaction.user.id):
        await interaction.response.send_message(
            "❌ Unauthorized",
            ephemeral=True
        )
        return
    
    await interaction.response.defer(ephemeral=False)
    
    try:
        # Create pack without rate limit check
        pack = await self._create_pack_internal(
            artist_name=artist_name,
            user_id=interaction.user.id,
            is_admin=True
        )
        
        await interaction.followup.send(
            f"✅ Admin pack created: {pack.id}"
        )
    
    except Exception as e:
        await interaction.followup.send(
            f"❌ Error: {str(e)}",
            ephemeral=True
        )
```

### 4. Rate Limit Status Command

```python
@app_commands.command(name="my_rate_limits")
async def show_rate_limits(self, interaction: Interaction):
    """Show your current rate limit status"""
    
    await interaction.response.defer(ephemeral=True)
    
    status = get_rate_limit_status(interaction.user.id)
    
    embed = discord.Embed(
        title="⏱️ Your Rate Limit Status",
        description=f"Abuse Score: {status['abuse_score']:.1f} / 100.0",
        color=discord.Color.blue()
    )
    
    # Add field for each action
    for action, limits in status['limits'].items():
        remaining = limits['remaining']
        max_requests = limits['max_requests']
        
        # Color code based on remaining
        if remaining == 0:
            emoji = "🔴"
        elif remaining < max_requests // 3:
            emoji = "🟡"
        else:
            emoji = "🟢"
        
        embed.add_field(
            name=f"{emoji} {action}",
            value=(
                f"{remaining} / {max_requests} remaining\n"
                f"Resets in {limits['window_seconds']} seconds"
            ),
            inline=False
        )
    
    if status['violations'] > 0:
        embed.add_field(
            name="⚠️  Violations",
            value=f"{status['violations']} in history",
            inline=False
        )
    
    await interaction.followup.send(embed=embed)
```

### 5. Manual Rate Limit Check

```python
async def create_gold_button_with_check(self, interaction: Interaction):
    """Create gold pack with explicit rate limit check"""
    
    # Manual check instead of decorator
    user_id = interaction.user.id
    allowed, state = rate_limiter.check_rate_limit(user_id, "pack_create")
    
    if not allowed:
        # Get remaining time
        remaining_time = 60  # Placeholder
        
        embed = discord.Embed(
            title="❌ Rate Limited",
            description=(
                f"You've created too many packs recently.\n"
                f"Try again in **{remaining_time} seconds**."
            ),
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )
        return
    
    # Proceed with normal flow
    await interaction.response.send_message(
        "Creating gold pack...",
        ephemeral=True
    )
```

## Database Integration

### 1. Store Rate Limit State

```python
# Optional: Persist rate limits to database for recovery

async def save_rate_limit_state(db_manager, user_id: int):
    """Save rate limit state to database"""
    
    status = get_rate_limit_status(user_id)
    
    query = """
    UPDATE users 
    SET rate_limit_state = $1, last_rate_limit_check = NOW()
    WHERE user_id = $2
    """
    
    await db_manager.execute(
        query,
        json.dumps(status),
        user_id
    )

async def restore_rate_limit_state(db_manager, user_id: int):
    """Restore rate limit state from database"""
    
    query = """
    SELECT rate_limit_state 
    FROM users 
    WHERE user_id = $1
    """
    
    result = await db_manager.fetchval(query, user_id)
    
    if result:
        state = json.loads(result)
        # Apply state to rate_limiter if needed
        return state
```

### 2. Track Long-term Abuse

```python
async def log_abuse_incident(db_manager, user_id: int):
    """Log abuse incident for long-term tracking"""
    
    score = rate_limiter.get_abuse_score(user_id)
    violations = len(rate_limiter.get_violation_history(user_id))
    
    query = """
    INSERT INTO abuse_log (user_id, abuse_score, violations, logged_at)
    VALUES ($1, $2, $3, NOW())
    """
    
    await db_manager.execute(query, user_id, score, violations)
    
    # Alert if score critical
    if score > 150:
        await alert_admins(f"🚨 User {user_id} has critical abuse score: {score}")
```

## Monitoring Commands

### 1. Admin Rate Limit Monitoring

```python
@app_commands.command(name="rate_limit_report")
@dev_only()
async def rate_limit_report(self, interaction: Interaction):
    """Show rate limiting statistics (admin only)"""
    
    await interaction.response.defer(ephemeral=True)
    
    # Collect statistics
    total_users = len(rate_limiter.abuse_scores)
    high_abuse = sum(
        1 for score in rate_limiter.abuse_scores.values()
        if score > 50
    )
    blocked_users = sum(
        1 for score in rate_limiter.abuse_scores.values()
        if score > 100
    )
    
    total_violations = sum(
        len(v) for v in rate_limiter.violation_history.values()
    )
    
    embed = discord.Embed(
        title="📊 Rate Limiting Report",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="Total Users Tracked", value=str(total_users))
    embed.add_field(name="High Abuse (50+)", value=str(high_abuse))
    embed.add_field(name="Blocked Users (100+)", value=str(blocked_users))
    embed.add_field(name="Total Violations", value=str(total_violations))
    
    await interaction.followup.send(embed=embed)
```

### 2. Reset Rate Limit

```python
@app_commands.command(name="reset_user_rate_limit")
@dev_only()
async def reset_user_rate_limit(
    self,
    interaction: Interaction,
    user_id: int
):
    """Reset rate limit for a user (admin only)"""
    
    rate_limiter.reset_abuse_score(user_id)
    
    await interaction.response.send_message(
        f"✅ Reset rate limit for user {user_id}",
        ephemeral=True
    )
```

## Testing Rate Limiting

```python
# test_rate_limiting.py

import asyncio
from cogs.rate_limiting_system import rate_limiter, RateLimitStrategy

async def test_rate_limiting():
    """Test rate limiting functionality"""
    
    user_id = 123456789
    action = "pack_create"
    
    print("🧪 Testing Rate Limiting System")
    print("=" * 50)
    
    # Test 1: Token Bucket
    print("\n1️⃣ Token Bucket Test")
    for i in range(6):
        allowed, state = rate_limiter.check_rate_limit(user_id, action)
        print(f"   Request {i+1}: {'✅ ALLOWED' if allowed else '❌ BLOCKED'}")
    
    # Test 2: Abuse Score
    print("\n2️⃣ Abuse Score Test")
    print(f"   Current Score: {rate_limiter.get_abuse_score(user_id)}")
    print(f"   Violations: {len(rate_limiter.get_violation_history(user_id))}")
    
    # Test 3: Reset
    print("\n3️⃣ Reset Test")
    rate_limiter.reset_abuse_score(user_id)
    print(f"   Score after reset: {rate_limiter.get_abuse_score(user_id)}")
    
    print("\n" + "=" * 50)
    print("✅ Rate Limiting Tests Complete")

if __name__ == "__main__":
    asyncio.run(test_rate_limiting())
```

## Performance Considerations

1. **Redis vs In-Memory**
   - Redis: Shared across multiple bot instances
   - In-Memory: Faster, but per-instance only

2. **Abuse Score Decay**
   - Consider implementing score decay over time
   - Users shouldn't be permanently penalized

3. **Escalating Limits**
   - Premium users might have higher limits
   - VIP status could bypass certain limits

4. **Monitoring**
   - Regular reports on abuse patterns
   - Alert on sudden spikes in violations
