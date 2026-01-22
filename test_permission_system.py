"""
Permission System Test Suite

Comprehensive tests for the role-based permission system.
Tests role configuration, decorators, UI security, and audit logging.
"""

import unittest
from unittest.mock import Mock, AsyncMock, patch
import discord
from datetime import datetime, timedelta

# Import the modules we're testing
from config.roles import (
    ROLES, ROLE_HIERARCHY, PERMISSIONS, COMMAND_ROLES,
    get_role_permissions, has_permission, can_access_command,
    is_admin, is_moderator, is_creator, UserRole
)
from middleware.permissions import (
    require_role, require_permission, require_any_role,
    admin_only, moderator_only, creator_only,
    check_user_permissions, PermissionChecker
)
from ui.secure_views import (
    SecureView, PersistentSecureView, SecureButton, 
    SecureSelect, SecureModal, secure_button, secure_select
)
from services.role_service import RoleService
from services.audit_service import AuditLog

class TestRoleConfiguration(unittest.TestCase):
    """Test role configuration and permission mappings."""
    
    def test_roles_defined(self):
        """Test that all required roles are defined."""
        self.assertIn("player", ROLES)
        self.assertIn("creator", ROLES)
        self.assertIn("moderator", ROLES)
        self.assertIn("admin", ROLES)
    
    def test_role_hierarchy(self):
        """Test role hierarchy is correct."""
        self.assertEqual(ROLE_HIERARCHY["player"], 0)
        self.assertEqual(ROLE_HIERARCHY["creator"], 1)
        self.assertEqual(ROLE_HIERARCHY["moderator"], 2)
        self.assertEqual(ROLE_HIERARCHY["admin"], 3)
    
    def test_permissions_structure(self):
        """Test that permissions are properly structured."""
        for role_name in ROLES.values():
            self.assertIn(role_name.lower(), PERMISSIONS)
            self.assertIsInstance(PERCMISSIONS[role_name.lower()], list)
    
    def test_permission_inheritance(self):
        """Test that higher roles have all lower role permissions."""
        player_perms = set(PERMISSIONS["player"])
        creator_perms = set(PERMISSIONS["creator"])
        moderator_perms = set(PERMISSIONS["moderator"])
        admin_perms = set(PERMISSIONS["admin"])
        
        # Each role should have all permissions of roles below it
        self.assertTrue(player_perms.issubset(creator_perms))
        self.assertTrue(creator_perms.issubset(moderator_perms))
        self.assertTrue(moderator_perms.issubset(admin_perms))
    
    def test_command_role_mappings(self):
        """Test that commands are properly mapped to roles."""
        # Creator commands
        self.assertEqual(COMMAND_ROLES["creator"], "creator")
        self.assertEqual(COMMAND_ROLES["submit_pack"], "creator")
        
        # Moderator commands
        self.assertEqual(COMMAND_ROLES["review"], "moderator")
        self.assertEqual(COMMAND_ROLES["approve"], "moderator")
        
        # Admin commands
        self.assertEqual(COMMAND_ROLES["refund"], "admin")
        self.assertEqual(COMMAND_ROLES["ban"], "admin")
        
        # Player commands (default)
        self.assertEqual(COMMAND_ROLES["packs"], "player")
        self.assertEqual(COMMAND_ROLES["collection"], "player")
    
    def test_permission_helper_functions(self):
        """Test permission utility functions."""
        # Test has_permission
        self.assertTrue(has_permission("admin", "ban_user"))
        self.assertTrue(has_permission("moderator", "review_pack"))
        self.assertFalse(has_permission("player", "ban_user"))
        self.assertFalse(has_permission("creator", "ban_user"))
        
        # Test can_access_command
        self.assertTrue(can_access_command("admin", "refund"))
        self.assertTrue(can_access_command("moderator", "review"))
        self.assertFalse(can_access_command("player", "refund"))
        
        # Test role checking functions
        self.assertTrue(is_admin("admin"))
        self.assertTrue(is_moderator("admin"))
        self.assertTrue(is_creator("admin"))
        self.assertFalse(is_admin("moderator"))
        self.assertTrue(is_moderator("moderator"))
        self.assertFalse(is_creator("moderator"))
        self.assertFalse(is_admin("creator"))
        self.assertFalse(is_moderator("creator"))
        self.assertTrue(is_creator("creator"))

