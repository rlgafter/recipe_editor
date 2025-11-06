#!/usr/bin/env python3
"""
Migration: Add tag_scope and user_id to tags table
- Adds tag_scope column (system/personal)
- Adds user_id column for personal tag ownership
- Updates unique constraints
"""

import sys
import logging
from datetime import datetime
import mysql.connector
from mysql.connector import Error
from db_config import get_mysql_config

# Setup logging
log_filename = f"logs/migration_add_tag_scope_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
    """Run the migration to add tag_scope and user_id columns."""
    conn = None
    cursor = None
    
    try:
        # Connect to database
        config = get_mysql_config()
        logger.info(f"Connecting to database: {config['database']}")
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        logger.info("Starting migration: Add tag_scope and user_id to tags table")
        
        # Check if columns already exist
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'tags' 
            AND COLUMN_NAME = 'tag_scope'
        """, (config['database'],))
        
        if cursor.fetchone()[0] > 0:
            logger.warning("Column 'tag_scope' already exists. Migration may have been run before.")
            response = input("Continue anyway? (yes/no): ").strip().lower()
            if response != 'yes':
                logger.info("Migration cancelled by user.")
                return
        
        # Step 1: Add tag_scope column
        logger.info("Step 1: Adding tag_scope column...")
        cursor.execute("""
            ALTER TABLE tags 
            ADD COLUMN tag_scope ENUM('system', 'personal') DEFAULT 'personal' AFTER slug
        """)
        logger.info("✓ Added tag_scope column")
        
        # Step 2: Add user_id column
        logger.info("Step 2: Adding user_id column...")
        cursor.execute("""
            ALTER TABLE tags 
            ADD COLUMN user_id INT NULL AFTER tag_scope,
            ADD CONSTRAINT fk_tags_user_id 
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        """)
        logger.info("✓ Added user_id column with foreign key")
        
        # Step 3: Add index on user_id
        logger.info("Step 3: Adding index on user_id...")
        cursor.execute("""
            ALTER TABLE tags 
            ADD INDEX idx_user_id (user_id)
        """)
        logger.info("✓ Added index on user_id")
        
        # Step 4: Add composite index for personal tag lookups
        logger.info("Step 4: Adding composite index for (user_id, name)...")
        cursor.execute("""
            ALTER TABLE tags 
            ADD INDEX idx_user_name (user_id, name)
        """)
        logger.info("✓ Added composite index")
        
        # Step 5: Remove unique constraints on name and slug
        logger.info("Step 5: Removing unique constraints on name and slug...")
        try:
            cursor.execute("""
                ALTER TABLE tags 
                DROP INDEX name
            """)
            logger.info("✓ Removed unique constraint on name")
        except Exception as e:
            logger.warning(f"Could not remove unique constraint on name: {e}")
        
        try:
            cursor.execute("""
                ALTER TABLE tags 
                DROP INDEX slug
            """)
            logger.info("✓ Removed unique constraint on slug")
        except Exception as e:
            logger.warning(f"Could not remove unique constraint on slug: {e}")
        
        # Step 6: Update existing tags to personal scope
        logger.info("Step 6: Setting existing tags to 'personal' scope...")
        cursor.execute("""
            UPDATE tags 
            SET tag_scope = 'personal'
        """)
        affected = cursor.rowcount
        logger.info(f"✓ Updated {affected} existing tags to personal scope")
        
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
    logger.info("MIGRATION: Add tag_scope and user_id to tags table")
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

