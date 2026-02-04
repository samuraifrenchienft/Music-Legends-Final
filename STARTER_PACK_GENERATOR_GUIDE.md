# Starter Pack Generator - Comprehensive Pack Creation

## Overview

The Starter Pack Generator creates pre-built, curated packs across multiple music genres. Perfect for:

- **Seeding the marketplace** with quality initial content
- **Testing pack creation** without manual setup
- **Providing starter packs** for new players
- **Bulk pack generation** across categories

## Features

### Categories Included

1. **EDM Bangers** (5 packs)
   - Calvin Harris, David Guetta, The Chainsmokers, etc.
   
2. **Rock Classics** (5 packs)
   - The Beatles, Led Zeppelin, Pink Floyd, etc.

3. **R&B Soul Pack** (5 packs)
   - Marvin Gaye, Stevie Wonder, Alicia Keys, etc.

4. **Pop Hits** (5 packs)
   - Taylor Swift, The Weeknd, Billie Eilish, etc.

5. **Hip Hop Legends** (5 packs)
   - Tupac, Eminem, Kanye West, Drake, etc.

**Total: 25 curated packs across genres**

## Usage

### Run the Generator

```bash
python scripts/generate_starter_packs.py
```

### Output

```
🎵 Music Legends Starter Pack Generator
Starting pack generation...

🎵 Starting Starter Pack Generation...
📊 Categories: 5
📦 Total Packs: 25

🎸 Generating EDM Bangers packs...
  ✅ EDM Bangers - Vol. 1: Calvin Harris
  ✅ EDM Bangers - Vol. 2: Marshmello
  ... more packs ...

📊 STARTER PACK GENERATION REPORT
============================================================
✅ Packs Created: 25
❌ Packs Failed: 0
📈 Success Rate: 100.0%
🎴 Total Cards Created: 125
============================================================
```

### Report Output

Generated `starter_packs_report.json`:

```json
{
  "timestamp": "2026-02-03T...",
  "total_packs_attempted": 25,
  "packs_created": 25,
  "packs_failed": 0,
  "success_rate": "100.0%",
  "total_cards_created": 125,
  "created_packs": [
    {
      "pack_id": "starter_edm_bangers_1_a1b2c3d4",
      "pack_name": "EDM Bangers - Vol. 1",
      "genre": "EDM Bangers",
      "primary_artist": "Calvin Harris"
    },
    ...
  ]
}
```

## Programmatic Usage

### Generate All Packs

```python
from scripts.generate_starter_packs import generate_starter_packs
import asyncio

# Generate and save report
report = asyncio.run(generate_starter_packs(save_report=True))

print(f"Created {report['packs_created']} packs")
```

### Custom Generator Instance

```python
from scripts.generate_starter_packs import StarterPackGenerator
from database import DatabaseManager
import asyncio

async def custom_generation():
    db = DatabaseManager()
    generator = StarterPackGenerator(db=db)
    
    report = await generator.generate_all_packs()
    generator.print_report(report)
    generator.save_report(report, 'custom_report.json')

asyncio.run(custom_generation())
```

## Pack Structure

Each generated pack includes:

### Pack Metadata
- **Pack ID**: Unique identifier (`starter_genre_number_hash`)
- **Pack Name**: Category and volume number
- **Genre**: Genre classification
- **Description**: Curator description
- **Pack Size**: 5 cards per pack

### Cards per Pack
- **Card 1**: Legendary rarity (primary artist)
- **Card 2**: Epic rarity (featured artist)
- **Card 3**: Rare rarity (featured artist)
- **Card 4-5**: Common rarity (featured artists)

### Card Data
- Artist name and image
- Rarity level
- Base stats (all 50):
  - Impact: 50
  - Skill: 50
  - Longevity: 50
  - Culture: 50
  - Hype: 50

## Artist Categories

### EDM Bangers
Modern electronic dance music producers and DJs

### Rock Classics
Legendary rock bands spanning decades

### R&B Soul Pack
Soulful R&B artists from classic to modern

### Pop Hits
Contemporary pop stars and hits

### Hip Hop Legends
Iconic rappers and hip hop artists

## Statistics

- **Total Categories**: 5
- **Packs Per Category**: 5
- **Total Packs**: 25
- **Cards Per Pack**: 5
- **Total Cards**: 125
- **Unique Artists**: 125+

## Integration Points

### Database Integration
- Creates packs in database
- Stores card data
- Associates with creator (user ID 0 for system)

### Logging Integration
- Logs each pack creation
- Logs overall generation event
- Sends Discord alert on completion

### Report Generation
- JSON format report
- Success rate tracking
- Failed pack tracking
- Detailed pack listings

## Customization

### Add New Genre

```python
PACK_CATEGORIES = {
    'My Genre': [
        ['Artist 1', 'Artist 2', 'Artist 3', 'Artist 4', 'Artist 5'],
        # More artist groups...
    ]
}
```

### Change Rarity Distribution

Modify `_assign_rarity()` method:

```python
def _assign_rarity(self, card_index: int) -> str:
    if card_index == 0:
        return 'epic'  # Change legendary to epic
    elif card_index == 1:
        return 'rare'
    # ... etc
```

### Custom Pack Names

Modify pack naming in `_create_starter_pack()`:

```python
pack_name = f"[STARTER] {genre} - Collection Vol. {pack_number}"
```

## Performance

- **Pack Creation Time**: ~5-10 seconds per pack
- **Total Generation Time**: ~2-3 minutes for all 25 packs
- **Database Operations**: ~750 inserts (25 packs × 30 records)
- **API Calls**: ~125 artist lookups

## Error Handling

- **Graceful Failures**: Individual pack failures don't stop generation
- **Partial Success**: Creates as many packs as possible
- **Error Logging**: All failures logged with context
- **Report Tracking**: Failed packs listed in report

## Troubleshooting

### No Packs Created?
- Check database connection
- Verify API keys configured
- Check log files for errors

### Low Success Rate?
- Check music API limits
- Verify artist names are correct
- Check database permissions

### Slow Generation?
- API rate limiting (add delays)
- Database performance (create indexes)
- Network latency (check connection)

## Future Enhancements

- [ ] Genre-specific stats distribution
- [ ] Random rarity distribution
- [ ] Image URL caching
- [ ] Batch API calls
- [ ] Progress tracking/resume
- [ ] Interactive genre selection
- [ ] Custom artist lists

## Files Generated

- `starter_packs_report.json` - Generation report

## Example Commands

### Generate with Logging

```bash
python scripts/generate_starter_packs.py 2>&1 | tee pack_generation.log
```

### Check Report

```bash
cat starter_packs_report.json | jq '.packs_created'
```

### Run from Python

```python
from scripts.generate_starter_packs import generate_starter_packs
import asyncio

asyncio.run(generate_starter_packs())
```
