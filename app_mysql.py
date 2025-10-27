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
import config
from db_models import db
from mysql_storage import MySQLStorage, init_storage
from auth import init_auth, authenticate_user, create_user as create_user_account, change_password, update_user_profile
from gemini_service import gemini_service
from email_service import email_service
from admin_routes import register_admin_routes

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SQLALCHEMY_ECHO'] = config.SQLALCHEMY_ECHO

# Initialize database
db.init_app(app)

# Initialize authentication
init_auth(app)

# Initialize storage
with app.app_context():
    storage = init_storage(db.session)

# Register admin routes
register_admin_routes(app)

# Configure logging
if not os.path.exists(config.LOGS_DIR):
    os.makedirs(config.LOGS_DIR)

file_handler = RotatingFileHandler(
    config.LOG_FILE,
    maxBytes=1024 * 1024,
    backupCount=10
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))
console_handler.setLevel(logging.INFO)

logger = logging.getLogger()
logger.addHandler(file_handler)
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)

app.logger.info("Recipe Editor (MySQL) application starting")


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
            bio = request.form.get('bio', '').strip()
            
            update_user_profile(current_user, display_name=display_name, bio=bio)
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
    
    return render_template('profile.html')


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
    user_id = current_user.id if current_user.is_authenticated else None
    
    # Get filter parameters
    selected_tags = request.args.getlist('tags')
    match_all = request.args.get('match_all') == 'true'
    
    # Get all tags
    all_tags = storage.get_all_tags()
    
    # Get recipes (filtered or all)
    if selected_tags:
        recipes = storage.filter_recipes_by_tags(selected_tags, match_all, user_id)
    else:
        recipes = storage.get_all_recipes(user_id)
    
    return render_template(
        'recipe_list.html',
        recipes=recipes,
        all_tags=all_tags,
        selected_tags=selected_tags,
        match_all=match_all
    )


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
        all_tags = storage.get_all_tags()
        gemini_configured = gemini_service.is_configured()
        return render_template('recipe_form.html', recipe=None, all_tags=all_tags, 
                             new_tags=[], gemini_configured=gemini_configured)
    
    # POST - Create new recipe
    try:
        recipe_data = _parse_recipe_form(request.form)
        
        # Validate recipe data
        is_valid, errors = _validate_recipe_data(recipe_data)
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            all_tags = storage.get_all_tags()
            gemini_configured = gemini_service.is_configured()
            return render_template('recipe_form.html', recipe=None, all_tags=all_tags, 
                                 new_tags=[], gemini_configured=gemini_configured), 400
        
        # Validate visibility permission
        visibility = recipe_data.get('visibility', 'incomplete')
        if visibility == 'public' and not current_user.can_publish_public_recipes():
            flash('You do not have permission to publish public recipes', 'error')
            all_tags = storage.get_all_tags()
            gemini_configured = gemini_service.is_configured()
            return render_template('recipe_form.html', recipe=None, all_tags=all_tags, 
                                 new_tags=[], gemini_configured=gemini_configured), 403
        
        recipe = storage.save_recipe(recipe_data, current_user.id)
        
        flash(f'Recipe "{recipe.name}" created successfully!', 'success')
        app.logger.info(f"Created new recipe {recipe.id}: {recipe.name}")
        
        return redirect(url_for('recipe_view', recipe_id=recipe.id))
    
    except Exception as e:
        app.logger.error(f"Error creating recipe: {str(e)}")
        flash('Error creating recipe. Please try again.', 'error')
        all_tags = storage.get_all_tags()
        gemini_configured = gemini_service.is_configured()
        return render_template('recipe_form.html', recipe=None, all_tags=all_tags, 
                             new_tags=[], gemini_configured=gemini_configured), 500


@app.route('/recipe/<int:recipe_id>/edit', methods=['GET', 'POST'])
@login_required
def recipe_edit(recipe_id):
    """Edit an existing recipe."""
    recipe = storage.get_recipe(recipe_id, current_user.id)
    
    if not recipe:
        flash('Recipe not found', 'error')
        return redirect(url_for('recipe_list'))
    
    if recipe.user_id != current_user.id:
        flash('You do not have permission to edit this recipe', 'error')
        return redirect(url_for('recipe_view', recipe_id=recipe_id))
    
    if request.method == 'GET':
        all_tags = storage.get_all_tags()
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
            all_tags = storage.get_all_tags()
            gemini_configured = gemini_service.is_configured()
            return render_template('recipe_form.html', recipe=recipe, all_tags=all_tags, 
                                 new_tags=[], gemini_configured=gemini_configured), 400
        
        # Validate visibility permission
        visibility = recipe_data.get('visibility', 'incomplete')
        if visibility == 'public' and not current_user.can_publish_public_recipes():
            flash('You do not have permission to publish public recipes', 'error')
            all_tags = storage.get_all_tags()
            gemini_configured = gemini_service.is_configured()
            return render_template('recipe_form.html', recipe=recipe, all_tags=all_tags, 
                                 new_tags=[], gemini_configured=gemini_configured), 403
        
        storage.save_recipe(recipe_data, current_user.id, recipe_id=recipe_id)
        
        flash(f'Recipe "{recipe.name}" updated successfully!', 'success')
        return redirect(url_for('recipe_view', recipe_id=recipe_id))
    
    except Exception as e:
        app.logger.error(f"Error updating recipe: {str(e)}")
        flash('Error updating recipe. Please try again.', 'error')
        return redirect(url_for('recipe_edit', recipe_id=recipe_id))


