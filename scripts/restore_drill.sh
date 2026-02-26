#!/bin/bash

# Restore Drill Script
# Tests complete database recovery from backup
# Verifies data integrity and system functionality

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}---- RESTORE DRILL START ----${NC}"
echo "Timestamp: $(date)"
echo "Host: $(hostname)"
echo ""

# Load environment variables
if [ -f ".env.txt" ]; then
    echo -e "${BLUE}📁 Loading environment from .env.txt${NC}"
    source .env.txt
elif [ -f ".env" ]; then
    echo -e "${BLUE}📁 Loading environment from .env${NC}"
    source .env
else
    echo -e "${RED}❌ No .env.txt or .env file found${NC}"
    exit 1
fi

# Validate required environment variables
echo -e "${BLUE}🔍 Validating environment variables...${NC}"

required_vars=("DATABASE_URL" "BACKUP_PATH" "REDIS_URL")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo -e "${RED}❌ Missing required environment variables:${NC}"
    for var in "${missing_vars[@]}"; do
        echo -e "${RED}   - $var${NC}"
    done
    exit 1
fi

echo -e "${GREEN}✅ Environment variables validated${NC}"

# Check backup directory
if [ ! -d "$BACKUP_PATH" ]; then
    echo -e "${RED}❌ Backup directory not found: $BACKUP_PATH${NC}"
    exit 1
fi

if [ ! -d "$BACKUP_PATH/db" ]; then
    echo -e "${RED}❌ Database backup directory not found: $BACKUP_PATH/db${NC}"
    exit 1
fi

echo -e "${BLUE}📂 Backup directory: $BACKUP_PATH${NC}"

# 1. Pick latest backup
echo -e "${BLUE}📦 Step 1: Selecting latest backup${NC}"
LATEST=$(ls -t "$BACKUP_PATH/db" | head -1)

if [ -z "$LATEST" ]; then
    echo -e "${RED}❌ No backups found in $BACKUP_PATH/db${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Using backup: $LATEST${NC}"
echo -e "${BLUE}📅 Backup date: $(ls -la "$BACKUP_PATH/db/$LATEST" | awk '{print $6, $7, $8}')${NC}"

# Validate backup file
if [ ! -f "$BACKUP_PATH/db/$LATEST" ]; then
    echo -e "${RED}❌ Backup file not found: $BACKUP_PATH/db/$LATEST${NC}"
    exit 1
fi

# Check backup file size
BACKUP_SIZE=$(stat -f%z "$BACKUP_PATH/db/$LATEST" 2>/dev/null || stat -c%s "$BACKUP_PATH/db/$LATEST" 2>/dev/null)
if [ "$BACKUP_SIZE" -lt 1000 ]; then
    echo -e "${RED}❌ Backup file seems too small: $BACKUP_SIZE bytes${NC}"
    exit 1
fi

echo -e "${BLUE}📊 Backup size: $BACKUP_SIZE bytes${NC}"

# 2. Safety snapshot
echo -e "${BLUE}🛡️  Step 2: Creating safety snapshot${NC}"
SNAPSHOT_FILE="$BACKUP_PATH/pre_drill_snapshot_$(date +%Y%m%d_%H%M%S).sql"

if ! pg_dump "$DATABASE_URL" > "$SNAPSHOT_FILE"; then
    echo -e "${RED}❌ Failed to create safety snapshot${NC}"
    exit 1
fi

SNAPSHOT_SIZE=$(stat -f%z "$SNAPSHOT_FILE" 2>/dev/null || stat -c%s "$SNAPSHOT_FILE" 2>/dev/null)
echo -e "${GREEN}✅ Safety snapshot created: $SNAPSHOT_FILE (${SNAPSHOT_SIZE} bytes)${NC}"

