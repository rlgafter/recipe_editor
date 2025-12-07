#!/usr/bin/env python3
"""Run SQL migration to create recipe_ingredients table."""
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
    print("Starting migration: Create recipe_ingredients table...")
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if 'recipe_ingredients' in existing_tables:
                print("✓ Table 'recipe_ingredients' already exists")
                return True
            
            print("Creating recipe_ingredients table...")
            with db.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE recipe_ingredients (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        recipe_id INT NOT NULL,
                        ingredient_id INT NOT NULL,
                        amount VARCHAR(50),
                        unit VARCHAR(50),
                        preparation VARCHAR(200),
                        is_optional BOOLEAN DEFAULT FALSE,
                        notes TEXT,
                        sort_order INT DEFAULT 0,
                        ingredient_group VARCHAR(100),
                        FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
                        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE RESTRICT,
                        INDEX idx_recipe_order (recipe_id, sort_order),
                        INDEX idx_ingredient (ingredient_id),
                        INDEX idx_recipe (recipe_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                conn.commit()
            
            print("✓ Migration completed successfully!")
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

