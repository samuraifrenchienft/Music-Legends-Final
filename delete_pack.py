#!/usr/bin/env python3
"""
Quick script to delete a specific pack from the database
"""

import sqlite3
import sys

def delete_pack(pack_id: str):
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
            
            # Delete pack
            cursor.execute("DELETE FROM creator_packs WHERE pack_id = ?", (pack_id,))
            deleted = cursor.rowcount
            
            conn.commit()
            
            if deleted > 0:
                print(f"✅ Deleted pack: {pack_id}")
                print(f"   Name: {pack_name}")
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
    success = delete_pack(pack_id)
    sys.exit(0 if success else 1)
