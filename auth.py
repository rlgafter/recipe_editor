"""
User Authentication System using Flask-Login and bcrypt.
"""
import logging
from functools import wraps
from datetime import datetime
from typing import Optional
from flask import flash, redirect, url_for, request
from flask_login import LoginManager, current_user
from sqlalchemy import or_
import bcrypt

from db_models import db, User, UserPreference, UserStats

logger = logging.getLogger(__name__)

# Initialize Flask-Login
login_manager = LoginManager()


def init_auth(app):
    """Initialize authentication system with Flask app."""
    login_manager.init_app(app)
    login_manager.login_view = 'auth_login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    logger.info("Authentication system initialized")


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return db.session.query(User).get(int(user_id))


# ============================================================================
# AUTHENTICATION FUNCTIONS
# ============================================================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def authenticate_user(username_or_email: str, password: str) -> tuple[bool, Optional[User], str]:
    """
    Authenticate a user.
    
    Returns:
        (success, user, error_message)
    """
    # Find user by username or email
    user = db.session.query(User).filter(
        or_(
            User.username == username_or_email,
            User.email == username_or_email
        )
    ).first()
    
    if not user:
        return False, None, "Invalid username or email"
    
    if not user.is_active:
        return False, None, "Account is disabled"
    
    if not verify_password(password, user.password_hash):
        return False, None, "Invalid password"
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    logger.info(f"User authenticated: {user.username}")
    return True, user, ""


def create_user(username: str, email: str, password: str, display_name: str = None, user_type: str = 'unvalidated') -> tuple[bool, Optional[User], str]:
    """
    Create a new user account.
    
    Args:
        username: Username
        email: Email address
        password: Password
        display_name: Display name (optional)
        user_type: User type ('unvalidated', 'validated', 'share_recipes', 'admin')
    
    Returns:
        (success, user, error_message)
    """
    # Validate input
    if not username or not email or not password:
        return False, None, "Username, email, and password are required"
    
    if len(password) < 8:
        return False, None, "Password must be at least 8 characters"
    
    if len(username) < 3:
        return False, None, "Username must be at least 3 characters"
    
    # Check if username exists
    existing_user = db.session.query(User).filter(User.username == username).first()
    if existing_user:
        return False, None, f"Username '{username}' already exists"
    
    # Check if email exists
    existing_email = db.session.query(User).filter(User.email == email).first()
    if existing_email:
        return False, None, f"Email '{email}' already registered"
    
    try:
        # Map user_type to boolean flags
        # user_type can be: 'unvalidated', 'validated', 'share_recipes', 'admin'
        is_admin = (user_type == 'admin')
        can_publish_public = (user_type in ['share_recipes', 'admin'])
        email_verified = (user_type in ['validated', 'share_recipes', 'admin'])
        
        # Create user
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            display_name=display_name or username,
            is_admin=is_admin,
            can_publish_public=can_publish_public,
            email_verified=email_verified,
            is_active=True
        )
        db.session.add(user)
        db.session.flush()
        
        # Create user preferences
        prefs = UserPreference(user_id=user.id)
        db.session.add(prefs)
        
        # Create user stats
        stats = UserStats(user_id=user.id)
        db.session.add(stats)
        
        db.session.commit()
        
        logger.info(f"Created new user: {username} (type: {user_type})")
        return True, user, ""
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating user: {e}")
        return False, None, f"Error creating user: {str(e)}"


def change_password(user: User, old_password: str, new_password: str) -> tuple[bool, str]:
    """Change user password."""
    if not verify_password(old_password, user.password_hash):
        return False, "Current password is incorrect"
    
    if len(new_password) < 8:
        return False, "New password must be at least 8 characters"
    
    user.password_hash = hash_password(new_password)
    db.session.commit()
    
    logger.info(f"Password changed for user: {user.username}")
    return True, "Password changed successfully"


def update_user_profile(user: User, display_name: str = None, bio: str = None, 
                       avatar_url: str = None) -> bool:
    """Update user profile."""
    if display_name is not None:
        user.display_name = display_name
    if bio is not None:
        user.bio = bio
    if avatar_url is not None:
        user.avatar_url = avatar_url
    
    db.session.commit()
    logger.info(f"Updated profile for user: {user.username}")
    return True


# ============================================================================
# DECORATORS
# ============================================================================

def login_required(f):
    """Decorator to require login for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('auth_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin privileges."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('auth_login', next=request.url))
        if not current_user.is_admin:
            flash('Admin privileges required.', 'error')
            return redirect(url_for('recipe_list'))
        return f(*args, **kwargs)
    return decorated_function


def owns_recipe(recipe):
    """Check if current user owns the recipe."""
    return current_user.is_authenticated and recipe.user_id == current_user.id


def can_view_recipe(recipe):
    """Check if current user can view the recipe."""
    if recipe.visibility == 'public':
        return True
    if current_user.is_authenticated and recipe.user_id == current_user.id:
        return True
    return False


def can_edit_recipe(recipe):
    """Check if current user can edit the recipe."""
    return current_user.is_authenticated and recipe.user_id == current_user.id

