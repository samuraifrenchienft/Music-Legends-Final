# models/audit_minimal.py
# Minimal audit logging model for Music Legends

import uuid
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from config import settings


def _get_audit_connection():
    """Get database connection - PostgreSQL if DATABASE_URL set, else SQLite."""
    database_url = settings.DATABASE_URL
    if database_url and ("postgresql://" in database_url or "postgres://" in database_url):
        import psycopg2
        from database import _PgConnectionWrapper
        url = database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return _PgConnectionWrapper(psycopg2.connect(url))
    else:
        db_path = database_url or "music_legends.db"
        if db_path.startswith("sqlite:///"):
            db_path = db_path[10:]
        return sqlite3.connect(db_path)


class AuditLog:
    """Minimal audit logging system"""
    
    @staticmethod
    def record(
        event: str,
        user_id: Optional[int] = None,
        target_id: Optional[str] = None,
        **payload_data
    ) -> str:
        """
        Record an audit event
        
        Args:
            event: Event type (pack_open, legendary_created, trade_complete, burn)
            user_id: User ID who performed the action
            target_id: Target object ID
            **payload_data: Additional event data
            
        Returns:
            str: The audit log ID
        """
        # Generate UUID
        audit_id = str(uuid.uuid4())
        
        # Prepare payload
        payload = json.dumps(payload_data) if payload_data else None
        
        # Get database connection
        conn = _get_audit_connection()
        cursor = conn.cursor()

        try:
            # Insert audit log
            cursor.execute("""
                INSERT INTO audit_logs (id, event, user_id, target_id, payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                audit_id,
                event,
                user_id,
                target_id,
                payload,
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            return audit_id
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    @staticmethod
    def record_pack_open(user_id: int, pack_type: str, card_serials: list) -> str:
        """Record pack opening event"""
        return AuditLog.record(
            event="pack_open",
            user_id=user_id,
            target_id=pack_type,
            pack_type=pack_type,
            cards=card_serials,
            card_count=len(card_serials)
        )
    
    @staticmethod
    def record_legendary_created(user_id: int, artist_id: str, serial: str, card_name: str) -> str:
        """Record legendary card creation"""
        return AuditLog.record(
            event="legendary_created",
            user_id=user_id,
            target_id=artist_id,
            artist_id=artist_id,
            serial=serial,
            card_name=card_name
        )
    
    @staticmethod
    def record_trade_complete(user_id: int, trade_id: str, cards_a: list, cards_b: list) -> str:
        """Record trade completion"""
        return AuditLog.record(
            event="trade_complete",
            user_id=user_id,
            target_id=trade_id,
            trade_id=trade_id,
            cards_a=cards_a,
            cards_b=cards_b
        )
    
    @staticmethod
    def record_burn(user_id: int, card_id: str, dust_amount: int) -> str:
        """Record card burning event"""
        return AuditLog.record(
            event="burn",
            user_id=user_id,
            target_id=card_id,
            card_id=card_id,
            dust=dust_amount
        )
    
    @staticmethod
    def get_user_actions(user_id: int, limit: int = 100) -> list:
        """
        Get all actions for a user
        
        Args:
            user_id: User ID to query
            limit: Maximum number of records to return
            
        Returns:
            list: Audit log records
        """
        conn = _get_audit_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, event, user_id, target_id, payload, created_at
                FROM audit_logs
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            actions = []
            for row in rows:
                action = {
                    'id': row[0],
                    'event': row[1],
                    'user_id': row[2],
                    'target_id': row[3],
                    'payload': json.loads(row[4]) if row[4] else None,
                    'created_at': row[5]
                }
                actions.append(action)
            
            return actions
            
        finally:
            conn.close()
    
    @staticmethod
    def get_legendary_creations(limit: int = 100) -> list:
        """
        List all legendary creations
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            list: Legendary creation records
        """
        conn = _get_audit_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, event, user_id, target_id, payload, created_at
                FROM audit_logs
                WHERE event = 'legendary_created'
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            legendaries = []
            for row in rows:
                legendary = {
                    'id': row[0],
                    'event': row[1],
                    'user_id': row[2],
                    'target_id': row[3],
                    'payload': json.loads(row[4]) if row[4] else None,
                    'created_at': row[5]
                }
                legendaries.append(legendary)
            
            return legendaries
            
        finally:
            conn.close()

# Test function
def test_audit_minimal():
    """Test minimal audit logging system"""
    print("🔍 Testing Minimal Audit Logging System")
    print("=====================================")
    
    # Initialize database
    if not Path(settings.DATABASE_URL.replace("sqlite:///", "")).exists():
        # Create audit table
        conn = sqlite3.connect(settings.DATABASE_URL.replace("sqlite:///", ""))
        cursor = conn.cursor()
        
        # Read and execute schema
        with open('database/audit_schema.sql', 'r') as f:
            schema = f.read()
        cursor.executescript(schema)
        
        conn.commit()
        conn.close()
        print("✅ Database schema created")
    
    # Test 1: Record pack open
    print("\n1. Testing pack open logging:")
    pack_id = AuditLog.record_pack_open(
        user_id=12345,
        pack_type="black",
        card_serials=["CARD_001", "CARD_002", "CARD_003"]
    )
    print(f"   ✅ Pack open logged: {pack_id}")
    
    # Test 2: Record legendary creation
    print("\n2. Testing legendary creation logging:")
    legendary_id = AuditLog.record_legendary_created(
        user_id=12345,
        artist_id="artist_001",
        serial="LEG_001",
        card_name="Fire Dragon"
    )
    print(f"   ✅ Legendary creation logged: {legendary_id}")
    
    # Test 3: Record trade complete
    print("\n3. Testing trade complete logging:")
    trade_id = AuditLog.record_trade_complete(
        user_id=12345,
        trade_id="trade_001",
        cards_a=["CARD_004"],
        cards_b=["CARD_005", "CARD_006"]
    )
    print(f"   ✅ Trade complete logged: {trade_id}")
    
    # Test 4: Record burn
    print("\n4. Testing burn logging:")
    burn_id = AuditLog.record_burn(
        user_id=12345,
        card_id="CARD_007",
        dust_amount=50
    )
    print(f"   ✅ Burn logged: {burn_id}")
    
    # Test 5: Query user actions
    print("\n5. Testing user actions query:")
    user_actions = AuditLog.get_user_actions(user_id=12345)
    print(f"   📊 Found {len(user_actions)} actions for user 12345")
    for action in user_actions:
        print(f"   - {action['event']} at {action['created_at']}")
    
    # Test 6: Query legendary creations
    print("\n6. Testing legendary creations query:")
    legendaries = AuditLog.get_legendary_creations()
    print(f"   📊 Found {len(legendaries)} legendary creations")
    for legendary in legendaries:
        payload = legendary['payload']
        print(f"   - {payload['card_name']} ({payload['serial']}) by user {legendary['user_id']}")
    
    print("\n✅ All audit logging tests passed!")
    return True

if __name__ == "__main__":
    test_audit_minimal()
