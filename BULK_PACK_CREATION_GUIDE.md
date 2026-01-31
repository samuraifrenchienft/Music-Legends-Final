# Bulk Pack Creation Guide

## Overview

This guide covers multiple methods for creating packs in bulk for the Music Legends bot. Choose the method that best fits your needs.

---

## Method 1: JSON Import (Recommended for Testing)

### What It's For
- Quick testing of marketplace functionality
- Creating curated packs with specific stats
- Reproducible pack creation
- Full control over card data

### Commands Available

1. **`/import_packs`** - Import packs from a JSON file
2. **`/import_packs_help`** - Show detailed help and examples
3. **`/create_pack_template`** - Generate a template JSON file

### Usage

#### Step 1: Generate a Template
Run this command in Discord (admin only):
```
/create_pack_template num_packs:5
```
This will create a `pack_template.json` file with 5 example packs.

#### Step 2: Edit the Template
Open the downloaded file and edit it to your liking:

```json
{
  "packs": [
    {
      "name": "Your Pack Name",
      "description": "Pack description here",
      "creator_id": 123456789,
      "price_cents": 699,
      "cards": [
        {
          "name": "Artist Name",
          "title": "Song Title",
          "rarity": "legendary",
          "youtube_url": "https://youtube.com/watch?v=...",
          "image_url": "https://...",
          "impact": 90,
          "skill": 88,
          "longevity": 85,
          "culture": 92,
          "hype": 87
        }
        // ... 4 more cards (must have exactly 5)
      ]
    }
  ]
}
```

#### Step 3: Import
Run this command and attach your JSON file:
```
/import_packs file:[your_edited_file.json]
```

### Requirements

- **5 cards per pack** (exactly)
- **Valid rarities**: `common`, `rare`, `epic`, `legendary`
- **Stats**: 0-92 (creator pack limit)
- **Required fields**: `name`, `rarity`

### Optional Fields

- `creator_id` - Defaults to your Discord ID
- `description` - Pack description text
- `price_cents` - Price in cents (default: 699 = $6.99)
- `title` - Song title for card
- `youtube_url` - YouTube video URL
- `image_url` - Card image URL

---

## Method 2: Seed Script (Recommended for Content Generation)

### What It's For
- Automatically generating packs from artist names
- Uses real YouTube data
- Generates stats based on view counts
- Good for seeding initial marketplace content

### Prerequisites

1. **YouTube API Key** must be configured in `.env.txt`
2. **Python environment** with all dependencies installed

### Usage

#### Option A: Command Line Artists
```bash
python scripts/seed_marketplace_packs.py --artists "Drake,The Weeknd,Beyonce" --count 1
```

#### Option B: From File
Create a text file with one artist per line:
```text
Drake
The Weeknd
Beyonce
Taylor Swift
Ed Sheeran
```

Then run:
```bash
python scripts/seed_marketplace_packs.py --artists-file scripts/artists_example.txt --count 1
```

### Parameters

- `--artists` - Comma-separated list of artist names
- `--artists-file` - Path to file with one artist per line
- `--count` - Number of packs to create per artist (default: 1)

### How It Works

1. Searches YouTube for artist's music videos
2. Selects top 5 videos
3. Generates battle stats based on view counts
4. Creates pack with rarity distribution:
   - 1 Legendary
   - 2 Epic
   - 1 Rare
   - 1 Common
5. Inserts directly into database as LIVE pack

### Example Output
```
🔍 Searching for Drake...
✅ Created pack: Drake Collection (ID: a1b2c3d4...)
🔍 Searching for The Weeknd...
✅ Created pack: The Weeknd Collection (ID: e5f6g7h8...)

✅ Seeding complete!
📊 Successfully created: 2 packs
❌ Failed: 0 packs
```

---

## Method 3: Example JSON File

We've included `bulk_packs_example.json` with 5 ready-to-use packs:

1. **Hip Hop Legends Vol. 1** - Kendrick, Drake, J. Cole, Travis Scott, Lil Baby
2. **Pop Hits 2024** - The Weeknd, Dua Lipa, Bruno Mars, Olivia Rodrigo, Ed Sheeran
3. **Rock Classics** - Queen, Led Zeppelin, Pink Floyd, AC/DC, The Beatles
4. **R&B Soul Pack** - Beyoncé, Frank Ocean, SZA, H.E.R., Daniel Caesar
5. **EDM Bangers** - Calvin Harris, Marshmello, The Chainsmokers, Kygo, Alan Walker

