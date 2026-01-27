# Music Legends - Implementation Checklist

## ✅ Completed

- [x] VIP Subscription system configuration (`config/vip.py`)
- [x] Battle Pass system configuration (`config/battle_pass.py`)
- [x] Persistent Menu System (`cogs/menu_system.py`)
- [x] User Hub with 8 interactive buttons
- [x] Dev Panel with 12 admin tools
- [x] Pack creation flow with YouTube integration
- [x] Last.fm API integration (`lastfm_integration.py`)
- [x] TheAudioDB API integration (`audiodb_integration.py`)
- [x] API setup guide (`docs/API_SETUP_GUIDE.md`)

---

## 🔄 In Progress

### 1. Add Spotify/Last.fm/AudioDB Fallback Integration
**Priority:** High  
**Status:** Ready to implement

**Tasks:**
- [ ] Create `music_api_manager.py` with waterfall logic:
  ```
  1. Last.fm → Get artist info + top tracks
  2. TheAudioDB → Get high-res images
  3. YouTube → Get video links
  ```
- [ ] Update `PackCreationModal` to use new API manager
- [ ] Add artist image preview in song selection
- [ ] Add popularity-based stat generation
- [ ] Test with multiple artists (Drake, Taylor Swift, etc.)

**Files to modify:**
- `cogs/menu_system.py` - Update pack creation flow
- Create `music_api_manager.py` - Unified API interface

---

### 2. Add Pack Preview Before Finalization
**Priority:** High  
**Status:** Pending

**Tasks:**
- [ ] Create `PackPreviewView` with card previews
- [ ] Show estimated stats for each card
- [ ] Add "Re-roll Stats" button (regenerate with ±10 variance)
- [ ] Add "Change Songs" button (go back to selection)
- [ ] Add "Confirm & Create" button (finalize)
- [ ] Show rarity distribution preview
- [ ] Display total pack value estimate

**Implementation:**
```python
class PackPreviewView(discord.ui.View):
    - Show all 5 cards with estimated stats
    - Button: "Re-roll Stats" (randomize again)
    - Button: "Change Songs" (back to selection)
    - Button: "Confirm & Create" (finalize)
```

**Files to modify:**
- `cogs/menu_system.py` - Add preview step after song selection
- Create `views/pack_preview.py` - Preview UI

---

### 3. Add Cost Display for Non-Dev Users
**Priority:** Medium  
**Status:** Pending

**Tasks:**
- [ ] Check if user is dev in pack creation buttons
- [ ] Show cost modal for non-devs:
  - Community Pack: 500 gold OR 5 tickets
  - Gold Pack: 1,000 gold OR 10 tickets
- [ ] Verify user has sufficient currency
- [ ] Deduct cost after pack creation
- [ ] Add "Insufficient Funds" error handling
- [ ] Show cost in pack creation modal subtitle

**Implementation:**
```python
# In DevPanelView buttons:
if not is_dev(interaction.user.id):
    # Show cost confirmation
    cost_embed = discord.Embed(
        title="💰 Pack Creation Cost",
        description=f"Community Pack: 500 gold OR 5 tickets"
    )
    # Add payment confirmation buttons
```

**Files to modify:**
- `cogs/menu_system.py` - Add cost checks
- `card_economy.py` - Add deduct_currency method

---

### 4. Add Pack Opening Animation
**Priority:** Medium  
**Status:** Pending

**Tasks:**
- [ ] Create sequential card reveal system
- [ ] Show "Opening pack..." loading message
- [ ] Reveal cards one-by-one with 2-second delay
- [ ] Add rarity-specific colors/effects:
  - Common: Gray
  - Rare: Blue
  - Epic: Purple
  - Legendary: Gold with ⭐
  - Mythic: Red with 🔥
- [ ] Play sound effect (optional, via bot status)
- [ ] Show final summary with all cards
- [ ] Add "New!" badge for first-time cards

