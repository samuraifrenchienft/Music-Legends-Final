-- ========================================
-- DATABASE ROLLBACK SCRIPTS
-- ========================================

-- SQLite Rollback
DROP TABLE IF EXISTS purchase_cards;
DROP TABLE IF EXISTS purchases;

-- PostgreSQL Rollback
DROP TABLE IF EXISTS purchase_cards;
DROP TABLE IF EXISTS purchases;
DROP FUNCTION IF EXISTS set_updated_at();

-- MySQL Rollback
DROP TABLE IF EXISTS purchase_cards;
DROP TABLE IF EXISTS purchases;

-- ========================================
-- USAGE INSTRUCTIONS
-- ========================================

-- For SQLite:
-- sqlite3 music_legends.db < rollback.sql

-- For PostgreSQL:
-- psql -U username -d database_name < rollback.sql

-- For MySQL:
-- mysql -u username -p database_name < rollback.sql
