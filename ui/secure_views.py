"""
Secure UI Views

Base classes and utilities for creating secure Discord UI components
that only allow the owner to interact with them.
"""

import discord
from discord.ui import View, Button, Select
from typing import Optional, Dict, Any
from services.audit_service import AuditLog

class SecureView(View):
    """
    Base view class that ensures only the owner can interact with buttons.
    Integrates with the state management system for persistent UI security.
    """
    
    def __init__(self, owner_id: int, timeout: Optional[float] = None):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        Check if the interaction user is the owner of this view.
        
        Args:
            interaction: Discord interaction to check
            
        Returns:
            True if user is owner, False otherwise
        """
        if interaction.user.id != self.owner_id:
            # Log unauthorized interaction attempt
            AuditLog.record(
                event="unauthorized_ui_interaction",
                user_id=interaction.user.id,
                target_id=self.owner_id,
                details={
                    "view_type": self.__class__.__name__,
                    "custom_id": getattr(interaction, 'custom_id', 'unknown'),
                    "channel_id": interaction.channel.id,
                    "message_id": interaction.message.id if interaction.message else None
                }
            )
            
            # Send ephemeral error message
            try:
                await interaction.response.send_message(
                    "🚫 You cannot interact with this UI element. It belongs to another user.",
                    ephemeral=True
                )
            except discord.InteractionResponded:
                pass  # Already responded
            
            return False
        
        return True

class PersistentSecureView(SecureView):
    """
    Extended secure view that works with persistent state management.
    Loads state to verify ownership and handles state restoration.
    """
    
    def __init__(self, owner_id: int, state_id: str, timeout: Optional[float] = None):
        super().__init__(owner_id, timeout=timeout)
        self.state_id = state_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        Enhanced interaction check that verifies ownership through persistent state.
        """
        try:
            # Load state to verify current owner
            from ui.state import load_state
            state_data = load_state(self.state_id)
            
            if not state_data:
                # State not found - treat as unauthorized
                AuditLog.record(
                    event="unauthorized_ui_interaction",
                    user_id=interaction.user.id,
                    target_id=self.owner_id,
                    details={
                        "view_type": self.__class__.__name__,
                        "reason": "state_not_found",
                        "state_id": self.state_id,
                        "custom_id": getattr(interaction, 'custom_id', 'unknown')
                    }
                )
                
                try:
                    await interaction.response.send_message(
                        "🚫 This UI element has expired or is invalid.",
                        ephemeral=True
                    )
                except discord.InteractionResponded:
                    pass
                
                return False
            
            # Verify user ownership through state
            if interaction.user.id != state_data.get("user"):
                AuditLog.record(
                    event="unauthorized_ui_interaction",
                    user_id=interaction.user.id,
                    target_id=state_data.get("user"),
                    details={
                        "view_type": self.__class__.__name__,
                        "reason": "state_mismatch",
                        "state_id": self.state_id,
                        "state_user": state_data.get("user"),
                        "interaction_user": interaction.user.id,
                        "custom_id": getattr(interaction, 'custom_id', 'unknown')
                    }
                )
                
                try:
                    await interaction.response.send_message(
                        "🚫 You cannot interact with this UI element. It belongs to another user.",
                        ephemeral=True
                    )
                except discord.InteractionResponded:
                    pass
                
                return False
            
            # Update owner_id if it differs from state (for consistency)
            if self.owner_id != state_data.get("user"):
                self.owner_id = state_data.get("user")
            
            return True
            
        except Exception as e:
            # Error loading state - deny access for safety
            AuditLog.record(
                event="ui_security_error",
                user_id=interaction.user.id,
                target_id=self.owner_id,
                details={
                    "view_type": self.__class__.__name__,
                    "error": str(e),
                    "state_id": self.state_id,
                    "custom_id": getattr(interaction, 'custom_id', 'unknown')
                }
            )
            
            try:
                await interaction.response.send_message(
                    "🚫 Security check failed. Please try again.",
                    ephemeral=True
                )
            except discord.InteractionResponded:
                pass
            
            return False

class SecureButton(Button):
    """
    Secure button that only allows the owner to interact.
    """
    
    def __init__(self, owner_id: int, **kwargs):
        super().__init__(**kwargs)
        self.owner_id = owner_id
    
    async def callback(self, interaction: discord.Interaction):
        """Override to add security check."""
        if interaction.user.id != self.owner_id:
            AuditLog.record(
                event="unauthorized_button_interaction",
                user_id=interaction.user.id,
                target_id=self.owner_id,
                details={
                    "button_label": self.label,
                    "custom_id": self.custom_id,
                    "view_type": self.view.__class__.__name__ if self.view else "unknown"
                }
            )
            
            try:
                await interaction.response.send_message(
                    "🚫 You cannot press this button.",
                    ephemeral=True
                )
            except discord.InteractionResponded:
                pass
            return
        
        # Call the actual callback if it exists
        if hasattr(self, '_actual_callback'):
            return await self._actual_callback(interaction)

