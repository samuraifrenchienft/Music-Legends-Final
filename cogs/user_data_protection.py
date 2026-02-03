# user_data_protection.py
"""
Comprehensive User Data Protection System
- Encryption of sensitive data at rest
- Access control and audit trails
- GDPR compliance utilities
- Data masking and sanitization
- Encryption key management
- Data export and deletion
"""

import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any, Tuple
from cryptography.fernet import Fernet
from functools import wraps
import discord
from discord import Interaction

from cogs.security_event_logger import security_logger, EventSeverity, log_suspicious_activity


# ==========================================
# ENCRYPTION & KEY MANAGEMENT
# ==========================================

class EncryptionManager:
    """Manage encryption keys and data encryption"""
    
    def __init__(self, key_file: str = "config/.encryption_key"):
        self.key_file = key_file
        self.cipher = None
        self._load_or_create_key()
    
    def _load_or_create_key(self):
        """Load existing encryption key or create new one"""
        try:
            if os.path.exists(self.key_file):
                with open(self.key_file, 'rb') as f:
                    key = f.read()
                print(f"✅ [ENCRYPTION] Loaded existing encryption key")
            else:
                # Create new key
                key = Fernet.generate_key()
                os.makedirs(os.path.dirname(self.key_file), exist_ok=True)
                
                # Save key with restricted permissions
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                os.chmod(self.key_file, 0o600)  # Read/write owner only
                
                print(f"✅ [ENCRYPTION] Generated new encryption key")
            
            self.cipher = Fernet(key)
        
        except Exception as e:
            print(f"❌ [ENCRYPTION] Failed to initialize encryption: {e}")
            raise
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data"""
        try:
            encrypted = self.cipher.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            print(f"❌ [ENCRYPTION] Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data"""
        try:
            decrypted = self.cipher.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            print(f"❌ [ENCRYPTION] Decryption failed: {e}")
            raise
    
    def encrypt_dict(self, data: Dict, fields_to_encrypt: List[str]) -> Dict:
        """Encrypt specific fields in dictionary"""
        encrypted = data.copy()
        for field in fields_to_encrypt:
            if field in encrypted and encrypted[field]:
                encrypted[field] = self.encrypt(str(encrypted[field]))
        return encrypted
    
    def decrypt_dict(self, data: Dict, fields_to_decrypt: List[str]) -> Dict:
        """Decrypt specific fields in dictionary"""
        decrypted = data.copy()
        for field in fields_to_decrypt:
            if field in decrypted and decrypted[field]:
                try:
                    decrypted[field] = self.decrypt(decrypted[field])
                except Exception as e:
                    print(f"⚠️  [ENCRYPTION] Failed to decrypt {field}: {e}")
                    decrypted[field] = None
        return decrypted


# ==========================================
# USER DATA PROTECTION
# ==========================================

class UserDataProtector:
    """
    Comprehensive user data protection
    
    Features:
    - Sensitive data masking
    - Encryption at rest
    - Access control
    - Audit trails
    - GDPR compliance
    """
    
    # Sensitive field patterns
    SENSITIVE_FIELDS = [
        'password', 'token', 'secret', 'key', 'api_key',
        'credit_card', 'ssn', 'email', 'phone', 'address',
        'ip_address', 'payment_method', 'stripe_id'
    ]
    
    # Fields that should be encrypted at rest
    ENCRYPTED_FIELDS = [
        'password_hash', 'payment_method', 'credit_card_token',
        'stripe_customer_id', 'api_key', 'oauth_token'
    ]
    
    def __init__(self, encryption_manager: EncryptionManager = None):
        self.encryption_manager = encryption_manager or EncryptionManager()
        print(f"✅ [DATA_PROTECTION] User data protector initialized")
    
    @staticmethod
    def is_sensitive_field(field_name: str) -> bool:
        """Check if field contains sensitive data"""
        return any(
            sensitive in field_name.lower()
            for sensitive in UserDataProtector.SENSITIVE_FIELDS
        )
    
    @staticmethod
    def mask_sensitive_data(
        data: Dict,
        mask_char: str = '*',
        mask_length: int = 4
    ) -> Dict:
        """
        Mask sensitive fields in dictionary
        
        Example:
            {'email': 'user@example.com', 'name': 'John'}
            → {'email': '****', 'name': 'John'}
        """
        masked = {}
        
        for key, value in data.items():
            if UserDataProtector.is_sensitive_field(key):
                # Create masked value
                if isinstance(value, str):
                    masked[key] = mask_char * mask_length
                else:
                    masked[key] = None
            else:
                masked[key] = value
        
        return masked
    
    @staticmethod
    def redact_sensitive_data(data: Dict) -> Dict:
        """
        Remove sensitive fields entirely from dictionary
        (More aggressive than masking)
        """
        redacted = {}
        
        for key, value in data.items():
            if not UserDataProtector.is_sensitive_field(key):
                redacted[key] = value
        
        return redacted
    
    @staticmethod
    def hash_sensitive_field(
        value: str,
        algorithm: str = 'sha256'
    ) -> str:
        """
        One-way hash of sensitive field
        (Cannot be decrypted, only compared)
        """
        if not value:
            return None
        
        try:
            if algorithm == 'sha256':
                return hashlib.sha256(value.encode()).hexdigest()
            else:
                return hashlib.md5(value.encode()).hexdigest()
        except Exception as e:
            print(f"❌ [DATA_PROTECTION] Hash failed: {e}")
            return None
    
    def encrypt_user_data(self, user_data: Dict) -> Dict:
        """Encrypt sensitive fields for storage"""
        return self.encryption_manager.encrypt_dict(
            user_data,
            self.ENCRYPTED_FIELDS
        )
    
    def decrypt_user_data(self, user_data: Dict) -> Dict:
        """Decrypt sensitive fields from storage"""
        return self.encryption_manager.decrypt_dict(
            user_data,
            self.ENCRYPTED_FIELDS
        )


