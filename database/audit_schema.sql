-- database/audit_schema.sql
-- Minimal audit logging schema for Music Legends

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,  -- UUID as string for compatibility
    event TEXT NOT NULL,
    user_id INTEGER,
    target_id TEXT,
    payload TEXT,  -- JSON string
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_audit_logs_event ON audit_logs(event);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_user ON audit_logs(event, user_id);
