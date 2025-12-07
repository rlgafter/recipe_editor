#!/usr/bin/env python3
"""Check if admin user exists in database."""
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
from sqlalchemy import text

def check_admin_user():
    """Check if admin user exists."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        try:
            # Query for admin user
            admin_user = User.query.filter_by(username='admin').first()
            
            if admin_user:
                print("✓ User with username 'admin' EXISTS")
                print(f"\nUser Details:")
                print(f"  ID: {admin_user.id}")
                print(f"  Username: {admin_user.username}")
                print(f"  Email: {admin_user.email}")
                print(f"  Display Name: {admin_user.display_name}")
                print(f"  Is Admin: {admin_user.is_admin}")
                print(f"  Can Publish Public: {admin_user.can_publish_public}")
                print(f"  Email Verified: {admin_user.email_verified}")
                print(f"  Is Active: {admin_user.is_active}")
                print(f"  Created At: {admin_user.created_at}")
                print(f"  Last Login: {admin_user.last_login}")
                return True
            else:
                print("✗ User with username 'admin' does NOT exist")
                
                # Show all users
                all_users = User.query.all()
                if all_users:
                    print(f"\nFound {len(all_users)} user(s) in database:")
                    for user in all_users:
                        print(f"  - {user.username} (email: {user.email}, admin: {user.is_admin})")
                else:
                    print("\nNo users found in database.")
                return False
                
        except Exception as e:
            print(f"✗ Error checking for admin user: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    check_admin_user()

