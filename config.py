"""
Configuration settings for the Recipe Editor application.
"""
import os

# Flask Configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', '5001'))

# Storage Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RECIPES_DIR = os.path.join(DATA_DIR, 'recipes')
TAGS_FILE = os.path.join(DATA_DIR, 'tags.json')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOGS_DIR, 'app.log')

# Email Configuration
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'True') == 'True'
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', SMTP_USERNAME)
SENDER_NAME = os.environ.get('SENDER_NAME', 'Recipe Editor')

# Storage Backend Configuration
STORAGE_BACKEND = os.environ.get('STORAGE_BACKEND', 'json')  # 'json' or 'mysql'

# MySQL Configuration (if using MySQL backend)
# Support both naming conventions
MYSQL_HOST = os.environ.get('MYSQL_HOST') or os.environ.get('RECIPE_DB_HOSTNAME', 'localhost')
MYSQL_PORT = int(os.environ.get('MYSQL_PORT') or os.environ.get('RECIPE_DB_PORT', '3306'))
MYSQL_USER = os.environ.get('MYSQL_USER') or os.environ.get('RECIPE_DB_USER_NAME', 'recipe_user')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or os.environ.get('RECIPE_DB_USER_PW', '')
MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE') or os.environ.get('RECIPE_DB_DATABASE_NAME', 'recipe_editor')

# SQLAlchemy Configuration
SQLALCHEMY_DATABASE_URI = f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = os.environ.get('SQL_ECHO', 'False').lower() == 'true'

# Application Settings
RECIPES_PER_PAGE = 50
MAX_INGREDIENTS = 100
MAX_TAG_LENGTH = 50

