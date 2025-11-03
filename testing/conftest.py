"""
Pytest configuration and fixtures for Recipe Editor test suite.
Integrates with real Flask applications.
"""
import os
import tempfile
import pytest
import json
import sys
from datetime import datetime
from flask import Flask, request
import bcrypt

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Monkey-patch config before importing app to use SQLite for testing
import config
config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Now import app modules
from app_mysql import app as mysql_app
from db_models import db, User, Recipe, RecipeIngredient, Ingredient
from auth import init_auth


@pytest.fixture(scope='session')
def test_config():
    """Test configuration for real app testing."""
    return {
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',  # Use in-memory SQLite for testing
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    }


@pytest.fixture
def app(test_config):
    """Create Flask app using real MySQL app with test database."""
    # Use the mysql_app with updated config
    app = mysql_app
    app.config.update(test_config)
    
    # Create test database
    with app.app_context():
        db.create_all()
        
        # Create test users
        test_user = User(
            username='testuser',
            email='test@example.com',
            password_hash=bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
            display_name='Test User',
            is_active=True,
            can_publish_public=True
        )
        
        admin_user = User(
            username='admin',
            email='admin@example.com',
            password_hash=bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
            display_name='Admin User',
            is_active=True,
            is_admin=True,
            can_publish_public=True
        )
        
        db.session.add(test_user)
        db.session.add(admin_user)
        db.session.commit()
    
    yield app
    
    # Cleanup
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Create authenticated test client."""
    def login_user(username='testuser', password='password123'):
        return client.post('/auth/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)
    
    def logout_user():
        return client.get('/auth/logout', follow_redirects=True)
    
    return {
        'client': client,
        'login': login_user,
        'logout': logout_user
    }


@pytest.fixture
def test_recipes(app):
    """Create test recipes for testing."""
    recipes = []
    
    with app.app_context():
        # Get the test user
        test_user = db.session.query(User).filter(User.username == 'testuser').first()
        
        if not test_user:
            return []
        
        # Create public recipe
        public_recipe = Recipe(
            user_id=test_user.id,
            name='Public Test Recipe',
            description='A public recipe for testing',
            instructions='1. Mix ingredients\n2. Cook for 30 minutes\n3. Serve hot',
            visibility='public',
            created_at=datetime.utcnow()
        )
        
        # Create private recipe
        private_recipe = Recipe(
            user_id=test_user.id,
            name='Private Test Recipe',
            description='A private recipe for testing',
            instructions='1. Secret ingredients\n2. Special cooking method\n3. Private serving',
            visibility='private',
            created_at=datetime.utcnow()
        )
        
        # Create incomplete recipe
        incomplete_recipe = Recipe(
            user_id=test_user.id,
            name='Incomplete Test Recipe',
            description='An incomplete recipe for testing',
            instructions='1. Start cooking',
            visibility='incomplete',
            created_at=datetime.utcnow()
        )
        
        db.session.add(public_recipe)
        db.session.add(private_recipe)
        db.session.add(incomplete_recipe)
        db.session.flush()  # Get IDs before creating ingredients
        
        # Add ingredients to make recipes valid
        ingredients_data = [
            ('flour', '1', 'cup'),
            ('sugar', '2', 'tbsp'),
            ('salt', '1', 'tsp')
        ]
        
        # Create unique ingredients for each recipe to avoid conflicts
        for i, recipe in enumerate([public_recipe, private_recipe, incomplete_recipe]):
            for j, (desc, amount, unit) in enumerate(ingredients_data):
                ingredient_name = f"{desc}_{i}_{j}"  # Make unique
                ingredient = Ingredient(name=ingredient_name)
                db.session.add(ingredient)
                db.session.flush()
                
                recipe_ingredient = RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=ingredient.id,
                    amount=amount,
                    unit=unit,
                    notes=desc
                )
                db.session.add(recipe_ingredient)
        
        db.session.commit()
        
        # Return recipe data as dictionaries to avoid session issues
        recipes = [
            {
                'id': public_recipe.id,
                'name': public_recipe.name,
                'visibility': public_recipe.visibility,
                'user_id': public_recipe.user_id
            },
            {
                'id': private_recipe.id,
                'name': private_recipe.name,
                'visibility': private_recipe.visibility,
                'user_id': private_recipe.user_id
            },
            {
                'id': incomplete_recipe.id,
                'name': incomplete_recipe.name,
                'visibility': incomplete_recipe.visibility,
                'user_id': incomplete_recipe.user_id
            }
        ]
    
    return recipes


@pytest.fixture
def invalid_recipe_data():
    """Invalid recipe data for validation testing."""
    return {
        'no_name': {
            'name': '',
            'instructions': 'Test instructions',
            'source_name': 'Test Source',
            'source_author': 'Test Author',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': 'tsp'
        },
        'no_instructions': {
            'name': 'Test Recipe',
            'instructions': '',
            'source_name': 'Test Source',
            'source_author': 'Test Author',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': 'tsp'
        },
        'no_source': {
            'name': 'Test Recipe',
            'instructions': 'Test instructions',
            'source_name': '',
            'source_author': '',
            'source_url': '',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': 'tsp'
        },
        'insufficient_ingredients': {
            'name': 'Test Recipe',
            'instructions': 'Test instructions',
            'source_name': 'Test Source',
            'source_author': 'Test Author',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp'
        },
        'invalid_amount': {
            'name': 'Test Recipe',
            'instructions': 'Test instructions',
            'source_name': 'Test Source',
            'source_author': 'Test Author',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': 'invalid_amount',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': 'tsp'
        },
        'invalid_url': {
            'name': 'Test Recipe',
            'instructions': 'Test instructions',
            'source_name': 'Test Source',
            'source_author': 'Test Author',
            'source_url': 'not-a-valid-url',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': 'tsp'
        }
    }


@pytest.fixture
def valid_recipe_data():
    """Valid recipe data for testing."""
    return {
        'name': 'Valid Test Recipe',
        'instructions': '1. Mix all ingredients\n2. Cook for 30 minutes\n3. Serve hot',
        'notes': 'Best served warm',
        'source_name': 'Test Cookbook',
        'source_author': 'Test Author',
        'source_url': 'https://example.com/recipe',
        'ingredient_description_0': 'all-purpose flour',
        'ingredient_amount_0': '2',
        'ingredient_unit_0': 'cups',
        'ingredient_description_1': 'granulated sugar',
        'ingredient_amount_1': '1/2',
        'ingredient_unit_1': 'cup',
        'ingredient_description_2': 'salt',
        'ingredient_amount_2': '1',
        'ingredient_unit_2': 'tsp',
        'ingredient_description_3': 'butter',
        'ingredient_amount_3': '1/4',
        'ingredient_unit_3': 'cup'
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )