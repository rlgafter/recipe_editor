#!/usr/bin/env python3
"""
Reset admin user password.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask
from db_models import db, User
from config import SQLALCHEMY_DATABASE_URI
import bcrypt

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Password to set
new_password = 'trouble'

def reset_admin_password():
    """Reset admin user password."""
    with app.app_context():
        try:
            # Find admin user
            admin_user = User.query.filter_by(username='admin').first()
            
            if not admin_user:
                print("Admin user not found!")
                print("\nCreating admin user with password 'trouble'...")
                
                # Hash the password
                password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                # Create admin user
                admin_user = User(
                    username='admin',
                    email='admin@recipe-editor.local',
                    password_hash=password_hash,
                    display_name='Administrator',
                    email_verified=True,
                    is_admin=True,
                    is_active=True,
                    can_publish_public=True
                )
                db.session.add(admin_user)
                db.session.commit()
                print(f"✓ Admin user created!")
                print(f"  Username: admin")
                print(f"  Email: admin@recipe-editor.local")
                print(f"  Password: {new_password}")
            else:
                print("✓ Admin user found!")
                print(f"  Current email: {admin_user.email}")
                
                # Hash the new password
                password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                # Update password
                admin_user.password_hash = password_hash
                admin_user.is_admin = True  # Ensure admin flag is set
                admin_user.is_active = True  # Ensure account is active
                admin_user.can_publish_public = True  # Grant publish permission
                db.session.commit()
                
                print(f"✓ Password reset successfully!")
                print(f"  Username: {admin_user.username}")
                print(f"  Email: {admin_user.email}")
                print(f"  New password: {new_password}")
                print(f"  Admin status: {admin_user.is_admin}")
            
            return True
            
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

if __name__ == '__main__':
    print("=" * 70)
    print("Reset Admin Password")
    print("=" * 70)
    print()
    success = reset_admin_password()
    sys.exit(0 if success else 1)

