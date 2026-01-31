# Junk Files and Duplicates Identified

## Duplicate/Old Files (Confirmed for Removal)

### Battle Engine Duplicates
- `battle_engine_old.py` - OLD version, replaced by battle_engine.py
- `battle_engine_original.py` - ORIGINAL version, replaced by battle_engine.py
- **Keep**: `battle_engine.py` (current version)

### Card Economy Duplicates
- `card_economy_old.py` - OLD version
- **Keep**: `card_economy.py` (current version)

### Discord Cards Duplicates
- `discord_cards_old.py` - OLD version
- **Keep**: `discord_cards.py` (current version)

## Test Files (Should be in tests/ folder)
These are test files in root that should ideally be in the `tests/` directory:
- `test_cron_handlers.py`
- `test_cron_service.py`
- `test_dependencies.py`
- `test_full_system.py`
- `test_pack_create.py`
- `test_pack_creation_flow.py`
- `test_pack_marketplace.py`
- `test_redis_connection.py`
- `simple_bot_test.py`

## Miscellaneous Files
- `Clawd memory fix.txt` - Text file, not code
- `stripe.zip` - Archive file in repo (should be .gitignored)
- `index.html` - Appears to be standalone, not part of Discord bot

## Commands Duplicates
Multiple similar files in `commands/` directory - need to check:
- `admin_preview.py`
- `admin_review.py`
- `admin_review_final.py`
- `enhanced_admin_review.py`
- `collection_ui.py`
- `enhanced_collection_ui.py`
- `creator_dashboard.py`
- `enhanced_creator_dashboard.py`
- `persistent_dashboard.py`

## Services That May Be Duplicates
Need to verify if these are actually used or duplicates:
- `services/creator_service.py`
- `services/creator_service_new.py`

## Summary

### High Priority Removals (Safe to Delete)
1. battle_engine_old.py
2. battle_engine_original.py
3. card_economy_old.py
4. discord_cards_old.py
5. Clawd memory fix.txt
6. stripe.zip

### Medium Priority (Review Before Deletion)
1. Test files in root (move to tests/ or delete if obsolete)
2. Enhanced vs non-enhanced command files
3. creator_service.py vs creator_service_new.py

### Low Priority
1. Extra documentation files (keep but could consolidate)
