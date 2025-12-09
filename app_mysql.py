"""
Recipe Editor - MySQL Multi-User Flask Application
This is the MySQL-enabled version with user authentication.
To use: set STORAGE_BACKEND=mysql in environment
"""
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from dotenv import load_dotenv

# Setup basic logging first (before any imports that might fail)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

logger.debug("=" * 70)
logger.debug("Recipe Editor - Starting Application")
logger.debug("=" * 70)

# Load environment variables from .env file
logger.debug("[1/10] Loading environment variables...")
try:
    env_loaded = load_dotenv()
    logger.debug(f"  .env file loaded: {env_loaded}")
    if os.path.exists('.env'):
        logger.debug(f"  .env file exists at: {os.path.abspath('.env')}")
    else:
        logger.warning("  .env file not found")
except Exception as e:
    logger.error(f"  Error loading .env file: {e}", exc_info=True)

logger.debug("[2/10] Importing configuration...")
try:
    import config
    logger.debug(f"  Config loaded: HOST={config.HOST}, PORT={config.PORT}, DEBUG={config.DEBUG}")
    logger.debug(f"  Database URI: {config.SQLALCHEMY_DATABASE_URI.split('@')[0]}@...")
except Exception as e:
    logger.error(f"  Error importing config: {e}", exc_info=True)
    raise

logger.debug("[3/10] Importing database models...")
try:
    from db_models import db
    logger.debug("  Database models imported successfully")
except Exception as e:
    logger.error(f"  Error importing db_models: {e}", exc_info=True)
    raise

logger.debug("[4/10] Importing storage module...")
try:
    from mysql_storage import MySQLStorage, init_storage
    logger.debug("  Storage module imported successfully")
except Exception as e:
    logger.error(f"  Error importing mysql_storage: {e}", exc_info=True)
    raise

logger.debug("[5/10] Importing authentication module...")
try:
    from auth import init_auth, authenticate_user, create_user as create_user_account, change_password, update_user_profile, request_email_change
    logger.debug("  Authentication module imported successfully")
except Exception as e:
    logger.error(f"  Error importing auth: {e}", exc_info=True)
    raise

logger.debug("[6/10] Importing service modules...")
try:
    from gemini_service import gemini_service
    logger.debug("  Gemini service imported")
except Exception as e:
    logger.warning(f"  Warning importing gemini_service: {e}")

try:
    from email_service import email_service
    logger.debug("  Email service imported")
except Exception as e:
    logger.warning(f"  Warning importing email_service: {e}")

logger.debug("[7/10] Importing admin routes...")
try:
    from admin_routes import register_admin_routes
    logger.debug("  Admin routes module imported successfully")
except Exception as e:
    logger.error(f"  Error importing admin_routes: {e}", exc_info=True)
    raise

# Initialize Flask app
logger.debug("[8/10] Initializing Flask application...")
try:
    app = Flask(__name__)
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS
    app.config['SQLALCHEMY_ECHO'] = config.SQLALCHEMY_ECHO
    logger.debug("  Flask app created and configured")
except Exception as e:
    logger.error(f"  Error initializing Flask app: {e}", exc_info=True)
    raise

# Initialize database
logger.debug("[9/10] Initializing database connection...")
try:
    db.init_app(app)
    logger.debug("  Database initialized with Flask app")
    
    # Test database connection
    with app.app_context():
        try:
            from db_config import test_connection
            success, msg = test_connection()
            if success:
                logger.debug(f"  Database connection test: {msg}")
            else:
                logger.error(f"  Database connection test failed: {msg}")
        except Exception as e:
            logger.warning(f"  Could not test database connection: {e}")
except Exception as e:
    logger.error(f"  Error initializing database: {e}", exc_info=True)
    raise

# Initialize authentication
logger.debug("[10/10] Initializing authentication...")
try:
    init_auth(app)
    logger.debug("  Authentication initialized")
except Exception as e:
    logger.error(f"  Error initializing authentication: {e}", exc_info=True)
    raise

# Initialize storage
logger.debug("Initializing storage...")
try:
    with app.app_context():
        storage = init_storage(db.session)
        logger.debug("  Storage initialized successfully")
except Exception as e:
    logger.error(f"  Error initializing storage: {e}", exc_info=True)
    raise

# Register admin routes
logger.debug("Registering admin routes...")
try:
    register_admin_routes(app)
    logger.debug("  Admin routes registered")
except Exception as e:
    logger.error(f"  Error registering admin routes: {e}", exc_info=True)
    raise

# Configure logging
logger.debug("Configuring application logging...")
try:
    if not os.path.exists(config.LOGS_DIR):
        os.makedirs(config.LOGS_DIR)
        logger.debug(f"  Created logs directory: {config.LOGS_DIR}")

    file_handler = RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=1024 * 1024,
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    file_handler.setLevel(logging.DEBUG)  # Changed to DEBUG

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    console_handler.setLevel(logging.DEBUG)  # Changed to DEBUG

    # Get root logger and configure
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.DEBUG)  # Changed to DEBUG
    
    # Also set Flask app logger to DEBUG
    app.logger.setLevel(logging.DEBUG)
    
    logger.debug(f"  Logging configured: file={config.LOG_FILE}, level=DEBUG")
    app.logger.info("Recipe Editor (MySQL) application starting")
    app.logger.debug("Debug logging enabled")
except Exception as e:
    logger.error(f"  Error configuring logging: {e}", exc_info=True)
    # Continue anyway - basic logging is already set up


# ============================================================================
# Authentication Routes
# ============================================================================

@app.route('/auth/login', methods=['GET', 'POST'])
def auth_login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for('recipe_list'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'
        
        success, user, error_msg = authenticate_user(username, password)
        
        if success:
            login_user(user, remember=remember)
            flash(f'Welcome back, {user.display_name}!', 'success')
            
            # Redirect to next page or home
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('recipe_list'))
        else:
            flash(error_msg, 'error')
    
    return render_template('login.html')


@app.route('/auth/logout')
@login_required
def auth_logout():
    """User logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('recipe_list'))


@app.route('/auth/register', methods=['GET', 'POST'])
def auth_register():
    """User registration."""
    if current_user.is_authenticated:
        return redirect(url_for('recipe_list'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        display_name = request.form.get('display_name', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        terms_accepted = request.form.get('terms_accepted') == 'on'
        
        # Validate
        if password != password_confirm:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        if not terms_accepted:
            flash('You must accept the terms of service to create an account', 'error')
            return render_template('register.html')
        
        success, user, error_msg = create_user_account(username, email, password, display_name or None)
        
        if success:
            # Link any pending shares for this email
            from db_models import PendingRecipeShare
            pending_shares = db.session.query(PendingRecipeShare).filter(
                PendingRecipeShare.recipient_email == email.lower(),
                PendingRecipeShare.shared_with_user_id.is_(None),
                PendingRecipeShare.status == 'pending'
            ).all()
            
            if pending_shares:
                for pending_share in pending_shares:
                    pending_share.shared_with_user_id = user.id
                db.session.commit()
                flash(f'Welcome! You have {len(pending_shares)} pending recipe share(s) waiting for you.', 'info')
            
            # Auto-login
            login_user(user)
            if not pending_shares:
                flash(f'Welcome to Recipe Editor, {user.display_name}!', 'success')
            return redirect(url_for('recipe_list'))
        else:
            flash(error_msg, 'error')
    
    return render_template('register.html')


@app.route('/auth/profile', methods=['GET', 'POST'])
@login_required
def auth_profile():
    """User profile page."""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_profile':
            display_name = request.form.get('display_name', '').strip()
            
            update_user_profile(current_user, display_name=display_name)
            flash('Profile updated successfully!', 'success')
        
        elif action == 'change_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            new_password_confirm = request.form.get('new_password_confirm', '')
            
            if new_password != new_password_confirm:
                flash('New passwords do not match', 'error')
            else:
                success, message = change_password(current_user, current_password, new_password)
                if success:
                    flash(message, 'success')
                else:
                    flash(message, 'error')
        
        elif action == 'change_email':
            current_password = request.form.get('current_password', '')
            new_email = request.form.get('new_email', '').strip().lower()
            
            if not current_password:
                flash('Current password is required to change email', 'error')
            elif not new_email or '@' not in new_email:
                flash('Valid email address is required', 'error')
            else:
                success, message = request_email_change(current_user, current_password, new_email)
                if success:
                    flash(message, 'success')
                else:
                    flash(message, 'error')
    
    return render_template('profile.html')


@app.route('/verify-email-change/<token>')
def verify_email_change_route(token):
    """Verify email change using token."""
    from auth import verify_email_change
    
    success, message = verify_email_change(token)
    
    if success:
        flash(message, 'success')
        return redirect(url_for('auth_profile'))
    else:
        flash(message, 'error')
        return redirect(url_for('auth_profile'))


@app.route('/auth/forgot-password', methods=['GET', 'POST'])
def auth_forgot_password():
    """Forgot password - request password reset."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        
        if not username:
            flash('Please enter your username', 'error')
            return render_template('forgot_password.html')
        
        # Find user by username
        from db_models import User, PasswordResetToken
        user = db.session.query(User).filter(User.username == username).first()
        
        if user:
            # Create password reset token (expires in 1 hour)
            import secrets
            from datetime import datetime, timedelta
            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=1)
            
            # Invalidate old tokens for this user
            db.session.query(PasswordResetToken).filter(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used == False
            ).update({PasswordResetToken.used: True})
            
            # Create new token
            reset_token = PasswordResetToken(
                user_id=user.id,
                token=token,
                expires_at=expires_at
            )
            db.session.add(reset_token)
            db.session.commit()
            
            # Send password reset email
            success, error_msg = email_service.send_password_reset_email(
                user.email,
                user.display_name or user.username,
                token
            )
            
            if success:
                app.logger.info(f"Password reset email sent to {user.email}")
        
        # Always show success message (security - don't reveal if user exists)
        return render_template(
            'recovery_confirmation.html',
            page_title='Email Sent',
            confirmation_message='If an account exists with that username, a password reset link has been sent to the registered email address.',
            recovery_type='password'
        )
    
    return render_template('forgot_password.html')


