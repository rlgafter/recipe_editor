"""
Migration script to add simple user types system.
Creates user_types table and migrates existing users.
"""
import logging
from datetime import datetime
from sqlalchemy import text
from db_config import get_db_connection

logger = logging.getLogger(__name__)

def migrate_user_types():
    """Add user types system to existing database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        print("Starting user types migration...")
        
        # 1. Create user_types table
        print("1. Creating user_types table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_types (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL,
                display_name VARCHAR(100) NOT NULL,
                description TEXT,
                can_view_recipes BOOLEAN DEFAULT TRUE,
                can_create_recipes BOOLEAN DEFAULT FALSE,
                can_edit_all_recipes BOOLEAN DEFAULT FALSE,
                can_delete_all_recipes BOOLEAN DEFAULT FALSE,
                can_manage_users BOOLEAN DEFAULT FALSE,
                can_manage_system BOOLEAN DEFAULT FALSE,
                can_share_recipes BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 2. Insert the four user types
        print("2. Inserting user types...")
        user_types = [
            (1, 'unvalidated', 'Unvalidated User', 'Can view public recipes only', 
             True, False, False, False, False, False, False, True),
            (2, 'validated', 'Validated User', 'Can view and create recipes', 
             True, True, False, False, False, False, False, True),
            (3, 'share_recipes', 'Share Recipes User', 'Can view, create, and share recipes', 
             True, True, False, False, False, False, True, True),
            (4, 'admin', 'Administrator', 'Full system access', 
             True, True, True, True, True, True, True, True)
        ]
        
        for user_type in user_types:
            cursor.execute("""
                INSERT IGNORE INTO user_types (
                    id, name, display_name, description,
                    can_view_recipes, can_create_recipes, can_edit_all_recipes,
                    can_delete_all_recipes, can_manage_users, can_manage_system,
                    can_share_recipes, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, user_type)
        
        # 3. Add user_type_id to users table
        print("3. Adding user_type_id to users table...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN user_type_id INT DEFAULT 1")
            cursor.execute("ALTER TABLE users ADD FOREIGN KEY (user_type_id) REFERENCES user_types(id)")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("   - user_type_id column already exists")
            else:
                raise e
        
        # 4. Update existing users
        print("4. Updating existing users...")
        
        # Set existing admin users to admin type (id=4)
        cursor.execute("""
            UPDATE users SET user_type_id = 4 WHERE is_admin = TRUE
        """)
        
        # Set all other users to validated type (id=2)
        cursor.execute("""
            UPDATE users SET user_type_id = 2 WHERE is_admin = FALSE OR is_admin IS NULL
        """)
        
        # 5. Create indexes for performance
        print("5. Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_user_type ON users(user_type_id)")
        
        conn.commit()
        print("✅ User types migration completed successfully!")
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT ut.name, ut.display_name, COUNT(u.id) as user_count 
            FROM user_types ut 
            LEFT JOIN users u ON ut.id = u.user_type_id 
            GROUP BY ut.id, ut.name, ut.display_name 
            ORDER BY ut.id
        """)
        type_counts = cursor.fetchall()
        
        print(f"\n📊 Migration Summary:")
        print(f"   Total users: {user_count}")
        for type_name, display_name, count in type_counts:
            print(f"   {display_name}: {count} users")
        
        print(f"\n🔧 User Type Permissions:")
        cursor.execute("""
            SELECT name, display_name, can_view_recipes, can_create_recipes, 
                   can_edit_all_recipes, can_delete_all_recipes, can_manage_users, 
                   can_manage_system, can_share_recipes
            FROM user_types ORDER BY id
        """)
        permissions = cursor.fetchall()
        
        for perm in permissions:
            name, display, view, create, edit_all, delete_all, manage_users, manage_system, share = perm
            print(f"\n   {display} ({name}):")
            print(f"     - View recipes: {view}")
            print(f"     - Create recipes: {create}")
            print(f"     - Edit all recipes: {edit_all}")
            print(f"     - Delete all recipes: {delete_all}")
            print(f"     - Manage users: {manage_users}")
            print(f"     - Manage system: {manage_system}")
            print(f"     - Share recipes: {share}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate_user_types()
