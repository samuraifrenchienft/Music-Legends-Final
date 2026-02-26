# Pack Opening Canonical Guide

## 🎯 FINAL-FORM GAME UX

This is not implementation detail — this is **game design + UX law**. Code must obey this flow exactly.

## 🔄 Finite State Machine

**INIT → SEALED → REVEAL_QUEUE → CARD_REVEAL[n] → LEGENDARY_PAUSE? → SUMMARY → COMPLETE**

**No skipping. No shortcuts.**

---

## 📦 State Breakdown

### 🟦 STATE 1 — INIT (Command Acknowledgement)

**Trigger**: `/open pack:black`

**Bot Response** (Ephemeral):
```
🎁 Pack Opening Initiated
Opening Black Pack…

🔒 Queue Status
Your position in queue: 1
Estimated wait: 0 seconds

Pack owned by @username
```

**Purpose**:
- Prevent spam
- Lock queue  
- Confirm ownership

**Timing**: 1.5s delay to SEALED

---

### ⬛ STATE 2 — SEALED PACK (HYPE MOMENT)

**Embed**:
- Large pack image
- Black + gold accents
- No card info yet

**Text**:
```
🎴 Black Pack
You open a Black Pack…

📦 Pack Details
Type: Black Pack
Cards: 5
Hero Slot: ✅

🎯 Drop Rates
🟡 Gold: 30.0%
💎 Platinum: 12.0%
👑 Legendary: 3.0%
```

**Buttons**: `▶ Open Pack`

**Purpose**: Creates anticipation

---

### 🟨 STATE 3 — REVEAL QUEUE (SERVER DRAMA)

When button pressed:

**Embed Update**:
```
🔀 Shuffling Cards…
The universe is deciding your fate…

⏳ Processing
Locking in your results…
This cannot be changed.
```

**Internally**:
- Cards already minted ✅
- Results locked ✅
- Nothing can change ✅

**Timing**: 0.8s delay to first reveal

---

### 🎴 STATE 4 — CARD REVEAL (ONE AT A TIME)

Cards revealed sequentially with user control.

**Each card reveal**:
```
🎴 Card 2 of 5
Luna Echo - Legendary

🎨 Artist
Name: Luna Echo
Genre: Electronic
Source: Spotify

⭐ Rarity
Tier: Legendary
Serial: ML-S1-L-0001
Print: 1/250

🏆 Badges
👑 legendary 🆕 first_print

⭐ HERO CARD
Selected for premium hero slot with boosted artist selection!

✨ Foil Card
This card has a special foil finish!

Card 2 of 5 • Serial: ML-S1-L-0001
```

**Buttons**: `▶ Next Card`

**Features**:
- Card image (hero crop)
- Tier badge
- Artist name
- Serial
- Foil/glow effects
- Footer: "Card X of Y"

---

### 🟥 LEGENDARY INTERRUPTION (MANDATORY)

If any card is Legendary:

**Reveal STOPS** - Special embed replaces normal flow

```
⚠️ LEGENDARY PULLED ⚠️
Luna Echo has been chosen by the universe!

👑 LEGENDARY CARD
Artist: Luna Echo
Genre: Electronic
Source: Spotify

🔢 SERIAL INFORMATION
Serial: ML-S1-L-0001
Print: 1/250
Scarcity: One of only 250 ever!

Legendary cards are extremely rare! • Card 2 of 5
```

**Rules**:
- Gold/red glow
- Larger image
- Serial emphasized
- Print cap shown
- **Minimum 3 seconds**
- **No skip**

**Purpose**: Creates server attention

---

### 🟩 STATE 5 — SUMMARY SCREEN

After final card:

**Embed**:
```
🎉 Black Pack Summary
Your pack revealed 5 amazing cards!

📋 Cards Received
1. 👑 Luna Echo (ML-S1-L-0001)⭐
2. 💎 Neon Dreams (ML-S1-P-0042)
3. 🟡 Crystal Waves (ML-S1-G-0156)
4. 🟡 Urban Pulse (ML-S1-G-0178)
5. ⚪ Folk Revival (ML-S1-C-0234)

📊 Tier Breakdown
👑 Legendary: 1
💎 Platinum: 1
🟡 Gold: 2
⚪ Community: 1

👑 Legendary Cards
👑 Luna Echo (ML-S1-L-0001) - 1/250

💎 Pack Value
Hero Slot: ✅
Legendary Pulls: 1
Total Value: 1,650 points

Pack opened by @username • Choose your next action
```

