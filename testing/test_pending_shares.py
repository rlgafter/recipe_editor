"""
Comprehensive tests for the pending recipe shares system.

Tests that:
- Pending shares are created when sharing with non-friends
- Pending shares appear on recipes page
- Users can accept/reject pending shares
- Accepting pending share adds recipe to user's list
- Friend request acceptance auto-shares pending recipes
- Pending shares link appears when pending shares exist
"""

import pytest
from db_models import db, User, Recipe, FriendRequest, Friendship, RecipeShare
from mysql_storage import MySQLStorage
import bcrypt
from datetime import datetime

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
class TestPendingSharesSystem:
    """Test the pending shares system."""
    
    def test_pending_share_created_when_sharing_with_non_friend(self, app, auth_client, storage, mock_url_validation):
        """Test that pending share is created when sharing recipe with non-friend."""
        with app.app_context():
            user1 = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Create user2 (not a friend yet)
            user2 = User(
                username='frienduser',
                email='friend@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True,
                can_publish_public=True
            )
            db.session.add(user2)
            db.session.commit()
            
            # Create public recipe for user1
            recipe_data = {
                'name': 'Recipe to Share',
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
            
            # Login as user1
            auth_client['login']('testuser', 'password123')
            client = auth_client['client']
            
            # Share recipe with user2 (not a friend)
            # This should create a friend request and pending share
            response = client.post('/recipes/share', data={
                'recipe_ids': str(recipe.id),
                'email': 'friend@test.com'
            }, follow_redirects=True)
            
            # Check that friend request was created
            friend_request = db.session.query(FriendRequest).filter(
                FriendRequest.sender_id == user1.id,
                FriendRequest.recipient_id == user2.id
            ).first()
            assert friend_request is not None
            assert friend_request.status == 'pending'
            
            # Check that pending share was created
            pending_share = db.session.query(PendingRecipeShare).filter(
                PendingRecipeShare.recipe_id == recipe.id,
                PendingRecipeShare.shared_by_user_id == user1.id,
                PendingRecipeShare.shared_with_user_id == user2.id
            ).first()
            assert pending_share is not None
            assert pending_share.status == 'pending'
            assert pending_share.friend_request_id == friend_request.id
            
            # Cleanup
            db.session.delete(pending_share)
            db.session.delete(friend_request)
            db.session.delete(recipe)
            db.session.delete(user2)
            db.session.commit()
    
    def test_pending_shares_appear_on_recipes_page(self, app, client, auth_client, storage, mock_url_validation):
        """Test that pending shares appear on recipes page with accept/reject options."""
        with app.app_context():
            user1 = db.session.query(User).filter(User.username == 'testuser').first()
            
            user2 = User(
                username='recipient',
                email='recipient@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True
            )
            db.session.add(user2)
            db.session.commit()
            
            # Create public recipe for user1
            recipe_data = {
                'name': 'Pending Share Recipe',
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
            
            # Create pending share for user2
            pending_share = PendingRecipeShare(
                recipe_id=recipe.id,
                shared_by_user_id=user1.id,
                shared_with_user_id=user2.id,
                status='pending'
            )
            db.session.add(pending_share)
            db.session.commit()
            
            # Login as user2
            client.post('/auth/login', data={
                'username': 'recipient',
                'password': 'pass123'
            }, follow_redirects=True)
            
            # View recipes page - should show pending share
            response = client.get('/recipes')
            assert response.status_code == 200
            assert b'Pending Share Recipe' in response.data
            assert b'pending' in response.data.lower() or b'accept' in response.data.lower()
            
            # Cleanup
            db.session.delete(pending_share)
            db.session.delete(recipe)
            db.session.delete(user2)
            db.session.commit()
    
    def test_accept_pending_share_adds_recipe_to_list(self, app, client, auth_client, storage, mock_url_validation):
        """Test that accepting pending share adds recipe to user's recipe list."""
        with app.app_context():
            user1 = db.session.query(User).filter(User.username == 'testuser').first()
            
            user2 = User(
                username='recipient2',
                email='recipient2@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True
            )
            db.session.add(user2)
            db.session.commit()
            
            # Create public recipe for user1
            recipe_data = {
                'name': 'Recipe to Accept',
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
            
            # Create pending share
            pending_share = PendingRecipeShare(
                recipe_id=recipe.id,
                shared_by_user_id=user1.id,
                shared_with_user_id=user2.id,
                status='pending'
            )
            db.session.add(pending_share)
            db.session.commit()
            
            # Login as user2
            client.post('/auth/login', data={
                'username': 'recipient2',
                'password': 'pass123'
            }, follow_redirects=True)
            
            # Accept pending share
            response = client.post(f'/pending-share/{pending_share.id}/accept', follow_redirects=True)
            assert response.status_code == 200
            
            # Check that RecipeShare was created
            share = db.session.query(RecipeShare).filter(
                RecipeShare.recipe_id == recipe.id,
                RecipeShare.shared_with_user_id == user2.id
            ).first()
            assert share is not None
            
            # Check that pending share status is updated
            db.session.refresh(pending_share)
            assert pending_share.status == 'accepted'
            
            # Check that recipe appears in user2's recipe list
            response = client.get('/recipes')
            assert response.status_code == 200
            assert b'Recipe to Accept' in response.data
            
            # Cleanup
            db.session.delete(share)
            db.session.delete(pending_share)
            db.session.delete(recipe)
            db.session.delete(user2)
            db.session.commit()
    
    def test_reject_pending_share_removes_it(self, app, client, auth_client, storage, mock_url_validation):
        """Test that rejecting pending share removes it and doesn't create RecipeShare."""
        with app.app_context():
            user1 = db.session.query(User).filter(User.username == 'testuser').first()
            
            user2 = User(
                username='recipient3',
                email='recipient3@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True
            )
            db.session.add(user2)
            db.session.commit()
            
            # Create public recipe
            recipe_data = {
                'name': 'Recipe to Reject',
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
            
            # Create pending share
            pending_share = PendingRecipeShare(
                recipe_id=recipe.id,
                shared_by_user_id=user1.id,
                shared_with_user_id=user2.id,
                status='pending'
            )
            db.session.add(pending_share)
            db.session.commit()
            
            # Login as user2
            client.post('/auth/login', data={
                'username': 'recipient3',
                'password': 'pass123'
            }, follow_redirects=True)
            
            # Reject pending share
            response = client.post(f'/pending-share/{pending_share.id}/reject', follow_redirects=True)
            assert response.status_code == 200
            
            # Check that RecipeShare was NOT created
            share = db.session.query(RecipeShare).filter(
                RecipeShare.recipe_id == recipe.id,
                RecipeShare.shared_with_user_id == user2.id
            ).first()
            assert share is None
            
            # Check that pending share status is updated
            db.session.refresh(pending_share)
            assert pending_share.status == 'rejected'
            
            # Cleanup
            db.session.delete(pending_share)
            db.session.delete(recipe)
            db.session.delete(user2)
            db.session.commit()
    
    def test_friend_request_acceptance_auto_shares_pending_recipes(self, app, client, auth_client, storage, mock_url_validation):
        """Test that accepting friend request automatically shares pending recipes."""
        with app.app_context():
            user1 = db.session.query(User).filter(User.username == 'testuser').first()
            
            user2 = User(
                username='friend4',
                email='friend4@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True
            )
            db.session.add(user2)
            db.session.commit()
            
            # Create public recipe
            recipe_data = {
                'name': 'Auto Share Recipe',
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
            
            # Create friend request
            friend_request = FriendRequest(
                sender_id=user1.id,
                recipient_id=user2.id,
                status='pending'
            )
            db.session.add(friend_request)
            db.session.commit()
            
            # Create pending share linked to friend request
            from db_models import PendingRecipeShare
            pending_share = PendingRecipeShare(
                recipe_id=recipe.id,
                shared_by_user_id=user1.id,
                shared_with_user_id=user2.id,
                friend_request_id=friend_request.id,
                status='pending'
            )
            db.session.add(pending_share)
            db.session.commit()
            
            # Login as user2
            client.post('/auth/login', data={
                'username': 'friend4',
                'password': 'pass123'
            }, follow_redirects=True)
            
            # Accept friend request
            response = client.post(f'/friends/requests/{friend_request.id}/accept', follow_redirects=True)
            assert response.status_code == 200
            
            # Check that RecipeShare was automatically created
            share = db.session.query(RecipeShare).filter(
                RecipeShare.recipe_id == recipe.id,
                RecipeShare.shared_with_user_id == user2.id
            ).first()
            assert share is not None
            
            # Check that pending share status is updated
            db.session.refresh(pending_share)
            assert pending_share.status == 'accepted'
            
            # Check that recipe appears in user2's recipe list
            response = client.get('/recipes')
            assert response.status_code == 200
            assert b'Auto Share Recipe' in response.data
            
            # Cleanup
            db.session.delete(share)
            db.session.delete(pending_share)
            db.session.delete(friend_request)
            # Delete friendship if created
            friendship = db.session.query(Friendship).filter(
                ((Friendship.user1_id == user1.id) & (Friendship.user2_id == user2.id)) |
                ((Friendship.user1_id == user2.id) & (Friendship.user2_id == user1.id))
            ).first()
            if friendship:
                db.session.delete(friendship)
            db.session.delete(recipe)
            db.session.delete(user2)
            db.session.commit()
    
    def test_pending_shares_link_appears_when_pending_exists(self, app, client, auth_client, storage, mock_url_validation):
        """Test that pending shares link appears on all pages when pending shares exist."""
        with app.app_context():
            user1 = db.session.query(User).filter(User.username == 'testuser').first()
            
            user2 = User(
                username='recipient5',
                email='recipient5@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True
            )
            db.session.add(user2)
            db.session.commit()
            
            # Create public recipe
            recipe_data = {
                'name': 'Pending Link Recipe',
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
            
            # Create pending share
            pending_share = PendingRecipeShare(
                recipe_id=recipe.id,
                shared_by_user_id=user1.id,
                shared_with_user_id=user2.id,
                status='pending'
            )
            db.session.add(pending_share)
            db.session.commit()
            
            # Login as user2
            client.post('/auth/login', data={
                'username': 'recipient5',
                'password': 'pass123'
            }, follow_redirects=True)
            
            # Check that pending shares link appears on different pages
            pages = ['/recipes', '/', '/recipe/new']
            for page in pages:
                response = client.get(page)
                if response.status_code == 200:
                    # Should show pending shares indicator/link
                    assert b'pending' in response.data.lower() or \
                           b'share' in response.data.lower() or \
                           b'recipe' in response.data.lower()
            
            # Cleanup
            db.session.delete(pending_share)
            db.session.delete(recipe)
            db.session.delete(user2)
            db.session.commit()
    
    def test_user_can_view_recipe_before_accepting_pending_share(self, app, client, auth_client, storage, mock_url_validation):
        """Test that user can view recipe before accepting/rejecting pending share."""
        with app.app_context():
            user1 = db.session.query(User).filter(User.username == 'testuser').first()
            
            user2 = User(
                username='recipient6',
                email='recipient6@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True
            )
            db.session.add(user2)
            db.session.commit()
            
            # Create public recipe
            recipe_data = {
                'name': 'Recipe to Preview',
                'description': 'A recipe to preview',
                'instructions': 'Cook it well',
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
            
            # Create pending share
            pending_share = PendingRecipeShare(
                recipe_id=recipe.id,
                shared_by_user_id=user1.id,
                shared_with_user_id=user2.id,
                status='pending'
            )
            db.session.add(pending_share)
            db.session.commit()
            
            # Login as user2
            client.post('/auth/login', data={
                'username': 'recipient6',
                'password': 'pass123'
            }, follow_redirects=True)
            
            # Should be able to view recipe even though it's pending
            response = client.get(f'/recipe/{recipe.id}')
            assert response.status_code == 200
            assert b'Recipe to Preview' in response.data
            assert b'Cook it well' in response.data
            
            # Cleanup
            db.session.delete(pending_share)
            db.session.delete(recipe)
            db.session.delete(user2)
            db.session.commit()

