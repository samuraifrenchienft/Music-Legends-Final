# 🛠️ Developer Guide - Music Legends Bot

## Table of Contents
1. [Quick Start](#quick-start)
2. [Development Environment Setup](#development-environment-setup)
3. [Project Architecture](#project-architecture)
4. [Code Structure](#code-structure)
5. [Database Setup](#database-setup)
6. [Testing](#testing)
7. [Debugging](#debugging)
8. [Deployment](#deployment)
9. [Contributing Guidelines](#contributing-guidelines)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites
- **Python 3.8+** - Bot framework requirement
- **Discord Account** - For bot application creation
- **Git** - For version control
- **Code Editor** - VS Code recommended

### 5-Minute Setup

1. **Clone & Install**
```bash
git clone https://github.com/samuraifrenchienft/Music-Legends.git
cd Music-Legends
pip install -r requirements.txt
```

2. **Configure Bot**
```bash
cp .env.txt.example .env.txt
# Edit .env.txt with your Discord bot token
```

3. **Run Bot**
```bash
python main.py
```

---

## Development Environment Setup

### 1. Discord Bot Setup

#### Create Discord Application
1. Visit [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Enter application name (e.g., "Music Legends Bot")
4. Go to "Bot" tab and click "Add Bot"

#### Configure Bot Permissions
**Bot Token**: Keep secure - add to `.env.txt`
**Privileged Gateway Intents**:
- ✅ **Message Content Intent** - Required for command processing
- ✅ **Server Members Intent** - For user management
- ✅ **Presence Intent** - For user status
- ✅ **Reaction Intent** - For pack opening interactions

#### OAuth2 URL Generator
**Scopes Required**:
- `bot`
- `applications.commands`

**Bot Permissions**:
- Send Messages
- Embed Links
- Use External Emojis
- Add Reactions
- Read Message History

### 2. Environment Configuration

#### Required Variables (.env.txt)
```env
# Discord Bot Configuration
BOT_TOKEN=your_bot_token_here
APPLICATION_ID=your_application_id_here
TEST_SERVER_ID=your_test_server_id_here_or_0_for_global
```

#### Optional Integrations
```env
# Spotify Integration (for artist data)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

# Stripe Payments (for creator packs)
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# YouTube Integration (for music videos)
YOUTUBE_API_KEY=your_youtube_api_key

# Redis (for production queue processing)
REDIS_URL=redis://localhost:6379
```

### 3. IDE Configuration

#### VS Code Extensions (Recommended)
- **Python** - Microsoft Python extension
- **Pylance** - Enhanced IntelliSense
- **Python Docstring Generator** - Auto-documentation
- **GitLens** - Enhanced Git capabilities
- **Docker** - For containerization

#### VS Code Settings (.vscode/settings.json)
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
```

---

## Project Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Discord Bot   │    │   Battle Engine │    │   Database      │
│                 │    │                 │    │                 │
│ • Commands      │◄──►│ • Game Logic    │◄──►│ • SQLite        │
│ • UI Components │    │ • Stat Calc     │    │ • User Data     │
│ • Interactions  │    │ • Match Mgmt    │    │ • Pack Data     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ External APIs   │    │   Queue System  │    │   Web Server   │
│                 │    │                 │    │                 │
│ • Spotify       │    │ • Redis         │    │ • Stripe Hooks  │
│ • YouTube       │    │ • Background    │    │ • Payment Proc  │
│ • Stripe        │    │ • Async Tasks   │    │ • Webhooks      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Component Interactions

1. **User Interaction** → Discord Bot Command
2. **Command Processing** → Database Query/Update
3. **Game Logic** → Battle Engine Calculation
4. **External Data** → Spotify/YouTube API Calls
5. **Payment Processing** → Stripe Integration
6. **Background Tasks** → Queue System Processing

---

## Code Structure

### Directory Layout

```
discordpy-v2-bot-template-main/
├── main.py                    # Bot entry point and setup
├── database.py               # Database management layer
├── battle_engine.py          # Core battle logic
├── card_data.py             # Card data management
├── discord_cards.py         # Discord UI components
├── requirements.txt          # Python dependencies
├── .env.txt.example         # Environment template
├── README.md                # Project overview
├── GAME_DOCUMENTATION.md    # Game rules & mechanics
├── API_REFERENCE.md         # API documentation
├── DEVELOPER_GUIDE.md       # This file
│
├── cogs/                    # Discord command modules
│   ├── card_game.py        # Core game commands
│   ├── example.py          # Example cog template
│   └── [additional_cogs]    # Feature-specific commands
│
├── infrastructure/          # Bot infrastructure
│   ├── __init__.py
│   ├── discord_infra.py    # Discord setup
│   ├── database_infra.py   # Database connections
│   └── external_apis.py    # API integrations
│
├── scheduler/              # Background job system
│   ├── __init__.py
│   ├── cron.py            # Cron job manager
│   └── jobs.py            # Scheduled tasks
│
├── payments/               # Payment processing
│   ├── stripe_payments.py # Stripe integration
│   └── webhook_server.py  # Payment webhooks
│
├── integrations/           # External API integrations
│   ├── spotify_integration.py # Spotify API
│   └── youtube_integration.py # YouTube API
│
└── tests/                 # Test suite
    ├── test_battle_engine.py
    ├── test_database.py
    └── test_commands.py
```

### Core Files Explained

#### main.py - Bot Entry Point
```python
# Key responsibilities:
# - Initialize Discord bot with proper intents
# - Load environment variables
# - Set up infrastructure components
# - Load command cogs
# - Sync slash commands
# - Handle bot lifecycle events
```

#### database.py - Data Layer
```python
# Key responsibilities:
# - SQLite database initialization
# - User management and statistics
# - Card collection tracking
# - Match history recording
# - Pack creation and validation
# - Revenue tracking
```

#### battle_engine.py - Game Logic
```python
# Key responsibilities:
# - Card stat comparison logic
# - Battle resolution mechanics
# - Momentum system implementation
- Tie-breaking algorithms
# - Match state management
```

#### cogs/card_game.py - Discord Commands
```python
# Key responsibilities:
# - Slash command definitions
# - User interaction handling
# - Discord UI components (modals, views)
# - Response formatting and embeds
# - Error handling and user feedback
```

---

## Database Setup

### SQLite Database

The bot uses SQLite for data persistence - no external database required.

#### Automatic Initialization
```python
# Database is created automatically on first run
db_path = "music_legends.db"
DatabaseManager(db_path).init_database()
```

#### Schema Overview
- **Users**: Player accounts and statistics
- **Cards**: Master card list with Spotify data
- **user_cards**: Card ownership tracking
- **matches**: Battle history and results
- **creator_packs**: Custom pack definitions
- **pack_purchases**: Transaction records
- **revenue_ledger**: Financial tracking

#### Database Operations

##### Adding New Tables
```python
def add_new_table(self):
    with sqlite3.connect(self.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS new_table (
                id INTEGER PRIMARY KEY,
                field1 TEXT,
                field2 INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
```

##### Database Migrations
```python
def migrate_database(self):
    """Handle database schema updates"""
    with sqlite3.connect(self.db_path) as conn:
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'new_field' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN new_field TEXT")
        
        conn.commit()
```

---

## Testing

### Test Structure

#### Unit Tests
```python
# tests/test_battle_engine.py
import pytest
from battle_engine import ArtistCard, resolve_round

def test_battle_resolution():
    card_a = ArtistCard("1", "Artist A", "Rare", 80, 70, 60, 75, 65)
    card_b = ArtistCard("2", "Artist B", "Rare", 70, 80, 65, 60, 70)
    
    winner, debug = resolve_round(card_a, card_b, "impact")
    assert winner == "A"
    assert debug['a_power'] > debug['b_power']

def test_tie_breaker():
    card_a = ArtistCard("1", "Artist A", "Rare", 70, 70, 70, 70, 80)
    card_b = ArtistCard("2", "Artist B", "Rare", 70, 70, 70, 70, 70)
    
    winner, debug = resolve_round(card_a, card_b, "impact")
    assert winner == "A"  # Higher hype wins tie
    assert debug['tiebreak'] == "hype"
```

#### Integration Tests
```python
# tests/test_database.py
import pytest
from database import DatabaseManager

@pytest.fixture
def db():
    return DatabaseManager(":memory:")

def test_user_creation(db):
    user = db.get_or_create_user(123, "TestUser", "TestUser#1234")
    assert user['user_id'] == 123
    assert user['username'] == "TestUser"
    assert user['total_battles'] == 0

def test_pack_creation_flow(db):
    pack_id = db.create_creator_pack(123, "Test Pack", "", 10)
    assert pack_id is not None
    
    card_data = {
        'name': 'Test Artist',
        'rarity': 'Common',
        'impact': 50,
        'skill': 50,
        'longevity': 50,
        'culture': 50,
        'hype': 50
    }
    
    success = db.add_card_to_pack(pack_id, card_data)
    assert success
```

#### Discord Bot Testing
```python
# tests/test_commands.py
import pytest
from discord.ext.test import bot, context
from cogs.card_game import CardGameCog

@pytest.mark.asyncio
async def test_pack_command(bot):
    cog = CardGameCog(bot)
    
    # Mock user interaction
    ctx = context.message()
    ctx.author.id = 123
    
    await cog.open_pack(ctx, "Daily")
    
    # Verify response
    assert ctx.sent is not None
    assert "Pack" in ctx.sent.content
```

### Running Tests

#### Setup Testing Environment
```bash
# Install test dependencies
pip install pytest pytest-asyncio discord.py[test]

# Create test database (in-memory)
export TEST_DATABASE=":memory:"
```

#### Execute Test Suite
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_battle_engine.py

# Run with coverage
pytest --cov=. --cov-report=html

# Run with verbose output
pytest -v
```

### Test Data Management

#### Fixtures for Test Data
```python
# tests/fixtures.py
import pytest

@pytest.fixture
def sample_card():
    return {
        'card_id': 'test_card_1',
        'name': 'Test Artist',
        'rarity': 'Rare',
        'impact': 65,
        'skill': 72,
        'longevity': 58,
        'culture': 61,
        'hype': 70
    }

@pytest.fixture
def sample_user():
    return {
        'user_id': 123456789,
        'username': 'TestUser',
        'discord_tag': 'TestUser#1234'
    }
```

---

## Debugging

### Common Issues & Solutions

#### Bot Won't Start
```python
# Check environment variables
import os
from dotenv import load_dotenv

load_dotenv('.env.txt')
required_vars = ['BOT_TOKEN', 'APPLICATION_ID', 'TEST_SERVER_ID']

for var in required_vars:
    if not os.getenv(var):
        print(f"Missing required environment variable: {var}")
```

#### Database Connection Issues
```python
# Check database file permissions
import os
from pathlib import Path

db_path = Path("music_legends.db")
if db_path.exists():
    print(f"Database exists: {db_path}")
    print(f"Permissions: {oct(db_path.stat().st_mode)}")
else:
    print("Database file not found - will be created on first run")
```

#### Discord API Rate Limits
```python
# Add rate limiting to commands
import asyncio
from discord.ext import commands

@commands.cooldown(1, 5, commands.BucketType.user)  # 1 use per 5 seconds
async def some_command(ctx):
    await ctx.send("This command is rate limited")
```

#### Spotify API Issues
```python
# Debug Spotify integration
from integrations.spotify_integration import spotify_integration

async def test_spotify():
    try:
        artists = spotify_integration.search_artists("test artist")
        print(f"Found {len(artists)} artists")
        for artist in artists[:3]:
            print(f"- {artist['name']} (popularity: {artist['popularity']})")
    except Exception as e:
        print(f"Spotify error: {e}")
```

### Debugging Tools

#### Logging Configuration
```python
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# Add to main.py
logger = logging.getLogger(__name__)
logger.info("Bot starting up...")
```

#### Database Query Debugging
```python
# Enable SQLite query logging
import sqlite3

def debug_query(query, params=()):
    print(f"SQL: {query}")
    print(f"Params: {params}")
    
    with sqlite3.connect("music_legends.db") as conn:
        conn.set_trace_callback(print)
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
```

#### Discord Interaction Debugging
```python
# Add debug information to command responses
import traceback

async def debug_command(ctx):
    try:
        # Your command logic here
        await ctx.send("Command executed successfully")
    except Exception as e:
        error_msg = f"Error: {str(e)}\n```\n{traceback.format_exc()}\n```"
        await ctx.send(error_msg)
```

---

## Deployment

### Production Deployment Options

#### 1. Self-Hosted (VPS/Dedicated Server)

**System Requirements**:
- **CPU**: 2+ cores recommended
- **RAM**: 2GB+ minimum
- **Storage**: 20GB+ SSD
- **OS**: Ubuntu 20.04+ or CentOS 8+

**Setup Steps**:
```bash
# 1. Server setup
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip git -y

# 2. Clone and setup
git clone https://github.com/samuraifrenchienft/Music-Legends.git
cd Music-Legends
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.txt.example .env.txt
nano .env.txt  # Edit with production values

# 4. Setup systemd service
sudo nano /etc/systemd/system/music-legends.service
```

**Systemd Service Configuration**:
```ini
[Unit]
Description=Music Legends Discord Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Music-Legends
Environment=PATH=/home/ubuntu/Music-Legends/venv/bin
ExecStart=/home/ubuntu/Music-Legends/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Start service
sudo systemctl enable music-legends
sudo systemctl start music-legends
sudo systemctl status music-legends
```

#### 2. Docker Deployment

**Dockerfile**:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Expose port for webhooks
EXPOSE 5000

# Start the bot
CMD ["python", "main.py"]
```

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  bot:
    build: .
    restart: unless-stopped
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - APPLICATION_ID=${APPLICATION_ID}
      - TEST_SERVER_ID=0
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    volumes:
      - ./data:/app/data

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

  webhook-server:
    build: .
    command: python webhook_server.py
    ports:
      - "5000:5000"
    environment:
      - STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET}

volumes:
  redis_data:
```

#### 3. Cloud Platform Deployment

**Heroku**:
```bash
# Install Heroku CLI
# Create Procfile
echo "web: python main.py" > Procfile

# Deploy
heroku create music-legends-bot
heroku config:set BOT_TOKEN=your_token
heroku config:set APPLICATION_ID=your_app_id
git push heroku main
```

**AWS Lambda** (Serverless):
- Use `zappa` for serverless deployment
- Configure API Gateway for webhooks
- Use DynamoDB for data persistence

### Environment Management

#### Production .env Configuration
```env
# Production settings
BOT_TOKEN=prod_bot_token
APPLICATION_ID=prod_app_id
TEST_SERVER_ID=0  # Global commands

# Production APIs
SPOTIFY_CLIENT_ID=prod_spotify_id
SPOTIFY_CLIENT_SECRET=prod_spotify_secret
STRIPE_SECRET_KEY=sk_live_prod_key
STRIPE_WEBHOOK_SECRET=whsec_prod_webhook

# Production infrastructure
REDIS_URL=redis://prod-redis:6379
DATABASE_URL=sqlite:///prod_music_legends.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/music-legends/bot.log
```

#### Health Checks
```python
# health_check.py
import asyncio
import discord
from database import DatabaseManager

async def health_check():
    """Verify all systems are operational"""
    checks = {
        'database': False,
        'discord_api': False,
        'external_apis': False
    }
    
    # Check database
    try:
        db = DatabaseManager()
        db.get_or_create_user(0, "health_check", "health#check")
        checks['database'] = True
    except Exception as e:
        print(f"Database check failed: {e}")
    
    # Check Discord API
    try:
        # Test Discord connection
        checks['discord_api'] = True
    except Exception as e:
        print(f"Discord API check failed: {e}")
    
    return checks

if __name__ == "__main__":
    status = asyncio.run(health_check())
    print(f"Health check results: {status}")
```

---

## Contributing Guidelines

### Code Standards

#### Python Style Guide
- **PEP 8** compliance
- **Type hints** for all function signatures
- **Docstrings** for all public functions and classes
- **Maximum line length**: 88 characters (Black formatter)

#### Code Example
```python
from typing import List, Dict, Optional
import discord
from discord.ext import commands

class ExampleCog(commands.Cog):
    """Example cog demonstrating proper code style."""
    
    def __init__(self, bot: commands.Bot) -> None:
        """Initialize the cog with bot instance."""
        self.bot = bot
        self.db = DatabaseManager()
    
    @app_commands.command(name="example")
    @app_commands.describe(
        parameter="Example parameter description"
    )
    async def example_command(
        self, 
        interaction: discord.Interaction, 
        parameter: str
    ) -> None:
        """
        Execute example command.
        
        Args:
            interaction: Discord interaction object
            parameter: Command parameter value
            
        Raises:
            ValueError: If parameter is invalid
        """
        if not parameter:
            raise ValueError("Parameter cannot be empty")
            
        await interaction.response.send_message(
            f"Parameter received: {parameter}"
        )
```

### Git Workflow

#### Branch Naming Convention
- `feature/feature-name` - New features
- `bugfix/issue-description` - Bug fixes
- `hotfix/urgent-fix` - Critical fixes
- `docs/documentation-update` - Documentation changes

#### Commit Message Format
```
type(scope): description

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(battle): add momentum system to battles

Implement hype bonus accumulation across rounds
with maximum cap of +10. Winners gain +5 bonus,
losers reset to 0.

Closes #123
```

```
fix(database): resolve pack creation validation error

Add proper error handling for invalid pack sizes
and improve validation messages for users.
```

### Pull Request Process

#### PR Template
```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Environment variables documented
```

#### Review Process
1. **Automated Checks**: CI/CD pipeline runs tests
2. **Code Review**: At least one maintainer approval
3. **Testing**: Manual verification in test environment
4. **Merge**: Squash merge to main branch

### Development Workflow

#### 1. Setup Development Environment
```bash
# Fork and clone repository
git clone https://github.com/your-username/Music-Legends.git
cd Music-Legends

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Setup pre-commit hooks
pre-commit install
```

#### 2. Create Feature Branch
```bash
git checkout -b feature/your-feature-name
```

#### 3. Make Changes
- Write code following style guidelines
- Add tests for new functionality
- Update documentation
- Run tests locally

#### 4. Submit Pull Request
```bash
git add .
git commit -m "feat: add your feature description"
git push origin feature/your-feature-name
```

---

## Troubleshooting

### Common Issues

#### Bot Token Issues
**Problem**: "Invalid Token" error
**Solution**:
1. Verify token in Discord Developer Portal
2. Check for extra spaces/newlines in .env.txt
3. Ensure bot is enabled in application settings

#### Permission Issues
**Problem**: Bot can't read messages or use commands
**Solution**:
1. Re-invite bot with proper scopes
2. Check server role permissions
3. Verify channel-specific permissions

#### Database Lock Issues
**Problem**: "database is locked" errors
**Solution**:
1. Check for long-running transactions
2. Ensure proper connection closing
3. Consider connection pooling for high traffic

#### Memory Issues
**Problem**: Bot memory usage increases over time
**Solution**:
1. Check for memory leaks in command handlers
2. Implement proper cleanup in cog unload
3. Monitor active matches and cleanup old ones

#### Rate Limiting
**Problem**: Discord API rate limits
**Solution**:
1. Implement command cooldowns
2. Use burst rate limiting
3. Queue non-critical operations

### Debugging Commands

#### Health Check Command
```python
@app_commands.command(name="health")
async def health_check(interaction: Interaction):
    """Check bot health and status"""
    try:
        # Test database
        db = DatabaseManager()
        user_count = len(db.get_leaderboard('wins', 1))
        
        # Test external APIs
        spotify_status = "✅ Connected" if spotify_integration.test_connection() else "❌ Disconnected"
        
        embed = discord.Embed(
            title="🏥 Bot Health Status",
            color=discord.Color.green()
        )
        embed.add_field(name="Database", value=f"✅ Operational ({user_count} users)", inline=False)
        embed.add_field(name="Spotify API", value=spotify_status, inline=False)
        embed.add_field(name="Memory Usage", value=f"{psutil.Process().memory_info().rss / 1024 / 1024:.1f} MB", inline=False)
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Health check failed: {str(e)}")
```

#### Debug Database State
```python
@app_commands.command(name="debug_db")
async def debug_database(interaction: Interaction):
    """Show database statistics for debugging"""
    if interaction.user.id not in ADMIN_USERS:
        await interaction.response.send_message("Admin only", ephemeral=True)
        return
    
    db = DatabaseManager()
    
    stats = {
        'Users': len(db.get_leaderboard('wins', 1000)),
        'Cards': len(db.get_all_cards()),
        'Matches': len(db.get_recent_matches(100)),
        'Packs': len(db.get_live_packs(100))
    }
    
    embed = discord.Embed(title="🔍 Database Debug Info", color=discord.Color.blue())
    for key, value in stats.items():
        embed.add_field(name=key, value=str(value), inline=True)
    
    await interaction.response.send_message(embed=embed)
```

### Performance Optimization

#### Database Optimization
```python
# Add indexes for frequently queried fields
cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_cards_user_id ON user_cards(user_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_player_a ON matches(player_a_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_player_b ON matches(player_b_id)")
```

#### Caching Strategy
```python
# Implement simple caching for frequently accessed data
from functools import lru_cache
from typing import Dict

class CacheManager:
    @staticmethod
    @lru_cache(maxsize=128)
    def get_user_stats_cached(user_id: int) -> Dict:
        """Cache user stats to reduce database queries"""
        db = DatabaseManager()
        return db.get_user_stats(user_id)
    
    @staticmethod
    def clear_user_cache(user_id: int):
        """Clear cache for specific user after updates"""
        CacheManager.get_user_stats_cached.cache_clear()
```

#### Async Operations
```python
# Use async for long-running operations
import asyncio

async def async_pack_opening(user_id: int, pack_type: str):
    """Async pack opening to prevent blocking"""
    # Generate cards asynchronously
    cards = await asyncio.to_thread(generate_pack_cards, pack_type)
    
    # Update database asynchronously
    await asyncio.to_thread(record_pack_opening, user_id, pack_type, cards)
    
    return cards
```

---

This developer guide provides comprehensive information for setting up, developing, testing, and deploying the Music Legends Discord bot. Follow these guidelines to ensure smooth development and production operations.
