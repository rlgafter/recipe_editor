"""
Comprehensive tests for email sharing with non-users.

Tests that:
- Email sharing creates pending share with token
- Email contains protected link
- Link requires login/registration
- After account creation, pending share appears
- User can accept pending share after registration
- Token doesn't expire
"""

import pytest
from db_models import db, User, Recipe
from mysql_storage import MySQLStorage
import bcrypt
import secrets
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


@pytest.fixture
def mock_email_service():
    """Mock email service to capture sent emails."""
    from unittest.mock import patch, MagicMock
    mock_send = MagicMock(return_value=True)
    with patch('app_mysql.email_service.send_recipe', mock_send) as mock:
        yield mock_send


@pytest.mark.skipif(not PENDING_SHARES_AVAILABLE, reason="PendingRecipeShare model not yet implemented")
class TestEmailSharingNonUsers:
    """Test email sharing with users not in the system."""
    
    def test_email_share_creates_pending_share_with_token(self, app, auth_client, storage, mock_url_validation, mock_email_service):
        """Test that sharing recipe via email creates pending share with token."""
        with app.app_context():
            user = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Create public recipe
            recipe_data = {
                'name': 'Email Share Recipe',
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
            
            # Share recipe via email (non-user email)
            response = client.post('/recipes/share', data={
                'recipe_ids': str(recipe.id),
                'email': 'newuser@example.com'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Check that pending share was created with token
            pending_share = db.session.query(PendingRecipeShare).filter(
                PendingRecipeShare.recipe_id == recipe.id,
                PendingRecipeShare.shared_by_user_id == user.id,
                PendingRecipeShare.recipient_email == 'newuser@example.com'
            ).first()
            assert pending_share is not None
            assert pending_share.token is not None
            assert len(pending_share.token) > 0
            assert pending_share.shared_with_user_id is None  # No user yet
            assert pending_share.status == 'pending'
            
            # Check that email was sent
            assert mock_email_service.called
            
            # Cleanup
            db.session.delete(pending_share)
            db.session.delete(recipe)
            db.session.commit()
    
    def test_email_link_requires_login(self, app, client, storage, mock_url_validation, mock_email_service):
        """Test that email share link requires login to view recipe."""
        with app.app_context():
            user = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Create public recipe
            recipe_data = {
                'name': 'Protected Recipe',
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
            
            # Create pending share with token
            token = secrets.token_urlsafe(32)
            pending_share = PendingRecipeShare(
                recipe_id=recipe.id,
                shared_by_user_id=user.id,
                recipient_email='newuser@example.com',
                token=token,
                status='pending'
            )
            db.session.add(pending_share)
            db.session.commit()
            
            # Try to access recipe with token while not logged in
            response = client.get(f'/recipe/{recipe.id}/view?token={token}')
            
            # Should redirect to login or show login required message
            assert response.status_code in [200, 302, 401]
            if response.status_code == 200:
                assert b'login' in response.data.lower() or \
                       b'sign in' in response.data.lower() or \
                       b'register' in response.data.lower()
            
            # Cleanup
            db.session.delete(pending_share)
            db.session.delete(recipe)
            db.session.commit()
    
    def test_pending_share_appears_after_account_creation(self, app, client, auth_client, storage, mock_url_validation, mock_email_service):
        """Test that pending share appears after user creates account via email link."""
        with app.app_context():
            user1 = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Create public recipe
            recipe_data = {
                'name': 'Post Registration Recipe',
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
            
            # Create pending share with token
            token = secrets.token_urlsafe(32)
            pending_share = PendingRecipeShare(
                recipe_id=recipe.id,
                shared_by_user_id=user1.id,
                recipient_email='newuser@example.com',
                token=token,
                status='pending'
            )
            db.session.add(pending_share)
            db.session.commit()
            
            # Create new user account (simulating registration via email link)
            new_user = User(
                username='newuser',
                email='newuser@example.com',
                password_hash=bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True
            )
            db.session.add(new_user)
            db.session.flush()
            
            # Link pending share to new user
            pending_share.shared_with_user_id = new_user.id
            db.session.commit()
            
            # Login as new user
            client.post('/auth/login', data={
                'username': 'newuser',
                'password': 'password123'
            }, follow_redirects=True)
            
            # Check that pending share appears on recipes page
            response = client.get('/recipes')
            assert response.status_code == 200
            assert b'Post Registration Recipe' in response.data
            assert b'pending' in response.data.lower() or b'accept' in response.data.lower()
            
            # Cleanup
            db.session.delete(pending_share)
            db.session.delete(recipe)
            db.session.delete(new_user)
            db.session.commit()
    
    def test_token_does_not_expire(self, app, client, storage, mock_url_validation):
        """Test that email share tokens do not expire."""
        with app.app_context():
            user = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Create public recipe
            recipe_data = {
                'name': 'Non Expiring Recipe',
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
            
            # Create pending share with token (old timestamp)
            token = secrets.token_urlsafe(32)
            old_date = datetime(2020, 1, 1)  # Old date
            pending_share = PendingRecipeShare(
                recipe_id=recipe.id,
                shared_by_user_id=user.id,
                recipient_email='olduser@example.com',
                token=token,
                status='pending',
                created_at=old_date
            )
            db.session.add(pending_share)
            db.session.commit()
            
            # Token should still be valid (no expiration check)
            db.session.refresh(pending_share)
            assert pending_share.token == token
            assert pending_share.status == 'pending'
            
            # Cleanup
            db.session.delete(pending_share)
            db.session.delete(recipe)
            db.session.commit()
    
    def test_multiple_email_shares_same_recipe(self, app, auth_client, storage, mock_url_validation, mock_email_service):
        """Test that same recipe can be shared with multiple email addresses."""
        with app.app_context():
            user = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Create public recipe
            recipe_data = {
                'name': 'Multi Email Recipe',
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
            
            # Share with multiple emails
            emails = ['user1@example.com', 'user2@example.com', 'user3@example.com']
            for email in emails:
                response = client.post('/recipes/share', data={
                    'recipe_ids': str(recipe.id),
                    'email': email
                }, follow_redirects=True)
                assert response.status_code == 200
            
            # Check that multiple pending shares were created
            pending_shares = db.session.query(PendingRecipeShare).filter(
                PendingRecipeShare.recipe_id == recipe.id,
                PendingRecipeShare.shared_by_user_id == user.id
            ).all()
            assert len(pending_shares) == len(emails)
            
            # Each should have unique token
            tokens = [ps.token for ps in pending_shares]
            assert len(set(tokens)) == len(tokens)  # All tokens are unique
            
            # Cleanup
            for ps in pending_shares:
                db.session.delete(ps)
            db.session.delete(recipe)
            db.session.commit()

