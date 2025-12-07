#!/usr/bin/env python3
"""
Verify database installation - check all tables and key columns exist
"""
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

from flask import Flask
from db_models import db
from config import SQLALCHEMY_DATABASE_URI
from sqlalchemy import inspect, text

# Expected tables based on the schema
EXPECTED_TABLES = [
    'users',
    'user_preferences',
    'password_reset_tokens',
    'user_stats',
    'recipes',
    'recipe_sources',
    'recipe_photos',
    'recipe_stats',
    'recipe_ingredients',
    'ingredients',
    'user_ingredient_substitutions',
    'tags',
    'recipe_tags',
    'recipe_favorites',
    'recipe_ratings',
    'collections',
    'collection_recipes',
    'meal_plans',
    'meal_plan_recipes',
    'recipe_email_log'
]

# Key columns to verify in critical tables
KEY_COLUMNS = {
    'users': [
        'id', 'username', 'email', 'password_hash', 'display_name',
        'email_verified', 'is_active', 'is_admin', 'can_publish_public',
        'pending_email', 'email_change_token', 'email_change_expires',
        'password_setup_token', 'password_setup_expires', 'account_setup_completed',
        'created_at', 'updated_at', 'last_login'
    ],
    'recipes': [
        'id', 'user_id', 'name', 'description', 'instructions', 'visibility',
        'ingredients_json', 'slug', 'prep_time', 'cook_time', 'servings',
        'difficulty', 'created_at', 'updated_at'
    ],
    'tags': [
        'id', 'name', 'slug', 'tag_scope', 'user_id', 'tag_type', 'created_at'
    ]
}

def verify_database():
    """Verify database installation."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    issues = []
    warnings = []
    
    with app.app_context():
        print("=" * 80)
        print("Database Verification Report")
        print("=" * 80)
        print()
        
        try:
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            # Check for expected tables
            print("1. Checking Tables...")
            print("-" * 80)
            missing_tables = []
            for table in EXPECTED_TABLES:
                if table in existing_tables:
                    print(f"  ✓ {table}")
                else:
                    print(f"  ✗ {table} - MISSING")
                    missing_tables.append(table)
            
            if missing_tables:
                issues.append(f"Missing tables: {', '.join(missing_tables)}")
            
            print()
            
            # Check key columns in critical tables
            print("2. Checking Key Columns...")
            print("-" * 80)
            
            for table_name, expected_columns in KEY_COLUMNS.items():
                if table_name not in existing_tables:
                    print(f"  ⚠ Skipping {table_name} - table does not exist")
                    continue
                
                print(f"\n  Table: {table_name}")
                table_columns = [col['name'] for col in inspector.get_columns(table_name)]
                missing_columns = []
                
                for col in expected_columns:
                    if col in table_columns:
                        print(f"    ✓ {col}")
                    else:
                        print(f"    ✗ {col} - MISSING")
                        missing_columns.append(col)
                
                if missing_columns:
                    issues.append(f"Table '{table_name}' missing columns: {', '.join(missing_columns)}")
            
            print()
            
            # Check for extra tables (warnings)
            print("3. Checking for Unexpected Tables...")
            print("-" * 80)
            extra_tables = [t for t in existing_tables if t not in EXPECTED_TABLES]
            if extra_tables:
                for table in extra_tables:
                    print(f"  ⚠ {table} - not in expected list")
                    warnings.append(f"Unexpected table: {table}")
            else:
                print("  ✓ No unexpected tables found")
            
            print()
            
            # Test database connection and basic query
            print("4. Testing Database Connection...")
            print("-" * 80)
            try:
                with db.engine.connect() as conn:
                    result = conn.execute(text("SELECT COUNT(*) FROM users"))
                    user_count = result.fetchone()[0]
                    print(f"  ✓ Database connection successful")
                    print(f"  ✓ Found {user_count} user(s) in database")
                    
                    # Check if can_publish_public column works
                    result = conn.execute(text("SELECT COUNT(*) FROM users WHERE can_publish_public = TRUE"))
                    pub_count = result.fetchone()[0]
                    print(f"  ✓ Found {pub_count} user(s) with publish permission")
            except Exception as e:
                print(f"  ✗ Database connection test failed: {e}")
                issues.append(f"Database connection test failed: {e}")
            
            print()
            
            # Summary
            print("=" * 80)
            print("Summary")
            print("=" * 80)
            
            if not issues:
                print("✓ Database installation appears to be CORRECT")
                print("  All expected tables and columns are present.")
                return True
            else:
                print("✗ Database installation has ISSUES:")
                for issue in issues:
                    print(f"  - {issue}")
                
                if warnings:
                    print("\n⚠ Warnings:")
                    for warning in warnings:
                        print(f"  - {warning}")
                
                return False
                
        except Exception as e:
            print(f"✗ Verification failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = verify_database()
    sys.exit(0 if success else 1)

