"""
Tests for public recipe visibility restrictions.

Tests that public recipes are NOT automatically visible to all users.
Users should only see:
- Their own recipes
- Recipes explicitly shared with them by friends
"""

import pytest
from db_models import db, User, Recipe, RecipeShare, Friendship
from mysql_storage import MySQLStorage
import bcrypt


@pytest.fixture
def storage(app):
    """Create a MySQLStorage instance for testing."""
    with app.app_context():
        return MySQLStorage()


class TestPublicRecipeVisibilityRestrictions:
    """Test that public recipes are not automatically visible."""
    
    def test_public_recipe_not_visible_to_other_users(self, app, client, auth_client, storage):
        """Test that a public recipe is NOT visible to other users unless shared."""
        with app.app_context():
            # Create two users
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
            
            # Create a public recipe for user1
            recipe_data = {
                'name': 'Swiss Chard and Chickpea Minestrone',
                'description': 'A delicious soup',
                'instructions': 'Cook everything together',
                'visibility': 'public',
                'ingredients': [{'description': 'swiss chard', 'amount': '1', 'unit': 'bunch'}],
                'tags': []
            }
            public_recipe = storage.save_recipe(recipe_data, user1.id)
            
            # Login as user2
            client.post('/auth/login', data={
                'username': 'otheruser',
                'password': 'pass123'
            }, follow_redirects=True)
            
            # Check recipe list - should NOT see user1's public recipe
            response = client.get('/recipes')
            assert response.status_code == 200
            assert b'Swiss Chard and Chickpea Minestrone' not in response.data
            
            # Try to access recipe directly - should not be accessible
            response = client.get(f'/recipe/{public_recipe.id}')
            assert response.status_code in [302, 404]  # Redirect or not found
            
            # Cleanup
            db.session.delete(public_recipe)
            db.session.delete(user2)
            db.session.commit()
    
    def test_public_recipe_visible_when_shared(self, app, client, auth_client, storage):
        """Test that a public recipe IS visible when explicitly shared."""
        with app.app_context():
            # Create two users
            user1 = db.session.query(User).filter(User.username == 'testuser').first()
            
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
            
            # Create a public recipe for user1
            recipe_data = {
                'name': 'Shared Public Recipe',
                'description': 'A shared recipe',
                'instructions': 'Cook it',
                'visibility': 'public',
                'ingredients': [{'description': 'ingredient', 'amount': '1', 'unit': 'cup'}],
                'tags': []
            }
            public_recipe = storage.save_recipe(recipe_data, user1.id)
            
            # Share recipe with user2
            share = RecipeShare(
                recipe_id=public_recipe.id,
                shared_by_user_id=user1.id,
                shared_with_user_id=user2.id
            )
            db.session.add(share)
            db.session.commit()
            
            # Login as user2
            client.post('/auth/login', data={
                'username': 'frienduser',
                'password': 'pass123'
            }, follow_redirects=True)
            
            # Check recipe list - SHOULD see shared recipe
            response = client.get('/recipes')
            assert response.status_code == 200
            assert b'Shared Public Recipe' in response.data
            
            # Should be able to access recipe directly
            response = client.get(f'/recipe/{public_recipe.id}')
            assert response.status_code == 200
            assert b'Shared Public Recipe' in response.data
            
            # Cleanup
            db.session.delete(share)
            db.session.delete(friendship)
            db.session.delete(public_recipe)
            db.session.delete(user2)
            db.session.commit()
    
    def test_user_can_see_own_public_recipes(self, app, auth_client, storage):
        """Test that users can always see their own public recipes."""
        with app.app_context():
            user = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Create a public recipe
            recipe_data = {
                'name': 'My Public Recipe',
                'description': 'My recipe',
                'instructions': 'Cook it',
                'visibility': 'public',
                'ingredients': [{'description': 'ingredient', 'amount': '1', 'unit': 'cup'}],
                'tags': []
            }
            public_recipe = storage.save_recipe(recipe_data, user.id)
            
            # Login as owner
            auth_client['login']('testuser', 'password123')
            
            # Should see own recipe
            response = auth_client['client'].get('/recipes')
            assert response.status_code == 200
            assert b'My Public Recipe' in response.data
            
            # Should be able to access directly
            response = auth_client['client'].get(f'/recipe/{public_recipe.id}')
            assert response.status_code == 200
            assert b'My Public Recipe' in response.data
            
            # Cleanup
            db.session.delete(public_recipe)
            db.session.commit()
    
    def test_unshared_public_recipe_not_in_search(self, app, client, auth_client, storage):
        """Test that unshared public recipes don't appear in search results."""
        with app.app_context():
            user1 = db.session.query(User).filter(User.username == 'testuser').first()
            
            user2 = User(
                username='searcher',
                email='searcher@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True,
                can_publish_public=True
            )
            db.session.add(user2)
            db.session.commit()
            
            # Create a public recipe for user1
            recipe_data = {
                'name': 'Searchable Recipe',
                'description': 'A recipe to search for',
                'instructions': 'Cook it',
                'visibility': 'public',
                'ingredients': [{'description': 'ingredient', 'amount': '1', 'unit': 'cup'}],
                'tags': []
            }
            public_recipe = storage.save_recipe(recipe_data, user1.id)
            
            # Login as user2
            client.post('/auth/login', data={
                'username': 'searcher',
                'password': 'pass123'
            }, follow_redirects=True)
            
            # Search for the recipe - should NOT find it
            response = client.get('/recipes?search=Searchable')
            assert response.status_code == 200
            assert b'Searchable Recipe' not in response.data
            
            # Cleanup
            db.session.delete(public_recipe)
            db.session.delete(user2)
            db.session.commit()
    
    def test_shared_public_recipe_appears_in_search(self, app, client, auth_client, storage):
        """Test that shared public recipes DO appear in search results."""
        with app.app_context():
            user1 = db.session.query(User).filter(User.username == 'testuser').first()
            
            user2 = User(
                username='searcher2',
                email='searcher2@test.com',
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
            
            # Create a public recipe for user1
            recipe_data = {
                'name': 'Shared Searchable Recipe',
                'description': 'A shared recipe to search for',
                'instructions': 'Cook it',
                'visibility': 'public',
                'ingredients': [{'description': 'ingredient', 'amount': '1', 'unit': 'cup'}],
                'tags': []
            }
            public_recipe = storage.save_recipe(recipe_data, user1.id)
            
            # Share recipe with user2
            share = RecipeShare(
                recipe_id=public_recipe.id,
                shared_by_user_id=user1.id,
                shared_with_user_id=user2.id
            )
            db.session.add(share)
            db.session.commit()
            
            # Login as user2
            client.post('/auth/login', data={
                'username': 'searcher2',
                'password': 'pass123'
            }, follow_redirects=True)
            
            # Search for the recipe - SHOULD find it
            response = client.get('/recipes?search=Shared Searchable')
            assert response.status_code == 200
            assert b'Shared Searchable Recipe' in response.data
            
            # Cleanup
            db.session.delete(share)
            db.session.delete(friendship)
            db.session.delete(public_recipe)
            db.session.delete(user2)
            db.session.commit()
    
    def test_public_recipe_not_visible_after_friendship_removed(self, app, client, auth_client, storage):
        """Test that shared recipe becomes invisible if friendship is removed."""
        with app.app_context():
            user1 = db.session.query(User).filter(User.username == 'testuser').first()
            
            user2 = User(
                username='tempfriend',
                email='temp@test.com',
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
            
            # Create and share public recipe
            recipe_data = {
                'name': 'Temporary Shared Recipe',
                'description': 'A recipe',
                'instructions': 'Cook it',
                'visibility': 'public',
                'ingredients': [{'description': 'ingredient', 'amount': '1', 'unit': 'cup'}],
                'tags': []
            }
            public_recipe = storage.save_recipe(recipe_data, user1.id)
            
            share = RecipeShare(
                recipe_id=public_recipe.id,
                shared_by_user_id=user1.id,
                shared_with_user_id=user2.id
            )
            db.session.add(share)
            db.session.commit()
            
            # Login as user2 - should see recipe
            client.post('/auth/login', data={
                'username': 'tempfriend',
                'password': 'pass123'
            }, follow_redirects=True)
            
            response = client.get('/recipes')
            assert response.status_code == 200
            assert b'Temporary Shared Recipe' in response.data
            
            # Remove friendship (but keep share as per requirements)
            db.session.delete(friendship)
            db.session.commit()
            
            # Recipe should no longer be visible (share exists but friendship doesn't)
            # Note: Our query checks for friendship, so recipe should disappear
            response = client.get('/recipes')
            assert response.status_code == 200
            assert b'Temporary Shared Recipe' not in response.data
            
            # Cleanup
            db.session.delete(share)
            db.session.delete(public_recipe)
            db.session.delete(user2)
            db.session.commit()
    
    def test_multiple_users_cannot_see_each_others_public_recipes(self, app, client, auth_client, storage):
        """Test that multiple users with public recipes can't see each other's recipes."""
        with app.app_context():
            user1 = db.session.query(User).filter(User.username == 'testuser').first()
            
            user2 = User(
                username='user2',
                email='user2@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True,
                can_publish_public=True
            )
            user3 = User(
                username='user3',
                email='user3@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True,
                can_publish_public=True
            )
            db.session.add_all([user2, user3])
            db.session.commit()
            
            # Create public recipes for each user
            recipe1_data = {
                'name': 'User1 Public Recipe',
                'description': 'Recipe 1',
                'instructions': 'Cook',
                'visibility': 'public',
                'ingredients': [{'description': 'ing', 'amount': '1', 'unit': 'cup'}],
                'tags': []
            }
            recipe2_data = {
                'name': 'User2 Public Recipe',
                'description': 'Recipe 2',
                'instructions': 'Cook',
                'visibility': 'public',
                'ingredients': [{'description': 'ing', 'amount': '1', 'unit': 'cup'}],
                'tags': []
            }
            recipe3_data = {
                'name': 'User3 Public Recipe',
                'description': 'Recipe 3',
                'instructions': 'Cook',
                'visibility': 'public',
                'ingredients': [{'description': 'ing', 'amount': '1', 'unit': 'cup'}],
                'tags': []
            }
            
            recipe1 = storage.save_recipe(recipe1_data, user1.id)
            recipe2 = storage.save_recipe(recipe2_data, user2.id)
            recipe3 = storage.save_recipe(recipe3_data, user3.id)
            
            # Login as user2
            client.post('/auth/login', data={
                'username': 'user2',
                'password': 'pass123'
            }, follow_redirects=True)
            
            # Should only see own recipe
            response = client.get('/recipes')
            assert response.status_code == 200
            assert b'User2 Public Recipe' in response.data
            assert b'User1 Public Recipe' not in response.data
            assert b'User3 Public Recipe' not in response.data
            
            # Cleanup
            db.session.delete(recipe1)
            db.session.delete(recipe2)
            db.session.delete(recipe3)
            db.session.delete(user2)
            db.session.delete(user3)
            db.session.commit()

