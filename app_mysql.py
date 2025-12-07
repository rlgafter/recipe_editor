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
            # Auto-login
            login_user(user)
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
@app.route('/recipes')
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
        selected_tags = request.args.getlist('tags')
        match_all = request.args.get('match_all') == 'true'
        
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
        
        app.logger.debug("Rendering template...")
        try:
            return render_template(
                'recipe_list.html',
                recipes=recipes,
                all_tags=all_tags,
                selected_tags=selected_tags,
                match_all=match_all,
                search_term=search_term
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
def recipe_view(recipe_id):
    """Display a single recipe."""
    user_id = current_user.id if current_user.is_authenticated else None
    recipe = storage.get_recipe(recipe_id, user_id)
    
    if not recipe:
        flash('Recipe not found or you do not have permission to view it', 'error')
        return redirect(url_for('recipe_list'))
    
    # Increment view count
    storage.increment_view_count(recipe_id)
    
    # Check if favorited (for authenticated users)
    is_favorited = False
    if current_user.is_authenticated:
        is_favorited = storage.is_favorited(current_user.id, recipe_id)
    
    # Get submitter information
    from db_models import User
    submitter = db.session.query(User).filter(User.id == recipe.user_id).first()
    
    email_configured = email_service.is_configured()
    
    return render_template(
        'recipe_view.html',
        recipe=recipe,
        submitter=submitter,
        is_favorited=is_favorited,
        email_configured=email_configured
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
        
        # Validate recipe data
        is_valid, errors = _validate_recipe_data(recipe_data)
        app.logger.info(f"Validation result: {'PASS' if is_valid else 'FAIL'}")
        if errors:
            app.logger.info(f"Validation errors: {errors}")
        
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
        visibility = recipe_data.get('visibility', 'incomplete')
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
        
        # Validate recipe data
        is_valid, errors = _validate_recipe_data(recipe_data)
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            all_tags = storage.get_all_tags(current_user.id)
            gemini_configured = gemini_service.is_configured()
            # Preserve user's entered data in the form
            recipe_form_data = _create_form_data_object(recipe_data, recipe_id)
            return render_template('recipe_form.html', recipe=recipe_form_data, all_tags=all_tags, 
                                 new_tags=recipe_data.get('tags', []), gemini_configured=gemini_configured), 400
        
        # Validate visibility permission
        visibility = recipe_data.get('visibility', 'incomplete')
        if visibility == 'public' and not current_user.can_publish_public_recipes():
            flash('You do not have permission to publish public recipes', 'error')
            all_tags = storage.get_all_tags(current_user.id)
            gemini_configured = gemini_service.is_configured()
            # Preserve user's entered data in the form
            recipe_form_data = _create_form_data_object(recipe_data, recipe_id)
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
                    # Preserve user's entered data in the form
                    recipe_form_data = _create_form_data_object(recipe_data)
                    recipe_form_data.id = recipe_id  # Keep the recipe ID for the form action
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

def _validate_recipe_data(recipe_data):
    """
    Validate recipe data and return (is_valid, errors).
    """
    errors = []
    
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
    
    # Source validation - name is REQUIRED, plus author OR URL
    source = recipe_data.get('source', {})
    has_name = source.get('name', '').strip()
    has_author = source.get('author', '').strip()
    has_url = source.get('url', '').strip()
    has_issue = source.get('issue', '').strip()
    
    # Source name is always required
    if not has_name:
        errors.append("Source name is required (e.g., cookbook title, website name, or publication)")
    
    # Must have either author OR URL (or both)
    if not (has_author or has_url):
        errors.append("Must provide either recipe author or source URL (or both)")
    
    # Validate source issue field format if provided
    if has_issue:
        # Check if issue contains publisher/year pattern
        import re
        if not re.search(r'(Press|Publishing|Books|Inc|Co\.|LLC).*\d{4}|\d{4}', has_issue):
            # This is a warning, not an error - some sources might have different formats
            logger.info(f"Source issue format might be incorrect: '{has_issue}'")
    
    # URL validation - must be a valid URL if provided
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
    
    return len(errors) == 0, errors


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
    
    # Parse tags
    tags = []
    tag_input = form_data.get('tags', '').strip()
    if tag_input:
        tags = [tag.strip() for tag in tag_input.split(',') if tag.strip()]
    
    # Check for individual tag checkboxes
    for key in form_data:
        if key.startswith('tag_'):
            tag_name = key[4:]
            if tag_name and tag_name not in tags:
                tags.append(tag_name)
    
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

