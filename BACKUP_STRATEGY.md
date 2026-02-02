# Dual Backup Strategy Documentation

## Overview

The Music Legends Bot uses a **dual backup strategy** that combines:
1. **Railway's Automatic PostgreSQL Backups** (7-day retention)
2. **Custom Backup System** (configurable retention, multiple storage locations)

## Why Use Both?

### Railway PostgreSQL Backups
- ✅ Automatic daily backups for 7 days
- ✅ Easy one-click restore through Railway dashboard
- ✅ No setup required
- ✅ Perfect for quick recovery from recent issues
- ⚠️ Limited to 7-day retention

### Custom Backup System
- ✅ Longer retention periods (months/years)
- ✅ Multiple storage locations (local + cloud)
- ✅ Full control over backup timing
- ✅ Protection against Railway service issues
- ✅ Better for compliance/audit requirements
- ✅ Custom backup triggers (before restarts, after rare cards, etc.)

## How It Works

### Database Detection

The bot automatically detects which database you're using:

- **PostgreSQL**: When `DATABASE_URL` environment variable is set (Railway provides this automatically)
- **SQLite**: Falls back to SQLite if `DATABASE_URL` is not set

### Backup Methods

#### PostgreSQL Backups
- Uses `pg_dump` to create SQL dumps
- Creates compressed `.sql.gz` files
- Stored in `backups/` directory with subdirectories:
  - `backups/daily/` - Daily backups
  - `backups/critical/` - Critical event backups
  - `backups/shutdown/` - Pre-shutdown backups
  - `backups/` - Periodic backups

#### SQLite Backups
- Uses SQLite backup API for atomic backups
- Creates compressed `.db.gz` files
- Same directory structure as PostgreSQL backups

## Backup Triggers

### Automatic Triggers

1. **Periodic Backups**: Every 20 minutes during active periods
2. **Shutdown Backup**: Before every bot restart/shutdown
3. **Critical Event Backups**:
   - After pack openings with rare cards (legendary/epic/mythic)
   - After marketplace transactions (buy/sell)
   - After pack publishing
   - After dust pack purchases

### Manual Triggers

You can trigger backups manually through the backup service API.

## Backup Schedule Example

```
Railway Automatic: Daily backups (handled automatically, 7-day retention)

Your Custom System:
├── Every 20 minutes during active periods
├── Before every bot restart/deployment
├── After any rare card acquisitions
└── Daily full exports for long-term storage
```

## Recovery Strategy

### Recent Issues (1-7 days)
**Use Railway's built-in restore feature:**
1. Go to Railway dashboard
2. Select your PostgreSQL service
3. Click "Backups" tab
4. Select the backup point
5. Click "Restore"

### Older Issues (7+ days)
**Use your custom backup files:**
1. Locate backup file in `backups/` directory
2. For PostgreSQL: Restore using `psql` or Railway restore
3. For SQLite: Copy backup file to replace current database

### Complete Disaster Recovery
1. Check Railway backups first (if available)
2. Check local backups in `backups/` directory
3. Check cloud storage backups (if configured)
4. Restore from most recent backup

## Environment Variables

### Required (Railway)
- `DATABASE_URL` - Automatically set by Railway when PostgreSQL service is added
  - Format: `postgresql://user:password@host:port/database`
  - Used for both normal operations and backups

### Optional (Custom Backup Storage)
- `POSTGRES_BACKUP_URL` - Your own PostgreSQL instance for long-term archival
  - Format: `postgresql://user:password@host:port/database`
  - Separate from Railway's PostgreSQL
  - Used for syncing backups to external storage

## Backup File Locations

```
backups/
├── daily/
│   ├── music_legends_daily_2024-01-15_12-00-00.sql.gz
│   └── ...
├── critical/
│   ├── music_legends_critical_pack_opening_user_123456.sql.gz
│   └── ...
├── shutdown/
│   ├── music_legends_shutdown_2024-01-15_18-30-00.sql.gz
│   └── ...
├── music_legends_periodic_2024-01-15_14-20-00.sql.gz
├── latest.sql.gz (symlink to latest backup)
└── backup_metadata.json (backup tracking)
```

## Backup Verification

All backups are automatically verified:
- **PostgreSQL**: Checks for SQL content and file integrity
- **SQLite**: Runs `PRAGMA integrity_check` to verify database integrity

Failed backups are automatically deleted and logged.

## Backup Cleanup

Old backups are automatically cleaned up:
- **Daily/Periodic backups**: Kept for 30 days
- **Critical backups**: Kept for 100 backups
- **Shutdown backups**: Kept for 30 days

## Monitoring

Check backup status:
- Logs show backup creation success/failure
- `backup_metadata.json` tracks all backups
- Use `backup_service.get_backup_stats()` for statistics

## Best Practices

1. **Test Restores Regularly**: Periodically test restoring from backups to ensure they work
2. **Monitor Disk Space**: Ensure `backups/` directory has enough space
3. **Cloud Storage**: Consider syncing backups to cloud storage (S3, Google Cloud, etc.)
4. **Documentation**: Keep track of which backup to use for different scenarios
5. **Multiple Locations**: Store backups in multiple locations for redundancy

## Troubleshooting

### pg_dump not found
**Error**: `pg_dump not found. Install PostgreSQL client tools.`

**Solution**: Install PostgreSQL client tools:
- **Ubuntu/Debian**: `apt-get install postgresql-client`
- **macOS**: `brew install postgresql`
- **Windows**: Download from PostgreSQL website

### Insufficient Disk Space
**Error**: `Insufficient disk space for backup`

**Solution**: 
1. Clean up old backups manually
2. Increase disk space allocation
3. Move backups to external storage

### Backup Integrity Check Failed
**Error**: `Backup integrity check failed`

**Solution**:
1. Check database connection
2. Verify database is not corrupted
3. Try creating backup again
4. Check logs for detailed error messages

## Railway Integration

When using Railway PostgreSQL:

1. **Automatic Backups**: Railway handles daily backups automatically
2. **Easy Restore**: Use Railway dashboard for quick restores
3. **Custom Backups**: Your custom backup system runs alongside Railway's backups
4. **No Configuration**: `DATABASE_URL` is automatically set by Railway

## Summary

- **Railway Backups**: Automatic, 7-day retention, easy restore
- **Custom Backups**: Configurable, longer retention, multiple triggers
- **Dual Strategy**: Best of both worlds - quick recovery + long-term protection