class SecureSelect(Select):
    """
    Secure select menu that only allows the owner to interact.
    """
    
    def __init__(self, owner_id: int, **kwargs):
        super().__init__(**kwargs)
        self.owner_id = owner_id
    
    async def callback(self, interaction: discord.Interaction):
        """Override to add security check."""
        if interaction.user.id != self.owner_id:
            AuditLog.record(
                event="unauthorized_select_interaction",
                user_id=interaction.user.id,
                target_id=self.owner_id,
                details={
                    "select_placeholder": self.placeholder,
                    "custom_id": self.custom_id,
                    "selected_values": self.values,
                    "view_type": self.view.__class__.__name__ if self.view else "unknown"
                }
            )
            
            try:
                await interaction.response.send_message(
                    "🚫 You cannot use this select menu.",
                    ephemeral=True
                )
            except discord.InteractionResponded:
                pass
            return
        
        # Call the actual callback if it exists
        if hasattr(self, '_actual_callback'):
            return await self._actual_callback(interaction)

def secure_button(owner_id: int, **button_kwargs):
    """
    Decorator to create secure buttons with automatic ownership checking.
    
    Args:
        owner_id: ID of the user who can interact with this button
        **button_kwargs: Arguments to pass to Button constructor
        
    Returns:
        Decorator function
    """
    def decorator(func):
        async def wrapper(interaction: discord.Interaction):
            # Security check is handled by SecureButton class
            return await func(interaction)
        
        # Create button with security
        button = SecureButton(owner_id, **button_kwargs)
        button._actual_callback = wrapper
        return button
    
    return decorator

def secure_select(owner_id: int, **select_kwargs):
    """
    Decorator to create secure select menus with automatic ownership checking.
    
    Args:
        owner_id: ID of the user who can interact with this select
        **select_kwargs: Arguments to pass to Select constructor
        
    Returns:
        Decorator function
    """
    def decorator(func):
        async def wrapper(interaction: discord.Interaction):
            # Security check is handled by SecureSelect class
            return await func(interaction)
        
        # Create select with security
        select = SecureSelect(owner_id, **select_kwargs)
        select._actual_callback = wrapper
        return select
    
    return decorator

class SecureModal(discord.ui.Modal):
    """
    Secure modal that only allows the owner to submit.
    """
    
    def __init__(self, owner_id: int, **kwargs):
        super().__init__(**kwargs)
        self.owner_id = owner_id
    
    async def on_submit(self, interaction: discord.Interaction):
        """Override to add security check."""
        if interaction.user.id != self.owner_id:
            AuditLog.record(
                event="unauthorized_modal_submission",
                user_id=interaction.user.id,
                target_id=self.owner_id,
                details={
                    "modal_title": self.title,
                    "view_type": self.view.__class__.__name__ if self.view else "unknown"
                }
            )
            
            try:
                await interaction.response.send_message(
                    "🚫 You cannot submit this modal.",
                    ephemeral=True
                )
            except discord.InteractionResponded:
                pass
            return
        
        # Call the actual on_submit if it exists
        if hasattr(self, '_actual_on_submit'):
            return await self._actual_on_submit(interaction)

def secure_modal(owner_id: int, **modal_kwargs):
    """
    Decorator to create secure modals with automatic ownership checking.
    
    Args:
        owner_id: ID of the user who can submit this modal
        **modal_kwargs: Arguments to pass to Modal constructor
        
    Returns:
        Decorator function
    """
    def decorator(func):
        async def wrapper(interaction: discord.Interaction):
            # Security check is handled by SecureModal class
            return await func(interaction)
        
        # Create modal with security
        modal = SecureModal(owner_id, **modal_kwargs)
        modal._actual_on_submit = wrapper
        return modal
    
    return decorator

# Utility functions for creating secure UI components
def create_secure_view(owner_id: int, timeout: Optional[float] = None) -> SecureView:
    """Create a new secure view for the given owner."""
    return SecureView(owner_id, timeout=timeout)

def create_persistent_secure_view(owner_id: int, state_id: str, timeout: Optional[float] = None) -> PersistentSecureView:
    """Create a new persistent secure view for the given owner."""
    return PersistentSecureView(owner_id, state_id, timeout=timeout)

def add_secure_button(view: SecureView, owner_id: int, label: str, callback, **kwargs):
    """Add a secure button to a view."""
    button = SecureButton(owner_id, label=label, **kwargs)
    button._actual_callback = callback
    view.add_item(button)
    return button

def add_secure_select(view: SecureView, owner_id: int, placeholder: str, callback, **kwargs):
    """Add a secure select menu to a view."""
    select = SecureSelect(owner_id, placeholder=placeholder, **kwargs)
    select._actual_callback = callback
    view.add_item(select)
    return select
