# ENHANCED INTERACTION SAFETY
# Complete interaction safety system for UI components
# Ensures only owners can interact with their own components

import time
from typing import Optional, Dict, Any
from discord import Interaction
from ui.state import load_state, save_state, get_user_states
from models.creator_pack import CreatorPack
from models.card import Card

class SafeDashboardView(View):
    """
    Enhanced Dashboard View with comprehensive safety checks
    Ensures only owners can interact with their dashboard
    """
    
    def __init__(self, user_id: int, state_id: Optional[str] = None):
        super().__init__(timeout=None)  # No timeout for persistence
        self.user_id = user_id
        self.state_id = state_id or f"dashboard:{user_id}:{int(time.time())}"
        
        # Load existing state or create new
        existing_state = load_state(self.state_id)
        if existing_state:
            self.page = existing_state.get("page", 0)
            self.selected_pack_id = existing_state.get("selected_pack_id")
            self.filters = existing_state.get("filters", {})
            self.sort_by = existing_state.get("sort_by", "newest")
            
            # Validate state integrity
            if not self._validate_state(existing_state):
                print(f"⚠️ State validation failed for user {user_id}")
                # Reset to safe defaults
                self.page = 0
                self.selected_pack_id = None
                self.filters = {}
                self.sort_by = "newest"
                self.state_id = f"dashboard:{user_id}:{int(time.time())}"
                self.save_state()
        else:
            # Create new state
            self.page = 0
            self.selected_pack_id = None
            self.filters = {}
            self.sort_by = "newest"
            self.state_id = f"dashboard:{user_id}:{int(time.time())}"
            
            # Save initial state
            self.save_state()
    
    def _validate_state(self, state_data: Dict[str, Any]) -> bool:
        """Validate state data integrity"""
        try:
            # Check basic structure
            if not isinstance(state_data, dict):
                return False
            
            # Check required fields
            if "user" not in state_data:
                return False
            
            # Check data types
            if not isinstance(state_data["user"], int):
                return False
            
            # Check page bounds
            page = state_data.get("page", 0)
            if not isinstance(page, int) or page < 0:
                return False
            
            # Check sort_by is valid
            valid_sort_options = ["newest", "oldest", "tier", "artist", "serial"]
            if state_data.get("sort_by") not in valid_sort_options:
                return False
            
            # Check filters are valid
            if state_data.get("filters"):
                filters = state_data.get("filters", {})
                if not isinstance(filters, dict):
                    return False
                
                valid_filter_keys = ["tier", "genre", "payment_status"]
                for key in filters:
                    if key not in valid_filter_keys:
                        return False
                
            return True
            
        except Exception as e:
            print(f"❌ State validation failed: {e}")
            return False
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        """Enhanced interaction check with state validation"""
        try:
            # Load current state
            current_state = load_state(self.state_id)
            
            # Verify state exists and is valid
            if not current_state:
                print(f"❌ No state found for {self.state_id}")
                return False
            
            if not self._validate_state(current_state):
                print(f"❌ Invalid state for {self.state_id}")
                return False
            
            # Verify user ownership
            if current_state.get("user") != self.user_id:
                print(f"❌ User mismatch: expected {self.user_id}, got {current_state.get('user')}")
                return False
            
            # Verify state integrity
            if current_state.get("state_id") != self.state_id:
                print(f"❌ State ID mismatch: expected {self.state_id}, got {current_state.get('state_id')}")
                return False
            
            # Verify timestamp (optional but recommended)
            last_updated = current_state.get("last_updated", 0)
            current_time = int(time.time())
            if current_time - last_updated > 86400: 24 hours
                print(f"⚠️ State expired for user {self.user_id} (last updated: {last_updated})")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Interaction check error: {e}")
            return False
    
    def save_state(self):
        """Save current state to file"""
        try:
            state_data = {
                "user": self.user_id,
                "page": self.page,
                "selected_pack_id": self.selected_pack_id,
                "filters": self.filters,
                "sort_by": self.sort_by,
                "last_updated": int(time.time())
            }
            
            return save_state(self.state_id, state_data)
        except Exception as e:
            print(f"❌ Error saving state: {e}")
            return False
    
    def update_state(self, updates: Dict[str, Any]) -> bool:
        """Update state with new data"""
        try:
            current_state = load_state(self.state_id)
            if current_state:
                current_state.update(updates)
                return save_state(self.state_id, current_state)
            return True
        except Exception as e:
            print(f"❌ Error updating state: {e}")
            return False
    
    def cleanup_expired_state(self) -> bool:
        """Clean up expired state"""
        try:
            from ui.state import delete_state
            return delete_state(self.state_id)
        except Exception as e:
            print(f"❌ Error cleaning up expired state: {e}")
            return False
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current state"""
        try:
            current_state = load_state(self.state_id)
            return {
                "state_id": self.state_id,
                "user_id": self.user_id,
                "page": self.page,
                "selected_pack_id": self.selected_pack_id,
                "filters": self.filters,
                "sort_by": self.sort_by,
                "last_updated": current_state.get("last_updated", 0),
                "age_seconds": int(time.time()) - current_state.get("last_updated", 0)
            }
        except Exception as e:
            print(f"❌ Error getting state summary: {e}")
            return {}
    
    def __repr__(self) -> str:
        return f"DashboardView(user_id={self.user_id}, page={self.page}, state_id={self.state_id})"


class SafeCollectionView(View):
    """
    Collection View with enhanced safety checks
    Ensures only owners can interact with their collection
    """
    
    def __init__(self, user_id: int, page: int = 0):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.page = page
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        """Enhanced interaction check with state validation"""
        try:
            # Load current state if available
            collection_state_id = f"collection:{self.user_id}:{int(time.time())}"
            current_state = load_state(collection_state_id)
            
            # Verify user ownership
            if current_state and current_state.get("user") == self.user_id:
                # Update page if state exists
                if current_state.get("page") != self.page:
                    self.page = current_state["page"]
                    # Save updated state
                    from ui.state import update_state
                    update_state(collection_state_id, {"page": self.page})
                return True
            
            # Fallback to basic check if no state
            return interaction.user.id == self.user_id
            
        except Exception as e:
            print(f"❌ Interaction check error: {e}")
            return False
    
    def save_state(self):
        """Save current state to file"""
        try:
            state_data = {
                "user": self.user_id,
                "page": self.page,
                "last_updated": int(time.time())
            }
            
            collection_state_id = f"collection:{self.user_id}:{int(time.time())}"
            return save_state(collection_state_id, state_data)
        except Exception as e:
            print(f"❌ Error saving collection state: {e}")
            return False


class SafePackActionsView(View):
    """Actions for individual packs in dashboard"""
    
    def __init__(self, pack: CreatorPack, user_id: int, state_id: str):
        super().__init__(timeout=300)
        self.pack = pack
        self.user_id = user_id
        self.state_id = state_id
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        """Enhanced interaction check with state validation"""
        try:
            # Load current state if available
            current_state = load_state(self.state_id)
            
            # Verify state exists and is valid
            if not current_state:
                print(f"❌ No state found for {self.state_id}")
                return False
            
            if not self._validate_state(current_state):
                print(f"❌ Invalid state for {self.state_id}")
                return False
            
            # Verify user ownership
            if current_state.get("user") != self.user_id:
                print(f"❌ User mismatch: expected {self.user_id}, got {current_state.get('user')}")
                return False
            
            # Verify state integrity
            if current_state.get("state_id") != self.state_id:
                print(f"❌ State ID mismatch: expected {self.state_id}, got {current_state.get('state_id')}")
                return False
            
            # Verify timestamp (optional but recommended)
            last_updated = current_state.get("last_updated", 0)
            current_time = int(time.time())
            if current_time - last_updated > 86400: 24 hours
                print(f"⚠️ State expired for user {self.user_id} (last updated: {last_updated})")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Interaction check error: {e}")
            return False
    
    def _validate_state(self, state_data: Dict[str, Any]) -> bool:
        """Validate state data integrity"""
        try:
            # Check basic structure
            if not isinstance(state_data, dict):
                return False
            
            # Check required fields
            if "user" not in state_data:
                return False
            
            # Check data types
            if not isinstance(state_data["user"], int):
                return False
            
            # Check page bounds
            page = state_data.get("page", 0)
            if not isinstance(page, int) or page < 0:
                return False
            
            # Check sort_by is valid
            valid_sort_options = ["newest", "oldest", "tier", "artist", "serial"]
            if state_data.get("sort_by") not in valid_sort_options:
                return False
            
            # Check filters are valid
            if state_data.get("filters"):
                filters = state_data.get("filters", {})
                if not isinstance(filters, dict):
                    return False
                
                valid_filter_keys = ["tier", "genre", "payment_status"]
                for key in filters:
                    if key not in valid_filter_keys:
                        return False
                
            return True
            
        except Exception as e:
            print(f"❌ State validation failed: {e}")
            return False
    
    def save_state(self):
        """Save current state to file"""
        try:
            state_data = {
                "user": self.user_id,
                "page": self.page,
                "selected_pack_id": self.selected_pack_id,
                "filters": self.filters,
                "sort_by": self.sort_by,
                "last_updated": int(time.time())
            }
            
            return save_state(self.state_id, state_data)
        except Exception as e:
            print(f"❌ Error saving state: {e}")
            return False
    
    def update_state(self, updates: Dict[str, Any]) -> bool:
        """Update state with new data"""
        try:
            current_state = load_state(self.state_id)
            if current_state:
                current_state.update(updates)
                return save_state(self.state_id, current_state)
            return True
        except Exception as e:
            print(f"❌ Error updating state: {e}")
            return False
    
    def cleanup_expired_state(self) -> bool:
        """Clean up expired state"""
        try:
            from ui.state import delete_state
            return delete_state(self.state_id)
        except Exception as e:
            print(f"❌ Error cleaning up expired state: {e}")
            return False
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current state"""
        try:
            current_state = load_state(self.state_id)
            return {
                "state_id": self.state_id,
                "user_id": self.user_id,
                "page": self.page,
                "selected_pack_id": self.selected_pack_id,
                "filters": self.filters,
                "sort_by": self.sort_by,
                "last_updated": current_state.get("last_updated", 0),
                "age_seconds": int(time.time()) - current_state.get("last_updated", 0)
            }
        except Exception as e:
            print(f"❌ Error getting state summary: {e}")
            return {}
    
    def __repr__(self) -> str:
        return f"PackActionsView(user_id={self.user_id}, pack_id={self.pack.id}, state_id={self.state_id})"


