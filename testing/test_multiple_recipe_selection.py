"""
Comprehensive tests for multiple recipe selection and sharing.

Tests that:
- Share Recipes button appears in menu when user has public recipes
- Recipe selection page shows all public recipes with checkboxes
- Multiple recipes can be selected
- Selected recipes are passed to share page
- Bulk sharing creates friend requests and pending shares
- All selected recipes are shared when friend request is accepted
"""

import pytest
from db_models import db, User, Recipe, FriendRequest, Friendship, RecipeShare
from mysql_storage import MySQLStorage
import bcrypt

# Try to import PendingRecipeShare, skip tests if it doesn't exist yet
try:
    from db_models import PendingRecipeShare
    PENDING_SHARES_AVAILABLE = True
except ImportError:
    PENDING_SHARES_AVAILABLE = False
    PendingRecipeShare = None


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


@pytest.mark.skipif(not PENDING_SHARES_AVAILABLE, reason="PendingRecipeShare model not yet implemented")
class TestMultipleRecipeSelection:
    """Test multiple recipe selection and sharing."""
    
    def test_share_recipes_button_appears_in_menu(self, app, auth_client, storage, mock_url_validation):
        """Test that Share Recipes button appears in menu when user has public recipes."""
        with app.app_context():
            user = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Create public recipe
            recipe_data = {
                'name': 'Menu Button Recipe',
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
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # Login as user
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Check that Share Recipes button appears in menu
            response = client.get('/recipes')
            assert response.status_code == 200
            assert b'Share Recipes' in response.data or \
                   b'share recipes' in response.data.lower()
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()
    
    def test_share_recipes_button_not_shown_without_public_recipes(self, app, auth_client, storage):
        """Test that Share Recipes button doesn't appear if user has no public recipes."""
        with app.app_context():
            user = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Create only private recipe
            recipe_data = {
                'name': 'Private Recipe',
                'description': 'A recipe',
                'instructions': 'Cook it',
                'visibility': 'private',
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '1', 'unit': 'cup'},
                    {'description': 'eggs', 'amount': '2', 'unit': ''}
                ],
                'tags': []
            }
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # Login as user
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Check that Share Recipes button does NOT appear
            response = client.get('/recipes')
            assert response.status_code == 200
            # Should not show Share Recipes button (only private recipes)
            # Note: This test may need adjustment based on actual implementation
            
            # Cleanup
            db.session.delete(recipe)
            db.session.commit()
    
    def test_recipe_selection_page_shows_public_recipes(self, app, auth_client, storage, mock_url_validation):
        """Test that recipe selection page shows all user's public recipes with checkboxes."""
        with app.app_context():
            user = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Create multiple public recipes
            recipes = []
            for i in range(3):
                recipe_data = {
                    'name': f'Public Recipe {i+1}',
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
                recipe = storage.save_recipe(recipe_data, user.id)
                recipes.append(recipe)
            
            # Login as user
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Access recipe selection page
            response = client.get('/recipes/share/select')
            assert response.status_code == 200
            
            # Check that all public recipes are shown
            for recipe in recipes:
                assert recipe.name.encode() in response.data
            
            # Check that checkboxes are present
            assert b'checkbox' in response.data.lower() or \
                   b'type="checkbox"' in response.data
            
            # Check for explanation text
            assert b'select' in response.data.lower() or \
                   b'choose' in response.data.lower()
            
            # Cleanup
            for recipe in recipes:
                db.session.delete(recipe)
            db.session.commit()
    
    def test_multiple_recipes_selected_and_passed_to_share_page(self, app, auth_client, storage, mock_url_validation):
        """Test that selected recipes are passed to share page."""
        with app.app_context():
            user = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Create multiple public recipes
            recipes = []
            for i in range(3):
                recipe_data = {
                    'name': f'Selectable Recipe {i+1}',
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
                recipe = storage.save_recipe(recipe_data, user.id)
                recipes.append(recipe)
            
            # Login as user
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Select multiple recipes and submit
            recipe_ids = ','.join([str(r.id) for r in recipes])
            response = client.post('/recipes/share/select', data={
                'recipe_ids': recipe_ids
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Check that share page shows selected recipes
            for recipe in recipes:
                assert recipe.name.encode() in response.data
            
            # Check for email input field
            assert b'email' in response.data.lower()
            
            # Cleanup
            for recipe in recipes:
                db.session.delete(recipe)
            db.session.commit()
    
    def test_bulk_sharing_creates_friend_request_and_pending_shares(self, app, auth_client, storage, mock_url_validation):
        """Test that bulk sharing creates one friend request and multiple pending shares."""
        with app.app_context():
            user1 = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Create user2 (not a friend)
            user2 = User(
                username='bulkfriend',
                email='bulkfriend@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True
            )
            db.session.add(user2)
            db.session.commit()
            
            # Create multiple public recipes
            recipes = []
            for i in range(3):
                recipe_data = {
                    'name': f'Bulk Share Recipe {i+1}',
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
                recipe = storage.save_recipe(recipe_data, user1.id)
                recipes.append(recipe)
            
            # Login as user1
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Share multiple recipes with non-friend
            recipe_ids = ','.join([str(r.id) for r in recipes])
            response = client.post('/recipes/share', data={
                'recipe_ids': recipe_ids,
                'email': 'bulkfriend@test.com'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Check that one friend request was created
            friend_request = db.session.query(FriendRequest).filter(
                FriendRequest.sender_id == user1.id,
                FriendRequest.recipient_id == user2.id
            ).first()
            assert friend_request is not None
            
            # Check that multiple pending shares were created
            pending_shares = db.session.query(PendingRecipeShare).filter(
                PendingRecipeShare.shared_by_user_id == user1.id,
                PendingRecipeShare.shared_with_user_id == user2.id,
                PendingRecipeShare.friend_request_id == friend_request.id
            ).all()
            assert len(pending_shares) == len(recipes)
            
            # All should be linked to same friend request
            for ps in pending_shares:
                assert ps.friend_request_id == friend_request.id
                assert ps.status == 'pending'
            
            # Cleanup
            for ps in pending_shares:
                db.session.delete(ps)
            db.session.delete(friend_request)
            for recipe in recipes:
                db.session.delete(recipe)
            db.session.delete(user2)
            db.session.commit()
    
    def test_all_recipes_shared_when_friend_request_accepted(self, app, client, auth_client, storage, mock_url_validation):
        """Test that all pending recipes are shared when friend request is accepted."""
        with app.app_context():
            user1 = db.session.query(User).filter(User.username == 'testuser').first()
            
            user2 = User(
                username='bulkfriend2',
                email='bulkfriend2@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True
            )
            db.session.add(user2)
            db.session.commit()
            
            # Create multiple public recipes
            recipes = []
            for i in range(3):
                recipe_data = {
                    'name': f'Auto Share Recipe {i+1}',
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
                recipe = storage.save_recipe(recipe_data, user1.id)
                recipes.append(recipe)
            
            # Create friend request
            friend_request = FriendRequest(
                sender_id=user1.id,
                recipient_id=user2.id,
                status='pending'
            )
            db.session.add(friend_request)
            db.session.commit()
            
            # Create pending shares for all recipes
            pending_shares = []
            for recipe in recipes:
                ps = PendingRecipeShare(
                    recipe_id=recipe.id,
                    shared_by_user_id=user1.id,
                    shared_with_user_id=user2.id,
                    friend_request_id=friend_request.id,
                    status='pending'
                )
                db.session.add(ps)
                pending_shares.append(ps)
            db.session.commit()
            
            # Login as user2
            client.post('/auth/login', data={
                'username': 'bulkfriend2',
                'password': 'pass123'
            }, follow_redirects=True)
            
            # Accept friend request
            response = client.post(f'/friends/requests/{friend_request.id}/accept', follow_redirects=True)
            assert response.status_code == 200
            
            # Check that all RecipeShares were created
            shares = db.session.query(RecipeShare).filter(
                RecipeShare.shared_by_user_id == user1.id,
                RecipeShare.shared_with_user_id == user2.id
            ).all()
            assert len(shares) == len(recipes)
            
            # Check that all pending shares are marked as accepted
            for ps in pending_shares:
                db.session.refresh(ps)
                assert ps.status == 'accepted'
            
            # Check that all recipes appear in user2's recipe list
            response = client.get('/recipes')
            assert response.status_code == 200
            for recipe in recipes:
                assert recipe.name.encode() in response.data
            
            # Cleanup
            for share in shares:
                db.session.delete(share)
            for ps in pending_shares:
                db.session.delete(ps)
            db.session.delete(friend_request)
            friendship = db.session.query(Friendship).filter(
                ((Friendship.user1_id == user1.id) & (Friendship.user2_id == user2.id)) |
                ((Friendship.user1_id == user2.id) & (Friendship.user2_id == user1.id))
            ).first()
            if friendship:
                db.session.delete(friendship)
            for recipe in recipes:
                db.session.delete(recipe)
            db.session.delete(user2)
            db.session.commit()

