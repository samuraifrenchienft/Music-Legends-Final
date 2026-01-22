# Smoke Test Suite

## Overview

This is the **checklist-critical** smoke test suite that verifies the core business logic must work for production launch.

## 🚨 Launch Gate Criteria

**ALL tests must pass before launch:**

✅ **Black Guarantee** - Black packs contain Gold+ tier  
✅ **Cap Downgrade** - Legendary caps prevent legendary cards  
✅ **No Duplicates** - Parallel pack opening creates unique cards  
✅ **Trade Atomic** - Trade finalization is single-use  
✅ **Rate Limit** - Rate limiter enforces limits  
✅ **Refund Revoke** - Refund deletes all purchase cards  

## 🧪 Test Coverage

### 1. Black Pack Guarantee (`test_black_guarantee`)
- Opens black pack for test user
- Verifies at least one Gold/Platinum/Legendary card
- Ensures premium value proposition

### 2. Legendary Cap (`test_legendary_cap`)
- Sets artist to legendary cap (100)
- Opens black pack
- Verifies no legendary cards awarded
- Tests cap enforcement logic

### 3. Parallel Open Safety (`test_parallel`)
- Counts cards before test
- Opens 5 black packs rapidly
- Verifies correct number of cards created
- Checks for duplicate card IDs

### 4. Trade Atomic (`test_trade`)
- Creates sample trade
- Finalizes trade successfully
- Attempts second finalization (must fail)
- Verifies atomic behavior

### 5. Rate Limit (`test_rate`)
- Creates rate limiter (2 requests per 5 seconds)
- Tests allowed requests
- Tests denied requests
- Verifies independent rate limiting

### 6. Refund (`test_refund`)
- Creates test purchase with cards
- Processes refund
- Verifies all cards deleted
- Checks card IDs no longer exist

## 🏃‍♂️ Running Tests

### Quick Run
```bash
python -m pytest tests/smoke.py -v
```

### Detailed Run
```bash
python -m pytest tests/smoke.py -v --tb=long --color=yes
```

### Run Individual Test
```bash
python -m pytest tests/smoke.py::TestSmokeSuite::test_black_guarantee -v
```

### Run with Coverage
```bash
python -m pytest tests/smoke.py --cov=services --cov=models --cov-report=html
```

## 📊 Test Results

### Success Output
```
🚀 Running Smoke Test Suite
==================================================
📦 Testing Black Pack Guarantee...
✅ Black pack guarantee passed - Found 1 Gold+ cards

🏆 Testing Legendary Cap...
✅ Legendary cap passed - No legendary cards found in 5 cards

🔄 Testing Parallel Open Safety...
✅ Parallel safety passed - Created 25 unique cards

🤝 Testing Trade Atomicity...
✅ Trade atomicity passed - Single finalization enforced

⏱️ Testing Rate Limit...
✅ Rate limit passed - Limits enforced correctly

💰 Testing Refund...
✅ Refund passed - Deleted 5 cards

==================================================
🏁 Smoke Test Suite Complete

🎉 ALL SMOKE TESTS PASSED!
✅ System is ready for launch
```

### Failure Output
```
❌ SMOKE TESTS FAILED!
🚫 System NOT ready for launch

Check test output for specific failures.
```

## 🔧 Configuration

### Environment Setup
```bash
# Set test environment
export ENVIRONMENT=test

# Database (test instance)
export DATABASE_URL=sqlite:///test.db

# Redis (test instance)  
export REDIS_URL=redis://localhost:6379/1

# Stripe (test mode)
export STRIPE_SECRET_KEY=sk_test_...
export STRIPE_WEBHOOK_SECRET=whsec_...
```

### Test Data
- Uses test user ID: `999999`
- Uses test payment ID: `"SMOKE_TEST_PAYMENT_123"`
- Automatically cleans up test data
- Isolated from production data

## 🚨 Troubleshooting

### Common Issues

**"Black pack should return cards"**
- Check `services.pack_youtube.open_black_pack()` implementation
- Verify database connection
- Check artist data exists

**"Cap must prevent legendary cards"**
- Verify artist cap logic in pack opening
- Check `current_legendary` field exists
- Verify cap threshold (100)

**"Possible duplicates"**
- Check card ID generation logic
- Verify database constraints
- Check parallel opening safety

**"Second trade finalize must fail"**
- Verify trade status updates
- Check atomic finalization logic
- Verify status checking

**"Third request should be denied"**
- Check rate limiter implementation
- Verify Redis connection
- Check rate limit window

**"Refund should delete all purchase cards"**
- Verify refund service logic
- Check card deletion cascade
- Verify purchase-card relationship

### Debug Mode
```bash
# Run with debug output
python -m pytest tests/smoke.py -v -s --tb=long

# Run specific failing test
python -m pytest tests/smoke.py::test_refund -v -s
```

## 📋 Pre-Launch Checklist

Before running smoke tests for launch:

- [ ] Test database is fresh copy of production
- [ ] Redis is cleared of old rate limits
- [ ] All services are running
- [ ] Environment variables are set
- [ ] Database migrations are applied
- [ ] Test user exists with proper permissions

## 🎯 Pass Criteria Verification

Each test verifies a critical business rule:

| Test | Business Rule | Verification |
|------|---------------|---------------|
| Black Guarantee | Premium value | Gold+ card in pack |
| Legendary Cap | Rarity control | No legendary when capped |
| Parallel Safety | Data integrity | No duplicate cards |
| Trade Atomic | Transaction safety | Single finalization |
| Rate Limit | Abuse prevention | Request limiting |
| Refund | Consumer protection | Card revocation |

## 🚀 Production Readiness

When all smoke tests pass:

✅ **Core business logic verified**  
✅ **Data integrity confirmed**  
✅ **Safety mechanisms working**  
✅ **Consumer protections active**  
✅ **System ready for launch**  

**Proceed with production deployment!**