class TestPermissionDecorators(unittest.TestCase):
    """Test permission decorators and middleware."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_ctx = Mock()
        self.mock_ctx.author = Mock()
        self.mock_ctx.author.roles = []
        self.mock_ctx.author.id = 12345
        self.mock_ctx.command = Mock()
        self.mock_ctx.command.name = "test_command"
        self.mock_ctx.respond = AsyncMock()
        self.mock_ctx.guild = Mock()
        self.mock_ctx.guild.id = 67890
    
    @patch('middleware.permissions.AuditLog')
    def test_require_role_success(self, mock_audit):
        """Test require_role decorator with correct role."""
        # Add required role to user
        creator_role = Mock()
        creator_role.name = ROLES["creator"]
        self.mock_ctx.author.roles = [creator_role]
        
        # Create a test function with the decorator
        @require_role("creator")
        async def test_func(ctx):
            return "success"
        
        # Run the test
        import asyncio
        result = asyncio.run(test_func(self.mock_ctx))
        
        # Verify success
        self.assertEqual(result, "success")
        self.mock_ctx.respond.assert_not_called()
        mock_audit.record.assert_called()
    
    @patch('middleware.permissions.AuditLog')
    def test_require_role_failure(self, mock_audit):
        """Test require_role decorator without correct role."""
        # User has no roles
        self.mock_ctx.author.roles = []
        
        # Create a test function with the decorator
        @require_role("creator")
        async def test_func(ctx):
            return "success"
        
        # Run the test
        import asyncio
        result = asyncio.run(test_func(self.mock_ctx))
        
        # Verify failure
        self.assertIsNone(result)
        self.mock_ctx.respond.assert_called_once()
        mock_audit.record.assert_called()
    
    @patch('middleware.permissions.AuditLog')
    def test_require_permission_success(self, mock_audit):
        """Test require_permission decorator with correct permission."""
        # Add admin role to user (has all permissions)
        admin_role = Mock()
        admin_role.name = ROLES["admin"]
        self.mock_ctx.author.roles = [admin_role]
        
        # Create a test function with the decorator
        @require_permission("ban_user")
        async def test_func(ctx):
            return "success"
        
        # Run the test
        import asyncio
        result = asyncio.run(test_func(self.mock_ctx))
        
        # Verify success
        self.assertEqual(result, "success")
        self.mock_ctx.respond.assert_not_called()
        mock_audit.record.assert_called()
    
    @patch('middleware.permissions.AuditLog')
    def test_require_any_role_success(self, mock_audit):
        """Test require_any_role decorator with one matching role."""
        # Add creator role (one of the required roles)
        creator_role = Mock()
        creator_role.name = ROLES["creator"]
        self.mock_ctx.author.roles = [creator_role]
        
        # Create a test function with the decorator
        @require_any_role(["creator", "moderator"])
        async def test_func(ctx):
            return "success"
        
        # Run the test
        import asyncio
        result = asyncio.run(test_func(self.mock_ctx))
        
        # Verify success
        self.assertEqual(result, "success")
        self.mock_ctx.respond.assert_not_called()
        mock_audit.record.assert_called()
    
    @patch('middleware.permissions.AuditLog')
    def test_shortcut_decorators(self, mock_audit):
        """Test shortcut decorators (admin_only, moderator_only, creator_only)."""
        # Test admin_only
        admin_role = Mock()
        admin_role.name = ROLES["admin"]
        self.mock_ctx.author.roles = [admin_role]
        
        @admin_only
        async def admin_func(ctx):
            return "admin_success"
        
        import asyncio
        result = asyncio.run(admin_func(self.mock_ctx))
        self.assertEqual(result, "admin_success")
        
        # Test moderator_only
        moderator_role = Mock()
        moderator_role.name = ROLES["moderator"]
        self.mock_ctx.author.roles = [moderator_role]
        
        @moderator_only
        async def mod_func(ctx):
            return "mod_success"
        
        result = asyncio.run(mod_func(self.mock_ctx))
        self.assertEqual(result, "mod_success")
        
        # Test creator_only
        creator_role = Mock()
        creator_role.name = ROLES["creator"]
        self.mock_ctx.author.roles = [creator_role]
        
        @creator_only
        async def creator_func(ctx):
            return "creator_success"
        
        result = asyncio.run(creator_func(self.mock_ctx))
        self.assertEqual(result, "creator_success")

class TestSecureViews(unittest.TestCase):
    """Test secure UI view classes."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.owner_id = 12345
        self.other_user_id = 67890
        
        self.mock_interaction = Mock()
        self.mock_interaction.user = Mock()
        self.mock_interaction.user.id = self.owner_id
        self.mock_interaction.response = AsyncMock()
        self.mock_interaction.channel = Mock()
        self.mock_interaction.channel.id = 11111
        self.mock_interaction.message = Mock()
        self.mock_interaction.message.id = 22222
    
    @patch('ui.secure_views.AuditLog')
    def test_secure_view_owner_access(self, mock_audit):
        """Test SecureView allows owner to interact."""
        view = SecureView(self.owner_id)
        
        # Test owner access
        result = view.interaction_check(self.mock_interaction)
        self.assertTrue(result)
        self.mock_interaction.response.assert_not_called()
        mock_audit.record.assert_not_called()
    
    @patch('ui.secure_views.AuditLog')
    def test_secure_view_unauthorized_access(self, mock_audit):
        """Test SecureView denies unauthorized user."""
        view = SecureView(self.owner_id)
        
        # Test unauthorized access
        self.mock_interaction.user.id = self.other_user_id
        result = view.interaction_check(self.mock_interaction)
        
        self.assertFalse(result)
        self.mock_interaction.response.assert_called_once()
        mock_audit.record.assert_called_once()
    
    @patch('ui.secure_views.AuditLog')
    @patch('ui.secure_views.load_state')
    def test_persistent_secure_view_success(self, mock_load_state, mock_audit):
        """Test PersistentSecureView with valid state."""
        # Mock state data
        mock_load_state.return_value = {
            "user": self.owner_id,
            "page": 1,
            "data": "test"
        }
        
        view = PersistentSecureView(self.owner_id, "test_state_id")
        
        # Test owner access
        result = view.interaction_check(self.mock_interaction)
        self.assertTrue(result)
        mock_load_state.assert_called_once_with("test_state_id")
    
    @patch('ui.secure_views.AuditLog')
    @patch('ui.secure_views.load_state')
    def test_persistent_secure_view_state_mismatch(self, mock_load_state, mock_audit):
        """Test PersistentSecureView with state user mismatch."""
        # Mock state data with different user
        mock_load_state.return_value = {
            "user": self.other_user_id,
            "page": 1,
            "data": "test"
        }
        
        view = PersistentSecureView(self.owner_id, "test_state_id")
        
        # Test unauthorized access
        result = view.interaction_check(self.mock_interaction)
        
        self.assertFalse(result)
        self.mock_interaction.response.assert_called_once()
        mock_audit.record.assert_called_once()
    
    @patch('ui.secure_views.AuditLog')
    def test_secure_button_owner_access(self, mock_audit):
        """Test SecureButton allows owner to interact."""
        button = SecureButton(self.owner_id, label="Test")
        
        # Mock the actual callback
        button._actual_callback = AsyncMock(return_value="callback_result")
        
        # Test owner access
        import asyncio
        result = asyncio.run(button.callback(self.mock_interaction))
        
        self.assertEqual(result, "callback_result")
        self.mock_interaction.response.assert_not_called()
        mock_audit.record.assert_not_called()
    
    @patch('ui.secure_views.AuditLog')
    def test_secure_button_unauthorized_access(self, mock_audit):
        """Test SecureButton denies unauthorized user."""
        button = SecureButton(self.owner_id, label="Test")
        
        # Test unauthorized access
        self.mock_interaction.user.id = self.other_user_id
        
        import asyncio
        result = asyncio.run(button.callback(self.mock_interaction))
        
        self.assertIsNone(result)
        self.mock_interaction.response.assert_called_once()
        mock_audit.record.assert_called_once()

