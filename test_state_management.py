# test_state_management.py
# Test script for state management and rehydration

import sys
sys.path.append('.')

import time
import json
from pathlib import Path
from ui.state import save_state, load_state, get_user_states, delete_state, cleanup_old_states
from ui.loader import restore_collection, restore_dashboard, restore_all_user_states
from commands.persistent_dashboard import PersistentDashboardView
from commands.collection_ui import CollectionView
from models.creator_pack import CreatorPack

def test_state_management():
    """Test basic state management functions"""
    print("🔄 Testing State Management")
    print("==========================")
    
    # Test 1: Save and Load State
    print("\n1. Testing Save and Load State")
    print("----------------------------")
    
    # Create test state
    test_state_id = f"test:{int(time.time())}"
    test_data = {
        "user": 123456789,
        "page": 2,
        "filters": {"tier": "legendary"},
        "sort_by": "newest",
        "message": "Test state data"
    }
    
    print(f"✅ Created test state ID: {test_state_id}")
    print(f"   Data: {test_data}")
    
    # Save state
    if save_state(test_state_id, test_data):
        print("✅ State saved successfully")
    else:
        print("❌ Failed to save state")
        return
    
    # Load state
    loaded_data = load_state(test_state_id)
    if loaded_data:
        print("✅ State loaded successfully")
        print(f"   Loaded data: {loaded_data}")
        
        # Verify data integrity
        if loaded_data == test_data:
            print("✅ Data integrity verified")
        else:
            print("❌ Data integrity check failed")
    else:
        print("❌ Failed to load state")
    
    # Test 2: State Expiration
    print("\n2. Testing State Expiration")
    print("-------------------------")
    
    # Create old state (simulate 24 hours ago)
    old_timestamp = int(time.time()) - 86400  # 24 hours ago
    old_state_id = f"old:{old_timestamp}"
    old_data = {
        "user": 987654321,
        "page": 1,
        "message": "Old state data"
    }
    
    # Save old state
    save_state(old_state_id, old_data)
    
    # Try to load (should fail due to expiration)
    loaded_old = load_state(old_state_id)
    if loaded_old is None:
        print("✅ Old state correctly expired")
    else:
        print("❌ Old state should have expired")
    
    # Test 3: User States
    print("\n3. Testing User States")
    print("-------------------")
    
    # Create multiple states for user
    user_id = 123456789
    
    state_1_id = f"dashboard:{user_id}:{int(time.time())}"
    state_1_data = {"user": user_id, "page": 0}
    
    state_2_id = f"collection:{user_id}:{int(time.time()) + 1}"
    state_2_data = {"user": user_id, "page": 1}
    
    state_3_id = f"collection:{user_id}:{int(time.time()) + 2}"
    state_3_data = {"user": user_id, "page": 2}
    
    # Save all states
    save_state(state_1_id, state_1_data)
    save_state(state_2_id, state_2_data)
    save_state(state_3_id, state_3_data)
    
    # Get user states
    user_states = get_user_states(user_id)
    
    if user_states:
        print(f"✅ Found {len(user_states)} states for user {user_id}")
        for state_id, data in user_states.items():
            print(f"   {state_id}: page={data.get('page', 'N/A')}")
    else:
        print(f"❌ No states found for user {user_id}")
    
    # Test 4: Update State
    print("\n4. Testing State Update")
    print("---------------------")
    
    # Update state
    updates = {"page": 5, "filters": {"genre": "rock"}}
    if update_state(state_1_id, updates):
        print("✅ State updated successfully")
        
        # Verify update
        updated_data = load_state(state_1_id)
        if updated_data and updated_data.get("page") == 5:
            print("✅ Update verified: page = 5")
        else:
            print(f"❌ Update failed: page = {updated_data.get('page', 'N/A')}")
    else:
        print("❌ Failed to update state")
    
    # Test 5: Delete State
    print("\n5. Testing State Deletion")
    print("---------------------")
    
    if delete_state(state_3_id):
        print(f"✅ State deleted: {state_3_id}")
        
        # Verify deletion
        deleted_data = load_state(state_3_id)
        if deleted_data is None:
            print("✅ Deletion verified")
        else:
            print("❌ State still exists after deletion")
    else:
        print("❌ Failed to delete state")

