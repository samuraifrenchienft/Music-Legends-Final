#!/bin/bash
# scripts/restore_db.sh
# Music Legends database restore procedure

set -e  # Exit on any error

BACKUP_FILE=$1
DATABASE_URL=${DATABASE_URL:-"music_legends.db"}
BACKUP_DIR="backups"

echo "🔄 Music Legends Database Restore"
echo "================================"

# Check if backup file is provided
if [ -z "$BACKUP_FILE" ]; then
    echo "❌ Usage: $0 <backup_file>"
    echo "📁 Available backups:"
    ls -la $BACKUP_DIR/db_*.gz $BACKUP_DIR/db_*.sql $BACKUP_DIR/db_*.db 2>/dev/null || echo "No backups found"
    exit 1
fi

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    # Try to find in backup directory
    if [ -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
        BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
    else
        echo "❌ Backup file not found: $BACKUP_FILE"
        exit 1
    fi
fi

echo "📦 Restoring from: $BACKUP_FILE"

# Create timestamped backup of current database
echo "📋 Creating backup of current database..."
CURRENT_DATE=$(date +"%Y-%m-%d_%H-%M-%S")

if [[ $DATABASE_URL == *.db ]] || [[ $DATABASE_URL == sqlite* ]]; then
    # SQLite backup
    if [ -f "$DATABASE_URL" ]; then
        cp "$DATABASE_URL" "$BACKUP_DIR/emergency_backup_$CURRENT_DATE.db"
        echo "✅ Current database backed up to: emergency_backup_$CURRENT_DATE.db"
    fi
    
elif [[ $DATABASE_URL == postgres* ]] || [[ $DATABASE_URL == psql* ]]; then
    # PostgreSQL backup
    pg_dump $DATABASE_URL > "$BACKUP_DIR/emergency_backup_$CURRENT_DATE.sql"
    echo "✅ Current database backed up to: emergency_backup_$CURRENT_DATE.sql"
fi

# Extract backup if compressed
TEMP_BACKUP="$BACKUP_FILE"
if [[ $BACKUP_FILE == *.gz ]]; then
    echo "🗜️  Extracting compressed backup..."
    TEMP_BACKUP="/tmp/restore_$(date +%s).db"
    gunzip -c "$BACKUP_FILE" > "$TEMP_BACKUP"
    echo "✅ Extracted to: $TEMP_BACKUP"
fi

# Restore database
echo "🔄 Restoring database..."

if [[ $DATABASE_URL == *.db ]] || [[ $DATABASE_URL == sqlite* ]]; then
    # SQLite restore
    echo "📄 Restoring SQLite database..."
    
    # Validate SQLite file
    if ! sqlite3 "$TEMP_BACKUP" "SELECT name FROM sqlite_master WHERE type='table';" > /dev/null 2>&1; then
        echo "❌ Invalid SQLite backup file"
        rm -f "$TEMP_BACKUP"
        exit 1
    fi
    
    # Copy backup to database location
    cp "$TEMP_BACKUP" "$DATABASE_URL"
    echo "✅ SQLite database restored"
    
elif [[ $DATABASE_URL == postgres* ]] || [[ $DATABASE_URL == psql* ]]; then
    # PostgreSQL restore
    echo "🐘 Restoring PostgreSQL database..."
    
    # Check if PostgreSQL is running
    if ! pg_isready -d $DATABASE_URL; then
        echo "❌ PostgreSQL is not ready"
        rm -f "$TEMP_BACKUP"
        exit 1
    fi
    
    # Restore from SQL file
    psql $DATABASE_URL < "$TEMP_BACKUP"
    echo "✅ PostgreSQL database restored"
fi

# Cleanup temporary file
if [ "$TEMP_BACKUP" != "$BACKUP_FILE" ]; then
    rm -f "$TEMP_BACKUP"
fi

# Verify restore
echo "🔍 Verifying database restore..."

if [[ $DATABASE_URL == *.db ]] || [[ $DATABASE_URL == sqlite* ]]; then
    # SQLite verification
    TABLE_COUNT=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
    USER_COUNT=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")
    PURCHASE_COUNT=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM purchases;" 2>/dev/null || echo "0")
    
    echo "📊 Database verification:"
    echo "  Tables: $TABLE_COUNT"
    echo "  Users: $USER_COUNT"
    echo "  Purchases: $PURCHASE_COUNT"
    
    if [ "$TABLE_COUNT" -gt 0 ] && [ "$USER_COUNT" -ge 0 ]; then
        echo "✅ Database restore verification passed"
    else
        echo "❌ Database restore verification failed"
        exit 1
    fi
    
elif [[ $DATABASE_URL == postgres* ]] || [[ $DATABASE_URL == psql* ]]; then
    # PostgreSQL verification
    TABLE_COUNT=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
    USER_COUNT=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")
    PURCHASE_COUNT=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM purchases;" 2>/dev/null || echo "0")
    
    echo "📊 Database verification:"
    echo "  Tables: $TABLE_COUNT"
    echo "  Users: $USER_COUNT"
    echo "  Purchases: $PURCHASE_COUNT"
    
    if [ "$TABLE_COUNT" -gt 0 ] && [ "$USER_COUNT" -ge 0 ]; then
        echo "✅ Database restore verification passed"
    else
        echo "❌ Database restore verification failed"
        exit 1
    fi
fi

# Log restore completion
echo "$(date): Database restore completed from $BACKUP_FILE" >> $BACKUP_DIR/restore.log

echo "🎉 Database restore completed successfully!"
echo "📁 Source: $BACKUP_FILE"
echo "📅 Restore date: $(date)"
echo "📊 Database verified and ready for use"

# Optional: Restart services
echo "💡 Consider restarting services to ensure data consistency:"
echo "   docker-compose restart worker"
echo "   docker-compose restart bot"