**Buttons**:
- `📦 View Collection`
- `🔁 Open Another` 
- `🔒 Close`

**Purpose**: Reinforces value

**Timing**: 10s auto-timeout

---

### ⚪ STATE 6 — COMPLETE

**View expires after timeout**
- State removed from Redis
- Audit already written
- Cards in collection

**Embed**:
```
✅ Pack Opening Complete
Your Black Pack cards have been added to your collection!

🎯 Collection Updated
Cards Added: 5
Legendary Cards: 1
Total Opening Time: 45 seconds

Thank you for opening a pack! • View your collection anytime
```

---

## ⏱️ Animation & Timing Rules

| Event | Minimum Time | Purpose |
|-------|-------------|---------|
| Pack open delay | 1.5s | Build anticipation |
| Card reveal | 0.8s | Processing drama |
| Legendary pause | 3.0s | Server attention |
| Summary display | 10s | Value reinforcement |

**These are intentional friction points.**

---

## 🎮 Discord UI Component Rules

### ✅ Requirements:
- **Buttons only**, no reactions
- **Views must be state-locked per user**
- **No multi-user interaction**
- **Resume safe after bot restart** (Redis state)

### ❌ Prohibited:
- Reaction-based interactions
- Shared pack openings
- State skipping
- Multiple simultaneous openings per user

---

## 🛡️ Abuse-Safe Guarantees

### ✅ Safety Features:
- **Cards minted before UI** - No loss on failure
- **UI failure ≠ loss** - Results already locked
- **Replays always show same results** - Deterministic
- **Duplicate presses ignored** - State protection

### 🔒 Protection:
- Payment processing completes before UI starts
- Pack results stored in database immediately
- UI only displays already-minted cards
- State machine prevents duplicate actions

---

## 🎯 Why This Is Top-Tier

This does what **Karuta & gacha games** understand:

```
anticipation > randomness
pacing > speed  
ceremony > efficiency
```

### 🎬 Psychological Effects:
- **Anticipation builds** through timed delays
- **Pacing creates drama** with sequential reveals
- **Ceremony adds value** with legendary interruptions
- **Friction points** make pulls feel meaningful

### 📱 User Behavior:
This makes people:
- Screen record pulls
- Post pulls on social media
- Chase legendaries
- Feel investment in results
- Remember the experience

---

## 🔒 What Is Now Locked

From this point forward:

### ✅ **Mandatory**:
- **Packs must open this way** - No exceptions
- **UI must respect these states** - No shortcuts
- **Future platforms must emulate this experience** - Consistency

### 🚫 **Forbidden**:
- Skipping states
- Instant reveals
- Multi-user packs
- Alternative opening methods

---

## 🎉 This Is Final-Form Game UX

This pack opening experience is designed to:

✅ **Create memorable moments** - Legendary interruptions  
✅ **Build anticipation** - Timed delays and pacing  
✅ **Reinforce value** - Summary screens and value display  
✅ **Prevent abuse** - Cards minted before UI  
✅ **Ensure consistency** - Same experience everywhere  

---

## 🔧 Implementation Notes

### State Persistence:
- Use Redis for cross-restart safety
- Store FSM state with TTL
- Auto-cleanup on completion

### Performance:
- Cards minted synchronously
- UI updates are asynchronous
- State transitions are atomic

### Error Handling:
- UI failures don't affect cards
- State recovery on restart
- Graceful timeout handling

---

## 🎯 Success Metrics

Track these to validate the design:

✅ **Screen recording rate** - Users recording pulls  
✅ **Social sharing** - Users posting results  
✅ **Session length** - Time spent in opening flow  
✅ **Repeat opens** - Users opening multiple packs  
✅ **Legendary chase** - Users continuing after legendaries  

---

## 🚀 Future Platforms

When expanding beyond Discord:

✅ **Must emulate this exact flow**
✅ **Same timing and pacing**
✅ **Legendary interruption behavior**
✅ **Value reinforcement moments**
✅ **Abuse-safe guarantees**

---

**This is final-form game UX.** 🎯

The experience is now **locked in** as the canonical way packs open across all platforms and all time. 🎉
