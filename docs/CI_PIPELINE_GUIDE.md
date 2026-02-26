# Continuous Integration Pipeline Guide

## Overview

This guide documents the complete CI/CD pipeline that ensures every code change meets the highest quality standards before merging to production.

## 🚀 Pipeline Architecture

### Triggers

The CI pipeline runs on:
- **Push to `main`** - Full validation + performance tests
- **Push to `dev`** - Standard validation + security tests  
- **Pull Request** - Standard validation + security tests

### Jobs Overview

```
CI Pipeline
├── test (main job)
│   ├── Environment setup
│   ├── Database migration
│   ├── Test data seeding
│   ├── Smoke tests
│   └── Additional tests
├── security (PR only)
│   ├── Secret scanning
│   └── Basic security checks
└── performance (main only)
    └── Rate limiter benchmarks
```

## 🧪 Test Job Details

### Environment Setup
- **Python 3.11** with caching for faster builds
- **PostgreSQL 15** with health checks
- **Redis 7** with health checks
- **System dependencies** (postgresql-client)

### Database Setup
```bash
# Wait for services
timeout 30 bash -c 'until redis-cli ping; do sleep 1; done'
timeout 30 bash -c 'until pg_isready; do sleep 1; done'

# Run migrations
python manage.py migrate

# Seed test data
python -c "seed_test_artists()"
```

### Smoke Tests Execution
```bash
pytest tests/smoke.py -v --tb=short --color=yes
```

**Critical Business Logic Verified:**
- ✅ Black Pack guarantee (Gold+ tier in packs)
- ✅ Legendary cap enforcement (downgrade logic)
- ✅ Parallel opening safety (no duplicates)
- ✅ Trade atomicity (single finalization)
- ✅ Rate limiting (abuse prevention)
- ✅ Refund revocation (consumer protection)

### Coverage Reporting
- **XML coverage** for Codecov integration
- **HTML coverage** for local viewing
- **Focused coverage** on services and models

## 🔒 Security Job Details

### Secret Detection
Scans for hardcoded secrets:
- `sk_live_` - Live Stripe keys
- `ghp_` - GitHub personal tokens
- Database connection strings
- API keys and tokens

### Basic Security Checks
- File permission validation
- Import security
- Dependency vulnerability scanning (basic)

## ⚡ Performance Job Details

### Rate Limiter Benchmarks
```python
# Performance test: 50 rate limit checks in < 1 second
limiter = RateLimiter('perf_test', 100, 60)
for i in range(50):
    limiter.allow()
```

### Metrics Tracked
- Response time thresholds
- Memory usage patterns
- Database query efficiency

## 📊 Test Results Interpretation

### Success Output
```
🧪 Smoke Tests Summary
======================
✅ Black Pack Guarantee - Verified
✅ Legendary Cap - Verified 
✅ Parallel Open Safety - Verified
✅ Trade Atomic - Verified
✅ Rate Limit - Verified
✅ Refund Revoke - Verified
======================
🎉 All critical business logic verified!
🚀 CI PASSED - Ready for merge!
```

### Failure Output
```
❌ CI FAILED - Check test output above
🚫 DO NOT MERGE - Fix failing tests first
```

### Failure Categories

**Smoke Test Failures:**
- **Black Pack Guarantee** - Pack opening logic broken
- **Legendary Cap** - Rarity control not working
- **Parallel Safety** - Database integrity issues
- **Trade Atomic** - Transaction logic broken
- **Rate Limit** - Abuse prevention broken
- **Refund** - Consumer protection broken

**Security Failures:**
- Hardcoded secrets detected
- Vulnerable dependencies
- Permission issues

**Performance Failures:**
- Rate limiter too slow
- Memory leaks
- Database performance regression

## 🔧 Local Development Setup

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov pytest-mock

# Start services
docker-compose up -d redis postgres