**Implementation:**
```python
async def reveal_pack_cards(interaction, cards):
    await interaction.followup.send("🎁 Opening pack...")
    
    for i, card in enumerate(cards):
        await asyncio.sleep(2)
        embed = create_card_reveal_embed(card, i+1, len(cards))
        await interaction.edit_original_response(embed=embed)
    
    # Final summary
    await asyncio.sleep(2)
    final_embed = create_pack_summary_embed(cards)
    await interaction.edit_original_response(embed=final_embed)
```

**Files to modify:**
- `cogs/card_game.py` - Update `open_pack` command
- Create `views/pack_opening.py` - Animation logic

---

### 5. Add Duplicate Protection/Quantity Tracking
**Priority:** High  
**Status:** Pending

**Tasks:**
- [ ] Add `quantity` column to `user_cards` table
- [ ] Update `add_card_to_collection` to increment quantity
- [ ] Show duplicate count in collection view
- [ ] Add "Duplicate!" badge in pack opening
- [ ] Give bonus dust for duplicates:
  - Common: +10 dust
  - Rare: +25 dust
  - Epic: +50 dust
  - Legendary: +100 dust
  - Mythic: +250 dust
- [ ] Add `/dust_card` command to convert dupes to dust
- [ ] Show "New!" vs "Duplicate x3" in reveals

**Database Schema Update:**
```sql
ALTER TABLE user_cards ADD COLUMN quantity INTEGER DEFAULT 1;
ALTER TABLE user_cards ADD COLUMN first_acquired_at TIMESTAMP;

-- Update existing records
UPDATE user_cards SET quantity = 1 WHERE quantity IS NULL;
```

**Files to modify:**
- `card_economy.py` - Update schema and add quantity logic
- `database.py` - Update `add_card_to_collection`
- `cogs/gameplay.py` - Show quantity in `/collection`

---

## 📋 Priority Order

1. **Last.fm/AudioDB Integration** (Unblocks better pack creation)
2. **Duplicate Protection** (Critical for economy balance)
3. **Pack Preview** (Better UX for pack creation)
4. **Pack Opening Animation** (Polish, can wait)
5. **Cost Display** (Important for non-dev users)

---

## 🎯 Next Steps

### Immediate (Today):
1. Get Last.fm API key from https://www.last.fm/api/account/create
2. Add keys to `.env.txt`
3. Test `lastfm_integration.py` with real API
4. Create `music_api_manager.py` with fallback logic

### Short-term (This Week):
1. Implement duplicate protection system
2. Add pack preview with re-roll option
3. Update pack creation to use Last.fm data
4. Test full flow end-to-end

### Medium-term (Next Week):
1. Add pack opening animation
2. Add cost display for non-devs
3. Polish UI/UX
4. Add more error handling

---

## 🧪 Testing Checklist

### Pack Creation Flow:
- [ ] Dev creates Community Pack → Success
- [ ] Dev creates Gold Pack → Success
- [ ] Non-dev creates pack → Shows cost modal
- [ ] Non-dev with insufficient funds → Error message
- [ ] Artist not found → Helpful error
- [ ] No songs selected → Validation error
- [ ] Preview shows correct stats → Matches final cards
- [ ] Re-roll changes stats → Different values
- [ ] Cancel at any step → No pack created

### API Integration:
- [ ] Last.fm returns artist data → Success
- [ ] Last.fm returns top tracks → Success
- [ ] TheAudioDB returns images → Success
- [ ] YouTube fallback works → Success
- [ ] All APIs fail → Graceful error

### Duplicate System:
- [ ] First card → quantity = 1, "New!" badge
- [ ] Duplicate card → quantity += 1, "Duplicate!" badge
- [ ] Duplicate gives dust → Correct amount
- [ ] Collection shows quantity → "x3" display
- [ ] Dust card command → Reduces quantity

---

## 📝 Notes

- **Last.fm API** is free and unlimited - perfect for our use case
- **TheAudioDB** free tier (key=1) has 100 req/day limit - should be enough for testing
- **Pack preview** should show estimated stats, not final (adds excitement)
- **Duplicate protection** is critical - without it, economy breaks
- **Animation** is polish - can be added last

---

## 🚀 Ready to Start?

Once you have your Last.fm API key, we can begin implementation!

**Get your key here:** https://www.last.fm/api/account/create
