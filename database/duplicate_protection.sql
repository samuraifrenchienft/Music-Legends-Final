-- duplicate_protection.sql
-- Database schema updates for duplicate protection and quantity tracking

-- Add quantity column to user_cards table
ALTER TABLE user_cards ADD COLUMN quantity INTEGER DEFAULT 1;

-- Add first_acquired_at column to track when user first got the card
ALTER TABLE user_cards ADD COLUMN first_acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Update existing records to have quantity = 1
UPDATE user_cards SET quantity = 1 WHERE quantity IS NULL;

-- Create index for faster duplicate lookups
CREATE INDEX IF NOT EXISTS idx_user_cards_lookup ON user_cards(user_id, card_id);

-- Add dust system for duplicate cards
CREATE TABLE IF NOT EXISTS user_dust (
    user_id INTEGER PRIMARY KEY,
    dust_amount INTEGER DEFAULT 0,
    total_dust_earned INTEGER DEFAULT 0,
    total_dust_spent INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Dust conversion rates by rarity
-- Common: 10 dust
-- Rare: 25 dust
-- Epic: 50 dust
-- Legendary: 100 dust
-- Mythic: 250 dust

-- Create dust transaction log
CREATE TABLE IF NOT EXISTS dust_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    transaction_type TEXT, -- 'earned_duplicate', 'spent_craft', 'spent_boost'
    card_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
