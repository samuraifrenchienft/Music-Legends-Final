#!/bin/bash
# scripts/backup_db.sh
# Professional database backup script with PostgreSQL, MySQL, and SQLite support

# Load environment variables
source .env.txt

DATE=$(date +"%Y-%m-%d_%H-%M")
FILE="$BACKUP_PATH/db/game_$DATE.sql"

mkdir -p $BACKUP_PATH/db
mkdir -p $BACKUP_PATH/logs

# Detect database type and backup accordingly
if [[ $DATABASE_URL == postgres* ]]; then
    echo "🐘 Backing up PostgreSQL database..."
    
    pg_dump $DATABASE_URL \
      --clean \
      --if-exists \
      --no-owner \
      --no-privileges \
      --verbose \
      > $FILE
      
elif [[ $DATABASE_URL == sqlite* ]]; then
    echo "🗄️  Backing up SQLite database..."
    
    # Extract database file path from SQLite URL
    DB_FILE=$(echo $DATABASE_URL | sed 's/sqlite:\/\///')
    
    if [ -f "$DB_FILE" ]; then
        cp "$DB_FILE" "$BACKUP_PATH/db/game_$DATE.db"
        FILE="$BACKUP_PATH/db/game_$DATE.db"
    else
        echo "❌ SQLite database file not found: $DB_FILE"
        exit 1
    fi
    
elif [[ $MYSQL_URL == mysql* ]]; then
    echo "🐬 Backing up MySQL database..."
    
    mysqldump $MYSQL_URL \
      --single-transaction \
      --routines \
      --triggers \
      > $FILE
      
else
    echo "❌ Unsupported database type"
    echo "DATABASE_URL: $DATABASE_URL"
    echo "MYSQL_URL: $MYSQL_URL"
    exit 1
fi

# Compress backup
if command -v gzip &> /dev/null; then
    gzip "$FILE"
    FILE="${FILE}.gz"
    echo "🗜️  Backup compressed: $FILE"
fi

# Verify backup was created
if [ -f "$FILE" ]; then
    BACKUP_SIZE=$(du -h "$FILE" | cut -f1)
    echo "✅ Database backup completed: $FILE ($BACKUP_SIZE)"
    
    # Log success
    echo "$(date): Database backup completed: $FILE ($BACKUP_SIZE)" >> $BACKUP_PATH/logs/backup.log
    
    # Keep only last N days
    find $BACKUP_PATH/db -type f -mtime +$RETENTION_DAYS -delete 2>/dev/null
    echo "🧹 Cleaned up backups older than $RETENTION_DAYS days"
    
else
    echo "❌ Backup failed: File not created"
    exit 1
fi

# Show backup statistics
BACKUP_COUNT=$(find $BACKUP_PATH/db -type f | wc -l)
TOTAL_SIZE=$(du -sh $BACKUP_PATH/db 2>/dev/null | cut -f1)

echo "📊 Backup statistics:"
echo "   Total backups: $BACKUP_COUNT"
echo "   Total size: $TOTAL_SIZE"
echo "   Retention: $RETENTION_DAYS days"
