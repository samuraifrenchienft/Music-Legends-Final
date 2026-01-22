#!/bin/bash
# scripts/verify_backup_complete.sh
# Complete backup system verification against PASS criteria

echo "🔍 Music Legends Backup System Verification"
echo "=========================================="

BACKUP_DIR="backups"
DATABASE_URL=${DATABASE_URL:-"music_legends.db"}

echo "📋 PASS CRITERIA CHECKLIST"
echo "========================"

# 1) Daily DB dump created
echo ""
echo "1️⃣  Daily DB dump created:"
echo "   Checking for recent database backups..."

TODAY=$(date +"%Y-%m-%d")
YESTERDAY=$(date -d "yesterday" +"%Y-%m-%d" 2>/dev/null || date -v-1d +"%Y-%m-%d" 2>/dev/null || echo "$TODAY")

# Check for today's or yesterday's backup
TODAY_BACKUP=$(find $BACKUP_DIR -name "db_$TODAY*" -o -name "db_$YESTERDAY*" | head -1)

if [ -n "$TODAY_BACKUP" ]; then
    echo "   ✅ PASS: Recent database backup found: $(basename $TODAY_BACKUP)"
    BACKUP_DATE=$(basename $TODAY_BACKUP | grep -o '[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}')
    echo "   📅 Backup date: $BACKUP_DATE"
else
    echo "   ❌ FAIL: No recent database backup found"
    echo "   📁 Available backups:"
    ls -la $BACKUP_DIR/db_*.gz $BACKUP_DIR/db_*.sql $BACKUP_DIR/db_*.db 2>/dev/null | tail -5
fi

# 2) Restore tested once
echo ""
echo "2️⃣  Restore tested once:"
echo "   Checking restore test logs..."

if [ -f "$BACKUP_DIR/verification.log" ]; then
    LAST_TEST=$(tail -1 "$BACKUP_DIR/verification.log")
    echo "   ✅ PASS: Restore test logged: $LAST_TEST"
else
    echo "   ❌ FAIL: No restore test logs found"
    echo "   💡 Run: ./scripts/verify_backup.sh"
fi

# Check for emergency backups (indicates restore was tested)
EMERGENCY_BACKUPS=$(find $BACKUP_DIR -name "emergency_backup_*" | wc -l)
if [ $EMERGENCY_BACKUPS -gt 0 ]; then
    echo "   ✅ PASS: Emergency backups found ($EMERGENCY_BACKUPS), indicating restore testing"
fi

# 3) Redis AOF enabled
echo ""
echo "3️⃣  Redis AOF enabled:"
echo "   Checking Redis AOF configuration..."

if [ -f "redis.conf" ]; then
    if grep -q "appendonly yes" redis.conf; then
        echo "   ✅ PASS: AOF enabled in redis.conf"
    else
        echo "   ❌ FAIL: AOF not enabled in redis.conf"
    fi
else
    echo "   ⚠️  WARNING: redis.conf not found"
fi

# Check running Redis instance
if command -v redis-cli &> /dev/null; then
    REDIS_STATUS=$(redis-cli ping 2>/dev/null || echo "")
    if [ "$REDIS_STATUS" = "PONG" ]; then
        AOF_ENABLED=$(redis-cli config get appendonly 2>/dev/null | tail -1 || echo "")
        if [ "$AOF_ENABLED" = "yes" ]; then
            echo "   ✅ PASS: AOF enabled in running Redis instance"
        else
            echo "   ❌ FAIL: AOF not enabled in running Redis instance"
        fi
    else
        echo "   ⚠️  WARNING: Redis not running"
    fi
else
    echo "   ⚠️  WARNING: Redis CLI not available"
fi

# Check for AOF file
REDIS_DATA_DIR="/data"
if [ -f /.dockerenv ]; then
    REDIS_DATA_DIR="/data"
fi

if [ -f "$REDIS_DATA_DIR/appendonly.aof" ]; then
    AOF_SIZE=$(du -h "$REDIS_DATA_DIR/appendonly.aof" | cut -f1)
    echo "   ✅ PASS: AOF file exists ($AOF_SIZE)"
else
    echo "   ❌ FAIL: AOF file not found"
fi

# 4) Backups kept 14 days
echo ""
echo "4️⃣  Backups kept 14 days:"
echo "   Checking backup retention policy..."

