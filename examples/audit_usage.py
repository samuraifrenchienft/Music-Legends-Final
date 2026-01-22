# examples/audit_usage.py
# Usage examples for minimal audit logging system

from models.audit_minimal import AuditLog

def example_pack_opening():
    """Example: Log pack opening"""
    print("📦 Example: Pack Opening")
    
    # User opens a black pack and gets 3 cards
    user_id = 12345
    pack_type = "black"
    cards_received = ["CARD_001", "CARD_002", "CARD_003"]
    
    # Log the pack opening
    audit_id = AuditLog.record_pack_open(
        user_id=user_id,
        pack_type=pack_type,
        card_serials=cards_received
    )
    
    print(f"   Pack opening logged: {audit_id}")
    print(f"   User {user_id} opened {pack_type} pack")
    print(f"   Cards received: {cards_received}")

def example_legendary_creation():
    """Example: Log legendary card creation"""
    print("\n🏆 Example: Legendary Creation")
    
    # User creates a legendary card
    user_id = 12345
    artist_id = "artist_001"
    card_serial = "LEG_001"
    card_name = "Fire Dragon"
    
    # Log the legendary creation
    audit_id = AuditLog.record_legendary_created(
        user_id=user_id,
        artist_id=artist_id,
        serial=card_serial,
        card_name=card_name
    )
    
    print(f"   Legendary creation logged: {audit_id}")
    print(f"   User {user_id} created {card_name} ({card_serial})")
    print(f"   Artist: {artist_id}")

def example_trade_completion():
    """Example: Log trade completion"""
    print("\n🤝 Example: Trade Completion")
    
    # Trade completed between users
    user_id = 12345  # User who initiated the trade
    trade_id = "trade_001"
    cards_from_user_a = ["CARD_004", "CARD_005"]
    cards_from_user_b = ["CARD_006", "CARD_007", "CARD_008"]
    
    # Log the trade completion
    audit_id = AuditLog.record_trade_complete(
        user_id=user_id,
        trade_id=trade_id,
        cards_a=cards_from_user_a,
        cards_b=cards_from_user_b
    )
    
    print(f"   Trade completion logged: {audit_id}")
    print(f"   Trade {trade_id} completed")
    print(f"   User A gave: {cards_from_user_a}")
    print(f"   User B gave: {cards_from_user_b}")

def example_card_burning():
    """Example: Log card burning"""
    print("\n🔥 Example: Card Burning")
    
    # User burns a card for dust
    user_id = 12345
    card_id = "CARD_009"
    dust_received = 50
    
    # Log the burn event
    audit_id = AuditLog.record_burn(
        user_id=user_id,
        card_id=card_id,
        dust_amount=dust_received
    )
    
    print(f"   Card burn logged: {audit_id}")
    print(f"   User {user_id} burned card {card_id}")
    print(f"   Dust received: {dust_received}")

def example_queries():
    """Example: Query audit logs"""
    print("\n📊 Example: Audit Queries")
    
    # Query 1: Show all actions for a user
    print("\n1. User Actions Query:")
    user_id = 12345
    user_actions = AuditLog.get_user_actions(user_id=user_id, limit=10)
    
    print(f"   Actions for user {user_id}:")
    for action in user_actions:
        payload = action['payload']
        if action['event'] == 'pack_open':
            print(f"   - {action['event']}: {payload['card_count']} cards from {payload['pack_type']} pack")
        elif action['event'] == 'legendary_created':
            print(f"   - {action['event']}: {payload['card_name']} ({payload['serial']})")
        elif action['event'] == 'trade_complete':
            print(f"   - {action['event']}: Trade {payload['trade_id']}")
        elif action['event'] == 'burn':
            print(f"   - {action['event']}: Card {payload['card_id']} for {payload['dust']} dust")
    
    # Query 2: List all legendary creations
    print("\n2. Legendary Creations Query:")
    legendaries = AuditLog.get_legendary_creations(limit=5)
    
    print(f"   Recent legendary creations:")
    for legendary in legendaries:
        payload = legendary['payload']
        print(f"   - {payload['card_name']} ({payload['serial']}) by user {legendary['user_id']}")
        print(f"     Artist: {payload['artist_id']}")
        print(f"     Created: {legendary['created_at']}")

def example_sql_queries():
    """Example: Raw SQL queries"""
    print("\n🗄️  Example: Raw SQL Queries")
    
    import sqlite3
    
    conn = sqlite3.connect('music_legends.db')
    cursor = conn.cursor()
    
    # Query 1: Show all actions for a user
    print("\n1. SQL: Show all actions for a user")
    user_id = 12345
    cursor.execute("""
        SELECT event, target_id, payload, created_at
        FROM audit_logs
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    
    rows = cursor.fetchall()
    print(f"   Found {len(rows)} actions for user {user_id}:")
    for row in rows:
        print(f"   - {row[0]} on {row[1]} at {row[3]}")
    
    # Query 2: List all legendary creations
    print("\n2. SQL: List all legendary creations")
    cursor.execute("""
        SELECT user_id, target_id, payload, created_at
        FROM audit_logs
        WHERE event = 'legendary_created'
        ORDER BY created_at DESC
    """)
    
    rows = cursor.fetchall()
    print(f"   Found {len(rows)} legendary creations:")
    for row in rows:
        import json
        payload = json.loads(row[2]) if row[2] else {}
        print(f"   - {payload.get('card_name', 'Unknown')} ({payload.get('serial', 'Unknown')}) by user {row[0]}")
    
    conn.close()

def run_all_examples():
    """Run all audit logging examples"""
    print("🎯 Music Legends Audit Logging Examples")
    print("=====================================")
    
    # Initialize database
    import os
    import sqlite3
    
    if not os.path.exists('music_legends.db'):
        conn = sqlite3.connect('music_legends.db')
        cursor = conn.cursor()
        
        with open('database/audit_schema.sql', 'r') as f:
            schema = f.read()
        cursor.executescript(schema)
        
        conn.commit()
        conn.close()
        print("✅ Database initialized")
    
    # Run examples
    example_pack_opening()
    example_legendary_creation()
    example_trade_completion()
    example_card_burning()
    example_queries()
    example_sql_queries()
    
    print("\n✅ All examples completed successfully!")

if __name__ == "__main__":
    run_all_examples()
