# Professional Card System Guide

## 🎯 Overview

This is a **professional-grade trading card system** built for long-term growth and investor confidence. Every component follows strict canonical definitions and business rules.

## 📁 System Architecture

### Core Components

1. **Canonical Card Schema** (`schemas/card_canonical.py`)
   - Authoritative card definition
   - Never changes casually
   - All rendering reads from this structure

2. **Pack Definition System** (`schemas/pack_definition.py`)
   - No code invents pack behavior outside this file
   - All pack logic reads from definitions
   - Formalized pack configurations

3. **Serial System** (`services/serial_system.py`)
   - Investor-grade serial numbers
   - Format: `ML-S{season}-{tier_letter}-{print_number}`
   - Global scarcity tracking

4. **Hero Slot System** (`services/hero_slot_system.py`)
   - Premium pack differentiation
   - Boosted artist selection
   - Visual impact guarantee

5. **Pack Opening Experience** (`services/pack_opening_experience.py`)
   - Sequential card reveals
   - Legendary pause effect
   - Premium UX feel

6. **Card Rendering System** (`services/card_rendering_system.py`)
   - Front zones (header/hero/footer)
   - Back design (system-level)
   - Discord embed generation

## 🎴 Canonical Card Structure

```json
{
  "card_id": "uuid",
  "artist": {
    "id": "uuid",
    "name": "string",
    "primary_genre": "string",
    "image_url": "string",
    "source": "youtube | spotify"
  },
  "rarity": {
    "tier": "community | gold | platinum | legendary",
    "print_number": 12,
    "print_cap": 250
  },
  "identity": {
    "season": 1,
    "serial": "ML-S1-L-0012",
    "mint_timestamp": "iso8601"
  },
  "origin": {
    "pack_key": "black | silver | creator_x",
    "opened_by": "user_id",
    "opened_at": "iso8601"
  },
  "presentation": {
    "frame_style": "lux_black",
    "foil": true,
    "badge_icons": ["legendary", "first_print"],
    "accent_color": "#D4AF37"
  }
}
```

## 📦 Pack Definitions

### Black Pack Example

```json
{
  "key": "black",
  "display_name": "Black Pack",
  "tier": "premium",
  "cards_per_pack": 5,
  "guarantees": {
    "min_rarity": "gold",
    "hero_slot": true
  },
  "odds": {
    "community": 0.55,
    "gold": 0.30,
    "platinum": 0.12,
    "legendary": 0.03
  },
  "visuals": {
    "pack_color": "#0B0B0B",
    "accent": "#D4AF37",
    "style": "luxury"
  }
}
```

### Available Packs

- **Starter**: 3 cards, community/gold
- **Silver**: 4 cards, guaranteed gold
- **Gold**: 5 cards, epic chances
- **Black**: 5 cards, hero slot, premium
- **Founder Gold**: 7 cards, guaranteed epics
- **Founder Black**: 8 cards, guaranteed platinums

## 🔢 Serial System

### Format

`ML-S{season}-{tier_letter}-{print_number}`

Examples:
- `ML-S1-L-0001` → First Legendary ever
- `ML-S1-G-0123` → Gold, mid-run

### Tier Letters

- `C` = Community
- `G` = Gold
- `P` = Platinum
- `L` = Legendary

### Rules

- Legendary serials are globally scarce
- Print # never reused
- Burned cards do NOT free serials
- Serials tell a story of scarcity

## ⭐ Hero Slot System

### Purpose

Premium packs must feel premium. Hero slot ensures:

- Visual impact, not just tier
- Recognizable artists
- Boosted selection probability

### Rules

- Slot 1 uses boosted artist selection
- Pulls higher-popularity artists first
- Hero ≠ Legendary, Hero = recognizable

### Artist Scoring

Artists scored by:
- **Popularity** (60%): Followers/subscribers
- **Visual Impact** (40%): Art quality

Hero eligibility: Score ≥ 70.0

## 🎬 Pack Opening Experience

### Flow

1. **Pack Animation Embed**
   - Pack details and odds
   - Visual anticipation

2. **Sequential Card Reveal**
   - Cards revealed one by one
   - Legendary cards pause longer
   - Hero cards highlighted

3. **Summary Embed**
   - Pack statistics
   - Best pulls highlighted
   - Hero card showcase

### Timing

- Standard cards: 1.5s pause
- High tiers: 2s pause
- Legendary: 3s pause

## 🎨 Card Rendering

### Front Zones

```
┌──────────────────────────┐
│  Artist Name        Tier │  ← Header band
│──────────────────────────│
│                          │
│      ARTIST IMAGE        │  ← Hero zone (safe crop)
│                          │
│──────────────────────────│
│  Genre        Season     │
│──────────────────────────│
│  Serial • Print # / Cap  │
└──────────────────────────┘
```

### Design Rules

- Tier always visible
- Serial never hidden
- Image never cropped by tier badge
- Print cap shown only on Platinum+

### Back Design

System-level design that changes only by:
- Season
- Edition
- Premium run

## 💳 Payment Integration

### Stripe Webhook Flow

1. **Payment Completion** → Stripe webhook
2. **Pack Processing** → Generate canonical cards
3. **Card Creation** → Store in database
4. **User Experience** → Pack opening sequence
5. **Discord Delivery** → Cards revealed to user

### Idempotency

- Payment ID as unique key
- Duplicate payments rejected
- Cards never double-created

## 🧪 Testing

### Run Tests

```bash
cd tests
python professional_card_system_test.py
```

### Test Coverage

- ✅ Canonical card schema
- ✅ Pack definitions
- ✅ Serial system
- ✅ Hero slot system
- ✅ Payment processing
- ✅ Card rendering
- ✅ Integration flows

## 🔧 Configuration

### Environment Variables

```env
# Stripe Configuration
STRIPE_SECRET=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Discord Configuration
SALES_CHANNEL_ID=123456789012345678

# System Configuration
WEBHOOK_PORT=5001
CURRENT_SEASON=1
```

### Pack Customization

Add custom packs by creating `pack_definitions.json`:

```json
{
  "packs": [
    {
      "key": "creator_special",
      "display_name": "Creator Special Pack",
      "tier": "premium",
      "cards_per_pack": 6,
      "guarantees": {
        "min_rarity": "platinum",
        "hero_slot": true
      },
      "odds": {
        "gold": 0.20,
        "platinum": 0.50,
        "legendary": 0.30
      },
      "visuals": {
        "pack_color": "#FF6B6B",
        "accent": "#FFFFFF",
        "style": "creator"
      },
      "price_cents": 1499
    }
  ]
}
```

## 🚀 Production Deployment

### Database Setup

- PostgreSQL for production
- Redis for caching
- Proper indexing on serials

### Performance Considerations

- Serial system uses file-based persistence
- Consider database for high volume
- Card rendering can be CPU intensive

### Scaling

- Horizontal scaling possible
- Serial system needs coordination
- Artist database should be cached

## 🎯 Business Logic Rules

### Pack Guarantees

- **Hero Slot**: Premium packs only
- **Min Rarity**: Enforced per pack definition
- **Odds Validation**: Must sum to 1.0

### Serial Scarcity

- **Legendary**: Max 250 per season
- **Platinum**: Max 1,000 per season
- **Gold**: Max 5,000 per season
- **Community**: Max 10,000 per season

### Artist Selection

- **Hero Slot**: Score ≥ 70.0
- **Standard Slots**: Tier-based pools
- **Genre Diversity**: Maintained across packs

## 🔮 Future Enhancements

### Planned Features

- Physical card printing integration
- NFT minting capabilities
- Advanced rarity tiers
- Seasonal special editions
- Artist collaboration packs

### Extensibility

The system is designed for:
- New pack types
- Additional rarity tiers
- Custom frame styles
- Enhanced presentation options

## 📞 Support

### Debugging

- Check Flask logs for webhook processing
- Verify serial system file permissions
- Validate pack definitions on startup

### Common Issues

- **Serial Collisions**: Restart serial system
- **Pack Validation**: Check odds sum to 1.0
- **Hero Selection**: Verify artist database

---

## 🎉 Summary

This professional card system ensures:

✅ **Future NFTs map 1:1** with canonical cards  
✅ **Physical cards print cleanly** with proper layouts  
✅ **Discord UI never breaks** with consistent structure  
✅ **Creators feel premium** with hero slot system  
✅ **Rarity inflation is controlled** with serial scarcity  
✅ **Investors don't laugh at serials** with investor-grade format  

This is not just a Discord bot with cards - this is a **real card game system** built to last for years. 🚀
