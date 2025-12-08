"""
Configuration settings for the Recipe Editor application.
"""
import os
import json

# Flask Configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', '8666'))

# Base Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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

# MySQL Configuration
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

# Recipe Page Layout Configuration
# Defines the order and visibility of sections on the recipe view page
# Each section has:
#   - id: unique identifier for the section
#   - enabled: whether the section should be displayed (True/False)
#   - order: display order (lower numbers appear first)
RECIPE_LAYOUT = {
    'sections': [
        {
            'id': 'header',
            'enabled': True,
            'order': 1
        },
        {
            'id': 'metadata',  # submitter only (tags are separate)
            'enabled': True,
            'order': 2
        },
        {
            'id': 'time_servings',  # prep time, cook time, servings
            'enabled': True,
            'order': 3
        },
        {
            'id': 'source',
            'enabled': True,
            'order': 4
        },
        {
            'id': 'tags',  # tags on their own line
            'enabled': True,
            'order': 5
        },
        {
            'id': 'actions',  # edit, print, email, delete buttons
            'enabled': True,
            'order': 6
        },
        {
            'id': 'ingredients',
            'enabled': True,
            'order': 7
        },
        {
            'id': 'instructions',
            'enabled': True,
            'order': 8
        },
        {
            'id': 'notes',
            'enabled': True,
            'order': 9
        },
        {
            'id': 'recipe_info',  # created/updated dates
            'enabled': True,
            'order': 10
        }
    ]
}

# Allow override via environment variable (JSON string)
# Example: export RECIPE_LAYOUT='{"sections":[{"id":"header","enabled":true,"order":1},...]}'
if os.environ.get('RECIPE_LAYOUT'):
    try:
        RECIPE_LAYOUT = json.loads(os.environ.get('RECIPE_LAYOUT'))
    except json.JSONDecodeError:
        # Use default if invalid JSON
        pass


def get_recipe_layout():
    """
    Get the recipe layout configuration with sections sorted by order.
    Returns a list of enabled sections in order.
    
    Returns:
        list: List of enabled section dictionaries, sorted by order
    """
    layout = RECIPE_LAYOUT.copy()
    # Filter enabled sections and sort by order
    enabled_sections = [
        section for section in layout['sections']
        if section.get('enabled', True)
    ]
    enabled_sections.sort(key=lambda x: x.get('order', 999))
    return enabled_sections


def is_section_enabled(section_id):
    """
    Check if a specific section is enabled in the layout configuration.
    
    Args:
        section_id (str): The ID of the section to check
        
    Returns:
        bool: True if the section is enabled, False otherwise
    """
    for section in RECIPE_LAYOUT['sections']:
        if section['id'] == section_id:
            return section.get('enabled', True)
    return False