# ==========================================
# ACCESS CONTROL & AUDIT TRAIL
# ==========================================

class DataAccessAuditor:
    """Track and audit all user data access"""
    
    def __init__(self, log_file: str = "logs/data_access_audit.json"):
        self.log_file = log_file
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        print(f"✅ [AUDIT] Data access auditor initialized")
    
    def log_access(
        self,
        accessor_user_id: int,
        target_user_id: int,
        action: str,
        fields_accessed: List[str],
        access_granted: bool,
        reason: str = None
    ):
        """Log user data access"""
        
        access_log = {
            "timestamp": datetime.now().isoformat(),
            "accessor_user_id": str(accessor_user_id),
            "target_user_id": str(target_user_id),
            "action": action,
            "fields_accessed": fields_accessed,
            "access_granted": access_granted,
            "reason": reason or "No reason provided"
        }
        
        try:
            with open(self.log_file, 'a') as f:
                json.dump(access_log, f)
                f.write('\n')
            
            status = "✅ GRANTED" if access_granted else "❌ DENIED"
            print(f"{status} [AUDIT] User {accessor_user_id} → {target_user_id}: {action}")
            
            # Log to security logger if denied
            if not access_granted:
                security_logger.log_event(
                    "DATA_ACCESS_DENIED",
                    severity=EventSeverity.WARNING,
                    user_id=accessor_user_id,
                    details={
                        "target_user": str(target_user_id),
                        "action": action,
                        "reason": reason
                    }
                )
        
        except Exception as e:
            print(f"❌ [AUDIT] Failed to log access: {e}")
    
    def get_access_history(
        self,
        user_id: int,
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict]:
        """Get access history for user"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        access_logs = []
        
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    try:
                        log_entry = json.loads(line)
                        log_time = datetime.fromisoformat(log_entry['timestamp'])
                        
                        if log_time < cutoff_time:
                            continue
                        
                        if (log_entry['target_user_id'] == str(user_id) or
                            log_entry['accessor_user_id'] == str(user_id)):
                            access_logs.append(log_entry)
                        
                        if len(access_logs) >= limit:
                            break
                    
                    except json.JSONDecodeError:
                        continue
        
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"❌ [AUDIT] Failed to read access history: {e}")
        
        return access_logs


# ==========================================
# GDPR COMPLIANCE UTILITIES
# ==========================================

class GDPRCompliance:
    """GDPR compliance utilities for user data"""
    
    def __init__(self, data_protector: UserDataProtector):
        self.data_protector = data_protector
        print(f"✅ [GDPR] GDPR compliance utilities initialized")
    
    @staticmethod
    def create_data_export(user_data: Dict) -> Dict:
        """
        Create GDPR-compliant data export
        
        Returns all personal data in portable format
        """
        
        export = {
            "export_date": datetime.now().isoformat(),
            "format_version": "1.0",
            "user_data": user_data,
            "data_categories": {
                "personal_info": ["name", "email", "user_id"],
                "account_data": ["created_at", "last_login", "settings"],
                "activity_data": ["packs_created", "cards_collected", "games_played"],
                "payment_data": ["subscription_status", "payment_history"]
            }
        }
        
        return export
    
    def create_anonymized_copy(self, user_data: Dict) -> Dict:
        """
        Create anonymized copy of user data
        (For testing/support without exposing PII)
        """
        
        anonymized = {}
        
        for key, value in user_data.items():
            if self.data_protector.is_sensitive_field(key):
                # Hash sensitive fields
                if isinstance(value, str):
                    anonymized[key] = self.data_protector.hash_sensitive_field(value)
                else:
                    anonymized[key] = "REDACTED"
            else:
                # Keep non-sensitive fields
                anonymized[key] = value
        
        return anonymized
    
    @staticmethod
    def prepare_deletion_package(user_id: int) -> Dict:
        """
        Prepare data for deletion (right to be forgotten)
        
        Documents what will be deleted
        """
        
        deletion_package = {
            "user_id": str(user_id),
            "deletion_date": datetime.now().isoformat(),
            "reason": "GDPR right to be forgotten",
            "data_to_delete": [
                "personal_information",
                "account_data",
                "payment_records",
                "activity_history",
                "preferences",
                "authentication_tokens"
            ],
            "data_to_retain": [
                "transaction_records (7 years - legal requirement)",
                "fraud_detection_logs (2 years - legal requirement)",
                "audit_logs (1 year - security requirement)"
            ],
            "deletion_confirmation_token": secrets.token_urlsafe(32)
        }
        
        return deletion_package


# ==========================================
# GLOBAL INSTANCES
# ==========================================

encryption_manager = EncryptionManager()
data_protector = UserDataProtector(encryption_manager)
access_auditor = DataAccessAuditor()
gdpr_compliance = GDPRCompliance(data_protector)


# ==========================================
# DECORATORS FOR DATA ACCESS CONTROL
# ==========================================

def protected_user_data(required_permission: str = "self"):
    """
    Decorator for commands that access user data
    
    Args:
        required_permission: "self" (own data) or "admin" (any user)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: Interaction, target_user_id: int = None, *args, **kwargs):
            accessor_id = interaction.user.id
            target_id = target_user_id or accessor_id
            
            # Determine if access is allowed
            is_self = accessor_id == target_id
            is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
            is_bot_owner = (await interaction.client.application_info()).owner.id == accessor_id
            
            access_allowed = False
            reason = None
            
            if required_permission == "self":
                if is_self:
                    access_allowed = True
                    reason = "Own data access"
                elif is_admin or is_bot_owner:
                    access_allowed = True
                    reason = "Admin/Owner override"
                else:
                    reason = "Not data owner and not admin"
            
            elif required_permission == "admin":
                if is_admin or is_bot_owner:
                    access_allowed = True
                    reason = "Admin permission granted"
                else:
                    reason = "Not administrator"
            
            # Log access attempt
            fields = kwargs.get('fields', [func.__name__])
            access_auditor.log_access(
                accessor_user_id=accessor_id,
                target_user_id=target_id,
                action=func.__name__,
                fields_accessed=fields,
                access_granted=access_allowed,
                reason=reason
            )
            
            # Deny access if not allowed
            if not access_allowed:
                security_logger.log_event(
                    "DATA_ACCESS_DENIED",
                    severity=EventSeverity.WARNING,
                    user_id=accessor_id,
                    details={
                        "command": func.__name__,
                        "target_user": str(target_id),
                        "reason": reason
                    }
                )
                
                await interaction.response.send_message(
                    "❌ **Access Denied**\n\n"
                    "You do not have permission to access this data.\n"
                    "This access attempt has been logged.",
                    ephemeral=True
                )
                return
            
            # Execute function with access granted
            return await func(interaction, target_user_id, *args, **kwargs)
        
        return wrapper
    return decorator


