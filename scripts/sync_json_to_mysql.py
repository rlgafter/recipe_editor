#!/usr/bin/env python3
"""
Synchronize JSON recipe data to MySQL database.
This script imports recipes, ingredients, tags, and all relationships.
"""

import sys
import os
import mysql.connector
import json
from pathlib import Path

# Load environment variables
def load_env():
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key.startswith('export '):
                        key = key[7:]
                    os.environ[key] = value

def get_db_connection():
    """Get database connection."""
    load_env()
    config = {
        'host': os.environ.get('RECIPE_DB_HOSTNAME', 'localhost'),
        'port': int(os.environ.get('RECIPE_DB_PORT', 3306)),
        'user': os.environ.get('RECIPE_DB_USER_NAME', 'recipe_user'),
        'password': os.environ.get('RECIPE_DB_USER_PW', ''),
        'database': os.environ.get('RECIPE_DB_DATABASE_NAME', 'recipe_editor'),
        'charset': 'utf8mb4'
    }
    return mysql.connector.connect(**config)

def sync_ingredients():
    """Import ingredients from JSON files to database."""
    print("Importing ingredients...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    json_files = sorted(Path('data/recipes').glob('recipe_*.json'))
    processed = 0
    
    for json_file in json_files:
        with open(json_file, 'r') as f:
            recipe_data = json.load(f)
        
        # Get recipe ID
        cursor.execute("SELECT id FROM recipes WHERE name = %s LIMIT 1", (recipe_data['name'],))
        recipe_row = cursor.fetchone()
        if not recipe_row:
            continue
        
        recipe_id = recipe_row[0]
        
        # Process ingredients
        if 'ingredients' in recipe_data and recipe_data['ingredients']:
            for idx, ing in enumerate(recipe_data['ingredients']):
                ingredient_name = ing['description'].strip()
                amount = ing.get('amount', '').strip()
                unit = ing.get('unit', '').strip()
                
                # Find or create ingredient
                cursor.execute("SELECT id FROM ingredients WHERE name = %s LIMIT 1", (ingredient_name,))
                ing_row = cursor.fetchone()
                
                if ing_row:
                    ingredient_id = ing_row[0]
                else:
                    cursor.execute(
                        "INSERT INTO ingredients (name, plural_name) VALUES (%s, %s)",
                        (ingredient_name, ingredient_name)
                    )
                    ingredient_id = cursor.lastrowid
                
                # Insert recipe_ingredient
                cursor.execute(
                    """INSERT INTO recipe_ingredients 
                       (recipe_id, ingredient_id, amount, unit, order_index)
                       VALUES (%s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE 
                       amount = VALUES(amount), unit = VALUES(unit), order_index = VALUES(order_index)""",
                    (recipe_id, ingredient_id, amount, unit, idx)
                )
        
        processed += 1
        print(f"  Processed {json_file.name}")
    
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✓ Imported ingredients for {processed} recipes\n")

def sync_tags():
    """Import tags from JSON to database."""
    print("Importing tags...")
    
    # Build recipe mapping
    recipe_map = {}
    json_files = sorted(Path('data/recipes').glob('recipe_*.json'))
    for json_file in json_files:
        with open(json_file, 'r') as f:
            data = json.load(f)
            recipe_map[data['id']] = data['name']
    
    # Load tags
    with open('data/tags.json', 'r') as f:
        tags_data = json.load(f)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get DB recipe IDs by name
    cursor.execute("SELECT id, name FROM recipes")
    db_recipes = {row[1]: row[0] for row in cursor.fetchall()}
    
    for tag_name, tag_data in tags_data.items():
        # Get/create tag
        cursor.execute("SELECT id FROM tags WHERE name = %s", (tag_name,))
        tag_row = cursor.fetchone()
        
        if tag_row:
            tag_id = tag_row[0]
        else:
            slug = tag_name.lower().replace(' ', '-')
            cursor.execute("INSERT INTO tags (name, slug) VALUES (%s, %s)", (tag_name, slug))
            tag_id = cursor.lastrowid
        
        # Tag each recipe
        for recipe_json_id in tag_data['recipes']:
            recipe_name = recipe_map.get(recipe_json_id)
            if recipe_name:
                db_recipe_id = db_recipes.get(recipe_name)
                if db_recipe_id:
                    cursor.execute(
                        "INSERT IGNORE INTO recipe_tags (recipe_id, tag_id) VALUES (%s, %s)",
                        (db_recipe_id, tag_id)
                    )
    
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✓ Imported {len(tags_data)} tags\n")

def main():
    """Main synchronization function."""
    print("=" * 70)
    print("JSON TO MYSQL DATABASE SYNCHRONIZATION")
    print("=" * 70)
    
    try:
        sync_ingredients()
        sync_tags()
        
        # Final verification
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM recipe_ingredients")
        ing_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM recipe_tags")
        tag_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        print("=" * 70)
        print("SYNCHRONIZATION COMPLETE")
        print("=" * 70)
        print(f"✓ Total ingredients imported: {ing_count}")
        print(f"✓ Total recipe-tag relationships: {tag_count}")
        print("\n✅ Database now fully reflects JSON file data!")
        
    except Exception as e:
        print(f"\n❌ Error during synchronization: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
