#!/usr/bin/env python3
"""
Migrate existing JSON recipe data to MySQL database.
"""
import sys
import os
from pathlib import Path
import json
import re
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import mysql.connector
from mysql.connector import Error
import db_config


def parse_ingredient_description(description):
    """
    Parse ingredient description to extract name.
    Simple heuristic - actual ingredient is usually at the end.
    """
    # Remove common preparations
    desc = description.lower().strip()
    
    # Common preparations to remove
    preparations = [
        'diced', 'chopped', 'minced', 'sliced', 'grated', 'shredded',
        'fresh', 'frozen', 'canned', 'dried', 'cooked', 'raw',
        'room temperature', 'softened', 'melted', 'beaten',
        'finely', 'coarsely', 'thinly', 'thickly'
    ]
    
    # Split and clean
    words = desc.split()
    
    # Remove preparation words from the start
    while words and words[0] in preparations:
        words.pop(0)
    
    # The remaining is likely the ingredient name
    return ' '.join(words) if words else description


def get_or_create_ingredient(cursor, description):
    """
    Get existing ingredient or create new one.
    Returns ingredient_id.
    """
    # Parse ingredient name
    ingredient_name = parse_ingredient_description(description)
    
    # Check if ingredient exists
    cursor.execute("""
        SELECT id FROM ingredients WHERE name = %s
    """, (ingredient_name,))
    
    result = cursor.fetchone()
    if result:
        return result[0]
    
    # Create new ingredient
    cursor.execute("""
        INSERT INTO ingredients (name, is_common)
        VALUES (%s, %s)
    """, (ingredient_name, False))
    
    return cursor.lastrowid


def migrate_recipes(default_user_id=None):
    """Migrate recipes from JSON to MySQL."""
    try:
        conn = mysql.connector.connect(**db_config.get_mysql_config())
        cursor = conn.cursor()
        
        # If no default user, create a migration user
        if not default_user_id:
            print("\n[1/5] Creating default migration user...")
            import bcrypt
            password_hash = bcrypt.hashpw('migration123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, display_name, email_verified)
                VALUES (%s, %s, %s, %s, %s)
            """, ('admin', 'admin@recipe-editor.local', password_hash, 'Administrator', True))
            default_user_id = cursor.lastrowid
            
            # Create user preferences and stats
            cursor.execute("INSERT INTO user_preferences (user_id) VALUES (%s)", (default_user_id,))
            cursor.execute("INSERT INTO user_stats (user_id) VALUES (%s)", (default_user_id,))
            
            print(f"✓ Created user 'admin' (ID: {default_user_id})")
            print(f"  Default password: migration123 (CHANGE THIS!)")
        
        # Get JSON recipe files
        recipes_dir = Path('data/recipes')
        recipe_files = list(recipes_dir.glob('*.json'))
        
        print(f"\n[2/5] Found {len(recipe_files)} recipe files to migrate")
        
        migrated = 0
        errors = 0
        
        print("\n[3/5] Migrating recipes...")
        for recipe_file in recipe_files:
            try:
                with open(recipe_file, 'r') as f:
                    recipe_data = json.load(f)
                
                # Insert recipe
                cursor.execute("""
                    INSERT INTO recipes 
                    (user_id, name, instructions, notes, visibility, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    default_user_id,
                    recipe_data.get('name', 'Untitled Recipe'),
                    recipe_data.get('instructions', ''),
                    recipe_data.get('notes', ''),
                    'public',  # Default to public for migrated recipes
                    recipe_data.get('created_at', datetime.now().isoformat()),
                    recipe_data.get('updated_at', datetime.now().isoformat())
                ))
                
                recipe_id = cursor.lastrowid
                
                # Insert source information
                source = recipe_data.get('source', {})
                if source and source.get('name'):
                    cursor.execute("""
                        INSERT INTO recipe_sources
                        (recipe_id, source_name, source_url, author, issue, imported_from)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        recipe_id,
                        source.get('name', ''),
                        source.get('url', ''),
                        source.get('author', ''),
                        source.get('issue', ''),
                        'manual'
                    ))
                
                # Insert ingredients
                for i, ing in enumerate(recipe_data.get('ingredients', [])):
                    description = ing.get('description', '').strip()
                    if not description:
                        continue
                    
                    # Get or create ingredient
                    ingredient_id = get_or_create_ingredient(cursor, description)
                    
                    # Insert recipe-ingredient relationship
                    cursor.execute("""
                        INSERT INTO recipe_ingredients
                        (recipe_id, ingredient_id, amount, unit, sort_order)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        recipe_id,
                        ingredient_id,
                        ing.get('amount', ''),
                        ing.get('unit', ''),
                        i
                    ))
                
                # Insert tags
                for tag_name in recipe_data.get('tags', []):
                    if not tag_name:
                        continue
                    
                    tag_name = tag_name.upper().strip()
                    slug = tag_name.lower().replace(' ', '-')
                    
                    # Get or create tag
                    cursor.execute("SELECT id FROM tags WHERE name = %s", (tag_name,))
                    result = cursor.fetchone()
                    
                    if result:
                        tag_id = result[0]
                    else:
                        cursor.execute("""
                            INSERT INTO tags (name, slug) VALUES (%s, %s)
                        """, (tag_name, slug))
                        tag_id = cursor.lastrowid
                    
                    # Link tag to recipe
                    cursor.execute("""
                        INSERT IGNORE INTO recipe_tags (recipe_id, tag_id)
                        VALUES (%s, %s)
                    """, (recipe_id, tag_id))
                
                # Initialize recipe stats
                cursor.execute("""
                    INSERT INTO recipe_stats (recipe_id) VALUES (%s)
                """, (recipe_id,))
                
                migrated += 1
                print(f"✓ Migrated: {recipe_data.get('name', 'Unknown')} ({recipe_file.name})")
                
            except Exception as e:
                errors += 1
                print(f"✗ Error migrating {recipe_file.name}: {e}")
        
        conn.commit()
        
        print(f"\n[4/5] Updating statistics...")
        
        # Update ingredient usage counts
        cursor.execute("""
            UPDATE ingredients i
            SET usage_count = (
                SELECT COUNT(*) FROM recipe_ingredients ri
                WHERE ri.ingredient_id = i.id
            )
        """)
        
        # Update user stats
        cursor.execute("""
            UPDATE user_stats us
            SET 
                recipe_count = (SELECT COUNT(*) FROM recipes WHERE user_id = us.user_id),
                public_recipe_count = (SELECT COUNT(*) FROM recipes WHERE user_id = us.user_id AND visibility = 'public')
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"\n[5/5] Migration Summary:")
        print(f"  ✓ Recipes migrated: {migrated}")
        if errors > 0:
            print(f"  ✗ Errors: {errors}")
        
        print("\n" + "=" * 70)
        print("✅ Migration complete!")
        print("=" * 70)
        
        return True
        
    except Error as e:
        print(f"\n✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\nThis script will migrate your JSON recipes to MySQL.")
    print("Make sure you've run init_database.py first!\n")
    
    proceed = input("Continue with migration? (y/N): ").lower().strip()
    if proceed != 'y':
        print("Migration cancelled.")
        sys.exit(0)
    
    success = migrate_recipes()
    sys.exit(0 if success else 1)

