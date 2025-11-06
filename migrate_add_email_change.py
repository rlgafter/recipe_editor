#!/usr/bin/env python3
"""
Migration: Add email change fields to users table
- Adds pending_email column for new email awaiting verification
- Adds email_change_token for verification
- Adds email_change_expires for token expiration
"""

import sys
import logging
from datetime import datetime
import mysql.connector
from mysql.connector import Error
from db_config import get_mysql_config

# Setup logging
log_filename = f"logs/migration_add_email_change_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
    """Run the migration to add email change fields."""
    conn = None
    cursor = None
    
    try:
        # Connect to database
        config = get_mysql_config()
        logger.info(f"Connecting to database: {config['database']}")
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        logger.info("Starting migration: Add email change fields to users table")
        
        # Check if columns already exist
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME = 'pending_email'
        """, (config['database'],))
        
        if cursor.fetchone()[0] > 0:
            logger.warning("Column 'pending_email' already exists. Migration may have been run before.")
            return True
        
        # Step 1: Add pending_email column
        logger.info("Step 1: Adding pending_email column...")
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN pending_email VARCHAR(255) NULL AFTER email
        """)
        logger.info("✓ Added pending_email column")
        
        # Step 2: Add email_change_token column
        logger.info("Step 2: Adding email_change_token column...")
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN email_change_token VARCHAR(100) NULL AFTER pending_email
        """)
        logger.info("✓ Added email_change_token column")
        
        # Step 3: Add email_change_expires column
        logger.info("Step 3: Adding email_change_expires column...")
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN email_change_expires TIMESTAMP NULL AFTER email_change_token
        """)
        logger.info("✓ Added email_change_expires column")
        
        # Step 4: Add index on email_change_token
        logger.info("Step 4: Adding index on email_change_token...")
        cursor.execute("""
            ALTER TABLE users 
            ADD INDEX idx_email_change_token (email_change_token)
        """)
        logger.info("✓ Added index on email_change_token")
        
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
    logger.info("MIGRATION: Add email change fields to users table")
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

