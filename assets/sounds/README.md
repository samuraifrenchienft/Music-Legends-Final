# Audio Assets for Music Legends

This directory contains audio files for enhanced user feedback in the game.

## Required Audio Files

### 1. legendary_pull.mp3
**Purpose**: Played when a player pulls a legendary card from a pack
**Suggested Sound**: Epic orchestral hit, triumphant fanfare, or dramatic reveal sound
**Duration**: 2-4 seconds
**Free Sources**:
- Freesound.org: Search "epic reveal", "legendary", "fanfare"
- Zapsplat.com: Free game sounds
- YouTube Audio Library: "Victory" or "Dramatic" category

### 2. daily_claim.mp3
**Purpose**: Played when a player claims their daily reward
**Suggested Sound**: Coin sound, cash register cha-ching, or success chime
**Duration**: 1-2 seconds
**Free Sources**:
- Freesound.org: Search "coin", "cash register", "cha-ching"
- Zapsplat.com: Coin/money sounds
- YouTube Audio Library: Short positive sounds

### 3. card_pickup.mp3
**Purpose**: Played when a player claims a dropped card
**Suggested Sound**: Soft whoosh, pickup sound, or card flip
**Duration**: 0.5-1 second
**Free Sources**:
- Freesound.org: Search "whoosh", "pickup", "card flip"
- Zapsplat.com: UI sounds
- YouTube Audio Library: Quick UI sounds

### 4. pack_purchase.mp3
**Purpose**: Played when a player successfully purchases a pack
**Suggested Sound**: Cash register, success chime, or purchase confirmation
**Duration**: 1-2 seconds
**Free Sources**:
- Freesound.org: Search "purchase", "buy", "transaction"
- Zapsplat.com: Cash register or UI success sounds
- YouTube Audio Library: Positive confirmation sounds

## Technical Requirements
- **Format**: MP3 (most compatible with Discord)
- **Bitrate**: 128kbps or higher
- **Sample Rate**: 44.1kHz
- **Max File Size**: 8MB per file (Discord limit)
- **Volume**: Normalized to avoid clipping

## Usage
These files are attached to Discord messages. Users must click to play them (Discord bots cannot auto-play audio).

## Licensing
Ensure all audio files are:
- Royalty-free
- Licensed for commercial use
- Properly attributed if required

## Implementation
Audio files are referenced in:
- `views/pack_opening.py` - Legendary pulls
- `cogs/gameplay.py` - Daily claims
- `drop_system.py` - Card pickups
- `cogs/marketplace.py` - Pack purchases
