#!/bin/bash
# scripts/verify_pass_criteria.sh
# Verify PASS criteria for backup system checklist

# Load environment variables
source .env.txt

echo "🔍 MUSIC LEGENDS PASS CRITERIA VERIFICATION"
echo "=========================================="

PASSED=0
TOTAL=5

echo "📋 CHECKLIST ITEM 4 - PASS CRITERIA"
echo "=================================="

# 1) Backup runs daily
echo ""
echo "1️⃣  Backup runs daily:"
echo "   Checking backup schedule and recent backups..."

# Check if cron jobs are set up
if crontab -l 2>/dev/null | grep -q "backup_db.sh"; then
    echo "   ✅ Database backup cron job found"
    PASSED=$((PASSED + 1))
else
    echo "   ❌ Database backup cron job not found"
fi

# Check for recent backups
if [ -d "$BACKUP_PATH/db" ]; then
    RECENT_BACKUPS=$(find $BACKUP_PATH/db -name "*.gz" -o -name "*.sql" -o -name "*.db" -mtime -2 | wc -l)
    if [ $RECENT_BACKUPS -gt 0 ]; then
        echo "   ✅ Recent backups found ($RECENT_BACKUPS in last 2 days)"
        PASSED=$((PASSED + 1))
    else
        echo "   ❌ No recent backups found (last 2 days)"
    fi
else
    echo "   ❌ Backup directory not found: $BACKUP_PATH/db"
fi

# 2) Restore test succeeds
echo ""
echo "2️⃣  Restore test succeeds:"
echo "   Checking restore test logs..."

if [ -f "$BACKUP_PATH/logs/restore_test.log" ]; then
    # Check for successful restore test
    SUCCESSFUL_RESTORE=$(tail -10 "$BACKUP_PATH/logs/restore_test.log" | grep -c "Restore test passed")
    if [ $SUCCESSFUL_RESTORE -gt 0 ]; then
        echo "   ✅ Successful restore test found in logs"
        PASSED=$((PASSED + 1))
    else
        echo "   ❌ No successful restore tests found"
    fi
    
    # Show last restore test result
    LAST_RESTORE=$(tail -1 "$BACKUP_PATH/logs/restore_test.log")
    echo "   📋 Last restore test: $LAST_RESTORE"
else
    echo "   ❌ Restore test log not found"
fi

# 3) Purchases table present
echo ""
echo "3️⃣  Purchases table present:"
echo "   Checking database schema..."

if [[ $DATABASE_URL == sqlite* ]]; then
    DB_FILE=$(echo $DATABASE_URL | sed 's/sqlite:\/\///')
    if [ -f "$DB_FILE" ]; then
        PURCHASES_TABLE=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='purchases';")
        if [ "$PURCHASES_TABLE" -eq 1 ]; then
            echo "   ✅ Purchases table found in database"
            PASSED=$((PASSED + 1))
            
            # Check table has data
            PURCHASE_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM purchases;" 2>/dev/null || echo "0")
            echo "   📊 Purchases records: $PURCHASE_COUNT"
        else
            echo "   ❌ Purchases table not found in database"
        fi
    else
        echo "   ❌ Database file not found: $DB_FILE"
    fi
else
    echo "   ⚠️  Non-SQLite database - manual verification required"
fi

# 4) Redis AOF enabled
echo ""
echo "4️⃣  Redis AOF enabled:"
echo "   Checking Redis configuration..."

# Check redis.conf
if [ -f "redis.conf" ]; then
    if grep -q "appendonly yes" redis.conf; then
        echo "   ✅ AOF enabled in redis.conf"
        PASSED=$((PASSED + 1))
    else
        echo "   ❌ AOF not enabled in redis.conf"
    fi
    
    # Check other AOF settings
    if grep -q "appendfsync everysec" redis.conf; then
        echo "   ✅ AOF fsync set to everysec"
    fi
    
    if grep -q "save 60 1" redis.conf; then
        echo "   ✅ RDB snapshots configured"
    fi
