#!/usr/bin/env python3
"""
MySQL Database Connection Troubleshooting Script
"""
import os
import sys
import socket
import mysql.connector
from mysql.connector import Error

def test_network_connectivity():
    """Test if we can reach the MySQL server"""
    print("=== Network Connectivity Test ===")
    
    host = os.environ.get('RECIPE_DB_HOSTNAME', 'localhost')
    port = int(os.environ.get('RECIPE_DB_PORT', 3306))
    
    print(f"Testing connection to {host}:{port}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ Network connection to {host}:{port} successful")
            return True
        else:
            print(f"❌ Cannot connect to {host}:{port} - Port may be closed or firewall blocking")
            return False
    except Exception as e:
        print(f"❌ Network error: {e}")
        return False

def test_mysql_connection():
    """Test MySQL connection with detailed error reporting"""
    print("\n=== MySQL Connection Test ===")
    
    host = os.environ.get('RECIPE_DB_HOSTNAME', 'localhost')
    port = int(os.environ.get('RECIPE_DB_PORT', 3306))
    database = os.environ.get('RECIPE_DB_DATABASE_NAME', 'recipe_editor')
    user = os.environ.get('RECIPE_DB_USER_NAME', 'recipe_user')
    password = os.environ.get('RECIPE_DB_USER_PW', '')
    
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Database: {database}")
    print(f"User: {user}")
    print(f"Password: {'*' * len(password) if password else '(empty)'}")
    
    try:
        # Test connection without database first
        print("\n1. Testing connection to MySQL server (no database)...")
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password
        )
        print("✅ Connected to MySQL server successfully")
        
        # Test database access
        print("\n2. Testing database access...")
        cursor = conn.cursor()
        cursor.execute(f"USE {database}")
        print(f"✅ Database '{database}' accessible")
        
        # Test basic query
        print("\n3. Testing basic query...")
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        print(f"✅ Query successful: {result}")
        
        # Check if tables exist
        print("\n4. Checking for existing tables...")
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        if tables:
            print(f"✅ Found {len(tables)} existing tables:")
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print("ℹ️  No tables found (database is empty)")
        
        cursor.close()
        conn.close()
        print("\n✅ All tests passed! Database connection is working.")
        return True
        
    except Error as e:
        print(f"\n❌ MySQL Error: {e}")
        
        # Provide specific troubleshooting based on error
        if e.errno == 1045:
            print("\n🔧 TROUBLESHOOTING: Access denied")
            print("   - Check username and password")
            print("   - Verify user exists: SELECT User, Host FROM mysql.user WHERE User='recipedb2';")
            print("   - Check user permissions: SHOW GRANTS FOR 'recipedb2'@'%';")
            print("   - User might need to be created or granted permissions")
            
        elif e.errno == 2003:
            print("\n🔧 TROUBLESHOOTING: Can't connect to server")
            print("   - Check if MySQL server is running")
            print("   - Verify hostname/IP address")
            print("   - Check firewall settings")
            print("   - Ensure MySQL is listening on the correct port")
            
        elif e.errno == 1049:
            print("\n🔧 TROUBLESHOOTING: Unknown database")
            print(f"   - Database '{database}' doesn't exist")
            print("   - Create database: CREATE DATABASE recipechest2;")
            print("   - Grant permissions: GRANT ALL ON recipechest2.* TO 'recipedb2'@'%';")
            
        elif e.errno == 1044:
            print("\n🔧 TROUBLESHOOTING: Access denied to database")
            print("   - User doesn't have permission to access this database")
            print("   - Grant permissions: GRANT ALL ON recipechest2.* TO 'recipedb2'@'%';")
            
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

def test_with_different_hosts():
    """Test connection with different host specifications"""
    print("\n=== Testing Different Host Formats ===")
    
    user = os.environ.get('RECIPE_DB_USER_NAME', 'recipe_user')
    password = os.environ.get('RECIPE_DB_USER_PW', '')
    database = os.environ.get('RECIPE_DB_DATABASE_NAME', 'recipe_editor')
    port = int(os.environ.get('RECIPE_DB_PORT', 3306))
    
    # Try different host formats
    hosts_to_try = [
        os.environ.get('RECIPE_DB_HOSTNAME', 'localhost'),
        'localhost',  # In case it's actually local
        '127.0.0.1'   # Local IP
    ]
    
    for host in hosts_to_try:
        print(f"\nTesting host: {host}")
        try:
            conn = mysql.connector.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database
            )
            print(f"✅ SUCCESS with host: {host}")
            conn.close()
            return True
        except Error as e:
            print(f"❌ Failed with {host}: {e}")
    
    return False

def main():
    print("MySQL Database Connection Troubleshooting")
    print("=" * 50)
    
    # Load environment variables
    if os.path.exists('.env'):
        print("Loading environment variables from .env...")
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.strip().split('=', 1)
                    if key.startswith('export '):
                        key = key[7:]  # Remove 'export '
                    os.environ[key] = value
        print("✅ Environment variables loaded")
    else:
        print("❌ .env file not found")
        return
    
    # Run tests
    network_ok = test_network_connectivity()
    
    if network_ok:
        mysql_ok = test_mysql_connection()
        
        if not mysql_ok:
            print("\n" + "="*50)
            print("ADDITIONAL TROUBLESHOOTING")
            print("="*50)
            test_with_different_hosts()
    else:
        print("\n❌ Cannot proceed with MySQL tests - network connectivity failed")
        print("\n🔧 TROUBLESHOOTING STEPS:")
        print("1. Check if MySQL server is running on your server")
        print("2. Verify the hostname/IP address is correct")
        print("3. Check firewall settings (port 3306 should be open)")
        print("4. Test from your server: telnet mysql.ricki.gafter.com 3306")

if __name__ == "__main__":
    main()
