# 🗄️ Database Backup & Restore Guide

This guide explains how to set up and use PostgreSQL client tools for database backups and restores.

## 🚀 Quick Setup

### For Local Development

#### Windows
1. **Download PostgreSQL installer** from [postgresql.org](https://www.postgresql.org/download/windows/)
2. During installation, make sure **"Command Line Tools"** is selected
3. Add PostgreSQL bin folder to your PATH (usually `C:\Program Files\PostgreSQL\15\bin`)
4. Test installation: `pg_dump --version`

#### Linux (Ubuntu/Debian)
```bash
# Install just the client tools (no server)
sudo apt update
sudo apt install postgresql-client

# Test installation
pg_dump --version
```

#### macOS
```bash
# Using Homebrew
brew install postgresql

# Test installation
pg_dump --version
```

## 🛠️ What You Get

Installing PostgreSQL client tools provides these essential utilities:

- **pg_dump:** Creates database backups (exports data and structure)
- **pg_restore:** Restores databases from backup files
- **psql:** Interactive PostgreSQL command line client
- **pg_dumpall:** Backs up entire PostgreSQL cluster
- **createdb/dropdb:** Database creation/deletion utilities

## 📋 Available Scripts

### 1. Automated Backup Script

#### Linux/macOS: `scripts/backup_database.sh`
```bash
# Make executable
chmod +x scripts/backup_database.sh

# Run with environment variables
export DB_NAME="music_legends"
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_USER="postgres"
export DB_PASSWORD="your_password"
export BACKUP_DIR="/path/to/backups"

./scripts/backup_database.sh
```

#### Windows: `scripts/backup_database.bat`
```batch
# Set environment variables
set DB_NAME=music_legends
set DB_HOST=localhost
set DB_PORT=5432
set DB_USER=postgres
set DB_PASSWORD=your_password
set BACKUP_DIR=C:\backups\music_legends

# Run backup
scripts\backup_database.bat
```

### 2. Database Restore Script: `scripts/restore_database.py`
```bash
# Restore from backup
python scripts/restore_database.py backup_file.sql.gz

# With custom database settings
python scripts/restore_database.py backup_file.sql.gz \
    --db-name music_legends \
    --db-host localhost \
    --db-port 5432 \
    --db-user postgres \
    --db-password your_password
```

## 🐳 Docker/Railway Setup

PostgreSQL client tools are now included in the deployment:

### Dockerfile
```dockerfile
# PostgreSQL client tools are now installed
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*
```

### Nixpacks
```toml
[phases.setup]
nixPkgs = ["python311", "gcc", "postgresql"]
```

## 🔄 Manual Backup Commands

### Create Backup
```bash
# Basic backup
pg_dump -h localhost -U postgres -d music_legends > backup.sql

# Compressed backup
pg_dump -h localhost -U postgres -d music_legends | gzip > backup.sql.gz

# Custom format (recommended for large databases)
pg_dump -h localhost -U postgres -d music_legends -Fc > backup.dump
```

### Restore Database
```bash
# From SQL file
psql -h localhost -U postgres -d music_legends < backup.sql

# From compressed file
gunzip -c backup.sql.gz | psql -h localhost -U postgres -d music_legends

# From custom format
pg_restore -h localhost -U postgres -d music_legends backup.dump
```

## 🌐 Environment Variables

Configure these environment variables for automated scripts:

```bash
# Database Configuration
DB_NAME=music_legends          # Database name
DB_HOST=localhost              # Database host
DB_PORT=5432                   # Database port
DB_USER=postgres               # Database username
DB_PASSWORD=your_password       # Database password

# Backup Configuration
BACKUP_DIR=/path/to/backups    # Backup storage directory
```

## 📅 Automated Backups

### Using Cron (Linux/macOS)
```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /path/to/scripts/backup_database.sh

# Add weekly backup on Sundays at 3 AM
0 3 * * 0 /path/to/scripts/backup_database.sh
```

### Using Task Scheduler (Windows)
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to daily at 2 AM
4. Action: Start a program
5. Program: `scripts\backup_database.bat`

## 🚨 Railway Deployment

The backup scripts automatically detect Railway environment and copy backups to persistent storage:

```bash
# Railway automatically provides these
export RAILWAY_ENVIRONMENT=true
export BACKUP_DIR=/tmp/backups
```

## 📊 Backup File Management

### File Naming Convention
```
music_legends_backup_YYYYMMDD_HHMMSS.sql.gz
Example: music_legends_backup_20260201_143022.sql.gz
```

### Cleanup Policy
- Automated scripts keep backups for **7 days**
- Manual cleanup: `find /backups -name "*.sql.gz" -mtime +7 -delete`

### Backup Verification
```bash
# Check backup file integrity
gzip -t backup.sql.gz

# Preview backup contents
pg_restore --list backup.dump

# Check backup size
du -h backup.sql.gz
```

## 🔍 Troubleshooting

### Common Issues

1. **"pg_dump: command not found"**
   - Install PostgreSQL client tools
   - Check PATH environment variable

2. **"Connection refused"**
   - Verify database is running
   - Check host and port settings
   - Ensure firewall allows connection

3. **"Permission denied"**
   - Check database user permissions
   - Verify backup directory permissions

4. **"Out of memory"**
   - Use custom format for large databases
   - Increase available memory
   - Split backup into smaller parts

### Testing Your Installation
```bash
# Check if tools are installed
pg_dump --version
pg_restore --version
psql --version

# Test database connection
pg_isready -h localhost -p 5432

# Test backup creation
pg_dump -h localhost -U postgres -d music_legends > test_backup.sql
```

## 📞 Support

If you encounter issues:

1. Check PostgreSQL client tools are properly installed
2. Verify database connection settings
3. Ensure sufficient disk space for backups
4. Review script error messages for specific issues

---

**🔥 Your Music Legends bot now has robust database backup and restore capabilities!**