@app.route('/auth/forgot-username', methods=['GET', 'POST'])
def auth_forgot_username():
    """Forgot username - recover username via email."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Please enter your email address', 'error')
            return render_template('forgot_username.html')
        
        # Find user by email
        from db_models import User
        user = db.session.query(User).filter(User.email == email).first()
        
        if user:
            # Send username recovery email
            success, error_msg = email_service.send_username_recovery_email(
                user.email,
                user.username
            )
            
            if success:
                app.logger.info(f"Username recovery email sent to {email}")
        
        # Always show success message (security - don't reveal if user exists)
        return render_template(
            'recovery_confirmation.html',
            page_title='Email Sent',
            confirmation_message='If an account exists with that email address, your username has been sent to that email.',
            recovery_type='username'
        )
    
    return render_template('forgot_username.html')


@app.route('/auth/reset-password/<token>', methods=['GET', 'POST'])
def auth_reset_password(token):
    """Reset password using token."""
    from db_models import User, PasswordResetToken
    from datetime import datetime
    
    # Validate token
    reset_token = db.session.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > datetime.utcnow()
    ).first()
    
    if not reset_token:
        flash('Invalid or expired password reset link. Please request a new one.', 'error')
        return redirect(url_for('auth_forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate passwords
        if not password or len(password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return render_template('reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('reset_password.html', token=token)
        
        # Update password
        user = db.session.query(User).filter(User.id == reset_token.user_id).first()
        if user:
            from werkzeug.security import generate_password_hash
            user.password_hash = generate_password_hash(password)
            reset_token.used = True
            db.session.commit()
            
            app.logger.info(f"Password reset successful for user {user.username}")
            flash('Your password has been reset successfully. Please log in with your new password.', 'success')
            return redirect(url_for('auth_login'))
    
    return render_template('reset_password.html', token=token)


@app.route('/setup-password/<token>', methods=['GET', 'POST'])
def setup_password(token):
    """Password setup for new users (admin-created accounts)."""
    from db_models import User
    from datetime import datetime
    from werkzeug.security import generate_password_hash
    
    # Find user by setup token
    user = db.session.query(User).filter(
        User.password_setup_token == token,
        User.account_setup_completed == False
    ).first()
    
    if not user:
        flash('Invalid or expired setup link. Please contact your administrator for a new link.', 'error')
        return redirect(url_for('auth_login'))
    
    # Check if token is expired
    if user.password_setup_expires < datetime.utcnow():
        flash('This setup link has expired. Please contact your administrator for a new link.', 'error')
        return redirect(url_for('auth_login'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate passwords
        if not password or len(password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return render_template('setup_password.html', token=token, user=user)
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('setup_password.html', token=token, user=user)
        
        try:
            # Update password
            user.password_hash = generate_password_hash(password)
            user.is_active = True
            user.account_setup_completed = True
            user.password_setup_token = None  # Invalidate token
            user.password_setup_expires = None
            db.session.commit()
            
            app.logger.info(f"Password setup completed for user {user.username}")
            flash('Your password has been set successfully! Please log in with your new credentials.', 'success')
            return redirect(url_for('auth_login'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error setting password: {str(e)}")
            flash('An error occurred. Please try again.', 'error')
    
    return render_template('setup_password.html', token=token, user=user)


# ============================================================================
# Recipe Routes (Multi-User)
# ============================================================================

@app.route('/')
def home():
    """Home page for unauthenticated users."""
    if current_user.is_authenticated:
        return redirect(url_for('recipe_list'))
    return render_template('home.html')


@app.route('/recipes')
@login_required
def recipe_list():
    """Display list of recipes."""
    try:
        app.logger.debug("=" * 70)
        app.logger.debug("RECIPE_LIST ROUTE - Starting request handling")
        app.logger.debug("=" * 70)
        
        # Check current_user status
        app.logger.debug(f"Current user authenticated: {current_user.is_authenticated}")
        if current_user.is_authenticated:
            app.logger.debug(f"Current user ID: {current_user.id}, Username: {current_user.username}")
        else:
            app.logger.debug("Current user is anonymous")
        
        user_id = current_user.id if current_user.is_authenticated else None
        app.logger.debug(f"Using user_id: {user_id}")
        
        # Get filter parameters
        search_term = request.args.get('search', '').strip()
        tag_input = request.args.get('tags', '').strip()
        match_all = request.args.get('match_all') == 'true'
        
        # Parse tags from text input - support both comma and space delimiters, normalize to lowercase
        selected_tags = []
        if tag_input:
            # Split by comma first, then by space for each part
            parts = tag_input.split(',')
            for part in parts:
                # Split each comma-separated part by spaces
                space_separated = part.strip().split()
                for tag in space_separated:
                    tag = tag.strip().lower()  # Normalize to lowercase
                    if tag and tag not in selected_tags:
                        selected_tags.append(tag)
        
        app.logger.debug(f"Request parameters - search_term: '{search_term}', selected_tags: {selected_tags}, match_all: {match_all}")
        
        # Get all tags (user's personal + system tags)
        app.logger.debug("Fetching all tags...")
        try:
            all_tags = storage.get_all_tags(user_id)
            app.logger.debug(f"Retrieved {len(all_tags) if all_tags else 0} tags")
        except Exception as e:
            app.logger.error(f"Error fetching tags: {e}", exc_info=True)
            all_tags = {}
        
        # Get recipes (search, filter by tags, or all)
        app.logger.debug("Fetching recipes...")
        try:
            if search_term:
                app.logger.debug(f"Using search_recipes with term: '{search_term}'")
                recipes = storage.search_recipes(
                    search_term=search_term, 
                    tag_names=selected_tags, 
                    match_all_tags=match_all, 
                    user_id=user_id
                )
            elif selected_tags:
                app.logger.debug(f"Filtering by tags: {selected_tags}")
                recipes = storage.filter_recipes_by_tags(selected_tags, match_all, user_id)
            else:
                app.logger.debug("Fetching all recipes")
                recipes = storage.get_all_recipes(user_id)
            
            app.logger.debug(f"Retrieved {len(recipes) if recipes else 0} recipes")
        except Exception as e:
            app.logger.error(f"Error fetching recipes: {e}", exc_info=True)
            import traceback
            app.logger.error(f"Traceback: {traceback.format_exc()}")
            recipes = []
        
        # Get shared recipe information for authenticated users
        shared_recipe_info = {}
        if user_id:
            from db_models import RecipeShare
            shared_recipes = db.session.query(RecipeShare).filter(
                RecipeShare.shared_with_user_id == user_id
            ).all()
            for share in shared_recipes:
                if share.recipe_id not in shared_recipe_info:
                    shared_recipe_info[share.recipe_id] = {
                        'shared_by': share.shared_by_user_id,
                        'shared_by_user': None
                    }
            # Get user objects for shared_by
            if shared_recipe_info:
                from db_models import User
                user_ids = [info['shared_by'] for info in shared_recipe_info.values()]
                users = db.session.query(User).filter(User.id.in_(user_ids)).all()
                user_dict = {u.id: u for u in users}
                for recipe_id, info in shared_recipe_info.items():
                    info['shared_by_user'] = user_dict.get(info['shared_by'])
        
        # Get pending shares for authenticated users
        pending_shares_list = []
        if user_id:
            from db_models import PendingRecipeShare, Recipe, User
            pending_shares = db.session.query(PendingRecipeShare).filter(
                PendingRecipeShare.shared_with_user_id == user_id,
                PendingRecipeShare.status == 'pending'
            ).all()
            
            for pending_share in pending_shares:
                recipe = db.session.query(Recipe).filter(Recipe.id == pending_share.recipe_id).first()
                sender = db.session.query(User).filter(User.id == pending_share.shared_by_user_id).first()
                if recipe:
                    pending_shares_list.append({
                        'pending_share': pending_share,
                        'recipe': recipe,
                        'sender': sender
                    })
        
        app.logger.debug("Rendering template...")
        try:
            return render_template(
                'recipe_list.html',
                recipes=recipes,
                all_tags=all_tags,
                selected_tags=selected_tags,
                match_all=match_all,
                search_term=search_term,
                shared_recipe_info=shared_recipe_info,
                current_user_id=user_id,
                pending_shares_list=pending_shares_list
            )
        except Exception as e:
            app.logger.error(f"Error rendering template: {e}", exc_info=True)
            import traceback
            app.logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        
    except Exception as e:
        app.logger.error("=" * 70)
        app.logger.error("RECIPE_LIST ROUTE - FATAL ERROR")
        app.logger.error("=" * 70)
        app.logger.error(f"Error type: {type(e).__name__}")
        app.logger.error(f"Error message: {str(e)}")
        import traceback
        app.logger.error(f"Full traceback:\n{traceback.format_exc()}")
        app.logger.error("=" * 70)
        
        # Re-raise to let Flask error handler deal with it
        raise


@app.route('/recipe/<int:recipe_id>')
@login_required
def recipe_view(recipe_id):
    """Display a single recipe."""
    user_id = current_user.id if current_user.is_authenticated else None
    recipe = storage.get_recipe(recipe_id, user_id)
    
    if not recipe:
        flash('Recipe not found or you do not have permission to view it', 'error')
        if current_user.is_authenticated:
            return redirect(url_for('recipe_list'))
        else:
            return redirect(url_for('home'))
    
    # Increment view count
    storage.increment_view_count(recipe_id)
    
    # Check if favorited (for authenticated users)
    is_favorited = False
    if current_user.is_authenticated:
        is_favorited = storage.is_favorited(current_user.id, recipe_id)
    
    # Get submitter information
    from db_models import User
    submitter = db.session.query(User).filter(User.id == recipe.user_id).first()
    
    # Check if recipe is shared with current user
    shared_by_friend = None
    is_shared_recipe = False
    if current_user.is_authenticated and recipe.user_id != current_user.id:
        shared_by_friend = recipe.get_shared_by_friend(current_user.id)
        is_shared_recipe = shared_by_friend is not None
    
    email_configured = email_service.is_configured()
    
    # Import layout configuration
    from config import get_recipe_layout, is_section_enabled
    
    return render_template(
        'recipe_view.html',
        recipe=recipe,
        submitter=submitter,
        is_favorited=is_favorited,
        email_configured=email_configured,
        layout_sections=get_recipe_layout(),
        is_section_enabled=is_section_enabled,
        shared_by_friend=shared_by_friend,
        is_shared_recipe=is_shared_recipe
    )


@app.route('/recipe/new', methods=['GET', 'POST'])
@login_required
def recipe_new():
    """Create a new recipe."""
    if request.method == 'GET':
        all_tags = storage.get_all_tags(current_user.id)
        gemini_configured = gemini_service.is_configured()
        return render_template('recipe_form.html', recipe=None, all_tags=all_tags, 
                             new_tags=[], gemini_configured=gemini_configured)
    
    # POST - Create new recipe
    try:
        app.logger.info("=== RECIPE CREATION DEBUG START ===")
        app.logger.info(f"Form data keys: {list(request.form.keys())}")
        app.logger.info(f"User: {current_user.username} (ID: {current_user.id})")
        
        recipe_data = _parse_recipe_form(request.form)
        app.logger.info(f"Parsed recipe data: name='{recipe_data.get('name')}', ingredients_count={len(recipe_data.get('ingredients', []))}")
        
        # Log each ingredient
        for i, ing in enumerate(recipe_data.get('ingredients', [])):
            app.logger.info(f"  Ingredient {i+1}: desc='{ing.get('description')}', amount='{ing.get('amount')}', unit='{ing.get('unit')}'")
        
        # Get visibility for validation
        visibility = recipe_data.get('visibility', 'incomplete')
        
        # Validate recipe data
        is_valid, errors, warnings = _validate_recipe_data(recipe_data, visibility=visibility)
        app.logger.info(f"Validation result: {'PASS' if is_valid else 'FAIL'}")
        if errors:
            app.logger.info(f"Validation errors: {errors}")
        if warnings:
            app.logger.info(f"Validation warnings: {warnings}")
        
        # Display warnings (non-blocking)
        for warning in warnings:
            flash(warning, 'warning')
        
        # Display errors (blocking)
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            all_tags = storage.get_all_tags(current_user.id)
            gemini_configured = gemini_service.is_configured()
            app.logger.info("=== RECIPE CREATION DEBUG END (VALIDATION FAILED) ===")
            # Preserve user's entered data in the form
            recipe_form_data = _create_form_data_object(recipe_data)
            return render_template('recipe_form.html', recipe=recipe_form_data, all_tags=all_tags, 
                                 new_tags=recipe_data.get('tags', []), gemini_configured=gemini_configured), 400
        
        # Validate visibility permission
        if visibility == 'public' and not current_user.can_publish_public_recipes():
            flash('You do not have permission to publish public recipes', 'error')
            all_tags = storage.get_all_tags(current_user.id)
            gemini_configured = gemini_service.is_configured()
            # Preserve user's entered data in the form
            recipe_form_data = _create_form_data_object(recipe_data)
            return render_template('recipe_form.html', recipe=recipe_form_data, all_tags=all_tags, 
                                 new_tags=recipe_data.get('tags', []), gemini_configured=gemini_configured), 403
        
        # Additional source validation for public recipes
        # Note: Source URL is optional, but if provided, it should be accessible
        if visibility == 'public':
            source = recipe_data.get('source', {})
            source_url = source.get('url', '').strip()
            
            # Only validate URL if one is provided (URL is optional)
            if source_url:
                if not gemini_service.validate_url_accessibility(source_url):
                    flash('The source URL is not publicly accessible. Please provide a valid URL or leave it blank.', 'error')
                    all_tags = storage.get_all_tags(current_user.id)
                    gemini_configured = gemini_service.is_configured()
                    # Preserve user's entered data in the form
                    recipe_form_data = _create_form_data_object(recipe_data)
                    return render_template('recipe_form.html', recipe=recipe_form_data, all_tags=all_tags, 
                                         new_tags=recipe_data.get('tags', []), gemini_configured=gemini_configured), 400
        
        recipe = storage.save_recipe(recipe_data, current_user.id)
        
        flash(f'Recipe "{recipe.name}" created successfully!', 'success')
        app.logger.info(f"Created new recipe {recipe.id}: {recipe.name}")
        app.logger.info("=== RECIPE CREATION DEBUG END (SUCCESS) ===")
        
        return redirect(url_for('recipe_view', recipe_id=recipe.id))
    
    except Exception as e:
        app.logger.error(f"Error creating recipe: {str(e)}")
        app.logger.error("=== RECIPE CREATION DEBUG END (EXCEPTION) ===")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Show specific error message to help user understand what went wrong
        error_message = str(e)
        if 'PendingRollbackError' in error_message or 'Unknown column' in error_message:
            flash('Database error occurred. The database schema may need updating. Please contact support.', 'error')
        elif 'IntegrityError' in str(type(e)):
            flash('Data integrity error. Please check that all required fields are filled correctly.', 'error')
        else:
            # Show the actual error to help with debugging
            flash(f'Error creating recipe: {str(e)[:200]}', 'error')
        
        # Preserve user's entered data in the form
        try:
            all_tags = storage.get_all_tags(current_user.id)
        except:
            all_tags = {}
        gemini_configured = gemini_service.is_configured()
        recipe_form_data = _create_form_data_object(recipe_data)
        return render_template('recipe_form.html', recipe=recipe_form_data, all_tags=all_tags, 
                             new_tags=recipe_data.get('tags', []), gemini_configured=gemini_configured), 500


@app.route('/recipe/<int:recipe_id>/edit', methods=['GET', 'POST'])
@login_required
def recipe_edit(recipe_id):
    """Edit an existing recipe."""
    recipe = storage.get_recipe(recipe_id, current_user.id)
    
    if not recipe:
        flash('Recipe not found', 'error')
        return redirect(url_for('recipe_list'))
    
    # Public recipes cannot be edited
    if recipe.visibility == 'public':
        flash('Public recipes cannot be edited', 'error')
        return redirect(url_for('recipe_view', recipe_id=recipe_id))
    
    if not current_user.can_edit_recipe(recipe):
        flash('You do not have permission to edit this recipe', 'error')
        return redirect(url_for('recipe_view', recipe_id=recipe_id))
    
    if request.method == 'GET':
        all_tags = storage.get_all_tags(current_user.id)
        gemini_configured = gemini_service.is_configured()
        return render_template('recipe_form.html', recipe=recipe, all_tags=all_tags, 
                             new_tags=[], gemini_configured=gemini_configured)
    
    # POST - Update recipe
    try:
        recipe_data = _parse_recipe_form(request.form)
        
        # Check if trying to change visibility from public to non-public when recipe has shares
        new_visibility = recipe_data.get('visibility', recipe.visibility)
        if recipe.visibility == 'public' and new_visibility != 'public':
            if recipe.has_active_shares():
                flash('Cannot change visibility: This recipe is shared with friends and must remain public', 'error')
                all_tags = storage.get_all_tags(current_user.id)
                gemini_configured = gemini_service.is_configured()
                return render_template('recipe_form.html', recipe=recipe, all_tags=all_tags, 
                                     new_tags=[], gemini_configured=gemini_configured), 400
        
        # Get visibility for validation
        visibility = recipe_data.get('visibility', recipe.visibility if recipe else 'incomplete')
        
        # Validate recipe data
        is_valid, errors, warnings = _validate_recipe_data(recipe_data, visibility=visibility)
        
        # Display warnings (non-blocking)
        for warning in warnings:
            flash(warning, 'warning')
        
        # Display errors (blocking)
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            all_tags = storage.get_all_tags(current_user.id)
            gemini_configured = gemini_service.is_configured()
            # Preserve user's entered data in the form, but keep recipe object for template compatibility
            recipe_form_data = _create_form_data_object(recipe_data, recipe_id)
            recipe_form_data.user_id = recipe.user_id  # Add user_id for template compatibility
            return render_template('recipe_form.html', recipe=recipe_form_data, all_tags=all_tags, 
                                 new_tags=recipe_data.get('tags', []), gemini_configured=gemini_configured), 400
        
        # Validate visibility permission
        if visibility == 'public' and not current_user.can_publish_public_recipes():
            flash('You do not have permission to publish public recipes', 'error')
            all_tags = storage.get_all_tags(current_user.id)
            gemini_configured = gemini_service.is_configured()
            # Preserve user's entered data in the form, but keep recipe object for template compatibility
            recipe_form_data = _create_form_data_object(recipe_data, recipe_id)
            recipe_form_data.user_id = recipe.user_id  # Add user_id for template compatibility
            return render_template('recipe_form.html', recipe=recipe_form_data, all_tags=all_tags, 
                                 new_tags=recipe_data.get('tags', []), gemini_configured=gemini_configured), 403
        
        # Additional source validation for public recipes
        # Note: For public recipes, source attribution is required but URL is optional.
        # At least one of: source name, author, or URL must be provided (validated separately).
        # If a URL is provided, it must be publicly accessible.
        if visibility == 'public':
            source = recipe_data.get('source', {})
            source_url = source.get('url', '').strip()
            
            # Only validate URL if one is provided (URL is optional)
            if source_url:
                if not gemini_service.validate_url_accessibility(source_url):
                    flash('The source URL is not publicly accessible. Please provide a valid URL or leave it blank.', 'error')
                    all_tags = storage.get_all_tags(current_user.id)
                    gemini_configured = gemini_service.is_configured()
                    # Preserve user's entered data in the form, but keep recipe object for template compatibility
                    recipe_form_data = _create_form_data_object(recipe_data, recipe_id)
                    recipe_form_data.user_id = recipe.user_id  # Add user_id for template compatibility
                    return render_template('recipe_form.html', recipe=recipe_form_data, all_tags=all_tags, 
                                         new_tags=recipe_data.get('tags', []), gemini_configured=gemini_configured), 400
        
        storage.save_recipe(recipe_data, current_user.id, recipe_id=recipe_id)
        
        app.logger.info(f"Updated recipe {recipe_id}: {recipe.name}")
        flash(f'Recipe "{recipe.name}" updated successfully!', 'success')
        return redirect(url_for('recipe_view', recipe_id=recipe_id))
    
    except Exception as e:
        app.logger.error(f"Error updating recipe: {str(e)}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Show specific error message to help user understand what went wrong
        error_message = str(e)
        if 'PendingRollbackError' in error_message or 'Unknown column' in error_message:
            flash('Database error occurred. The database schema may need updating. Please contact support.', 'error')
        elif 'IntegrityError' in str(type(e)):
            flash('Data integrity error. Please check that all required fields are filled correctly.', 'error')
        else:
            # Show the actual error to help with debugging
            flash(f'Error updating recipe: {str(e)[:200]}', 'error')
        
        # Preserve user's entered data in the form
        try:
            all_tags = storage.get_all_tags(current_user.id)
        except:
            all_tags = {}
        gemini_configured = gemini_service.is_configured()
        recipe_form_data = _create_form_data_object(recipe_data, recipe_id)
        return render_template('recipe_form.html', recipe=recipe_form_data, all_tags=all_tags, 
                             new_tags=recipe_data.get('tags', []), gemini_configured=gemini_configured), 500


@app.route('/recipe/<int:recipe_id>/delete', methods=['POST'])
@login_required
def recipe_delete(recipe_id):
    """Delete a recipe."""
    # Check if recipe exists first
    recipe = storage.get_recipe(recipe_id, current_user.id)
    if not recipe:
        flash('Recipe not found or already deleted', 'error')
        return redirect(url_for('recipe_list'))
    
    success = storage.delete_recipe(recipe_id, current_user.id)
    
    if success:
        flash('Recipe deleted successfully', 'success')
    else:
        flash('Error deleting recipe or permission denied', 'error')
    
    return redirect(url_for('recipe_list'))


# ============================================================================
# Recipe Import Routes
# ============================================================================

@app.route('/api/recipe/import/url', methods=['POST'])
@login_required
def import_recipe_from_url():
    """Import recipe from URL."""
    if not gemini_service.is_configured():
        return jsonify({'success': False, 'error': 'Gemini API not configured'}), 500
    
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400
        
        success, recipe_data, error_msg = gemini_service.extract_from_url(url)
        
        if success and recipe_data:
            # Apply source validation and correction
            gemini_service._validate_and_correct_source(recipe_data)
            
            # For URL imports, the source URL is already set
            source = recipe_data.get('source', {})
            if not source.get('name'):
                source['name'] = 'Web Source'  # Default name for URL imports
            
            return jsonify({'success': True, 'recipe': recipe_data})
        else:
            return jsonify({'success': False, 'error': error_msg or 'Could not extract recipe'}), 400
    
    except Exception as e:
        app.logger.error(f"Error importing from URL: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/recipe/import/file', methods=['POST'])
@login_required
def import_recipe_from_file():
    """Import recipe from file."""
    if not gemini_service.is_configured():
        return jsonify({'success': False, 'error': 'Gemini API not configured'}), 500
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        filename = file.filename
        file_content = file.read()
        
        # Determine file type
        if filename.lower().endswith('.pdf'):
            success, recipe_data, error_msg = gemini_service.extract_from_pdf(file_content, filename)
        elif filename.lower().endswith(('.txt', '.text')):
            text_content = file_content.decode('utf-8', errors='ignore')
            success, recipe_data, error_msg = gemini_service.extract_from_text(text_content, filename)
        else:
            try:
                text_content = file_content.decode('utf-8', errors='ignore')
                success, recipe_data, error_msg = gemini_service.extract_from_text(text_content, filename)
            except Exception as e:
                return jsonify({'success': False, 'error': f'Unsupported file type'}), 400
        
        if success and recipe_data:
            # Apply source validation and correction
            gemini_service._validate_and_correct_source(recipe_data)
            
            # Check if this is an adapted recipe that needs source input
            source = recipe_data.get('source', {})
            original_source = source.get('original_source', {})
            
            # If there's an original source but no current source name, try smart detection
            if original_source.get('name') and not source.get('name'):
                app.logger.info("Attempting smart source detection for adapted recipe")
                detected_source = gemini_service.smart_source_detection(recipe_data)
                
                if detected_source:
                    source['name'] = detected_source['name']
                    source['url'] = detected_source['url']
                    app.logger.info(f"Smart detection found source: {detected_source['name']}")
                else:
                    # Mark as needing user input
                    recipe_data['_needs_source_input'] = True
                    app.logger.info("Smart detection failed, will prompt user for source")
            
            return jsonify({'success': True, 'recipe': recipe_data})
        else:
            return jsonify({'success': False, 'error': error_msg or 'Could not extract recipe'}), 400
    
    except Exception as e:
        app.logger.error(f"Error importing from file: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# Ingredient Autocomplete API
# ============================================================================

@app.route('/api/ingredients/search')
def ingredient_search():
    """Search ingredients for autocomplete."""
    query = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 20))
    
    results = storage.autocomplete_ingredients(query, limit)
    return jsonify(results)


# ============================================================================
# Favorite Routes
# ============================================================================

@app.route('/recipe/<int:recipe_id>/favorite', methods=['POST'])
@login_required
def recipe_favorite_toggle(recipe_id):
    """Toggle favorite status."""
    is_favorited = storage.toggle_favorite(current_user.id, recipe_id)
    
    if is_favorited:
        flash('Added to favorites!', 'success')
    else:
        flash('Removed from favorites', 'info')
    
    return redirect(url_for('recipe_view', recipe_id=recipe_id))


@app.route('/favorites')
@login_required
def favorites_list():
    """Show user's favorite recipes."""
    favorites = storage.get_user_favorites(current_user.id)
    return render_template('favorites_list.html', recipes=favorites)


