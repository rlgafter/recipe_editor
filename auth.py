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


def update_user_profile(user: User, display_name: str = None, 
                       avatar_url: str = None) -> bool:
    """Update user profile."""
    if display_name is not None:
        user.display_name = display_name
    if avatar_url is not None:
        user.avatar_url = avatar_url
    
    db.session.commit()
    logger.info(f"Updated profile for user: {user.username}")
    return True


def request_email_change(user: User, current_password: str, new_email: str) -> tuple[bool, str]:
    """
    Request email change with verification.
    Requires current password for security.
    Sends verification to new email and notification to old email.
    """
    import secrets
    from datetime import timedelta
    from email_service import email_service
    
    # Verify current password
    if not verify_password(current_password, user.password_hash):
        return False, "Current password is incorrect"
    
    # Validate new email
    new_email = new_email.lower().strip()
    if not new_email or '@' not in new_email:
        return False, "Valid email address is required"
    
    # Check if email is same as current
    if new_email == user.email:
        return False, "New email is the same as your current email"
    
    # Check if email already exists
    existing_user = User.query.filter(User.email == new_email).first()
    if existing_user and existing_user.id != user.id:
        return False, "This email address is already registered"
    
    # Generate verification token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    # Store pending email change
    user.pending_email = new_email
    user.email_change_token = token
    user.email_change_expires = expires_at
    db.session.commit()
    
    # Send verification email to new address
    verification_success, verification_error = email_service.send_email_change_verification(
        new_email,
        user.display_name or user.username,
        token
    )
    
    if not verification_success:
        logger.error(f"Failed to send verification email: {verification_error}")
        return False, f"Failed to send verification email: {verification_error}"
    
    # Send notification to old email
    notification_success, notification_error = email_service.send_email_change_notification(
        user.email,
        user.display_name or user.username,
        new_email
    )
    
    if not notification_success:
        logger.warning(f"Failed to send notification to old email: {notification_error}")
    
    logger.info(f"Email change requested for user {user.username}: {user.email} → {new_email}")
    return True, f"Verification email sent to {new_email}. Please check your inbox to complete the email change."


def verify_email_change(token: str) -> tuple[bool, str]:
    """
    Verify email change using token.
    Updates user email if token is valid and not expired.
    """
    user = User.query.filter(User.email_change_token == token).first()
    
    if not user:
        return False, "Invalid verification link"
    
    # Check if token expired
    if user.email_change_expires and datetime.utcnow() > user.email_change_expires:
        # Clear expired token
        user.pending_email = None
        user.email_change_token = None
        user.email_change_expires = None
        db.session.commit()
        return False, "Verification link has expired. Please request a new email change."
    
    if not user.pending_email:
        return False, "No pending email change found"
    
    # Check if pending email is already taken (race condition check)
    existing_user = User.query.filter(User.email == user.pending_email).first()
    if existing_user and existing_user.id != user.id:
        user.pending_email = None
        user.email_change_token = None
        user.email_change_expires = None
        db.session.commit()
        return False, "This email address is already registered by another user"
    
    # Update email
    old_email = user.email
    user.email = user.pending_email
    user.email_verified = True  # New email is verified
    user.pending_email = None
    user.email_change_token = None
    user.email_change_expires = None
    db.session.commit()
    
    logger.info(f"Email changed for user {user.username}: {old_email} → {user.email}")
    return True, "Email address updated successfully!"


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

