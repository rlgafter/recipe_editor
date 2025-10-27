"""
Admin routes for user type management.
"""
import logging
import sys
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from db_models import db

# Fix password hashing compatibility for older Python versions
import hashlib

# Check if scrypt is available in hashlib
if hasattr(hashlib, 'scrypt'):
    # Modern Python with scrypt support - use default Werkzeug behavior
    from werkzeug.security import generate_password_hash
else:
    # Older Python without scrypt - force compatible method
    from werkzeug.security import generate_password_hash as _original_generate_password_hash
    def generate_password_hash(password, method='pbkdf2:sha256', salt_length=16):
        """Compatible password hashing for systems without scrypt support."""
        # Always use pbkdf2:sha256 for maximum compatibility
        return _original_generate_password_hash(password, method='pbkdf2:sha256', salt_length=salt_length)

logger = logging.getLogger(__name__)


def require_admin(f):
    """Decorator to require admin access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth_login'))
        if not current_user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('recipe_list'))
        return f(*args, **kwargs)
    return decorated_function


def register_admin_routes(app):
    """Register admin routes with Flask app."""
    
    @app.route('/admin')
    @login_required
    @require_admin
    def admin_dashboard():
        """Admin dashboard - redirect to enhanced admin users page."""
        return redirect(url_for('admin_users'))
    
    @app.route('/admin/users')
    @login_required
    @require_admin
    def admin_users():
        """User management page."""
        from db_models import User, UserStats
        
        logger.info("=== ADMIN USERS DEBUG START ===")
        logger.info(f"Current user: {current_user.username} (ID: {current_user.id})")
        logger.info(f"Request args: {dict(request.args)}")
        
        # Get search and filter parameters
        search = request.args.get('search', '').strip()
        page = int(request.args.get('page', 1))
        per_page = 20
        
        logger.info(f"Search: '{search}', Page: {page}, Per page: {per_page}")
        
        # Build query
        query = User.query
        logger.info(f"Base query: {query}")
        
        # Apply search filter
        if search:
            query = query.filter(
                db.or_(
                    User.username.contains(search),
                    User.email.contains(search),
                    User.display_name.contains(search)
                )
            )
            logger.info(f"Query after search filter: {query}")
        
        # Get total count for pagination
        total = query.count()
        pages = (total + per_page - 1) // per_page
        logger.info(f"Total users matching query: {total}, Pages: {pages}")
        
        # Get users with pagination
        pagination = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        users = pagination.items
        
        logger.info(f"Users fetched: {len(users)}")
        for i, user in enumerate(users):
            logger.info(f"User {i+1}: ID={user.id}, Username={user.username}, Email={user.email}, Active={user.is_active}, Admin={user.is_admin}, Created={user.created_at}")
        
        # Get user statistics
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        admin_users = User.query.filter_by(is_admin=True).count()
        verified_users = User.query.filter_by(email_verified=True).count()
        
        logger.info(f"Statistics - Total: {total_users}, Active: {active_users}, Admin: {admin_users}, Verified: {verified_users}")
        
        # Calculate user stats for each user
        for user in users:
            # Get recipe count for each user
            user.recipe_count = len(user.recipes.all())
            user.public_recipe_count = len([r for r in user.recipes.all() if r.visibility == 'public'])
            logger.info(f"User {user.username} - Recipe count: {user.recipe_count}, Public recipes: {user.public_recipe_count}")
        
        logger.info("=== ADMIN USERS DEBUG END ===")
        
        return render_template('admin_users.html',
                             users=users,
                             page=page,
                             pages=pages,
                             total=total,
                             search=search,
                             total_users=total_users,
                             active_users=active_users,
                             admin_users=admin_users,
                             verified_users=verified_users)
    
    @app.route('/admin/users/activate', methods=['POST'])
    @login_required
    @require_admin
    def admin_activate_user():
        """Activate a user."""
        from db_models import User
        
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID required'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        user.is_active = True
        db.session.commit()
        
        logger.info(f"User {user.username} activated by admin {current_user.username}")
        return jsonify({'success': True, 'message': 'User activated successfully'})
    
    @app.route('/admin/users/deactivate', methods=['POST'])
    @login_required
    @require_admin
    def admin_deactivate_user():
        """Deactivate a user."""
        from db_models import User
        
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID required'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Don't allow deactivating yourself
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot deactivate your own account'}), 400
        
        user.is_active = False
        db.session.commit()
        
        logger.info(f"User {user.username} deactivated by admin {current_user.username}")
        return jsonify({'success': True, 'message': 'User deactivated successfully'})
    
    @app.route('/admin/users/toggle-admin', methods=['POST'])
    @login_required
    @require_admin
    def admin_toggle_admin():
        """Toggle admin status for a user."""
        from db_models import User
        
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID required'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Don't allow removing admin from yourself
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot change your own admin status'}), 400
        
        user.is_admin = not user.is_admin
        db.session.commit()
        
        status = 'granted' if user.is_admin else 'removed'
        logger.info(f"Admin status {status} for user {user.username} by admin {current_user.username}")
        return jsonify({'success': True, 'message': f'Admin status {status} successfully'})
    
    @app.route('/admin/users/update', methods=['POST'])
    @login_required
    @require_admin
    def admin_update_user():
        """Update user role and status."""
        from db_models import User
        
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID required'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Don't allow removing admin from yourself
        if user.id == current_user.id and not data.get('is_admin', False):
            return jsonify({'success': False, 'message': 'Cannot remove your own admin privileges'}), 400
        
        try:
            # Update fields
            if 'is_admin' in data:
                user.is_admin = bool(data['is_admin'])
            
            if 'is_active' in data:
                user.is_active = bool(data['is_active'])
            
            if 'email_verified' in data:
                user.email_verified = bool(data['email_verified'])
            
            if 'account_setup_completed' in data:
                user.account_setup_completed = bool(data['account_setup_completed'])
            
            if 'can_publish_public' in data:
                user.can_publish_public = bool(data['can_publish_public'])
            
            db.session.commit()
            
            logger.info(f"User {user.username} updated by admin {current_user.username}")
            return jsonify({'success': True, 'message': 'User updated successfully'})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating user: {str(e)}")
            return jsonify({'success': False, 'message': f'Error updating user: {str(e)}'}), 500
    
    @app.route('/admin/users/create', methods=['POST'])
    @login_required
    @require_admin
    def admin_create_user():
        """Create a new user with password setup flow."""
        from db_models import User
        from datetime import datetime, timedelta
        import secrets
        
        logger.info("=== USER CREATION START ===")
        logger.info(f"Form data: {dict(request.form)}")
        
        # Get form data (NO PASSWORD field)
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        display_name = request.form.get('display_name', '').strip()
        is_admin = request.form.get('is_admin') == '1'
        email_verified = request.form.get('email_verified') == '1'
        
        logger.info(f"Creating user: {username}, {email}")
        
        # Validation
        errors = []
        
        if not username or len(username) < 3 or len(username) > 50:
            errors.append('Username must be 3-50 characters long')
        
        if not email or '@' not in email:
            errors.append('Valid email address is required')
        
        # Check for existing username
        if User.query.filter_by(username=username).first():
            errors.append('Username already exists')
        
        # Check for existing email
        if User.query.filter_by(email=email).first():
            errors.append('Email address already exists')
        
        if errors:
            flash('; '.join(errors), 'error')
            logger.info("=== USER CREATION END (VALIDATION FAILED) ===")
            return redirect(url_for('admin_users'))
        
        try:
            # Generate secure token for password setup
            setup_token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            # Create user with temp password hash and setup token
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(secrets.token_urlsafe(32)),  # Random temp password
                display_name=display_name or None,
                is_admin=is_admin,
                email_verified=email_verified,
                is_active=False,  # Inactive until password is set
                password_setup_token=setup_token,
                password_setup_expires=expires_at,
                account_setup_completed=False
            )
            
            db.session.add(user)
            db.session.commit()
            
            logger.info(f"User created: ID={user.id}, Username={user.username}")
            
            # Send welcome email with password setup link
            from email_service import email_service
            success, error_msg = email_service.send_password_setup_email(
                user.email,
                user.display_name or user.username,
                setup_token
            )
            
            if success:
                logger.info(f"Welcome email sent to {user.email}")
                flash(f'User "{username}" created successfully! A welcome email with password setup instructions has been sent.', 'success')
            else:
                logger.error(f"Failed to send welcome email: {error_msg}")
                flash(f'User "{username}" created but email could not be sent: {error_msg}', 'warning')
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            flash('Error creating user. Please try again.', 'error')
        
        logger.info("=== USER CREATION END ===")
        return redirect(url_for('admin_users'))
    
    logger.info("Admin routes registered successfully")
