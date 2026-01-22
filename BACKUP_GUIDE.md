# BACKUP AND RECOVERY GUIDE

## 🗄️ Database Backup Strategy

### What Must Be Backed Up

#### Primary Database Tables (Source of Truth)
- **users** - User accounts and profiles
- **cards** - All card instances and metadata
- **purchases** - Founder Packs and transactions
- **trades** - Trade history and escrow data
- **audit_logs** - Complete audit trail
- **drops** - Drop system data
- **artists** - Artist information and royalties

#### Redis Data (Session and Queue State)
- **queue state** - RQ job queue data
- **rate limiter keys** - User rate limiting state
- **session data** - Temporary session information
- **locks** - Distributed locks (can be lost, but better to backup)

## 🚀 Daily Backup Script

### Automated Backup Script
```bash
#!/bin/bash
# scripts/backup_db.sh

DATE=$(date +"%Y-%m-%d")
BACKUP_DIR="backups"
DATABASE_URL=${DATABASE_URL:-"music_legends.db"}

# SQLite backup
if [[ $DATABASE_URL == *.db ]]; then
    cp "$DATABASE_URL" "$BACKUP_DIR/db_$DATE.db"
fi

# PostgreSQL backup
if [[ $DATABASE_URL == postgres* ]]; then
    pg_dump $DATABASE_URL > "$BACKUP_DIR/db_$DATE.sql"
fi

# Redis backup
redis-cli BGSAVE

# Cleanup old backups (keep 14 days)
find $BACKUP_DIR -type f -mtime +14 -delete
```

### Usage
```bash
# Make executable
chmod +x scripts/backup_db.sh

# Run manually
./scripts/backup_db.sh

# Add to crontab for daily execution
0 2 * * * /path/to/scripts/backup_db.sh
```

## 🔴 Redis Persistence Configuration

### Redis Configuration (redis.conf)
```conf
# Enable AOF persistence
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec

# Enable RDB snapshots
save 60 1
save 300 10
save 900 30

# Memory management
maxmemory 256mb
maxmemory-policy allkeys-lru
```

### Docker Compose Setup
```yaml
services:
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
      - ./redis.conf:/usr/local/etc/redis/redis.conf
    command: redis-server /usr/local/etc/redis/redis.conf --appendonly yes
```

## 📋 Backup Verification

### Daily Backup Checklist
- [ ] Database backup completed successfully
- [ ] Redis AOF file created
- [ ] Backup file size is reasonable
- [ ] Old backups cleaned up
- [ ] Backup log entry created
- [ ] Backup can be restored

### Weekly Backup Checklist
- [ ] Verify backup integrity
- [ ] Test restore process
- [ ] Check disk space usage
- [ ] Review backup logs
- [ ] Update backup retention policy

## 🔄 Recovery Procedures

### Database Recovery
```bash
# SQLite Recovery
cp backups/db_2026-01-20.db music_legends.db

# PostgreSQL Recovery
psql -U username -d database_name < backups/db_2026-01-20.sql

# Automated Restore Script
./scripts/restore_db.sh backups/db_2026-01-20.sql.gz
```

### Redis Recovery
```bash
# Start Redis with AOF
redis-server --appendonly yes

# Automated Redis Restore
./scripts/restore_redis.sh /data/appendonly.aof.backup

# Docker Redis Restore
docker-compose stop redis
cp backup/appendonly.aof redis_data/
docker-compose start redis
```

### Full System Recovery
```bash
# 1. Stop all services
docker-compose down

# 2. Restore database
./scripts/restore_db.sh backups/db_2026-01-20.sql.gz

# 3. Restore Redis
./scripts/restore_redis.sh /data/appendonly.aof

# 4. Start services
docker-compose up -d

# 5. Verify system status
docker-compose ps
./scripts/verify_backup_complete.sh
```

## 📊 Backup Storage

### Local Storage
- **Location**: `./backups/`
- **Retention**: 14 days
- **Compression**: Enabled (gzip)
- **Size**: ~10-50MB per backup

### Cloud Storage (Optional)
```bash
# Upload to AWS S3
aws s3 cp backups/ s3://music-legends-backups/

# Upload to Google Cloud
gsutil cp backups/* gs://music-legends-backups/
```

## 🚨 Emergency Procedures

### Immediate Actions
1. **Stop all services** to prevent data corruption
2. **Assess damage** - what data is lost/corrupted
3. **Restore from latest backup**
4. **Verify data integrity**
5. **Restart services**
6. **Monitor system health**

### Data Corruption Recovery
```bash
# 1. Identify last good backup
ls -la backups/ | grep "db_"

# 2. Restore database
cp backups/db_2026-01-19.db music_legends.db

# 3. Verify integrity
sqlite3 music_legends.db ".schema"
sqlite3 music_legends.db "SELECT COUNT(*) FROM users;"
```

### Redis Failure Recovery
```bash
# 1. Check Redis status
docker-compose logs redis

# 2. Clear corrupted data
docker-compose exec redis redis-cli FLUSHALL

# 3. Restart with fresh data
docker-compose restart redis
```

## 📈 Monitoring and Alerts

### Backup Monitoring
```bash
# Check backup script logs
tail -f backups/backup.log

# Monitor backup file sizes
du -sh backups/

# Check Redis persistence
docker-compose exec redis redis-cli LASTSAVE
```

### Alert Setup
```bash
# Email alert for backup failures
echo "Backup failed on $(date)" | mail -s "Backup Alert" admin@example.com

# Slack webhook for backup status
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Music Legends backup completed successfully"}' \
  $SLACK_WEBHOOK_URL
```

## 🔧 Configuration Files

### Environment Variables (.env)
```bash
# Database configuration
DATABASE_URL=sqlite:///music_legends.db
POSTGRES_DB=music_legends
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# Redis configuration
REDIS_HOST=localhost
REDIS_PORT=6381
REDIS_PASSWORD=your_redis_password

# Backup configuration
BACKUP_RETENTION_DAYS=14
BACKUP_COMPRESSION=true
BACKUP_NOTIFICATION_EMAIL=admin@example.com
```

### Cron Job Setup
```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /path/to/music_legends/scripts/backup_db.sh

# Add weekly verification
0 6 * * 0 /path/to/music_legends/scripts/verify_backup.sh
```

## 🎯 Best Practices

### Backup Best Practices
- ✅ **Automate daily backups**
- ✅ **Test restore procedures**
- ✅ **Monitor backup success**
- ✅ **Use compression**
- ✅ **Implement retention policy**
- ✅ **Store backups off-site**
- ✅ **Document procedures**
- ✅ **Train team on recovery**

### Redis Persistence Best Practices
- ✅ **Enable AOF persistence**
- ✅ **Configure RDB snapshots**
- ✅ **Set memory limits**
- ✅ **Monitor disk usage**
- ✅ **Test recovery procedures**
- ✅ **Use appropriate fsync policy**

### Security Considerations
- 🔒 **Encrypt sensitive backups**
- 🔒 **Limit backup file permissions**
- 🔒 **Use secure file transfer**
- 🔒 **Implement access controls**
- 🔒 **Monitor backup access logs**

## 📞 Support and Troubleshooting

### Common Issues
1. **Backup fails** - Check disk space and permissions
2. **Redis won't start** - Check config file syntax
3. **Database corruption** - Use backup verification
4. **Slow backups** - Optimize database size
5. **Restore fails** - Check file integrity

### Getting Help
- 📖 **Documentation**: Check this guide first
- 🐛 **Issue Tracker**: Report bugs on GitHub
- 💬 **Community**: Ask in Discord server
- 📧 **Support**: Email support@example.com
