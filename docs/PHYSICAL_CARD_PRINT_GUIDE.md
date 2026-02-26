# Physical Card Print Specifications (Canonical)

## 🎯 Core Principle (LOCKED)

**Every physical card must correspond 1:1 with a digital card.**
- ✅ No exceptions
- ✅ No "promo-only" shortcuts that undermine scarcity
- ✅ Physical cards are redeemed representations, not separate mints

---

## 📏 Card Size & Format (Standardized)

### Final Size (Tarot Format – Locked)
```
Card size: 70 × 120 mm (2.75 × 4.75 in)
Aspect ratio: ~1:1.71
Corners: 3 mm rounded
```

### Why Tarot:
- ✅ **Premium feel** - Larger than standard trading cards
- ✅ **More space for art + serials** - Better visual impact
- ✅ **Differentiates from Pokémon/Magic clones** - Unique positioning

---

## 🖨️ Print File Specifications

### Full Bleed Size
```
76 × 126 mm (3 mm bleed on all sides)
Resolution: 300 DPI minimum
Final canvas: ~900 × 1500 px
Color: CMYK
```

### Rich Black for Luxury Packs
```
C: 60 / M: 40 / Y: 40 / K: 100
```

---

## 🎨 Front Layout – Print Safe Zones

```
┌──────────────────────────┐
│  SAFE HEADER (8mm)       │
│  Artist Name | Tier     │
├──────────────────────────┤
│                          │
│  ART SAFE ZONE           │
│  (no text overlays)      │
│                          │
├──────────────────────────┤
│  META BAND (6mm)         │
│  Genre • Season          │
├──────────────────────────┤
│  SERIAL ZONE (6mm)       │
│  ML-S1-L-0001 / 100      │
└──────────────────────────┘
```

### Rules:
- ✅ **No critical text inside bleed**
- ✅ **Serial must be print-safe, not foil-only**
- ✅ **Tier badge cannot overlap artist name**

---

## 🔄 Card Back – Physical Rules

### Back Design Constraints:
- ✅ **No artist data**
- ✅ **No serial**
- ✅ **No QR code on back** (security)

### Allowed:
- ✅ **Game logo**
- ✅ **Season mark**
- ✅ **Pattern / emblem**

### Purpose:
Prevents back-facing identification during play.

---

## 🏆 Material & Finish Tiers (Top-Tier Only)

### Community / Gold
```
350 GSM black-core cardstock
Matte finish
```

### Platinum
```
350–400 GSM
Soft-touch laminate
Spot UV on tier badge
```

### Legendary
```
400 GSM
Soft-touch laminate
Gold foil stamp (tier only)
Optional holographic foil layer
```

**Legendary must be felt, not just seen.**

---

## 🔢 Serial & Authenticity (Critical)

### Front Serial (Mandatory)
```
ML-S1-L-0001 / 100
```

### Microprint (Optional, Premium Runs)
```
Tiny repeating serial text
Only visible under magnification
```

### Purpose:
- ✅ **Physical authentication**
- ✅ **Anti-counterfeiting**
- ✅ **Collector verification**

---

## 🔄 Digital → Physical Redemption Flow

### Redemption Rules:
1. ✅ **User owns digital card**
2. ✅ **Card must be unburned**
3. ✅ **Redemption burns the digital card**
4. ✅ **Physical card is printed and shipped**

### Why Burn?
- ✅ **Prevents duplicate existence**
- ✅ **Protects scarcity**
- ✅ **Keeps trust**

### Process Flow:
```
Digital Card → Check Eligibility → Burn Digital → Queue Print → Ship Physical
```

---

## 📱 QR Code Policy (Security)

### QR codes are optional and front-only, micro-sized.

### QR links to:
- ✅ **Public card verification page**
- ✅ **Serial + season only**
- ✅ **No wallet info**

### QR must never:
- ❌ **Allow minting**
- ❌ **Reveal owner**
- ❌ **Allow duplication**

### Specifications:
```
Position: Front bottom right
Size: 8mm (micro-sized)
Content: Verification URL only
```

---

## 📦 Packaging (Founders / Premium)

### Premium Pack Box
```
Rigid tuck box
Matte black
Gold foil logo
Serial range printed on box (optional)
```

### Purpose:
- ✅ **Perceived value**
- ✅ **Collector experience**
- ✅ **Brand premium positioning**

---

## 🔒 What Is Now Locked

From this point forward:

### ✅ **Fixed Specifications:**
- **Card dimensions do not change**
- **Serial placement does not move**
- **Physical cards are burn-backed**
- **Legendary finishes are consistent**

### ✅ **Manufacturing Standards:**
- **Print-safe zones are permanent**
- **Material tiers are locked**
- **Color specifications are final**
- **Redemption flow is canonical**

