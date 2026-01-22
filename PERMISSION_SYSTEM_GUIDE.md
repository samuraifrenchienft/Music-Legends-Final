# Permission System Implementation Guide

## Overview

This guide documents the comprehensive role-based permission system implemented for your Discord bot. The system provides secure access control, UI interaction safety, and complete audit logging.

## 🏗️ System Architecture

### 1. Role Configuration (`config/roles.py`)

**Role Hierarchy:**
- **Player** (Level 0) - Basic users: open packs, trade, collect
- **Creator** (Level 1) - Can submit creator packs
- **Moderator** (Level 2) - Can review packs, manage content
- **Admin** (Level 3) - Full control: refunds, bans, economy

**Key Features:**
- Permission inheritance (higher roles get all lower role permissions)
- Command-to-role mapping
- Utility functions for permission checking

### 2. Permission Middleware (`middleware/permissions.py`)

**Decorators:**
```python
@require_role("creator")        # Requires specific Discord role
@require_permission("submit_pack")  # Requires specific permission
@require_any_role(["moderator", "admin"])  # Any of multiple roles
@admin_only                    # Admin-only shortcut
@moderator_only               # Moderator-only shortcut
@creator_only                 # Creator-only shortcut
```

**Features:**
- Automatic audit logging for all permission checks
- Ephemeral error messages for denied access
- Integration with Discord role system

### 3. Secure UI Views (`ui/secure_views.py`)

**Base Classes:**
- `SecureView` - Basic owner-only interaction
- `PersistentSecureView` - Enhanced with state verification
- `SecureButton`, `SecureSelect`, `SecureModal` - Secure UI components

**Security Features:**
- Owner-only interaction enforcement
- Automatic audit logging for unauthorized attempts
- Integration with persistent state management

### 4. Role Management Service (`services/role_service.py`)

**Capabilities:**
- Automatic role creation with proper permissions
- Role granting/revoking with audit logging
- Role statistics and cleanup
- Bulk role operations

### 5. Audit Service (`services/audit_service.py`)

**Logging Features:**
- Comprehensive event logging
- Daily log rotation
- Advanced filtering and search
- Statistics and reporting
- Export functionality

## 🚀 Quick Start

### 1. Set Up Roles

```python
# In your bot's on_ready event
from services.role_service import RoleService

@bot.event
async def on_ready():
    role_service = RoleService(bot)
    for guild in bot.guilds:
        await role_service.ensure_roles_exist(guild)
```

### 2. Apply to Commands

```python
from middleware.permissions import require_role, admin_only

@bot.slash_command(name="creator")
@require_role("creator")
async def creator_command(ctx):
    await ctx.respond("Creator-only content!")

@bot.slash_command(name="admin_panel")
@admin_only
async def admin_command(ctx):
    await ctx.respond("Admin panel!")
```

### 3. Secure UI Components

```python
from ui.secure_views import SecureView

class MySecureView(SecureView):
    def __init__(self, owner_id):
        super().__init__(owner_id, timeout=None)  # Never expires
    
    @discord.ui.button(label="Secret Button")
    async def secret_button(self, interaction, button):
        await interaction.response.send_message("Only you can see this!", ephemeral=True)

# Usage
view = MySecureView(ctx.author.id)
await ctx.respond("Secure UI", view=view)
```

## 📋 Command Examples

### Creator Commands
```python
@bot.slash_command(name="submit_pack")
@require_role("creator")
async def submit_pack(ctx, name: str, artists: str):
    # Creator pack submission logic
    pass
```

### Moderator Commands
```python
@bot.slash_command(name="review")
@require_role("moderator")
async def review_pack(ctx, pack_id: str):
    # Pack review logic
    pass
```

### Admin Commands
```python
@bot.slash_command(name="refund")
@admin_only
async def refund_payment(ctx, payment_id: str):
    # Refund logic
    pass
```

## 🔐 Security Features

### 1. UI Interaction Safety

**Problem:** Users could press other users' buttons
**Solution:** `SecureView` with `interaction_check` guard

```python
async def interaction_check(self, interaction):
    if interaction.user.id != self.owner_id:
        # Log unauthorized attempt
        AuditLog.record("unauthorized_ui_interaction", ...)
        await interaction.response.send_message("🚫 Access denied", ephemeral=True)
        return False
    return True
```

### 2. Permission Enforcement

**Problem:** Users could access commands beyond their role
**Solution:** Decorator-based permission checking

```python
@require_role("admin")
async def admin_command(ctx):
    # Only executes if user has "Admin" Discord role
```

### 3. Audit Trail

**Problem:** No visibility into security events
**Solution:** Comprehensive audit logging

```python
# Automatically logged:
# - Permission denials
# - Role changes
# - Unauthorized UI interactions
# - Command usage
```

## 📊 Audit & Monitoring

### View Audit Logs

```python
from services.audit_service import AuditLog

# Get recent permission denials
events = AuditLog.get_events(event_type="permission_denied", limit=50)

# Get user activity
events = AuditLog.get_events(user_id=12345, days=7)

# Get statistics
stats = AuditLog.get_statistics(days=30)
```

