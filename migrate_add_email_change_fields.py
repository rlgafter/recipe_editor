#!/usr/bin/env python3
"""Run SQL migration to add email change fields."""
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
from db_models import db
from sqlalchemy import inspect, text

def run_migration():
    """Run the migration."""
    print("Starting migration: Add email change fields...")
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            print("Current columns:", columns)
            
            # Add missing columns
            if 'pending_email' not in columns:
                print("Adding pending_email...")
                db.session.execute(text("ALTER TABLE users ADD COLUMN pending_email VARCHAR(255)"))
            
            if 'email_change_token' not in columns:
                print("Adding email_change_token...")
                db.session.execute(text("ALTER TABLE users ADD COLUMN email_change_token VARCHAR(100)"))
            
            if 'email_change_expires' not in columns:
                print("Adding email_change_expires...")
                db.session.execute(text("ALTER TABLE users ADD COLUMN email_change_expires DATETIME"))
            
            db.session.commit()
            print("✓ Migration completed successfully!")
            
            # Show updated columns
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]
            print("\nUpdated columns:")
            for col in columns:
                print(f"  - {col}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)


