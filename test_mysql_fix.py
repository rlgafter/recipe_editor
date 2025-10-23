#!/usr/bin/env python3
"""
Test MySQL connection with different approaches
"""
import os
import mysql.connector
from mysql.connector import Error

def test_connection_approaches():
    """Test different connection approaches"""
    
    host = os.environ.get('RECIPE_DB_HOSTNAME', 'localhost')
    port = int(os.environ.get('RECIPE_DB_PORT', 3306))
    database = os.environ.get('RECIPE_DB_DATABASE_NAME', 'recipe_editor')
    user = os.environ.get('RECIPE_DB_USER_NAME', 'recipe_user')
    password = os.environ.get('RECIPE_DB_USER_PW', '')
    
    print("Testing different connection approaches...")
    
    # Approach 1: Without database first
    print("\n1. Connecting without database...")
    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password
        )
        print("✅ Connected to MySQL server")
        
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SHOW DATABASES LIKE %s", (database,))
        if cursor.fetchone():
            print(f"✅ Database '{database}' exists")
        else:
            print(f"❌ Database '{database}' does not exist")
            print(f"   Create it with: CREATE DATABASE {database};")
        
        # Check user permissions
        cursor.execute("SELECT User, Host FROM mysql.user WHERE User = %s", (user,))
        users = cursor.fetchall()
        if users:
            print(f"✅ User '{user}' exists:")
            for u in users:
                print(f"   - {u[0]}@{u[1]}")
        else:
            print(f"❌ User '{user}' does not exist")
            print(f"   Create with: CREATE USER '{user}'@'%' IDENTIFIED BY 'password';")
        
        cursor.close()
        conn.close()
        return True
        
    except Error as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    # Load environment
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.strip().split('=', 1)
                    if key.startswith('export '):
                        key = key[7:]
                    os.environ[key] = value
    
    test_connection_approaches()