### Role Statistics

```python
from services.role_service import RoleService

role_service = RoleService(bot)
stats = await role_service.get_role_statistics(guild)

# Output:
# {
#     "admin": {"count": 2, "percentage": 1.2},
#     "moderator": {"count": 5, "percentage": 3.1},
#     "creator": {"count": 23, "percentage": 14.2},
#     "player": {"count": 132, "percentage": 81.5}
# }
```

## 🛠️ Role Management Commands

### `/myroles` - Check Your Roles
Shows your current roles and permissions.

### `/checkroles @user` - Check User Roles
(Moderator+) Check another user's roles and permissions.

### `/manageroles @user` - Manage User Roles
(Admin) Open role management interface for granting/revoking roles.

### `/rolestats` - Role Statistics
(Moderator+) Show server role distribution.

### `/setuproles` - Setup Roles
(Admin) Create all required roles with proper permissions.

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_permission_system.py
```

**Test Coverage:**
- Role configuration and hierarchy
- Permission decorators
- Secure UI views
- Role service operations
- Audit logging functionality
- Integration scenarios

## 📁 File Structure

```
├── config/
│   └── roles.py                 # Role configuration and permissions
├── middleware/
│   └── permissions.py          # Permission decorators and middleware
├── ui/
│   └── secure_views.py          # Secure UI component base classes
├── services/
│   ├── role_service.py          # Role management service
│   └── audit_service.py         # Audit logging service
├── commands/
│   └── role_commands.py         # Role management commands
└── test_permission_system.py    # Comprehensive test suite
```

## 🔧 Configuration

### Environment Variables

```env
# Discord Bot Configuration
DISCORD_BOT_TOKEN=your_bot_token
GUILD_ID=your_server_id

# Audit Configuration
AUDIT_LOG_DIR=logs/audit
AUDIT_RETENTION_DAYS=30
```

### Role Customization

Edit `config/roles.py` to customize:
- Role names and hierarchy
- Permission sets
- Command mappings
- Role colors and permissions

## 🚨 Security Best Practices

### 1. Principle of Least Privilege
- Users get minimum permissions needed
- Role inheritance prevents permission gaps
- Regular audits of role assignments

### 2. Audit Monitoring
- Monitor permission denial patterns
- Review role changes regularly
- Set up alerts for suspicious activity

### 3. UI Security
- Always use `SecureView` for user-specific UI
- Implement timeout=None for persistent UI
- Log all unauthorized interaction attempts

### 4. Role Management
- Use `/setuproles` to initialize roles
- Regular role cleanup with `role_service.cleanup_duplicate_roles()`
- Document role assignment procedures

## 📈 Performance Considerations

### 1. Caching
- Role checks use Discord.py's internal caching
- Audit logs use file-based storage with daily rotation
- Permission checks are O(1) operations

### 2. Memory Usage
- Secure views store minimal state (owner_id only)
- Audit logs are written immediately, not held in memory
- Role service uses Discord.py's role cache

### 3. Database Impact
- No database writes for permission checks
- Audit logs use file storage (configurable)
- Role changes logged but not stored in database

## 🔍 Troubleshooting

### Common Issues

**Permission Denied Unexpectedly**
1. Check user has the correct Discord role
2. Verify role name matches `config/roles.py`
3. Check role hierarchy and permissions

**UI Buttons Not Working**
1. Ensure using `SecureView` or `PersistentSecureView`
2. Verify `owner_id` is set correctly
3. Check audit logs for unauthorized attempts

**Audit Logs Not Appearing**
1. Check `logs/audit` directory exists
2. Verify write permissions
3. Check log rotation (daily files)

**Role Creation Fails**
1. Ensure bot has "Manage Roles" permission
2. Check bot's role is higher than roles being created
3. Verify server role limits not exceeded

## 🎯 Pass Criteria Verification

✅ **Creators only submit packs**
- `@require_role("creator")` on submission commands
- Audit logging for all attempts

✅ **Mods only review**
- `@require_role("moderator")` on review commands
- Permission inheritance allows admins too

✅ **Admins only refund**
- `@admin_only` decorator on economy commands
- Multiple permission layers for security

✅ **Buttons locked to owner**
- `SecureView` base class with `interaction_check`
- Persistent state verification
- Comprehensive audit logging

✅ **Violations logged**
- All permission denials logged
- Unauthorized UI interactions logged
- Role changes tracked
- Command usage monitored

## 🎉 Result

🔒 **Secure multi-role system**
- Four-tier role hierarchy with inheritance
- Granular permission control
- Discord integration

🎮 **Works with Discord UI**
- Native Discord role system
- Secure UI components
- Ephemeral error messages

🌐 **No website required**
- Everything within Discord
- File-based audit storage
- Built-in role management

📋 **Audit-ready**
- Comprehensive event logging
- Advanced filtering and search
- Statistics and reporting
- Export capabilities

The permission system is now fully implemented and ready for production use!
