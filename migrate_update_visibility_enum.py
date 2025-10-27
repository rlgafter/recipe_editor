#!/usr/bin/env python3
"""
Migration: Update visibility ENUM to use 'incomplete' instead of 'unlisted'
"""

import sys
import os
from datetime import datetime
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from db_models import db
from config import SQLALCHEMY_DATABASE_URI
from sqlalchemy import text

# Configure logging
log_filename = f"logs/migration_update_visibility_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def run_migration():
    """Run the migration to update visibility ENUM."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        logger.info("=" * 80)
        logger.info("Starting migration: Update visibility ENUM (unlisted -> incomplete)")
        logger.info("=" * 80)
        
        try:
            # Check existing recipes with 'unlisted' visibility
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*) as count 
                    FROM recipes 
                    WHERE visibility = 'unlisted'
                """))
                count = result.fetchone()[0]
                logger.info(f"Found {count} recipes with 'unlisted' visibility")
            
            # Update recipes with 'unlisted' to 'incomplete'
            if count > 0:
                logger.info("Converting 'unlisted' recipes to 'incomplete'...")
                with db.engine.connect() as conn:
                    result = conn.execute(text("""
                        UPDATE recipes 
                        SET visibility = 'incomplete' 
                        WHERE visibility = 'unlisted'
                    """))
                    conn.commit()
                    logger.info(f"✓ Updated {result.rowcount} recipes to 'incomplete'")
            
            # Modify ENUM type (MySQL specific)
            logger.info("Updating ENUM type...")
            with db.engine.connect() as conn:
                # Note: This is MySQL-specific syntax
                conn.execute(text("""
                    ALTER TABLE recipes 
                    MODIFY COLUMN visibility ENUM('private', 'public', 'incomplete') 
                    DEFAULT 'incomplete' NOT NULL
                """))
                conn.commit()
                logger.info("✓ Updated recipes.visibility ENUM type")
            
            # Update user_preferences table if it exists
            with db.engine.connect() as conn:
                inspector = db.inspect(db.engine)
                tables = inspector.get_table_names()
                
                if 'user_preferences' in tables:
                    columns = [col['name'] for col in inspector.get_columns('user_preferences')]
                    if 'default_visibility' in columns:
                        logger.info("Updating user_preferences.default_visibility ENUM...")
                        conn.execute(text("""
                            ALTER TABLE user_preferences 
                            MODIFY COLUMN default_visibility ENUM('private', 'public', 'incomplete') 
                            DEFAULT 'incomplete'
                        """))
                        conn.commit()
                        logger.info("✓ Updated user_preferences.default_visibility ENUM type")
            
            db.session.commit()
            logger.info("=" * 80)
            logger.info("✓ Migration completed successfully")
            logger.info("=" * 80)
            logger.info(f"Migration log saved to: {log_filename}")
            
        except Exception as e:
            logger.error(f"✗ Migration failed: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    run_migration()
