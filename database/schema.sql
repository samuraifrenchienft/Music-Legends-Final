CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    discord_tag TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_battles INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    packs_opened INTEGER DEFAULT 0,
    victory_tokens INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cards (
    card_id TEXT PRIMARY KEY,
    type TEXT NOT NULL DEFAULT 'artist',
    name TEXT NOT NULL,
    artist_name TEXT,
    title TEXT,
    image_url TEXT,
    youtube_url TEXT,
    rarity TEXT NOT NULL,
    tier TEXT,
    variant TEXT DEFAULT 'Classic',
    era TEXT,
    impact INTEGER,
    skill INTEGER,
    longevity INTEGER,
    culture INTEGER,
    hype INTEGER,
    serial_number TEXT,
    print_number INTEGER DEFAULT 1,
    quality TEXT DEFAULT 'standard',
    effect_type TEXT,
    effect_value TEXT,
    pack_id TEXT,
    created_by_user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pack_id) REFERENCES creator_packs(pack_id),
    FOREIGN KEY (created_by_user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS server_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activity_type TEXT DEFAULT 'message'
);

CREATE TABLE IF NOT EXISTS user_cosmetics (
    user_id TEXT NOT NULL,
    cosmetic_id TEXT NOT NULL,
    cosmetic_type TEXT NOT NULL,
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT,
    PRIMARY KEY (user_id, cosmetic_id)
);

CREATE TABLE IF NOT EXISTS cosmetics_catalog (
    cosmetic_id TEXT PRIMARY KEY,
    cosmetic_type TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    rarity TEXT,
    unlock_method TEXT,
    price_gold INTEGER,
    price_tickets INTEGER,
    image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS card_cosmetics (
    user_id TEXT NOT NULL,
    card_id TEXT NOT NULL,
    frame_style TEXT,
    foil_effect TEXT,
    card_back TEXT,
    PRIMARY KEY (user_id, card_id)
);

CREATE TABLE IF NOT EXISTS user_inventory (
    user_id INTEGER NOT NULL,
    card_id TEXT NOT NULL,
    quantity INTEGER DEFAULT 1,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_locked BOOLEAN DEFAULT FALSE,
    is_favorite BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (user_id, card_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (card_id) REFERENCES cards(card_id)
);

CREATE TABLE IF NOT EXISTS user_currency (
    user_id INTEGER PRIMARY KEY,
    gold INTEGER DEFAULT 0,
    tickets INTEGER DEFAULT 0,
    dust INTEGER DEFAULT 0,
    last_daily_claim TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS creator_packs (
    pack_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    creator_id INTEGER NOT NULL,
    description TEXT,
    price INTEGER NOT NULL,
    card_count INTEGER NOT NULL,
    cover_image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_public BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (creator_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS creator_pack_cards (
    pack_id TEXT NOT NULL,
    card_id TEXT NOT NULL,
    PRIMARY KEY (pack_id, card_id),
    FOREIGN KEY (pack_id) REFERENCES creator_packs(pack_id),
    FOREIGN KEY (card_id) REFERENCES cards(card_id)
);

CREATE TABLE IF NOT EXISTS transaction_audit_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    user_id INTEGER,
    transaction_id TEXT,
    details TEXT,
    success BOOLEAN,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS battles (
    battle_id TEXT PRIMARY KEY,
    player1_id INTEGER NOT NULL,
    player2_id INTEGER,
    player1_deck TEXT,
    player2_deck TEXT,
    status TEXT NOT NULL,
    winner_id INTEGER,
    wager INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS battle_decks (
    deck_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    deck_name TEXT NOT NULL,
    card_ids TEXT NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS pending_tma_battles (
    battle_id TEXT PRIMARY KEY,
    player_id INTEGER NOT NULL,
    deck_card_ids TEXT NOT NULL,
    wager INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS marketplace_listings (
    listing_id TEXT PRIMARY KEY,
    seller_id INTEGER NOT NULL,
    card_id TEXT NOT NULL,
    price INTEGER NOT NULL,
    listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (seller_id) REFERENCES users(user_id),
    FOREIGN KEY (card_id) REFERENCES cards(card_id)
);

CREATE TABLE IF NOT EXISTS trade_history (
    trade_id TEXT PRIMARY KEY,
    user_-id INTEGER NOT NULL,
    user_b_id INTEGER NOT NULL,
    user_a_cards TEXT,
    user_b_cards TEXT,
    user_a_gold INTEGER,
    user_b_gold INTEGER,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS season_progress (
    user_id INTEGER NOT NULL,
    season_id TEXT NOT NULL,
    tier INTEGER DEFAULT 0,
    is_premium BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (user_id, season_id)
);

CREATE TABLE IF NOT EXISTS vip_status (
    user_id INTEGER PRIMARY KEY,
    is_vip BOOLEAN DEFAULT FALSE,
    expiration_date TEXT,
    stripe_subscription_id TEXT
);

CREATE TABLE IF NOT EXISTS user_created_packs (
    pack_id TEXT PRIMARY KEY,
    creator_id INTEGER NOT NULL,
    pack_name TEXT NOT NULL,
    card_ids TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (creator_id) REFERENCES users(user_id)
);
