# Discord Receipt System Guide

## Overview

This guide documents the Discord receipt system that provides beautiful, informative embeds for all payment events. Users get instant confirmation, visual card reveals, and refund notifications, while admins get complete sales logging.

## 🎨 Receipt Types

### 1. Purchase Confirmation
**Trigger**: `checkout.session.completed` webhook event

**Features**:
- 🛒 Purchase confirmation embed
- 📦 Pack type and order ID
- 💰 Purchase amount
- ⏰ Delivery notification
- 🖼️ Pack icon thumbnail

**Example**:
```
🛒 Purchase Confirmed

📦 Pack Type: Black Pack
🆔 Order ID: sess_1234567890
💰 Amount: $9.99
📅 Purchase Time: 2023-12-01 15:30:45 UTC

Cards will appear in your collection momentarily ⏳
```

### 2. Card Delivery
**Trigger**: After payment processing completes

**Features**:
- 🎁 Pack opened announcement
- 🎴 Complete card list with tier emojis
- 👤 Artist information for each card
- 🖼️ Hero image (first card's artist)
- 📊 Card count summary

**Card Display Format**:
```
1. 🟡 **LEG-001** - Legendary • John Doe
2. ⭐ **PLT-002** - Platinum • Jane Smith
3. 🏆 **GLD-003** - Gold • Bob Johnson
```

### 3. Refund Confirmation
**Trigger**: `charge.refunded` webhook event

**Features**:
- 💳 Refund processed notification
- 🆔 Original order ID
- 📊 Cards revoked status
- 💰 Refund amount
- ⏰ Refund processing time

### 4. Admin Sales Log
**Trigger**: Every successful purchase

**Features**:
- 💰 New sale notification
- 📦 Pack type and amount
- 👤 User ID (for admin reference)
- 🆔 Session ID
- 📅 Sale timestamp

### 5. Admin Refund Log
**Trigger**: Every processed refund

**Features**:
- 💳 Refund processed notification
- 🆔 Original session ID
- 👤 User ID
- 💰 Refund amount
- 🎴 Cards revoked count

## 🛠️ Implementation

### Core Components

#### **`ui/receipts.py`**
- `purchase_embed()` - Creates purchase confirmation
- `delivery_embed()` - Creates card delivery reveal
- `refund_embed()` - Creates refund notification
- `admin_sale_embed()` - Creates admin sales log
- `admin_refund_embed()` - Creates admin refund log

#### **`webhooks/stripe_hook.py`**
- Integrated receipt sending in webhook handlers
- Automatic user lookup and DM delivery
- Admin channel logging
- Error handling for failed deliveries

### Receipt Flow

```
Stripe Event → Webhook Handler → Business Logic → Receipt System → Discord DM
     ↓                ↓               ↓              ↓              ↓
checkout.session → handle_payment() → Cards Created → Embed Created → User Notified
charge.refunded → refund_purchase() → Cards Revoked → Embed Created → User Notified
```

## 🔧 Configuration

### Environment Variables
```env
# Required for receipt system
STRIPE_SECRET=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Optional for admin logging
SALES_CHANNEL_ID=123456789012345678

# Bot configuration
BOT_TOKEN=your_bot_token
```

### Bot Import Setup
The receipt system needs access to your bot instance. Set up the import in your main bot file:

```python
# main.py or bot.py
import discord
from discord.ext import commands

bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

# Make bot available to webhook system
import webhooks.stripe_hook
webhooks.stripe_hook.bot = bot
```

## 🎯 Features

### Tier Emojis
- ⚪ Common
- 🟢 Uncommon
- 🔵 Rare
- 🟣 Epic
- 🟡 Legendary
- ⭐ Platinum
- 🏆 Gold
- 💎 Diamond

### Pack Icons
- 📦 Starter Pack
- 🥈 Silver Pack
- 🥇 Gold Pack
- ⚫ Black Pack
- 🖤 Founder Black Pack
- 👑 Founder Gold Pack

### Error Handling
- Graceful fallback if user not found
- Continues processing even if DM fails
- Comprehensive error logging
- Admin notifications for failures

## 📊 Admin Channel Setup

### Create Sales Channel
1. Create a Discord channel for sales notifications
2. Get the channel ID
3. Set `SALES_CHANNEL_ID` in environment variables

### Channel Permissions
- Bot: Send Messages, Read Message History
- Admins: View Channel, Read Message History
- Others: No access (private channel)

### Admin Embed Examples

**Sale Notification**:
```
💰 New Sale

📦 Pack Type: Black Pack
🆔 Session ID: sess_1234567890
👤 User ID: 123456789
💰 Amount: $9.99
📅 Sale Time: 2023-12-01 15:30:45 UTC
```

**Refund Notification**:
```
💳 Refund Processed

🆔 Original Session: sess_1234567890
👤 User ID: 123456789
💰 Refund Amount: $9.99
🎴 Cards Revoked: 5
📅 Refund Time: 2023-12-02 10:15:30 UTC
```

## 🧪 Testing

### Test Purchase Flow
```python
# Simulate purchase completion
event = {
    "type": "checkout.session.completed",
    "data": {
        "object": {
            "id": "sess_test_123",
            "metadata": {"user_id": "123456789", "pack": "black"},
            "amount_total": 999
        }
    }
}

# Process webhook
result = await handle_checkout_session_completed(event)
```

### Test Refund Flow
```python
# Simulate refund
event = {
    "type": "charge.refunded",
    "data": {
        "object": {
            "id": "ch_test_123",
            "payment_intent": "pi_test_123",
            "amount_refunded": 999
        }
    }
}

# Process webhook
result = await handle_charge_refunded(event)
```

## 🔍 Troubleshooting

### Common Issues

**"User not found for receipt"**
- User may have left the server
- User may have DMs disabled
- Check user ID is correct

**"Failed to send purchase receipt"**
- Bot may not have permission to DM user
- User may have DMs from server members disabled
- Check bot permissions

**"No cards found for session"**
- Payment processing may have failed
- Cards may not have been created yet
- Check payment service logs

**"Admin channel not found"**
- `SALES_CHANNEL_ID` not set
- Channel ID may be incorrect
- Bot may not have channel access

### Debug Mode
Enable detailed logging:
```python
import logging
logging.getLogger('ui.receipts').setLevel(logging.DEBUG)
logging.getLogger('webhooks.stripe_hook').setLevel(logging.DEBUG)
```

### Manual Receipt Testing
```python
# Test receipt creation directly
from ui.receipts import purchase_embed
import discord

# Create mock user
user = discord.User(state=None, data={
    "id": 123456789,
    "username": "TestUser",
    "display_name": "Test User"
})

# Create embed
embed = purchase_embed(user, "black", "sess_test_123", 999)
print(embed.to_dict())
```

## 📈 Analytics

### Receipt Metrics
- Purchase confirmation delivery rate
- Card delivery success rate
- Refund notification delivery rate
- Admin logging success rate

### User Engagement
- Receipt open rates (if using tracking)
- Card reveal interaction
- Refund request patterns

### Sales Analytics
- Pack type popularity
- Purchase frequency
- Refund rates by pack type

## 🚀 Production Deployment

### Pre-Launch Checklist
- [ ] Bot has DM permissions
- [ ] Admin sales channel created
- [ ] Environment variables set
- [ ] Test purchases completed
- [ ] Error monitoring configured
- [ ] Admin notifications tested

### Monitoring
- Receipt delivery success rate
- Webhook processing errors
- User feedback on receipts
- Admin channel activity

### Scaling Considerations
- Rate limiting for DM sends
- Queue system for high volume
- Fallback delivery methods
- Performance monitoring

---

## 🎯 Benefits

### For Users
- ✅ **Instant confirmation** - Immediate purchase acknowledgment
- ✅ **Visual card reveal** - Beautiful presentation of new cards
- ✅ **Complete transparency** - Clear refund notifications
- ✅ **Purchase history** - Order tracking and receipts

### For Admins
- ✅ **Real-time sales tracking** - Instant notification of purchases
- ✅ **Refund monitoring** - Complete refund audit trail
- ✅ **User insights** - Purchase patterns and behavior
- ✅ **Error visibility** - Failed delivery notifications

### For Support
- ✅ **Order reference** - Session IDs for support tickets
- ✅ **Purchase verification** - Easy order lookup
- ✅ **Refund confirmation** - Clear refund status
- ✅ **Audit trail** - Complete event history

---

**🎉 The receipt system provides a professional, transparent payment experience that builds user trust and simplifies administration!**
