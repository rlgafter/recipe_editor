#!/usr/bin/env python3
"""
Migration: Add URL confidence tracking fields to recipe_sources table
Date: 2025-11-04
"""
import os
import sys
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from db_models import db
from config import SQLALCHEMY_DATABASE_URI
from sqlalchemy import text

# Setup logging
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f'migration_add_url_confidence_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def run_migration():
    """Add source_url_confidence and source_url_detection_method fields."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        logger.info("=" * 80)
        logger.info("Starting migration: Add URL confidence tracking fields")
        logger.info("=" * 80)
        
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('recipe_sources')]
            
            confidence_exists = 'source_url_confidence' in columns
            method_exists = 'source_url_detection_method' in columns
            
            if confidence_exists and method_exists:
                logger.info("✓ Columns already exist. Migration already applied.")
                return True
            
            # Add source_url_confidence field
            if not confidence_exists:
                logger.info("Adding source_url_confidence column...")
                with db.engine.connect() as conn:
                    conn.execute(text("""
                        ALTER TABLE recipe_sources 
                        ADD COLUMN source_url_confidence DECIMAL(3,2) DEFAULT NULL
                        COMMENT 'Confidence score (0.00-1.00) for automatically detected URLs'
                    """))
                    conn.commit()
                logger.info("✓ Added source_url_confidence column")
            else:
                logger.info("✓ source_url_confidence column already exists, skipping")
            
            # Add source_url_detection_method field
            if not method_exists:
                logger.info("Adding source_url_detection_method column...")
                with db.engine.connect() as conn:
                    conn.execute(text("""
                        ALTER TABLE recipe_sources 
                        ADD COLUMN source_url_detection_method ENUM('manual', 'gemini_suggested', 'search_api', 'user_provided') DEFAULT 'manual'
                        COMMENT 'Method used to determine the source URL'
                    """))
                    conn.commit()
                logger.info("✓ Added source_url_detection_method column")
            else:
                logger.info("✓ source_url_detection_method column already exists, skipping")
            
            logger.info("=" * 80)
            logger.info("Migration completed successfully!")
            logger.info("=" * 80)
            
            # Show table structure
            columns = inspector.get_columns('recipe_sources')
            logger.info("\nUpdated recipe_sources table structure:")
            for col in columns:
                logger.info(f"  {col['name']}: {col['type']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False


def rollback_migration():
    """Remove the added fields (rollback)."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        logger.info("=" * 80)
        logger.info("Starting migration rollback: Remove URL confidence tracking fields")
        logger.info("=" * 80)
        
        try:
            # Check if columns exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('recipe_sources')]
            
            confidence_exists = 'source_url_confidence' in columns
            method_exists = 'source_url_detection_method' in columns
            
            if not confidence_exists and not method_exists:
                logger.info("✓ Columns don't exist. Nothing to rollback.")
                return True
            
            # Remove source_url_confidence
            if confidence_exists:
                logger.info("Removing source_url_confidence column...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE recipe_sources DROP COLUMN source_url_confidence"))
                    conn.commit()
                logger.info("✓ Removed source_url_confidence column")
            
            # Remove source_url_detection_method
            if method_exists:
                logger.info("Removing source_url_detection_method column...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE recipe_sources DROP COLUMN source_url_detection_method"))
                    conn.commit()
                logger.info("✓ Removed source_url_detection_method column")
            
            logger.info("=" * 80)
            logger.info("Migration rollback completed successfully!")
            logger.info("=" * 80)
            return True
            
        except Exception as e:
            logger.error(f"Migration rollback failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate recipe_sources table to add URL confidence tracking')
    parser.add_argument('--down', action='store_true', help='Rollback the migration')
    args = parser.parse_args()
    
    try:
        if args.down:
            success = rollback_migration()
        else:
            success = run_migration()
        
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Migration script error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
