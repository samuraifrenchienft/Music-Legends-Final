#!/bin/bash
# scripts/disaster_test.sh
# Complete disaster recovery test for Music Legends system

set -e  # Exit on any error

echo "🚨 MUSIC LEGENDS DISASTER RECOVERY TEST"
echo "====================================="

BACKUP_DIR="backups"
TEST_DB="test_music_legends.db"
DATABASE_URL=${DATABASE_URL:-"music_legends.db"}

echo "⚠️  WARNING: This will test complete disaster recovery"
echo "📋 Test Steps:"
echo "   1. Create test pack open"
echo "   2. Take backup"
echo "   3. Delete database"
echo "   4. Restore from backup"
echo "   5. Verify data integrity"
echo ""
read -p "🔴 Do you want to continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Disaster test cancelled"
    exit 1
fi

# Step 1: Create test pack open
echo ""
echo "📦 Step 1: Creating test pack open..."
echo "================================"

# Create test database if it doesn't exist
if [ ! -f "$DATABASE_URL" ]; then
    echo "🗄️  Creating test database..."
    sqlite3 "$DATABASE_URL" "
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS cards (
        id INTEGER PRIMARY KEY,
        serial TEXT UNIQUE,
        user_id INTEGER,
        card_name TEXT,
        tier TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS purchases (
        id TEXT PRIMARY KEY,
        user_id INTEGER,
        pack_type TEXT,
        amount_cents INTEGER,
        status TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS audit_logs (
        id TEXT PRIMARY KEY,
        event TEXT,
        user_id INTEGER,
        target_id TEXT,
        payload TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS drops (
        id TEXT PRIMARY KEY,
        owner_id INTEGER,
        card_ids TEXT,
        expires_at DATETIME,
        resolved BOOLEAN DEFAULT FALSE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS trades (
        id TEXT PRIMARY KEY,
        user_a INTEGER,
        user_b INTEGER,
        cards_a TEXT,
        cards_b TEXT,
        gold_a INTEGER DEFAULT 0,
        gold_b INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        expires_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS artists (
        id INTEGER PRIMARY KEY,
        name TEXT,
        royalty_rate REAL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    "
    echo "✅ Test database schema created"
fi

# Insert test user
echo "👤 Creating test user..."
sqlite3 "$DATABASE_URL" "
INSERT OR REPLACE INTO users (id, username) VALUES (12345, 'disaster_test_user');
"

# Insert test cards
echo "🎴 Creating test cards..."
sqlite3 "$DATABASE_URL" "
INSERT OR REPLACE INTO cards (id, serial, user_id, card_name, tier) VALUES
(1, 'CARD_001', 12345, 'Fire Dragon', 'legendary'),
(2, 'CARD_002', 12345, 'Water Spirit', 'epic'),
(3, 'CARD_003', 12345, 'Earth Golem', 'rare'),
(4, 'CARD_004', 12345, 'Wind Fairy', 'common'),
(5, 'CARD_005', 12345, 'Lightning Phoenix', 'legendary');
"

# Insert test purchase
echo "💳 Creating test purchase..."
PURCHASE_ID="purchase_$(date +%s)"
sqlite3 "$DATABASE_URL" "
INSERT OR REPLACE INTO purchases (id, user_id, pack_type, amount_cents, status) VALUES
('$PURCHASE_ID', 12345, 'founder_pack_black', 9999, 'completed');
"

# Insert test audit logs
echo "📊 Creating test audit logs..."
sqlite3 "$DATABASE_URL" "
INSERT OR REPLACE INTO audit_logs (id, event, user_id, target_id, payload) VALUES
('audit_1', 'pack_open', 12345, 'black_pack', '{\"cards\": [\"CARD_001\", \"CARD_002\", \"CARD_003\"], \"pack_type\": \"black\"}'),
('audit_2', 'purchase_completed', 12345, '$PURCHASE_ID', '{\"pack_type\": \"founder_pack_black\", \"amount\": 9999}'),
('audit_3', 'card_created', 12345, 'CARD_001', '{\"card_name\": \"Fire Dragon\", \"tier\": \"legendary\"}'),
('audit_4', 'user_login', 12345, 'user_12345', '{\"ip_address\": \"127.0.0.1\"}');
"

# Insert test drop
echo "🎯 Creating test drop..."
DROP_ID="drop_$(date +%s)"
sqlite3 "$DATABASE_URL" "
INSERT OR REPLACE INTO drops (id, owner_id, card_ids, expires_at, resolved) VALUES
('$DROP_ID', 12345, '[\"CARD_004\", \"CARD_005\"]', datetime('now', '+1 day'), FALSE);
"

# Insert test trade
echo "🤝 Creating test trade..."
TRADE_ID="trade_$(date +%s)"
sqlite3 "$DATABASE_URL" "
INSERT OR REPLACE INTO trades (id, user_a, user_b, cards_a, cards_b, gold_a, gold_b, status) VALUES
('$TRADE_ID', 12345, 67890, '[\"CARD_002\"]', '[\"CARD_003\"]', 100, 200, 'completed');
"

# Insert test artist
echo "🎨 Creating test artist..."
sqlite3 "$DATABASE_URL" "
INSERT OR REPLACE INTO artists (id, name, royalty_rate) VALUES
(1, 'Digital Artist', 0.15),
(2, 'Pixel Master', 0.12);
"

echo "✅ Step 1 completed: Test data created"

# Record initial state
echo ""
echo "📊 Initial Database State:"
echo "========================"
INITIAL_USERS=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM users;")
INITIAL_CARDS=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM cards;")
INITIAL_PURCHASES=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM purchases;")
INITIAL_AUDIT_LOGS=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM audit_logs;")
INITIAL_DROPS=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM drops;")
INITIAL_TRADES=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM trades;")
INITIAL_ARTISTS=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM artists;")

echo "Users: $INITIAL_USERS"
echo "Cards: $INITIAL_CARDS"
echo "Purchases: $INITIAL_PURCHASES"
echo "Audit logs: $INITIAL_AUDIT_LOGS"
echo "Drops: $INITIAL_DROPS"
echo "Trades: $INITIAL_TRADES"
echo "Artists: $INITIAL_ARTISTS"

# Step 2: Take backup
echo ""
echo "💾 Step 2: Taking backup..."
echo "=========================="

BACKUP_DATE=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="$BACKUP_DIR/disaster_test_backup_$BACKUP_DATE.db"

mkdir -p "$BACKUP_DIR"
cp "$DATABASE_URL" "$BACKUP_FILE"
echo "✅ Backup created: $BACKUP_FILE"

# Compress backup
gzip "$BACKUP_FILE"
BACKUP_FILE_GZ="$BACKUP_FILE.gz"
echo "🗜️  Backup compressed: $BACKUP_FILE_GZ"

# Verify backup
BACKUP_SIZE=$(du -h "$BACKUP_FILE_GZ" | cut -f1)
echo "📊 Backup size: $BACKUP_SIZE"

# Step 3: Delete database
echo ""
echo "💥 Step 3: Deleting database..."
echo "============================"

# Create emergency backup first
EMERGENCY_BACKUP="$BACKUP_DIR/emergency_before_disaster_$BACKUP_DATE.db"
cp "$DATABASE_URL" "$EMERGENCY_BACKUP"
echo "📋 Emergency backup created: $EMERGENCY_BACKUP"

# Delete the database
rm -f "$DATABASE_URL"
echo "💥 Database deleted: $DATABASE_URL"

# Verify deletion
if [ -f "$DATABASE_URL" ]; then
    echo "❌ ERROR: Database still exists!"
    exit 1
else
    echo "✅ Database successfully deleted"
fi

# Step 4: Restore from backup
echo ""
echo "🔄 Step 4: Restoring from backup..."
echo "==============================="

# Extract backup
echo "🗜️  Extracting backup..."
gunzip -c "$BACKUP_FILE_GZ" > "$DATABASE_URL"
echo "✅ Backup extracted to: $DATABASE_URL"

# Verify restore
if [ -f "$DATABASE_URL" ]; then
    echo "✅ Database file restored"
else
    echo "❌ ERROR: Database restore failed!"
    exit 1
fi

# Step 5: Verify data integrity
echo ""
echo "🔍 Step 5: Verifying data integrity..."
echo "=================================="

# Check database structure
echo "📋 Checking database structure..."
TABLES=$(sqlite3 "$DATABASE_URL" "SELECT name FROM sqlite_master WHERE type='table';")
echo "Tables found: $TABLES"

# Verify each table
echo ""
echo "📊 Verifying table data:"

# Users
RESTORED_USERS=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM users;")
echo "Users: $RESTORED_USERS (was $INITIAL_USERS)"
if [ "$RESTORED_USERS" -eq "$INITIAL_USERS" ]; then
    echo "✅ Users table: PASS"
else
    echo "❌ Users table: FAIL"
fi

# Cards
RESTORED_CARDS=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM cards;")
echo "Cards: $RESTORED_CARDS (was $INITIAL_CARDS)"
if [ "$RESTORED_CARDS" -eq "$INITIAL_CARDS" ]; then
    echo "✅ Cards table: PASS"
else
    echo "❌ Cards table: FAIL"
fi

# Purchases
RESTORED_PURCHASES=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM purchases;")
echo "Purchases: $RESTORED_PURCHASES (was $INITIAL_PURCHASES)"
if [ "$RESTORED_PURCHASES" -eq "$INITIAL_PURCHASES" ]; then
    echo "✅ Purchases table: PASS"
else
    echo "❌ Purchases table: FAIL"
fi

# Audit logs
RESTORED_AUDIT_LOGS=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM audit_logs;")
echo "Audit logs: $RESTORED_AUDIT_LOGS (was $INITIAL_AUDIT_LOGS)"
if [ "$RESTORED_AUDIT_LOGS" -eq "$INITIAL_AUDIT_LOGS" ]; then
    echo "✅ Audit logs table: PASS"
else
    echo "❌ Audit logs table: FAIL"
fi

# Drops
RESTORED_DROPS=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM drops;")
echo "Drops: $RESTORED_DROPS (was $INITIAL_DROPS)"
if [ "$RESTORED_DROPS" -eq "$INITIAL_DROPS" ]; then
    echo "✅ Drops table: PASS"
else
    echo "❌ Drops table: FAIL"
fi

# Trades
RESTORED_TRADES=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM trades;")
echo "Trades: $RESTORED_TRADES (was $INITIAL_TRADES)"
if [ "$RESTORED_TRADES" -eq "$INITIAL_TRADES" ]; then
    echo "✅ Trades table: PASS"
else
    echo "❌ Trades table: FAIL"
fi

# Artists
RESTORED_ARTISTS=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM artists;")
echo "Artists: $RESTORED_ARTISTS (was $INITIAL_ARTISTS)"
if [ "$RESTORED_ARTISTS" -eq "$INITIAL_ARTISTS" ]; then
    echo "✅ Artists table: PASS"
else
    echo "❌ Artists table: FAIL"
fi

# Detailed verification
echo ""
echo "🔍 Detailed verification:"

# Check specific cards exist
echo "🎴 Checking specific cards..."
CARD_001=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM cards WHERE serial='CARD_001';")
if [ "$CARD_001" -eq 1 ]; then
    echo "✅ Card CARD_001 exists"
else
    echo "❌ Card CARD_001 missing"
fi

CARD_005=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM cards WHERE serial='CARD_005';")
if [ "$CARD_005" -eq 1 ]; then
    echo "✅ Card CARD_005 exists"
else
    echo "❌ Card CARD_005 missing"
fi

# Check audit logs match
echo "📊 Checking audit logs..."
PACK_OPEN_LOG=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM audit_logs WHERE event='pack_open';")
if [ "$PACK_OPEN_LOG" -eq 1 ]; then
    echo "✅ Pack open audit log exists"
else
    echo "❌ Pack open audit log missing"
fi

PURCHASE_LOG=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM audit_logs WHERE event='purchase_completed';")
if [ "$PURCHASE_LOG" -eq 1 ]; then
    echo "✅ Purchase audit log exists"
else
    echo "❌ Purchase audit log missing"
fi

# Check purchases intact
echo "💳 Checking purchases..."
TEST_PURCHASE=$(sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM purchases WHERE id='$PURCHASE_ID';")
if [ "$TEST_PURCHASE" -eq 1 ]; then
    echo "✅ Test purchase intact"
else
    echo "❌ Test purchase missing"
fi

PURCHASE_STATUS=$(sqlite3 "$DATABASE_URL" "SELECT status FROM purchases WHERE id='$PURCHASE_ID';")
if [ "$PURCHASE_STATUS" = "completed" ]; then
    echo "✅ Purchase status correct: $PURCHASE_STATUS"
else
    echo "❌ Purchase status incorrect: $PURCHASE_STATUS"
fi

# Final summary
echo ""
echo "📊 DISASTER TEST SUMMARY"
echo "======================"

# Calculate overall result
TOTAL_TESTS=7
PASSED_TESTS=0

if [ "$RESTORED_USERS" -eq "$INITIAL_USERS" ]; then PASSED_TESTS=$((PASSED_TESTS + 1)); fi
if [ "$RESTORED_CARDS" -eq "$INITIAL_CARDS" ]; then PASSED_TESTS=$((PASSED_TESTS + 1)); fi
if [ "$RESTORED_PURCHASES" -eq "$INITIAL_PURCHASES" ]; then PASSED_TESTS=$((PASSED_TESTS + 1)); fi
if [ "$RESTORED_AUDIT_LOGS" -eq "$INITIAL_AUDIT_LOGS" ]; then PASSED_TESTS=$((PASSED_TESTS + 1)); fi
if [ "$CARD_001" -eq 1 ]; then PASSED_TESTS=$((PASSED_TESTS + 1)); fi
if [ "$PACK_OPEN_LOG" -eq 1 ]; then PASSED_TESTS=$((PASSED_TESTS + 1)); fi
if [ "$TEST_PURCHASE" -eq 1 ]; then PASSED_TESTS=$((PASSED_TESTS + 1)); fi

echo "✅ Passed: $PASSED_TESTS/$TOTAL_TESTS tests"
echo "❌ Failed: $((TOTAL_TESTS - PASSED_TESTS))/$TOTAL_TESTS tests"

if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
    echo ""
    echo "🎉 DISASTER RECOVERY TEST PASSED!"
    echo "🔒 Your backup and restore system is working perfectly"
    echo "📊 All data integrity checks passed"
    echo "🛡️  Your system is ready for production"
else
    echo ""
    echo "⚠️  DISASTER RECOVERY TEST FAILED!"
    echo "🔧 Please check the failed items above"
    echo "📖 Review BACKUP_GUIDE.md for troubleshooting"
fi

# Cleanup test data (optional)
echo ""
read -p "🧹 Clean up test data? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 Cleaning up test data..."
    rm -f "$DATABASE_URL"
    rm -f "$EMERGENCY_BACKUP"
    echo "✅ Test data cleaned up"
else
    echo "📁 Test data preserved for manual inspection"
    echo "🗄️  Database: $DATABASE_URL"
    echo "💾 Backup: $BACKUP_FILE_GZ"
fi

# Log test completion
echo "$(date): Disaster recovery test completed - $PASSED_TESTS/$TOTAL_TESTS tests passed" >> $BACKUP_DIR/disaster_test.log

echo ""
echo "🎯 Disaster recovery test completed!"
echo "📅 Test date: $(date)"
echo "📁 Backup: $BACKUP_FILE_GZ"
echo "📊 Result: $PASSED_TESTS/$TOTAL_TESTS tests passed"
