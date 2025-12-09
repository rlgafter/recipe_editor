#!/usr/bin/env python3
"""Update admin user email and password."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Load .env file if it exists
try:
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and 'export ' in line:
                    key_value = line.replace('export ', '').strip()
                    if '=' in key_value:
                        key, value = key_value.split('=', 1)
                        value = value.strip('\'"')
                        os.environ[key.strip()] = value
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")

import config
from flask import Flask
from db_models import db, User
from auth import hash_password, is_valid_email

def update_admin_user():
    """Update admin user email and password."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        try:
            # Find admin user
            admin_user = User.query.filter_by(username='admin').first()
            
            if not admin_user:
                print("✗ Admin user not found!")
                return False
            
            # Update email
            new_email = 'rlgafter@gmail.com'
            old_email = admin_user.email
            
            # Validate email format
            if not is_valid_email(new_email):
                print(f"✗ Invalid email format: {new_email}")
                return False
            
            admin_user.email = new_email
            
            # Update password
            new_password = 'trouble'
            admin_user.password_hash = hash_password(new_password)
            
            # Commit changes
            db.session.commit()
            
            print("✓ Admin user updated successfully!")
            print(f"\nUpdated Details:")
            print(f"  Username: {admin_user.username}")
            print(f"  Email: {old_email} → {new_email}")
            print(f"  Password: {new_password}")
            print(f"  Is Admin: {admin_user.is_admin}")
            print(f"  Can Publish Public: {admin_user.can_publish_public}")
            
            return True
                
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error updating admin user: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = update_admin_user()
    sys.exit(0 if success else 1)

