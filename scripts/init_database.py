#!/usr/bin/env python3
"""
Initialize the MySQL database with schema and initial data.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import mysql.connector
from mysql.connector import Error
import db_config


def init_database():
    """Initialize the database with schema."""
    print("=" * 70)
    print("Recipe Editor - Database Initialization")
    print("=" * 70)
    
    # Check configuration
    config = db_config.get_mysql_config()
    print(f"\nMySQL Configuration:")
    print(f"  Host: {config['host']}")
    print(f"  Port: {config['port']}")
    print(f"  User: {config['user']}")
    print(f"  Database: {config['database']}")
    
    # Connect to MySQL (without database first)
    try:
        print("\n[1/4] Connecting to MySQL server...")
        conn = mysql.connector.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password']
        )
        cursor = conn.cursor()
        print("✓ Connected to MySQL server")
        
        # Create database if it doesn't exist
        print(f"\n[2/4] Creating database '{config['database']}'...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config['database']} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✓ Database '{config['database']}' ready")
        
        # Use the database
        cursor.execute(f"USE {config['database']}")
        
        # Read and execute schema file
        print("\n[3/4] Executing schema SQL...")
        schema_path = Path(__file__).parent.parent / 'schema' / 'mysql_schema.sql'
        
        if not schema_path.exists():
            print(f"✗ Schema file not found: {schema_path}")
            return False
        
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        # Split by delimiter and execute
        statements = []
        current_statement = []
        in_delimiter = False
        
        for line in schema_sql.split('\n'):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('--'):
                continue
            
            # Handle DELIMITER changes
            if line.startswith('DELIMITER'):
                in_delimiter = not in_delimiter
                continue
            
            current_statement.append(line)
            
            # Execute when we hit a statement terminator
            if in_delimiter:
                if line.endswith('$$'):
                    statement = ' '.join(current_statement)
                    statements.append(statement)
                    current_statement = []
            else:
                if line.endswith(';'):
                    statement = ' '.join(current_statement)
                    statements.append(statement)
                    current_statement = []
        
        # Execute all statements
        executed = 0
        for statement in statements:
            statement = statement.strip()
            if statement and statement != 'USE recipe_editor;':
                try:
                    cursor.execute(statement)
                    executed += 1
                except Error as e:
                    # Ignore "table already exists" errors
                    if 'already exists' not in str(e).lower():
                        print(f"Warning: {e}")
        
        conn.commit()
        print(f"✓ Executed {executed} SQL statements")
        
        # Verify tables
        print("\n[4/4] Verifying database structure...")
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        print(f"✓ Found {len(tables)} tables:")
        for table in sorted(tables):
            print(f"   - {table}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 70)
        print("✅ Database initialization complete!")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Run migration script to import existing JSON data")
        print("   python scripts/migrate_json_to_mysql.py")
        print("\n2. Create an admin user")
        print("   python scripts/create_user.py")
        print("\n3. Start the application")
        print("   ./server start")
        print()
        
        return True
        
    except Error as e:
        print(f"\n✗ Error: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)

