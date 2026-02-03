# RATE LIMITING SYSTEM INTEGRATION GUIDE

## Overview

The `cogs/rate_limiting_system.py` module provides an enterprise-grade rate limiting and abuse prevention system with:

- ✅ Multiple rate limiting strategies (Token Bucket, Sliding Window, Fixed Window)
- ✅ Redis support with automatic in-memory fallback
- ✅ Adaptive rate limiting based on violation history
- ✅ Comprehensive abuse detection and scoring
- ✅ Cascading limits across related actions
- ✅ Security event logging and alerting
- ✅ Easy decorator-based integration

## Quick Start

### 1. Basic Usage - Protect a Command

```python
from discord.ext import commands
from cogs.rate_limiting_system import rate_limited

@app_commands.command(name="create_pack")
@rate_limited("pack_create")
async def create_pack(interaction: Interaction):
    """Create a new card pack (rate limited)"""
    await interaction.response.send_message("Creating pack...")
    # Pack creation logic here
```

### 2. Check Rate Limit Manually

```python
from cogs.rate_limiting_system import rate_limiter

# In your command or handler
user_id = interaction.user.id
allowed, state = rate_limiter.check_rate_limit(user_id, "pack_create")

if not allowed:
    await interaction.response.send_message(
        f"❌ Rate limit exceeded for pack creation",
        ephemeral=True
    )
    return

# Proceed with action
```

### 3. Get User's Rate Limit Status

```python
from cogs.rate_limiting_system import get_rate_limit_status

status = get_rate_limit_status(user_id)
print(f"Abuse Score: {status['abuse_score']}")
print(f"Violations: {status['violations']}")
print(f"Pack Create Remaining: {status['limits']['pack_create']['remaining']}")
```

## Strategies Explained

### Token Bucket Algorithm
- **Best for:** API calls, general rate limiting
- **How it works:** Tokens refill at a constant rate, requests consume tokens
- **Advantage:** Allows burst traffic, smooth rate limiting
- **Use case:** YouTube API calls, Discord API interactions

```python
RateLimitConfig(
    action='api_call',
    max_requests=100,
    window_seconds=60,
    strategy=RateLimitStrategy.TOKEN_BUCKET
)
```

### Sliding Window Algorithm
- **Best for:** Purchase limits, transactions
- **How it works:** Tracks exact timestamps of all requests in window
- **Advantage:** Most accurate, prevents burst abuse
- **Use case:** Pack purchases, payment processing

```python
RateLimitConfig(
    action='pack_purchase',
    max_requests=10,
    window_seconds=86400,
    strategy=RateLimitStrategy.SLIDING_WINDOW
)
```

### Fixed Window Algorithm
- **Best for:** Login attempts, security-sensitive actions
- **How it works:** Counter resets at fixed time intervals
- **Advantage:** Simple, low memory, obvious reset time
- **Use case:** Failed login attempts, account lockout

```python
RateLimitConfig(
    action='failed_login',
    max_requests=5,
    window_seconds=900,
    strategy=RateLimitStrategy.FIXED_WINDOW
)
```

## Pre-configured Actions

| Action | Max | Window | Strategy |
|--------|-----|--------|----------|
| `pack_create` | 5 | 3600s (1h) | Token Bucket |
| `pack_purchase` | 10 | 86400s (24h) | Sliding Window |
| `payment` | 5 | 3600s (1h) | Token Bucket |
| `api_call` | 100 | 60s (1m) | Token Bucket |
| `login_attempt` | 10 | 900s (15m) | Fixed Window |
| `failed_login` | 5 | 900s (15m) | Fixed Window |

## Advanced Configuration

### Register Custom Rate Limits

```python
from cogs.rate_limiting_system import rate_limiter, RateLimitConfig, RateLimitStrategy

# Add custom limit
rate_limiter.register_limit(
    RateLimitConfig(
        action='tournament_join',
        max_requests=3,
        window_seconds=7200,  # 3 joins per 2 hours
        strategy=RateLimitStrategy.SLIDING_WINDOW,
        enable_adaptive=True,
        enable_cascading=True
    )
)
```

### Adaptive Rate Limiting

When enabled, repeat violations increase the abuse score more aggressively:

```python
config = RateLimitConfig(
    action='pack_create',
    max_requests=5,
    window_seconds=3600,
    enable_adaptive=True  # Score increases exponentially with violations
)
```

## Abuse Scoring System

Each violation increases a user's abuse score:

| Situation | Score Increase |
|-----------|-----------------|
| First violation | +10 |
| With recent violations | +10 × (1 + recent_count × 0.5) |
| High score exceeded | Auto-block |

**Threshold:** 100.0 (automatic blocking)
**Reset:** Manual reset or after period of no violations

```python
# Get abuse score
score = rate_limiter.get_abuse_score(user_id)

# Reset if appropriate
rate_limiter.reset_abuse_score(user_id)
```

## Violation History

Track when and what actions were rate limited:

```python
# Get violation history
violations = rate_limiter.get_violation_history(user_id)

for violation in violations:
    print(f"{violation['timestamp']}: {violation['action']}")
```

## Security Integration

All rate limit violations are automatically logged:

```
🚨 [SECURITY] RATE_LIMIT_EXCEEDED_PACK_CREATE
   User: 123456789
   Abuse Score: 45.0
   Recent Violations: 3
```

High abuse scores trigger suspicious activity alerts:

```
🚨 [SUSPICIOUS] EXCESSIVE_PACK_CREATE_ATTEMPTS
   User: 123456789
   Violations: 15
   Abuse Score: 150.0
```

## Discord Bot Integration Example

