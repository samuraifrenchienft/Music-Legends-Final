# decorators/rate_guard.py
from middleware.rate_limiter import RateLimiter
from config.rates import RATES

def rate_guard(action):
    """
    Discord rate limiting decorator for commands
    
    Usage:
        @rate_guard("pack")
        async def buy_pack(ctx, pack_type):
            # Command logic here
            pass
    """
    
    def wrapper(func):
        
        async def inner(ctx, *args, **kwargs):
            # Create rate limiter for this user and action
            key = f"{action}:{ctx.author.id}"
            rule = RATES[action]
            
            limiter = RateLimiter(
                key,
                rule["limit"],
                rule["window"]
            )
            
            # Check if request is allowed
            if not limiter.allow():
                # Get status for informative message
                status = limiter.get_status()
                await ctx.send(
                    f"⏰ **Rate Limit Exceeded**\n"
                    f"You can use this command **{status['remaining']}** more time(s) "
                    f"in the next **{rule['window']}** seconds.\n"
                    f"Limit: **{status['current']}/{status['limit']}**"
                )
                return
            
            # Execute the original function
            return await func(ctx, *args, **kwargs)
        
        return inner
    
    return wrapper

# Example usage
if __name__ == "__main__":
    # This would be used in your Discord bot cogs
    pass
