"""
Migration script to add user types and roles system.
Run this after backing up your database.
"""
import logging
from datetime import datetime
from sqlalchemy import text
from db_config import get_db_connection

logger = logging.getLogger(__name__)

def migrate_user_types():
    """Add user types and roles to existing database."""
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
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 2. Create permissions table
        print("2. Creating permissions table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS permissions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                display_name VARCHAR(150) NOT NULL,
                description TEXT,
                category VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 3. Create user_type_permissions junction table
        print("3. Creating user_type_permissions table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_type_permissions (
                user_type_id INT NOT NULL,
                permission_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_type_id, permission_id),
                FOREIGN KEY (user_type_id) REFERENCES user_types(id) ON DELETE CASCADE,
                FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 4. Add user_type_id to users table
        print("4. Adding user_type_id to users table...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN user_type_id INT DEFAULT 1")
            cursor.execute("ALTER TABLE users ADD FOREIGN KEY (user_type_id) REFERENCES user_types(id)")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("   - user_type_id column already exists")
            else:
                raise e
        
        # 5. Insert default user types
        print("5. Inserting default user types...")
        user_types = [
            (1, 'guest', 'Guest', 'Limited read-only access to public recipes', True),
            (2, 'member', 'Member', 'Standard user with full recipe management', True),
            (3, 'premium', 'Premium', 'Enhanced features with advanced analytics', True),
            (4, 'moderator', 'Moderator', 'Can moderate public content and manage tags', True),
            (5, 'admin', 'Administrator', 'Full system administration access', True),
            (6, 'super_admin', 'Super Administrator', 'Complete system control', True)
        ]
        
        for user_type_id, name, display_name, description, is_active in user_types:
            cursor.execute("""
                INSERT IGNORE INTO user_types (id, name, display_name, description, is_active)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_type_id, name, display_name, description, is_active))
        
        # 6. Insert permissions
        print("6. Inserting permissions...")
        permissions = [
            # Recipe permissions
            ('view_public_recipes', 'View Public Recipes', 'Can view public recipes', 'recipes'),
            ('view_private_recipes', 'View Private Recipes', 'Can view private recipes', 'recipes'),
            ('create_recipes', 'Create Recipes', 'Can create new recipes', 'recipes'),
            ('edit_own_recipes', 'Edit Own Recipes', 'Can edit own recipes', 'recipes'),
            ('edit_all_recipes', 'Edit All Recipes', 'Can edit any recipe', 'recipes'),
            ('delete_own_recipes', 'Delete Own Recipes', 'Can delete own recipes', 'recipes'),
            ('delete_all_recipes', 'Delete All Recipes', 'Can delete any recipe', 'recipes'),
            ('publish_recipes', 'Publish Recipes', 'Can make recipes public', 'recipes'),
            
            # User management permissions
            ('view_users', 'View Users', 'Can view user list', 'users'),
            ('edit_users', 'Edit Users', 'Can edit user profiles', 'users'),
            ('delete_users', 'Delete Users', 'Can delete user accounts', 'users'),
            ('manage_user_types', 'Manage User Types', 'Can assign user types', 'users'),
            
            # System permissions
            ('manage_tags', 'Manage Tags', 'Can create, edit, and delete tags', 'system'),
            ('moderate_content', 'Moderate Content', 'Can moderate public content', 'system'),
            ('view_analytics', 'View Analytics', 'Can view system analytics', 'system'),
            ('manage_system', 'Manage System', 'Can manage system settings', 'system'),
            
            # Advanced features
            ('unlimited_collections', 'Unlimited Collections', 'Can create unlimited collections', 'features'),
            ('advanced_search', 'Advanced Search', 'Access to advanced search features', 'features'),
            ('bulk_operations', 'Bulk Operations', 'Can perform bulk operations', 'features'),
            ('api_access', 'API Access', 'Can access API endpoints', 'features')
        ]
        
        for name, display_name, description, category in permissions:
            cursor.execute("""
                INSERT IGNORE INTO permissions (name, display_name, description, category)
                VALUES (%s, %s, %s, %s)
            """, (name, display_name, description, category))
        
        # 7. Assign permissions to user types
        print("7. Assigning permissions to user types...")
        
        # Guest permissions
        guest_permissions = ['view_public_recipes']
        for perm_name in guest_permissions:
            cursor.execute("""
                INSERT IGNORE INTO user_type_permissions (user_type_id, permission_id)
                SELECT 1, id FROM permissions WHERE name = %s
            """, (perm_name,))
        
        # Member permissions
        member_permissions = [
            'view_public_recipes', 'view_private_recipes', 'create_recipes', 
            'edit_own_recipes', 'delete_own_recipes', 'publish_recipes'
        ]
        for perm_name in member_permissions:
            cursor.execute("""
                INSERT IGNORE INTO user_type_permissions (user_type_id, permission_id)
                SELECT 2, id FROM permissions WHERE name = %s
            """, (perm_name,))
        
        # Premium permissions (includes all member permissions + more)
        premium_permissions = member_permissions + [
            'unlimited_collections', 'advanced_search', 'bulk_operations', 'view_analytics'
        ]
        for perm_name in premium_permissions:
            cursor.execute("""
                INSERT IGNORE INTO user_type_permissions (user_type_id, permission_id)
                SELECT 3, id FROM permissions WHERE name = %s
            """, (perm_name,))
        
        # Moderator permissions (includes premium + moderation)
        moderator_permissions = premium_permissions + [
            'manage_tags', 'moderate_content', 'view_users'
        ]
        for perm_name in moderator_permissions:
            cursor.execute("""
                INSERT IGNORE INTO user_type_permissions (user_type_id, permission_id)
                SELECT 4, id FROM permissions WHERE name = %s
            """, (perm_name,))
        
        # Admin permissions (includes moderator + user management)
        admin_permissions = moderator_permissions + [
            'edit_users', 'delete_users', 'manage_user_types', 'manage_system'
        ]
        for perm_name in admin_permissions:
            cursor.execute("""
                INSERT IGNORE INTO user_type_permissions (user_type_id, permission_id)
                SELECT 5, id FROM permissions WHERE name = %s
            """, (perm_name,))
        
        # Super Admin permissions (all permissions)
        cursor.execute("""
            INSERT IGNORE INTO user_type_permissions (user_type_id, permission_id)
            SELECT 6, id FROM permissions
        """)
        
        # 8. Update existing users
        print("8. Updating existing users...")
        
        # Set existing admin users to admin type
        cursor.execute("""
            UPDATE users SET user_type_id = 5 WHERE is_admin = TRUE
        """)
        
        # Set all other users to member type
        cursor.execute("""
            UPDATE users SET user_type_id = 2 WHERE is_admin = FALSE OR is_admin IS NULL
        """)
        
        # 9. Create indexes for performance
        print("9. Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_user_type ON users(user_type_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_type_permissions ON user_type_permissions(user_type_id, permission_id)")
        
        conn.commit()
        print("✅ User types migration completed successfully!")
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT name, COUNT(*) FROM user_types ut LEFT JOIN users u ON ut.id = u.user_type_id GROUP BY ut.id, ut.name")
        type_counts = cursor.fetchall()
        
        print(f"\n📊 Migration Summary:")
        print(f"   Total users: {user_count}")
        for type_name, count in type_counts:
            print(f"   {type_name.title()}: {count} users")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate_user_types()