# ==========================================
# HELPER FUNCTIONS
# ==========================================

async def get_user_data_safe(
    user_id: int,
    requester_id: int,
    is_admin: bool = False
) -> Tuple[bool, Optional[Dict]]:
    """
    Safely retrieve user data with access control
    
    Returns:
        Tuple of (success, data or error_message)
    """
    
    # Check access permission
    if user_id != requester_id and not is_admin:
        access_auditor.log_access(
            accessor_user_id=requester_id,
            target_user_id=user_id,
            action="get_user_data",
            fields_accessed=["all"],
            access_granted=False,
            reason="Not data owner and not admin"
        )
        return False, "Access denied: insufficient permissions"
    
    # Log successful access
    access_auditor.log_access(
        accessor_user_id=requester_id,
        target_user_id=user_id,
        action="get_user_data",
        fields_accessed=["all"],
        access_granted=True,
        reason="Owner access" if user_id == requester_id else "Admin access"
    )
    
    # Return masked user data (implementation depends on your DB)
    user_data = {
        "user_id": user_id,
        "username": "****",  # Would fetch from DB
        "email": "****",
        "created_at": "2026-01-15T10:30:00"
    }
    
    return True, data_protector.mask_sensitive_data(user_data)


async def export_user_data(user_id: int) -> Dict:
    """Export user data in GDPR-compliant format"""
    
    # Fetch user data (implementation depends on your DB)
    user_data = {
        "user_id": user_id,
        "username": "john_doe",
        "email": "john@example.com",
        "created_at": "2026-01-15T10:30:00"
    }
    
    # Create export
    export = gdpr_compliance.create_data_export(user_data)
    
    # Log data export
    security_logger.log_event(
        "DATA_EXPORT_REQUESTED",
        severity=EventSeverity.INFO,
        user_id=user_id,
        details={"export_date": export["export_date"]}
    )
    
    return export


async def delete_user_data(user_id: int) -> Dict:
    """Delete user data (right to be forgotten)"""
    
    # Create deletion package
    deletion_pkg = gdpr_compliance.prepare_deletion_package(user_id)
    
    # Log deletion request
    security_logger.log_event(
        "DATA_DELETION_REQUESTED",
        severity=EventSeverity.INFO,
        user_id=user_id,
        details={
            "deletion_date": deletion_pkg["deletion_date"],
            "confirmation_token": deletion_pkg["deletion_confirmation_token"]
        }
    )
    
    return deletion_pkg