class TestRoleService(unittest.TestCase):
    """Test RoleService functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_bot = Mock()
        self.mock_guild = Mock()
        self.mock_member = Mock()
        self.mock_member.id = 12345
        self.mock_member.guild = self.mock_guild
        
        self.role_service = RoleService(self.mock_bot)
    
    @patch('services.role_service.AuditLog')
    async def test_ensure_roles_exist(self, mock_audit):
        """Test role creation functionality."""
        # Mock guild with no existing roles
        self.mock_guild.roles = [Mock(name="@everyone")]
        self.mock_guild.create_role = AsyncMock()
        
        results = await self.role_service.ensure_roles_exist(self.mock_guild)
        
        # Should attempt to create all roles
        self.assertEqual(len(self.mock_guild.create_role.call_args_list), 4)
        self.assertIn("created", results)
        self.assertIn("existing", results)
        self.assertIn("errors", results)
    
    @patch('services.role_service.AuditLog')
    async def test_grant_role_success(self, mock_audit):
        """Test successful role granting."""
        # Mock role exists
        mock_role = Mock()
        self.mock_guild.roles = [mock_role]
        discord.utils.get = Mock(return_value=mock_role)
        
        # Mock member doesn't have role
        self.mock_member.roles = []
        self.mock_member.add_roles = AsyncMock()
        
        result = await self.role_service.grant_role(self.mock_member, "Creator")
        
        self.assertTrue(result)
        self.mock_member.add_roles.assert_called_once()
        mock_audit.record.assert_called_once()
    
    @patch('services.role_service.AuditLog')
    async def test_grant_role_already_has(self, mock_audit):
        """Test granting role user already has."""
        # Mock role exists and user has it
        mock_role = Mock()
        self.mock_guild.roles = [mock_role]
        discord.utils.get = Mock(return_value=mock_role)
        self.mock_member.roles = [mock_role]
        
        result = await self.role_service.grant_role(self.mock_member, "Creator")
        
        self.assertTrue(result)
        self.mock_member.add_roles.assert_not_called()
    
    @patch('services.role_service.AuditLog')
    async def test_revoke_role_success(self, mock_audit):
        """Test successful role revocation."""
        # Mock role exists and user has it
        mock_role = Mock()
        self.mock_guild.roles = [mock_role]
        discord.utils.get = Mock(return_value=mock_role)
        self.mock_member.roles = [mock_role]
        self.mock_member.remove_roles = AsyncMock()
        
        result = await self.role_service.revoke_role(self.mock_member, "Creator")
        
        self.assertTrue(result)
        self.mock_member.remove_roles.assert_called_once()
        mock_audit.record.assert_called_once()

class TestAuditService(unittest.TestCase):
    """Test audit logging functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary audit log for testing
        self.audit_log = AuditLog("test_audit")
    
    def test_record_event(self):
        """Test recording an audit event."""
        # Mock file operations
        with patch('builtins.open', create=True) as mock_open:
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            # Record an event
            AuditLog.record(
                event="test_event",
                user_id=12345,
                target_id=67890,
                details={"key": "value"}
            )
            
            # Verify file was written to
            mock_file.write.assert_called_once()
    
    def test_get_events_filtering(self):
        """Test event retrieval with filters."""
        # Mock log file reading
        mock_events = [
            {"timestamp": "2023-01-01T12:00:00", "event": "test_event", "user_id": 12345},
            {"timestamp": "2023-01-01T13:00:00", "event": "other_event", "user_id": 67890},
        ]
        
        with patch.object(self.audit_log, '_read_log_file', return_value=mock_events):
            # Test event type filtering
            events = self.audit_log.get_events(event_type="test_event")
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["event"], "test_event")
            
            # Test user filtering
            events = self.audit_log.get_events(user_id=12345)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["user_id"], 12345)
    
    def test_statistics(self):
        """Test audit statistics generation."""
        # Mock event data
        mock_events = [
            {"timestamp": "2023-01-01T12:00:00", "event": "permission_denied", "user_id": 12345},
            {"timestamp": "2023-01-01T13:00:00", "event": "permission_denied", "user_id": 67890},
            {"timestamp": "2023-01-01T14:00:00", "event": "role_granted", "user_id": 12345},
        ]
        
        with patch.object(self.audit_log, 'get_events', return_value=mock_events):
            stats = self.audit_log.get_statistics(days=7)
            
            self.assertEqual(stats["total_events"], 3)
            self.assertEqual(stats["unique_users"], 2)
            self.assertIn("permission_denied", stats["event_counts"])
            self.assertEqual(stats["event_counts"]["permission_denied"], 2)

class TestIntegration(unittest.TestCase):
    """Integration tests for the complete permission system."""
    
    @patch('services.audit_service.AuditLog')
    def test_permission_flow(self, mock_audit):
        """Test complete permission flow from command to audit."""
        # This would test the full flow:
        # 1. User attempts command
        # 2. Decorator checks permissions
        # 3. Command executes or is denied
        # 4. Event is logged to audit
        
        # Mock context with admin role
        mock_ctx = Mock()
        mock_ctx.author = Mock()
        mock_ctx.author.id = 12345
        admin_role = Mock()
        admin_role.name = ROLES["admin"]
        mock_ctx.author.roles = [admin_role]
        mock_ctx.respond = AsyncMock()
        mock_ctx.command = Mock()
        mock_ctx.command.name = "admin_command"
        
        # Create admin-only command
        @admin_only
        async def admin_command(ctx):
            return "admin_success"
        
        # Execute command
        import asyncio
        result = asyncio.run(admin_command(mock_ctx))
        
        # Verify success and audit logging
        self.assertEqual(result, "admin_success")
        mock_audit.record.assert_called()

if __name__ == '__main__':
    unittest.main()
