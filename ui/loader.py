# ui/loader.py
"""
UI Component Loader for Rehydration
Handles restoration of UI state after bot restart
"""

import time
from typing import Optional, Dict, Any
from ui.state import load_state, save_state, get_user_states
from commands.collection_ui import CollectionView
from commands.creator_dashboard import DashboardView


def restore_collection(state_id: str) -> Optional[CollectionView]:
    """
    Restore CollectionView from saved state
    
    Args:
        state_id: Unique identifier for the state
        
    Returns:
        CollectionView instance or None if state not found
    """
    try:
        data = load_state(state_id)
        if not data:
            return None

        return CollectionView(
            user_id=data["user"],
            page=data.get("page", 0),
            state_id=state_id
        )
        
    except Exception as e:
        print(f"Error restoring collection view: {e}")
        return None


def restore_dashboard(state_id: str) -> Optional[DashboardView]:
    """
    Restore DashboardView from saved state
    
    Args:
        state_id: Unique identifier for the state
        
    Returns:
        DashboardView instance or None if state not found
    """
    try:
        data = load_state(state_id)
        if not data:
            return None

        return DashboardView(
            user_id=data["user"],
            state_id=state_id
        )
        
    except Exception as e:
        print(f"Error restoring dashboard view: {e}")
        return None


def restore_all_user_states(user_id: int) -> Dict[str, Any]:
    """
    Restore all UI states for a user after restart
    
    Args:
        user_id: Discord user ID
        
    Returns:
        Dictionary mapping state_id to restored UI components
    """
    restored_states = {}
    
    try:
        user_states = get_user_states(user_id)
        
        for state_id, state_data in user_states.items():
            # Determine component type from state_id
            if "collection:" in state_id:
                view = restore_collection(state_id)
                if view:
                    restored_states[state_id] = view
                    
            elif "dashboard:" in state_id:
                view = restore_dashboard(state_id)
                if view:
                    restored_states[state_id] = view
                    
            # Add more component types as needed
            # elif "admin_review:" in state_id:
            #     view = restore_admin_review(state_id)
            #     if view:
            #         restored_states[state_id] = view
        
        if restored_states:
            print(f"✅ Restored {len(restored_states)} UI states for user {user_id}")
        
        return restored_states
        
    except Exception as e:
        print(f"Error restoring user states: {e}")
        return {}


def save_view_state(view, additional_data: Optional[Dict[str, Any]] = None) -> str:
    """
    Save current state of a view
    
    Args:
        view: The view instance to save state for
        additional_data: Additional data to save
        
    Returns:
        The state_id used for saving
    """
    try:
        # Get base state data
        state_data = {}
        
        # Add view-specific data
        if hasattr(view, 'user_id'):
            state_data["user"] = view.user_id
        
        if hasattr(view, 'page'):
            state_data["page"] = view.page
        
        if hasattr(view, 'state_id'):
            state_data["state_id"] = view.state_id
        
        # Add additional data
        if additional_data:
            state_data.update(additional_data)
        
        # Generate state_id if not present
        if not hasattr(view, 'state_id') or not view.state_id:
            view.state_id = f"{view.__class__.__name__.lower()}:{view.user_id}:{int(time.time())}"
        
        # Save state
        if save_state(view.state_id, state_data):
            return view.state_id
        
        return view.state_id
        
    except Exception as e:
        print(f"Error saving view state: {e}")
        return ""


def auto_save_state(view):
    """
    Automatically save state when view is modified
    Can be called from view methods to persist state changes
    """
    save_view_state(view)


def cleanup_expired_states():
    """
    Clean up expired state files
    Called on bot startup
    """
    from ui.state import cleanup_old_states
    cleanup_old_states()


# Example usage
def example_usage():
    """Example of loader usage"""
    
    # Restore collection view
    collection_view = restore_collection("collection:123456789:1642699200")
    if collection_view:
        print(f"✅ Restored collection view for user {collection_view.user_id}")
        print(f"   Current page: {collection_view.page}")
    
    # Restore dashboard view
    dashboard_view = restore_dashboard("dashboard:123456789:1642699200")
    if dashboard_view:
        print(f"✅ Restored dashboard view for user {dashboard_view.user_id}")
    
    # Restore all user states
    restored = restore_all_user_states(123456789)
    print(f"✅ Restored {len(restored_states)} UI components")


if __name__ == "__main__":
    example_usage()
