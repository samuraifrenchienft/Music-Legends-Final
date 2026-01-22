# ROLLOUT_PLAN.md

## 🚀 Rollout Plan - Cron Service & Infrastructure

### **Phase 1: Dependencies (Day 1)**
- [ ] Add APScheduler to requirements.txt
- [ ] Add Redis and RQ dependencies
- [ ] Test Redis connection locally
- [ ] Verify Docker installation

### **Phase 2: Core Infrastructure (Day 2)**
- [ ] Implement queue/redis.py
- [ ] Implement queue/locks.py
- [ ] Implement queue/tasks.py
- [ ] Test Redis locks manually
- [ ] Verify queue worker startup

### **Phase 3: Cron Module (Day 3)**
- [ ] Implement scheduler/cron.py
- [ ] Implement scheduler/services.py
- [ ] Implement scheduler/jobs.py
- [ ] Test job scheduling locally
- [ ] Verify Redis lock integration

### **Phase 4: Daily Rewards Migration (Day 4)**
- [ ] Migrate existing daily reward logic
- [ ] Test daily rewards job
- [ ] Verify idempotency
- [ ] Check Redis lock behavior
- [ ] Monitor job execution logs

### **Phase 5: Auto Drops (Day 5)**
- [ ] Implement activity-based drops
- [ ] Test drop spawning logic
- [ ] Verify no duplicate drops
- [ ] Monitor drop frequency
- [ ] Check performance impact

### **Phase 6: Trade Expiration (Day 6)**
- [ ] Implement trade expiration logic
- [ ] Test stale trade cleanup
- [ ] Verify trade status updates
- [ ] Check notification system
- [ ] Monitor expiration accuracy

### **Phase 7: Monitoring & Testing (Day 7)**
- [ ] Add job status monitoring
- [ ] Implement health checks
- [ ] Run acceptance tests
- [ ] Verify restart resilience
- [ ] Test Docker deployment

### **Phase 8: Production Deployment (Day 8)**
- [ ] Deploy Docker Compose
- [ ] Start Redis service
- [ ] Start worker processes
- [ ] Start bot with cron
- [ ] Monitor all services

### **Phase 9: Validation (Day 9)**
- [ ] Verify daily rewards execute once
- [ ] Confirm no duplicate drops
- [ ] Check expired trades cancelled
- [ ] Test job restart resilience
- [ ] Validate Redis lock behavior

### **Phase 10: Documentation & Training (Day 10)**
- [ ] Update README with cron info
- [ ] Document monitoring procedures
- [ ] Create troubleshooting guide
- [ ] Train team on new infrastructure
- [ ] Document rollback procedures

## 🧪 Testing Checklist

### **Acceptance Criteria Tests**
- [ ] Daily rewards execute once only
- [ ] Drops trigger without duplicates
- [ ] Expired trades cancelled
- [ ] Jobs resume after restart
- [ ] Redis locks prevent double run

### **Performance Tests**
- [ ] Redis connection stability
- [ ] Job execution performance
- [ ] Memory usage monitoring
- [ ] CPU usage validation
- [ ] Response time checks

### **Integration Tests**
- [ ] Bot startup with cron
- [ ] Worker process stability
- [ ] Queue processing accuracy
- [ ] Database consistency
- [ ] Error handling validation

## 🚨 Rollback Procedures

### **Immediate Rollback (Within 1 Hour)**
1. Stop Docker services: `docker-compose down`
2. Revert to previous code version
3. Restart without cron: `python main.py`
4. Monitor for issues

### **Partial Rollback (Within 4 Hours)**
1. Disable specific jobs: `cron_service.pause_job(job_id)`
2. Monitor system stability
3. Fix identified issues
4. Re-enable jobs gradually

### **Full Rollback (Within 24 Hours)**
1. Stop all services
2. Restore database backup
3. Deploy previous version
4. Verify system stability
5. Investigate root cause

## 📊 Monitoring Metrics

### **Job Metrics**
- Job execution frequency
- Job success/failure rates
- Average job duration
- Queue length trends
- Lock contention rates

### **System Metrics**
- Redis memory usage
- Worker process health
- Bot response times
- Database query performance
- Error rates by service

### **Business Metrics**
- Daily reward claims
- Drop spawn rates
- Trade expiration accuracy
- User engagement levels
- System uptime

## 🔧 Troubleshooting Guide

### **Common Issues**

#### **Jobs Not Running**
- Check Redis connection
- Verify scheduler status
- Check job configuration
- Review error logs

#### **Duplicate Executions**
- Verify Redis locks
- Check job idempotency
- Review queue processing
- Monitor lock contention

#### **Performance Issues**
- Check Redis memory
- Monitor queue backlog
- Review job complexity
- Optimize database queries

#### **Redis Connection Issues**
- Verify Redis service
- Check network connectivity
- Review connection pool
- Monitor Redis logs

### **Emergency Procedures**

#### **Redis Down**
1. Stop worker processes
2. Queue jobs in memory (temporary)
3. Restart Redis service
4. Resume worker processes
5. Monitor for data loss

#### **Worker Crash**
1. Check error logs
2. Restart worker service
3. Verify queue integrity
4. Monitor for recurring issues
5. Scale workers if needed

#### **Bot Crash**
1. Check cron service status
2. Verify job execution logs
3. Restart bot service
4. Monitor for stability
5. Investigate root cause

## 📞 Support Contacts

### **Technical Support**
- Infrastructure: DevOps team
- Code issues: Development team
- Redis issues: Database team
- Performance: Monitoring team

### **Escalation Procedures**
1. Level 1: On-call engineer
2. Level 2: Team lead
3. Level 3: Engineering manager
4. Level 4: CTO

## 📚 Documentation Links

- [Redis Documentation](https://redis.io/documentation)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [RQ Documentation](https://python-rq.org/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
