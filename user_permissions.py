"""
User permission decorators and utilities for the recipe application.
"""
from functools import wraps
from flask import flash, redirect, url_for, request
from flask_login import current_user


def user_type_required(*allowed_types):
    """
    Decorator to require specific user types.
    
    Args:
        *allowed_types: List of user type names that are allowed
        
    Example:
        @user_type_required('validated', 'share_recipes', 'admin')
        @user_type_required('admin')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'info')
                return redirect(url_for('auth_login', next=request.url))
            
            if current_user.user_type.name not in allowed_types:
                flash('Insufficient permissions to access this page.', 'error')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def can_create_recipes_required(f):
    """Decorator to require recipe creation permissions."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('auth_login', next=request.url))
        
        if not current_user.can_create_recipes():
            flash('You do not have permission to create recipes.', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function


def can_manage_users_required(f):
    """Decorator to require user management permissions."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('auth_login', next=request.url))
        
        if not current_user.can_manage_users():
            flash('You do not have permission to manage users.', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function


def can_manage_system_required(f):
    """Decorator to require system management permissions."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('auth_login', next=request.url))
        
        if not current_user.can_manage_system():
            flash('You do not have permission to manage system settings.', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function


def can_share_recipes_required(f):
    """Decorator to require recipe sharing permissions."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('auth_login', next=request.url))
        
        if not current_user.can_share_recipes():
            flash('You do not have permission to share recipes.', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin privileges (backward compatibility)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('auth_login', next=request.url))
        
        if not current_user.is_admin():
            flash('Admin privileges required.', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function


# Utility functions for permission checking
def can_view_recipe(recipe):
    """Check if current user can view a recipe."""
    if not current_user.is_authenticated:
        return recipe.visibility == 'public'
    
    # Admin can see everything
    if current_user.is_admin():
        return True
    
    # Public recipes are visible to all authenticated users
    if recipe.visibility == 'public':
        return True
    
    # Users can see their own recipes
    return recipe.user_id == current_user.id


def can_edit_recipe(recipe):
    """Check if current user can edit a recipe."""
    if not current_user.is_authenticated:
        return False
    
    return current_user.can_edit_recipe(recipe)


def can_delete_recipe(recipe):
    """Check if current user can delete a recipe."""
    if not current_user.is_authenticated:
        return False
    
    return current_user.can_delete_recipe(recipe)


def get_user_type_display_name(user_type_name):
    """Get display name for user type."""
    type_names = {
        'unvalidated': 'Unvalidated User',
        'validated': 'Validated User', 
        'share_recipes': 'Share Recipes User',
        'admin': 'Administrator'
    }
    return type_names.get(user_type_name, user_type_name.title())


def get_user_type_description(user_type_name):
    """Get description for user type."""
    descriptions = {
        'unvalidated': 'Can view public recipes only',
        'validated': 'Can view and create recipes',
        'share_recipes': 'Can view, create, and share recipes',
        'admin': 'Full system access'
    }
    return descriptions.get(user_type_name, 'Unknown user type')