# ============================================================================
# My Recipes
# ============================================================================

@app.route('/my-recipes')
@login_required
def my_recipes():
    """Show current user's recipes."""
    recipes = storage.get_user_recipes(current_user.id)
    return render_template('my_recipes.html', recipes=recipes)


# ============================================================================
# Email Sharing
# ============================================================================

@app.route('/recipe/<int:recipe_id>/email', methods=['GET', 'POST'])
@login_required
def recipe_email(recipe_id):
    """Send recipe via email."""
    user_id = current_user.id if current_user.is_authenticated else None
    recipe = storage.get_recipe(recipe_id, user_id)
    
    if not recipe:
        flash('Recipe not found', 'error')
        return redirect(url_for('recipe_list'))
    
    if not email_service.is_configured():
        flash('Email service is not configured', 'error')
        return redirect(url_for('recipe_view', recipe_id=recipe_id))
    
    if request.method == 'GET':
        return render_template('recipe_email.html', recipe=recipe)
    
    # POST - Send email
    recipient_email = request.form.get('recipient_email', '').strip()
    recipient_name = request.form.get('recipient_name', '').strip()
    custom_message = request.form.get('message', '').strip()
    
    if not recipient_email:
        flash('Recipient email is required', 'error')
        return render_template('recipe_email.html', recipe=recipe), 400
    
    try:
        # Convert recipe to dict for email service (which expects old format)
        recipe_dict = _recipe_to_dict(recipe)
        
        success, error_msg = email_service.send_recipe(
            recipe_dict,
            recipient_email,
            recipient_name,
            custom_message
        )
        
        if success:
            # Log the email
            storage.log_email_share(recipe_id, current_user.id, recipient_email, recipient_name, custom_message)
            
            # Return JSON response for AJAX handling with detailed popup
            return jsonify({
                'success': True,
                'message': 'Email sent successfully!',
                'recipient_name': recipient_name,
                'recipient_email': recipient_email,
                'custom_message': custom_message,
                'recipe_name': recipe.name
            })
        else:
            # Return JSON response for AJAX handling with error popup
            return jsonify({
                'success': False,
                'error': error_msg,
                'recipient_email': recipient_email
            }), 500
    
    except Exception as e:
        app.logger.error(f"Error emailing recipe: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error sending email: {str(e)}',
            'recipient_email': recipient_email
        }), 500


