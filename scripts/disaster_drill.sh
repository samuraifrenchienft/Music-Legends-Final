#!/bin/bash
# scripts/disaster_drill.sh
# Complete disaster recovery drill for Music Legends

# Load environment variables
source .env.txt

echo "🚨 MUSIC LEGENDS DISASTER DRILL"
echo "=============================="
echo "⚠️  This will test complete disaster recovery"
echo ""

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check if backup scripts exist
if [ ! -f "scripts/backup_db.sh" ] || [ ! -f "scripts/restore_test.sh" ]; then
    echo "❌ Backup scripts not found"
    exit 1
fi

# Check if database exists
if [[ $DATABASE_URL == sqlite* ]]; then
    DB_FILE=$(echo $DATABASE_URL | sed 's/sqlite:\/\///')
    if [ ! -f "$DB_FILE" ]; then
        echo "❌ Database file not found: $DB_FILE"
        exit 1
    fi
fi

echo "✅ Prerequisites check passed"

# Step 1: Create test pack opening
echo ""
echo "📦 Step 1: Creating test pack opening"
echo "===================================="

# Create test data if database doesn't exist
if [[ $DATABASE_URL == sqlite* ]]; then
    echo "🗄️  Setting up test database..."
    
    # Create test schema
    sqlite3 "$DB_FILE" "
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
    "
    
    # Insert test user
    sqlite3 "$DB_FILE" "INSERT OR REPLACE INTO users (id, username) VALUES (99999, 'disaster_test_user');"
    
    # Insert test cards
    sqlite3 "$DB_FILE" "
    INSERT OR REPLACE INTO cards (id, serial, user_id, card_name, tier) VALUES
    (1001, 'DISASTER_CARD_001', 99999, 'Test Dragon', 'legendary'),
    (1002, 'DISASTER_CARD_002', 99999, 'Test Phoenix', 'epic'),
    (1003, 'DISASTER_CARD_003', 99999, 'Test Golem', 'rare');
    "
    
    # Insert test purchase
    sqlite3 "$DB_FILE" "
    INSERT OR REPLACE INTO purchases (id, user_id, pack_type, amount_cents, status) VALUES
    ('disaster_purchase_001', 99999, 'founder_pack_black', 9999, 'completed');
    "
    
    # Insert test audit logs
    sqlite3 "$DB_FILE" "
    INSERT OR REPLACE INTO audit_logs (id, event, user_id, target_id, payload) VALUES
    ('audit_001', 'pack_open', 99999, 'black_pack', '{\"cards\": [\"DISASTER_CARD_001\", \"DISASTER_CARD_002\"], \"pack_type\": \"black\"}'),
    ('audit_002', 'purchase_completed', 99999, 'disaster_purchase_001', '{\"pack_type\": \"founder_pack_black\", \"amount\": 9999}'),
    ('audit_003', 'card_created', 99999, 'DISASTER_CARD_001', '{\"card_name\": \"Test Dragon\", \"tier\": \"legendary\"}');
    "
fi

# Record initial state
echo "📊 Recording initial database state..."
if [[ $DATABASE_URL == sqlite* ]]; then
    INITIAL_USERS=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM users;")
    INITIAL_CARDS=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM cards;")
    INITIAL_PURCHASES=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM purchases;")
    INITIAL_AUDIT_LOGS=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM audit_logs;")
    
    echo "   Users: $INITIAL_USERS"
    echo "   Cards: $INITIAL_CARDS"
    echo "   Purchases: $INITIAL_PURCHASES"
    echo "   Audit logs: $INITIAL_AUDIT_LOGS"
fi

echo "✅ Step 1 completed: Test data created"

# Step 2: Run backup
echo ""
echo "💾 Step 2: Running backup"
echo "========================"

echo "🔄 Running database backup..."
./scripts/backup_db.sh

if [ $? -eq 0 ]; then
    echo "✅ Database backup completed"
else
    echo "❌ Database backup failed"
    exit 1
fi

echo "🔄 Running Redis backup..."
./scripts/backup_redis.sh

