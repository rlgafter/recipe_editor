#!/usr/bin/env python3
"""Run SQL migration to add password setup fields."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import config
from flask import Flask
from db_models import db

def run_migration():
    """Run the migration."""
    print("Starting migration...")
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        try:
            # Check if columns already exist
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            print("Current columns:", columns)
            
            # Add missing columns
            if 'password_setup_token' not in columns:
                print("Adding password_setup_token...")
                db.session.execute(text("ALTER TABLE users ADD COLUMN password_setup_token VARCHAR(100)"))
            
            if 'password_setup_expires' not in columns:
                print("Adding password_setup_expires...")
                db.session.execute(text("ALTER TABLE users ADD COLUMN password_setup_expires DATETIME"))
            
            if 'account_setup_completed' not in columns:
                print("Adding account_setup_completed...")
                db.session.execute(text("ALTER TABLE users ADD COLUMN account_setup_completed BOOLEAN DEFAULT 0"))
            
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
