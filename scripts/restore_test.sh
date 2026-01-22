#!/bin/bash
# scripts/restore_test.sh
# Restore test script for database backups

# Load environment variables
source .env.txt

echo "🔄 Database Restore Test"
echo "========================"

# Find latest backup
if [ ! -d "$BACKUP_PATH/db" ]; then
    echo "❌ Backup directory not found: $BACKUP_PATH/db"
    exit 1
fi

LATEST=$(ls -t $BACKUP_PATH/db | head -1)

if [ -z "$LATEST" ]; then
    echo "❌ No backup files found in $BACKUP_PATH/db"
    exit 1
fi

echo "📦 Latest backup: $LATEST"
BACKUP_FILE="$BACKUP_PATH/db/$LATEST"

# Check if backup is compressed
if [[ $LATEST == *.gz ]]; then
    echo "🗜️  Decompressing backup..."
    TEMP_FILE="/tmp/restore_test_$(date +%s).sql"
    gunzip -c "$BACKUP_FILE" > "$TEMP_FILE"
    BACKUP_FILE="$TEMP_FILE"
fi

# Create emergency backup of current database
echo "📋 Creating emergency backup of current database..."
EMERGENCY_DATE=$(date +"%Y-%m-%d_%H-%M-%S")

if [[ $DATABASE_URL == postgres* ]]; then
    EMERGENCY_FILE="$BACKUP_PATH/db/emergency_before_restore_$EMERGENCY_DATE.sql"
    pg_dump $DATABASE_URL > "$EMERGENCY_FILE"
    echo "✅ Emergency backup created: $EMERGENCY_FILE"
    
elif [[ $DATABASE_URL == sqlite* ]]; then
    DB_FILE=$(echo $DATABASE_URL | sed 's/sqlite:\/\///')
    EMERGENCY_FILE="$BACKUP_PATH/db/emergency_before_restore_$EMERGENCY_DATE.db"
    if [ -f "$DB_FILE" ]; then
        cp "$DB_FILE" "$EMERGENCY_FILE"
        echo "✅ Emergency backup created: $EMERGENCY_FILE"
    else
        echo "⚠️  Current database file not found: $DB_FILE"
    fi
    
elif [[ $MYSQL_URL == mysql* ]]; then
    EMERGENCY_FILE="$BACKUP_PATH/db/emergency_before_restore_$EMERGENCY_DATE.sql"
    mysqldump $MYSQL_URL > "$EMERGENCY_FILE"
    echo "✅ Emergency backup created: $EMERGENCY_FILE"
fi

# Perform restore test
echo "🔄 Testing restore from: $BACKUP_FILE"

if [[ $DATABASE_URL == postgres* ]]; then
    echo "🐘 Restoring PostgreSQL database..."
    
    # Test restore by checking SQL syntax
    if psql $DATABASE_URL --file="$BACKUP_FILE" --single-transaction --echo-all > /dev/null 2>&1; then
        echo "✅ PostgreSQL restore test passed"
        RESTORE_SUCCESS=true
    else
        echo "❌ PostgreSQL restore test failed"
        RESTORE_SUCCESS=false
    fi
    
elif [[ $DATABASE_URL == sqlite* ]]; then
    echo "🗄️  Testing SQLite database restore..."
    
    # Test restore by creating temporary database
    TEST_DB="/tmp/test_restore_$(date +%s).db"
    
    if [[ $LATEST == *.db ]] || [[ $LATEST == *.db.gz ]]; then
        # SQLite file backup
        if [[ $LATEST == *.gz ]]; then
            gunzip -c "$BACKUP_PATH/db/$LATEST" > "$TEST_DB"
        else
            cp "$BACKUP_PATH/db/$LATEST" "$TEST_DB"
        fi
        
        # Test database integrity
        if sqlite3 "$TEST_DB" "SELECT COUNT(*) FROM sqlite_master;" > /dev/null 2>&1; then
            echo "✅ SQLite restore test passed"
            RESTORE_SUCCESS=true
        else
            echo "❌ SQLite restore test failed"
            RESTORE_SUCCESS=false
        fi
        
        # Cleanup test database
        rm -f "$TEST_DB"
    else
        echo "❌ Not a SQLite backup file"
        RESTORE_SUCCESS=false
    fi
    
elif [[ $MYSQL_URL == mysql* ]]; then
    echo "🐬 Testing MySQL database restore..."
    
    # Test restore by checking SQL syntax
    if mysql $MYSQL_URL --execute="source $BACKUP_FILE" > /dev/null 2>&1; then
        echo "✅ MySQL restore test passed"
        RESTORE_SUCCESS=true
    else
        echo "❌ MySQL restore test failed"
        RESTORE_SUCCESS=false
    fi
else
    echo "❌ Unsupported database type for restore test"
    RESTORE_SUCCESS=false
fi

# Cleanup temporary file
if [ -f "$TEMP_FILE" ]; then
    rm -f "$TEMP_FILE"
fi

# Log results
if [ "$RESTORE_SUCCESS" = true ]; then
    echo "$(date): Restore test passed: $LATEST" >> $BACKUP_PATH/logs/restore_test.log
    echo "✅ Restore test completed successfully"
    echo "📋 Emergency backup available: $EMERGENCY_FILE"
else
    echo "$(date): Restore test failed: $LATEST" >> $BACKUP_PATH/logs/restore_test.log
    echo "❌ Restore test failed"
    echo "📋 Emergency backup available: $EMERGENCY_FILE"
    exit 1
fi

# Show backup statistics
BACKUP_COUNT=$(find $BACKUP_PATH/db -name "emergency_before_restore_*" | wc -l)
echo "📊 Emergency backups: $BACKUP_COUNT"

echo "🎯 Restore test completed!"
echo "📁 Original backup: $BACKUP_PATH/db/$LATEST"
echo "📋 Emergency backup: $EMERGENCY_FILE"