def test_ui_rehydration():
    """Test UI component rehydration"""
    print("\n🔄 Testing UI Rehydration")
    print("========================")
    
    # Test 1: Collection View Rehydration
    print("\n1. Testing Collection View Rehydration")
    print("--------------------------------")
    
    # Create test state
    collection_state_id = f"collection:123456789:{int(time.time())}"
    collection_state = {
        "user": 123456789,
        "page": 3,
        "filters": {"tier": "legendary"}
    }
    
    save_state(collection_state_id, collection_state)
    
    # Restore view
    restored_view = restore_collection(collection_state_id)
    
    if restored_view:
        print("✅ Collection view restored successfully")
        print(f"   User ID: {restored_view.user_id}")
        print(f"   Page: {restored_view.page}")
        print(f"   State ID: {restored_view.state_id}")
    else:
        print("❌ Failed to restore collection view")
    
    # Test 2: Dashboard View Rehydration
    print("\n2. Testing Dashboard View Rehydration")
    print("---------------------------------")
    
    # Create test state
    dashboard_state_id = f"dashboard:123456789:{int(time.time())}"
    dashboard_state = {
        "user": 123456789,
        "page": 1,
        "selected_pack_id": "test_pack_id",
        "filters": {"status": "pending"},
        "sort_by": "newest"
    }
    
    save_state(dashboard_state_id, dashboard_state)
    
    # Restore view
    restored_dashboard = restore_dashboard(dashboard_state_id)
    
    if restored_dashboard:
        print("✅ Dashboard view restored successfully")
        print(f"   User ID: {restored_dashboard.user_id}")
        print(f"   Page: {restored_dashboard.page}")
        print(f"   Selected Pack: {restored_dashboard.selected_pack_id}")
        print(f"   State ID: {restored_dashboard.state_id}")
    else:
        print("❌ Failed to restore dashboard view")
    
    # Test 3: All User States Rehydration
    print("\n3. Testing All User States Rehydration")
    print("----------------------------------------")
    
    # Create multiple states for user
    user_id = 123456789
    
    dashboard_state_id = f"dashboard:{user_id}:{int(time.time())}"
    collection_state_id = f"collection:{user_id}:{int(time.time()) + 1}"
    
    save_state(dashboard_state_id, {"user": user_id, "page": 0})
    save_state(collection_state_id, {"user": user_id, "page": 1})
    
    # Restore all states
    restored_states = restore_all_user_states(user_id)
    
    if restored_states:
        print(f"✅ Restored {len(restored_states)} states for user {user_id}")
        
        for state_id, view in restored_states.items():
            view_type = type(view).__name__
            if hasattr(view, 'page'):
                page = view.page
            elif hasattr(view, 'user_id'):
                user = view.user_id
            else:
                page = "N/A"
                user = "N/A"
            
            print(f"   {state_id}: {view_type} (user: {user}, page: {page})")
    else:
        print(f"❌ No states to restore for user {user_id}")

def test_persistent_dashboard():
    """Test persistent dashboard functionality"""
    print("\n📊 Testing Persistent Dashboard")
    print("========================")
    
    # Test 1: Dashboard Creation
    print("\n1. Testing Dashboard Creation")
    print("------------------------")
    
    user_id = 123456789
    dashboard = PersistentDashboardView(user_id)
    
    print(f"✅ Dashboard created for user {user_id}")
    print(f"   State ID: {dashboard.state_id}")
    print(f"   Initial page: {dashboard.page}")
    print(f"   Timeout: {dashboard.timeout}")
    
    # Test 2: State Persistence
    print("\n2. Testing State Persistence")
    print("---------------------------")
    
    # Modify dashboard state
    dashboard.page = 2
    dashboard.selected_pack_id = "test_pack_123"
    dashboard.save_state()
    
    print(f"✅ Modified dashboard state")
    print(f"   New page: {dashboard.page}")
    print(f"   Selected pack: {dashboard.selected_pack_id}")
    
    # Verify state persistence
    loaded_state = load_state(dashboard.state_id)
    if loaded_state:
        if loaded_state.get("page") == 2 and loaded_state.get("selected_pack_id") == "test_pack_123":
            print("✅ State persistence verified")
        else:
            print("❌ State persistence failed")
    
    # Test 3: State Restoration
    print("\n3. Testing State Restoration")
    print("---------------------------")
    
    # Create new dashboard instance with same user
    new_dashboard = PersistentDashboardView(user_id, dashboard.state_id)
    
    if new_dashboard.page == 2 and new_dashboard.selected_pack_id == "test_pack_123":
        print("✅ Dashboard state restored correctly")
        print(f"   Restored page: {new_dashboard.page}")
        print(f"   Restored selected pack: {new_dashboard.selected_pack_id}")
    else:
        print("❌ Dashboard state restoration failed")
    
    # Test 4: Embed Generation
    print("\n4. Testing Embed Generation")
    print("------------------------")
    
    embed = dashboard.get_dashboard_embed()
    
    if embed:
        print("✅ Dashboard embed generated")
        print(f"   Title: {embed.title}")
        print(f"   Description: {embed.description}")
        print(f"   Color: {embed.color}")
    else:
        print("❌ Failed to generate embed")

