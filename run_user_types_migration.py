#!/usr/bin/env python3
"""
Script to run the user types migration.
Run this after backing up your database.
"""
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from migrate_user_types_simple import migrate_user_types

if __name__ == "__main__":
    print("🚀 Starting User Types Migration")
    print("=" * 50)
    print("⚠️  IMPORTANT: Make sure you have backed up your database!")
    print("=" * 50)
    
    response = input("Have you backed up your database? (yes/no): ").lower().strip()
    if response != 'yes':
        print("❌ Please backup your database first and run this script again.")
        sys.exit(1)
    
    try:
        migrate_user_types()
        print("\n🎉 Migration completed successfully!")
        print("\nNext steps:")
        print("1. Update your Flask app to use the new user types system")
        print("2. Test the new permission system")
        print("3. Update your templates to show user types")
        print("4. Configure admin routes in your main app")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("Please check the error and try again.")
        sys.exit(1)