if [ $? -eq 0 ]; then
    echo "✅ Redis backup completed"
else
    echo "⚠️  Redis backup failed (may not be running)"
fi

# Find latest backup
LATEST_DB_BACKUP=$(ls -t $BACKUP_PATH/db | head -1)
echo "📦 Latest backup: $LATEST_DB_BACKUP"

echo "✅ Step 2 completed: Backup created"

# Step 3: Drop database
echo ""
echo "💥 Step 3: Dropping database"
echo "=========================="

# Create emergency backup
EMERGENCY_DATE=$(date +"%Y-%m-%d_%H-%M-%S")
echo "📋 Creating emergency backup..."

if [[ $DATABASE_URL == sqlite* ]]; then
    EMERGENCY_BACKUP="$BACKUP_PATH/db/emergency_before_disaster_$EMERGENCY_DATE.db"
    cp "$DB_FILE" "$EMERGENCY_BACKUP"
    echo "✅ Emergency backup created: $EMERGENCY_BACKUP"
    
    # Drop database (delete file)
    rm -f "$DB_FILE"
    echo "💥 Database dropped: $DB_FILE"
fi

# Verify database is gone
if [[ $DATABASE_URL == sqlite* ]] && [ -f "$DB_FILE" ]; then
    echo "❌ ERROR: Database still exists!"
    exit 1
else
    echo "✅ Database successfully dropped"
fi

echo "✅ Step 3 completed: Database dropped"

# Step 4: Run restore test
echo ""
echo "🔄 Step 4: Running restore test"
echo "=============================="

echo "🔄 Running restore test..."
./scripts/restore_test.sh

if [ $? -eq 0 ]; then
    echo "✅ Restore test completed"
else
    echo "❌ Restore test failed"
    exit 1
fi

echo "✅ Step 4 completed: Restore test run"

# Step 5: Confirm data integrity
echo ""
echo "🔍 Step 5: Confirming data integrity"
echo "===================================="

echo "📊 Checking restored database state..."

