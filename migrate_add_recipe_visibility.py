#!/usr/bin/env python3
"""
Migration: Add recipe visibility permissions
Adds can_publish_public field to users table and grants permission to existing admins
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
log_filename = f"logs/migration_add_recipe_visibility_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
    """Run the migration to add recipe visibility permissions."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        logger.info("=" * 80)
        logger.info("Starting migration: Add recipe visibility permissions")
        logger.info("=" * 80)
        
        try:
            # Check if column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            if 'can_publish_public' in columns:
                logger.info("Column 'can_publish_public' already exists in users table")
            else:
                # Add can_publish_public to users table
                logger.info("Adding can_publish_public column to users table...")
                with db.engine.connect() as conn:
                    conn.execute(text("""
                        ALTER TABLE users 
                        ADD COLUMN can_publish_public BOOLEAN 
                        DEFAULT FALSE NOT NULL
                    """))
                    conn.commit()
                logger.info("✓ Added can_publish_public column to users table")
            
            # Check if visibility column exists in recipes table
            recipes_columns = [col['name'] for col in inspector.get_columns('recipes')]
            
            if 'visibility' not in recipes_columns:
                # Add visibility to recipes table
                logger.info("Adding visibility column to recipes table...")
                with db.engine.connect() as conn:
                    conn.execute(text("""
                        ALTER TABLE recipes 
                        ADD COLUMN visibility ENUM('private', 'public', 'unlisted') 
                        DEFAULT 'private' NOT NULL
                    """))
                    conn.commit()
                logger.info("✓ Added visibility column to recipes table")
            else:
                logger.info("Column 'visibility' already exists in recipes table")
            
            # Grant permission to existing admins
            logger.info("Granting publish permission to admin users...")
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    UPDATE users 
                    SET can_publish_public = TRUE 
                    WHERE is_admin = TRUE AND can_publish_public = FALSE
                """))
                conn.commit()
                logger.info(f"✓ Updated {result.rowcount} admin users with publish permission")
            
            # Count users with permission
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*) as count 
                    FROM users 
                    WHERE can_publish_public = TRUE
                """))
                count = result.fetchone()[0]
                logger.info(f"Total users with publish permission: {count}")
            
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