# ============================================================================
# Friend Management Routes
# ============================================================================

@app.route('/friends/find', methods=['GET', 'POST'])
@login_required
def friends_find():
    """Find friend by email and send friend request. Can also share recipe."""
    from db_models import User, FriendRequest, Friendship, Notification, Recipe, RecipeShare, PendingRecipeShare
    import secrets
    
    # Check if sharing a recipe
    recipe_id = request.args.get('recipe_id', type=int) or request.form.get('recipe_id', type=int)
    recipe = None
    if recipe_id:
        recipe = storage.get_recipe(recipe_id, current_user.id)
        if not recipe or recipe.user_id != current_user.id or recipe.visibility != 'public':
            recipe = None
            recipe_id = None
    
    if request.method == 'GET':
        return render_template('friends_find.html', recipe=recipe, recipe_id=recipe_id)
    
    # POST - Process friend request and/or recipe share
    email = request.form.get('email', '').strip().lower()
    
    if not email:
        flash('Email address is required', 'error')
        return render_template('friends_find.html', recipe=recipe, recipe_id=recipe_id), 400
    
    # Validate email format
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        flash('Please enter a valid email address', 'error')
        return render_template('friends_find.html', recipe=recipe, recipe_id=recipe_id), 400
    
    # Check if user is trying to friend themselves
    if email == current_user.email:
        flash('You cannot send a friend request to yourself', 'error')
        return render_template('friends_find.html', recipe=recipe, recipe_id=recipe_id), 400
    
    # Find user by email (without revealing if they exist)
    recipient = db.session.query(User).filter(User.email == email).first()
    
    if recipient:
        # User exists
        if current_user.is_friends_with(recipient.id):
            # Already friends - share recipe directly if provided
            if recipe_id:
                existing_share = db.session.query(RecipeShare).filter(
                    RecipeShare.recipe_id == recipe_id,
                    RecipeShare.shared_by_user_id == current_user.id,
                    RecipeShare.shared_with_user_id == recipient.id
                ).first()
                
                if not existing_share:
                    share = RecipeShare(
                        recipe_id=recipe_id,
                        shared_by_user_id=current_user.id,
                        shared_with_user_id=recipient.id
                    )
                    db.session.add(share)
                    
                    notification = Notification(
                        user_id=recipient.id,
                        notification_type='recipe_shared',
                        related_user_id=current_user.id,
                        recipe_id=recipe_id,
                        message=f"{current_user.display_name or current_user.username} shared a recipe with you: {recipe.name}"
                    )
                    db.session.add(notification)
                    db.session.commit()
                    flash(f'Recipe shared with {recipient.display_name or recipient.username}!', 'success')
                else:
                    flash('Recipe already shared with this friend', 'info')
                return redirect(url_for('recipe_view', recipe_id=recipe_id))
            else:
                flash('You are already friends with this user', 'info')
                return render_template('friends_find.html', recipe=recipe, recipe_id=recipe_id)
        
        # Check if request already exists
        existing_request = db.session.query(FriendRequest).filter(
            ((FriendRequest.sender_id == current_user.id) & (FriendRequest.recipient_id == recipient.id)) |
            ((FriendRequest.sender_id == recipient.id) & (FriendRequest.recipient_id == current_user.id))
        ).filter(FriendRequest.status == 'pending').first()
        
        if existing_request:
            if existing_request.sender_id == current_user.id:
                if recipe_id:
                    # Create pending share linked to existing request
                    existing_pending = db.session.query(PendingRecipeShare).filter(
                        PendingRecipeShare.recipe_id == recipe_id,
                        PendingRecipeShare.shared_by_user_id == current_user.id,
                        PendingRecipeShare.shared_with_user_id == recipient.id,
                        PendingRecipeShare.status == 'pending'
                    ).first()
                    
                    if not existing_pending:
                        pending_share = PendingRecipeShare(
                            recipe_id=recipe_id,
                            shared_by_user_id=current_user.id,
                            shared_with_user_id=recipient.id,
                            friend_request_id=existing_request.id,
                            status='pending'
                        )
                        db.session.add(pending_share)
                        db.session.commit()
                        flash('Friend request already sent. Recipe will be shared once accepted.', 'info')
                    else:
                        flash('Friend request already sent. Recipe share already pending.', 'info')
                    return redirect(url_for('recipe_view', recipe_id=recipe_id))
                else:
                    flash('You have already sent a friend request to this user', 'info')
                    return render_template('friends_find.html', recipe=recipe, recipe_id=recipe_id)
            else:
                flash('This user has already sent you a friend request. Please check your friend requests.', 'info')
                return render_template('friends_find.html', recipe=recipe, recipe_id=recipe_id)
        
        # Create friend request
        friend_request = FriendRequest(
            sender_id=current_user.id,
            recipient_id=recipient.id,
            status='pending'
        )
        db.session.add(friend_request)
        db.session.flush()
        
        # If sharing recipe, create pending share
        if recipe_id:
            pending_share = PendingRecipeShare(
                recipe_id=recipe_id,
                shared_by_user_id=current_user.id,
                shared_with_user_id=recipient.id,
                friend_request_id=friend_request.id,
                status='pending'
            )
            db.session.add(pending_share)
        
        # Create notification for recipient
        notification = Notification(
            user_id=recipient.id,
            notification_type='friend_request',
            related_user_id=current_user.id,
            message=f"{current_user.display_name or current_user.username} sent you a friend request"
        )
        db.session.add(notification)
        
        db.session.commit()
        
        app.logger.info(f"Friend request sent: {current_user.id} -> {recipient.id}")
        
        if recipe_id:
            flash('Friend request sent. Recipe will be shared once accepted.', 'success')
            return redirect(url_for('recipe_view', recipe_id=recipe_id))
        else:
            flash('If a user with that email exists, they will be notified of your friend request.', 'success')
            return redirect(url_for('friends_requests'))
    else:
        # User doesn't exist
        if recipe_id:
            # Ask if user wants to send recipe via email
            return render_template('friends_find.html', recipe=recipe, recipe_id=recipe_id, 
                                 email=email, show_email_form=True)
        else:
            # Regular friend request - always show success (security)
            flash('If a user with that email exists, they will be notified of your friend request.', 'success')
            return redirect(url_for('friends_requests'))


