#!/bin/bash

# Database Backup Script for Music Legends Bot
# Uses PostgreSQL client tools for creating backups

set -e  # Exit on any error

# Configuration
DB_NAME="${DB_NAME:-music_legends}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
BACKUP_DIR="${BACKUP_DIR:-/app/backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/music_legends_backup_${TIMESTAMP}.sql"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "🗄️ Starting database backup..."
echo "📅 Timestamp: $TIMESTAMP"
echo "📁 Backup file: $BACKUP_FILE"

# Check if PostgreSQL tools are available
if ! command -v pg_dump &> /dev/null; then
    echo "❌ Error: pg_dump not found. PostgreSQL client tools not installed."
    exit 1
fi

# Test database connection
echo "🔗 Testing database connection..."
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; then
    echo "❌ Error: Cannot connect to database at $DB_HOST:$DB_PORT"
    exit 1
fi

# Create the backup
echo "💾 Creating database backup..."
if PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_FILE"; then
    echo "✅ Backup created successfully!"
    echo "📊 Backup size: $(du -h "$BACKUP_FILE" | cut -f1)"
else
    echo "❌ Error: Backup creation failed"
    exit 1
fi

# Compress the backup
echo "🗜️ Compressing backup..."
gzip "$BACKUP_FILE"
COMPRESSED_FILE="${BACKUP_FILE}.gz"
echo "✅ Backup compressed: $COMPRESSED_FILE"
echo "📊 Compressed size: $(du -h "$COMPRESSED_FILE" | cut -f1)"

# Clean up old backups (keep last 7 days)
echo "🧹 Cleaning up old backups..."
find "$BACKUP_DIR" -name "music_legends_backup_*.sql.gz" -mtime +7 -delete
echo "✅ Old backups cleaned up"

echo "🎉 Backup completed successfully!"
echo "📍 Location: $COMPRESSED_FILE"

# If running in Railway, also copy to Railway's persistent storage
if [ -n "$RAILWAY_ENVIRONMENT" ]; then
    echo "🚂 Railway environment detected - copying to persistent storage..."
    cp "$COMPRESSED_FILE" "/tmp/railway_backup_${TIMESTAMP}.sql.gz"
    echo "✅ Backup copied to Railway persistent storage"
fi
