#!/usr/bin/env python3
"""
Script to remove all tags from all existing recipes.

This script removes all tag associations from recipes while keeping
the tags themselves in the database (in case they're needed later).
"""

import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_config import get_database_uri, SQLALCHEMY_ENGINE_OPTIONS
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def remove_all_recipe_tags():
    """Remove all tag associations from all recipes."""
    engine = create_engine(get_database_uri(), **SQLALCHEMY_ENGINE_OPTIONS)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Count existing tag associations
        result = session.execute(text("SELECT COUNT(*) FROM recipe_tags"))
        count_before = result.scalar()
        
        if count_before == 0:
            print("No recipe tags found. Nothing to remove.")
            return
        
        print(f"Found {count_before} tag associations to remove.")
        
        # Remove all tag associations
        session.execute(text("DELETE FROM recipe_tags"))
        session.commit()
        
        print(f"✓ Successfully removed {count_before} tag associations from recipes.")
        print("Note: Tags themselves remain in the database (not deleted).")
        
    except Exception as e:
        session.rollback()
        print(f"✗ Error removing tags: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == '__main__':
    print("=" * 70)
    print("Remove All Recipe Tags")
    print("=" * 70)
    print()
    
    # Confirm before proceeding
    response = input("This will remove ALL tags from ALL recipes. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Operation cancelled.")
        sys.exit(0)
    
    print()
    remove_all_recipe_tags()
    print()
    print("=" * 70)
    print("Done!")
    print("=" * 70)