class SafeCardActionsView(View):
    """Actions for individual cards in collection"""
    
    def __init__(self, card: Card, user_id: int):
        super().__init__(timeout=300)
        self.card = card
        self.user_id = user_id
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        """Enhanced interaction check with state validation"""
        try:
            # Load current state if available
            card_state_id = f"card:{self.user_id}:{self.card.id}:{int(time.time())}"
            current_state = load_state(card_state_id)
            
            # Verify user ownership
            if current_state and current_state.get("user") == self.user_id:
                # Update card info if state exists
                return True
            
            # Fallback to basic check if no state
            return interaction.user.id == self.user_id
            
        except Exception as e:
            print(f"❌ Interaction check error: {e}")
            return False
    
    def save_state(self):
        """Save current state to file"""
        try:
            state_data = {
                "user": self.user_id,
                "card_id": self.card.id,
                "last_updated": int(time.time())
            }
            
            card_state_id = f"card:{self.user_id}:{self.card.id}:{int(time.time())}"
            return save_state(card_state_id, state_data)
        except Exception as e:
            print(f"❌ Error saving card state: {e}")
            return False


class SafetyCheckService:
    """Service for comprehensive safety checks"""
    
    @staticmethod
    def safe_images(preview: Dict[str, Any]) -> tuple[bool, str]:
        """
        Check if all artists have appropriate images
        
        Args:
            preview: Preview data dictionary
            
        Returns:
            (is_safe, message) tuple
        """
        try:
            missing_images = []
            inappropriate_images = []
            
            for artist in preview.get("artists", []):
                # Check if image exists
                if not artist.get("image"):
                    missing_images.append(artist["name"])
                
                # Check for inappropriate image URLs
                image_url = artist.get("image", "")
                if image_url:
                    # Check for suspicious domains
                    suspicious_domains = ["nsfw", "adult", "xxx", "porn"]
                    if any(domain in image_url.lower() for domain in suspicious_domains):
                        inappropriate_images.append(artist["name"])
            
            if inappropriate_images:
                return False, f"Inappropriate images for: {', '.join(inappropriate_images)}"
            
            if missing_images:
                return False, f"Missing images for: {', '.join(missing_images)}"
            
            return True, "All images appropriate"
            
        except Exception as e:
            return False, f"Error checking images: {e}"


