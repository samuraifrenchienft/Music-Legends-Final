# ui/state.py
"""
State Management for UI Components
Handles persistent state across bot restarts
"""

import json
import time
from typing import Dict, Any, Optional
from pathlib import Path

# State storage directory
STATE_DIR = Path("state")
STATE_DIR.mkdir(exist_ok=True)

def save_state(state_id: str, data: Dict[str, Any]) -> bool:
    """
    Save state data to file
    
    Args:
        state_id: Unique identifier for the state
        data: Dictionary of state data
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        state_file = STATE_DIR / f"{state_id}.json"
        
        # Add timestamp
        data["saved_at"] = int(time.time())
        data["state_id"] = state_id
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return True
        
    except Exception as e:
        print(f"Error saving state {state_id}: {e}")
        return False


def load_state(state_id: str) -> Optional[Dict[str, Any]]:
    """
    Load state data from file
    
    Args:
        state_id: Unique identifier for the state
        
    Returns:
        Dictionary of state data or None if not found
    """
    try:
        state_file = STATE_DIR / f"{state_id}.json"
        
        if not state_file.exists():
            return None
        
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check if state is too old (24 hours)
        saved_at = data.get("saved_at", 0)
        if int(time.time()) - saved_at > 86400:  # 24 hours
            # Clean up old state
            state_file.unlink()
            return None
        
        return data
        
    except Exception as e:
        print(f"Error loading state {state_id}: {e}")
        return None


def cleanup_old_states():
    """Clean up state files older than 24 hours"""
    try:
        current_time = int(time.time())
        cleanup_count = 0
        
        for state_file in STATE_DIR.glob("*.json"):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                saved_at = data.get("saved_at", 0)
                if current_time - saved_at > 86400:  # 24 hours
                    state_file.unlink()
                    cleanup_count += 1
                    
            except Exception:
                # Try to delete corrupted file
                try:
                    state_file.unlink()
                    cleanup_count += 1
                except:
                    pass
                    
        except Exception as e:
            print(f"Error during cleanup: {e}")
        
        if cleanup_count > 0:
            print(f"Cleaned up {cleanup_count} old state files")
            
    except Exception as e:
        print(f"Error during state cleanup: {e}")


def get_user_states(user_id: int) -> Dict[str, Dict[str, Any]]:
    """
    Get all states for a specific user
    
    Args:
        user_id: Discord user ID
        
    Returns:
        Dictionary mapping state_id to state data
    """
    user_states = {}
    
    try:
        for state_file in STATE_DIR.glob(f"*{user_id}*.json"):
            try:
                state_id = state_file.stem  # filename without .json
                data = load_state(state_id)
                if data:
                    user_states[state_id] = data
            except Exception:
                continue
                
    except Exception as e:
        print(f"Error getting user states: {e}")
    
    return user_states


def delete_state(state_id: str) -> bool:
    """
    Delete a specific state file
    
    Args:
        state_id: Unique identifier for the state
        
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        state_file = STATE_DIR / f"{state_id}.json"
        
        if state_file.exists():
            state_file.unlink()
            return True
        
        return False
        
    except Exception as e:
        print(f"Error deleting state {state_id}: {e}")
        return False


def update_state(state_id: str, updates: Dict[str, Any]) -> bool:
    """
    Update existing state with new data
    
    Args:
        state_id: Unique identifier for the state
        updates: Dictionary of updates to apply
        
    Returns:
        True if updated successfully, False otherwise
    """
    try:
        data = load_state(state_id)
        if not data:
            return False
        
        data.update(updates)
        return save_state(state_id, data)
        
    except Exception as e:
        print(f"Error updating state {state_id}: {e}")
        return False


# Example usage
def example_usage():
    """Example of state management usage"""
    
    # Save state
    state_id = f"dash:123456789:{int(time.time())}"
    state_data = {
        "user": 123456789,
        "page": 0,
        "filters": {"tier": "legendary"},
        "sort_by": "newest"
    }
    
    if save_state(state_id, state_data):
        print(f"✅ State saved: {state_id}")
    
    # Load state
    loaded_data = load_state(state_id)
    if loaded_data:
        print(f"✅ State loaded: {loaded_data}")
    
    # Update state
    updates = {"page": 1, "filters": {"tier": "epic"}}
    if update_state(state_id, updates):
        print(f"✅ State updated: {state_id}")
    
    # Delete state
    if delete_state(state_id):
        print(f"✅ State deleted: {state_id}")


if __name__ == "__main__":
    example_usage()