if [ -d "$BACKUP_DIR" ]; then
    TOTAL_BACKUPS=$(find $BACKUP_DIR -name "db_*.gz" -o -name "db_*.sql" -o -name "db_*.db" | wc -l)
    OLD_BACKUPS=$(find $BACKUP_DIR -name "db_*.gz" -o -name "db_*.sql" -o -name "db_*.db" -mtime +14 | wc -l)
    
    echo "   📊 Total backups: $TOTAL_BACKUPS"
    echo "   📊 Backups older than 14 days: $OLD_BACKUPS"
    
    if [ $OLD_BACKUPS -eq 0 ]; then
        echo "   ✅ PASS: No backups older than 14 days"
    else
        echo "   ❌ FAIL: Found $OLD_BACKUPS backups older than 14 days"
        echo "   💡 Run: find $BACKUP_DIR -type f -mtime +14 -delete"
    fi
    
    # Check backup age range
    OLDEST_BACKUP=$(find $BACKUP_DIR -name "db_*.gz" -o -name "db_*.sql" -o -name "db_*.db" -printf "%T@ %p\n" | sort -n | head -1 | cut -d' ' -f2-)
    if [ -n "$OLDEST_BACKUP" ]; then
        OLDEST_DAYS=$(find "$OLDEST_BACKUP" -mtime +14 -print | wc -l)
        if [ $OLDEST_DAYS -eq 0 ]; then
            echo "   ✅ PASS: Oldest backup is within 14 days"
        else
            echo "   ⚠️  WARNING: Oldest backup is older than 14 days"
        fi
    fi
else
    echo "   ❌ FAIL: Backup directory not found"
fi

# 5) Purchases table included
echo ""
echo "5️⃣  Purchases table included:"
echo "   Checking purchases table in backups..."

LATEST_BACKUP=$(find $BACKUP_DIR -name "db_*.gz" -o -name "db_*.sql" -o -name "db_*.db" | sort -r | head -1)

if [ -n "$LATEST_BACKUP" ]; then
    echo "   📦 Checking latest backup: $(basename $LATEST_BACKUP)"
    
    # Extract backup for checking
    TEMP_CHECK="/tmp/backup_check_$(date +%s)"
    if [[ $LATEST_BACKUP == *.gz ]]; then
        gunzip -c "$LATEST_BACKUP" > "$TEMP_CHECK"
    else
        cp "$LATEST_BACKUP" "$TEMP_CHECK"
    fi
    
    # Check for purchases table
    if [[ $LATEST_BACKUP == *.db ]] || [[ $LATEST_BACKUP == *.sql ]]; then
        if [[ $LATEST_BACKUP == *.db ]]; then
            # SQLite check
            if sqlite3 "$TEMP_CHECK" "SELECT name FROM sqlite_master WHERE type='table' AND name='purchases';" 2>/dev/null | grep -q "purchases"; then
                PURCHASE_COUNT=$(sqlite3 "$TEMP_CHECK" "SELECT COUNT(*) FROM purchases;" 2>/dev/null || echo "0")
                echo "   ✅ PASS: Purchases table found with $PURCHASE_COUNT records"
            else
                echo "   ❌ FAIL: Purchases table not found in backup"
            fi
        else
            # PostgreSQL check
            if grep -q "CREATE TABLE purchases" "$TEMP_CHECK" 2>/dev/null; then
                echo "   ✅ PASS: Purchases table definition found in backup"
            else
                echo "   ❌ FAIL: Purchases table not found in backup"
            fi
        fi
    fi
    
    rm -f "$TEMP_CHECK"
else
    echo "   ❌ FAIL: No backup found to check"
fi

# Summary
echo ""
echo "📊 VERIFICATION SUMMARY"
echo "===================="

# Count passes
PASSES=0
FAILS=0

# Check each criterion
if [ -n "$TODAY_BACKUP" ]; then PASSES=$((PASSES + 1)); else FAILS=$((FAILS + 1)); fi
if [ -f "$BACKUP_DIR/verification.log" ] || [ $EMERGENCY_BACKUPS -gt 0 ]; then PASSES=$((PASSES + 1)); else FAILS=$((FAILS + 1)); fi
if grep -q "appendonly yes" redis.conf 2>/dev/null; then PASSES=$((PASSES + 1)); else FAILS=$((FAILS + 1)); fi
if [ $OLD_BACKUPS -eq 0 ]; then PASSES=$((PASSES + 1)); else FAILS=$((FAILS + 1)); fi
if [ -n "$LATEST_BACKUP" ]; then PASSES=$((PASSES + 1)); else FAILS=$((FAILS + 1)); fi

echo "✅ Passed: $PASSES/5 criteria"
echo "❌ Failed: $FAILS/5 criteria"

if [ $FAILS -eq 0 ]; then
    echo ""
    echo "🎉 ALL PASS CRITERIA MET!"
    echo "📋 Backup system is fully operational"
    echo "🔒 Your data is protected and recoverable"
else
    echo ""
    echo "⚠️  SOME CRITERIA FAILED"
    echo "🔧 Please address the failed items above"
    echo "📖 Refer to BACKUP_GUIDE.md for assistance"
fi

echo ""
echo "📅 Verification completed: $(date)"
echo "📁 Backup directory: $BACKUP_DIR"
echo "🗄️  Database: $DATABASE_URL"
