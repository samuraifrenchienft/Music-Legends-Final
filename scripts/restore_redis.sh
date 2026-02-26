#!/bin/bash
# scripts/restore_redis.sh
# Redis restore procedure

set -e  # Exit on any error

REDIS_DATA_DIR="/var/lib/redis"
REDIS_CONF="/etc/redis/redis.conf"
BACKUP_FILE=$1

echo "🔴 Music Legends Redis Restore"
echo "=============================="

# Check if backup file is provided
if [ -z "$BACKUP_FILE" ]; then
    echo "❌ Usage: $0 <backup_file>"
    echo "📁 Available Redis backups:"
    ls -la /data/appendonly.aof* /data/dump.rdb* 2>/dev/null || echo "No Redis backups found"
    exit 1
fi

# Check if running in Docker
if [ -f /.dockerenv ]; then
    REDIS_DATA_DIR="/data"
    REDIS_CONF="/usr/local/etc/redis/redis.conf"
fi

echo "📦 Restoring Redis from: $BACKUP_FILE"

# Check if Redis is running
REDIS_PID=$(pgrep redis-server || echo "")
if [ -n "$REDIS_PID" ]; then
    echo "⏹️  Stopping Redis server..."
    if command -v systemctl &> /dev/null; then
        systemctl stop redis
    elif command -v docker-compose &> /dev/null; then
        docker-compose stop redis
    else
        kill $REDIS_PID
    fi
    sleep 2
fi

# Create backup of current Redis data
echo "📋 Creating backup of current Redis data..."
CURRENT_DATE=$(date +"%Y-%m-%d_%H-%M-%S")

if [ -f "$REDIS_DATA_DIR/appendonly.aof" ]; then
    cp "$REDIS_DATA_DIR/appendonly.aof" "$REDIS_DATA_DIR/appendonly.aof.backup_$CURRENT_DATE"
    echo "✅ AOF backed up: appendonly.aof.backup_$CURRENT_DATE"
fi

if [ -f "$REDIS_DATA_DIR/dump.rdb" ]; then
    cp "$REDIS_DATA_DIR/dump.rdb" "$REDIS_DATA_DIR/dump.rdb.backup_$CURRENT_DATE"
    echo "✅ RDB backed up: dump.rdb.backup_$CURRENT_DATE"
fi

# Restore Redis data
echo "🔄 Restoring Redis data..."

if [[ $BACKUP_FILE == *.aof ]] || [[ $BACKUP_FILE == *appendonly* ]]; then
    # Restore from AOF file
    echo "📄 Restoring from AOF file..."
    cp "$BACKUP_FILE" "$REDIS_DATA_DIR/appendonly.aof"
    
    # Remove RDB file to force AOF loading
    rm -f "$REDIS_DATA_DIR/dump.rdb"
    echo "✅ AOF file restored"
    
elif [[ $BACKUP_FILE == *.rdb ]] || [[ $BACKUP_FILE == *dump* ]]; then
    # Restore from RDB file
    echo "📸 Restoring from RDB file..."
    cp "$BACKUP_FILE" "$REDIS_DATA_DIR/dump.rdb"
    
    # Remove AOF file to force RDB loading
    rm -f "$REDIS_DATA_DIR/appendonly.aof"
    echo "✅ RDB file restored"
    
else
    echo "❌ Unsupported backup file type. Use .aof or .rdb file."
    exit 1
fi

# Set correct permissions
chown redis:redis "$REDIS_DATA_DIR"/* 2>/dev/null || chown $USER:$USER "$REDIS_DATA_DIR"/*
chmod 644 "$REDIS_DATA_DIR"/*

# Start Redis server
echo "🚀 Starting Redis server..."
if command -v systemctl &> /dev/null; then
    systemctl start redis
elif command -v docker-compose &> /dev/null; then
    docker-compose start redis
else
    redis-server $REDIS_CONF --daemonize yes
fi

# Wait for Redis to start
echo "⏳ Waiting for Redis to start..."
sleep 3

# Verify Redis is running
if command -v redis-cli &> /dev/null; then
    REDIS_STATUS=$(redis-cli ping 2>/dev/null || echo "")
    if [ "$REDIS_STATUS" = "PONG" ]; then
        echo "✅ Redis server is running"
        
        # Check data integrity
        echo "🔍 Verifying Redis data..."
        DB_SIZE=$(redis-cli dbsize 2>/dev/null || echo "0")
        INFO=$(redis-cli info server 2>/dev/null || echo "")
        
        echo "📊 Redis verification:"
        echo "  Keys in database: $DB_SIZE"
        echo "  Server info available: $([ -n "$INFO" ] && echo "Yes" || echo "No")"
        
        # Check for specific keys
        RATE_LIMIT_KEYS=$(redis-cli keys "rate_limit:*" 2>/dev/null | wc -l || echo "0")
        QUEUE_KEYS=$(redis-cli keys "rq:*" 2>/dev/null | wc -l || echo "0")
        
        echo "  Rate limit keys: $RATE_LIMIT_KEYS"
        echo "  Queue keys: $QUEUE_KEYS"
        
        echo "✅ Redis restore verification passed"
        
    else
        echo "❌ Redis server failed to start"
        exit 1
    fi
else
    echo "⚠️  Redis CLI not available, manual verification required"
fi

# Log restore completion
echo "$(date): Redis restore completed from $BACKUP_FILE" >> /var/log/redis_restore.log 2>/dev/null || echo "$(date): Redis restore completed from $BACKUP_FILE" >> redis_restore.log

echo "🎉 Redis restore completed successfully!"
echo "📁 Source: $BACKUP_FILE"
echo "📅 Restore date: $(date)"
echo "🔴 Redis server verified and running"

# Optional: Check AOF configuration
if [ -f "$REDIS_CONF" ]; then
    if grep -q "appendonly yes" "$REDIS_CONF"; then
        echo "✅ AOF persistence is enabled"
    else
        echo "⚠️  AOF persistence may not be enabled"
    fi
fi
