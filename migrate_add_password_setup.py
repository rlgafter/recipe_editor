#!/usr/bin/env python3
"""
Migration script to add password setup fields to users table.
Adds: password_setup_token, password_setup_expires, account_setup_completed
"""
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import config
from flask import Flask
from db_models import db, User

def run_migration():
    """Run the migration to add password setup fields."""
    print("=" * 60)
    print("Password Setup Migration")
    print("=" * 60)
    print()
    
    # Initialize Flask app
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        try:
            # Check if columns already exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            print("Current columns in users table:")
            for col in columns:
                print(f"  - {col}")
            print()
            
            # Check what needs to be added
            needs_password_setup_token = 'password_setup_token' not in columns
            needs_password_setup_expires = 'password_setup_expires' not in columns
            needs_account_setup_completed = 'account_setup_completed' not in columns
            
            if not any([needs_password_setup_token, needs_password_setup_expires, needs_account_setup_completed]):
                print("✓ All password setup fields already exist. No migration needed.")
                return True
            
            print("Fields to add:")
            if needs_password_setup_token:
                print("  - password_setup_token (VARCHAR(100), nullable)")
            if needs_password_setup_expires:
                print("  - password_setup_expires (DATETIME, nullable)")
            if needs_account_setup_completed:
                print("  - account_setup_completed (BOOLEAN, default=False)")
            print()
            
            # Get confirmation
            response = input("Do you want to proceed with this migration? (yes/no): ")
            if response.lower() != 'yes':
                print("Migration cancelled.")
                return False
            
            print()
            print("Starting migration...")
            
            # Add columns one by one
            if needs_password_setup_token:
                print("Adding password_setup_token column...")
                db.session.execute(db.text("ALTER TABLE users ADD COLUMN password_setup_token VARCHAR(100)"))
                print("✓ Added password_setup_token")
            
            if needs_password_setup_expires:
                print("Adding password_setup_expires column...")
                db.session.execute(db.text("ALTER TABLE users ADD COLUMN password_setup_expires DATETIME"))
                print("✓ Added password_setup_expires")
            
            if needs_account_setup_completed:
                print("Adding account_setup_completed column...")
                db.session.execute(db.text("ALTER TABLE users ADD COLUMN account_setup_completed BOOLEAN DEFAULT 0"))
                print("✓ Added account_setup_completed")
            
            # Commit the changes
            db.session.commit()
            
            print()
            print("✓ Migration completed successfully!")
            print()
            
            # Show updated columns
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]
            print("Updated columns in users table:")
            for col in columns:
                print(f"  - {col}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print()
            print(f"✗ Migration failed: {str(e)}")
            print()
            return False

def rollback_migration():
    """Rollback the migration (remove the added columns)."""
    print("=" * 60)
    print("Rollback: Remove Password Setup Fields")
    print("=" * 60)
    print()
    print("WARNING: This will remove the password setup fields from the users table.")
    print("Make sure to backup your database before proceeding!")
    print()
    
    response = input("Are you sure you want to rollback? Type 'yes' to confirm: ")
    if response.lower() != 'yes':
        print("Rollback cancelled.")
        return False
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        try:
            print()
            print("Removing columns...")
            
            # Try to drop each column (MySQL syntax)
            try:
                db.session.execute(db.text("ALTER TABLE users DROP COLUMN password_setup_token"))
                print("✓ Removed password_setup_token")
            except Exception as e:
                print(f"  Note: password_setup_token - {str(e)}")
            
            try:
                db.session.execute(db.text("ALTER TABLE users DROP COLUMN password_setup_expires"))
                print("✓ Removed password_setup_expires")
            except Exception as e:
                print(f"  Note: password_setup_expires - {str(e)}")
            
            try:
                db.session.execute(db.text("ALTER TABLE users DROP COLUMN account_setup_completed"))
                print("✓ Removed account_setup_completed")
            except Exception as e:
                print(f"  Note: account_setup_completed - {str(e)}")
            
            db.session.commit()
            
            print()
            print("✓ Rollback completed successfully!")
            return True
            
        except Exception as e:
            db.session.rollback()
            print()
            print(f"✗ Rollback failed: {str(e)}")
            return False

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate database to add password setup fields')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    args = parser.parse_args()
    
    if args.rollback:
        success = rollback_migration()
    else:
        success = run_migration()
    
    sys.exit(0 if success else 1)
