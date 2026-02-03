# 🗄️ PostgreSQL Setup Guide for Railway

This guide will help you create all necessary database tables for the Music Legends bot on Railway's PostgreSQL.

## 🚀 Quick Setup Steps

### Step 1: Add PostgreSQL to Your Railway Service

1. **Go to your Railway project**
2. **Select your bot service**
3. **Click on "Variables" tab**
4. **Add a PostgreSQL database**:
   - Click "+ New Variable"
   - Select "PostgreSQL" from the dropdown
   - Railway will automatically add `DATABASE_URL`

### Step 2: Update Requirements

Make sure you have PostgreSQL support in your `requirements.txt`:

```txt
psycopg2-binary==2.9.7
```

### Step 3: Run the Setup Script

#### Option A: Run Locally (Recommended)
```bash
# Set DATABASE_URL from Railway
export DATABASE_URL="postgresql://username:password@host:port/database"

# Run the setup script
python setup_postgresql.py
```

#### Option B: Run on Railway
1. **Add setup script to your deployment**
2. **Run it via Railway console or temporary deployment**

### Step 4: Verify Tables Created

The setup script will create these tables:

| Table Name | Purpose |
|------------|---------|
| `users` | User profiles and stats |
| `cards` | Card catalog and ownership |
| `user_inventory` | Gold, XP, and assets |
| `card_collections` | User card collections |
| `creator_packs` | Custom pack information |
| `pack_purchases` | Purchase transactions |
| `battle_matches` | Battle history |
| `audit_logs` | Action logging |
| `server_settings` | Server configuration |
| `drops` | Drop system data |

## 🔧 Manual Setup (Alternative)

If you prefer to set up manually, connect to your Railway PostgreSQL and run these SQL commands:

### Connect to Railway PostgreSQL

```bash
# Get DATABASE_URL from Railway Variables
# Extract connection details:
# Host: your-db.railway.app
# Port: 5432 (usually)
# Database: railway
# Username: postgres
# Password: [from Railway]

# Connect using psql
psql "postgresql://username:password@host:port/database"
```

### Create Tables SQL

```sql
-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    discord_tag VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    total_battles INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    packs_opened INTEGER DEFAULT 0,
    victory_tokens INTEGER DEFAULT 0
);

-- Cards table
CREATE TABLE IF NOT EXISTS cards (
    card_id VARCHAR(255) PRIMARY KEY,
    type VARCHAR(50) NOT NULL DEFAULT 'artist',
    spotify_artist_id VARCHAR(255),
    spotify_track_id VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    image_url TEXT,
    spotify_url TEXT,
    youtube_url TEXT,
    rarity VARCHAR(50) NOT NULL,
    variant VARCHAR(100) DEFAULT 'Classic',
    era VARCHAR(100),
    impact INTEGER,
    skill INTEGER,
    longevity INTEGER,
    culture INTEGER,
    hype INTEGER,
    power INTEGER,
    serial VARCHAR(255),
    owner_id BIGINT,
    acquisition_source VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(user_id)
);

-- User inventory table
CREATE TABLE IF NOT EXISTS user_inventory (
    user_id BIGINT PRIMARY KEY,
    gold INTEGER DEFAULT 100,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    daily_streak INTEGER DEFAULT 0,
    last_daily_claim TIMESTAMP WITH TIME ZONE,
    premium_expires TIMESTAMP WITH TIME ZONE,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Card collections table
CREATE TABLE IF NOT EXISTS card_collections (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    card_id VARCHAR(255),
    acquired_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (card_id) REFERENCES cards(card_id),
    UNIQUE(user_id, card_id)
);

-- Creator packs table
CREATE TABLE IF NOT EXISTS creator_packs (
    pack_id VARCHAR(255) PRIMARY KEY,
    creator_id BIGINT,
    pack_name VARCHAR(255) NOT NULL,
    description TEXT,
    pack_size INTEGER DEFAULT 5,
    status VARCHAR(50) DEFAULT 'draft',
    cards_data TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP WITH TIME ZONE,
    total_purchases INTEGER DEFAULT 0,
    FOREIGN KEY (creator_id) REFERENCES users(user_id)
);

-- Pack purchases table
CREATE TABLE IF NOT EXISTS pack_purchases (
    purchase_id VARCHAR(255) PRIMARY KEY,
    pack_id VARCHAR(255),
    buyer_id BIGINT,
    amount_cents INTEGER,
    platform_cents INTEGER,
    creator_cents INTEGER,
    payment_id VARCHAR(255),
    received_cards TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pack_id) REFERENCES creator_packs(pack_id),
    FOREIGN KEY (buyer_id) REFERENCES users(user_id)
);

-- Battle matches table
CREATE TABLE IF NOT EXISTS battle_matches (
    match_id VARCHAR(255) PRIMARY KEY,
    player_a_id BIGINT,
    player_b_id BIGINT,
    wager_level VARCHAR(50),
    wager_amount INTEGER,
    status VARCHAR(50) DEFAULT 'pending',
    winner_id BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    battle_data TEXT,
    FOREIGN KEY (player_a_id) REFERENCES users(user_id),
    FOREIGN KEY (player_b_id) REFERENCES users(user_id),
    FOREIGN KEY (winner_id) REFERENCES users(user_id)
);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    event VARCHAR(255),
    user_id BIGINT,
    target_id VARCHAR(255),
    payload TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Server settings table
CREATE TABLE IF NOT EXISTS server_settings (
    server_id BIGINT PRIMARY KEY,
    premium_expires TIMESTAMP WITH TIME ZONE,
    settings TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Drops table
CREATE TABLE IF NOT EXISTS drops (
    drop_id VARCHAR(255) PRIMARY KEY,
    channel_id BIGINT,
    server_id BIGINT,
    initiator_user_id BIGINT,
    cards TEXT,
    drop_type VARCHAR(50) DEFAULT 'random',
    expires_at TIMESTAMP WITH TIME ZONE,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (initiator_user_id) REFERENCES users(user_id)
);
```