# Set environment
export DATABASE_URL="postgres://game:game@localhost:5432/game"
export REDIS_URL="redis://localhost:6379"
export ENVIRONMENT="test"
```

### Run Tests Locally
```bash
# Full smoke test suite
pytest tests/smoke.py -v

# With coverage
pytest tests/smoke.py --cov=services --cov=models --cov-report=html

# Individual test
pytest tests/smoke.py::TestSmokeSuite::test_black_guarantee -v
```

### Debug Mode
```bash
# Verbose output with prints
pytest tests/smoke.py -v -s --tb=long

# Stop on first failure
pytest tests/smoke.py -x
```

## 🚨 Troubleshooting Guide

### Common CI Issues

**"Service not ready"**
```bash
# Check service health
docker-compose ps
docker-compose logs redis
docker-compose logs postgres
```

**"Database connection failed"**
```bash
# Verify database exists
psql -h localhost -U game -d game -c "\dt"

# Check permissions
psql -h localhost -U game -d game -c "\l"
```

**"Redis connection failed"**
```bash
# Test Redis connection
redis-cli -h localhost ping
```

**"Import errors"**
```bash
# Check PYTHONPATH
export PYTHONPATH="$PWD:$PYTHONPATH"
python -c "import services.pack_youtube"
```

### Test-Specific Issues

**Black Pack Test Fails**
- Check `services.pack_youtube.open_black_pack()` implementation
- Verify artist data exists
- Check pack configuration

**Legendary Cap Test Fails**
- Verify artist cap logic
- Check `current_legendary` field
- Verify cap threshold (100)

**Parallel Test Fails**
- Check card ID generation
- Verify database constraints
- Check transaction isolation

**Trade Test Fails**
- Verify trade creation logic
- Check finalization atomicity
- Verify status updates

**Rate Limit Test Fails**
- Check Redis connection
- Verify rate limiter implementation
- Check window logic

**Refund Test Fails**
- Verify refund service logic
- Check card deletion cascade
- Verify purchase-card relationship

### Performance Issues

**Rate Limiter Slow**
- Check Redis performance
- Verify algorithm efficiency
- Profile the limiter code

**Memory Issues**
- Check for memory leaks
- Verify cleanup logic
- Profile memory usage

## 📋 Pre-Push Checklist

Before pushing code:

### Code Quality
- [ ] Code follows project style
- [ ] No debug prints left in
- [ ] No hardcoded secrets
- [ ] Documentation updated if needed

### Testing
- [ ] Local smoke tests pass
- [ ] New functionality has tests
- [ ] Edge cases considered
- [ ] Error handling implemented

### Performance
- [ ] No obvious performance regressions
- [ ] Database queries optimized
- [ ] Memory usage reasonable

### Security
- [ ] No secrets committed
- [ ] Input validation added
- [ ] Permissions checked
- [ ] SQL injection prevented

## 🎯 Pipeline Benefits

### Quality Assurance
- **Automated Testing** - Every change tested
- **Business Logic Verification** - Critical rules enforced
- **Security Scanning** - Vulnerabilities caught early
- **Performance Monitoring** - Regressions prevented

### Developer Experience
- **Fast Feedback** - Quick test results
- **Clear Requirements** - Explicit pass/fail criteria
- **Local Testing** - Same environment as CI
- **Debug Support** - Detailed error messages

### Production Safety
- **Gatekeeping** - Broken code never reaches main
- **Rollback Safety** - Issues caught before deployment
- **Audit Trail** - Complete test history
- **Emergency Procedures** - Documented bypass process

## 🔄 Continuous Improvement

### Metrics to Track
- Test execution time
- Failure rate by category
- Performance benchmarks
- Security scan results

### Optimization Opportunities
- Parallel test execution
- Better caching strategies
- Faster service startup
- More efficient test data

### Future Enhancements
- Integration tests
- Load testing
- Security scanning expansion
- Automated deployment

---

**🚀 This CI pipeline ensures every merge to main guarantees production-ready, secure, and performant code!**