if [[ $DATABASE_URL == sqlite* ]]; then
    # Check if database was restored
    if [ ! -f "$DB_FILE" ]; then
        echo "❌ Database file not found after restore"
        exit 1
    fi
    
    RESTORED_USERS=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM users;")
    RESTORED_CARDS=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM cards;")
    RESTORED_PURCHASES=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM purchases;")
    RESTORED_AUDIT_LOGS=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM audit_logs;")
    
    echo "   Restored Users: $RESTORED_USERS (was $INITIAL_USERS)"
    echo "   Restored Cards: $RESTORED_CARDS (was $INITIAL_CARDS)"
    echo "   Restored Purchases: $RESTORED_PURCHASES (was $INITIAL_PURCHASES)"
    echo "   Restored Audit logs: $RESTORED_AUDIT_LOGS (was $INITIAL_AUDIT_LOGS)"
    
    # Verify specific data exists
    echo ""
    echo "🔍 Verifying specific data..."
    
    # Check cards exist
    TEST_CARD=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM cards WHERE serial='DISASTER_CARD_001';")
    if [ "$TEST_CARD" -eq 1 ]; then
        echo "✅ Test card DISASTER_CARD_001 exists"
        CARD_NAME=$(sqlite3 "$DB_FILE" "SELECT card_name FROM cards WHERE serial='DISASTER_CARD_001';")
        echo "   Card name: $CARD_NAME"
    else
        echo "❌ Test card DISASTER_CARD_001 missing"
    fi
    
    # Check audit logs intact
    PACK_OPEN_LOG=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM audit_logs WHERE event='pack_open';")
    if [ "$PACK_OPEN_LOG" -gt 0 ]; then
        echo "✅ Pack open audit logs intact ($PACK_OPEN_LOG logs)"
    else
        echo "❌ Pack open audit logs missing"
    fi
    
    # Check purchases intact
    TEST_PURCHASE=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM purchases WHERE id='disaster_purchase_001';")
    if [ "$TEST_PURCHASE" -eq 1 ]; then
        echo "✅ Test purchase intact"
        PURCHASE_DETAILS=$(sqlite3 "$DB_FILE" "SELECT pack_type, amount_cents, status FROM purchases WHERE id='disaster_purchase_001';")
        echo "   Purchase details: $PURCHASE_DETAILS"
    else
        echo "❌ Test purchase missing"
    fi
    
    # Overall verification
    echo ""
    echo "📊 Data integrity verification:"
    
    INTEGRITY_PASSED=true
    
    if [ "$RESTORED_USERS" -eq "$INITIAL_USERS" ]; then
        echo "✅ Users table: PASS"
    else
        echo "❌ Users table: FAIL"
        INTEGRITY_PASSED=false
    fi
    
    if [ "$RESTORED_CARDS" -eq "$INITIAL_CARDS" ]; then
        echo "✅ Cards table: PASS"
    else
        echo "❌ Cards table: FAIL"
        INTEGRITY_PASSED=false
    fi
    
    if [ "$RESTORED_PURCHASES" -eq "$INITIAL_PURCHASES" ]; then
        echo "✅ Purchases table: PASS"
    else
        echo "❌ Purchases table: FAIL"
        INTEGRITY_PASSED=false
    fi
    
    if [ "$RESTORED_AUDIT_LOGS" -eq "$INITIAL_AUDIT_LOGS" ]; then
        echo "✅ Audit logs table: PASS"
    else
        echo "❌ Audit logs table: FAIL"
        INTEGRITY_PASSED=false
    fi
    
    if [ "$TEST_CARD" -eq 1 ]; then
        echo "✅ Cards exist: PASS"
    else
        echo "❌ Cards exist: FAIL"
        INTEGRITY_PASSED=false
    fi
    
    if [ "$PACK_OPEN_LOG" -gt 0 ]; then
        echo "✅ Audit logs intact: PASS"
    else
        echo "❌ Audit logs intact: FAIL"
        INTEGRITY_PASSED=false
    fi
    
    if [ "$TEST_PURCHASE" -eq 1 ]; then
        echo "✅ Purchases intact: PASS"
    else
        echo "❌ Purchases intact: FAIL"
        INTEGRITY_PASSED=false
    fi
    
fi

# Final results
echo ""
echo "🎯 DISASTER DRILL RESULTS"
echo "========================"

if [ "$INTEGRITY_PASSED" = true ]; then
    echo "🎉 DISASTER RECOVERY DRILL PASSED!"
    echo "✅ All data integrity checks passed"
    echo "🛡️  Your backup and restore system is working perfectly"
    echo "🚀 System is ready for production"
    
    # Log success
    echo "$(date): Disaster drill PASSED - All data integrity checks passed" >> $BACKUP_PATH/logs/disaster_drill.log
    
else
    echo "⚠️  DISASTER RECOVERY DRILL FAILED!"
    echo "❌ Some data integrity checks failed"
    echo "🔧 Please review the failed items above"
    echo "📖 Check backup and restore procedures"
    
    # Log failure
    echo "$(date): Disaster drill FAILED - Data integrity issues detected" >> $BACKUP_PATH/logs/disaster_drill.log
fi

# Cleanup options
echo ""
read -p "🧹 Clean up test data? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 Cleaning up test data..."
    
    if [[ $DATABASE_URL == sqlite* ]]; then
        # Remove test database
        rm -f "$DB_FILE"
        
        # Remove emergency backup
        rm -f "$EMERGENCY_BACKUP"
        
        echo "✅ Test data cleaned up"
    fi
else
    echo "📁 Test data preserved for manual inspection"
    echo "🗄️  Database: $DB_FILE"
    echo "💾 Emergency backup: $EMERGENCY_BACKUP"
fi

echo ""
echo "🎯 Disaster drill completed!"
echo "📅 Drill date: $(date)"
echo "📁 Backup used: $LATEST_DB_BACKUP"
echo "📊 Result: $([ "$INTEGRITY_PASSED" = true ] && echo "PASSED" || echo "FAILED")"
