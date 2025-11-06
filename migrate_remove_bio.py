#!/usr/bin/env python3
"""
Migration: Remove bio column from users table
"""

import sys
import logging
from datetime import datetime
import mysql.connector
from mysql.connector import Error
from db_config import get_mysql_config

# Setup logging
log_filename = f"logs/migration_remove_bio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
    """Run the migration to remove bio column."""
    conn = None
    cursor = None
    
    try:
        # Connect to database
        config = get_mysql_config()
        logger.info(f"Connecting to database: {config['database']}")
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        logger.info("Starting migration: Remove bio column from users table")
        
        # Check if column exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME = 'bio'
        """, (config['database'],))
        
        if cursor.fetchone()[0] == 0:
            logger.info("Column 'bio' does not exist. Migration already completed.")
            return True
        
        # Remove bio column
        logger.info("Removing bio column from users table...")
        cursor.execute("""
            ALTER TABLE users 
            DROP COLUMN bio
        """)
        logger.info("✓ Removed bio column")
        
        # Commit transaction
        conn.commit()
        logger.info("Migration completed successfully!")
        logger.info(f"Log file: {log_filename}")
        
        return True
        
    except Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Migration failed: {e}")
        logger.error(f"Log file: {log_filename}")
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == '__main__':
    logger.info("="*70)
    logger.info("MIGRATION: Remove bio column from users table")
    logger.info("="*70)
    
    success = run_migration()
    
    if success:
        logger.info("="*70)
        logger.info("MIGRATION COMPLETED SUCCESSFULLY")
        logger.info("="*70)
        sys.exit(0)
    else:
        logger.error("="*70)
        logger.error("MIGRATION FAILED")
        logger.error("="*70)
        sys.exit(1)

