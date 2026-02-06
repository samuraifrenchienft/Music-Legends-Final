#!/usr/bin/env python3
"""
Quick script to delete a specific pack from the database
"""

import sqlite3
import sys

def delete_pack(pack_id: str, owner_id: int = None):
    """Delete a pack and all associated data"""

    db_path = "music_legends.db"

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Check if pack exists
            cursor.execute("SELECT name, creator_id FROM creator_packs WHERE pack_id = ?", (pack_id,))
            pack = cursor.fetchone()

            if not pack:
                print(f"❌ Pack {pack_id} not found")
                return False

            pack_name, creator_id = pack
            print(f"Found pack: {pack_name} (Creator ID: {creator_id})")

            # Verify ownership if owner_id is provided
            if owner_id is not None and creator_id != owner_id:
                print(f"❌ Permission denied: You are not the owner of this pack")
                return False

            # Delete pack
            cursor.execute("DELETE FROM creator_packs WHERE pack_id = ?", (pack_id,))
            deleted = cursor.rowcount

            # Cascading delete - remove marketplace listings that reference cards from this pack
            # This is a basic cascade since the schema doesn't have foreign keys
            # Also delete cards that belong to this pack
            cursor.execute("""
                DELETE FROM market_listings
                WHERE card_id IN (
                    SELECT card_id FROM cards WHERE pack_id = ?
                )
            """, (pack_id,))
            cascade_deleted = cursor.rowcount

            # Delete cards associated with this pack
            cursor.execute("DELETE FROM cards WHERE pack_id = ?", (pack_id,))
            cards_deleted = cursor.rowcount
            if cards_deleted > 0:
                print(f"   Deleted {cards_deleted} cards from pack")

            conn.commit()

            if deleted > 0:
                print(f"✅ Deleted pack: {pack_id}")
                print(f"   Name: {pack_name}")
                if cascade_deleted > 0:
                    print(f"   Removed {cascade_deleted} marketplace listings (cascade)")
                return True
            else:
                print(f"❌ Failed to delete pack")
                return False

    except Exception as e:
        print(f"❌ Error deleting pack: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python delete_pack.py <pack_id>")
        print("\nExample:")
        print("  python delete_pack.py 5b706b21-559c-4ecc-a521-63f530b24c54")
        sys.exit(1)

    pack_id = sys.argv[1]

    # Show pack details and ask for confirmation
    db_path = "music_legends.db"
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, creator_id, created_at FROM creator_packs WHERE pack_id = ?", (pack_id,))
            pack = cursor.fetchone()

            if pack:
                pack_name, creator_id, created_at = pack
                print(f"\nPack Details:")
                print(f"  ID: {pack_id}")
                print(f"  Name: {pack_name}")
                print(f"  Creator ID: {creator_id}")
                print(f"  Created: {created_at}")
                print()

                confirmation = input("Confirm delete? (y/N): ").strip().lower()
                if confirmation != 'y':
                    print("Deletion cancelled.")
                    sys.exit(0)
    except Exception as e:
        print(f"Warning: Could not retrieve pack details: {e}")

    success = delete_pack(pack_id)
    sys.exit(0 if success else 1)
