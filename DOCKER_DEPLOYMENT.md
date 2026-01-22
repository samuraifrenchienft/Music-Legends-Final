# DOCKER_DEPLOYMENT.md

## 🐳 Docker Deployment Guide

### **Prerequisites**
- Docker and Docker Compose installed
- Redis server (handled by Docker Compose)
- Environment variables configured in `.env.txt`

### **Quick Start**

1. **Build and Start Services**
```bash
# Build and start all services
docker-compose up --build -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

2. **Verify Services**
```bash
# Test Redis connection
docker-compose exec redis redis-cli ping

# Check worker status
docker-compose exec worker python -c "import queue; print('Worker OK')"

# Check bot status
docker-compose logs bot | grep "Bot is ready"
```

3. **Monitor Jobs**
```bash
# View Redis monitoring
open http://localhost:8081

# Check job status
docker-compose exec bot python -c "
from scheduler.cron import cron_service
print(cron_service.get_job_status())
"
```

### **Service Management**

#### **Start Services**
```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d redis
docker-compose up -d worker
docker-compose up -d bot
```

#### **Stop Services**
```bash
# Stop all services
docker-compose down

# Stop specific service
docker-compose stop bot
docker-compose stop worker
docker-compose stop redis
```

#### **Restart Services**
```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart bot
docker-compose restart worker
```

#### **View Logs**
```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs bot
docker-compose logs worker
docker-compose logs redis

# Follow logs in real-time
docker-compose logs -f bot
```

### **Development Workflow**

#### **Local Development**
```bash
# Start only Redis for local development
docker-compose up -d redis

# Run bot locally
python main.py

# Run worker locally
python -m queue.worker
```

#### **Testing Changes**
```bash
# Rebuild and restart specific service
docker-compose up --build -d bot

# Test with new code
docker-compose exec bot python -c "print('Testing new code')"
```

#### **Debugging**
```bash
# Enter container for debugging
docker-compose exec bot bash
docker-compose exec worker bash

# View container processes
docker-compose exec bot ps aux
```

### **Production Deployment**

#### **Environment Setup**
```bash
# Copy environment template
cp .env.txt.example .env.txt

# Edit environment variables
nano .env.txt
```

#### **Deploy to Production**
```bash
# Build production image
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Scale workers if needed
docker-compose up -d --scale worker=3
```

#### **Health Checks**
```bash
# Check service health
docker-compose ps

# Check Redis health
docker-compose exec redis redis-cli ping

# Check job execution
docker-compose exec bot python -c "
from scheduler.cron import cron_service
status = cron_service.get_job_status()
for job_id, job_info in status.items():
    print(f'{job_id}: {job_info.get(\"active\", False)}')
"
```

### **Troubleshooting**

#### **Common Issues**

**Redis Connection Failed**
```bash
# Check Redis container
docker-compose logs redis

# Test Redis connection
docker-compose exec bot python -c "
import redis
r = redis.Redis(host='redis', port=6379)
print(r.ping())
"
```

**Worker Not Processing Jobs**
```bash
# Check worker logs
docker-compose logs worker

# Check queue status
docker-compose exec worker python -c "
from queue.redis import QUEUES
for name, queue in QUEUES.items():
    print(f'{name}: {queue.count}')
"
```

**Bot Not Responding**
```bash
# Check bot logs
docker-compose logs bot

# Restart bot service
docker-compose restart bot
```

#### **Performance Issues**

**High Memory Usage**
```bash
# Check container resource usage
docker stats

# Check Redis memory
docker-compose exec redis redis-cli info memory
```

**Slow Job Processing**
```bash
# Check queue backlog
docker-compose exec worker python -c "
from queue.redis import QUEUES
for name, queue in QUEUES.items():
    print(f'{name}: {queue.count} jobs pending')
"
```

### **Backup and Recovery**

#### **Data Backup**
```bash
# Backup Redis data
docker-compose exec redis redis-cli BGSAVE

# Copy Redis data
docker cp $(docker-compose ps -q redis):/data ./redis_backup
```

#### **Service Recovery**
```bash
# Restore from backup
docker-compose down
docker volume rm music_legends_redis_data
docker-compose up -d redis

# Restore Redis data
docker cp ./redis_backup/* $(docker-compose ps -q redis):/data/
docker-compose restart redis
```

### **Scaling**

#### **Scale Workers**
```bash
# Scale to 3 workers
docker-compose up -d --scale worker=3

# Scale to 5 workers
docker-compose up -d --scale worker=5
```

#### **Load Balancing**
```bash
# View worker distribution
docker-compose ps

# Monitor worker performance
docker-compose exec worker python -c "
import time
import queue.redis
from queue.redis import QUEUES
while True:
    for name, queue in QUEUES.items():
        print(f'{name}: {queue.count}')
    time.sleep(10)
"
```

### **Security**

#### **Network Security**
```bash
# View network configuration
docker network ls
docker network inspect music_legends_network

# Restrict external access
docker-compose down
# Edit docker-compose.yml to remove port mappings
docker-compose up -d
```

#### **Environment Security**
```bash
# Check environment variables
docker-compose exec bot env | grep -E "(TOKEN|SECRET|KEY)"

# Use secrets in production
# Update docker-compose.yml to use Docker secrets
```

### **Monitoring**

#### **Resource Monitoring**
```bash
# Real-time resource usage
docker stats

# Historical resource usage
docker stats --no-stream
```

#### **Service Monitoring**
```bash
# Service health check
docker-compose exec bot python -c "
import redis
r = redis.Redis(host='redis', port=6379)
print(f'Redis: {r.ping()}')
print(f'Jobs: {len(r.keys(\"job:*\"))}')
"
```

#### **Log Monitoring**
```bash
# Follow all logs
docker-compose logs -f

# Filter logs by level
docker-compose logs bot | grep ERROR
docker-compose logs worker | grep WARNING
```

### **Updates and Maintenance**

#### **Update Services**
```bash
# Pull latest images
docker-compose pull

# Rebuild and restart
docker-compose up --build -d
```

#### **Maintenance Tasks**
```bash
# Clean up unused images
docker image prune

# Clean up unused volumes
docker volume prune

# Restart services weekly
docker-compose restart
```

### **Support**

#### **Get Help**
```bash
# Check Docker version
docker --version
docker-compose --version

# Check system resources
docker system df
docker system info

# Get container information
docker-compose exec bot python -c "
import sys
print(f'Python: {sys.version}')
import discord
print(f'Discord.py: {discord.__version__}')
"
```
