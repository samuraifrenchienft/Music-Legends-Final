# Changelog Manager - System Change Tracking

## Overview

The ChangeLogManager is a comprehensive system for tracking, logging, and alerting on significant system changes within Music Legends. It provides:

- **Audit Trail**: Complete history of pack creation, card generation, and user actions
- **Discord Alerts**: Real-time notifications in dev channels for critical events
- **Severity Levels**: Categorized alerts based on importance (critical, high, medium, low)
- **Statistical Analysis**: Track patterns and trends in system activity
- **Filtering & Search**: Query changes by category, user, severity, and time period

## Architecture

### Components

1. **ChangeLogManager** (`services/changelog_manager.py`)
   - Core logging and retrieval logic
   - Discord alert integration
   - Change filtering and statistics

2. **ChangelogCommandsCog** (`cogs/changelog_commands.py`)
   - Discord commands for viewing changelog
   - Admin/dev access control
   - Statistics display

3. **JSON Change Log** (`logs/change_log.json`)
   - Persistent storage of all changes
   - One entry per line for easy streaming
   - Timestamp-based queries

## Usage

### Basic Logging

```python
from services.changelog_manager import get_changelog_manager

manager = get_changelog_manager()

# Log a pack creation
manager.log_change(
    category='pack_creation',
    description='Created pack: Drake (Community)',
    user_id=12345,
    severity='high',
    metadata={'pack_id': 'pack_123', 'artist': 'Drake'},
    send_alert=True
)
```

### Convenience Functions

```python
from services.changelog_manager import (
    log_pack_creation,
    log_card_generation,
    log_user_action,
    log_system_event,
    log_error
)

# Log pack creation
log_pack_creation(
    pack_id='pack_123',
    artist_name='Drake',
    creator_id=12345,
    pack_type='community'
)

# Log card generation
log_card_generation(
    pack_id='pack_123',
    card_count=5,
    creator_id=12345
)

# Log user action
log_user_action(
    action='opened_pack',
    user_id=12345,
    details={'pack_id': 'pack_123', 'cards_received': 5}
)

# Log system event
log_system_event(
    event_type='database_migration',
    description='Migrated card database',
    severity='high',
    metadata={'tables': 5, 'records': 10000}
)

# Log error
log_error(
    error_type='YouTube API Error',
    error_message='Rate limit exceeded',
    severity='high',
    metadata={'retry_after': 3600}
)
```

## Categories

| Category | Usage |
|----------|-------|
| `pack_creation` | New pack created |
| `card_generation` | Cards generated for pack |
| `user_action` | Player actions (open pack, battle, etc.) |
| `system_event` | System maintenance, migrations, etc. |
| `error` | System errors and exceptions |
| `security` | Security events, unauthorized access attempts |
| `payment` | Payment processing and transactions |
| `admin_action` | Admin commands executed |
| `deployment` | Bot deployments and updates |
| `database` | Database operations and migrations |

## Severity Levels

| Level | Emoji | Usage |
|-------|-------|-------|
| `critical` | 🔴 | System failures, security breaches |
| `high` | 🟠 | Major changes, pack creation, errors |
| `medium` | 🟡 | Moderate changes, normal operations |
| `low` | ⚪ | Minor changes, informational |

## Discord Commands

### View Changelog

```
/changelog [category] [limit]
```

Shows recent system changes with optional filtering.

**Parameters:**
- `category` (optional): Filter by category (e.g., pack_creation)
- `limit` (optional): Number of entries to show (1-50, default 10)

**Example:**
```
/changelog category:pack_creation limit:20
```

### View Statistics

```
/changelog_stats
```

Shows changelog statistics including:
- Total entries logged
- Changes by category
- Changes by severity
- Date range of entries

## Alert Channel Detection

Alerts are automatically sent to the first matching channel:
- `dev-logs`
- `dev-channel`
- `admin-logs`
- `admin-channel`
- `system-logs`
- `changelog`

### Setting Up Alert Channel

1. Create a channel named `dev-logs` or similar in your Discord server
2. Give the bot permission to send messages in that channel
3. Alerts will automatically post there when `send_alert=True`

## Discord Alert Format

Each alert includes:

```
🟠 System Change Alert

[Description of change]

Category: Pack Creation
Severity: 🟠 HIGH
User ID: 12345

Metadata:
• pack_id: pack_123
• artist: Drake
• type: community
```

## Log File Format

The changelog is stored as JSONL (JSON Lines) format:

```json
{"timestamp": "2026-02-03T10:30:45.123456", "category": "pack_creation", "category_name": "Pack Creation", "description": "Created pack: Drake (Community)", "user_id": 12345, "severity": "high", "severity_emoji": "🟠", "metadata": {"pack_id": "pack_123", "artist": "Drake", "type": "community"}}
{"timestamp": "2026-02-03T10:31:20.654321", "category": "card_generation", "category_name": "Card Generation", "description": "Generated 5 cards for pack", "user_id": 12345, "severity": "high", "severity_emoji": "🟠", "metadata": {"pack_id": "pack_123", "card_count": 5}}
```

## Example Integration

### In Pack Creation

```python
from services.changelog_manager import log_pack_creation

async def create_pack(artist_name, creator_id):
    # ... pack creation logic ...
    
    log_pack_creation(
        pack_id='pack_' + str(uuid.uuid4()),
        artist_name=artist_name,
        creator_id=creator_id,
        pack_type='community'
    )
```

### In Error Handling

```python
from services.changelog_manager import log_error

try:
    # ... risky operation ...
except Exception as e:
    log_error(
        error_type=type(e).__name__,
        error_message=str(e),
        severity='high',
        metadata={'traceback': traceback.format_exc()}
    )
```

## Maintenance

### Clear Old Entries

Remove entries older than 90 days:

```python
manager = get_changelog_manager()
removed = manager.clear_old_entries(days=90)
print(f"Removed {removed} old entries")
```

### Get Statistics

```python
stats = manager.get_stats()
print(f"Total changes: {stats['total']}")
print(f"By category: {stats['by_category']}")
print(f"By severity: {stats['by_severity']}")
```

### Query Changes

```python
# Get all pack creation changes
changes = manager.get_changes(
    category='pack_creation',
    limit=100
)

# Get changes by specific user
changes = manager.get_changes(
    user_id=12345,
    limit=50
)

# Get critical changes
changes = manager.get_changes(
    severity='critical',
    limit=50
)
```

## Performance Considerations

- **File Size**: Each entry averages 300-500 bytes
- **Monthly Growth**: ~15-30MB per month (high activity)
- **Query Time**: O(n) - scans entire file
- **Cleanup**: Run `clear_old_entries()` monthly to maintain performance

### Recommendations

- Clear entries older than 90 days monthly
- Use `/changelog_stats` to monitor log growth
- Set up alerts only for `critical` and `high` severity
- Archive logs quarterly for long-term storage

## Security

- All user IDs and metadata are logged (no PII filtering)
- Ensure `logs/` directory has proper permissions (not world-readable)
- Consider encrypting log file in production
- Restrict `/changelog` command to admins/devs only (future enhancement)

## Future Enhancements

- [ ] Log rotation by date or size
- [ ] Role-based access control for `/changelog` commands
- [ ] Webhook alerts to external systems
- [ ] JSON export for analysis tools
- [ ] Log encryption
- [ ] Advanced filtering (date range, regex patterns)
- [ ] Real-time streaming to monitoring systems
