"""
Admin routes for user type management.
"""
import logging
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from user_permissions import can_manage_users_required, can_manage_system_required
from admin_user_management import AdminUserManagement

logger = logging.getLogger(__name__)


def register_admin_routes(app):
    """Register admin routes with Flask app."""
    
    @app.route('/admin')
    @login_required
    @can_manage_system_required
    def admin_dashboard():
        """Admin dashboard."""
        admin_mgmt = AdminUserManagement()
        user_stats = admin_mgmt.get_user_type_stats()
        recent_users = admin_mgmt.get_recent_users(5)
        
        return render_template('admin_dashboard.html', 
                             user_stats=user_stats,
                             recent_users=recent_users)
    
    @app.route('/admin/users')
    @login_required
    @can_manage_users_required
    def admin_users():
        """User management page."""
        admin_mgmt = AdminUserManagement()
        
        # Get search parameters
        search_query = request.args.get('search', '')
        user_type_filter = request.args.get('user_type', '')
        page = int(request.args.get('page', 1))
        
        # Get user types for filter dropdown
        user_types = admin_mgmt.get_all_user_types()
        
        # Get users based on search/filter
        if search_query:
            users_data = admin_mgmt.search_users(search_query, page, 20)
        else:
            users_data = admin_mgmt.get_all_users(page, 20)
        
        # Get user type statistics
        user_stats = admin_mgmt.get_user_type_stats()
        
        # Add recipe counts to users
        for user in users_data['users']:
            user_details = admin_mgmt.get_user_details(user.id)
            if user_details:
                user.recipe_count = user_details['recipe_count']
                user.public_recipe_count = user_details['public_recipe_count']
        
        return render_template('admin_users.html',
                             users=users_data['users'],
                             user_types=user_types,
                             user_stats=user_stats,
                             page=users_data['page'],
                             pages=users_data['pages'],
                             total=users_data['total'])
    
    @app.route('/admin/users/change-type', methods=['POST'])
    @login_required
    @can_manage_users_required
    def admin_change_user_type():
        """Change a user's type."""
        user_id = request.form.get('user_id')
        new_type_id = request.form.get('new_type_id')
        
        if not user_id or not new_type_id:
            flash('Missing required parameters', 'error')
            return redirect(url_for('admin_users'))
        
        try:
            admin_mgmt = AdminUserManagement()
            success, message = admin_mgmt.change_user_type(
                int(user_id), 
                int(new_type_id), 
                current_user.id
            )
            
            if success:
                flash(message, 'success')
            else:
                flash(message, 'error')
                
        except Exception as e:
            logger.error(f"Error changing user type: {e}")
            flash(f'Error changing user type: {str(e)}', 'error')
        
        return redirect(url_for('admin_users'))
    
    @app.route('/admin/users/deactivate', methods=['POST'])
    @login_required
    @can_manage_users_required
    def admin_deactivate_user():
        """Deactivate a user."""
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'Missing user ID'})
        
        try:
            admin_mgmt = AdminUserManagement()
            success, message = admin_mgmt.deactivate_user(int(user_id), current_user.id)
            return jsonify({'success': success, 'message': message})
            
        except Exception as e:
            logger.error(f"Error deactivating user: {e}")
            return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    
    @app.route('/admin/users/activate', methods=['POST'])
    @login_required
    @can_manage_users_required
    def admin_activate_user():
        """Activate a user."""
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'Missing user ID'})
        
        try:
            admin_mgmt = AdminUserManagement()
            success, message = admin_mgmt.activate_user(int(user_id), current_user.id)
            return jsonify({'success': success, 'message': message})
            
        except Exception as e:
            logger.error(f"Error activating user: {e}")
            return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    
    @app.route('/admin/user-types')
    @login_required
    @can_manage_system_required
    def admin_user_types():
        """User types management page."""
        admin_mgmt = AdminUserManagement()
        user_types = admin_mgmt.get_all_user_types()
        user_stats = admin_mgmt.get_user_type_stats()
        
        return render_template('admin_user_types.html',
                             user_types=user_types,
                             user_stats=user_stats)
    
    @app.route('/admin/users/<int:user_id>')
    @login_required
    @can_manage_users_required
    def admin_user_details(user_id):
        """User details page."""
        admin_mgmt = AdminUserManagement()
        user_details = admin_mgmt.get_user_details(user_id)
        
        if not user_details:
            flash('User not found', 'error')
            return redirect(url_for('admin_users'))
        
        return render_template('admin_user_details.html',
                             user_details=user_details)
    
    logger.info("Admin routes registered successfully")