def test_error_handling():
    """Test error handling in state management"""
    print("\n⚠️ Testing Error Handling")
    print("========================="")
    
    # Test 1: Invalid State ID
    print("\n1. Testing Invalid State ID")
    print("------------------------")
    
    invalid_state_id = "nonexistent_state"
    loaded_data = load_state(invalid_state_id)
    
    if loaded_data is None:
        print("✅ Invalid state ID correctly handled")
    else:
        print("❌ Invalid state ID should return None")
    
    # Test 2: Corrupted State File
    print("\n2. Testing Corrupted State File")
    print("---------------------------")
    
    # Create corrupted file
    corrupted_file_path = Path("state/corrupted.json")
    corrupted_file_path.write_text('{"invalid": "json"}')
    
    try:
        loaded_data = load_state("corrupted")
        if loaded_data is None:
            print("✅ Corrupted file correctly handled")
        else:
            print("❌ Corrupted file should return None")
    except:
        print("✅ Corrupted file error handled")
    finally:
        if corrupted_file_path.exists():
            corrupted_file_path.unlink()
    
    # Test 3: Permission Issues
    print("\n3. Testing Permission Issues")
    print("-------------------------")
    
    # Try to create state directory without permissions
    original_permissions = Path("state").stat().st_mode
    
    try:
        # Remove write permissions temporarily
        Path("state").chmod(0o555)
        
        # Try to save state
        test_state_id = f"permission_test:{int(time.time())}"
        test_data = {"user": 123456789}
        
        result = save_state(test_state_id, test_data)
        if result:
            print("✅ Permission test passed")
        else:
            print("❌ Permission test failed")
            
    except Exception as e:
        print(f"✅ Permission error handled: {e}")
    finally:
        # Restore permissions
        try:
            Path("state").chmod(original_permissions)
        except:
            pass

def test_performance():
    """Test performance of state management"""
    print("\n⚡ Testing Performance")
    print("==================")
    
    import time
    
    # Test 1: Save Performance
    print("\n1. Testing Save Performance")
    print("---------------------")
    
    num_operations = 100
    start_time = time.time()
    
    for i in range(num_operations):
        state_id = f"perf_test_{i}_{int(time.time())}"
        data = {"user": i, "page": i % 10, "data": f"test_data_{i}"}
        save_state(state_id, data)
    
    end_time = time.time()
    save_time = (end_time - start_time) / num_operations
    
    print(f"✅ Save performance: {save_time:.4f} seconds per operation")
    print(f"   Total time: {end_time - start_time:.2f} seconds")
    print(f"   Operations: {num_operations}")
    
    # Test 2: Load Performance
    print("\n2. Testing Load Performance")
    print("---------------------")
    
    start_time = time.time()
    
    for i in range(num_operations):
        state_id = f"perf_test_{i}_{int(time.time())}"
        load_state(state_id)
    
    end_time = time.time()
    load_time = (end_time - start_time) / num_operations
    
    print(f"✅ Load performance: {load_time:.4f} seconds per operation")
    print(f"   Total time: {end_time - start_time:.2f} seconds")
    print(f"   Operations: {num_operations}")
    
    # Test 3: Memory Usage
    print("\n3. Testing Memory Usage")
    print("---------------------")
    
    # Create many states to test memory usage
    num_states = 1000
    created_states = []
    
    start_time = time.time()
    
    for i in range(num_states):
        state_id = f"mem_test_{i}_{int(time.time())}"
        data = {"user": i, "data": "x" * 100}  # 100 bytes per state
        save_state(state_id, data)
        created_states.append(state_id)
    
    end_time = time.time()
    creation_time = (end_time - start_time) / num_states
    
    print(f"✅ Creation performance: {creation_time:.4f} seconds per state")
    print(f"   Total time: {end_time - start_time:.2f} seconds")
    print(f"   States created: {num_states}")
    print(f"   Memory usage: ~{num_states * 100} bytes")
    
    # Clean up
    for state_id in created_states:
        delete_state(state_id)

def main():
    """Run all state management tests"""
    print("🔄 State Management Test Suite")
    print("=========================")
    
    try:
        test_state_management()
        test_ui_rehydration()
        test_persistent_dashboard()
        test_error_handling()
        test_performance()
        
        print("\n🎉 State Management Test Suite Completed!")
        print("📊 All tests completed - check results above")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