### Quick Import
Simply upload `bulk_packs_example.json` to Discord and run:
```
/import_packs file:bulk_packs_example.json
```

This will instantly populate your marketplace with 5 diverse packs!

---

## Comparison Table

| Method | Speed | Control | Real Data | Best For |
|--------|-------|---------|-----------|----------|
| **JSON Import** | ⚡ Instant | ✅ Full | ❌ No | Testing, custom packs |
| **Seed Script** | 🐌 Slow | ⚠️ Partial | ✅ Yes | Realistic content |
| **Example File** | ⚡ Instant | ❌ None | ⚠️ Mixed | Quick start |

---

## Troubleshooting

### "JSON Parse Error"
- Make sure your JSON is valid (use a JSON validator)
- Check for trailing commas
- Ensure all quotes are double quotes (`"`)

### "Pack must have exactly 5 cards"
- Each pack requires exactly 5 cards
- Count your cards in the `cards` array

### "Invalid rarity"
- Use lowercase: `common`, `rare`, `epic`, `legendary`
- No other rarities allowed for creator packs

### "Stats must be 0-92"
- Creator packs have a 92 stat ceiling
- Adjust any stats over 92

### "YOUTUBE_API_KEY not found"
- For seed script only
- Check your `.env.txt` file
- Make sure the key is valid

### "Not enough videos found"
- For seed script only
- Artist may not have enough YouTube content
- Try a different artist name

---

## Tips & Best Practices

### For JSON Import
1. **Start with the template** - Use `/create_pack_template` to get the structure right
2. **Validate before import** - Use a JSON validator online
3. **Keep it organized** - Group similar packs together
4. **Backup your JSON** - Save copies before making changes

### For Seed Script
1. **Test with 1-2 artists first** - Make sure it's working
2. **Watch YouTube API quota** - You have limited daily requests
3. **Use popular artists** - They have more videos and better data
4. **Check the results** - Use `/packs` to verify created packs

### General
1. **Use admin commands carefully** - Packs go LIVE immediately
2. **Check marketplace after import** - Run `/packs` to see your creations
3. **Delete test packs** - Clean up any unwanted test data
4. **Document your imports** - Keep notes on what you created

---

## Advanced Usage

### Combining Methods

You can use both methods together:

1. **Generate base content** with seed script
2. **Create special packs** with JSON import
3. **Mix and match** for variety

### Custom Stat Distribution

For JSON import, you can create themed packs with custom stat emphasis:

- **Skill-focused**: High skill, moderate other stats (technical artists)
- **Culture-focused**: High culture, lower other stats (influential artists)
- **Balanced**: All stats similar (well-rounded artists)
- **Hype-heavy**: High hype, varied other stats (trending artists)

### Batch Processing

For large imports:

```bash
# Create multiple artist packs at once
python scripts/seed_marketplace_packs.py --artists-file my_100_artists.txt --count 1
```

---

## Files Reference

### Created Files
- `cogs/admin_bulk_import.py` - Admin commands for JSON import
- `scripts/seed_marketplace_packs.py` - Seed script for YouTube-based generation
- `bulk_packs_example.json` - Example pack data (5 packs)
- `scripts/artists_example.txt` - Example artist list

### Modified Files
- `database.py` - Added `bulk_create_packs()` method
- `main.py` - Added `admin_bulk_import` cog to load list

---

## Support

If you encounter issues:

1. Check this guide for troubleshooting
2. Use `/import_packs_help` for quick reference
3. Verify your JSON with an online validator
4. Check bot logs for detailed error messages

---

## Quick Start (TL;DR)

### Fastest Way to Get Packs
```
1. Run: /import_packs file:bulk_packs_example.json
2. Done! You now have 5 packs live
```

### Generate Real Data
```bash
python scripts/seed_marketplace_packs.py --artists "Drake,Beyonce,Taylor Swift" --count 1
```

---

**Happy pack creating! 🎵🃏**