@app.route('/friends/find/send-email', methods=['POST'])
@login_required
def friends_find_send_email():
    """Send recipe to non-user via email."""
    from db_models import Recipe, PendingRecipeShare
    import secrets
    
    recipe_id = request.form.get('recipe_id', type=int)
    email = request.form.get('email', '').strip().lower()
    
    if not recipe_id or not email:
        flash('Missing recipe or email', 'error')
        return redirect(url_for('friends_find'))
    
    recipe = storage.get_recipe(recipe_id, current_user.id)
    if not recipe or recipe.user_id != current_user.id or recipe.visibility != 'public':
        flash('Invalid recipe', 'error')
        return redirect(url_for('recipe_list'))
    
    # Validate email format
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        flash('Invalid email address', 'error')
        return redirect(url_for('friends_find', recipe_id=recipe_id))
    
    # Create pending share with token
    token = secrets.token_urlsafe(32)
    pending_share = PendingRecipeShare(
        recipe_id=recipe_id,
        shared_by_user_id=current_user.id,
        recipient_email=email,
        token=token,
        status='pending'
    )
    db.session.add(pending_share)
    db.session.commit()
    
    # Send email with protected link
    try:
        from email_service import email_service
        from db_models import Recipe
        recipe_obj = db.session.query(Recipe).filter(Recipe.id == recipe_id).first()
        if recipe_obj:
            recipe_url = url_for('recipe_view_token', recipe_id=recipe_id, token=token, _external=True)
            custom_message = f"I'd like to share this recipe with you. Please create an account to view it.\n\nView recipe: {recipe_url}"
            success, error_msg = email_service.send_recipe(
                recipe=recipe_obj,
                recipient_email=email,
                recipient_name='',
                custom_message=custom_message
            )
            if success:
                flash('Recipe link sent via email!', 'success')
            else:
                flash('Recipe share created, but email sending failed. Please try again later.', 'warning')
    except Exception as e:
        app.logger.error(f"Error sending email share: {e}")
        flash('Recipe share created, but email sending failed. Please try again later.', 'warning')
    
    return redirect(url_for('recipe_view', recipe_id=recipe_id))


@app.route('/recipe/<int:recipe_id>/view/<token>', methods=['GET'])
def recipe_view_token(recipe_id, token):
    """View recipe via token (for non-users who received email)."""
    from db_models import Recipe, PendingRecipeShare, User
    
    # Find pending share with this token
    pending_share = db.session.query(PendingRecipeShare).filter(
        PendingRecipeShare.recipe_id == recipe_id,
        PendingRecipeShare.token == token,
        PendingRecipeShare.status == 'pending'
    ).first()
    
    if not pending_share:
        flash('Invalid or expired recipe link', 'error')
        return redirect(url_for('home'))
    
    recipe = storage.get_recipe(recipe_id, None)
    if not recipe or recipe.visibility != 'public':
        flash('Recipe not found or not accessible', 'error')
        return redirect(url_for('home'))
    
    # If user is logged in and matches the recipient email, link the pending share
    if current_user.is_authenticated:
        if pending_share.recipient_email and pending_share.recipient_email.lower() == current_user.email.lower():
            # Link pending share to user account
            pending_share.shared_with_user_id = current_user.id
            db.session.commit()
            # Redirect to pending shares page
            return redirect(url_for('pending_shares'))
    
    # Show recipe with registration prompt
    return render_template('recipe_view_token.html', recipe=recipe, token=token, 
                         recipient_email=pending_share.recipient_email)


@app.route('/pending-shares', methods=['GET'])
@login_required
def pending_shares():
    """View and manage pending recipe shares."""
    from db_models import PendingRecipeShare, Recipe, User
    
    pending_shares_list = current_user.get_pending_shares_received()
    
    # Get full details
    shares_with_details = []
    for pending_share in pending_shares_list:
        recipe = db.session.query(Recipe).filter(Recipe.id == pending_share.recipe_id).first()
        sender = db.session.query(User).filter(User.id == pending_share.shared_by_user_id).first()
        if recipe:
            shares_with_details.append({
                'pending_share': pending_share,
                'recipe': recipe,
                'sender': sender
            })
    
    return render_template('pending_shares.html', shares_with_details=shares_with_details)


@app.route('/pending-share/<int:pending_share_id>/accept', methods=['POST'])
@login_required
def pending_share_accept(pending_share_id):
    """Accept a pending recipe share."""
    from db_models import PendingRecipeShare, RecipeShare, Notification, Recipe, User
    
    pending_share = db.session.query(PendingRecipeShare).filter(
        PendingRecipeShare.id == pending_share_id,
        PendingRecipeShare.shared_with_user_id == current_user.id,
        PendingRecipeShare.status == 'pending'
    ).first()
    
    if not pending_share:
        flash('Pending share not found', 'error')
        return redirect(url_for('pending_shares'))
    
    # Check if recipe share already exists
    existing_share = db.session.query(RecipeShare).filter(
        RecipeShare.recipe_id == pending_share.recipe_id,
        RecipeShare.shared_by_user_id == pending_share.shared_by_user_id,
        RecipeShare.shared_with_user_id == current_user.id
    ).first()
    
    if not existing_share:
        # Create actual share
        share = RecipeShare(
            recipe_id=pending_share.recipe_id,
            shared_by_user_id=pending_share.shared_by_user_id,
            shared_with_user_id=current_user.id
        )
        db.session.add(share)
        
        # Create notification
        recipe = db.session.query(Recipe).filter(Recipe.id == pending_share.recipe_id).first()
        sender = db.session.query(User).filter(User.id == pending_share.shared_by_user_id).first()
        if recipe and sender:
            notification = Notification(
                user_id=current_user.id,
                notification_type='recipe_shared',
                related_user_id=pending_share.shared_by_user_id,
                recipe_id=pending_share.recipe_id,
                message=f"{sender.display_name or sender.username} shared a recipe with you: {recipe.name}"
            )
            db.session.add(notification)
    
    # Mark pending share as accepted
    pending_share.status = 'accepted'
    db.session.commit()
    
    flash('Recipe share accepted!', 'success')
    return redirect(url_for('pending_shares'))


@app.route('/pending-share/<int:pending_share_id>/reject', methods=['POST'])
@login_required
def pending_share_reject(pending_share_id):
    """Reject a pending recipe share."""
    from db_models import PendingRecipeShare
    
    pending_share = db.session.query(PendingRecipeShare).filter(
        PendingRecipeShare.id == pending_share_id,
        PendingRecipeShare.shared_with_user_id == current_user.id,
        PendingRecipeShare.status == 'pending'
    ).first()
    
    if not pending_share:
        flash('Pending share not found', 'error')
        return redirect(url_for('pending_shares'))
    
    # Mark pending share as rejected
    pending_share.status = 'rejected'
    db.session.commit()
    
    flash('Recipe share rejected', 'info')
    return redirect(url_for('pending_shares'))


@app.route('/friends/requests')
@login_required
def friends_requests():
    """View pending friend requests."""
    from db_models import FriendRequest, User
    
    received_requests = current_user.get_pending_received_requests()
    sent_requests = current_user.get_pending_sent_requests()
    
    # Get user details for requests
    received_with_users = []
    for req in received_requests:
        sender = db.session.query(User).filter(User.id == req.sender_id).first()
        received_with_users.append({
            'request': req,
            'user': sender
        })
    
    sent_with_users = []
    for req in sent_requests:
        recipient = db.session.query(User).filter(User.id == req.recipient_id).first()
        sent_with_users.append({
            'request': req,
            'user': recipient
        })
    
    return render_template(
        'friends_requests.html',
        received_requests=received_with_users,
        sent_requests=sent_with_users
    )


@app.route('/friends/requests/<int:request_id>/accept', methods=['POST'])
@login_required
def friends_request_accept(request_id):
    """Accept a friend request and auto-share any pending recipes."""
    from db_models import FriendRequest, Friendship, Notification, RecipeShare, PendingRecipeShare, Recipe, User
    
    friend_request = db.session.query(FriendRequest).filter(
        FriendRequest.id == request_id,
        FriendRequest.recipient_id == current_user.id,
        FriendRequest.status == 'pending'
    ).first()
    
    if not friend_request:
        flash('Friend request not found or already processed', 'error')
        return redirect(url_for('friends_requests'))
    
    # Create friendship (ensure user1_id < user2_id)
    user1_id = min(friend_request.sender_id, friend_request.recipient_id)
    user2_id = max(friend_request.sender_id, friend_request.recipient_id)
    
    # Check if friendship already exists
    existing_friendship = db.session.query(Friendship).filter(
        Friendship.user1_id == user1_id,
        Friendship.user2_id == user2_id
    ).first()
    
    if not existing_friendship:
        friendship = Friendship(
            user1_id=user1_id,
            user2_id=user2_id
        )
        db.session.add(friendship)
    
    # Update request status
    friend_request.status = 'accepted'
    
    # Auto-share any pending recipes linked to this friend request
    pending_shares = db.session.query(PendingRecipeShare).filter(
        PendingRecipeShare.friend_request_id == friend_request.id,
        PendingRecipeShare.status == 'pending'
    ).all()
    
    shared_count = 0
    for pending_share in pending_shares:
        # Check if recipe share already exists
        existing_share = db.session.query(RecipeShare).filter(
            RecipeShare.recipe_id == pending_share.recipe_id,
            RecipeShare.shared_by_user_id == pending_share.shared_by_user_id,
            RecipeShare.shared_with_user_id == current_user.id
        ).first()
        
        if not existing_share:
            # Create actual share
            share = RecipeShare(
                recipe_id=pending_share.recipe_id,
                shared_by_user_id=pending_share.shared_by_user_id,
                shared_with_user_id=current_user.id
            )
            db.session.add(share)
            shared_count += 1
            
            # Create notification
            recipe = db.session.query(Recipe).filter(Recipe.id == pending_share.recipe_id).first()
            if recipe:
                notification = Notification(
                    user_id=current_user.id,
                    notification_type='recipe_shared',
                    related_user_id=pending_share.shared_by_user_id,
                    recipe_id=pending_share.recipe_id,
                    message=f"{db.session.query(User).filter(User.id == pending_share.shared_by_user_id).first().display_name or db.session.query(User).filter(User.id == pending_share.shared_by_user_id).first().username} shared a recipe with you: {recipe.name}"
                )
                db.session.add(notification)
        
        # Mark pending share as accepted
        pending_share.status = 'accepted'
    
    # Mark notification as read
    notification = db.session.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.notification_type == 'friend_request',
        Notification.related_user_id == friend_request.sender_id,
        Notification.read == False
    ).first()
    
    if notification:
        notification.read = True
    
    db.session.commit()
    
    app.logger.info(f"Friend request accepted: {friend_request.sender_id} <-> {friend_request.recipient_id}")
    if shared_count > 0:
        flash(f'Friend request accepted! {shared_count} recipe(s) have been shared with you.', 'success')
    else:
        flash('Friend request accepted!', 'success')
    return redirect(url_for('friends_requests'))


@app.route('/friends/requests/<int:request_id>/reject', methods=['POST'])
@login_required
def friends_request_reject(request_id):
    """Reject a friend request."""
    from db_models import FriendRequest, Notification
    
    friend_request = db.session.query(FriendRequest).filter(
        FriendRequest.id == request_id,
        FriendRequest.recipient_id == current_user.id,
        FriendRequest.status == 'pending'
    ).first()
    
    if not friend_request:
        flash('Friend request not found or already processed', 'error')
        return redirect(url_for('friends_requests'))
    
    # Update request status (don't notify sender)
    friend_request.status = 'rejected'
    
    # Mark notification as read
    notification = db.session.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.notification_type == 'friend_request',
        Notification.related_user_id == friend_request.sender_id,
        Notification.read == False
    ).first()
    
    if notification:
        notification.read = True
    
    db.session.commit()
    
    app.logger.info(f"Friend request rejected: {friend_request.sender_id} -> {friend_request.recipient_id}")
    flash('Friend request rejected', 'info')
    return redirect(url_for('friends_requests'))


