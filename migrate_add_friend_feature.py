#!/usr/bin/env python3
"""
Migration: Add friend feature tables and soft delete support
- Creates friend_requests table
- Creates friendships table
- Creates recipe_shares table
- Creates notifications table
- Adds deleted_at column to recipes table for soft delete
"""

import sys
import logging
from datetime import datetime
import mysql.connector
from mysql.connector import Error
from db_config import get_mysql_config

# Setup logging
log_filename = f"logs/migration_add_friend_feature_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def table_exists(cursor, table_name, database):
    """Check if a table exists."""
    cursor.execute("""
        SELECT COUNT(*) 
        FROM information_schema.TABLES 
        WHERE TABLE_SCHEMA = %s 
        AND TABLE_NAME = %s
    """, (database, table_name))
    return cursor.fetchone()[0] > 0


def column_exists(cursor, table_name, column_name, database):
    """Check if a column exists."""
    cursor.execute("""
        SELECT COUNT(*) 
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = %s 
        AND TABLE_NAME = %s 
        AND COLUMN_NAME = %s
    """, (database, table_name, column_name))
    return cursor.fetchone()[0] > 0


def run_migration():
    """Run the migration to add friend feature tables."""
    conn = None
    cursor = None
    
    try:
        # Connect to database
        config = get_mysql_config()
        logger.info(f"Connecting to database: {config['database']}")
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        logger.info("Starting migration: Add friend feature tables and soft delete support")
        
        # Step 1: Create friend_requests table
        logger.info("Step 1: Creating friend_requests table...")
        if table_exists(cursor, 'friend_requests', config['database']):
            logger.warning("Table 'friend_requests' already exists. Skipping creation.")
        else:
            cursor.execute("""
                CREATE TABLE friend_requests (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    sender_id INT NOT NULL,
                    recipient_id INT NOT NULL,
                    status ENUM('pending', 'accepted', 'rejected', 'cancelled') DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (recipient_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_request (sender_id, recipient_id),
                    INDEX idx_recipient_status (recipient_id, status),
                    INDEX idx_sender_status (sender_id, status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            logger.info("✓ Created friend_requests table")
        
        # Step 2: Create friendships table
        logger.info("Step 2: Creating friendships table...")
        if table_exists(cursor, 'friendships', config['database']):
            logger.warning("Table 'friendships' already exists. Skipping creation.")
        else:
            cursor.execute("""
                CREATE TABLE friendships (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    user1_id INT NOT NULL,
                    user2_id INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user1_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (user2_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_friendship (user1_id, user2_id),
                    INDEX idx_user1 (user1_id),
                    INDEX idx_user2 (user2_id),
                    CHECK (user1_id < user2_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            logger.info("✓ Created friendships table")
        
        # Step 3: Create recipe_shares table
        logger.info("Step 3: Creating recipe_shares table...")
        if table_exists(cursor, 'recipe_shares', config['database']):
            logger.warning("Table 'recipe_shares' already exists. Skipping creation.")
        else:
            cursor.execute("""
                CREATE TABLE recipe_shares (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    recipe_id INT NOT NULL,
                    shared_by_user_id INT NOT NULL,
                    shared_with_user_id INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
                    FOREIGN KEY (shared_by_user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (shared_with_user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_share (recipe_id, shared_by_user_id, shared_with_user_id),
                    INDEX idx_shared_with (shared_with_user_id),
                    INDEX idx_shared_by (shared_by_user_id),
                    INDEX idx_recipe (recipe_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            logger.info("✓ Created recipe_shares table")
        
        # Step 4: Create notifications table
        logger.info("Step 4: Creating notifications table...")
        if table_exists(cursor, 'notifications', config['database']):
            logger.warning("Table 'notifications' already exists. Skipping creation.")
        else:
            cursor.execute("""
                CREATE TABLE notifications (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    user_id INT NOT NULL,
                    notification_type ENUM('friend_request', 'recipe_shared') NOT NULL,
                    related_user_id INT,
                    recipe_id INT,
                    message TEXT,
                    `read` BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (related_user_id) REFERENCES users(id) ON DELETE SET NULL,
                    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
                    INDEX idx_user_read (user_id, `read`),
                    INDEX idx_user_created (user_id, created_at DESC)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            logger.info("✓ Created notifications table")
        
        # Step 5: Add deleted_at column to recipes table
        logger.info("Step 5: Adding deleted_at column to recipes table...")
        if column_exists(cursor, 'recipes', 'deleted_at', config['database']):
            logger.warning("Column 'deleted_at' already exists in recipes table. Skipping.")
        else:
            cursor.execute("""
                ALTER TABLE recipes 
                ADD COLUMN deleted_at TIMESTAMP NULL AFTER published_at
            """)
            logger.info("✓ Added deleted_at column to recipes table")
            
            # Add index on deleted_at for efficient queries
            cursor.execute("""
                ALTER TABLE recipes 
                ADD INDEX idx_deleted_at (deleted_at)
            """)
            logger.info("✓ Added index on deleted_at")
        
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
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == '__main__':
    logger.info("="*70)
    logger.info("MIGRATION: Add friend feature tables and soft delete support")
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

