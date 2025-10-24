"""
Admin interface for managing user types and permissions.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

from db_models import db, User, UserType

logger = logging.getLogger(__name__)


class AdminUserManagement:
    """Admin interface for user type management."""
    
    def __init__(self, db_session: Session = None):
        """Initialize with database session."""
        self.db = db_session or db.session
    
    def get_all_user_types(self) -> List[UserType]:
        """Get all user types."""
        return self.db.query(UserType).filter(UserType.is_active == True).order_by(UserType.id).all()
    
    def get_user_type(self, type_id: int) -> Optional[UserType]:
        """Get user type by ID."""
        return self.db.query(UserType).filter(UserType.id == type_id).first()
    
    def get_user_type_by_name(self, name: str) -> Optional[UserType]:
        """Get user type by name."""
        return self.db.query(UserType).filter(UserType.name == name).first()
    
    def get_all_users(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get paginated list of users with their types."""
        query = self.db.query(User).join(UserType).order_by(User.created_at.desc())
        
        total = query.count()
        users = query.offset((page - 1) * per_page).limit(per_page).all()
        
        return {
            'users': users,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }
    
    def search_users(self, query: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Search users by username, email, or display name."""
        search_query = self.db.query(User).join(UserType).filter(
            or_(
                User.username.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%'),
                User.display_name.ilike(f'%{query}%')
            )
        ).order_by(User.created_at.desc())
        
        total = search_query.count()
        users = search_query.offset((page - 1) * per_page).limit(per_page).all()
        
        return {
            'users': users,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page,
            'query': query
        }
    
    def change_user_type(self, user_id: int, new_type_id: int, changed_by_user_id: int) -> tuple[bool, str]:
        """
        Change a user's type.
        
        Args:
            user_id: ID of user to change
            new_type_id: New user type ID
            changed_by_user_id: ID of admin making the change
            
        Returns:
            (success, message)
        """
        try:
            # Verify the admin has permission
            admin_user = self.db.query(User).filter(User.id == changed_by_user_id).first()
            if not admin_user or not admin_user.can_manage_users():
                return False, "Insufficient permissions to change user types"
            
            # Get the user to change
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False, "User not found"
            
            # Get the new user type
            new_type = self.db.query(UserType).filter(UserType.id == new_type_id).first()
            if not new_type:
                return False, "User type not found"
            
            # Prevent changing admin users unless you're a super admin
            if user.user_type.name == 'admin' and admin_user.user_type.name != 'admin':
                return False, "Cannot change admin user types"
            
            # Prevent non-admins from making users admin
            if new_type.name == 'admin' and admin_user.user_type.name != 'admin':
                return False, "Only admins can assign admin privileges"
            
            # Change the user type
            old_type_name = user.user_type.name
            user.user_type_id = new_type_id
            
            # Update is_admin for backward compatibility
            user.is_admin = (new_type.name == 'admin')
            
            self.db.commit()
            
            logger.info(f"User {user.username} type changed from {old_type_name} to {new_type.name} by admin {admin_user.username}")
            return True, f"User type changed from {old_type_name} to {new_type.display_name}"
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error changing user type: {e}")
            return False, f"Error changing user type: {str(e)}"
    
    def get_user_type_stats(self) -> Dict[str, Any]:
        """Get statistics about user types."""
        stats = self.db.query(
            UserType.name,
            UserType.display_name,
            func.count(User.id).label('user_count')
        ).outerjoin(User).group_by(UserType.id, UserType.name, UserType.display_name).all()
        
        total_users = self.db.query(User).count()
        
        return {
            'stats': [
                {
                    'type_name': stat.name,
                    'display_name': stat.display_name,
                    'user_count': stat.user_count,
                    'percentage': round((stat.user_count / total_users * 100), 1) if total_users > 0 else 0
                }
                for stat in stats
            ],
            'total_users': total_users
        }
    
    def get_recent_users(self, limit: int = 10) -> List[User]:
        """Get recently registered users."""
        return self.db.query(User).join(UserType).order_by(User.created_at.desc()).limit(limit).all()
    
    def get_user_details(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a user."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # Get user's recipe count
        recipe_count = self.db.query(func.count(User.recipes)).filter(User.id == user_id).scalar()
        
        # Get user's public recipe count
        public_recipe_count = self.db.query(func.count(User.recipes)).filter(
            User.id == user_id,
            User.recipes.any(visibility='public')
        ).scalar()
        
        return {
            'user': user,
            'recipe_count': recipe_count,
            'public_recipe_count': public_recipe_count,
            'user_type': user.user_type,
            'last_login': user.last_login,
            'created_at': user.created_at,
            'is_active': user.is_active,
            'email_verified': user.email_verified
        }
    
    def deactivate_user(self, user_id: int, admin_user_id: int) -> tuple[bool, str]:
        """Deactivate a user account."""
        try:
            admin_user = self.db.query(User).filter(User.id == admin_user_id).first()
            if not admin_user or not admin_user.can_manage_users():
                return False, "Insufficient permissions"
            
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False, "User not found"
            
            if user.user_type.name == 'admin':
                return False, "Cannot deactivate admin users"
            
            user.is_active = False
            self.db.commit()
            
            logger.info(f"User {user.username} deactivated by admin {admin_user.username}")
            return True, f"User {user.username} has been deactivated"
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deactivating user: {e}")
            return False, f"Error deactivating user: {str(e)}"
    
    def activate_user(self, user_id: int, admin_user_id: int) -> tuple[bool, str]:
        """Activate a user account."""
        try:
            admin_user = self.db.query(User).filter(User.id == admin_user_id).first()
            if not admin_user or not admin_user.can_manage_users():
                return False, "Insufficient permissions"
            
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False, "User not found"
            
            user.is_active = True
            self.db.commit()
            
            logger.info(f"User {user.username} activated by admin {admin_user.username}")
            return True, f"User {user.username} has been activated"
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error activating user: {e}")
            return False, f"Error activating user: {str(e)}"
