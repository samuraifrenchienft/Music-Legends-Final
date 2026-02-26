# Music Legends Sound Effects Implementation

## Overview
This document describes how sound effects enhance the Music Legends game experience.

## Sound Effects Implemented

### 1. Pack Opening Sound (`pack_opening.mp3`)
**When**: Plays at the start when a player opens a pack
**Purpose**: Creates excitement and anticipation
**Suggested Sound**: 
- Whoosh or air release sound (2-3 seconds)
- Card box opening sound
- Magical reveal effect

**Free Sources**:
- Freesound.org: Search "pack open", "box open", "reveal"
- Zapsplat.com: UI and gaming sounds
- YouTube Audio Library: "Reveal" or "Mystery" sounds

### 2. Legendary Card Sound (`legendary_pull.mp3`)
**When**: Plays when a legendary (rare) card is revealed during pack opening
**Purpose**: Celebrates the rare pull with triumph and excitement
**Suggested Sound**:
- Epic orchestral fanfare (3-4 seconds)
- Winning/victory trumpet
- Dramatic reveal chord progression
- "You won!" achievement sound

**Free Sources**:
- Freesound.org: Search "epic", "fanfare", "victory", "legendary"
- Zapsplat.com: Game victory sounds, triumph music
- YouTube Audio Library: "Victory", "Achievement", or "Triumph" category

### 3. Card Pickup Sound (`card_pickup.mp3`)
**When**: Plays when a player claims a dropped card
**Purpose**: Confirms card acquisition with satisfying feedback
**Suggested Sound**:
- Soft whoosh or pickup sound (0.5-1 second)
- Card flip sound
- Collection confirm chime
- "Pop" or "grab" sound effect

**Free Sources**:
- Freesound.org: Search "whoosh", "pickup", "card flip", "pop"
- Zapsplat.com: UI and click sounds
- YouTube Audio Library: Quick positive UI sounds

## Implementation Details

### Where Sounds Are Used

1. **Pack Opening** (`views/pack_opening.py`)
   - `pack_opening.mp3`: Attached to initial pack loading message
   - `legendary_pull.mp3`: Attached to legendary card teaser
   - Line 290-301: Pack opening starts with sound
   - Line 333-337: Legendary pull triggers sound

### How to Add Sound Files

1. Download royalty-free MP3 files (see sources above)
2. Place in `assets/sounds/` directory
3. Name them according to the constants in `views/pack_opening.py`
4. Ensure they are MP3 format and under 8MB

### File Requirements

- **Format**: MP3 (Discord bot compatible)
- **Bitrate**: 128kbps or higher
- **Sample Rate**: 44.1kHz
- **Max Size**: 8MB per file
- **Normalize**: Audio should be normalized to -3dB to avoid clipping

### Discord Bot Behavior

- **Auto-play**: NOT supported (Discord security)
- **User Action**: Users can click the attached file to play
- **Attachment**: Audio files are attached as Discord message attachments
- **Preview**: Discord shows an audio player preview in the message

## Enhancement Ideas

1. **Battle Victory Sound**: Play when a player wins a card battle
2. **Daily Reward Sound**: Coin/chime sound when claiming daily rewards
3. **Pack Purchase Sound**: Success chime when buying a pack
4. **Achievement Sound**: Special fanfare for milestones

## Technical Architecture

```
Pack Opening Flow:
1. User clicks /open_pack command
2. PackOpeningAnimator creates loading message
3. pack_opening.mp3 attached (if exists)
4. Cards are revealed sequentially
5. For each legendary card:
   - legendary_pull.mp3 attached to message
   - Visual teaser shown
   - Delay for dramatic effect
6. Summary shown with card stats
```

## Testing

To test sounds locally:
1. Ensure MP3 files are in `assets/sounds/`
2. Run bot with `/open_pack` command
3. Check that audio files appear as attachments in Discord
4. Verify they play when clicked

## Licensing & Attribution

All sound effects must be:
- Royalty-free
- Licensed for commercial use  
- Properly attributed in this file if required

### Suggested Attributions (add here when adding sounds)

```
- legendary_pull.mp3: [Source and attribution]
- pack_opening.mp3: [Source and attribution]
- card_pickup.mp3: [Source and attribution]
```

## Troubleshooting

### Sounds not playing?
- Check file exists at `assets/sounds/[filename].mp3`
- Verify MP3 format (not WAV, OGG, etc.)
- Check file size (must be under 8MB)
- Discord may need permissions to attach files

### File too large?
- Re-encode with lower bitrate (128kbps)
- Trim unnecessary silence
- Use audio compression tool

### Sound quality poor?
- Verify it's 44.1kHz sample rate
- Check normalization is -3dB
- Re-encode with better quality source
