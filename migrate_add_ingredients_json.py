#!/usr/bin/env python3
"""
Migration: Add ingredients_json field to recipes table
This field will store ingredients as JSON to preserve empty ingredient positions.
"""

import os
import sys
import logging
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import SQLALCHEMY_DATABASE_URI
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
log_filename = f"logs/migration_add_ingredients_json_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def run_migration():
    """Add ingredients_json field to recipes table."""
    try:
        logger.info("Starting migration: Add ingredients_json field")
        
        # Create database connection
        engine = create_engine(SQLALCHEMY_DATABASE_URI)
        
        with engine.connect() as conn:
            # Check if the field already exists
            result = conn.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'recipes' 
                AND COLUMN_NAME = 'ingredients_json'
            """))
            
            if result.fetchone():
                logger.info("Field ingredients_json already exists, skipping migration")
                return True
            
            # Add the ingredients_json field
            logger.info("Adding ingredients_json field to recipes table...")
            conn.execute(text("""
                ALTER TABLE recipes 
                ADD COLUMN ingredients_json JSON NULL 
                AFTER meta_description
            """))
            
            conn.commit()
            logger.info("✓ Successfully added ingredients_json field")
            
            # Verify the field was added
            result = conn.execute(text("""
                SELECT COLUMN_NAME, DATA_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'recipes' 
                AND COLUMN_NAME = 'ingredients_json'
            """))
            
            field_info = result.fetchone()
            if field_info:
                logger.info(f"✓ Verified field exists: {field_info[0]} ({field_info[1]})")
            else:
                logger.error("✗ Field verification failed")
                return False
            
            logger.info("Migration completed successfully!")
            return True
            
    except SQLAlchemyError as e:
        logger.error(f"Database error during migration: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        return False

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("MIGRATION: Add ingredients_json field to recipes table")
    logger.info("=" * 60)
    
    success = run_migration()
    
    if success:
        logger.info("Migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("Migration failed!")
        sys.exit(1)