@app.route('/recipe/<int:recipe_id>/delete', methods=['POST'])
@login_required
def recipe_delete(recipe_id):
    """Delete a recipe."""
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

@app.route('/tags', methods=['GET', 'POST'])
def tag_manager():
    """Manage tags."""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'edit':
            old_name = request.form.get('old_name', '').strip().upper()
            new_name = request.form.get('new_name', '').strip().upper()
            
            success, message = storage.update_tag_name(old_name, new_name)
            flash(message, 'success' if success else 'error')
        
        elif action == 'delete':
            tag_name = request.form.get('tag_name', '').strip().upper()
            success, message = storage.delete_tag(tag_name)
            flash(message, 'success' if success else 'error')
    
    all_tags = storage.get_all_tags()
    sorted_tags = sorted(all_tags.items(), key=lambda x: x[0])
    
    return render_template('tag_manager.html', tags=sorted_tags)


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
    
    # Source validation - at least one field must have non-blank content
    source = recipe_data.get('source', {})
    has_name = source.get('name', '').strip()
    has_author = source.get('author', '').strip()
    has_url = source.get('url', '').strip()
    
    if not (has_name or has_author or has_url):
        errors.append("Please provide the recipe's provenance (source name, author, or URL)")
    
    # URL validation - must be a valid URL if provided
    if has_url:
        if not (has_url.startswith('http://') or has_url.startswith('https://')):
            errors.append("Please enter a valid URL (must start with http:// or https://)")
    
    # Ingredient validation
    ingredients = recipe_data.get('ingredients', [])
    
    # Check minimum 3 ingredients
    if len(ingredients) < 3:
        errors.append("Recipes must have at least three ingredients")
    
    # Validate each ingredient
    for i, ing in enumerate(ingredients, 1):
        description = ing.get('description', '').strip()
        amount = ing.get('amount', '').strip()
        
        # Each ingredient must have both description and amount
        if not description and not amount:
            continue  # Skip completely empty ingredients
        
        if not description:
            errors.append(f"Ingredient {i}: Please enter a valid ingredient description")
        
        if not amount:
            errors.append(f"Ingredient {i}: Please enter a valid ingredient amount")
        
        # Amount must be numerical (1, 1.5, 1/2, 1 1/2, etc.)
        if amount and not _is_valid_amount(amount):
            errors.append(f"Ingredient {i}: Please enter a valid numerical amount (e.g., 1, 1.5, 1/2, 1 1/2)")
    
    return len(errors) == 0, errors


def _is_valid_amount(amount: str) -> bool:
    """
    Validate amount is a number or fraction.
    Reuses validation logic from models.py
    """
    import re
    
    amount = amount.strip()
    if not amount:
        return True
    
    # Check for simple number (integer or decimal)
    if re.match(r'^\d+\.?\d*$', amount):
        value = float(amount)
        return 0 <= value <= 1000
    
    # Check for fraction (e.g., 1/2, 3/4)
    if re.match(r'^\d+/\d+$', amount):
        parts = amount.split('/')
        numerator = int(parts[0])
        denominator = int(parts[1])
        if denominator == 0:
            return False
        value = numerator / denominator
        return 0 <= value <= 1000
    
    # Check for mixed number (e.g., 1 1/2)
    if re.match(r'^\d+\s+\d+/\d+$', amount):
        parts = amount.split()
        whole = int(parts[0])
        frac_parts = parts[1].split('/')
        numerator = int(frac_parts[0])
        denominator = int(frac_parts[1])
        if denominator == 0:
            return False
        value = whole + (numerator / denominator)
        return 0 <= value <= 1000
    
    return False


def _parse_recipe_form(form_data):
    """Parse recipe data from form submission."""
    name = form_data.get('name', '').strip()
    description = form_data.get('description', '').strip()
    instructions = form_data.get('instructions', '').strip()
    notes = form_data.get('notes', '').strip()
    
    # Parse source
    source = {
        'name': form_data.get('source_name', '').strip(),
        'url': form_data.get('source_url', '').strip(),
        'author': form_data.get('source_author', '').strip(),
        'issue': form_data.get('source_issue', '').strip()
    }
    
    # Parse ingredients
    ingredients = []
    ingredient_count = 0
    
    while f'ingredient_description_{ingredient_count}' in form_data:
        description = form_data.get(f'ingredient_description_{ingredient_count}', '').strip()
        
        if description:
            amount = form_data.get(f'ingredient_amount_{ingredient_count}', '').strip()
            unit = form_data.get(f'ingredient_unit_{ingredient_count}', '').strip()
            
            ingredients.append({
                'amount': amount,
                'unit': unit,
                'description': description
            })
        
        ingredient_count += 1
    
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
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    app.logger.error(f"Internal server error: {str(e)}")
    return render_template('500.html'), 500


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    app.logger.info(f"Starting Recipe Editor (MySQL) on {config.HOST}:{config.PORT}")
    app.logger.info(f"Debug mode: {config.DEBUG}")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)

