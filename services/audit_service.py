"""
Audit Service

Provides comprehensive logging and audit trail functionality for the Discord bot.
Tracks all important events including permissions, role changes, and user actions.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

class AuditLog:
    """
    Comprehensive audit logging system for tracking bot events.
    """
    
    def __init__(self, log_dir: str = "logs/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Current log file (rotates daily)
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.current_log_file = self.log_dir / f"audit_{self.current_date}.log"
    
    @classmethod
    def record(cls, event: str, user_id: int, target_id: Optional[int] = None, 
               details: Optional[Dict[str, Any]] = None):
        """
        Record an audit event.
        
        Args:
            event: Type of event (e.g., "permission_denied", "role_granted")
            user_id: ID of the user who performed the action
            target_id: ID of the target (user, role, etc.) if applicable
            details: Additional event details
        """
        instance = cls()
        instance._write_log(event, user_id, target_id, details)
    
    def _write_log(self, event: str, user_id: int, target_id: Optional[int], 
                   details: Optional[Dict[str, Any]]):
        """Write an audit log entry."""
        # Check if we need to rotate log files
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self.current_date:
            self.current_date = today
            self.current_log_file = self.log_dir / f"audit_{self.current_date}.log"
        
        # Create log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "user_id": user_id,
            "target_id": target_id,
            "details": details or {}
        }
        
        # Write to log file
        try:
            with open(self.current_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"Failed to write audit log: {e}")
    
    def get_events(self, event_type: Optional[str] = None, 
                   user_id: Optional[int] = None,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve audit events with filtering options.
        
        Args:
            event_type: Filter by event type
            user_id: Filter by user ID
            start_date: Filter events after this date
            end_date: Filter events before this date
            limit: Maximum number of events to return
            
        Returns:
            List of audit events
        """
        events = []
        
        # Determine which log files to search
        if start_date and end_date:
            # Search specific date range
            current_date = start_date.date()
            while current_date <= end_date.date():
                log_file = self.log_dir / f"audit_{current_date.strftime('%Y-%m-%d')}.log"
                if log_file.exists():
                    events.extend(self._read_log_file(log_file))
                current_date += timedelta(days=1)
        else:
            # Search recent logs (last 7 days by default)
            current_date = datetime.now().date()
            for i in range(7):
                log_file = self.log_dir / f"audit_{current_date.strftime('%Y-%m-%d')}.log"
                if log_file.exists():
                    events.extend(self._read_log_file(log_file))
                current_date -= timedelta(days=1)
        
        # Apply filters
        filtered_events = events
        
        if event_type:
            filtered_events = [e for e in filtered_events if e.get("event") == event_type]
        
        if user_id:
            filtered_events = [e for e in filtered_events if e.get("user_id") == user_id]
        
        if start_date:
            filtered_events = [
                e for e in filtered_events 
                if datetime.fromisoformat(e.get("timestamp")) >= start_date
            ]
        
        if end_date:
            filtered_events = [
                e for e in filtered_events 
                if datetime.fromisoformat(e.get("timestamp")) <= end_date
            ]
        
        # Sort by timestamp (newest first) and limit
        filtered_events.sort(
            key=lambda x: datetime.fromisoformat(x.get("timestamp")), 
            reverse=True
        )
        
        return filtered_events[:limit]
    
    def _read_log_file(self, log_file: Path) -> List[Dict[str, Any]]:
        """Read and parse a log file."""
        events = []
        
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            print(f"Failed to read log file {log_file}: {e}")
        
        return events
    
    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get audit statistics for the specified time period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with audit statistics
        """
        start_date = datetime.now() - timedelta(days=days)
        events = self.get_events(start_date=start_date, limit=10000)
        
        # Count events by type
        event_counts = {}
        for event in events:
            event_type = event.get("event", "unknown")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        # Count unique users
        unique_users = len(set(e.get("user_id") for e in events if e.get("user_id")))
        
        # Most common events
        sorted_events = sorted(event_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "period_days": days,
            "total_events": len(events),
            "unique_users": unique_users,
            "event_counts": event_counts,
            "top_events": sorted_events[:10],
            "events_per_day": round(len(events) / days, 2) if days > 0 else 0
        }
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """
        Clean up old audit log files.
        
        Args:
            days_to_keep: Number of days to keep log files
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for log_file in self.log_dir.glob("audit_*.log"):
            try:
                # Extract date from filename
                date_str = log_file.stem.replace("audit_", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                if file_date < cutoff_date:
                    log_file.unlink()
                    print(f"Deleted old audit log: {log_file}")
                    
            except ValueError:
                continue  # Skip files that don't match the expected format
    
    def export_events(self, output_file: str, event_type: Optional[str] = None,
                      user_id: Optional[int] = None, days: int = 7) -> bool:
        """
        Export audit events to a JSON file.
        
        Args:
            output_file: Path to output file
            event_type: Filter by event type
            user_id: Filter by user ID
            days: Number of days to export
            
        Returns:
            True if successful, False otherwise
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            events = self.get_events(
                event_type=event_type,
                user_id=user_id,
                start_date=start_date,
                limit=10000
            )
            
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "filters": {
                    "event_type": event_type,
                    "user_id": user_id,
                    "days": days
                },
                "events": events
            }
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Failed to export audit events: {e}")
            return False

# Global audit log instance
audit_log = AuditLog()

# Convenience functions
def record_permission_denied(user_id: int, command: str, required_role: str, **details):
    """Record a permission denial event."""
    AuditLog.record(
        event="permission_denied",
        user_id=user_id,
        details={
            "command": command,
            "required_role": required_role,
            **details
        }
    )

def record_role_change(user_id: int, role_name: str, action: str, **details):
    """Record a role change event."""
    AuditLog.record(
        event=f"role_{action}",
        user_id=user_id,
        details={
            "role_name": role_name,
            **details
        }
    )

def record_ui_interaction(user_id: int, owner_id: int, interaction_type: str, **details):
    """Record a UI interaction event."""
    AuditLog.record(
        event=f"ui_{interaction_type}",
        user_id=user_id,
        target_id=owner_id,
        details=details
    )

def record_command_usage(user_id: int, command: str, success: bool, **details):
    """Record a command usage event."""
    AuditLog.record(
        event="command_usage",
        user_id=user_id,
        details={
            "command": command,
            "success": success,
            **details
        }
    )

def record_security_event(user_id: int, event_type: str, **details):
    """Record a security-related event."""
    AuditLog.record(
        event=f"security_{event_type}",
        user_id=user_id,
        details=details
    )