@app.route('/friends/requests/<int:request_id>/cancel', methods=['POST'])
@login_required
def friends_request_cancel(request_id):
    """Cancel a sent friend request."""
    from db_models import FriendRequest
    
    friend_request = db.session.query(FriendRequest).filter(
        FriendRequest.id == request_id,
        FriendRequest.sender_id == current_user.id,
        FriendRequest.status == 'pending'
    ).first()
    
    if not friend_request:
        flash('Friend request not found or already processed', 'error')
        return redirect(url_for('friends_requests'))
    
    # Update request status
    friend_request.status = 'cancelled'
    db.session.commit()
    
    app.logger.info(f"Friend request cancelled: {current_user.id} -> {friend_request.recipient_id}")
    flash('Friend request cancelled', 'info')
    return redirect(url_for('friends_requests'))


@app.route('/friends')
@login_required
def friends_list():
    """List all friends."""
    from db_models import User, Friendship
    
    friends = current_user.get_friends()
    
    # Get friendship creation dates
    friendships = db.session.query(Friendship).filter(
        (Friendship.user1_id == current_user.id) | (Friendship.user2_id == current_user.id)
    ).all()
    
    friend_dates = {}
    for friendship in friendships:
        other_user_id = friendship.user2_id if friendship.user1_id == current_user.id else friendship.user1_id
        friend_dates[other_user_id] = friendship.created_at
    
    # Create list with friendship dates
    friends_with_dates = []
    for friend in friends:
        friends_with_dates.append({
            'friend': friend,
            'friendship_date': friend_dates.get(friend.id)
        })
    
    return render_template('friends_list.html', friends_data=friends_with_dates)


@app.route('/friends/<int:friend_id>/remove', methods=['POST'])
@login_required
def friends_remove(friend_id):
    """Remove a friend."""
    from db_models import Friendship
    
    # Find friendship (check both user1 and user2)
    friendship = db.session.query(Friendship).filter(
        ((Friendship.user1_id == current_user.id) & (Friendship.user2_id == friend_id)) |
        ((Friendship.user1_id == friend_id) & (Friendship.user2_id == current_user.id))
    ).first()
    
    if not friendship:
        flash('Friendship not found', 'error')
        return redirect(url_for('friends_list'))
    
    # Delete friendship (recipe shares remain as per requirements)
    db.session.delete(friendship)
    db.session.commit()
    
    app.logger.info(f"Friendship removed: {current_user.id} <-> {friend_id}")
    flash('Friend removed', 'info')
    return redirect(url_for('friends_list'))


# ============================================================================
# Recipe Sharing Routes
# ============================================================================

@app.route('/recipe/<int:recipe_id>/share', methods=['GET'])
@login_required
def recipe_share(recipe_id):
    """Redirect to find friend page with recipe to share."""
    recipe = storage.get_recipe(recipe_id, current_user.id)
    
    if not recipe:
        flash('Recipe not found', 'error')
        return redirect(url_for('recipe_list'))
    
    # Check if user owns the recipe
    if recipe.user_id != current_user.id:
        flash('You can only share recipes you own', 'error')
        return redirect(url_for('recipe_view', recipe_id=recipe_id))
    
    # Check if recipe is public (required for sharing)
    if recipe.visibility != 'public':
        flash('Only public recipes can be shared with friends', 'error')
        return redirect(url_for('recipe_view', recipe_id=recipe_id))
    
    # Redirect to find friend page with recipe_id
    return redirect(url_for('friends_find', recipe_id=recipe_id))


@app.route('/recipes/share/select', methods=['GET', 'POST'])
@login_required
def recipes_share_select():
    """Select recipes to share (checkbox interface)."""
    from db_models import Recipe
    
    if request.method == 'GET':
        # Get all user's public recipes
        public_recipes = storage.get_user_recipes(current_user.id, visibility='public')
        # Filter out soft-deleted
        public_recipes = [r for r in public_recipes if r.deleted_at is None]
        
        return render_template('recipes_share_select.html', recipes=public_recipes)
    
    # POST - Process selected recipes
    selected_recipe_ids = request.form.getlist('recipe_ids')
    
    if not selected_recipe_ids:
        flash('Please select at least one recipe to share', 'error')
        public_recipes = storage.get_user_recipes(current_user.id, visibility='public')
        public_recipes = [r for r in public_recipes if r.deleted_at is None]
        return render_template('recipes_share_select.html', recipes=public_recipes), 400
    
    # Validate recipe IDs
    recipe_ids = [int(rid) for rid in selected_recipe_ids]
    user_recipe_ids = {r.id for r in storage.get_user_recipes(current_user.id, visibility='public')}
    
    if not all(rid in user_recipe_ids for rid in recipe_ids):
        flash('Invalid recipe selected', 'error')
        return redirect(url_for('recipes_share_select'))
    
    # Redirect to share page with recipe IDs
    recipe_ids_str = ','.join(str(rid) for rid in recipe_ids)
    return redirect(url_for('recipes_share', recipe_ids=recipe_ids_str))


@app.route('/recipes/share', methods=['GET', 'POST'])
@login_required
def recipes_share():
    """Share selected recipes with friends via email."""
    from db_models import Recipe, User, FriendRequest, Friendship, RecipeShare, PendingRecipeShare, Notification
    import secrets
    
    # Get recipe IDs from query parameter or form
    recipe_ids_str = request.args.get('recipe_ids') or request.form.get('recipe_ids', '')
    
    if not recipe_ids_str:
        flash('No recipes selected', 'error')
        return redirect(url_for('recipes_share_select'))
    
    try:
        recipe_ids = [int(rid.strip()) for rid in recipe_ids_str.split(',') if rid.strip()]
    except ValueError:
        flash('Invalid recipe IDs', 'error')
        return redirect(url_for('recipes_share_select'))
    
    # Validate recipes belong to user and are public
    recipes = []
    for recipe_id in recipe_ids:
        recipe = storage.get_recipe(recipe_id, current_user.id)
        if not recipe or recipe.user_id != current_user.id or recipe.visibility != 'public':
            flash('Invalid recipe selected', 'error')
            return redirect(url_for('recipes_share_select'))
        recipes.append(recipe)
    
    if request.method == 'GET':
        return render_template('recipes_share.html', recipes=recipes, recipe_ids=recipe_ids_str)
    
    # POST - Process sharing
    emails_str = request.form.get('emails', '').strip()
    
    if not emails_str:
        flash('Please enter at least one email address', 'error')
        return render_template('recipes_share.html', recipes=recipes, recipe_ids=recipe_ids_str), 400
    
    # Parse emails (comma or newline separated)
    emails = [e.strip().lower() for e in emails_str.replace('\n', ',').split(',') if e.strip()]
    
    if not emails:
        flash('Please enter at least one valid email address', 'error')
        return render_template('recipes_share.html', recipes=recipes, recipe_ids=recipe_ids_str), 400
    
    # Validate email format
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    valid_emails = []
    for email in emails:
        if re.match(email_pattern, email):
            if email != current_user.email:
                valid_emails.append(email)
            else:
                flash(f'Cannot share with yourself ({email})', 'warning')
        else:
            flash(f'Invalid email address: {email}', 'warning')
    
    if not valid_emails:
        flash('No valid email addresses to share with', 'error')
        return render_template('recipes_share.html', recipes=recipes, recipe_ids=recipe_ids_str), 400
    
    # Process each email
    friend_requests_created = 0
    pending_shares_created = 0
    email_shares_created = 0
    direct_shares_created = 0
    
    for email in valid_emails:
        recipient = db.session.query(User).filter(User.email == email).first()
        
        if recipient:
            # User exists - check if friend
            if current_user.is_friends_with(recipient.id):
                # Already friends - share directly
                for recipe in recipes:
                    # Check if already shared
                    existing_share = db.session.query(RecipeShare).filter(
                        RecipeShare.recipe_id == recipe.id,
                        RecipeShare.shared_by_user_id == current_user.id,
                        RecipeShare.shared_with_user_id == recipient.id
                    ).first()
                    
                    if not existing_share:
                        share = RecipeShare(
                            recipe_id=recipe.id,
                            shared_by_user_id=current_user.id,
                            shared_with_user_id=recipient.id
                        )
                        db.session.add(share)
                        direct_shares_created += 1
                        
                        # Create notification
                        notification = Notification(
                            user_id=recipient.id,
                            notification_type='recipe_shared',
                            related_user_id=current_user.id,
                            recipe_id=recipe.id,
                            message=f"{current_user.display_name or current_user.username} shared a recipe with you: {recipe.name}"
                        )
                        db.session.add(notification)
            else:
                # Not friends - create friend request and pending shares
                # Check if friend request already exists
                existing_request = db.session.query(FriendRequest).filter(
                    ((FriendRequest.sender_id == current_user.id) & (FriendRequest.recipient_id == recipient.id)) |
                    ((FriendRequest.sender_id == recipient.id) & (FriendRequest.recipient_id == current_user.id))
                ).filter(FriendRequest.status == 'pending').first()
                
                if not existing_request:
                    friend_request = FriendRequest(
                        sender_id=current_user.id,
                        recipient_id=recipient.id,
                        status='pending'
                    )
                    db.session.add(friend_request)
                    db.session.flush()
                    friend_requests_created += 1
                else:
                    friend_request = existing_request
                
                # Create pending shares for all recipes
                for recipe in recipes:
                    # Check if pending share already exists
                    existing_pending = db.session.query(PendingRecipeShare).filter(
                        PendingRecipeShare.recipe_id == recipe.id,
                        PendingRecipeShare.shared_by_user_id == current_user.id,
                        PendingRecipeShare.shared_with_user_id == recipient.id,
                        PendingRecipeShare.status == 'pending'
                    ).first()
                    
                    if not existing_pending:
                        pending_share = PendingRecipeShare(
                            recipe_id=recipe.id,
                            shared_by_user_id=current_user.id,
                            shared_with_user_id=recipient.id,
                            friend_request_id=friend_request.id,
                            status='pending'
                        )
                        db.session.add(pending_share)
                        pending_shares_created += 1
                
                # Create notification for friend request
                if not existing_request:
                    notification = Notification(
                        user_id=recipient.id,
                        notification_type='friend_request',
                        related_user_id=current_user.id,
                        message=f"{current_user.display_name or current_user.username} sent you a friend request"
                    )
                    db.session.add(notification)
        else:
            # User doesn't exist - create email share with token
            for recipe in recipes:
                token = secrets.token_urlsafe(32)
                pending_share = PendingRecipeShare(
                    recipe_id=recipe.id,
                    shared_by_user_id=current_user.id,
                    recipient_email=email,
                    token=token,
                    status='pending'
                )
                db.session.add(pending_share)
                email_shares_created += 1
                
                # Send email with protected link
                try:
                    from email_service import email_service
                    recipe_url = url_for('recipe_view_token', recipe_id=recipe.id, token=token, _external=True)
                    custom_message = f"I'd like to share this recipe with you. Please create an account to view it.\n\nView recipe: {recipe_url}"
                    success, error_msg = email_service.send_recipe(
                        recipe=recipe,
                        recipient_email=email,
                        recipient_name='',
                        custom_message=custom_message
                    )
                    if not success:
                        app.logger.error(f"Error sending email share: {error_msg}")
                except Exception as e:
                    app.logger.error(f"Error sending email share: {e}")
                    # Continue even if email fails
    
    db.session.commit()
    
    # Create success message
    messages = []
    if direct_shares_created > 0:
        messages.append(f"Shared {direct_shares_created} recipe(s) directly")
    if friend_requests_created > 0:
        messages.append(f"Sent {friend_requests_created} friend request(s). Recipe(s) will be shared when accepted.")
    if pending_shares_created > 0:
        messages.append(f"Created {pending_shares_created} pending share(s)")
    if email_shares_created > 0:
        messages.append(f"Sent {email_shares_created} email share(s)")
    
    if messages:
        flash(' | '.join(messages), 'success')
    else:
        flash('No new shares created', 'info')
    
    return redirect(url_for('recipe_list'))


