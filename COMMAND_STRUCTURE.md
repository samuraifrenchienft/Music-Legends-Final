# Music Legends Bot - Command Structure

## Command Categories

### 1. Player Commands (Public)
- `/start_game` - Initialize game in server
- `/deck` - View battle deck
- `/stats` - View player statistics
- `/daily` - Claim daily reward
- `/balance` - Check currency balance
- `/rank` - View player ranking

### 2. Collection Commands (Public)
- `/collection` - View card collection (NOTE: Currently loads from gameplay.py but may be missing)
- (Future: `/display_card`, `/collection_value`)

### 3. Economy Commands (Public)
- `/open_pack` - Open a card pack
- `/create_pack` - Create a new pack
- `/sell` - Sell card to marketplace
- `/buy` - Purchase card from marketplace
- `/packs` - Browse available packs

### 4. Battle Commands (Public)
- `/battle` - Challenge another player
- `/battle_accept` - Accept battle challenge

### 5. Cosmetics Commands (Public)
- `/cosmetic_shop` - Browse cosmetics
- `/purchase_cosmetic` - Buy cosmetic item
- `/customize_card` - Customize card appearance
- `/my_cosmetics` - View owned cosmetics

### 6. Season Commands (Public)
- `/season_info` - View current season
- `/season_progress` - Check progress
- `/season_rewards` - View rewards
- `/season_leaderboard` - Season rankings
- `/claim_reward` - Claim season reward

### 7. Dust Commands (Public)
- `/dust` - Check dust balance
- `/craft` - Craft specific card
- `/boost` - Boost card stats
- `/reroll` - Reroll card stats
- `/buy_pack_dust` - Purchase pack with dust
- `/dust_shop` - Dust shop items

### 8. Admin Commands (Restricted)
- `/setup_user_hub` - Post user hub
- `/sync_commands` - Sync commands
- `/delete_pack` - Delete pack
- `/server_analytics` - View analytics
- `/import_packs` - Import packs from JSON (TEST_SERVER only)

### 9. Dev-Only Commands (TEST_SERVER)
- `/setup_dev_panel` - Setup dev panel with buttons

## Current Issues
- **Missing**: `/collection` command (referenced but not in active commands)
- **Cleanup Done**: Removed `/changelog`, `/changelog_stats`, `/uptime`, `/restarts`, `/restart_stats`, `/performance`, `/errors`, `/error_stats`, `/system_health`

## Monitoring & Logging (No Commands)
- System monitor (restarts, uptime, resources) - tracked but not exposed
- Changelog logging - tracked but not exposed  
- Error logging - tracked but not exposed
- These feed data to dev dashboard/webhooks only

## Security
- Dev commands restricted to TEST_SERVER_ID
- Admin commands restricted to administrators
- All sensitive operations logged for audit trail
