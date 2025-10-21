#!/usr/bin/env python3
"""
Create a new user account.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import bcrypt
import mysql.connector
import db_config
from getpass import getpass


def create_user(username, email, password, is_admin=False):
    """Create a new user in the database."""
    try:
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Connect to database
        conn = mysql.connector.connect(**db_config.get_mysql_config())
        cursor = conn.cursor()
        
        # Insert user
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, display_name, email_verified, is_admin)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (username, email, password_hash, username, True, is_admin))
        
        user_id = cursor.lastrowid
        
        # Create user preferences
        cursor.execute("""
            INSERT INTO user_preferences (user_id) VALUES (%s)
        """, (user_id,))
        
        # Create user stats
        cursor.execute("""
            INSERT INTO user_stats (user_id) VALUES (%s)
        """, (user_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ User created successfully!")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        print(f"   Admin: {'Yes' if is_admin else 'No'}")
        print(f"   User ID: {user_id}")
        return True
        
    except mysql.connector.Error as e:
        print(f"✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Main function."""
    print("=" * 70)
    print("Recipe Editor - Create User")
    print("=" * 70)
    
    # Get user input
    print("\nEnter user details:")
    username = input("Username: ").strip()
    email = input("Email: ").strip()
    password = getpass("Password: ")
    password_confirm = getpass("Confirm password: ")
    
    if password != password_confirm:
        print("✗ Passwords do not match!")
        return False
    
    if len(password) < 8:
        print("✗ Password must be at least 8 characters!")
        return False
    
    if not username or not email:
        print("✗ Username and email are required!")
        return False
    
    # Ask if admin
    is_admin = input("\nMake this user an admin? (y/N): ").lower().strip() == 'y'
    
    print(f"\nCreating user '{username}'...")
    return create_user(username, email, password, is_admin)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

