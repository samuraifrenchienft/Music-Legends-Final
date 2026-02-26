-- SQLite schema for Founder Packs purchases
CREATE TABLE purchases (
    id CHAR(36) PRIMARY KEY,

    user_id BIGINT NOT NULL,
    pack_type VARCHAR(50) NOT NULL,

    idempotency_key VARCHAR(100) NOT NULL UNIQUE,

    status VARCHAR(20) NOT NULL DEFAULT 'pending',

    amount_cents INT,
    currency VARCHAR(10) DEFAULT 'USD',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP 
        ON UPDATE CURRENT_TIMESTAMP
);

-- Purchase-Cards relationship table
CREATE TABLE purchase_cards (
    purchase_id CHAR(36) REFERENCES purchases(id),
    card_id CHAR(36) REFERENCES cards(id),

    PRIMARY KEY (purchase_id, card_id)
);

-- Drops table
CREATE TABLE drops (
    id CHAR(36) PRIMARY KEY,

    owner_id BIGINT,                    -- NULL for unclaimed drops
    card_ids TEXT,                      -- JSON array of card IDs
    expires_at DATETIME NOT NULL,
    resolved BOOLEAN DEFAULT FALSE,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Trades table
CREATE TABLE trades (
    id CHAR(36) PRIMARY KEY,

    user_a BIGINT NOT NULL,
    user_b BIGINT NOT NULL,

    cards_a TEXT DEFAULT "[]",         -- JSON array of card IDs from user A
    cards_b TEXT DEFAULT "[]",         -- JSON array of card IDs from user B

    gold_a INTEGER DEFAULT 0,          -- Gold offered by user A
    gold_b INTEGER DEFAULT 0,          -- Gold offered by user B

    status VARCHAR(20) DEFAULT "pending", -- pending, complete, cancelled
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL
);

-- Audit logs table
CREATE TABLE audit_logs (
    id CHAR(36) PRIMARY KEY,

    event VARCHAR(40) NOT NULL,

    user_id BIGINT,
    target_id VARCHAR(64),

    payload TEXT,                       -- JSON string for SQLite

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_purchases_user ON purchases(user_id);
CREATE INDEX idx_purchases_status ON purchases(status);
CREATE INDEX idx_purchases_pack_type ON purchases(pack_type);
CREATE INDEX idx_purchase_cards_purchase ON purchase_cards(purchase_id);
CREATE INDEX idx_purchase_cards_card ON purchase_cards(card_id);

-- Drops indexes
CREATE INDEX idx_drops_owner ON drops(owner_id);
CREATE INDEX idx_drops_expires ON drops(expires_at);
CREATE INDEX idx_drops_resolved ON drops(resolved);
CREATE INDEX idx_drops_unclaimed ON drops(owner_id) WHERE owner_id IS NULL;

-- Trades indexes
CREATE INDEX idx_trades_user_a ON trades(user_a);
CREATE INDEX idx_trades_user_b ON trades(user_b);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_expires ON trades(expires_at);
CREATE INDEX idx_trades_pending ON trades(status) WHERE status = "pending";

-- Audit logs indexes
CREATE INDEX idx_audit_event ON audit_logs(event);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at);
CREATE INDEX idx_audit_target ON audit_logs(target_id);

-- Sample queries for SQLite
-- Get user's purchase history
-- SELECT * FROM purchases WHERE user_id = ? ORDER BY created_at DESC;

-- Get pending purchases
-- SELECT * FROM purchases WHERE status = 'pending';

-- Check for duplicate payment
-- SELECT * FROM purchases WHERE idempotency_key = ?;

-- Get cards from a specific purchase
-- SELECT c.* FROM cards c
-- JOIN purchase_cards pc ON c.id = pc.card_id
-- WHERE pc.purchase_id = ?;

-- Get purchase history with cards
-- SELECT p.*, c.card_name, c.rarity FROM purchases p
-- JOIN purchase_cards pc ON p.id = pc.purchase_id
-- JOIN cards c ON pc.card_id = c.id
-- WHERE p.user_id = ? ORDER BY p.created_at DESC;

-- Drop queries
-- Find unclaimed drops
-- SELECT * FROM drops WHERE owner_id IS NULL AND resolved = FALSE AND expires_at > NOW();

-- Claim a drop
-- UPDATE drops SET owner_id = ?, resolved = TRUE WHERE id = ? AND owner_id IS NULL;

-- Get user's claimed drops
-- SELECT * FROM drops WHERE owner_id = ? AND resolved = TRUE;

-- Clean up expired drops
-- DELETE FROM drops WHERE expires_at <= NOW() AND resolved = FALSE;

-- Trade queries
-- Get pending trades for user
-- SELECT * FROM trades WHERE status = 'pending' AND (user_a = ? OR user_b = ?);

-- Get trade by ID
-- SELECT * FROM trades WHERE id = ?;

-- Cancel expired trades
-- UPDATE trades SET status = 'cancelled' WHERE status = 'pending' AND expires_at <= NOW();

-- Create new trade
-- INSERT INTO trades (id, user_a, user_b, cards_a, cards_b, gold_a, gold_b, expires_at)
-- VALUES (?, ?, ?, ?, ?, ?, ?, ?);

-- Complete trade
-- UPDATE trades SET status = 'complete' WHERE id = ?;

-- Audit queries
-- Record audit log
-- INSERT INTO audit_logs (id, event, user_id, target_id, payload) VALUES (?, ?, ?, ?, ?);

-- Get user activity
-- SELECT * FROM audit_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT 50;

-- Get event logs
-- SELECT * FROM audit_logs WHERE event = ? ORDER BY created_at DESC LIMIT 100;

-- Get recent logs
-- SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 100;

-- Search audit logs
-- SELECT * FROM audit_logs WHERE event LIKE ? AND created_at >= ? ORDER BY created_at DESC;

-- Insert new purchase
-- INSERT INTO purchases (id, user_id, pack_type, idempotency_key, amount_cents, currency)
-- VALUES (?, ?, ?, ?, ?, ?);

-- Update purchase status
-- UPDATE purchases SET status = 'delivered' WHERE idempotency_key = ?;

-- Add cards to purchase
-- INSERT INTO purchase_cards (purchase_id, card_id) VALUES (?, ?);

-- Create new drop
-- INSERT INTO drops (id, card_ids, expires_at) VALUES (?, ?, ?);

-- ========================================
-- ROLLBACK SCRIPTS
-- ========================================

-- SQLite Rollback
DROP TABLE IF EXISTS purchase_cards;
DROP TABLE IF EXISTS purchases;
DROP TABLE IF EXISTS drops;
DROP TABLE IF EXISTS trades;
DROP TABLE IF EXISTS audit_logs;

-- PostgreSQL Rollback
-- DROP TABLE IF EXISTS purchase_cards;
-- DROP TABLE IF EXISTS purchases;
-- DROP TABLE IF EXISTS drops;
-- DROP TABLE IF EXISTS trades;
-- DROP TABLE IF EXISTS audit_logs;
-- DROP FUNCTION IF EXISTS set_updated_at();

-- MySQL Rollback
-- DROP TABLE IF EXISTS purchase_cards;
-- DROP TABLE IF EXISTS purchases;
-- DROP TABLE IF EXISTS drops;
-- DROP TABLE IF EXISTS trades;
-- DROP TABLE IF EXISTS audit_logs;
