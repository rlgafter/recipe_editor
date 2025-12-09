#!/usr/bin/env python3
"""
Migration: Add pending_recipe_shares table
- Creates pending_recipe_shares table for tracking pending recipe shares
"""

import sys
import logging
from datetime import datetime
import mysql.connector
from mysql.connector import Error
from db_config import get_mysql_config

# Setup logging
log_filename = f"logs/migration_add_pending_shares_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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


def main():
    """Run the migration."""
    config = get_mysql_config()
    database = config['database']
    
    try:
        conn = mysql.connector.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=database
        )
        cursor = conn.cursor()
        
        logger.info("=" * 70)
        logger.info("Migration: Add pending_recipe_shares table")
        logger.info("=" * 70)
        
        # Check if table already exists
        if table_exists(cursor, 'pending_recipe_shares', database):
            logger.info("Table 'pending_recipe_shares' already exists. Skipping creation.")
            return 0
        
        logger.info("Creating pending_recipe_shares table...")
        
        cursor.execute("""
            CREATE TABLE pending_recipe_shares (
                id INT AUTO_INCREMENT PRIMARY KEY,
                recipe_id INT NOT NULL,
                shared_by_user_id INT NOT NULL,
                shared_with_user_id INT NULL,
                recipient_email VARCHAR(255) NULL,
                friend_request_id INT NULL,
                token VARCHAR(255) NULL,
                status ENUM('pending', 'accepted', 'rejected') NOT NULL DEFAULT 'pending',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
                FOREIGN KEY (shared_by_user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (shared_with_user_id) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY (friend_request_id) REFERENCES friend_requests(id) ON DELETE CASCADE,
                INDEX idx_pending_share_email (recipient_email),
                INDEX idx_pending_share_token (token),
                INDEX idx_pending_share_status (status),
                UNIQUE KEY unique_token (token)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        conn.commit()
        logger.info("✓ Created pending_recipe_shares table successfully")
        
        cursor.close()
        conn.close()
        
        logger.info("=" * 70)
        logger.info("Migration completed successfully!")
        logger.info("=" * 70)
        return 0
        
    except Error as e:
        logger.error(f"Database error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())


