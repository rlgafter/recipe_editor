#!/usr/bin/env python3
"""
Migration: Convert existing tags to personal tags per user
- For each tag, creates a personal copy for each user who has recipes with that tag
- Updates recipe_tags associations to point to user's personal tag
- Deletes original tags after migration
"""

import sys
import logging
from datetime import datetime
from collections import defaultdict
import mysql.connector
from mysql.connector import Error
from db_config import get_mysql_config

# Setup logging
log_filename = f"logs/migration_tags_to_personal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
    """Run the migration to convert tags to personal tags per user."""
    conn = None
    cursor = None
    
    try:
        # Connect to database
        config = get_mysql_config()
        logger.info(f"Connecting to database: {config['database']}")
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor(dictionary=True)
        
        logger.info("Starting migration: Convert tags to personal tags per user")
        
        # Check if migration is needed
        cursor.execute("SELECT COUNT(*) as count FROM tags WHERE tag_scope = 'system'")
        system_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM tags WHERE user_id IS NOT NULL")
        assigned_count = cursor.fetchone()['count']
        
        if assigned_count > 0:
            logger.warning(f"Found {assigned_count} tags already assigned to users.")
            response = input("This migration may have been run before. Continue anyway? (yes/no): ").strip().lower()
            if response != 'yes':
                logger.info("Migration cancelled by user.")
                return
        
        # Step 1: Get all existing tags with no user_id
        logger.info("Step 1: Fetching existing tags...")
        cursor.execute("""
            SELECT id, name, slug, description, tag_type, icon, created_at
            FROM tags
            WHERE user_id IS NULL
            ORDER BY id
        """)
        existing_tags = cursor.fetchall()
        logger.info(f"Found {len(existing_tags)} existing tags to migrate")
        
        if len(existing_tags) == 0:
            logger.info("No tags to migrate. Exiting.")
            return True
        
        # Step 2: For each tag, find which users have recipes using it
        logger.info("Step 2: Analyzing tag usage by user...")
        tag_users = defaultdict(set)  # tag_id -> set of user_ids
        
        for tag in existing_tags:
            tag_id = tag['id']
            tag_name = tag['name']
            
            cursor.execute("""
                SELECT DISTINCT r.user_id
                FROM recipes r
                JOIN recipe_tags rt ON r.id = rt.recipe_id
                WHERE rt.tag_id = %s
            """, (tag_id,))
            
            users = cursor.fetchall()
            for user in users:
                tag_users[tag_id].add(user['user_id'])
            
            logger.info(f"  Tag '{tag_name}' (ID: {tag_id}) used by {len(users)} user(s)")
        
        # Step 3: Create personal tag copies and update associations
        logger.info("Step 3: Creating personal tag copies and updating associations...")
        
        tag_mapping = {}  # (old_tag_id, user_id) -> new_tag_id
        created_count = 0
        updated_count = 0
        
        for tag in existing_tags:
            old_tag_id = tag['id']
            tag_name = tag['name']
            
            if old_tag_id not in tag_users or len(tag_users[old_tag_id]) == 0:
                logger.info(f"  Tag '{tag_name}' has no users, will be deleted")
                continue
            
            for user_id in tag_users[old_tag_id]:
                # Create personal tag for this user
                cursor.execute("""
                    INSERT INTO tags (name, slug, description, tag_type, icon, tag_scope, user_id, created_at)
                    VALUES (%s, %s, %s, %s, %s, 'personal', %s, %s)
                """, (
                    tag['name'],
                    tag['slug'],
                    tag['description'],
                    tag['tag_type'],
                    tag['icon'],
                    user_id,
                    tag['created_at']
                ))
                
                new_tag_id = cursor.lastrowid
                tag_mapping[(old_tag_id, user_id)] = new_tag_id
                created_count += 1
                
                logger.info(f"  Created personal tag '{tag_name}' for user {user_id} (new ID: {new_tag_id})")
                
                # Update recipe_tags associations for this user's recipes
                cursor.execute("""
                    UPDATE recipe_tags rt
                    JOIN recipes r ON rt.recipe_id = r.id
                    SET rt.tag_id = %s
                    WHERE rt.tag_id = %s AND r.user_id = %s
                """, (new_tag_id, old_tag_id, user_id))
                
                affected = cursor.rowcount
                updated_count += affected
                logger.info(f"    Updated {affected} recipe associations")
        
        # Step 4: Delete original tags
        logger.info("Step 4: Deleting original tags...")
        cursor.execute("""
            DELETE FROM tags
            WHERE user_id IS NULL
        """)
        deleted_count = cursor.rowcount
        logger.info(f"✓ Deleted {deleted_count} original tags")
        
        # Commit transaction
        conn.commit()
        
        logger.info("="*70)
        logger.info("Migration Summary:")
        logger.info(f"  - Original tags processed: {len(existing_tags)}")
        logger.info(f"  - Personal tags created: {created_count}")
        logger.info(f"  - Recipe associations updated: {updated_count}")
        logger.info(f"  - Original tags deleted: {deleted_count}")
        logger.info("="*70)
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
    logger.info("MIGRATION: Convert existing tags to personal tags per user")
    logger.info("="*70)
    logger.info("")
    logger.info("This migration will:")
    logger.info("  1. Analyze which users use each tag")
    logger.info("  2. Create personal tag copies for each user")
    logger.info("  3. Update recipe associations")
    logger.info("  4. Delete original tags")
    logger.info("")
    logger.info("="*70)
    
    response = input("Proceed with migration? (yes/no): ").strip().lower()
    if response != 'yes':
        logger.info("Migration cancelled by user.")
        sys.exit(0)
    
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

