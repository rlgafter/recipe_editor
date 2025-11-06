"""
Test suite for email update functionality.

Tests cover:
- Email change request with password verification
- Email verification process
- Duplicate email handling
- Security notifications
- Token expiration
"""

import pytest
from datetime import datetime, timedelta
from db_models import db, User
from auth import request_email_change, verify_email_change


class TestEmailChangeRequest:
    """Test email change request functionality."""
    
    def test_request_email_change_success(self, app, auth_client):
        """Test successful email change request."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            old_email = user.email
            new_email = 'newemail@example.com'
            
            success, message = request_email_change(user, 'password123', new_email)
            
            assert success is True
            assert 'Verification email sent' in message
            assert user.pending_email == new_email
            assert user.email_change_token is not None
            assert user.email_change_expires is not None
            # Original email should not change yet
            assert user.email == old_email
    
    def test_request_email_change_wrong_password(self, app, auth_client):
        """Test email change with incorrect password."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            
            success, message = request_email_change(user, 'wrongpassword', 'new@example.com')
            
            assert success is False
            assert 'incorrect' in message.lower()
            assert user.pending_email is None
    
    def test_request_email_change_duplicate_email(self, app, auth_client):
        """Test email change with already registered email."""
        with app.app_context():
            # Create another user
            user2 = User(
                username='otheruser',
                email='other@example.com',
                password_hash='hash',
                is_active=True
            )
            db.session.add(user2)
            db.session.commit()
            
            auth_client['login']('testuser', 'password123')
            user = User.query.filter_by(username='testuser').first()
            
            success, message = request_email_change(user, 'password123', 'other@example.com')
            
            assert success is False
            assert 'already registered' in message
    
    def test_request_email_change_same_email(self, app, auth_client):
        """Test email change to same email."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            
            success, message = request_email_change(user, 'password123', user.email)
            
            assert success is False
            assert 'same as' in message.lower()
    
    def test_request_email_change_invalid_email(self, app, auth_client):
        """Test email change with invalid email."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            
            success, message = request_email_change(user, 'password123', 'notanemail')
            
            assert success is False
            assert 'valid email' in message.lower()


class TestEmailChangeVerification:
    """Test email change verification functionality."""
    
    def test_verify_email_change_success(self, app, auth_client):
        """Test successful email verification."""
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            old_email = user.email
            new_email = 'verified@example.com'
            
            # Request email change
            success, message = request_email_change(user, 'password123', new_email)
            assert success is True
            
            token = user.email_change_token
            
            # Verify email change
            success, message = verify_email_change(token)
            
            assert success is True
            assert 'successfully' in message.lower()
            
            # Check email updated
            user = User.query.filter_by(username='testuser').first()
            assert user.email == new_email
            assert user.email_verified is True
            assert user.pending_email is None
            assert user.email_change_token is None
    
    def test_verify_email_change_invalid_token(self, app):
        """Test verification with invalid token."""
        with app.app_context():
            success, message = verify_email_change('invalid-token-12345')
            
            assert success is False
            assert 'invalid' in message.lower()
    
    def test_verify_email_change_expired_token(self, app, auth_client):
        """Test verification with expired token."""
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            
            # Request email change
            success, message = request_email_change(user, 'password123', 'expired@example.com')
            assert success is True
            
            # Manually expire the token
            user.email_change_expires = datetime.utcnow() - timedelta(hours=1)
            db.session.commit()
            
            token = user.email_change_token
            
            # Try to verify
            success, message = verify_email_change(token)
            
            assert success is False
            assert 'expired' in message.lower()
            
            # Check fields cleared
            user = User.query.filter_by(username='testuser').first()
            assert user.pending_email is None
            assert user.email_change_token is None


class TestEmailUpdateRoutes:
    """Test email update HTTP routes."""
    
    def test_change_email_route(self, app, auth_client):
        """Test email change POST route."""
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].post('/auth/profile', data={
            'action': 'change_email',
            'new_email': 'newroute@example.com',
            'current_password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Verification email sent' in response.data
        
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            assert user.pending_email == 'newroute@example.com'
    
    def test_verify_email_change_route(self, app, auth_client):
        """Test email verification route."""
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            
            # Request email change
            success, message = request_email_change(user, 'password123', 'routetest@example.com')
            token = user.email_change_token
        
        # Visit verification link
        response = auth_client['client'].get(f'/verify-email-change/{token}', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'successfully' in response.data
        
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            assert user.email == 'routetest@example.com'
    
    def test_profile_shows_pending_email(self, app, auth_client):
        """Test that profile page shows pending email status."""
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            request_email_change(user, 'password123', 'pending@example.com')
        
        auth_client['login']('testuser', 'password123')
        response = auth_client['client'].get('/auth/profile')
        
        assert response.status_code == 200
        assert b'Change Pending' in response.data
        assert b'pending@example.com' in response.data


# Mark tests as requiring database
pytestmark = pytest.mark.usefixtures("app")