---

## 🎯 Manufacturing Guidelines

### Print Requirements:
- ✅ **300 DPI minimum**
- ✅ **CMYK color mode**
- ✅ **3mm bleed on all sides**
- ✅ **Print-safe text placement**

### Quality Control:
- ✅ **Serial verification**
- ✅ **Material consistency**
- ✅ **Finish inspection**
- ✅ **Packaging integrity**

### Anti-Counterfeiting:
- ✅ **Microprint verification**
- ✅ **QR code authentication**
- ✅ **Material specification checks**
- ✅ **Serial database verification**

---

## 📊 Print File Data Structure

### Front Layout:
```json
{
  "size_mm": [70, 120],
  "bleed_mm": [76, 126],
  "safe_zones": {
    "header": {"y_mm": 3, "height_mm": 8},
    "art_zone": {"y_mm": 16, "height_mm": 88},
    "meta_band": {"y_mm": 104, "height_mm": 6},
    "serial_zone": {"y_mm": 110, "height_mm": 6}
  },
  "material_spec": {
    "gsm": 400,
    "finish": "soft_touch_laminate",
    "special_features": ["gold_foil_tier"],
    "foil": true
  }
}
```

### Back Layout:
```json
{
  "content": {
    "game_logo": true,
    "season_mark": "S1",
    "pattern": true,
    "no_artist_data": true,
    "no_serial": true,
    "no_qr_code": true
  }
}
```

---

## 🔄 Integration with Digital System

### 1:1 Parity Rules:
- ✅ **Every physical card has digital counterpart**
- ✅ **Digital card burned when physical redeemed**
- ✅ **Serial numbers match exactly**
- ✅ **Tier specifications consistent**

### Data Flow:
```
Digital Card → Redemption Check → Burn Digital → Print Queue → Ship Physical → Update Status
```

### Verification:
- ✅ **QR code verification**
- ✅ **Serial database lookup**
- ✅ **Physical-digital parity check**
- ✅ **Redemption status verification**

---

## 🎯 Quality Standards

### Visual Standards:
- ✅ **Consistent color reproduction**
- ✅ **Accurate serial placement**
- ✅ **Proper tier badge positioning**
- ✅ **Clean art reproduction**

### Tactile Standards:
- ✅ **Material consistency by tier**
- ✅ **Finish quality verification**
- ✅ **Foil application accuracy**
- ✅ **Corner rounding precision**

### Packaging Standards:
- ✅ **Protective packaging**
- ✅ **Brand consistency**
- ✅ **Collector experience**
- ✅ **Shipping safety**

---

## 🚀 Future Considerations

### Season 2 Planning:
- ✅ **Same card dimensions**
- ✅ **Updated serial namespace**
- ✅ **New season marks**
- ✅ **Consistent material tiers**

### Expansion Possibilities:
- ✅ **Special edition finishes**
- ✅ **Collaborative packaging**
- ✅ **Limited run materials**
- ✅ **Enhanced security features**

### Manufacturing Evolution:
- ✅ **Improved print technology**
- ✅ **Enhanced materials**
- ✅ **Better security features**
- ✅ **Sustainable options**

---

## 🎉 Summary

**Physical card specifications are now locked as manufacturing law:**

✅ **Tarot format (70×120mm)** - Premium positioning  
✅ **Print-safe zones** - Consistent quality  
✅ **Material tiers** - Tactile differentiation  
✅ **1:1 digital parity** - Scarcity protection  
✅ **Burn redemption** - Trust preservation  
✅ **Security features** - Anti-counterfeiting  

This ensures:
- 🎯 **Manufacturing consistency** across all time
- 🎯 **Collector confidence** in physical cards
- 🎯 **Digital-physical trust** through parity
- 🎯 **Premium positioning** in the market
- 🎯 **Long-term value preservation** for collectors

---

## 🔒 LOCKED STATUS

From this point forward:

- ✅ **Card dimensions are final**
- ✅ **Print specifications cannot change**
- ✅ **Material tiers are permanent**
- ✅ **Redemption flow is canonical**
- ✅ **1:1 parity is mandatory**

**This is the manufacturing foundation that ensures physical cards maintain trust and value for years to come.** 🎯

---

## 📞 Implementation Notes

### For Print Partners:
- Use provided print file data structure
- Follow material specifications exactly
- Maintain quality control standards
- Implement security verification

### For Development:
- Integrate redemption flow with digital system
- Implement QR code verification
- Maintain serial database accuracy
- Ensure 1:1 parity enforcement

### For Quality Assurance:
- Verify print specifications
- Check material consistency
- Test security features
- Validate packaging standards

**This specification ensures every physical card is a premium, trustworthy representation of its digital counterpart.** 🚀
