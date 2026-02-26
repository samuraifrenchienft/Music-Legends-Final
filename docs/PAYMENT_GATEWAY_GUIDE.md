# Payment Gateway Webhook Guide

## Overview

This guide documents the complete payment gateway webhook system that provides a gateway-agnostic interface for processing payment events from multiple providers (Stripe, PayPal, etc.).

## 🏗️ Architecture

### Gateway-Agnostic Design

The system uses a standardized event format that abstracts away provider-specific differences:

```
Provider Event → Adapter → Standard Event → Business Logic
     ↓              ↓           ↓              ↓
Stripe/PayPal → Mapping → Unified → Payment Service
```

### Core Components

1. **Webhook Adapter** (`webhooks/payments.py`) - Gateway-agnostic event processor
2. **HTTP Endpoint** (`app.py`) - Flask webhook receiver
3. **Gateway Adapters** - Provider-specific event mappers
4. **Signature Verification** - Security verification layer

## 📡 Webhook Endpoints

### Main Payment Webhook
```
POST /webhooks/payments
```
- Accepts events from any gateway
- Auto-detects gateway from headers
- Routes to appropriate adapter

### Gateway-Specific Endpoints
```
POST /webhooks/stripe    # Stripe-specific
POST /webhooks/paypal    # PayPal-specific
```

### Management Endpoints
```
GET  /health             # Service health check
GET  /status             # Detailed service status
POST /webhooks/test      # Test endpoint (debug only)
```

## 🔄 Event Processing Flow

### 1. Webhook Reception
```python
@app.post('/webhooks/payments')
async def payments_webhook():
    # 1. Verify signature
    verify_signature(request, gateway)
    
    # 2. Parse JSON payload
    event = request.get_json()
    
    # 3. Map to standard format
    standard_event = map_stripe_event(event)
    
    # 4. Process event
    result = await payment_webhook(standard_event)
    
    return jsonify(result)
```

### 2. Event Mapping
```python
# Stripe event mapping
stripe_event = {
    "type": "payment_intent.succeeded",
    "data": {
        "object": {
            "id": "pi_123",
            "amount": 4999,
            "metadata": {"user": "12345", "pack": "founder_black"}
        }
    }
}

# Standardized event
standard_event = {
    "type": "payment.captured",
    "data": {
        "id": "pi_123",
        "amount": 4999,
        "metadata": {"user": "12345", "pack": "founder_black"}
    }
}
```

### 3. Business Logic Processing
```python
async def payment_webhook(event):
    if event["type"] == "payment.captured":
        result = handle_payment(
            user_id=event["data"]["metadata"]["user"],
            pack_type=event["data"]["metadata"]["pack"],
            payment_id=event["data"]["id"]
        )
        return {"status": "captured", "result": result}
```

## 🎯 Supported Event Types

### Standard Event Types

| Event Type | Description | Business Logic |
|-------------|-------------|----------------|
| `payment.captured` | Payment successfully captured | Create cards, update purchase |
| `payment.refunded` | Payment refunded | Revoke cards, update purchase |
| `payment.failed` | Payment failed | Log failure, no action |
| `payment.pending` | Payment pending | Log pending, no action |

### Gateway Event Mappings

#### Stripe → Standard
| Stripe Event | Standard Event |
|--------------|----------------|
| `payment_intent.succeeded` | `payment.captured` |
| `payment_intent.payment_failed` | `payment.failed` |
| `charge.refunded` | `payment.refunded` |
| `payment_intent.requires_action` | `payment.pending` |

#### PayPal → Standard
| PayPal Event | Standard Event |
|--------------|----------------|
| `PAYMENT.CAPTURE.COMPLETED` | `payment.captured` |
| `PAYMENT.CAPTURE.DENIED` | `payment.failed` |
| `PAYMENT.SALE.REFUNDED` | `payment.refunded` |
| `PAYMENT.CAPTURE.PENDING` | `payment.pending` |

## 🔐 Security Features

### Signature Verification

#### Stripe Verification
```python
def verify_stripe_signature(request):
    signature_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    # Extract timestamp and signatures
    timestamp, signatures = parse_signature(signature_header)
    
    # Verify timestamp tolerance (5 minutes)
    if abs(current_time - int(timestamp)) > 300:
        raise WebhookSignatureError("Timestamp too old")
    
    # Construct and compare signature
    expected_signature = hmac.new(
        webhook_secret.encode(),
        f"{timestamp}.{payload}".encode(),
        hashlib.sha256
    ).hexdigest()
    
    return compare_signatures(signatures, expected_signature)
```

#### PayPal Verification
```python
def verify_paypal_signature(request):
    cert_id = request.headers.get('Paypal-Cert-Id')
    transmission_id = request.headers.get('Paypal-Transmission-Id')
    
    # Verify with PayPal API (simplified here)
    return verify_with_paypal_api(cert_id, transmission_id, payload)
```

### Security Headers
- **Stripe**: `Stripe-Signature`
- **PayPal**: `Paypal-Cert-Id`, `Paypal-Transmission-Id`

### Environment Variables
```env
# Stripe
STRIPE_WEBHOOK_SECRET=whsec_...

# PayPal
PAYPAL_WEBHOOK_ID=...

# Security
REQUIRE_WEBHOOK_SIGNATURE=True
```

## 🛠️ Configuration