# 3. Test database connectivity before dropping
echo -e "${BLUE}🔌 Step 3: Testing database connectivity${NC}"
if ! psql "$DATABASE_URL" -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${RED}❌ Cannot connect to database${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Database connectivity confirmed${NC}"

# 4. Drop & recreate schema
echo -e "${BLUE}🗑️  Step 4: Recreating database schema${NC}"
echo -e "${YELLOW}⚠️  Dropping existing schema...${NC}"

if ! psql "$DATABASE_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" > /dev/null 2>&1; then
    echo -e "${RED}❌ Failed to recreate schema${NC}"
    echo -e "${YELLOW}🔄 Attempting to restore from safety snapshot...${NC}"
    psql "$DATABASE_URL" < "$SNAPSHOT_FILE"
    exit 1
fi

echo -e "${GREEN}✅ Database schema recreated${NC}"

# 5. Restore from backup
echo -e "${BLUE}📥 Step 5: Restoring database${NC}"
echo -e "${YELLOW}⏳ Restoring from $LATEST...${NC}"

if ! psql "$DATABASE_URL" < "$BACKUP_PATH/db/$LATEST"; then
    echo -e "${RED}❌ Database restore failed${NC}"
    echo -e "${YELLOW}🔄 Attempting to restore from safety snapshot...${NC}"
    psql "$DATABASE_URL" < "$SNAPSHOT_FILE"
    exit 1
fi

echo -e "${GREEN}✅ Database restore completed${NC}"

# 6. Verification queries
echo -e "${BLUE}🔍 Step 6: Verifying data integrity${NC}"

# Create verification script
VERIFICATION_SCRIPT=$(cat << 'EOF'
import os
import sys
sys.path.append('.')

try:
    from models.card import Card
    from models.purchase import Purchase
    from models.artist import Artist
    from models.trade import Trade
    
    # Check basic data exists
    card_count = Card.count()
    purchase_count = Purchase.count()
    artist_count = Artist.count()
    trade_count = Trade.count()
    
    print(f"Cards: {card_count}")
    print(f"Purchases: {purchase_count}")
    print(f"Artists: {artist_count}")
    print(f"Trades: {trade_count}")
    
    # Basic sanity checks
    if card_count == 0:
        print("ERROR: No cards found after restore")
        sys.exit(1)
    
    if purchase_count == 0:
        print("ERROR: No purchases found after restore")
        sys.exit(1)
    
    if artist_count == 0:
        print("ERROR: No artists found after restore")
        sys.exit(1)
    
    # Check data relationships
    # Verify some cards have purchases
    cards_with_purchases = len([c for c in Card.all() if c.purchase_id])
    if cards_with_purchases == 0:
        print("WARNING: No cards have purchase_id")
    
    # Verify purchase amounts are reasonable
    purchases = Purchase.all()
    if purchases:
        total_amount = sum(p.amount for p in purchases if p.amount)
        print(f"Total purchase amount: ${total_amount/100:.2f}")
        
        if total_amount <= 0:
            print("WARNING: Total purchase amount is zero or negative")
    
    print("SUCCESS: Data verification passed")
    
except ImportError as e:
    print(f"ERROR: Cannot import models: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Verification failed: {e}")
    sys.exit(1)
EOF
)

# Run verification
echo "$VERIFICATION_SCRIPT" | python

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Data verification failed${NC}"
    echo -e "${YELLOW}🔄 Attempting to restore from safety snapshot...${NC}"
    psql "$DATABASE_URL" < "$SNAPSHOT_FILE"
    exit 1
fi

echo -e "${GREEN}✅ Data verification passed${NC}"

# 7. Redis check
echo -e "${BLUE}🔴 Step 7: Checking Redis connectivity${NC}"

# Extract Redis host and port from REDIS_URL
REDIS_HOST=$(echo "$REDIS_URL" | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
REDIS_PORT=$(echo "$REDIS_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

if [ -z "$REDIS_HOST" ]; then
    REDIS_HOST="localhost"
fi

if [ -z "$REDIS_PORT" ]; then
    REDIS_PORT="6379"
fi

echo -e "${BLUE}🔌 Testing Redis at $REDIS_HOST:$REDIS_PORT${NC}"

if ! redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" PING > /dev/null 2>&1; then
    echo -e "${RED}❌ Redis is not reachable${NC}"
    echo -e "${YELLOW}⚠️  This is a warning, not a failure (Redis may be optional)${NC}"
else
    echo -e "${GREEN}✅ Redis is reachable${NC}"
    
    # Check Redis data if any
    REDIS_KEYS=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" DBSIZE 2>/dev/null || echo "0")
    echo -e "${BLUE}🔑 Redis keys: $REDIS_KEYS${NC}"
fi

# 8. Final system checks
echo -e "${BLUE}🔧 Step 8: Final system checks${NC}"

# Check if we can create a test record
echo -e "${BLUE}🧪 Testing database write capability...${NC}"

TEST_SQL="CREATE TABLE IF NOT EXISTS restore_drill_test (id SERIAL PRIMARY KEY, test_time TIMESTAMP DEFAULT NOW());"
if psql "$DATABASE_URL" -c "$TEST_SQL" > /dev/null 2>&1; then
    # Clean up test table
    psql "$DATABASE_URL" -c "DROP TABLE IF EXISTS restore_drill_test;" > /dev/null 2>&1
    echo -e "${GREEN}✅ Database write capability confirmed${NC}"
else
    echo -e "${RED}❌ Database write capability failed${NC}"
    exit 1
fi

# Calculate total time
END_TIME=$(date +%s)
START_TIME=$(date -d "$(echo $TIMESTAMP)" +%s 2>/dev/null || echo "$END_TIME")
DURATION=$((END_TIME - START_TIME))

echo ""
echo -e "${GREEN}---- RESTORE DRILL PASSED ----${NC}"
echo -e "${GREEN}✅ Backup used: $LATEST${NC}"
echo -e "${GREEN}✅ Safety snapshot: $SNAPSHOT_FILE${NC}"
echo -e "${GREEN}✅ Database restored successfully${NC}"
echo -e "${GREEN}✅ Data verification passed${NC}"
echo -e "${GREEN}✅ System checks passed${NC}"
echo -e "${GREEN}⏱️  Duration: ${DURATION} seconds${NC}"
echo ""

# Cleanup old safety snapshots (keep last 5)
echo -e "${BLUE}🧹 Cleaning up old safety snapshots...${NC}"
cd "$BACKUP_PATH"
ls -t pre_drill_snapshot_*.sql | tail -n +6 | xargs -r rm
echo -e "${GREEN}✅ Cleanup completed${NC}"

echo -e "${GREEN}🎉 Restore drill completed successfully!${NC}"
echo -e "${BLUE}📋 Summary:${NC}"
echo -e "${BLUE}   - Database backup integrity verified${NC}"
echo -e "${BLUE}   - Complete restore capability confirmed${NC}"
echo -e "${BLUE}   - Data integrity maintained${NC}"
echo -e "${BLUE}   - System functionality preserved${NC}"

exit 0
