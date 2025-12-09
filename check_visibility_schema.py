#!/usr/bin/env python3
"""Check the visibility column schema in the database."""
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
from sqlalchemy import text, inspect

def check_schema():
    """Check the visibility column schema."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            
            # Check recipes table
            print("Checking recipes table...")
            columns = inspector.get_columns('recipes')
            vis_col = [c for c in columns if c['name'] == 'visibility']
            
            if vis_col:
                col_info = vis_col[0]
                print(f"  Column: {col_info['name']}")
                print(f"  Type: {col_info['type']}")
                print(f"  Nullable: {col_info['nullable']}")
                print(f"  Default: {col_info.get('default', 'None')}")
                
                # Try to get the actual ENUM values
                with db.engine.connect() as conn:
                    result = conn.execute(text("""
                        SHOW COLUMNS FROM recipes WHERE Field = 'visibility'
                    """))
                    row = result.fetchone()
                    if row:
                        print(f"  Full column info: {row}")
                        # Type is usually in row[1]
                        print(f"  MySQL Type: {row[1]}")
            else:
                print("  ERROR: visibility column not found!")
            
            # Check user_preferences table
            print("\nChecking user_preferences table...")
            try:
                columns = inspector.get_columns('user_preferences')
                vis_col = [c for c in columns if c['name'] == 'default_visibility']
                
                if vis_col:
                    col_info = vis_col[0]
                    print(f"  Column: {col_info['name']}")
                    print(f"  Type: {col_info['type']}")
                    
                    with db.engine.connect() as conn:
                        result = conn.execute(text("""
                            SHOW COLUMNS FROM user_preferences WHERE Field = 'default_visibility'
                        """))
                        row = result.fetchone()
                        if row:
                            print(f"  MySQL Type: {row[1]}")
                else:
                    print("  default_visibility column not found (may not exist)")
            except Exception as e:
                print(f"  Error checking user_preferences: {e}")
            
            # Test inserting different visibility values
            print("\nTesting visibility values...")
            test_values = ['incomplete', 'private', 'public']
            for val in test_values:
                try:
                    with db.engine.connect() as conn:
                        # Just test the value, don't actually insert
                        result = conn.execute(text(f"SELECT '{val}' AS test_val"))
                        print(f"  '{val}': OK")
                except Exception as e:
                    print(f"  '{val}': ERROR - {e}")
                    
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    check_schema()






