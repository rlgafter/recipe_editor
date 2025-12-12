#!/usr/bin/env python3
"""Clear pending email change fields for admin user."""
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

def clear_admin_pending_email():
    """Clear pending email change fields for admin user."""
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
            
            print(f"Current admin user email: {admin_user.email}")
            print(f"Pending email: {admin_user.pending_email}")
            print(f"Email change token: {admin_user.email_change_token}")
            print(f"Email change expires: {admin_user.email_change_expires}")
            
            # Clear pending email change fields
            admin_user.pending_email = None
            admin_user.email_change_token = None
            admin_user.email_change_expires = None
            
            # Commit changes
            db.session.commit()
            
            print("\n✓ Cleared pending email change fields for admin user!")
            print(f"  Email: {admin_user.email}")
            print(f"  Pending email: None")
            print(f"  Email change token: None")
            print(f"  Email change expires: None")
            
            return True
                
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error clearing pending email fields: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = clear_admin_pending_email()
    sys.exit(0 if success else 1)




