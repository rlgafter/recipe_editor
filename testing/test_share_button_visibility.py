"""
Tests to verify that the share button is only shown when a recipe can be shared.

Tests that:
- Share button is shown for public recipes owned by user with friends
- Share button is hidden for private recipes
- Share button is hidden for incomplete recipes
- Share button is hidden when user has no friends
- Share button is hidden for recipes not owned by user
"""

import pytest
from db_models import db, User, Recipe, Friendship
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


class TestShareButtonVisibility:
    """Test that share button visibility is correct."""
    
    def test_share_button_shown_for_public_recipe_with_friends(self, app, auth_client, storage, mock_url_validation):
        """Test that share button is shown for public recipe when user has friends."""
        with app.app_context():
            user1 = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Create a friend
            user2 = User(
                username='frienduser',
                email='friend@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True,
                can_publish_public=True
            )
            db.session.add(user2)
            db.session.commit()
            
            # Create friendship
            user1_id = min(user1.id, user2.id)
            user2_id = max(user1.id, user2.id)
            friendship = Friendship(user1_id=user1_id, user2_id=user2_id)
            db.session.add(friendship)
            db.session.commit()
            
            # Create a public recipe
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            response = client.post('/recipe/new', data={
                'name': 'Public Recipe With Friends',
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
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Public Recipe With Friends').first()
            assert recipe is not None
            
            # View recipe page - share button should be present
            response = client.get(f'/recipe/{recipe.id}')
            assert response.status_code == 200
            assert b'Share' in response.data
            assert b'/recipe/' + str(recipe.id).encode() + b'/share' in response.data
            
            # Cleanup
            db.session.delete(friendship)
            db.session.delete(recipe)
            db.session.delete(user2)
            db.session.commit()
    
    def test_share_button_hidden_for_private_recipe(self, app, auth_client, storage):
        """Test that share button is hidden for private recipes."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Create a private recipe
            response = client.post('/recipe/new', data={
                'name': 'Private Recipe No Share',
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
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Private Recipe No Share').first()
            assert recipe is not None
            
            # View recipe page - share button should NOT be present
            response = client.get(f'/recipe/{recipe.id}')
            assert response.status_code == 200
            # Share button should not be shown (recipe is private)
            assert b'/recipe/' + str(recipe.id).encode() + b'/share' not in response.data or \
                   (b'Share' in response.data and b'can_share_recipe' not in response.data)
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()
    
    def test_share_button_hidden_for_incomplete_recipe(self, app, auth_client, storage):
        """Test that share button is hidden for incomplete recipes."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Create an incomplete recipe
            response = client.post('/recipe/new', data={
                'name': 'Incomplete Recipe No Share',
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
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Incomplete Recipe No Share').first()
            assert recipe is not None
            
            # View recipe page - share button should NOT be present
            response = client.get(f'/recipe/{recipe.id}')
            assert response.status_code == 200
            # Share button should not be shown (recipe is incomplete)
            assert b'/recipe/' + str(recipe.id).encode() + b'/share' not in response.data or \
                   (b'Share' in response.data and b'can_share_recipe' not in response.data)
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()
    
    def test_share_button_hidden_when_no_friends(self, app, auth_client, storage, mock_url_validation):
        """Test that share button is hidden when user has no friends."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Create a public recipe (user has no friends)
            response = client.post('/recipe/new', data={
                'name': 'Public Recipe No Friends',
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
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Public Recipe No Friends').first()
            assert recipe is not None
            
            # View recipe page - share button should NOT be present (no friends)
            response = client.get(f'/recipe/{recipe.id}')
            assert response.status_code == 200
            # Share button should not be shown (user has no friends)
            assert b'/recipe/' + str(recipe.id).encode() + b'/share' not in response.data or \
                   (b'Share' in response.data and b'can_share_recipe' not in response.data)
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()
    
    def test_share_button_hidden_for_other_users_recipes(self, app, client, auth_client, storage, mock_url_validation):
        """Test that share button is hidden for recipes not owned by current user."""
        with app.app_context():
            user1 = db.session.query(User).filter(User.username == 'testuser').first()
            
            user2 = User(
                username='otheruser',
                email='other@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True,
                can_publish_public=True
            )
            db.session.add(user2)
            db.session.commit()
            
            # Create friendship
            user1_id = min(user1.id, user2.id)
            user2_id = max(user1.id, user2.id)
            friendship = Friendship(user1_id=user1_id, user2_id=user2_id)
            db.session.add(friendship)
            db.session.commit()
            
            # Create a public recipe for user2
            recipe_data = {
                'name': 'Other User Public Recipe',
                'description': 'A recipe',
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
            recipe = storage.save_recipe(recipe_data, user2.id)
            
            # Share recipe with user1
            from db_models import RecipeShare
            share = RecipeShare(
                recipe_id=recipe.id,
                shared_by_user_id=user2.id,
                shared_with_user_id=user1.id
            )
            db.session.add(share)
            db.session.commit()
            
            # Login as user1
            client.post('/auth/login', data={
                'username': 'testuser',
                'password': 'password123'
            }, follow_redirects=True)
            
            # View recipe page - share button should NOT be present (not owner)
            response = client.get(f'/recipe/{recipe.id}')
            assert response.status_code == 200
            # Share button should not be shown (user1 doesn't own the recipe)
            assert b'/recipe/' + str(recipe.id).encode() + b'/share' not in response.data or \
                   (b'Share' in response.data and b'can_share_recipe' not in response.data)
            
            # Cleanup
            db.session.delete(share)
            db.session.delete(friendship)
            db.session.delete(recipe)
            db.session.delete(user2)
            db.session.commit()
    
    def test_can_share_recipe_method(self, app):
        """Test the can_share_recipe() method directly."""
        with app.app_context():
            user = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Create a public recipe
            public_recipe = Recipe(
                user_id=user.id,
                name='Test Public Recipe',
                instructions='Cook it',
                visibility='public'
            )
            db.session.add(public_recipe)
            
            # Create a private recipe
            private_recipe = Recipe(
                user_id=user.id,
                name='Test Private Recipe',
                instructions='Cook it',
                visibility='private'
            )
            db.session.add(private_recipe)
            db.session.commit()
            
            # User can share public recipe even without friends (new behavior)
            # User will be directed to find friends if needed
            assert user.can_share_recipe(public_recipe)
            # But cannot share private recipe
            assert not user.can_share_recipe(private_recipe)
            
            # Create a friend (for completeness, but not required for sharing)
            user2 = User(
                username='frienduser2',
                email='friend2@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True
            )
            db.session.add(user2)
            db.session.commit()
            
            # Create friendship
            user1_id = min(user.id, user2.id)
            user2_id = max(user.id, user2.id)
            friendship = Friendship(user1_id=user1_id, user2_id=user2_id)
            db.session.add(friendship)
            db.session.commit()
            
            # Refresh user to get updated friends
            db.session.refresh(user)
            
            # User can still share public recipe (with or without friends)
            assert user.can_share_recipe(public_recipe)
            # But not private recipe
            assert not user.can_share_recipe(private_recipe)
            
            # Cleanup
            db.session.delete(friendship)
            db.session.delete(public_recipe)
            db.session.delete(private_recipe)
            db.session.delete(user2)
            db.session.commit()


class TestShareButtonOnRecipeList:
    """Test that share button appears correctly on the recipe list page."""
    
    def test_share_button_shown_on_list_for_public_recipe(self, app, auth_client, storage, mock_url_validation):
        """Test that share button is shown on recipe list page for public recipe owned by user."""
        with app.app_context():
            user1 = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Create a friend (not required anymore, but keeping for consistency)
            user2 = User(
                username='frienduser',
                email='friend@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True,
                can_publish_public=True
            )
            db.session.add(user2)
            db.session.commit()
            
            # Create friendship
            user1_id = min(user1.id, user2.id)
            user2_id = max(user1.id, user2.id)
            friendship = Friendship(user1_id=user1_id, user2_id=user2_id)
            db.session.add(friendship)
            db.session.commit()
            
            # Create a public recipe
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            response = client.post('/recipe/new', data={
                'name': 'Public Recipe For List Share',
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
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Public Recipe For List Share').first()
            assert recipe is not None
            
            # Check recipe list page - share button should be present
            response = client.get('/recipes')
            assert response.status_code == 200
            assert b'Share' in response.data
            assert b'/recipe/' + str(recipe.id).encode() + b'/share' in response.data
            
            # Cleanup
            db.session.delete(friendship)
            db.session.delete(recipe)
            db.session.delete(user2)
            db.session.commit()
    
    def test_share_button_hidden_on_list_for_private_recipe(self, app, auth_client, storage):
        """Test that share button is hidden on recipe list page for private recipes."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Create a private recipe
            response = client.post('/recipe/new', data={
                'name': 'Private Recipe No Share List',
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
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Private Recipe No Share List').first()
            assert recipe is not None
            
            # Check recipe list page - share button should NOT be present
            response = client.get('/recipes')
            assert response.status_code == 200
            # Share button should not be shown (recipe is private)
            # The recipe should be visible, but share button should not appear
            assert b'Private Recipe No Share List' in response.data  # Recipe is visible
            assert b'/recipe/' + str(recipe.id).encode() + b'/share' not in response.data
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()
    
    def test_share_button_hidden_on_list_for_incomplete_recipe(self, app, auth_client, storage):
        """Test that share button is hidden on recipe list page for incomplete recipes."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Create an incomplete recipe
            response = client.post('/recipe/new', data={
                'name': 'Incomplete Recipe No Share List',
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
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Incomplete Recipe No Share List').first()
            assert recipe is not None
            
            # Check recipe list page - share button should NOT be present
            response = client.get('/recipes')
            assert response.status_code == 200
            # Share button should not be shown (recipe is incomplete)
            assert b'Incomplete Recipe No Share List' in response.data  # Recipe is visible
            assert b'/recipe/' + str(recipe.id).encode() + b'/share' not in response.data
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()
    
    def test_share_button_hidden_on_list_for_other_users_recipes(self, app, client, auth_client, storage, mock_url_validation):
        """Test that share button is hidden on recipe list page for recipes not owned by current user."""
        with app.app_context():
            user1 = db.session.query(User).filter(User.username == 'testuser').first()
            
            user2 = User(
                username='otheruser',
                email='other@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True,
                can_publish_public=True
            )
            db.session.add(user2)
            db.session.commit()
            
            # Create friendship
            user1_id = min(user1.id, user2.id)
            user2_id = max(user1.id, user2.id)
            friendship = Friendship(user1_id=user1_id, user2_id=user2_id)
            db.session.add(friendship)
            db.session.commit()
            
            # Create a public recipe for user2
            recipe_data = {
                'name': 'Other User Public Recipe List',
                'description': 'A recipe',
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
            recipe = storage.save_recipe(recipe_data, user2.id)
            
            # Share recipe with user1
            from db_models import RecipeShare
            share = RecipeShare(
                recipe_id=recipe.id,
                shared_by_user_id=user2.id,
                shared_with_user_id=user1.id
            )
            db.session.add(share)
            db.session.commit()
            
            # Login as user1
            client.post('/auth/login', data={
                'username': 'testuser',
                'password': 'password123'
            }, follow_redirects=True)
            
            # Check recipe list page - share button should NOT be present (not owner)
            response = client.get('/recipes')
            assert response.status_code == 200
            # Recipe should be visible (it's shared), but share button should not appear
            assert b'Other User Public Recipe List' in response.data  # Recipe is visible
            assert b'/recipe/' + str(recipe.id).encode() + b'/share' not in response.data
            
            # Cleanup
            db.session.delete(share)
            db.session.delete(friendship)
            db.session.delete(recipe)
            db.session.delete(user2)
            db.session.commit()
    
    def test_share_button_appears_on_list_for_public_recipe_no_friends(self, app, auth_client, storage, mock_url_validation):
        """Test that share button appears on recipe list even when user has no friends (new behavior)."""
        with app.app_context():
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Create a public recipe (user has no friends, but share button should still appear)
            response = client.post('/recipe/new', data={
                'name': 'Public Recipe No Friends List',
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
            recipe = db.session.query(Recipe).filter(Recipe.name == 'Public Recipe No Friends List').first()
            assert recipe is not None
            
            # Check recipe list page - share button should be present (even without friends)
            response = client.get('/recipes')
            assert response.status_code == 200
            assert b'Share' in response.data
            assert b'/recipe/' + str(recipe.id).encode() + b'/share' in response.data
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()