### Create Indexes

```sql
-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_cards_owner ON cards(owner_id);
CREATE INDEX IF NOT EXISTS idx_cards_rarity ON cards(rarity);
CREATE INDEX IF NOT EXISTS idx_card_collections_user ON card_collections(user_id);
CREATE INDEX IF NOT EXISTS idx_battle_matches_players ON battle_matches(player_a_id, player_b_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event ON audit_logs(event);
CREATE INDEX IF NOT EXISTS idx_pack_purchases_buyer ON pack_purchases(buyer_id);
CREATE INDEX IF NOT EXISTS idx_creator_packs_creator ON creator_packs(creator_id);
CREATE INDEX IF NOT EXISTS idx_creator_packs_status ON creator_packs(status);
CREATE INDEX IF NOT EXISTS idx_drops_server ON drops(server_id);
CREATE INDEX IF NOT EXISTS idx_drops_expires ON drops(expires_at);
CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active);
CREATE INDEX IF NOT EXISTS idx_cards_created_at ON cards(created_at);
```

## 🔍 Verify Setup

Check that tables were created:

```sql
-- List all tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;

-- Check table counts
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats 
WHERE schemaname = 'public'
ORDER BY tablename;
```

## 🚨 Troubleshooting

### Common Issues

1. **"Connection refused"**
   - Check DATABASE_URL is correct
   - Verify Railway PostgreSQL is running

2. **"Permission denied"**
   - Check database user permissions
   - Verify DATABASE_URL credentials

3. **"Table already exists"**
   - This is normal - the script uses IF NOT EXISTS
   - Tables won't be recreated

4. **"Foreign key constraint"**
   - Make sure tables are created in order
   - Use the setup script to handle dependencies

### Test Connection

```python
import psycopg2
import os

# Test connection
try:
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    print("✅ PostgreSQL connection successful!")
    
    # List tables
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        print(f"📋 Found {len(tables)} tables")
        for table in tables:
            print(f"  📝 {table[0]}")
    
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

## 📋 Environment Variables

Make sure these are set in Railway:

```env
DATABASE_URL=postgresql://username:password@host:port/database
DB_NAME=railway
DB_HOST=your-db.railway.app
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
```

## 🎯 Next Steps

1. ✅ **Add PostgreSQL** to Railway service
2. ✅ **Run setup script** to create tables
3. ✅ **Verify tables** are created
4. ✅ **Restart bot** to use PostgreSQL
5. ✅ **Test commands** to ensure everything works

---

**🔥 Your Music Legends bot will now use PostgreSQL on Railway with all tables properly created!**
