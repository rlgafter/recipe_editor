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
    
    @app.route('/admin/recipes')
    @login_required
    @require_admin
    def admin_recipes():
        """Admin recipe management page."""
        from db_models import Recipe, User
        
        logger.info("=== ADMIN RECIPES DEBUG START ===")
        logger.info(f"Current user: {current_user.username} (ID: {current_user.id})")
        logger.info(f"Request args: {dict(request.args)}")
        
        # Get search and filter parameters
        search = request.args.get('search', '').strip()
        user_filter = request.args.get('user', '').strip()
        visibility_filter = request.args.get('visibility', '').strip()
        page = int(request.args.get('page', 1))
        per_page = 20
        
        logger.info(f"Search: '{search}', User: '{user_filter}', Visibility: '{visibility_filter}', Page: {page}")
        
        # Build query
        query = Recipe.query
        logger.info(f"Base query: {query}")
        
        # Apply search filter
        if search:
            query = query.filter(
                db.or_(
                    Recipe.name.contains(search),
                    Recipe.description.contains(search)
                )
            )
            logger.info(f"Query after search filter: {query}")
        
        # Apply user filter
        if user_filter:
            query = query.filter(Recipe.user_id == user_filter)
            logger.info(f"Query after user filter: {query}")
        
        # Apply visibility filter
        if visibility_filter:
            query = query.filter(Recipe.visibility == visibility_filter)
            logger.info(f"Query after visibility filter: {query}")
        
        # Get total count for pagination
        total = query.count()
        pages = (total + per_page - 1) // per_page
        logger.info(f"Total recipes matching query: {total}, Pages: {pages}")
        
        # Get recipes with pagination
        pagination = query.order_by(Recipe.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        recipes = pagination.items
        
        logger.info(f"Recipes fetched: {len(recipes)}")
        for i, recipe in enumerate(recipes):
            logger.info(f"Recipe {i+1}: ID={recipe.id}, Name={recipe.name}, User ID={recipe.user_id}, Visibility={recipe.visibility}, Created={recipe.created_at}")
        
        # Get all users for filter dropdown
        all_users = User.query.order_by(User.username).all()
        
        # Get recipe statistics
        total_recipes = Recipe.query.count()
        public_recipes = Recipe.query.filter_by(visibility='public').count()
        private_recipes = Recipe.query.filter_by(visibility='private').count()
        incomplete_recipes = Recipe.query.filter_by(visibility='incomplete').count()
        
        logger.info(f"Statistics - Total: {total_recipes}, Public: {public_recipes}, Private: {private_recipes}, Incomplete: {incomplete_recipes}")
        
        logger.info("=== ADMIN RECIPES DEBUG END ===")
        
        return render_template('admin_recipes.html',
                             recipes=recipes,
                             page=page,
                             pages=pages,
                             total=total,
                             search=search,
                             user_filter=user_filter,
                             visibility_filter=visibility_filter,
                             all_users=all_users,
                             total_recipes=total_recipes,
                             public_recipes=public_recipes,
                             private_recipes=private_recipes,
                             incomplete_recipes=incomplete_recipes)
    
    @app.route('/admin/recipes/<int:recipe_id>/delete', methods=['POST'])
    @login_required
    @require_admin
    def admin_delete_recipe(recipe_id):
        """Admin delete recipe (bypasses ownership checks) and cleanup orphaned tags."""
        from db_models import Recipe, Tag
        
        recipe = Recipe.query.get(recipe_id)
        if not recipe:
            flash('Recipe not found or already deleted', 'error')
            return redirect(url_for('admin_recipes'))
        
        recipe_name = recipe.name
        
        # Delete the recipe (cascade will remove recipe_tags associations)
        db.session.delete(recipe)
        db.session.commit()
        
        # Clean up orphaned tags (tags with no recipes)
        orphaned_tags = Tag.query.filter(
            ~Tag.recipes.any()
        ).all()
        
        if orphaned_tags:
            tag_names = [tag.name for tag in orphaned_tags]
            for tag in orphaned_tags:
                db.session.delete(tag)
            db.session.commit()
            logger.info(f"Admin {current_user.username} deleted recipe {recipe_id}: {recipe_name} and cleaned up {len(orphaned_tags)} orphaned tags: {tag_names}")
        else:
            logger.info(f"Admin {current_user.username} deleted recipe {recipe_id}: {recipe_name}")
        
        flash(f'Recipe "{recipe_name}" deleted successfully', 'success')
        
        return redirect(url_for('admin_recipes'))
    
    @app.route('/admin/tags')
    @login_required
    @require_admin
    def admin_tags():
        """Admin tag management page."""
        from db_models import Tag, User
        from sqlalchemy import or_, and_, func
        
        logger.info("=== ADMIN TAGS DEBUG START ===")
        logger.info(f"Current user: {current_user.username} (ID: {current_user.id})")
        logger.info(f"Request args: {dict(request.args)}")
        
        # Get filter and sort parameters
        search = request.args.get('search', '').strip()
        scope_filter = request.args.get('scope', '').strip()  # 'system' or 'personal'
        user_filter = request.args.get('user', '').strip()    # user_id
        sort_by = request.args.get('sort_by', 'name')  # Column to sort by
        sort_order = request.args.get('sort_order', 'asc')  # 'asc' or 'desc'
        page = int(request.args.get('page', 1))
        per_page = 50
        
        logger.info(f"Filters - Search: '{search}', Scope: '{scope_filter}', User: '{user_filter}', Page: {page}")
        logger.info(f"Sort - By: '{sort_by}', Order: '{sort_order}'")
        
        # Build query
        query = Tag.query
        
        # Apply search filter
        if search:
            query = query.filter(Tag.name.contains(search.upper()))
        
        # Apply scope filter
        if scope_filter in ('system', 'personal'):
            query = query.filter(Tag.tag_scope == scope_filter)
        
        # Apply user filter
        if user_filter:
            query = query.filter(Tag.user_id == user_filter)
        
        # Apply sorting
        if sort_by == 'recipes':
            # For recipe count sorting, use subquery
            from db_models import recipe_tags
            recipe_count_subquery = db.session.query(
                recipe_tags.c.tag_id,
                func.count(recipe_tags.c.recipe_id).label('recipe_count')
            ).group_by(recipe_tags.c.tag_id).subquery()
            
            query = query.outerjoin(recipe_count_subquery, Tag.id == recipe_count_subquery.c.tag_id)
            
            if sort_order == 'desc':
                sort_column = func.coalesce(recipe_count_subquery.c.recipe_count, 0).desc()
            else:
                sort_column = func.coalesce(recipe_count_subquery.c.recipe_count, 0).asc()
        else:
            # Standard column sorting
            sort_column = Tag.name  # Default
            if sort_by == 'scope':
                sort_column = Tag.tag_scope
            elif sort_by == 'owner':
                sort_column = Tag.user_id
            
            if sort_order == 'desc':
                sort_column = sort_column.desc()
            else:
                sort_column = sort_column.asc()
        
        # Get total count
        total = query.count()
        pages = (total + per_page - 1) // per_page
        
        # Get tags with pagination and sorting
        pagination = query.order_by(sort_column).paginate(
            page=page, per_page=per_page, error_out=False
        )
        tags = pagination.items
        
        logger.info(f"Tags fetched: {len(tags)}")
        
        # Get all users for filter dropdown
        all_users = User.query.order_by(User.username).all()
        
        # Get tag statistics
        total_tags = Tag.query.count()
        system_tags = Tag.query.filter_by(tag_scope='system').count()
        personal_tags = Tag.query.filter_by(tag_scope='personal').count()
        
        # Count unique personal tag names
        from db_models import recipe_tags
        personal_tag_names_query = db.session.query(func.count(func.distinct(Tag.name)))\
            .filter(Tag.tag_scope == 'personal')
        unique_personal_names = personal_tag_names_query.scalar()
        
        logger.info(f"Statistics - Total: {total_tags}, System: {system_tags}, Personal: {personal_tags}")
        logger.info("=== ADMIN TAGS DEBUG END ===")
        
        return render_template('tag_manager.html',
                             tags=tags,
                             page=page,
                             pages=pages,
                             total=total,
                             search=search,
                             scope_filter=scope_filter,
                             user_filter=user_filter,
                             sort_by=sort_by,
                             sort_order=sort_order,
                             all_users=all_users,
                             total_tags=total_tags,
                             system_tags=system_tags,
                             personal_tags=personal_tags,
                             unique_personal_names=unique_personal_names,
                             is_admin_view=True)
    
    @app.route('/admin/tags/create', methods=['POST'])
    @login_required
    @require_admin
    def admin_create_tag():
        """Create a new system tag."""
        from db_models import Tag
        
        tag_name = request.form.get('tag_name', '').strip().upper()
        
        if not tag_name:
            flash('Tag name is required', 'error')
            return redirect(url_for('admin_tags'))
        
        # Check if system tag already exists
        existing = Tag.query.filter_by(name=tag_name, tag_scope='system').first()
        if existing:
            flash(f'System tag "{tag_name}" already exists', 'error')
            return redirect(url_for('admin_tags'))
        
        # Create new system tag
        slug = tag_name.lower().replace(' ', '-')
        tag = Tag(
            name=tag_name,
            slug=slug,
            tag_scope='system',
            user_id=None
        )
        db.session.add(tag)
        db.session.commit()
        
        logger.info(f"Admin {current_user.username} created system tag: {tag_name}")
        flash(f'System tag "{tag_name}" created successfully', 'success')
        
        return redirect(url_for('admin_tags'))
    
    @app.route('/admin/tags/<int:tag_id>/edit', methods=['POST'])
    @login_required
    @require_admin
    def admin_edit_tag(tag_id):
        """Edit a tag."""
        from db_models import Tag
        
        tag = Tag.query.get(tag_id)
        if not tag:
            flash('Tag not found', 'error')
            return redirect(url_for('admin_tags'))
        
        new_name = request.form.get('tag_name', '').strip().upper()
        
        if not new_name:
            flash('Tag name is required', 'error')
            return redirect(url_for('admin_tags'))
        
        old_name = tag.name
        tag.name = new_name
        tag.slug = new_name.lower().replace(' ', '-')
        
        db.session.commit()
        
        logger.info(f"Admin {current_user.username} renamed tag '{old_name}' to '{new_name}'")
        flash(f'Tag renamed to "{new_name}"', 'success')
        
        return redirect(url_for('admin_tags'))
    
    @app.route('/admin/tags/<int:tag_id>/delete', methods=['POST'])
    @login_required
    @require_admin
    def admin_delete_tag(tag_id):
        """Delete a tag."""
        from db_models import Tag
        from mysql_storage import MySQLStorage
        
        # Use storage method for proper cleanup
        from app_mysql import storage
        success, message = storage.delete_tag(tag_id)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
        
        return redirect(url_for('admin_tags'))
    
    @app.route('/admin/tags/convert-to-system', methods=['POST'])
    @login_required
    @require_admin
    def admin_convert_tag_to_system():
        """Convert all personal tags with a given name to a system tag."""
        from mysql_storage import MySQLStorage
        
        tag_name = request.form.get('tag_name', '').strip().upper()
        
        if not tag_name:
            flash('Tag name is required', 'error')
            return redirect(url_for('admin_tags'))
        
        # Use storage method for conversion
        from app_mysql import storage
        success, message = storage.convert_personal_to_system_tag(tag_name)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
        
        return redirect(url_for('admin_tags'))
    
    @app.route('/admin/tags/cleanup', methods=['POST'])
    @login_required
    @require_admin
    def admin_cleanup_tags():
        """Cleanup orphaned tags."""
        from mysql_storage import MySQLStorage
        
        # Use storage method for cleanup
        from app_mysql import storage
        count = storage.cleanup_orphaned_tags()
        
        if count > 0:
            flash(f'Cleaned up {count} orphaned tag(s)', 'success')
        else:
            flash('No orphaned tags found', 'info')
        
        return redirect(url_for('admin_tags'))
    
    logger.info("Admin routes registered successfully")