@app.route('/recipe/<int:recipe_id>/shares', methods=['GET'])
@login_required
def recipe_view_shares(recipe_id):
    """View who a recipe is shared with."""
    from db_models import Recipe, RecipeShare, User
    
    recipe = storage.get_recipe(recipe_id, current_user.id)
    
    if not recipe:
        flash('Recipe not found', 'error')
        return redirect(url_for('recipe_list'))
    
    # Check if user owns the recipe
    if recipe.user_id != current_user.id:
        flash('You can only view shares for recipes you own', 'error')
        return redirect(url_for('recipe_view', recipe_id=recipe_id))
    
    # Get shares
    shares = db.session.query(RecipeShare).filter(
        RecipeShare.recipe_id == recipe_id,
        RecipeShare.shared_by_user_id == current_user.id
    ).all()
    
    shares_with_users = []
    for share in shares:
        friend = db.session.query(User).filter(User.id == share.shared_with_user_id).first()
        if friend:
            shares_with_users.append({
                'share': share,
                'friend': friend
            })
    
    return render_template(
        'recipe_shares.html',
        recipe=recipe,
        shares=shares_with_users
    )


@app.route('/friends/<int:friend_id>/share-all', methods=['POST'])
@login_required
def friends_share_all(friend_id):
    """Share all public recipes with a friend."""
    from db_models import Recipe, RecipeShare, Notification, Friendship
    
    # Verify friendship
    if not current_user.is_friends_with(friend_id):
        flash('You can only share recipes with friends', 'error')
        return redirect(url_for('friends_list'))
    
    # Get all user's public recipes
    recipes = db.session.query(Recipe).filter(
        Recipe.user_id == current_user.id,
        Recipe.visibility == 'public',
        Recipe.deleted_at.is_(None)  # Only non-deleted recipes
    ).all()
    
    if not recipes:
        flash('You have no public recipes to share', 'info')
        return redirect(url_for('friends_list'))
    
    # Get already shared recipes
    existing_shares = db.session.query(RecipeShare).filter(
        RecipeShare.shared_by_user_id == current_user.id,
        RecipeShare.shared_with_user_id == friend_id
    ).all()
    already_shared_recipe_ids = {share.recipe_id for share in existing_shares}
    
    # Create shares for recipes not already shared
    new_shares = []
    for recipe in recipes:
        if recipe.id not in already_shared_recipe_ids:
            share = RecipeShare(
                recipe_id=recipe.id,
                shared_by_user_id=current_user.id,
                shared_with_user_id=friend_id
            )
            db.session.add(share)
            new_shares.append(share)
    
    # Create notification
    if new_shares:
        from db_models import User
        friend = db.session.query(User).filter(User.id == friend_id).first()
        notification = Notification(
            user_id=friend_id,
            notification_type='recipe_shared',
            related_user_id=current_user.id,
            message=f"{current_user.display_name or current_user.username} shared {len(new_shares)} recipe(s) with you"
        )
        db.session.add(notification)
    
    db.session.commit()
    
    app.logger.info(f"Shared {len(new_shares)} recipes with friend {friend_id} by user {current_user.id}")
    flash(f'Shared {len(new_shares)} recipe(s) with friend!', 'success')
    return redirect(url_for('friends_list'))


@app.route('/recipe/<int:recipe_id>/unshare-self', methods=['POST'])
@login_required
def recipe_unshare_self(recipe_id):
    """Remove a shared recipe from own view (recipient action)."""
    from db_models import RecipeShare
    
    # Find share where current user is the recipient
    share = db.session.query(RecipeShare).filter(
        RecipeShare.recipe_id == recipe_id,
        RecipeShare.shared_with_user_id == current_user.id
    ).first()
    
    if not share:
        flash('Shared recipe not found', 'error')
        return redirect(url_for('recipe_list'))
    
    # Delete the share (removes from recipient's view)
    db.session.delete(share)
    db.session.commit()
    
    app.logger.info(f"User {current_user.id} removed shared recipe {recipe_id} from their view")
    flash('Recipe removed from your recipes', 'info')
    return redirect(url_for('recipe_list'))


# ============================================================================
# Tag Management
# ============================================================================

@app.route('/tags')
@login_required
def tag_manager():
    """Redirect to admin tag management (admin-only feature)."""
    if current_user.is_admin:
        return redirect(url_for('admin_tags'))
    else:
        flash('Tag management is an admin-only feature', 'error')
        return redirect(url_for('recipe_list'))


# ============================================================================
# Helper Functions
# ============================================================================

def _validate_recipe_data(recipe_data, visibility=None):
    """
    Validate recipe data and return (is_valid, errors, warnings).
    
    Args:
        recipe_data: Dictionary with recipe information
        visibility: Recipe visibility ('public', 'private', 'incomplete'). If None, extracted from recipe_data.
    
    Returns:
        Tuple of (is_valid, errors, warnings)
        - is_valid: Boolean indicating if recipe can be saved
        - errors: List of error messages (blocking)
        - warnings: List of warning messages (non-blocking)
    """
    errors = []
    warnings = []
    
    # Extract visibility if not provided
    if visibility is None:
        visibility = recipe_data.get('visibility', 'incomplete')
    
    # Name validation - must be at least 3 characters after removing whitespace
    name = recipe_data.get('name', '').strip()
    if not name:
        errors.append("Please provide a valid recipe name")
    elif len(name) < 3:
        errors.append("Recipe name must be at least 3 characters long")
    
    # Instructions validation - must have non-blank characters
    instructions = recipe_data.get('instructions', '').strip()
    if not instructions:
        errors.append("Please provide recipe instructions")
    
    # Source validation - conditional based on visibility
    source = recipe_data.get('source', {})
    has_name = source.get('name', '').strip()
    has_author = source.get('author', '').strip()
    has_url = source.get('url', '').strip()
    has_issue = source.get('issue', '').strip()
    
    if visibility == 'public':
        # For public recipes: source information is REQUIRED (errors)
        if not has_name:
            errors.append("Source name is required for public recipes (e.g., cookbook title, website name, or publication)")
        
        # Must have either author OR URL (or both)
        if not (has_author or has_url):
            errors.append("Must provide either recipe author or source URL (or both) for public recipes")
    else:
        # For private/incomplete recipes: source information is optional (warnings)
        if not has_name and not (has_author or has_url):
            warnings.append("Source information is recommended. If you make this recipe public later, you'll need to provide: (1) Source name, and (2) either Author or URL.")
        elif not has_name:
            warnings.append("Source name is recommended. If you make this recipe public later, a source name will be required.")
        elif not (has_author or has_url):
            warnings.append("Either recipe author or source URL is recommended. If you make this recipe public later, at least one will be required.")
    
    # Validate source issue field format if provided
    if has_issue:
        # Check if issue contains publisher/year pattern
        import re
        if not re.search(r'(Press|Publishing|Books|Inc|Co\.|LLC).*\d{4}|\d{4}', has_issue):
            # This is a warning, not an error - some sources might have different formats
            logger.info(f"Source issue format might be incorrect: '{has_issue}'")
    
    # URL validation - must be a valid URL if provided (applies to all recipes)
    if has_url:
        if not (has_url.startswith('http://') or has_url.startswith('https://')):
            errors.append("Please enter a valid URL (must start with http:// or https://)")
    
    # Ingredient validation
    ingredients = recipe_data.get('ingredients', [])
    
    # Count non-empty ingredients
    non_empty_ingredients = [ing for ing in ingredients if not ing.get('is_empty', False)]
    
    # Check minimum 3 non-empty ingredients
    if len(non_empty_ingredients) < 3:
        errors.append("Recipes must have at least three ingredients")
    
    # Validate each non-empty ingredient
    for i, ing in enumerate(ingredients, 1):
        if ing.get('is_empty', False):
            continue  # Skip empty ingredients
        
        description = ing.get('description', '').strip()
        amount = ing.get('amount', '').strip()
        
        if not description:
            errors.append(f"Ingredient {i}: Please enter a valid ingredient description")
        
        # Amount must be numerical (1, 1.5, 1/2, 1 1/2, etc.) or a range (1-2, 1/2-1, etc.)
        if amount and not _is_valid_amount(amount):
            errors.append(f"Ingredient {i}: Please enter a valid numerical amount (e.g., 1, 1.5, 1/2, 1 1/2) or range (e.g., 1-2, 1/2-1)")
    
    return len(errors) == 0, errors, warnings


def _is_valid_amount(amount: str) -> bool:
    """
    Validate amount is a number, fraction, or range.
    Supports Unicode fractions and various formats.
    
    Valid formats:
    - Simple numbers: 1, 2.5, 10
    - Fractions: 1/2, 3/4
    - Mixed numbers: 1 1/2, 2 3/4
    - Unicode fractions: ½, ¾
    - Ranges: 1-2, 1/2-1, 1-1 1/2 (with or without spaces around hyphen)
    """
    import re
    
    amount = amount.strip()
    if not amount:
        return True
    
    # Convert Unicode fractions to ASCII equivalents
    unicode_fractions = {
        '½': '1/2', '⅓': '1/3', '⅔': '2/3', '¼': '1/4', '¾': '3/4',
        '⅕': '1/5', '⅖': '2/5', '⅗': '3/5', '⅘': '4/5',
        '⅙': '1/6', '⅚': '5/6', '⅐': '1/7', '⅛': '1/8', '⅜': '3/8',
        '⅝': '5/8', '⅞': '7/8', '⅑': '1/9', '⅒': '1/10'
    }
    
    # Replace Unicode fractions
    for unicode_frac, ascii_frac in unicode_fractions.items():
        amount = amount.replace(unicode_frac, ascii_frac)
    
    # Normalize various dash types to regular hyphen for range detection
    # En-dash (–), em-dash (—), minus sign (−) → regular hyphen (-)
    amount = amount.replace('–', '-').replace('—', '-').replace('−', '-')
    
    # Check if this is a range (contains hyphen, but not at the start)
    # Allow spaces around hyphen: "1-2" or "1 - 2"
    if '-' in amount and not amount.startswith('-'):
        # Split on hyphen and strip whitespace from both parts
        parts = [part.strip() for part in amount.split('-', 1)]  # Split only on first hyphen
        
        if len(parts) == 2 and parts[0] and parts[1]:
            # Both parts must be valid amounts
            min_val = _parse_amount_value(parts[0])
            max_val = _parse_amount_value(parts[1])
            
            if min_val is not None and max_val is not None:
                # Validate both are in range and min < max
                if 0 <= min_val <= 1000 and 0 <= max_val <= 1000 and min_val < max_val:
                    return True
        
        return False
    
    # Not a range, validate as single amount
    value = _parse_amount_value(amount)
    if value is not None:
        return 0 <= value <= 1000
    
    return False


