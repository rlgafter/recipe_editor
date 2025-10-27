"""
Database configuration and connection management for MySQL.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# Load .env file if it exists
try:
    with open('.env', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and 'export ' in line:
                # Handle export VAR=value format
                key_value = line.replace('export ', '').strip()
                if '=' in key_value:
                    key, value = key_value.split('=', 1)
                    # Remove quotes from value
                    value = value.strip('\'"')
                    os.environ[key.strip()] = value
except FileNotFoundError:
    pass

# MySQL Configuration from environment variables
MYSQL_HOST = os.environ.get('RECIPE_DB_HOSTNAME', os.environ.get('MYSQL_HOST', 'localhost'))
MYSQL_PORT = int(os.environ.get('RECIPE_DB_PORT', os.environ.get('MYSQL_PORT', 3306)))
MYSQL_USER = os.environ.get('RECIPE_DB_USER_NAME', os.environ.get('MYSQL_USER', 'recipe_user'))
MYSQL_PASSWORD = os.environ.get('RECIPE_DB_USER_PW', os.environ.get('MYSQL_PASSWORD', ''))
MYSQL_DATABASE = os.environ.get('RECIPE_DB_DATABASE_NAME', os.environ.get('MYSQL_DATABASE', 'recipe_editor'))

# SQLAlchemy Database URI
SQLALCHEMY_DATABASE_URI = f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"

# SQLAlchemy Configuration
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = os.environ.get('SQL_ECHO', 'False').lower() == 'true'  # Log SQL queries in debug mode
SQLALCHEMY_POOL_SIZE = 10
SQLALCHEMY_POOL_RECYCLE = 3600  # Recycle connections after 1 hour
SQLALCHEMY_POOL_TIMEOUT = 30

# Connection pool settings
SQLALCHEMY_ENGINE_OPTIONS = {
    'poolclass': QueuePool,
    'pool_size': SQLALCHEMY_POOL_SIZE,
    'pool_recycle': SQLALCHEMY_POOL_RECYCLE,
    'pool_timeout': SQLALCHEMY_POOL_TIMEOUT,
    'pool_pre_ping': True,  # Verify connections before using
    'connect_args': {
        'charset': 'utf8mb4',
        'use_unicode': True,
    }
}


def get_database_uri():
    """Get the database URI for SQLAlchemy."""
    return SQLALCHEMY_DATABASE_URI


def test_connection():
    """Test database connection."""
    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URI, **SQLALCHEMY_ENGINE_OPTIONS)
        with engine.connect() as conn:
            result = conn.execute(db.text("SELECT 1"))
            return True, "Database connection successful"
    except Exception as e:
        return False, f"Database connection failed: {str(e)}"


def get_mysql_config():
    """Get MySQL configuration dictionary."""
    return {
        'host': MYSQL_HOST,
        'port': MYSQL_PORT,
        'user': MYSQL_USER,
        'password': MYSQL_PASSWORD,
        'database': MYSQL_DATABASE,
        'charset': 'utf8mb4',
        'use_unicode': True,
        'autocommit': False
    }

