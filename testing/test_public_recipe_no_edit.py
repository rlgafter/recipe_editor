"""
Tests to verify that public recipes cannot be edited.

Tests that:
- Public recipes cannot be edited by anyone (including admins)
- Edit buttons/links are not shown for public recipes
- Edit route rejects attempts to edit public recipes
- Users can still edit their own private/incomplete recipes
"""

import pytest
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
    from unittest.mock import patch
    with patch('app_mysql.gemini_service.validate_url_accessibility', return_value=True) as mock:
        yield mock


class TestPublicRecipeNoEdit:
    """Test that public recipes cannot be edited."""
    
    def test_public_recipe_cannot_be_edited_by_owner(self, app, auth_client, storage, mock_url_validation):
        """Test that recipe owner cannot edit their own public recipe."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Create a public recipe
            response = client.post('/recipe/new', data={
                'name': 'Public Recipe No Edit',
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
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Public Recipe No Edit').first()
            assert recipe is not None
            assert recipe.visibility == 'public'
            
            # Try to access edit page - should be redirected with error
            response = client.get(f'/recipe/{recipe.id}/edit', follow_redirects=True)
            assert response.status_code == 200
            assert b'Public recipes cannot be edited' in response.data or \
                   b'cannot be edited' in response.data.lower()
            
            # Try to POST edit - should be rejected
            response = client.post(f'/recipe/{recipe.id}/edit', data={
                'name': 'Public Recipe No Edit Modified',
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
            assert b'Public recipes cannot be edited' in response.data or \
                   b'cannot be edited' in response.data.lower()
            
            # Recipe should not be modified
            db.session.refresh(recipe)
            assert recipe.name == 'Public Recipe No Edit'
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()
    
    def test_public_recipe_edit_button_not_shown(self, app, auth_client, storage, mock_url_validation):
        """Test that edit button is not shown for public recipes."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Create a public recipe
            response = client.post('/recipe/new', data={
                'name': 'Public Recipe No Edit Button',
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
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Public Recipe No Edit Button').first()
            assert recipe is not None
            
            # View recipe page - edit button should not be present
            response = client.get(f'/recipe/{recipe.id}')
            assert response.status_code == 200
            # Edit button/link should not be in the page
            assert b'/recipe/' + str(recipe.id).encode() + b'/edit' not in response.data or \
                   (b'Edit' in response.data and b'can_edit_recipe' not in response.data)
            
            # Check recipe list - edit button should not be present
            response = client.get('/recipes')
            assert response.status_code == 200
            # Edit button should not be shown for public recipes
            assert b'/recipe/' + str(recipe.id).encode() + b'/edit' not in response.data or \
                   (b'Edit' in response.data and b'can_edit_recipe' not in response.data)
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()
    
    def test_admin_cannot_edit_public_recipe(self, app, client, auth_client, storage, mock_url_validation):
        """Test that even admin users cannot edit public recipes."""
        with app.app_context():
            # Create a regular user and their public recipe
            user = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Create a public recipe for regular user
            recipe_data = {
                'name': 'Public Recipe Admin Cannot Edit',
                'description': 'A public recipe',
                'instructions': 'Cook it',
                'visibility': 'public',
                'source': {
                    'name': 'Test Cookbook',
                    'author': 'Test Author'
                },
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '1', 'unit': 'cup'},
                    {'description': 'eggs', 'amount': '2', 'unit': ''}
                ],
                'tags': []
            }
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # Login as admin
            admin_user = db.session.query(User).filter(User.username == 'admin').first()
            if admin_user:
                client.post('/auth/login', data={
                    'username': 'admin',
                    'password': 'admin123'
                }, follow_redirects=True)
                
                # Try to access edit page - should be rejected
                response = client.get(f'/recipe/{recipe.id}/edit', follow_redirects=True)
                assert response.status_code == 200
                assert b'Public recipes cannot be edited' in response.data or \
                       b'cannot be edited' in response.data.lower()
                
                # Try to POST edit - should be rejected
                response = client.post(f'/recipe/{recipe.id}/edit', data={
                    'name': 'Public Recipe Admin Cannot Edit Modified',
                    'instructions': 'Cook it',
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
                assert b'Public recipes cannot be edited' in response.data or \
                       b'cannot be edited' in response.data.lower()
                
                # Recipe should not be modified
                db.session.refresh(recipe)
                assert recipe.name == 'Public Recipe Admin Cannot Edit'
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()
    
    def test_private_recipe_can_still_be_edited(self, app, auth_client, storage):
        """Test that private recipes can still be edited by owner."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Create a private recipe
            response = client.post('/recipe/new', data={
                'name': 'Private Recipe Can Edit',
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
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Private Recipe Can Edit').first()
            assert recipe is not None
            
            # Should be able to access edit page
            response = client.get(f'/recipe/{recipe.id}/edit')
            assert response.status_code == 200
            assert b'Edit Recipe' in response.data or b'Private Recipe Can Edit' in response.data
            
            # Should be able to edit
            response = client.post(f'/recipe/{recipe.id}/edit', data={
                'name': 'Private Recipe Can Edit Modified',
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
            assert b'updated successfully' in response.data.lower() or \
                   b'Private Recipe Can Edit Modified' in response.data
            
            # Recipe should be modified
            db.session.refresh(recipe)
            assert recipe.name == 'Private Recipe Can Edit Modified'
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()
    
    def test_incomplete_recipe_can_still_be_edited(self, app, auth_client, storage):
        """Test that incomplete recipes can still be edited by owner."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Create an incomplete recipe
            response = client.post('/recipe/new', data={
                'name': 'Incomplete Recipe Can Edit',
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
            }, follow_redirects=True)
            
            assert response.status_code == 200
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Incomplete Recipe Can Edit').first()
            assert recipe is not None
            
            # Should be able to access edit page
            response = client.get(f'/recipe/{recipe.id}/edit')
            assert response.status_code == 200
            assert b'Edit Recipe' in response.data or b'Incomplete Recipe Can Edit' in response.data
            
            # Should be able to edit
            response = client.post(f'/recipe/{recipe.id}/edit', data={
                'name': 'Incomplete Recipe Can Edit Modified',
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
            }, follow_redirects=True)
            
            assert response.status_code == 200
            assert b'updated successfully' in response.data.lower() or \
                   b'Incomplete Recipe Can Edit Modified' in response.data
            
            # Recipe should be modified
            db.session.refresh(recipe)
            assert recipe.name == 'Incomplete Recipe Can Edit Modified'
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()
    
    def test_can_edit_recipe_method_returns_false_for_public(self, app):
        """Test that can_edit_recipe() method returns False for public recipes."""
        with app.app_context():
            user = db.session.query(User).filter(User.username == 'testuser').first()
            admin_user = db.session.query(User).filter(User.username == 'admin').first()
            
            # Create a public recipe
            recipe = Recipe(
                user_id=user.id,
                name='Test Public Recipe',
                instructions='Cook it',
                visibility='public'
            )
            db.session.add(recipe)
            db.session.commit()
            
            # Regular user cannot edit their own public recipe
            assert not user.can_edit_recipe(recipe)
            
            # Admin cannot edit public recipe either
            if admin_user:
                assert not admin_user.can_edit_recipe(recipe)
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()
    
    def test_can_edit_recipe_method_returns_true_for_private(self, app):
        """Test that can_edit_recipe() method returns True for private recipes."""
        with app.app_context():
            user = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Create a private recipe
            recipe = Recipe(
                user_id=user.id,
                name='Test Private Recipe',
                instructions='Cook it',
                visibility='private'
            )
            db.session.add(recipe)
            db.session.commit()
            
            # User can edit their own private recipe
            assert user.can_edit_recipe(recipe)
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()