# Global safety check service instance
safety_checks = SafetyCheckService()


# Global state management functions
def cleanup_all_expired_states():
    """Clean up all expired states"""
    try:
        from ui.state import cleanup_old_states
        cleanup_old_states()
        print("🧹 Cleaned up all expired states")
    except Exception as e:
        print(f"❌ Error cleaning up expired states: {e}")


def get_all_user_states() -> Dict[int, Dict[str, Any]]:
    """Get all user states for debugging"""
    try:
        all_states = {}
        
        # Get all state files
        from ui.state import STATE_DIR
        for state_file in STATE_DIR.glob("*.json"):
            try:
                state_id = state_file.stem
                state_data = load_state(state_id)
                if state_data:
                    user_id = state_data.get("user")
                    if user_id:
                        if user_id not in all_states:
                            all_states[user_id] = {}
                        all_states[user_id][state_id] = state_data
            except:
                continue
        
        return all_states
        
    except Exception as e:
        print(f"❌ Error getting all user states: {e}")
        return {}


def validate_user_interaction(user_id: int, state_id: str) -> bool:
    """
    Validate that a user can interact with a component
    
    Args:
        user_id: Discord user ID
        state_id: State ID to validate
        
    Returns:
        True if user can interact, False otherwise
    """
    try:
        current_state = load_state(state_id)
        
        if not current_state:
            return False
        
        # Check user ownership
        return current_state.get("user") == user_id
        
    except Exception as e:
        print(f"❌ Error validating user interaction: {e}")
        return False