### Environment Setup
```env
# Flask Configuration
FLASK_DEBUG=False
PORT=5000
HOST=0.0.0.0

# Gateway Secrets
STRIPE_WEBHOOK_SECRET=whsec_your_stripe_secret
PAYPAL_WEBHOOK_ID=your_paypal_webhook_id

# Security
REQUIRE_WEBHOOK_SIGNATURE=True
```

### Gateway-Specific Setup

#### Stripe Setup
1. Create webhook endpoint in Stripe Dashboard
2. Set endpoint URL: `https://your-domain.com/webhooks/stripe`
3. Select events: `payment_intent.succeeded`, `charge.refunded`, etc.
4. Copy webhook secret to environment variables

#### PayPal Setup
1. Create webhook in PayPal Developer Dashboard
2. Set endpoint URL: `https://your-domain.com/webhooks/paypal`
3. Select event types: `PAYMENT.CAPTURE.COMPLETED`, `PAYMENT.SALE.REFUNDED`, etc.
4. Copy webhook ID to environment variables

## 📊 Event Examples

### Stripe Payment Success
```json
{
  "type": "payment_intent.succeeded",
  "data": {
    "object": {
      "id": "pi_1234567890",
      "amount": 4999,
      "currency": "usd",
      "metadata": {
        "user": "12345",
        "pack": "founder_black"
      },
      "status": "succeeded"
    }
  }
}
```

### Standardized Event
```json
{
  "type": "payment.captured",
  "data": {
    "id": "pi_1234567890",
    "amount": 4999,
    "currency": "usd",
    "metadata": {
      "user": "12345",
      "pack": "founder_black"
    },
    "status": "succeeded"
  },
  "gateway": "stripe",
  "original_event": "payment_intent.succeeded"
}
```

### Processing Result
```json
{
  "status": "captured",
  "payment_id": "pi_1234567890",
  "user_id": "12345",
  "pack_type": "founder_black",
  "result": {
    "cards_created": 5,
    "purchase_id": 789
  }
}
```

## 🧪 Testing

### Test Webhook Endpoint
```bash
# Test endpoint (debug mode only)
curl -X POST http://localhost:5000/webhooks/test \
  -H "Content-Type: application/json" \
  -d '{
    "type": "payment.captured",
    "data": {
      "id": "test_123",
      "metadata": {"user": "999", "pack": "founder_black"}
    }
  }'
```

### Stripe Test Events
```bash
# Use Stripe CLI to test webhooks
stripe listen --forward-to localhost:5000/webhooks/stripe

# Trigger test events
stripe trigger payment_intent.succeeded
stripe trigger charge.refunded
```

### PayPal Test Events
```bash
# Use PayPal sandbox environment
# Set up test webhooks in PayPal Developer Dashboard
# Trigger test transactions through PayPal sandbox
```

## 🔧 Troubleshooting

### Common Issues

**"Invalid signature"**
```bash
# Check webhook secret
echo $STRIPE_WEBHOOK_SECRET

# Verify signature format
curl -X POST http://localhost:5000/webhooks/stripe \
  -H "Stripe-Signature: t=timestamp,v1=signature" \
  -d '{"test": "data"}'
```

**"Event mapping failed"**
```bash
# Check event structure
python -c "
from webhooks.gateways.stripe_adapter import StripeAdapter
adapter = StripeAdapter()
print(adapter.adapt_event(your_event))
"
```

**"Payment processing failed"**
```bash
# Check payment service
python -c "
from services.payment_service import handle_payment
result = handle_payment(123, 'founder_black', 'test_payment')
print(result)
"
```

### Debug Mode
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Skip signature verification (development only)
os.environ['REQUIRE_WEBHOOK_SIGNATURE'] = 'False'
```

### Health Checks
```bash
# Service health
curl http://localhost:5000/health

# Detailed status
curl http://localhost:5000/status
```

## 📈 Monitoring

### Metrics to Track
- Webhook processing success rate
- Event processing latency
- Signature verification failures
- Gateway-specific error rates
- Business logic processing time

### Logging
```python
# Structured logging
logger.info("Webhook processed", extra={
    "event_type": event_type,
    "gateway": gateway,
    "processing_time": duration,
    "result": result
})
```

### Alerting
- High failure rate (>5%)
- Signature verification failures
- Processing latency spikes
- Service unavailability

## 🚀 Deployment

### Production Checklist
- [ ] Webhook secrets configured
- [ ] HTTPS endpoint available
- [ ] Signature verification enabled
- [ ] Error monitoring setup
- [ ] Rate limiting configured
- [ ] Load balancing configured
- [ ] Database connections tested
- [ ] Redis connections tested

### Docker Deployment
```dockerfile
FROM python:3.11

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

### Environment Variables
```yaml
# docker-compose.yml
services:
  webhook:
    environment:
      - STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET}
      - PAYPAL_WEBHOOK_ID=${PAYPAL_WEBHOOK_ID}
      - REQUIRE_WEBHOOK_SIGNATURE=true
      - FLASK_DEBUG=false
```

## 🔄 Future Enhancements

### Additional Gateways
- Square
- Apple Pay
- Google Pay
- Crypto payments

### Advanced Features
- Event replay functionality
- Webhook retry logic
- Event deduplication
- Real-time monitoring dashboard

### Performance Optimizations
- Async event processing
- Event batching
- Caching layer
- Database connection pooling

---

**🎯 This gateway-agnostic webhook system provides a robust, secure foundation for processing payments from any provider!**
