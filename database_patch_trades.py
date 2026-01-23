"""
Quick patch to add missing trades table to database
Run this once to fix the cron job error
"""
import sqlite3

def add_trades_table():
    """Add trades table for active pending trades"""
    conn = sqlite3.connect("music_legends.db")
    cursor = conn.cursor()
    
    # Create trades table for active/pending trades
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            trade_id TEXT PRIMARY KEY,
            initiator_user_id INTEGER,
            receiver_user_id INTEGER,
            initiator_cards TEXT, -- JSON array
            receiver_cards TEXT, -- JSON array
            gold_from_initiator INTEGER DEFAULT 0,
            gold_from_receiver INTEGER DEFAULT 0,
            dust_from_initiator INTEGER DEFAULT 0,
            dust_from_receiver INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending', -- pending, completed, expired, cancelled
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            expired_at TIMESTAMP,
            FOREIGN KEY (initiator_user_id) REFERENCES users(user_id),
            FOREIGN KEY (receiver_user_id) REFERENCES users(user_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Trades table added successfully!")

if __name__ == "__main__":
    add_trades_table()
