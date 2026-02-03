# services/backup_service.py
"""
Backup Service for Music Legends Bot
Handles database backups with local file storage and optional PostgreSQL sync
Supports both SQLite (file-based) and PostgreSQL (pg_dump) backups
"""

import os
import sqlite3
import gzip
import shutil
import asyncio
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
import json
import logging

logger = logging.getLogger(__name__)


class BackupService:
    """Service for managing database backups"""
    
    def __init__(self, db_path: str = "music_legends.db"):
        self.db_path = db_path
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.backup_dir / "daily").mkdir(exist_ok=True)
        (self.backup_dir / "critical").mkdir(exist_ok=True)
        (self.backup_dir / "shutdown").mkdir(exist_ok=True)
        
        # Check database type - disable PostgreSQL backups on Railway until tables are set up
        self.database_url = os.getenv("DATABASE_URL")
        self.is_railway = os.getenv("RAILWAY_ENVIRONMENT") is not None
        self.is_postgresql = bool(self.database_url and (
            "postgresql://" in self.database_url or 
            "postgres://" in self.database_url or
            "postgresql+asyncpg://" in self.database_url
        )) and not self.is_railway  # Disable on Railway for now
        # #region agent log
        with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
            import json
            f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"B","location":"backup_service.py:37","message":"Database type detection","data":{"database_url_set":self.database_url is not None,"is_postgresql":self.is_postgresql,"url_preview":self.database_url[:50] if self.database_url else None},"timestamp":int(__import__('time').time()*1000)})+'\n')
        # #endregion
        
        self.postgres_backup_url = os.getenv("POSTGRES_BACKUP_URL")
        self.last_backup_time = None
        self.backup_metadata_file = self.backup_dir / "backup_metadata.json"
        
        if self.is_railway:
            logger.info("🚂 Railway environment detected - using SQLite fallback backups")
        elif self.is_postgresql:
            logger.info("🗄️ PostgreSQL detected - using pg_dump for backups")
        else:
            logger.info("🗄️ SQLite detected - using file-based backups")
        
    def _load_metadata(self) -> Dict:
        """Load backup metadata"""
        if self.backup_metadata_file.exists():
            try:
                with open(self.backup_metadata_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_metadata(self, metadata: Dict):
        """Save backup metadata"""
        try:
            with open(self.backup_metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save backup metadata: {e}")
    
    def _get_backup_filename(self, backup_type: str, suffix: str = "", extension: str = None) -> str:
        """Generate backup filename with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        base_name = f"music_legends_{backup_type}_{timestamp}"
        if suffix:
            base_name += f"_{suffix}"
        
        # Determine extension based on database type
        if extension:
            return f"{base_name}.{extension}"
        elif self.is_postgresql:
            return f"{base_name}.sql"
        else:
            return f"{base_name}.db"
    
    def _check_disk_space(self, required_mb: int = 100) -> bool:
        """Check if enough disk space available"""
        try:
            import shutil
            stat = shutil.disk_usage(self.backup_dir)
            free_mb = stat.free / (1024 * 1024)
            return free_mb > required_mb
        except:
            return True  # Assume OK if check fails
    
    async def _backup_postgresql(self, backup_type: str, suffix: str, backup_subdir: Path) -> Optional[str]:
        """
        Create PostgreSQL backup using pg_dump
        
        Args:
            backup_type: Type of backup
            suffix: Optional suffix for filename
            backup_subdir: Directory to save backup
            
        Returns:
            Path to backup file if successful, None otherwise
        """
        try:
            # Parse DATABASE_URL to extract connection details
            # Format: postgresql://user:password@host:port/database
            # or: postgresql+asyncpg://user:password@host:port/database
            # #region agent log
            with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"A","location":"backup_service.py:109","message":"PostgreSQL backup entry","data":{"database_url_exists":self.database_url is not None,"url_length":len(self.database_url) if self.database_url else 0},"timestamp":int(__import__('time').time()*1000)})+'\n')
            # #endregion
            db_url = self.database_url.replace("postgresql+asyncpg://", "postgresql://")
            db_url = db_url.replace("postgres://", "postgresql://")
            
            # Extract components
            if not db_url.startswith("postgresql://"):
                logger.error(f"Invalid PostgreSQL URL format: {self.database_url}")
                # #region agent log
                with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    import json
                    f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"A","location":"backup_service.py:116","message":"Invalid URL format","data":{"db_url":db_url[:100]},"timestamp":int(__import__('time').time()*1000)})+'\n')
                # #endregion
                return None
            
            # Remove protocol
            url_part = db_url.replace("postgresql://", "")
            
            # Parse user:password@host:port/database
            if "@" not in url_part:
                logger.error("Invalid PostgreSQL URL format")
                return None
            
            auth_part, host_part = url_part.split("@", 1)
            # #region agent log
            with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"A","location":"backup_service.py:128","message":"URL parsing","data":{"auth_part_length":len(auth_part),"host_part_length":len(host_part),"has_colon":":" in auth_part},"timestamp":int(__import__('time').time()*1000)})+'\n')
            # #endregion
            if ":" in auth_part:
                user, password = auth_part.split(":", 1)
            else:
                user = auth_part
                password = ""
            
            if "/" in host_part:
                host_port, database = host_part.split("/", 1)
            else:
                host_port = host_part
                database = ""
            
            if ":" in host_port:
                host, port = host_port.split(":", 1)
            else:
                host = host_port
                port = "5432"
            
            # Generate backup filename
            backup_filename = self._get_backup_filename(backup_type, suffix, "sql")
            backup_path = backup_subdir / backup_filename
            temp_backup_path = backup_subdir / f"{backup_filename}.tmp"
            
            # Build pg_dump command
            # Use PGPASSWORD environment variable for password
            env = os.environ.copy()
            if password:
                env["PGPASSWORD"] = password
            
            # Use plain SQL format (-F p) for easier verification and restoration
            pg_dump_cmd = [
                "pg_dump",
                "-h", host,
                "-p", port,
                "-U", user,
                "-d", database,
                "-F", "p",  # Plain SQL format (readable, easy to verify)
                "--no-owner",  # Don't include ownership commands
                "--no-acl",    # Don't include access privileges
            ]
            
            # Run pg_dump in executor to avoid blocking
            loop = asyncio.get_event_loop()
            
            def run_pg_dump():
                try:
                    # #region agent log
                    with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        import json
                        f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"C","location":"backup_service.py:173","message":"pg_dump start","data":{"cmd":pg_dump_cmd[:5],"temp_path":str(temp_backup_path)},"timestamp":int(__import__('time').time()*1000)})+'\n')
                    # #endregion
                    # Write output directly to temp file
                    with open(temp_backup_path, 'w', encoding='utf-8') as f:
                        result = subprocess.run(
                            pg_dump_cmd,
                            env=env,
                            stdout=f,
                            stderr=subprocess.PIPE,
                            text=True,
                            check=True
                        )
                    # #region agent log
                    with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        import json
                        f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"C","location":"backup_service.py:185","message":"pg_dump success","data":{"returncode":result.returncode if 'result' in locals() else None},"timestamp":int(__import__('time').time()*1000)})+'\n')
                    # #endregion
                    return True
                except subprocess.CalledProcessError as e:
                    logger.error(f"pg_dump failed: {e.stderr}")
                    # #region agent log
                    with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        import json
                        f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"C","location":"backup_service.py:187","message":"pg_dump error","data":{"returncode":e.returncode,"stderr":str(e.stderr)[:200]},"timestamp":int(__import__('time').time()*1000)})+'\n')
                    # #endregion
                    return False
                except FileNotFoundError:
                    logger.error("pg_dump not found. Install PostgreSQL client tools.")
                    # #region agent log
                    with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        import json
                        f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"C","location":"backup_service.py:190","message":"pg_dump not found","data":{},"timestamp":int(__import__('time').time()*1000)})+'\n')
                    # #endregion
                    return False
            
            success = await loop.run_in_executor(None, run_pg_dump)
            
            if not success:
                if temp_backup_path.exists():
                    temp_backup_path.unlink()
                return None
            
            # Compress SQL backup
            compressed_path = backup_path.with_suffix('.sql.gz')
            # #region agent log
            with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"D","location":"backup_service.py:201","message":"Before compression","data":{"temp_exists":temp_backup_path.exists(),"temp_size":temp_backup_path.stat().st_size if temp_backup_path.exists() else 0},"timestamp":int(__import__('time').time()*1000)})+'\n')
            # #endregion
            try:
                with open(temp_backup_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                # #region agent log
                with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    import json
                    f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"D","location":"backup_service.py:207","message":"After compression","data":{"compressed_exists":compressed_path.exists(),"compressed_size":compressed_path.stat().st_size if compressed_path.exists() else 0},"timestamp":int(__import__('time').time()*1000)})+'\n')
                # #endregion
            except Exception as comp_err:
                # #region agent log
                with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    import json
                    f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"D","location":"backup_service.py:210","message":"Compression error","data":{"error":str(comp_err)},"timestamp":int(__import__('time').time()*1000)})+'\n')
                # #endregion
                raise
            
            # Remove uncompressed temp file
            temp_backup_path.unlink()
            
            # Verify backup
            # #region agent log
            with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"E","location":"backup_service.py:215","message":"Before integrity check","data":{"compressed_path":str(compressed_path)},"timestamp":int(__import__('time').time()*1000)})+'\n')
            # #endregion
            integrity_result = self.verify_backup_integrity(compressed_path)
            # #region agent log
            with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"E","location":"backup_service.py:217","message":"After integrity check","data":{"integrity_passed":integrity_result},"timestamp":int(__import__('time').time()*1000)})+'\n')
            # #endregion
            if not integrity_result:
                logger.error(f"PostgreSQL backup integrity check failed: {compressed_path}")
                compressed_path.unlink()
                return None
            
            # Update metadata
            metadata = self._load_metadata()
            backup_info = {
                "path": str(compressed_path),
                "type": backup_type,
                "database_type": "postgresql",
                "size_mb": compressed_path.stat().st_size / (1024 * 1024),
                "timestamp": datetime.now().isoformat(),
                "suffix": suffix
            }
            
            if "backups" not in metadata:
                metadata["backups"] = []
            metadata["backups"].append(backup_info)
            metadata["last_backup"] = datetime.now().isoformat()
            metadata["last_backup_type"] = backup_type
            metadata["database_type"] = "postgresql"
            self._save_metadata(metadata)
            
            # Update latest symlink (for PostgreSQL backups)
            latest_path = self.backup_dir / "latest.sql.gz"
            try:
                if latest_path.exists() or latest_path.is_symlink():
                    latest_path.unlink()
                latest_path.symlink_to(compressed_path.relative_to(self.backup_dir))
            except:
                pass  # Symlinks not supported on Windows
            
            self.last_backup_time = datetime.now()
            logger.info(f"✅ PostgreSQL backup created: {compressed_path} ({backup_info['size_mb']:.2f} MB)")
            
            return str(compressed_path)
            
        except Exception as e:
            logger.error(f"❌ PostgreSQL backup failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def backup_to_local(self, backup_type: str = "periodic", suffix: str = "") -> Optional[str]:
        """
        Create local backup of database (SQLite or PostgreSQL)
        
        Args:
            backup_type: Type of backup (periodic, critical, shutdown, daily)
            suffix: Optional suffix for filename
            
        Returns:
            Path to backup file if successful, None otherwise
        """
        # #region agent log
        with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
            import json
            f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"D","location":"backup_service.py:323","message":"backup_to_local entry","data":{"backup_type":backup_type,"suffix":suffix,"is_postgresql":self.is_postgresql,"db_path":self.db_path},"timestamp":int(__import__('time').time()*1000)})+'\n')
        # #endregion
        # Determine backup directory
        if backup_type == "daily":
            backup_subdir = self.backup_dir / "daily"
        elif backup_type == "critical":
            backup_subdir = self.backup_dir / "critical"
        elif backup_type == "shutdown":
            backup_subdir = self.backup_dir / "shutdown"
        else:
            backup_subdir = self.backup_dir
        
        backup_subdir.mkdir(exist_ok=True)
        
        # Use PostgreSQL backup if DATABASE_URL is set
        if self.is_postgresql:
            # #region agent log
            with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"B","location":"backup_service.py:340","message":"Using PostgreSQL backup","data":{},"timestamp":int(__import__('time').time()*1000)})+'\n')
            # #endregion
            return await self._backup_postgresql(backup_type, suffix, backup_subdir)
        
        # Otherwise use SQLite backup
        # #region agent log
        with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
            import json
            f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"D","location":"backup_service.py:346","message":"Using SQLite backup","data":{"db_path":self.db_path,"db_exists":os.path.exists(self.db_path)},"timestamp":int(__import__('time').time()*1000)})+'\n')
        # #endregion
        if not os.path.exists(self.db_path):
            logger.error(f"Database file not found: {self.db_path}")
            # #region agent log
            with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"D","location":"backup_service.py:351","message":"Database file not found","data":{"db_path":self.db_path},"timestamp":int(__import__('time').time()*1000)})+'\n')
            # #endregion
            return None
        
        if not self._check_disk_space():
            logger.warning("Insufficient disk space for backup")
            return None
        
        try:
            # Determine backup directory
            if backup_type == "daily":
                backup_subdir = self.backup_dir / "daily"
            elif backup_type == "critical":
                backup_subdir = self.backup_dir / "critical"
            elif backup_type == "shutdown":
                backup_subdir = self.backup_dir / "shutdown"
            else:
                backup_subdir = self.backup_dir
            
            backup_subdir.mkdir(exist_ok=True)
            
            # Generate backup filename
            backup_filename = self._get_backup_filename(backup_type, suffix)
            backup_path = backup_subdir / backup_filename
            temp_backup_path = backup_subdir / f"{backup_filename}.tmp"
            
            # Use SQLite backup API for atomic backup (run in executor to avoid blocking)
            loop = asyncio.get_event_loop()
            
            def do_backup():
                source_conn = sqlite3.connect(self.db_path)
                backup_conn = sqlite3.connect(str(temp_backup_path))
                try:
                    source_conn.backup(backup_conn)
                    backup_conn.close()
                    source_conn.close()
                    return True
                except Exception as e:
                    backup_conn.close()
                    source_conn.close()
                    raise e
            
            await loop.run_in_executor(None, do_backup)
            
            # Compress backup
            compressed_path = backup_path.with_suffix('.db.gz')
            with open(temp_backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove temporary file
            temp_backup_path.unlink()
            
            # Verify backup integrity
            if not self.verify_backup_integrity(compressed_path):
                logger.error(f"Backup integrity check failed: {compressed_path}")
                compressed_path.unlink()
                return None
            
            # Update metadata
            metadata = self._load_metadata()
            backup_info = {
                "path": str(compressed_path),
                "type": backup_type,
                "database_type": "sqlite",
                "size_mb": compressed_path.stat().st_size / (1024 * 1024),
                "timestamp": datetime.now().isoformat(),
                "suffix": suffix
            }
            
            if "backups" not in metadata:
                metadata["backups"] = []
            metadata["backups"].append(backup_info)
            metadata["last_backup"] = datetime.now().isoformat()
            metadata["last_backup_type"] = backup_type
            metadata["database_type"] = "sqlite"
            self._save_metadata(metadata)
            
            # Update latest symlink (if supported)
            latest_path = self.backup_dir / "latest.db.gz"
            try:
                if latest_path.exists() or latest_path.is_symlink():
                    latest_path.unlink()
                latest_path.symlink_to(compressed_path.relative_to(self.backup_dir))
            except:
                pass  # Symlinks not supported on Windows
            
            self.last_backup_time = datetime.now()
            logger.info(f"✅ Backup created: {compressed_path} ({backup_info['size_mb']:.2f} MB)")
            
            return str(compressed_path)
                
        except Exception as e:
            if 'temp_backup_path' in locals() and temp_backup_path.exists():
                temp_backup_path.unlink()
            logger.error(f"❌ Backup failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def backup_to_postgresql(self, backup_file_path: Optional[str] = None) -> bool:
        """
        Sync backup to external PostgreSQL storage (for long-term archival)
        This is separate from Railway's automatic backups - this is YOUR custom backup storage
        
        Args:
            backup_file_path: Path to backup file to sync (if None, uses latest backup)
        
        Returns:
            True if successful, False otherwise
        """
        # Note: Railway already handles automatic PostgreSQL backups (7 days retention)
        # This method is for syncing to YOUR OWN PostgreSQL instance for longer retention
        
        if not self.postgres_backup_url:
            logger.debug("POSTGRES_BACKUP_URL not set - skipping external PostgreSQL backup")
            return False
        
        try:
            import subprocess
            import tempfile
            
            # If no backup file specified, use latest backup
            if not backup_file_path:
                latest_backup = self.backup_dir / "latest.db.gz"
                if not latest_backup.exists():
                    logger.warning("No latest backup found for PostgreSQL sync")
                    return False
                backup_file_path = str(latest_backup)
            
            # Decompress backup if needed
            if backup_file_path.endswith('.gz'):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
                    with gzip.open(backup_file_path, 'rb') as f_in:
                        shutil.copyfileobj(f_in, tmp)
                    temp_db_path = tmp.name
            else:
                temp_db_path = backup_file_path
            
            try:
                # Use pg_dump approach: Convert SQLite to SQL and import to PostgreSQL
                # This is a simplified approach - for production, consider using a proper migration tool
                
                # Export SQLite schema and data
                sql_dump_path = temp_db_path.replace('.db', '.sql')
                subprocess.run([
                    'sqlite3', temp_db_path, '.dump'
                ], stdout=open(sql_dump_path, 'w'), check=False)
                
                # Import to PostgreSQL (requires psql)
                # Note: This is a basic implementation - SQLite and PostgreSQL have different SQL dialects
                # For production, use a proper migration tool or direct connection
                logger.info(f"PostgreSQL backup sync attempted for: {backup_file_path}")
                logger.warning("PostgreSQL sync requires manual SQL conversion - using local backup only")
                
                # Cleanup temp file
                if backup_file_path.endswith('.gz') and os.path.exists(temp_db_path):
                    os.unlink(temp_db_path)
                if os.path.exists(sql_dump_path):
                    os.unlink(sql_dump_path)
                
                return False  # Not fully implemented yet
                
            except Exception as e:
                logger.error(f"PostgreSQL backup processing failed: {e}")
                if backup_file_path.endswith('.gz') and os.path.exists(temp_db_path):
                    os.unlink(temp_db_path)
                return False
                
        except ImportError:
            logger.warning("PostgreSQL tools not available - skipping PostgreSQL backup")
            return False
        except Exception as e:
            logger.error(f"PostgreSQL backup failed: {e}")
            return False
    
    def verify_backup_integrity(self, backup_path: Path) -> bool:
        """
        Verify backup file integrity
        
        Args:
            backup_path: Path to backup file (.db, .db.gz, .sql, or .sql.gz)
            
        Returns:
            True if backup is valid, False otherwise
        """
        try:
            # PostgreSQL backup verification
            if backup_path.suffix in ['.sql', '.gz'] and ('.sql' in backup_path.name or self.is_postgresql):
                # For PostgreSQL, check if file exists and has content
                if backup_path.suffix == '.gz':
                    # Check if gzip file can be decompressed
                    try:
                        with gzip.open(backup_path, 'rb') as f:
                            # Read first few bytes to verify it's a valid gzip
                            header = f.read(100)
                            if len(header) < 10:
                                return False
                            # Check for pg_dump header markers
                            content = header.decode('utf-8', errors='ignore')
                            # pg_dump custom format has specific markers
                            if 'PGDMP' in content or 'CREATE' in content or 'INSERT' in content:
                                return True
                    except Exception as e:
                        logger.error(f"PostgreSQL backup verification failed: {e}")
                        return False
                else:
                    # Uncompressed SQL file
                    if backup_path.exists() and backup_path.stat().st_size > 0:
                        # Check for SQL content
                        with open(backup_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(1000)
                            if 'CREATE' in content or 'INSERT' in content:
                                return True
                return False
            
            # SQLite backup verification
            # Decompress if needed
            if backup_path.suffix == '.gz':
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
                    with gzip.open(backup_path, 'rb') as f_in:
                        shutil.copyfileobj(f_in, tmp)
                    tmp_path = tmp.name
            else:
                tmp_path = str(backup_path)
            
            # Try to open and verify SQLite database
            conn = sqlite3.connect(tmp_path)
            cursor = conn.cursor()
            
            # Check critical tables exist
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('users', 'cards', 'creator_packs', 'user_cards')
            """)
            tables = {row[0] for row in cursor.fetchall()}
            
            required_tables = {'users', 'cards', 'creator_packs', 'user_cards'}
            if not required_tables.issubset(tables):
                conn.close()
                if backup_path.suffix == '.gz':
                    os.unlink(tmp_path)
                return False
            
            # Check database integrity
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()
            
            if backup_path.suffix == '.gz':
                os.unlink(tmp_path)
            
            return result[0] == 'ok'
            
        except Exception as e:
            logger.error(f"Backup integrity check failed: {e}")
            return False
    
    def cleanup_old_backups(self, keep_days: int = 30, keep_critical: int = 100):
        """
        Clean up old backup files
        
        Args:
            keep_days: Keep backups for this many days
            keep_critical: Keep this many critical backups
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            deleted_count = 0
            
            # Clean up daily and periodic backups (both SQLite and PostgreSQL)
            for backup_file in self.backup_dir.glob("**/*.db.gz"):
                if backup_file.parent.name in ["daily", "shutdown"]:
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        backup_file.unlink()
                        deleted_count += 1
            
            # Clean up PostgreSQL backups (.sql.gz)
            for backup_file in self.backup_dir.glob("**/*.sql.gz"):
                if backup_file.parent.name in ["daily", "shutdown"]:
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        backup_file.unlink()
                        deleted_count += 1
            
            # Clean up critical backups (keep last N) - SQLite
            critical_backups = sorted(
                list((self.backup_dir / "critical").glob("*.db.gz")) +
                list((self.backup_dir / "critical").glob("*.sql.gz")),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            if len(critical_backups) > keep_critical:
                for old_backup in critical_backups[keep_critical:]:
                    old_backup.unlink()
                    deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"🗑️ Cleaned up {deleted_count} old backups")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            return 0
    
    async def backup_critical(self, event_type: str, event_id: str = "") -> Optional[str]:
        """Create critical backup after important event"""
        return await self.backup_to_local("critical", f"{event_type}_{event_id}")
    
    async def backup_shutdown(self) -> Optional[str]:
        """Create backup before bot shutdown"""
        return await self.backup_to_local("shutdown")
    
    async def backup_periodic(self) -> Optional[str]:
        """Create periodic backup"""
        # Skip if backup was created recently (within last 10 minutes)
        if self.last_backup_time:
            time_since_backup = datetime.now() - self.last_backup_time
            if time_since_backup.total_seconds() < 600:  # 10 minutes
                return None
        
        return await self.backup_to_local("periodic")
    
    async def backup_daily(self) -> Optional[str]:
        """Create daily backup"""
        return await self.backup_to_local("daily")
    
    def get_backup_stats(self) -> Dict:
        """Get backup statistics"""
        metadata = self._load_metadata()
        stats = {
            "total_backups": 0,
            "last_backup": metadata.get("last_backup"),
            "last_backup_type": metadata.get("last_backup_type"),
            "backups_by_type": {},
            "total_size_mb": 0
        }
        
        # Count SQLite backups
        for backup_file in self.backup_dir.glob("**/*.db.gz"):
            stats["total_backups"] += 1
            stats["total_size_mb"] += backup_file.stat().st_size / (1024 * 1024)
            
            backup_type = backup_file.parent.name
            if backup_type not in stats["backups_by_type"]:
                stats["backups_by_type"][backup_type] = 0
            stats["backups_by_type"][backup_type] += 1
        
        # Count PostgreSQL backups
        for backup_file in self.backup_dir.glob("**/*.sql.gz"):
            stats["total_backups"] += 1
            stats["total_size_mb"] += backup_file.stat().st_size / (1024 * 1024)
            
            backup_type = backup_file.parent.name
            if backup_type not in stats["backups_by_type"]:
                stats["backups_by_type"][backup_type] = 0
            stats["backups_by_type"][backup_type] += 1
        
        return stats


# Global instance
backup_service = BackupService()