else
    echo "   ❌ redis.conf not found"
fi

# Check running Redis instance
if command -v redis-cli &> /dev/null; then
    REDIS_STATUS=$(redis-cli ping 2>/dev/null || echo "")
    if [ "$REDIS_STATUS" = "PONG" ]; then
        AOF_ENABLED=$(redis-cli config get appendonly 2>/dev/null | tail -1 || echo "")
        if [ "$AOF_ENABLED" = "yes" ]; then
            echo "   ✅ AOF enabled in running Redis"
        else
            echo "   ❌ AOF not enabled in running Redis"
        fi
    else
        echo "   ⚠️  Redis not running"
    fi
else
    echo "   ⚠️  Redis CLI not available"
fi

# 5) 14-day retention
echo ""
echo "5️⃣  14-day retention:"
echo "   Checking backup retention policy..."

# Check environment variable
if [ "$RETENTION_DAYS" = "14" ]; then
    echo "   ✅ RETENTION_DAYS set to 14"
else
    echo "   ❌ RETENTION_DAYS not set to 14 (current: $RETENTION_DAYS)"
fi

# Check backup cleanup in scripts
if grep -q "mtime +\$RETENTION_DAYS" scripts/backup_db.sh; then
    echo "   ✅ Database backup cleanup configured"
else
    echo "   ❌ Database backup cleanup not configured"
fi

if grep -q "mtime +\$RETENTION_DAYS" scripts/backup_redis.sh; then
    echo "   ✅ Redis backup cleanup configured"
else
    echo "   ❌ Redis backup cleanup not configured"
fi

# Check for old backups
if [ -d "$BACKUP_PATH/db" ]; then
    OLD_BACKUPS=$(find $BACKUP_PATH/db -name "*.gz" -o -name "*.sql" -o -name "*.db" -mtime +14 | wc -l)
    if [ $OLD_BACKUPS -eq 0 ]; then
        echo "   ✅ No backups older than 14 days"
        PASSED=$((PASSED + 1))
    else
        echo "   ⚠️  Found $OLD_BACKUPS backups older than 14 days"
    fi
else
    echo "   ❌ Backup directory not found"
fi

# Summary
echo ""
echo "📊 PASS CRITERIA SUMMARY"
echo "======================"
echo "✅ Passed: $PASSED/5 criteria"
echo "❌ Failed: $((5 - PASSED))/5 criteria"

if [ $PASSED -eq 5 ]; then
    echo ""
    echo "🎉 ALL PASS CRITERIA MET!"
    echo "📋 Checklist Item 4 = PASS"
    echo "🛡️  Backup system is fully operational"
    echo "🚀 Ready for production deployment"
    
    # Log success
    echo "$(date): PASS criteria verification - ALL CRITERIA MET" >> $BACKUP_PATH/logs/pass_criteria.log
    
else
    echo ""
    echo "⚠️  SOME CRITERIA FAILED"
    echo "🔧 Please address the failed items above"
    echo "📖 Review backup configuration and procedures"
    
    # Log failure
    echo "$(date): PASS criteria verification - $PASSED/5 criteria met" >> $BACKUP_PATH/logs/pass_criteria.log
fi

echo ""
echo "📅 Verification completed: $(date)"
echo "📁 Backup directory: $BACKUP_PATH"
echo "🗄️  Database: $DATABASE_URL"

# Show backup statistics
if [ -d "$BACKUP_PATH/db" ]; then
    BACKUP_COUNT=$(find $BACKUP_PATH/db -name "*.gz" -o -name "*.sql" -o -name "*.db" | wc -l)
    TOTAL_SIZE=$(du -sh $BACKUP_PATH/db 2>/dev/null | cut -f1)
    echo "📊 Current backup statistics:"
    echo "   Total backups: $BACKUP_COUNT"
    echo "   Total size: $TOTAL_SIZE"
fi