def _parse_amount_value(amount: str) -> float:
    """
    Parse an amount string to a numeric value.
    Returns None if the amount cannot be parsed.
    
    Supports:
    - Simple numbers: 1, 2.5
    - Fractions: 1/2, 3/4
    - Mixed numbers: 1 1/2, 2 3/4
    """
    import re
    
    amount = amount.strip()
    if not amount:
        return None
    
    # Check for simple number (integer or decimal)
    if re.match(r'^\d+\.?\d*$', amount):
        return float(amount)
    
    # Check for fraction (e.g., 1/2, 3/4)
    if re.match(r'^\d+/\d+$', amount):
        parts = amount.split('/')
        numerator = int(parts[0])
        denominator = int(parts[1])
        if denominator == 0:
            return None
        return numerator / denominator
    
    # Check for mixed number (e.g., 1 1/2)
    if re.match(r'^\d+\s+\d+/\d+$', amount):
        parts = amount.split()
        whole = int(parts[0])
        frac_parts = parts[1].split('/')
        numerator = int(frac_parts[0])
        denominator = int(frac_parts[1])
        if denominator == 0:
            return None
        return whole + (numerator / denominator)
    
    return None


def _format_recipe_text(text):
    """
    Format recipe text to add blank lines between numbered steps and paragraphs.
    
    For instructions:
    - Adds blank line before each numbered step (Step 1, 1., etc.)
    - Adds blank lines between paragraphs
    
    For notes:
    - Adds blank lines between paragraphs
    """
    if not text:
        return text
    
    import re
    
    # Normalize line endings first
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Split into lines for processing
    lines = text.split('\n')
    
    # Step 1: Add blank line before numbered steps
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this line starts a numbered step
        if re.match(r'^\s*(Step \d+|^\d+[.)]|\d+\))', line):
            # Add blank line before this numbered step (unless it's the first line)
            if i > 0 and result and result[-1].strip():
                result.append('')
            result.append(line)
        else:
            result.append(line)
        
        i += 1
    
    # Step 2: Add blank lines between paragraphs
    # Join back, then identify paragraph boundaries
    text = '\n'.join(result)
    lines = text.split('\n')
    
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        result.append(line)
        
        # If this line ends a paragraph (punctuation), add blank line if next is start of new paragraph
        if line.strip() and i < len(lines) - 1:
            next_line = lines[i + 1]
            # Check if line ends with sentence-ending punctuation
            if line.strip().endswith(('.', '!', '?', ':')):
                # Check if next line starts a new sentence (capital letter)
                if next_line.strip() and next_line.strip()[0].isupper():
                    result.append('')
        
        i += 1
    
    # Join and clean up multiple blank lines
    formatted = '\n'.join(result)
    formatted = re.sub(r'\n{3,}', '\n\n', formatted)
    
    # Strip leading/trailing whitespace
    return formatted.strip()
    

def _trim_empty_ingredients_from_end(ingredients):
    """Remove empty ingredients that are not followed by non-empty ingredients."""
    if not ingredients:
        return ingredients
    
    # Work backwards to find the last non-empty ingredient
    last_non_empty_index = -1
    for i in range(len(ingredients) - 1, -1, -1):
        description = ingredients[i].get('description', '').strip()
        if description:
            last_non_empty_index = i
            break
    
    # If no non-empty ingredients found, return empty list
    if last_non_empty_index == -1:
        return []
    
    # Return ingredients up to and including the last non-empty one
    return ingredients[:last_non_empty_index + 1]


def _parse_recipe_form(form_data):
    """Parse recipe data from form submission."""
    name = form_data.get('name', '').strip()
    description = form_data.get('description', '').strip()
    instructions = form_data.get('instructions', '').strip()
    notes = form_data.get('notes', '').strip()
    
    # Clean up instructions - remove carriage returns and normalize line endings
    instructions = instructions.replace('\r\n', '\n').replace('\r', '\n')
    
    # Parse source
    source = {
        'name': form_data.get('source_name', '').strip(),
        'url': form_data.get('source_url', '').strip(),
        'author': form_data.get('source_author', '').strip(),
        'issue': form_data.get('source_issue', '').strip()
    }
    
    # Parse ingredients - preserve empty positions
    ingredients = []
    ingredient_count = 0
    
    while f'ingredient_description_{ingredient_count}' in form_data:
        description = form_data.get(f'ingredient_description_{ingredient_count}', '').strip()
        amount = form_data.get(f'ingredient_amount_{ingredient_count}', '').strip()
        unit = form_data.get(f'ingredient_unit_{ingredient_count}', '').strip()
        
        # Always add ingredient position, even if empty
        ingredients.append({
            'amount': amount,
            'unit': unit,
            'description': description,
            'is_empty': not description  # Mark empty ingredients
        })
        
        ingredient_count += 1
    
    # Trim empty ingredients from the end of the list
    ingredients = _trim_empty_ingredients_from_end(ingredients)
    
    # Parse tags - support both comma and space delimiters, normalize to lowercase
    tags = []
    tag_input = form_data.get('tags', '').strip()
    if tag_input:
        # Split by comma first, then by space for each part
        # This handles: "tag1, tag2 tag3" -> ["tag1", "tag2", "tag3"]
        parts = tag_input.split(',')
        for part in parts:
            # Split each comma-separated part by spaces
            space_separated = part.strip().split()
            for tag in space_separated:
                tag = tag.strip().lower()  # Normalize to lowercase
                if tag and tag not in tags:
                    tags.append(tag)
    
    return {
        'name': name,
        'description': description,
        'instructions': instructions,
        'notes': notes,
        'source': source,
        'ingredients': ingredients,
        'tags': tags,
        'visibility': form_data.get('visibility', 'incomplete')
    }


def _create_form_data_object(recipe_data, recipe_id=None):
    """
    Create a mock recipe object from parsed form data for template rendering.
    Used when validation fails to preserve user input.
    
    Args:
        recipe_data: Parsed form data dictionary
        recipe_id: Optional recipe ID (for edits), None for new recipes
    """
    from types import SimpleNamespace
    
    return SimpleNamespace(
        id=recipe_id,  # None for new recipes, actual ID for edits
        name=recipe_data.get('name', ''),
        description=recipe_data.get('description', ''),
        instructions=recipe_data.get('instructions', ''),
        notes=recipe_data.get('notes', ''),
        prep_time=recipe_data.get('prep_time'),
        cook_time=recipe_data.get('cook_time'),
        servings=recipe_data.get('servings'),
        visibility=recipe_data.get('visibility', 'incomplete'),
        ingredients=recipe_data.get('ingredients', []),
        tags=[],
        source=SimpleNamespace(
            source_name=recipe_data.get('source', {}).get('name', ''),
            author=recipe_data.get('source', {}).get('author', ''),
            source_url=recipe_data.get('source', {}).get('url', ''),
            issue=recipe_data.get('source', {}).get('issue', '')
        ) if recipe_data.get('source') else None
    )


def _recipe_to_dict(recipe):
    """Convert SQLAlchemy Recipe to dictionary (for email service compatibility)."""
    return {
        'id': recipe.id,
        'name': recipe.name,
        'description': recipe.description or '',
        'ingredients': [ri.to_dict() for ri in recipe.recipe_ingredients],
        'instructions': recipe.instructions,
        'notes': recipe.notes or '',
        'tags': [tag.name for tag in recipe.tags],
        'source': {
            'name': recipe.source.source_name if recipe.source else '',
            'url': recipe.source.source_url if recipe.source else '',
            'author': recipe.source.author if recipe.source else '',
            'issue': recipe.source.issue if recipe.source else ''
        } if recipe.source else {},
        'created_at': recipe.created_at.isoformat() if recipe.created_at else '',
        'updated_at': recipe.updated_at.isoformat() if recipe.updated_at else ''
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    app.logger.warning(f"404 Not Found: {request.url}")
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    import traceback
    import sys
    
    app.logger.error("=" * 70)
    app.logger.error("INTERNAL SERVER ERROR (500)")
    app.logger.error("=" * 70)
    app.logger.error(f"Error type: {type(e).__name__}")
    app.logger.error(f"Error message: {str(e)}")
    app.logger.error(f"Request URL: {request.url}")
    app.logger.error(f"Request method: {request.method}")
    app.logger.error(f"Request args: {dict(request.args)}")
    app.logger.error(f"Request form: {dict(request.form)}")
    
    # Get the exception info
    exc_type, exc_value, exc_traceback = sys.exc_info()
    if exc_traceback:
        app.logger.error("Full traceback:")
        app.logger.error("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
    else:
        app.logger.error("Traceback (from exception object):")
        app.logger.error(traceback.format_exc())
    
    app.logger.error("=" * 70)
    
    return render_template('500.html'), 500


# Add a before_request handler to log all requests
@app.before_request
def log_request_info():
    """Log request information for debugging."""
    try:
        app.logger.debug(f"Request: {request.method} {request.url}")
        app.logger.debug(f"Remote address: {request.remote_addr}")
        try:
            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                app.logger.debug(f"Authenticated user: {current_user.username} (ID: {current_user.id})")
            else:
                app.logger.debug("Anonymous user")
        except Exception:
            app.logger.debug("Could not determine user status")
    except Exception as e:
        app.logger.warning(f"Error in log_request_info: {e}")


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    try:
        logger.debug("=" * 70)
        logger.debug("Starting Flask development server...")
        logger.debug("=" * 70)
        app.logger.info(f"Starting Recipe Editor (MySQL) on {config.HOST}:{config.PORT}")
        app.logger.info(f"Debug mode: {config.DEBUG}")
        app.logger.debug(f"Database: {config.MYSQL_DATABASE} on {config.MYSQL_HOST}:{config.MYSQL_PORT}")
        app.logger.debug(f"Log file: {config.LOG_FILE}")
        
        # Final connection test before starting
        with app.app_context():
            try:
                from db_config import test_connection
                success, msg = test_connection()
                if success:
                    app.logger.debug(f"Pre-startup database check: {msg}")
                else:
                    app.logger.error(f"Pre-startup database check failed: {msg}")
                    app.logger.error("Application will start but database operations may fail")
            except Exception as e:
                app.logger.warning(f"Could not perform pre-startup database check: {e}")
        
        app.logger.info("=" * 70)
        app.logger.info("Application startup complete - ready to accept requests")
        app.logger.info("=" * 70)
        
        app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Fatal error starting application: {e}", exc_info=True)
        sys.exit(1)

