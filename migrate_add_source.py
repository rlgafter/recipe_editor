#!/usr/bin/env python3
"""
Migration script to add source fields to existing recipes.
This script adds a 'source' object with default values to all recipes that don't have one.
"""
import json
import os
from pathlib import Path
from datetime import datetime


def migrate_recipes():
    """Add source fields to all existing recipe files."""
    recipes_dir = Path("data/recipes")
    
    if not recipes_dir.exists():
        print("Error: data/recipes directory not found")
        return
    
    recipe_files = list(recipes_dir.glob("recipe_*.json"))
    
    if not recipe_files:
        print("No recipe files found to migrate")
        return
    
    print(f"Found {len(recipe_files)} recipe files to process")
    print("-" * 60)
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for recipe_file in sorted(recipe_files):
        try:
            # Read the recipe file
            with open(recipe_file, 'r', encoding='utf-8') as f:
                recipe_data = json.load(f)
            
            recipe_id = recipe_data.get('id', recipe_file.name)
            recipe_name = recipe_data.get('name', 'Unknown')
            
            # Check if source field already exists
            if 'source' in recipe_data:
                print(f"✓ Skipped {recipe_id} ({recipe_name}) - already has source field")
                skipped_count += 1
                continue
            
            # Add source field with default values
            recipe_data['source'] = {
                'name': 'Ricki',
                'url': '',
                'author': '',
                'issue': ''
            }
            
            # Write the updated recipe back to file
            with open(recipe_file, 'w', encoding='utf-8') as f:
                json.dump(recipe_data, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Updated {recipe_id} ({recipe_name})")
            updated_count += 1
            
        except json.JSONDecodeError as e:
            print(f"✗ Error reading {recipe_file.name}: Invalid JSON - {e}")
            error_count += 1
        except Exception as e:
            print(f"✗ Error processing {recipe_file.name}: {e}")
            error_count += 1
    
    print("-" * 60)
    print(f"\nMigration complete!")
    print(f"  Updated: {updated_count} recipes")
    print(f"  Skipped: {skipped_count} recipes (already have source)")
    print(f"  Errors:  {error_count} recipes")
    
    # Create a log file
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"migration_add_source_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"Migration run at: {datetime.now().isoformat()}\n")
        f.write(f"Updated: {updated_count}\n")
        f.write(f"Skipped: {skipped_count}\n")
        f.write(f"Errors: {error_count}\n")
    
    print(f"\nLog saved to: {log_file}")


if __name__ == "__main__":
    print("Recipe Source Field Migration")
    print("=" * 60)
    print("This will add source fields to all existing recipes")
    print("Default source name: 'Ricki'")
    print("=" * 60)
    print()
    
    migrate_recipes()

