# 📚 API Reference - Music Legends Bot

## Table of Contents
1. [Database API](#database-api)
2. [Discord Commands API](#discord-commands-api)
3. [Battle Engine API](#battle-engine-api)
4. [Card Management API](#card-management-api)
5. [Spotify Integration API](#spotify-integration-api)
6. [Stripe Payments API](#stripe-payments-api)
7. [Webhook Endpoints](#webhook-endpoints)

---

## Database API

### DatabaseManager Class

#### User Management

```python
def get_or_create_user(user_id: int, username: str, discord_tag: str) -> Dict
```
**Purpose**: Get existing user or create new one in database
**Returns**: User data dictionary with all fields
**Example**:
```python
user = db.get_or_create_user(123456789, "PlayerName", "PlayerName#1234")
```

```python
def get_user_collection(user_id: int) -> List[Dict]
```
**Purpose**: Get all cards owned by a user
**Returns**: List of card dictionaries with acquisition details
**Example**:
```python
collection = db.get_user_collection(user_id)
for card in collection:
    print(f"{card['name']} - {card['rarity']}")
```

```python
def get_user_deck(user_id: int, limit: int = 3) -> List[Dict]
```
**Purpose**: Get user's battle deck (top N cards)
**Returns**: List of card dictionaries for battle
**Example**:
```python
deck = db.get_user_deck(user_id, 3)
if len(deck) < 3:
    print("Not enough cards for battle!")
```

```python
def get_user_stats(user_id: int) -> Dict
```
**Purpose**: Get comprehensive user statistics
**Returns**: Stats dictionary including win rate and totals
**Example**:
```python
stats = db.get_user_stats(user_id)
print(f"Win Rate: {stats['win_rate']:.1f}%")
print(f"Total Battles: {stats['total_battles']}")
```

#### Battle Management

```python
def record_match(match_data: Dict) -> bool
```
**Purpose**: Record a completed match and update stats
**Parameters**:
```python
match_data = {
    'match_id': 'uuid-string',
    'player_a_id': 123456789,
    'player_b_id': 987654321,
    'winner_id': 123456789,
    'final_score_a': 2,
    'final_score_b': 1,
    'match_type': 'casual'  # optional
}
```
**Returns**: True if successful, False on error

```python
def get_leaderboard(metric: str = 'wins', limit: int = 10) -> List[Dict]
```
**Purpose**: Get leaderboard by specified metric
**Valid Metrics**: 'wins', 'total_battles', 'win_rate', 'total_cards', 'packs_opened'
**Returns**: List of user rankings
**Example**:
```python
top_players = db.get_leaderboard('win_rate', 5)
for i, player in enumerate(top_players, 1):
    print(f"{i}. {player['username']}: {player['win_rate']:.1f}%")
```

#### Card Management

```python
def add_card_to_master(card_data: Dict) -> bool
```
**Purpose**: Add a card to the master card list
**Parameters**:
```python
card_data = {
    'card_id': 'unique-id',
    'name': 'Artist Name',
    'rarity': 'Rare',
    'impact': 65,
    'skill': 72,
    'longevity': 58,
    'culture': 61,
    'hype': 70,
    'image_url': 'https://...',
    'spotify_url': 'https://...',
    'card_type': 'artist'
}
```

```python
def add_card_to_collection(user_id: int, card_id: str, acquired_from: str = 'pack') -> bool
```
**Purpose**: Add a card to user's collection
**Parameters**:
- `user_id`: Discord user ID
- `card_id`: Unique card identifier
- `acquired_from`: Source ('pack', 'trade', 'reward')

#### Pack Management

```python
def create_creator_pack(creator_id: int, name: str, description: str = "", pack_size: int = 10) -> str
```
**Purpose**: Create a new creator pack in DRAFT status
**Returns**: Pack ID string
**Example**:
```python
pack_id = db.create_creator_pack(user_id, "My Pack", "Description", 10)
```

```python
def add_card_to_pack(pack_id: str, card_data: Dict) -> bool
```
**Purpose**: Add a card to pack's cards_data JSON
**Returns**: True if successful, False if pack is full

```python
def validate_pack_rules(pack_id: str) -> Dict
```
**Purpose**: Validate pack against creation rules
**Returns**:
```python
{
    'valid': bool,
    'errors': ['error messages'],
    'warnings': ['warning messages'],
    'pack_info': pack_data_dict
}
```

```python
def publish_pack(pack_id: str, stripe_payment_id: str) -> bool
```
**Purpose**: Publish pack after payment confirmation
**Returns**: True if successful

```python
def get_live_packs(limit: int = 20) -> List[Dict]
```
**Purpose**: Get all live packs for browsing
**Returns**: List of pack dictionaries with creator info

---

## Discord Commands API

### CardGameCog Commands

#### Player Commands

```python
@app_commands.command(name="card")
async def view_card(interaction: Interaction, card_id: str)
```
**Description**: View a specific card by ID
**Parameters**:
- `card_id`: Unique card identifier
**Response**: Card embed with stats and image

```python
@app_commands.command(name="collection")
async def show_collection(interaction: Interaction)
```
**Description**: Show user's card collection
**Response**: Embed grouped by rarity with card counts

```python
@app_commands.command(name="deck")
async def show_deck(interaction: Interaction)
```
**Description**: Show user's battle deck (top 3 cards)
**Response**: Embed with deck cards and total power

```python
@app_commands.command(name="stats")
async def show_stats(interaction: Interaction)
```
**Description**: View user's battle statistics
**Response**: Embed with wins, losses, win rate, etc.

```python
@app_commands.command(name="leaderboard")
async def show_leaderboard(interaction: Interaction, metric: str = "wins")
```
**Description**: View global leaderboard
**Parameters**:
- `metric`: Leaderboard category ('wins', 'total_battles', etc.)
**Response**: Top 10 players embed

```python
@app_commands.command(name="battle")
async def battle_challenge(interaction: Interaction, opponent: discord.User)
```
**Description**: Challenge another user to battle
**Parameters**:
- `opponent`: Discord user to challenge
**Response**: Challenge embed with match ID

```python
@app_commands.command(name="battle_accept")
async def battle_accept(interaction: Interaction, match_id: str)
```
**Description**: Accept a battle challenge
**Parameters**:
- `match_id`: Match ID from challenge
**Response**: Battle progression embeds

```python
@app_commands.command(name="pack")
async def open_pack(interaction: Interaction, pack_type: str = "Daily")
```
**Description**: Open a card pack
**Parameters**:
- `pack_type`: Type of pack to open
**Response**: Pack opening embed with card reveal

#### Creator Commands

```python
@app_commands.command(name="pack_create")
async def pack_create(interaction: Interaction, name: str, description: str = "", pack_size: int = 10)
```
**Description**: Create a new creator pack draft
**Parameters**:
- `name`: Pack name
- `description`: Pack description
- `pack_size`: Number of cards (5, 10, or 15)
**Response**: Pack creation confirmation embed

```python
@app_commands.command(name="pack_add_artist_smart")
async def pack_add_artist_smart(interaction: Interaction)
```
**Description**: Smart Spotify artist selection
**Response**: Modal for artist search → Selection view

```python
@app_commands.command(name="pack_add_artist")
async def pack_add_artist(interaction: Interaction, artist_name: str, rarity: str, 
                         spotify_url: str, impact: int = 50, skill: int = 50, 
                         longevity: int = 50, culture: int = 50, hype: int = 50)
```
**Description**: Manual artist card addition
**Parameters**: All card stats and details
**Response**: Card added confirmation embed

```python
@app_commands.command(name="pack_preview")
async def pack_preview(interaction: Interaction)
```
**Description**: Preview current draft pack
**Response**: Pack preview embed with validation

---

## Battle Engine API

### Core Classes

```python
@dataclass(frozen=True)
class ArtistCard:
    id: str
    name: str
    rarity: str
    impact: int
    skill: int
    longevity: int
    culture: int
    hype: int
    
    def total_power(self) -> int
    def get_stat(self, stat: Stat) -> int
```

```python
@dataclass
class PlayerState:
    user_id: int
    deck: List[ArtistCard]
    score: int = 0
    hype_bonus: int = 0
```

```python
@dataclass
class MatchState:
    match_id: str
    a: PlayerState
    b: PlayerState
    round_index: int = 0
    categories: List[Stat] = None
    last_round_loser: Optional[int] = None
    winner_user_id: Optional[int] = None
```

### Battle Functions

```python
def pick_category_option_a(match: MatchState) -> Stat
```
**Purpose**: Select category for round (random for rounds 1 & 3)
**Returns**: Selected stat category

```python
def resolve_round(card_a: ArtistCard, card_b: ArtistCard, category: Stat, 
                 hype_bonus_a: int = 0, hype_bonus_b: int = 0) -> Tuple[str, Dict]
```
**Purpose**: Resolve a single battle round
**Returns**: ("A"|"B"|"TIE", debug_dict)
**Debug Dictionary**:
```python
{
    'category': 'impact',
    'a_stat': 65,
    'b_stat': 72,
    'a_hype_bonus': 5,
    'b_hype_bonus': 0,
    'a_power': 70,
    'b_power': 72,
    'tiebreak': 'total_power'  # if applicable
}
```

```python
def apply_momentum(winner: PlayerState, loser: PlayerState) -> None
```
**Purpose**: Apply momentum bonuses after round
**Effects**: Winner gets +5 hype bonus (max 10), loser reset to 0

```python
def play_match_best_of_3(match_id: str, deck_a: List[ArtistCard], deck_b: List[ArtistCard],
                        category_round1: Optional[Stat] = None, 
                        category_round3: Optional[Stat] = None) -> Dict
```
**Purpose**: Auto-play complete best-of-3 match
**Returns**: Match result dictionary with log

---

## Card Management API

### CardDataManager Class

```python
def initialize_database_cards(self) -> None
```
**Purpose**: Initialize database with sample cards
**Effects**: Creates default card set if database is empty

```python
def generate_pack_drop(self, pack_type: str) -> List[str]
```
**Purpose**: Generate card IDs for pack opening
**Parameters**:
- `pack_type`: Type of pack ('Daily', 'Premium', etc.)
**Returns**: List of card IDs

```python
def get_card_by_id(self, card_id: str) -> Optional[Dict]
```
**Purpose**: Retrieve card data by ID
**Returns**: Card dictionary or None if not found

### Card Display Components

```python
class ArtistCard:
    def __init__(self, card_id: str, name: str, title: str, rarity: str, 
                 era: str, variant: str, impact: int, skill: int, 
                 longevity: int, culture: int, hype: int, 
                 image_url: str, spotify_url: str, youtube_url: str)
```

```python
def build_artist_embed(card: ArtistCard) -> discord.Embed
```
**Purpose**: Create Discord embed for card display
**Returns**: Formatted embed with stats and image

```python
class PackDrop:
    def __init__(self, label: str, guaranteed: str, items: List[str])
```

```python
def build_pack_open_embed(drop: PackDrop) -> discord.Embed
```
**Purpose**: Create pack opening result embed
**Returns**: Embed with pack contents

---

## Spotify Integration API

### SpotifyIntegration Class

```python
def search_artists(self, query: str, limit: int = 10) -> List[Dict]
```
**Purpose**: Search for artists on Spotify
**Parameters**:
- `query`: Artist search term
- `limit`: Maximum results (default 10)
**Returns**: List of artist dictionaries:
```python
{
    'id': 'spotify-id',
    'name': 'Artist Name',
    'popularity': 75,
    'followers': 1000000,
    'genres': ['pop', 'electronic'],
    'image_url': 'https://...',
    'spotify_url': 'https://...',
}
```

```python
def get_artist_info_from_url(self, spotify_url: str) -> Optional[Dict]
```
**Purpose**: Extract artist data from Spotify URL
**Parameters**:
- `spotify_url`: Full Spotify artist URL
**Returns**: Artist data dictionary or None

```python
def validate_spotify_url(self, url: str) -> bool
```
**Purpose**: Validate Spotify artist URL format
**Returns**: True if valid URL format

```python
def generate_card_stats(self, artist_data: Dict) -> Dict
```
**Purpose**: Generate card stats from Spotify data
**Algorithm**: Based on popularity and follower counts
**Returns**: Stats dictionary:
```python
{
    'impact': calculated_value,
    'skill': calculated_value,
    'longevity': calculated_value,
    'culture': calculated_value,
    'hype': calculated_value
}
```

```python
def determine_rarity(self, artist_data: Dict) -> str
```
**Purpose**: Determine card rarity from Spotify data
**Algorithm**: Based on popularity score
**Returns**: Rarity string ('Common', 'Rare', 'Epic', 'Legendary')

---

## Stripe Payments API

### StripeManager Class

```python
def create_payment_intent(self, amount_cents: int, pack_id: str, user_id: int) -> Dict
```
**Purpose**: Create Stripe payment intent for pack purchase
**Parameters**:
- `amount_cents`: Payment amount in cents
- `pack_id`: Pack being purchased
- `user_id`: Buyer's Discord ID
**Returns**: Stripe payment intent object

```python
def calculate_revenue_split(self, amount_cents: int) -> Dict
```
**Purpose**: Calculate platform/creator revenue split
**Returns**:
```python
{
    'platform_cents': int,  # 70% of amount
    'creator_cents': int,   # 30% of amount
    'total_cents': int
}
```

```python
def confirm_payment(self, payment_intent_id: str) -> Dict
```
**Purpose**: Confirm payment and retrieve details
**Returns**: Payment confirmation data

```python
def process_refund(self, payment_intent_id: str) -> bool
```
**Purpose**: Process payment refund
**Returns**: True if refund successful

---

## Webhook Endpoints

### Stripe Webhook Handler

```python
@app.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
```
**Purpose**: Handle Stripe webhook events
**Events Handled**:
- `payment_intent.succeeded`: Process pack purchase
- `payment_intent.payment_failed`: Handle failed payments
- `charge.dispute.created`: Handle disputes

**Security**: Validates webhook signature using `STRIPE_WEBHOOK_SECRET`

### Pack Purchase Flow

1. **Payment Intent Created**: User initiates purchase
2. **Payment Confirmation**: Stripe sends webhook
3. **Pack Processing**: Generate cards for buyer
4. **Revenue Tracking**: Record creator earnings
5. **User Notification**: Send pack opening embed

### Error Handling

```python
def handle_webhook_error(event_type: str, error: Exception) -> None
```
**Purpose**: Log webhook errors for debugging
**Effects**: Records error details and notifies admin

---

## Data Models & Schemas

### User Schema
```json
{
    "user_id": "integer",
    "username": "string",
    "discord_tag": "string",
    "created_at": "timestamp",
    "last_active": "timestamp",
    "total_battles": "integer",
    "wins": "integer",
    "losses": "integer",
    "packs_opened": "integer",
    "victory_tokens": "integer"
}
```

### Card Schema
```json
{
    "card_id": "string",
    "type": "string",
    "spotify_artist_id": "string",
    "name": "string",
    "title": "string",
    "rarity": "string",
    "impact": "integer",
    "skill": "integer",
    "longevity": "integer",
    "culture": "integer",
    "hype": "integer",
    "image_url": "string",
    "spotify_url": "string",
    "youtube_url": "string",
    "created_at": "timestamp"
}
```

### Match Schema
```json
{
    "match_id": "string",
    "player_a_id": "integer",
    "player_b_id": "integer",
    "winner_id": "integer",
    "final_score_a": "integer",
    "final_score_b": "integer",
    "started_at": "timestamp",
    "completed_at": "timestamp",
    "match_type": "string"
}
```

### Pack Schema
```json
{
    "pack_id": "string",
    "creator_id": "integer",
    "name": "string",
    "description": "string",
    "pack_size": "integer",
    "status": "string",
    "price_cents": "integer",
    "total_purchases": "integer",
    "cards_data": "json_array",
    "created_at": "timestamp",
    "published_at": "timestamp"
}
```

---

## Error Handling

### Database Errors
- `sqlite3.Error`: Database operation failures
- **Handling**: Log error and return False/None

### API Integration Errors
- **Spotify**: Rate limiting, invalid tokens
- **Stripe**: Payment failures, webhook errors
- **Handling**: Retry logic, user notifications

### Discord Bot Errors
- **Permissions**: Missing bot permissions
- **Rate Limits**: Discord API rate limiting
- **Handling**: Graceful degradation, error messages

---

## Testing Examples

### Unit Tests
```python
def test_battle_resolution():
    card_a = ArtistCard("1", "Artist A", "Rare", 80, 70, 60, 75, 65)
    card_b = ArtistCard("2", "Artist B", "Rare", 70, 80, 65, 60, 70)
    
    winner, debug = resolve_round(card_a, card_b, "impact")
    assert winner == "A"
    assert debug['a_power'] > debug['b_power']
```

### Integration Tests
```python
def test_pack_creation_flow():
    # Create pack
    pack_id = db.create_creator_pack(user_id, "Test Pack", "", 10)
    
    # Add card
    card_data = {'name': 'Test Artist', 'rarity': 'Common', ...}
    success = db.add_card_to_pack(pack_id, card_data)
    assert success
    
    # Validate
    validation = db.validate_pack_rules(pack_id)
    assert not validation['valid']  # Pack not full yet
```

---

This API reference provides comprehensive documentation for all major components of the Music Legends Discord bot. Use this guide for integration, development, and troubleshooting purposes.
