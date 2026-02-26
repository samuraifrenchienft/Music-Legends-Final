# Restore Drill Guide

## Overview

The restore drill is a critical disaster recovery test that verifies the complete database backup and restore functionality. It ensures that in case of a catastrophic failure, the system can be fully recovered from backups.

## 🚨 Purpose

The restore drill validates:
- **Backup integrity** - Backups contain complete, usable data
- **Restore capability** - Database can be completely rebuilt from backup
- **Data integrity** - All data relationships and constraints are preserved
- **System functionality** - Restored system operates correctly
- **Recovery time** - Restore process completes within acceptable timeframes

## 🔄 Drill Process

### Phase 1: Preparation
1. **Select latest backup** - Choose most recent database backup
2. **Create safety snapshot** - Backup current state before drill
3. **Validate environment** - Check database and Redis connectivity

### Phase 2: Execution
1. **Drop database schema** - Complete database reset
2. **Restore from backup** - Load backup data into clean database
3. **Verify data integrity** - Validate all data exists and is correct

### Phase 3: Validation
1. **Data counts verification** - Cards, purchases, artists exist
2. **Relationship testing** - Foreign keys and constraints work
3. **Functionality testing** - System operations work correctly
4. **Redis verification** - Cache system operational

## 📋 Pass Criteria

### Critical Success Factors

✅ **Database restores without errors**
- SQL restore completes successfully
- No schema conflicts or data errors
- All tables and indexes created correctly

✅ **Cards + purchases exist**
- Card count > 0 after restore
- Purchase count > 0 after restore
- Artist count > 0 after restore
- Data relationships intact

✅ **Redis reachable**
- Redis server responds to PING
- Read/write operations work
- Cache functionality preserved

✅ **Script exit 0**
- No unhandled errors
- All verification steps pass
- Clean completion

### Data Integrity Checks

```python
# Verification queries performed during drill
assert Card.count() > 0, "No cards after restore"
assert Purchase.count() > 0, "No purchases after restore"
assert Artist.count() > 0, "No artists after restore"

# Additional checks
cards_with_purchases = len([c for c in Card.all() if c.purchase_id])
total_purchase_amount = sum(p.amount for p in Purchase.all())
```

## 🛠️ Manual Execution

### Prerequisites
```bash
# Required environment variables
DATABASE_URL="postgres://user:pass@host:port/db"
REDIS_URL="redis://host:port/db"
BACKUP_PATH="/path/to/backups"

# Required tools
- psql (PostgreSQL client)
- redis-cli (Redis client)
- Python with models access
```

### Running the Drill
```bash
# Make script executable
chmod +x scripts/restore_drill.sh

# Run the drill
./scripts/restore_drill.sh

# Or with specific environment
DATABASE_URL="..." REDIS_URL="..." BACKUP_PATH="..." ./scripts/restore_drill.sh
```

### Expected Output
```
---- RESTORE DRILL START ----
📁 Loading environment from .env.txt
🔍 Validating environment variables...
✅ Environment variables validated
📂 Backup directory: /path/to/backups
📦 Step 1: Selecting latest backup
✅ Using backup: backup_20231201_050001.sql
🛡️  Step 2: Creating safety snapshot
✅ Safety snapshot created: pre_drill_snapshot_20231201_053015.sql
🔌 Step 3: Testing database connectivity
✅ Database connectivity confirmed
🗑️  Step 4: Recreating database schema
✅ Database schema recreated
📥 Step 5: Restoring database
✅ Database restore completed
🔍 Step 6: Verifying data integrity
Cards: 1234
Purchases: 567
Artists: 89
SUCCESS: Data verification passed
✅ Data verification passed
🔴 Step 7: Checking Redis connectivity
✅ Redis is reachable
🔑 Redis keys: 42
🔧 Step 8: Final system checks
✅ Database write capability confirmed

---- RESTORE DRILL PASSED ----
✅ Backup used: backup_20231201_050001.sql
✅ Safety snapshot: pre_drill_snapshot_20231201_053015.sql
✅ Database restored successfully
✅ Data verification passed
✅ System checks passed
⏱️  Duration: 45 seconds
🎉 Restore drill completed successfully!
```

## 🔄 Automated Execution (CI/CD)

### GitHub Actions Schedule
```yaml
# Runs weekly on Monday at 5:00 AM UTC
schedule:
  - cron: "0 5 * * 1"
```

