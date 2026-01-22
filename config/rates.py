# config/rates.py

# Rate limiting configuration for Discord commands
RATES = {
    "drop":  {"limit": 1,  "window": 1800},   # 30 min
    "grab":  {"limit": 5,  "window": 10},     # 10 sec
    "pack":  {"limit": 10, "window": 60},     # 1 min
    "trade": {"limit": 20, "window": 60},     # 1 min
    "founder_pack": {"limit": 5, "window": 60},  # 1 min
    "daily_reward": {"limit": 1, "window": 86400},  # 24 hours
}
