"""
Comprehensive tests for source validation based on recipe visibility.

Tests that:
- Public recipes REQUIRE source information (errors if missing)
- Private/incomplete recipes have OPTIONAL source information (warnings if missing)
- Warnings don't block saving, errors do
- All edge cases and combinations
"""

import pytest
from unittest.mock import patch, Mock
from db_models import db, User, Recipe
from mysql_storage import MySQLStorage
import bcrypt


@pytest.fixture
def storage(app):
    """Create a MySQLStorage instance for testing."""
    with app.app_context():
        return MySQLStorage()


@pytest.fixture
def mock_url_validation():
    """Mock URL validation to return True for test URLs."""
    with patch('app_mysql.gemini_service.validate_url_accessibility', return_value=True) as mock:
        yield mock


class TestSourceValidationByVisibility:
    """Test source validation rules based on recipe visibility."""
    
    def test_public_recipe_without_source_name_fails(self, app, auth_client, storage):
        """Test that public recipe without source name fails validation."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Try to create public recipe without source name
            response = client.post('/recipe/new', data={
                'name': 'Test Public Recipe',
                'instructions': 'Cook it well',
                'visibility': 'public',
                'ingredient_description_0': 'flour',
                'ingredient_amount_0': '1',
                'ingredient_unit_0': 'cup',
                'ingredient_description_1': 'sugar',
                'ingredient_amount_1': '1',
                'ingredient_unit_1': 'cup',
                'ingredient_description_2': 'eggs',
                'ingredient_amount_2': '2',
                'ingredient_unit_2': '',
                # No source information
            }, follow_redirects=True)
            
            # Should return 400 (validation error) or 200 (if following redirects)
            assert response.status_code in [200, 400]
            # Should show error about source name
            assert b'Source name is required for public recipes' in response.data or \
                   b'source name' in response.data.lower()
            
            # Recipe should not be created
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Test Public Recipe').first()
            assert recipe is None
    
    def test_public_recipe_without_author_or_url_fails(self, app, auth_client, storage):
        """Test that public recipe without author or URL fails validation."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Try to create public recipe with source name but no author/URL
            response = client.post('/recipe/new', data={
                'name': 'Test Public Recipe 2',
                'instructions': 'Cook it well',
                'visibility': 'public',
                'source_name': 'Test Cookbook',
                'ingredient_description_0': 'flour',
                'ingredient_amount_0': '1',
                'ingredient_unit_0': 'cup',
                'ingredient_description_1': 'sugar',
                'ingredient_amount_1': '1',
                'ingredient_unit_1': 'cup',
                'ingredient_description_2': 'eggs',
                'ingredient_amount_2': '2',
                'ingredient_unit_2': '',
                # Has source name but no author or URL
            }, follow_redirects=True)
            
            # Should return 400 (validation error) or 200 (if following redirects)
            assert response.status_code in [200, 400]
            # Should show error about author or URL
            assert b'Must provide either recipe author or source URL' in response.data or \
                   b'author or source URL' in response.data.lower()
            
            # Recipe should not be created
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Test Public Recipe 2').first()
            assert recipe is None
    
    def test_public_recipe_with_source_name_and_author_succeeds(self, app, auth_client, storage):
        """Test that public recipe with source name and author succeeds."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Create public recipe with complete source information
            response = client.post('/recipe/new', data={
                'name': 'Test Public Recipe 3',
                'instructions': 'Cook it well',
                'visibility': 'public',
                'source_name': 'Test Cookbook',
                'source_author': 'Test Author',
                'ingredient_description_0': 'flour',
                'ingredient_amount_0': '1',
                'ingredient_unit_0': 'cup',
                'ingredient_description_1': 'sugar',
                'ingredient_amount_1': '1',
                'ingredient_unit_1': 'cup',
                'ingredient_description_2': 'eggs',
                'ingredient_amount_2': '2',
                'ingredient_unit_2': '',
            }, follow_redirects=True)
            
            assert response.status_code == 200
            # Should succeed
            assert b'created successfully' in response.data.lower() or \
                   b'Test Public Recipe 3' in response.data
            
            # Recipe should be created
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Test Public Recipe 3').first()
            assert recipe is not None
            assert recipe.visibility == 'public'
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()
    
    def test_public_recipe_with_source_name_and_url_succeeds(self, app, auth_client, storage, mock_url_validation):
        """Test that public recipe with source name and URL succeeds."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Create public recipe with source name and URL
            response = client.post('/recipe/new', data={
                'name': 'Test Public Recipe 4',
                'instructions': 'Cook it well',
                'visibility': 'public',
                'source_name': 'Test Website',
                'source_url': 'https://example.com/recipe',
                'ingredient_description_0': 'flour',
                'ingredient_amount_0': '1',
                'ingredient_unit_0': 'cup',
                'ingredient_description_1': 'sugar',
                'ingredient_amount_1': '1',
                'ingredient_unit_1': 'cup',
                'ingredient_description_2': 'eggs',
                'ingredient_amount_2': '2',
                'ingredient_unit_2': '',
            }, follow_redirects=True)
            
            assert response.status_code == 200
            # Should succeed
            assert b'created successfully' in response.data.lower() or \
                   b'Test Public Recipe 4' in response.data
            
            # Recipe should be created
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Test Public Recipe 4').first()
            assert recipe is not None
            assert recipe.visibility == 'public'
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()
    
    def test_private_recipe_without_source_succeeds_with_warning(self, app, auth_client, storage):
        """Test that private recipe without source succeeds but shows warning."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Create private recipe without source information
            response = client.post('/recipe/new', data={
                'name': 'Test Private Recipe',
                'instructions': 'Cook it well',
                'visibility': 'private',
                'ingredient_description_0': 'flour',
                'ingredient_amount_0': '1',
                'ingredient_unit_0': 'cup',
                'ingredient_description_1': 'sugar',
                'ingredient_amount_1': '1',
                'ingredient_unit_1': 'cup',
                'ingredient_description_2': 'eggs',
                'ingredient_amount_2': '2',
                'ingredient_unit_2': '',
                # No source information
            }, follow_redirects=True)
            
            assert response.status_code == 200
            # Should succeed (recipe created)
            assert b'created successfully' in response.data.lower() or \
                   b'Test Private Recipe' in response.data
            
            # Should show warning about source information
            assert b'Source information is recommended' in response.data or \
                   b'recommended' in response.data.lower()
            
            # Recipe should be created
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Test Private Recipe').first()
            assert recipe is not None
            assert recipe.visibility == 'private'
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()
    
    def test_incomplete_recipe_without_source_succeeds_with_warning(self, app, auth_client, storage):
        """Test that incomplete recipe without source succeeds but shows warning."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Create incomplete recipe without source information
            response = client.post('/recipe/new', data={
                'name': 'Test Incomplete Recipe',
                'instructions': 'Cook it well',
                'visibility': 'incomplete',
                'ingredient_description_0': 'flour',
                'ingredient_amount_0': '1',
                'ingredient_unit_0': 'cup',
                'ingredient_description_1': 'sugar',
                'ingredient_amount_1': '1',
                'ingredient_unit_1': 'cup',
                'ingredient_description_2': 'eggs',
                'ingredient_amount_2': '2',
                'ingredient_unit_2': '',
                # No source information
            }, follow_redirects=True)
            
            assert response.status_code == 200
            # Should succeed (recipe created)
            assert b'created successfully' in response.data.lower() or \
                   b'Test Incomplete Recipe' in response.data
            
            # Should show warning about source information
            assert b'Source information is recommended' in response.data or \
                   b'recommended' in response.data.lower()
            
            # Recipe should be created
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Test Incomplete Recipe').first()
            assert recipe is not None
            assert recipe.visibility == 'incomplete'
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()
    
    def test_private_recipe_with_source_succeeds_no_warning(self, app, auth_client, storage):
        """Test that private recipe with source succeeds without warning."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Create private recipe with source information
            response = client.post('/recipe/new', data={
                'name': 'Test Private Recipe With Source',
                'instructions': 'Cook it well',
                'visibility': 'private',
                'source_name': 'Test Cookbook',
                'source_author': 'Test Author',
                'ingredient_description_0': 'flour',
                'ingredient_amount_0': '1',
                'ingredient_unit_0': 'cup',
                'ingredient_description_1': 'sugar',
                'ingredient_amount_1': '1',
                'ingredient_unit_1': 'cup',
                'ingredient_description_2': 'eggs',
                'ingredient_amount_2': '2',
                'ingredient_unit_2': '',
            }, follow_redirects=True)
            
            assert response.status_code == 200
            # Should succeed
            assert b'created successfully' in response.data.lower() or \
                   b'Test Private Recipe With Source' in response.data
            
            # Should NOT show warning (has source info)
            assert b'Source information is recommended' not in response.data
            
            # Recipe should be created
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Test Private Recipe With Source').first()
            assert recipe is not None
            assert recipe.visibility == 'private'
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()
    
    def test_edit_private_to_public_requires_source(self, app, auth_client, storage):
        """Test that changing private recipe to public requires source information."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Create private recipe without source
            response = client.post('/recipe/new', data={
                'name': 'Test Recipe To Make Public',
                'instructions': 'Cook it well',
                'visibility': 'private',
                'ingredient_description_0': 'flour',
                'ingredient_amount_0': '1',
                'ingredient_unit_0': 'cup',
                'ingredient_description_1': 'sugar',
                'ingredient_amount_1': '1',
                'ingredient_unit_1': 'cup',
                'ingredient_description_2': 'eggs',
                'ingredient_amount_2': '2',
                'ingredient_unit_2': '',
            }, follow_redirects=True)
            
            assert response.status_code == 200
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Test Recipe To Make Public').first()
            assert recipe is not None
            
            # Try to change to public without source
            response = client.post(f'/recipe/{recipe.id}/edit', data={
                'name': 'Test Recipe To Make Public',
                'instructions': 'Cook it well',
                'visibility': 'public',
                'ingredient_description_0': 'flour',
                'ingredient_amount_0': '1',
                'ingredient_unit_0': 'cup',
                'ingredient_description_1': 'sugar',
                'ingredient_amount_1': '1',
                'ingredient_unit_1': 'cup',
                'ingredient_description_2': 'eggs',
                'ingredient_amount_2': '2',
                'ingredient_unit_2': '',
                # No source information
            }, follow_redirects=True)
            
            # Should return 400 (validation error) or 200 (if following redirects)
            assert response.status_code in [200, 400]
            # Should show error about source
            assert b'Source name is required for public recipes' in response.data or \
                   b'source name' in response.data.lower()
            
            # Recipe should still be private
            db.session.refresh(recipe)
            assert recipe.visibility == 'private'
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()
    
    def test_edit_private_to_public_with_source_succeeds(self, app, auth_client, storage, mock_url_validation):
        """Test that changing private recipe to public with source succeeds."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Create private recipe without source
            response = client.post('/recipe/new', data={
                'name': 'Test Recipe To Make Public 2',
                'instructions': 'Cook it well',
                'visibility': 'private',
                'ingredient_description_0': 'flour',
                'ingredient_amount_0': '1',
                'ingredient_unit_0': 'cup',
                'ingredient_description_1': 'sugar',
                'ingredient_amount_1': '1',
                'ingredient_unit_1': 'cup',
                'ingredient_description_2': 'eggs',
                'ingredient_amount_2': '2',
                'ingredient_unit_2': '',
            }, follow_redirects=True)
            
            assert response.status_code == 200
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Test Recipe To Make Public 2').first()
            assert recipe is not None
            
            # Change to public with source information
            response = client.post(f'/recipe/{recipe.id}/edit', data={
                'name': 'Test Recipe To Make Public 2',
                'instructions': 'Cook it well',
                'visibility': 'public',
                'source_name': 'Test Cookbook',
                'source_author': 'Test Author',
                'ingredient_description_0': 'flour',
                'ingredient_amount_0': '1',
                'ingredient_unit_0': 'cup',
                'ingredient_description_1': 'sugar',
                'ingredient_amount_1': '1',
                'ingredient_unit_1': 'cup',
                'ingredient_description_2': 'eggs',
                'ingredient_amount_2': '2',
                'ingredient_unit_2': '',
            }, follow_redirects=True)
            
            assert response.status_code == 200
            # Should succeed
            assert b'updated successfully' in response.data.lower() or \
                   b'Test Recipe To Make Public 2' in response.data
            
            # Recipe should be public
            db.session.refresh(recipe)
            assert recipe.visibility == 'public'
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()
    
    def test_public_recipe_with_invalid_url_fails(self, app, auth_client, storage):
        """Test that public recipe with invalid URL format fails."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Try to create public recipe with invalid URL
            response = client.post('/recipe/new', data={
                'name': 'Test Public Recipe Invalid URL',
                'instructions': 'Cook it well',
                'visibility': 'public',
                'source_name': 'Test Website',
                'source_url': 'not-a-valid-url',  # Invalid URL
                'ingredient_description_0': 'flour',
                'ingredient_amount_0': '1',
                'ingredient_unit_0': 'cup',
                'ingredient_description_1': 'sugar',
                'ingredient_amount_1': '1',
                'ingredient_unit_1': 'cup',
                'ingredient_description_2': 'eggs',
                'ingredient_amount_2': '2',
                'ingredient_unit_2': '',
            }, follow_redirects=True)
            
            # Should return 400 (validation error) or 200 (if following redirects)
            assert response.status_code in [200, 400]
            # Should show error about URL format
            assert b'valid URL' in response.data.lower() or \
                   b'http://' in response.data or \
                   b'https://' in response.data
            
            # Recipe should not be created
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Test Public Recipe Invalid URL').first()
            assert recipe is None
    
    def test_private_recipe_with_invalid_url_fails(self, app, auth_client, storage):
        """Test that private recipe with invalid URL format fails (URL validation applies to all)."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Try to create private recipe with invalid URL
            response = client.post('/recipe/new', data={
                'name': 'Test Private Recipe Invalid URL',
                'instructions': 'Cook it well',
                'visibility': 'private',
                'source_name': 'Test Website',
                'source_url': 'not-a-valid-url',  # Invalid URL
                'ingredient_description_0': 'flour',
                'ingredient_amount_0': '1',
                'ingredient_unit_0': 'cup',
                'ingredient_description_1': 'sugar',
                'ingredient_amount_1': '1',
                'ingredient_unit_1': 'cup',
                'ingredient_description_2': 'eggs',
                'ingredient_amount_2': '2',
                'ingredient_unit_2': '',
            }, follow_redirects=True)
            
            # Should return 400 (validation error) or 200 (if following redirects)
            assert response.status_code in [200, 400]
            # Should show error about URL format (URL validation applies to all recipes)
            assert b'valid URL' in response.data.lower() or \
                   b'http://' in response.data or \
                   b'https://' in response.data
            
            # Recipe should not be created
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Test Private Recipe Invalid URL').first()
            assert recipe is None


class TestSourceValidationEdgeCases:
    """Test edge cases for source validation."""
    
    def test_public_recipe_with_only_source_name_fails(self, app, auth_client, storage):
        """Test that public recipe with only source name (no author/URL) fails."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            response = client.post('/recipe/new', data={
                'name': 'Test Public Only Name',
                'instructions': 'Cook it',
                'visibility': 'public',
                'source_name': 'Test Cookbook',
                # No author, no URL
                'ingredient_description_0': 'flour',
                'ingredient_amount_0': '1',
                'ingredient_unit_0': 'cup',
                'ingredient_description_1': 'sugar',
                'ingredient_amount_1': '1',
                'ingredient_unit_1': 'cup',
                'ingredient_description_2': 'eggs',
                'ingredient_amount_2': '2',
                'ingredient_unit_2': '',
            }, follow_redirects=True)
            
            # Should return 400 (validation error) or 200 (if following redirects)
            assert response.status_code in [200, 400]
            assert b'Must provide either recipe author or source URL' in response.data or \
                   b'author or source URL' in response.data.lower()
            
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Test Public Only Name').first()
            assert recipe is None
    
    def test_public_recipe_with_only_author_fails(self, app, auth_client, storage):
        """Test that public recipe with only author (no source name) fails."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            response = client.post('/recipe/new', data={
                'name': 'Test Public Only Author',
                'instructions': 'Cook it',
                'visibility': 'public',
                'source_author': 'Test Author',
                # No source name, no URL
                'ingredient_description_0': 'flour',
                'ingredient_amount_0': '1',
                'ingredient_unit_0': 'cup',
                'ingredient_description_1': 'sugar',
                'ingredient_amount_1': '1',
                'ingredient_unit_1': 'cup',
                'ingredient_description_2': 'eggs',
                'ingredient_amount_2': '2',
                'ingredient_unit_2': '',
            }, follow_redirects=True)
            
            # Should return 400 (validation error) or 200 (if following redirects)
            assert response.status_code in [200, 400]
            assert b'Source name is required for public recipes' in response.data or \
                   b'source name' in response.data.lower()
            
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Test Public Only Author').first()
            assert recipe is None
    
    def test_public_recipe_with_only_url_fails(self, app, auth_client, storage, mock_url_validation):
        """Test that public recipe with only URL (no source name) fails."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            response = client.post('/recipe/new', data={
                'name': 'Test Public Only URL',
                'instructions': 'Cook it',
                'visibility': 'public',
                'source_url': 'https://example.com',
                # No source name, no author
                'ingredient_description_0': 'flour',
                'ingredient_amount_0': '1',
                'ingredient_unit_0': 'cup',
                'ingredient_description_1': 'sugar',
                'ingredient_amount_1': '1',
                'ingredient_unit_1': 'cup',
                'ingredient_description_2': 'eggs',
                'ingredient_amount_2': '2',
                'ingredient_unit_2': '',
            }, follow_redirects=True)
            
            # Should return 400 (validation error) or 200 (if following redirects)
            assert response.status_code in [200, 400]
            assert b'Source name is required for public recipes' in response.data or \
                   b'source name' in response.data.lower()
            
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Test Public Only URL').first()
            assert recipe is None

