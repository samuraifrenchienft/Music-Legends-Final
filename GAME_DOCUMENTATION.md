# 🎵 Music Legends - Complete Game Documentation

## Table of Contents
1. [Game Overview](#game-overview)
2. [Core Gameplay Mechanics](#core-gameplay-mechanics)
3. [Card System](#card-system)
4. [Battle System](#battle-system)
5. [Pack Creation & Economy](#pack-creation--economy)
6. [Player Progression](#player-progression)
7. [Database Architecture](#database-architecture)
8. [API Reference](#api-reference)
9. [Development Guide](#development-guide)

---

## Game Overview

**Music Legends** is a Discord-based card collecting and battling game focused on music artists. Players collect artist cards, build decks, and compete in strategic battles while creators can design and sell custom card packs.

### Key Features
- **Card Collection**: Collect artist cards with real music data
- **Strategic Battles**: Best-of-3 PvP matches with stat-based combat
- **Creator Economy**: Design and monetize custom card packs
- **Progression System**: Stats, leaderboards, and achievements
- **Dual Media Integration**: Spotify for artist data + YouTube for video content

---

## Core Gameplay Mechanics

### Card Stats System

Each artist card has five core stats:

| Stat | Description | Max Value |
|------|-------------|-----------|
| **Impact** | Overall influence and popularity | 100 |
| **Skill** | Technical ability and artistry | 100 |
| **Longevity** | Career endurance and relevance | 100 |
| **Culture** | Cultural significance and impact | 100 |
| **Hype** | Current momentum (tie-breaker) | 100 |

### Rarity System

Cards are classified into five rarity tiers:

| Rarity | Color Emoji | Stat Range | Drop Rate |
|--------|-------------|------------|-----------|
| **Common** | 🟩 | 0-39 | 45% |
| **Rare** | 🟦 | 40-59 | 30% |
| **Epic** | 🟪 | 60-74 | 20% |
| **Legendary** | ⭐ | 75-89 | 4.5% |
| **Mythic** | 🔴 | 90-100 | 0.5% (Official packs only) |

### Battle Categories

Battles are fought across four main categories:
- **Impact**: Raw popularity and reach
- **Skill**: Technical proficiency and artistry  
- **Longevity**: Career sustainability and endurance
- **Culture**: Cultural impact and significance

---

## Card System

### Card Structure

```python
{
    "card_id": "unique_identifier",
    "name": "Artist Name",
    "rarity": "Rare",
    "impact": 65,
    "skill": 72,
    "longevity": 58,
    "culture": 61,
    "hype": 70,
    "image_url": "https://...",
    "spotify_url": "https://open.spotify.com/artist/...",
    "spotify_id": "spotify_artist_id",
    "genres": ["pop", "electronic"],
    "card_type": "artist"
}
```

### Card Acquisition

1. **Daily Packs**: Free pack every 24 hours
2. **Creator Packs**: Purchase custom packs from other users
3. **Victory Tokens**: Guaranteed rewards from battle wins
4. **Special Events**: Limited-time promotional packs

### Collection Management

- **Deck Building**: Select top 3 cards for battle
- **Favorites**: Mark favorite cards for quick access
- **Trade System**: (Planned feature) Exchange cards with other players

---

## Battle System

### Match Format

- **Best-of-3 Rounds**: First to win 2 rounds wins the match
- **3-Card Decks**: Each player uses their top 3 cards
- **Category Selection**: Round 1 (random) → Round 2 (loser picks) → Round 3 (random)

### Battle Resolution

1. **Stat Comparison**: Compare selected category stats
2. **Hype Bonus**: Apply momentum bonuses (+5 per win, max +10)
3. **Tie-Breakers**:
   - Higher Hype stat
   - Higher total power
   - Coin flip (rare)

### Momentum System

- Winners gain +5 hype bonus next round (capped at +10)
- Losers have their hype bonus reset to 0
- Creates strategic depth and comeback potential

### Match Rewards

- **Winner**: +1 Victory Token (guaranteed pack)
- **Loser**: Small consolation reward
- **Both Players**: Updated stats and leaderboard position

---

## Pack Creation & Economy

### Creator Pack System

Users can create and sell custom card packs:

#### Pack Sizes & Pricing
- **Micro Pack** (5 cards): $10.00
- **Mini Pack** (10 cards): $25.00  
- **Event Pack** (15 cards): $50.00

#### Creator Restrictions
- **1 live pack** per creator at a time
- **7-day cooldown** between publications
- **Maximum 92** stats per card (creator packs only)
- **No Mythic rarity** cards in creator packs

#### Revenue Split
- **Platform**: 70% of revenue
- **Creator**: 30% of revenue
- **Payment Processing**: Handled via Stripe

### Pack Creation Process

1. **Create Draft**: `/pack_create <name> <description> <size>`
2. **Add Artists**: 
   - Smart selection: `/pack_add_artist_smart` (Spotify integration)
   - Manual entry: `/pack_add_artist` (custom stats)
3. **Preview**: `/pack_preview` to validate
4. **Publish**: `/pack_publish` (requires payment)
5. **Sales**: Pack goes live in marketplace

### Smart Artist Selection

The bot integrates with both Spotify and YouTube to:
- **Spotify**: Search for artists, auto-generate stats based on popularity/followers, determine appropriate rarity, enrich cards with real data (images, genres, links)
- **YouTube**: Find official music videos, provide visual content, enhance card displays with video thumbnails, offer multimedia artist content

---

## Player Progression

### User Statistics

Tracked metrics include:
- **Total Battles**: Overall match count
- **Win/Loss Record**: Battle performance
- **Win Rate**: Percentage of victories
- **Cards Collected**: Total unique cards owned
- **Packs Opened**: Total packs claimed
- **Victory Tokens**: Current token balance

### Leaderboard System

Multiple leaderboard categories:
- **Most Wins**: Total victory count
- **Highest Win Rate**: Best win percentage (min 5 battles)
- **Most Battles**: Most matches played
- **Largest Collection**: Most cards owned
- **Pack Opener**: Most packs opened

### Achievement System (Planned)

Future achievements may include:
- **First Victory**: Win your first battle
- **Collector**: Collect 100 cards
- **Creator**: Publish first pack
- **Master**: Reach 80% win rate
- **Legend**: Collect a Mythic card

---

## Database Architecture

### Core Tables

#### Users
```sql
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    discord_tag TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_battles INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    packs_opened INTEGER DEFAULT 0,
    victory_tokens INTEGER DEFAULT 0
);
```

#### Cards
```sql
CREATE TABLE cards (
    card_id TEXT PRIMARY KEY,
    type TEXT NOT NULL DEFAULT 'artist',
    spotify_artist_id TEXT,
    name TEXT NOT NULL,
    rarity TEXT NOT NULL,
    impact INTEGER,
    skill INTEGER,
    longevity INTEGER,
    culture INTEGER,
    hype INTEGER,
    image_url TEXT,
    spotify_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Matches
```sql
CREATE TABLE matches (
    match_id TEXT PRIMARY KEY,
    player_a_id INTEGER,
    player_b_id INTEGER,
    winner_id INTEGER,
    final_score_a INTEGER,
    final_score_b INTEGER,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    match_type TEXT DEFAULT 'casual'
);
```

#### Creator Packs
```sql
CREATE TABLE creator_packs (
    pack_id TEXT PRIMARY KEY,
    creator_id INTEGER,
    name TEXT NOT NULL,
    description TEXT,
    pack_size INTEGER DEFAULT 10,
    status TEXT DEFAULT 'DRAFT',
    price_cents INTEGER DEFAULT 500,
    total_purchases INTEGER DEFAULT 0,
    cards_data TEXT, -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP
);
```

### Data Relationships

- **Users** → **user_cards** → **cards** (ownership)
- **Users** → **matches** (participation)
- **Users** → **creator_packs** (creation)
- **creator_packs** → **pack_purchases** (sales)
- **matches** → **match_rounds** (detailed results)

---

## API Reference

### Discord Slash Commands

#### Player Commands
```
/pack [type]                    - Open a card pack
/collection                     - View your card collection
/deck                          - View your battle deck
/stats                         - View your statistics
/leaderboard [metric]          - View global rankings
/battle <opponent>             - Challenge to battle
/battle_accept <match_id>      - Accept battle challenge
/card <card_id>                - View specific card
```

#### Creator Commands
```
/pack_create <name> <desc> <size>  - Create new pack draft
/pack_add_artist_smart              - Smart artist selection
/pack_add_artist <details>          - Manual artist addition
/pack_preview                       - Preview draft pack
/pack_publish                      - Publish pack (payment)
/pack_cancel                       - Cancel draft pack
/packs                             - Browse available packs
```

### Database Methods

#### User Management
```python
db.get_or_create_user(user_id, username, discord_tag)
db.get_user_collection(user_id)
db.get_user_deck(user_id, limit=3)
db.get_user_stats(user_id)
```

#### Battle System
```python
db.record_match(match_data)
db.get_leaderboard(metric, limit)
```

#### Pack Management
```python
db.create_creator_pack(creator_id, name, description, pack_size)
db.add_card_to_pack(pack_id, card_data)
db.validate_pack_rules(pack_id)
db.publish_pack(pack_id, stripe_payment_id)
db.get_live_packs(limit)
```

---

## Development Guide

### Environment Setup

1. **Clone Repository**
```bash
git clone https://github.com/samuraifrenchienft/Music-Legends.git
cd Music-Legends
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Environment Variables**
```bash
cp .env.txt.example .env.txt
# Edit .env.txt with your credentials
```

### Required Environment Variables

```env
# Discord Bot
BOT_TOKEN=your_discord_bot_token
APPLICATION_ID=your_application_id
TEST_SERVER_ID=your_test_server_id

# Optional Integrations
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
STRIPE_SECRET_KEY=sk_test_your_stripe_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
YOUTUBE_API_KEY=your_youtube_api_key
```

### Project Structure

```
discordpy-v2-bot-template-main/
├── main.py                 # Bot entry point
├── database.py            # Database management
├── battle_engine.py       # Battle logic
├── card_data.py          # Card data management
├── discord_cards.py      # Card display components
├── cogs/                 # Discord command modules
│   ├── card_game.py      # Core game commands
│   ├── example.py        # Example cog
│   └── ...
├── infrastructure/        # Bot infrastructure
├── scheduler/           # Background jobs
└── requirements.txt     # Dependencies
```

### Key Components

#### Battle Engine (`battle_engine.py`)
- Core battle logic and resolution
- Stat comparison and tie-breaking
- Momentum system implementation
- Match state management

#### Database Manager (`database.py`)
- SQLite database operations
- User data persistence
- Pack creation and validation
- Revenue tracking

#### Card Game Cog (`cogs/card_game.py`)
- Discord slash command handlers
- User interaction flows
- Pack creation interface
- Battle matchmaking

### Testing

```bash
# Run basic bot test
python test_bot.py

# Test individual components
python -m pytest tests/
```

### Deployment Considerations

1. **Database**: SQLite (file-based) - no external DB required
2. **Webhooks**: Stripe webhook endpoint for payment processing
3. **Background Jobs**: APScheduler for daily pack resets
4. **Queue System**: Redis + RQ for async processing
5. **Scaling**: Horizontal scaling via Redis shared state

---

## Contributing

### Code Style
- Follow PEP 8 Python standards
- Use type hints where appropriate
- Document complex logic with comments
- Write unit tests for new features

### Development Workflow
1. Fork the repository
2. Create feature branch
3. Implement changes with tests
4. Submit pull request
5. Code review and merge

### Feature Ideas
- Song cards with special effects
- Tournament mode with brackets
- Card trading marketplace
- Guild/team system
- Mobile app companion
- NFT integration for rare cards

---

## Support & Community

- **Discord Server**: [Join our community](https://discord.gg/yourserver)
- **GitHub Issues**: [Report bugs and request features](https://github.com/samuraifrenchienft/Music-Legends/issues)
- **Documentation Wiki**: [Extended documentation](https://github.com/samuraifrenchienft/Music-Legends/wiki)

---

**Built with ❤️ for the Discord music community**
