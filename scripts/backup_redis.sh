#!/bin/bash
# scripts/backup_redis.sh
# Redis backup script with AOF and RDB support

# Load environment variables
source .env.txt

DATE=$(date +"%Y-%m-%d_%H-%M")
FILE="$BACKUP_PATH/redis/redis_$DATE.rdb"

mkdir -p $BACKUP_PATH/redis
mkdir -p $BACKUP_PATH/logs

# Redis configuration
REDIS_HOST=${REDIS_HOST:-"localhost"}
REDIS_PORT=${REDIS_PORT:-"6379"}
REDIS_PASSWORD=${REDIS_PASSWORD:-""}
REDIS_DATA_DIR=${REDIS_DATA_DIR:-"/var/lib/redis"}

echo "🔴 Starting Redis backup..."

# Check if Redis is running
if command -v redis-cli &> /dev/null; then
    # Test Redis connection
    if [[ -n "$REDIS_PASSWORD" ]]; then
        REDIS_PING=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping 2>/dev/null)
    else
        REDIS_PING=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT ping 2>/dev/null)
    fi
    
    if [ "$REDIS_PING" != "PONG" ]; then
        echo "❌ Redis is not responding"
        exit 1
    fi
else
    echo "❌ Redis CLI not found"
    exit 1
fi

# Create background save
echo "💾 Creating Redis background save..."
if [[ -n "$REDIS_PASSWORD" ]]; then
    redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD BGSAVE
else
    redis-cli -h $REDIS_HOST -p $REDIS_PORT BGSAVE
fi

# Wait for background save to complete
echo "⏳ Waiting for background save to complete..."
while true; do
    if [[ -n "$REDIS_PASSWORD" ]]; then
        LASTSAVE=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD LASTSAVE)
        BGSAVE_STATUS=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD INFO persistence | grep "rdb_bgsave_in_progress" | cut -d: -f2 | tr -d '\r')
    else
        LASTSAVE=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT LASTSAVE)
        BGSAVE_STATUS=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT INFO persistence | grep "rdb_bgsave_in_progress" | cut -d: -f2 | tr -d '\r')
    fi
    
    if [ "$BGSAVE_STATUS" = "0" ]; then
        echo "✅ Background save completed"
        break
    fi
    
    echo "   Save in progress... (last save: $LASTSAVE)"
    sleep 2
done

# Copy RDB file
if [ -f "$REDIS_DATA_DIR/dump.rdb" ]; then
    cp "$REDIS_DATA_DIR/dump.rdb" "$FILE"
    echo "✅ RDB file copied: $FILE"
else
    echo "❌ RDB file not found: $REDIS_DATA_DIR/dump.rdb"
    exit 1
fi

# Also backup AOF file if it exists
AOF_FILE="$BACKUP_PATH/redis/redis_$DATE.aof"
if [ -f "$REDIS_DATA_DIR/appendonly.aof" ]; then
    cp "$REDIS_DATA_DIR/appendonly.aof" "$AOF_FILE"
    echo "✅ AOF file copied: $AOF_FILE"
fi

# Compress backups
if command -v gzip &> /dev/null; then
    gzip "$FILE"
    FILE="${FILE}.gz"
    echo "🗜️  RDB backup compressed: $FILE"
    
    if [ -f "$AOF_FILE" ]; then
        gzip "$AOF_FILE"
        AOF_FILE="${AOF_FILE}.gz"
        echo "🗜️  AOF backup compressed: $AOF_FILE"
    fi
fi

# Verify backup was created
if [ -f "$FILE" ]; then
    BACKUP_SIZE=$(du -h "$FILE" | cut -f1)
    echo "✅ Redis backup completed: $FILE ($BACKUP_SIZE)"
    
    # Log success
    echo "$(date): Redis backup completed: $FILE ($BACKUP_SIZE)" >> $BACKUP_PATH/logs/backup.log
    
    # Keep only last N days
    find $BACKUP_PATH/redis -type f -mtime +$RETENTION_DAYS -delete 2>/dev/null
    echo "🧹 Cleaned up Redis backups older than $RETENTION_DAYS days"
    
else
    echo "❌ Redis backup failed: File not created"
    exit 1
fi

# Show Redis statistics
if command -v redis-cli &> /dev/null; then
    echo "📊 Redis statistics:"
    if [[ -n "$REDIS_PASSWORD" ]]; then
        INFO=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD INFO server 2>/dev/null)
        DB_SIZE=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD DBSIZE 2>/dev/null)
    else
        INFO=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT INFO server 2>/dev/null)
        DB_SIZE=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT DBSIZE 2>/dev/null)
    fi
    
    if [ -n "$INFO" ]; then
        REDIS_VERSION=$(echo "$INFO" | grep "redis_version" | cut -d: -f2 | tr -d '\r')
        UPTIME=$(echo "$INFO" | grep "uptime_in_seconds" | cut -d: -f2 | tr -d '\r')
        echo "   Redis version: $REDIS_VERSION"
        echo "   Uptime: $UPTIME seconds"
        echo "   Database size: $DB_SIZE keys"
    fi
fi

# Show backup statistics
BACKUP_COUNT=$(find $BACKUP_PATH/redis -type f | wc -l)
TOTAL_SIZE=$(du -sh $BACKUP_PATH/redis 2>/dev/null | cut -f1)

echo "📊 Backup statistics:"
echo "   Total Redis backups: $BACKUP_COUNT"
echo "   Total size: $TOTAL_SIZE"
echo "   Retention: $RETENTION_DAYS days"
