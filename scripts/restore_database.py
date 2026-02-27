#!/usr/bin/env python3
"""
Database Restore Script for Music Legends Bot
Uses PostgreSQL client tools for restoring from backup
"""


import sys
import argparse
import subprocess
from datetime import datetime
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import settings
from urllib.parse import urlparse

def _parse_db_url(url: str) -> dict:
    """Parse database URL into components."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://")
    p = urlparse(url)
    return {
        "db_user": p.username,
        "db_password": p.password,
        "db_host": p.hostname,
        "db_port": p.port,
        "db_name": p.path.lstrip("/"),
    }


def run_command(cmd, check=True):
    """Run a shell command and handle errors"""
    try:
        result = subprocess.run(cmd, shell=True, check=check, 
                              capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running command: {cmd}")
        print(f"Error output: {e.stderr}")
        return None

def check_postgres_tools():
    """Check if PostgreSQL client tools are available"""
    if not run_command("pg_restore --version", check=False):
        print("❌ Error: pg_restore not found. PostgreSQL client tools not installed.")
        return False
    return True

def test_database_connection(db_host, db_port, db_user):
    """Test database connection"""
    cmd = f"pg_isready -h {db_host} -p {db_port} -U {db_user}"
    return run_command(cmd, check=False) is not None

def restore_database(backup_file, db_name, db_host, db_port, db_user, db_password):
    """Restore database from backup file"""
    
    # Check if backup file exists
    if not os.path.exists(backup_file):
        print(f"❌ Error: Backup file not found: {backup_file}")
        return False
    
    # Set environment variables
    env = os.environ.copy()
    env['PGPASSWORD'] = db_password
    
    # Check if backup is compressed
    if backup_file.endswith('.gz'):
        print("🗜️ Decompressing backup file...")
        decompress_cmd = f"gunzip -c {backup_file}"
        restore_cmd = f"psql -h {db_host} -p {db_port} -U {db_user} -d {db_name}"
        
        try:
            with subprocess.Popen(decompress_cmd, shell=True, stdout=subprocess.PIPE) as decompress:
                result = subprocess.run(restore_cmd, shell=True, 
                                      stdin=decompress.stdout, 
                                      capture_output=True, text=True, env=env)
                decompress.stdout.close()
                if result.returncode != 0:
                    print(f"❌ Error during restore: {result.stderr}")
                    return False
        except Exception as e:
            print(f"❌ Error during decompression/restore: {e}")
            return False
    else:
        # Direct restore for uncompressed files
        restore_cmd = f"psql -h {db_host} -p {db_port} -U {db_user} -d {db_name} < {backup_file}"
        
        result = subprocess.run(restore_cmd, shell=True, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            print(f"❌ Error during restore: {result.stderr}")
            return False
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Restore Music Legends database from backup')
    parser.add_argument('backup_file', help='Path to backup file (.sql or .sql.gz)')
    db_parts = _parse_db_url(settings.DATABASE_URL)

    parser.add_argument('--db-name', default=db_parts.get('db_name', 'music_legends'), 
                       help='Database name')
    parser.add_argument('--db-host', default=db_parts.get('db_host', 'localhost'), 
                       help='Database host')
    parser.add_argument('--db-port', default=db_parts.get('db_port', '5432'), 
                       help='Database port')
    parser.add_argument('--db-user', default=db_parts.get('db_user', 'postgres'), 
                       help='Database user')
    parser.add_argument('--db-password', default=db_parts.get('db_password'), 
                       help='Database password')
    
    args = parser.parse_args()
    
    print("🗄️ Database Restore Script for Music Legends Bot")
    print("=" * 50)
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Backup file: {args.backup_file}")
    print(f"🗃️ Database: {args.db_name}")
    print(f"🌐 Host: {args.db_host}:{args.db_port}")
    print()
    
    # Check prerequisites
    if not check_postgres_tools():
        sys.exit(1)
    
    if not test_database_connection(args.db_host, args.db_port, args.db_user):
        print(f"❌ Error: Cannot connect to database at {args.db_host}:{args.db_port}")
        sys.exit(1)
    
    # Confirm restore
    response = input("⚠️  This will overwrite the existing database. Continue? (y/N): ")
    if response.lower() not in ['y', 'yes']:
        print("❌ Restore cancelled by user")
        sys.exit(0)
    
    # Perform restore
    print("🔄 Starting database restore...")
    if restore_database(args.backup_file, args.db_name, args.db_host, 
                       args.db_port, args.db_user, args.db_password):
        print("✅ Database restore completed successfully!")
        print("🎉 Your Music Legends database has been restored from backup")
    else:
        print("❌ Database restore failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