```python
# In your cogs/commands.py

import discord
from discord.ext import commands
from cogs.rate_limiting_system import rate_limited, get_rate_limit_status

class PackCreation(commands.Cog):
    """Pack creation commands with rate limiting"""
    
    @app_commands.command(name="create_pack")
    @rate_limited("pack_create")
    async def create_pack(self, interaction: discord.Interaction):
        """Create a new card pack"""
        
        # Rate limit already checked by decorator
        await interaction.response.defer()
        
        try:
            # Pack creation logic
            pack = await self.create_pack_data(interaction.user.id)
            
            await interaction.followup.send(
                f"✅ Pack created successfully!\n"
                f"Pack ID: `{pack.id}`"
            )
        
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error creating pack: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="rate_status")
    async def rate_status(self, interaction: discord.Interaction):
        """Check your rate limit status"""
        
        status = get_rate_limit_status(interaction.user.id)
        
        embed = discord.Embed(
            title="⏱️ Your Rate Limits",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Abuse Score",
            value=f"{status['abuse_score']:.1f} / 100",
            inline=False
        )
        
        embed.add_field(
            name="Violations",
            value=str(status['violations']),
            inline=False
        )
        
        for action, limit in status['limits'].items():
            embed.add_field(
                name=action,
                value=f"{limit['remaining']} / {limit['max_requests']} remaining",
                inline=True
            )
        
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )
    
    async def create_pack_data(self, user_id: int):
        # Simulated pack creation
        return type('Pack', (), {'id': f'pack_{user_id}_{int(time.time())}'})()

async def setup(bot):
    await bot.add_cog(PackCreation(bot))
```

## Redis Configuration

### Environment Variables

```bash
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Fallback Behavior

If Redis is unavailable:
1. System logs a warning
2. Switches to in-memory storage
3. Continues operating normally
4. Rate limits remain enforced

```python
# Automatically detects Redis availability
rate_limiter = AdvancedRateLimiter(redis_client, enable_redis=True)

# If Redis fails during operation
# -> Automatically falls back to in-memory storage
# -> No service interruption
```

## Monitoring & Analytics

### View Abuse Trends

```python
def get_abuse_report(hours: int = 24) -> Dict:
    """Generate abuse report"""
    report = {
        "period_hours": hours,
        "high_abuse_users": [],
        "total_violations": 0,
        "actions_limited": {}
    }
    
    # Analyze abuse scores and violations
    for user_id, score in rate_limiter.abuse_scores.items():
        if score > 50:  # Threshold for concern
            report['high_abuse_users'].append({
                "user_id": user_id,
                "score": score,
                "violations": len(rate_limiter.get_violation_history(user_id))
            })
        
        report['total_violations'] += len(
            rate_limiter.get_violation_history(user_id)
        )
    
    return report
```

### Create Alerts

```python
async def check_abuse_alerts(bot: discord.Client):
    """Check for abuse patterns and alert admins"""
    
    alert_channel = bot.get_channel(ALERTS_CHANNEL_ID)
    
    for user_id, score in rate_limiter.abuse_scores.items():
        if score > 100:  # Critical threshold
            embed = discord.Embed(
                title="🚨 Critical Abuse Score",
                color=discord.Color.red()
            )
            embed.add_field(
                name="User",
                value=f"<@{user_id}>",
                inline=False
            )
            embed.add_field(
                name="Abuse Score",
                value=f"{score:.1f}",
                inline=False
            )
            embed.add_field(
                name="Violations",
                value=len(rate_limiter.get_violation_history(user_id)),
                inline=False
            )
            
            await alert_channel.send(embed=embed)
```

## Best Practices

1. **Use Decorators for Simplicity**
   ```python
   @rate_limited("pack_create")
   async def create_pack(interaction):
       pass
   ```

2. **Check Before Expensive Operations**
   ```python
   # Check first, then do expensive work
   allowed, _ = rate_limiter.check_rate_limit(user_id, "pack_create")
   if not allowed:
       return  # Don't waste resources
   
   # Expensive operation here
   ```

3. **Provide Helpful Messages**
   ```python
   if not allowed:
       await interaction.response.send_message(
           f"❌ Rate limited\n"
           f"Try again in {remaining} seconds",
           ephemeral=True
       )
   ```

4. **Monitor Abuse Trends**
   ```python
   # Regular monitoring
   report = get_abuse_report(hours=24)
   print(f"High abuse users: {len(report['high_abuse_users'])}")
   ```

5. **Balance Strictness**
   - Too strict → User frustration
   - Too lenient → Abuse risk
   - Use adaptive limits for balance

## Troubleshooting

### Redis Connection Issues

```python
# Check if using Redis
if rate_limiter.use_redis:
    print("✅ Using Redis")
else:
    print("⚠️  Using in-memory storage (Redis unavailable)")
```

### Rate Limit Not Working

```python
# Verify configuration exists
if "my_action" not in rate_limiter.configs:
    print("❌ Action not configured!")
    
    # Register it
    from cogs.rate_limiting_system import rate_limiter, RateLimitConfig
    rate_limiter.register_limit(
        RateLimitConfig(
            action="my_action",
            max_requests=5,
            window_seconds=3600
        )
    )
```

### High Abuse Scores

```python
# Check violation history
violations = rate_limiter.get_violation_history(user_id)
print(f"User has {len(violations)} violations")

# If false positive, reset
rate_limiter.reset_abuse_score(user_id)
```

## Security Considerations

1. **Abuse Score Persistence** - Consider persisting to database for long-term tracking
2. **Coordinated Attacks** - Monitor for patterns across multiple users
3. **Rate Limit Timing** - Ensure clients can see remaining time
4. **Graceful Degradation** - System works without Redis
5. **Privacy** - Don't expose exact rate limit values to users

