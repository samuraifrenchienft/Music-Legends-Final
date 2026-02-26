#!/bin/bash
# scripts/setup_cron.sh
# Setup cron jobs for automated backups

# Load environment variables
source .env.txt

echo "⏰ Setting up automated backup cron jobs"
echo "======================================"

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"

# Create cron entries
CRON_ENTRIES="# Music Legends Automated Backups
# Database backup every day at 2 AM
0 2 * * * cd $APP_DIR && scripts/backup_db.sh

# Redis backup every day at 2:10 AM
10 2 * * * cd $APP_DIR && scripts/backup_redis.sh

# Restore test every Sunday at 3 AM
0 3 * * 0 cd $APP_DIR && scripts/restore_test.sh

# Cleanup logs every Monday at 4 AM
0 4 * * 1 cd $APP_DIR && find $BACKUP_PATH/logs -name \"*.log\" -mtime +30 -delete
"

echo "📋 Proposed cron entries:"
echo "$CRON_ENTRIES"

# Ask user if they want to install
echo ""
read -p "🔧 Install these cron jobs? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Create temporary cron file
    TEMP_CRON="/tmp/music_legends_cron_$(date +%s)"
    echo "$CRON_ENTRIES" > "$TEMP_CRON"
    
    # Add to crontab
    crontab "$TEMP_CRON" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "✅ Cron jobs installed successfully"
        
        # Show current crontab
        echo ""
        echo "📋 Current crontab:"
        crontab -l | grep "Music Legends" -A 10
    else
        echo "❌ Failed to install cron jobs"
        echo "💡 You may need to run: crontab -e and add manually"
    fi
    
    # Cleanup
    rm -f "$TEMP_CRON"
else
    echo "⏭️  Cron installation skipped"
    echo "💡 To install manually, run: crontab -e"
    echo "   and add the entries above"
fi

echo ""
echo "🎯 Backup automation setup complete!"
echo "📅 Schedule:"
echo "   🗄️  Database backup: Daily at 2:00 AM"
echo "   🔴 Redis backup: Daily at 2:10 AM"
echo "   🔄 Restore test: Weekly on Sunday at 3:00 AM"
echo "   🧹 Log cleanup: Weekly on Monday at 4:00 AM"