### Manual Trigger
```bash
# Via GitHub UI
1. Go to Actions tab
2. Select "restore-drill" workflow
3. Click "Run workflow"
4. Add reason for manual run
```

### CI Environment Setup
The CI workflow:
1. Creates test database with sample data
2. Generates test backup
3. Runs restore drill script
4. Verifies results
5. Generates report
6. Uploads artifacts

## 📊 Monitoring and Alerting

### Success Indicators
- ✅ Script exits with code 0
- ✅ All verification steps pass
- ✅ Data counts within expected ranges
- ✅ Redis operations successful
- ✅ Duration under 5 minutes

### Failure Indicators
- ❌ Script exits with non-zero code
- ❌ Database restore errors
- ❌ Data counts zero or unexpected
- ❌ Redis connectivity issues
- ❌ Verification failures

### Alert Configuration
```yaml
# On failure
- Send Slack notification
- Create GitHub issue
- Email maintainers
- Update dashboard status
```

## 🔧 Troubleshooting

### Common Issues

**"No backups found"**
```bash
# Check backup directory
ls -la $BACKUP_PATH/db/

# Check backup permissions
ls -ld $BACKUP_PATH

# Create test backup
pg_dump $DATABASE_URL > $BACKUP_PATH/db/test_backup.sql
```

**"Database restore failed"**
```bash
# Check backup file integrity
pg_dump --verbose $DATABASE_URL > /dev/null

# Check backup content
head -20 $BACKUP_PATH/db/backup_file.sql

# Test restore manually
psql $DATABASE_URL < $BACKUP_PATH/db/backup_file.sql
```

**"Data verification failed"**
```bash
# Check database connectivity
psql $DATABASE_URL -c "\dt"

# Check table contents
psql $DATABASE_URL -c "SELECT COUNT(*) FROM cards;"

# Check model imports
python -c "from models.card import Card; print(Card.count())"
```

**"Redis is not reachable"**
```bash
# Check Redis server
redis-cli -h $REDIS_HOST -p $REDIS_PORT PING

# Check Redis configuration
redis-cli -h $REDIS_HOST -p $REDIS_PORT INFO

# Test Redis operations
redis-cli set test_key test_value
redis-cli get test_key
```

### Recovery Procedures

**If restore fails:**
1. **Stop immediately** - Don't continue with corrupted data
2. **Restore from safety snapshot** - Use pre-drill backup
3. **Investigate failure** - Check logs and error messages
4. **Fix underlying issue** - Resolve root cause
5. **Retry drill** - Run again after fix

**If safety snapshot fails:**
1. **Check current state** - Verify database is still accessible
2. **Create new backup** - Generate fresh backup before proceeding
3. **Document issue** - Record for future prevention
4. **Continue with caution** - Proceed only if data is safe

## 📈 Performance Metrics

### Expected Performance
- **Restore time**: < 2 minutes for typical database
- **Verification time**: < 30 seconds
- **Total drill time**: < 5 minutes
- **Backup size**: Typically 10-100MB

### Performance Monitoring
```bash
# Track restore duration
time psql $DATABASE_URL < backup_file.sql

# Monitor database size
du -sh $BACKUP_PATH/db/backup_file.sql

# Check Redis performance
redis-cli --latency-history
```

## 🎯 Best Practices

### Before Running Drill
- [ ] Verify recent backups exist and are complete
- [ ] Check system load is reasonable
- [ ] Notify team of scheduled drill
- [ ] Have rollback plan ready

### During Drill
- [ ] Monitor progress closely
- [ ] Document any issues
- [ ] Don't interrupt unless critical failure
- [ ] Record timing metrics

### After Drill
- [ ] Review results and logs
- [ ] Update documentation if needed
- [ ] Share results with team
- [ ] Schedule next drill

### Continuous Improvement
- [ ] Track drill success rate
- [ ] Monitor restore times
- [ ] Identify and fix recurring issues
- [ ] Optimize backup/restore process

## 🚀 Emergency Procedures

### Production Disaster Recovery
If actual disaster occurs:
1. **Stop all application traffic**
2. **Run restore drill script with production backup**
3. **Verify data integrity**
4. **Restart application services**
5. **Monitor system closely**

### Emergency Bypass
If drill must be skipped:
1. **Document reason for bypass**
2. **Get approval from maintainers**
3. **Schedule makeup drill ASAP**
4. **Review prevention measures**

---

**🎯 The restore drill ensures your system can survive any database disaster and recover completely!**