# Example usage
def example_usage():
    """Example of interaction safety usage"""
    
    print("🔒 Interaction Safety Examples:")
    print("=======================")
    
    # Example 1: Safe Dashboard View
    print("\n1. Safe Dashboard View")
    print("---------------------")
    
    dashboard = SafeDashboardView(123456789)
    print(f"✅ Created dashboard for user {dashboard.user_id}")
    print(f"   State ID: {dashboard.state_id}")
    print(f"   Current page: {dashboard.page}")
    
    # Example 2: Invalid Interaction
    print("\n2. Invalid Interaction")
    print("-------------------")
    
    # Mock interaction with wrong user
    class MockInteraction:
        user_id = 987654321  # Wrong user
        user_id = 123456789  # Correct user
    
    mock_interaction = MockInteraction()
    
    # This should fail
    result = dashboard.interaction_check(mock_interaction)
    print(f"✅ Invalid interaction result: {result}")
    
    # Example 3: State Validation
    print("\n3. State Validation")
    print("-------------------")
    
    # Create invalid state
    invalid_state = {
        "user": "not_an_int",
        "page": -1,
        "sort_by": "invalid_option"
    }
    
    # This should fail validation
    is_valid = dashboard._validate_state(invalid_state)
    print(f"✅ Invalid state validation: {is_valid}")
    
    # Example 4: State Persistence
    print("\n4. State Persistence")
    print("-------------------")
    
    # Modify dashboard
    dashboard.page = 2
    dashboard.selected_pack_id = "test_pack_123"
    
    # Save state
    success = dashboard.save_state()
    print(f"✅ State saved: {success}")
    
    # Load state
    dashboard.page = 0  # Reset page
    loaded_state = load_state(dashboard.state_id)
    
    if loaded_state:
        dashboard.page = loaded_state.get("page", 0)
        dashboard.selected_pack_id = loaded_state.get("selected_pack_id")
        print(f"✅ State loaded: page={dashboard.page}, pack_id={dashboard.selected_pack_id}")
    else:
        print("❌ Failed to load state")


if __name__ == "__main__":
    example_usage()
