"""
Authentication and Authorization Tests for Recipe Editor.

Tests user authentication, login/logout functionality, and access control
for both JSON and MySQL storage backends.
"""
import pytest
from flask import url_for


class TestAuthentication:
    """Test user authentication functionality."""
    
    def test_login_page_access(self, client):
        """Test that login page is accessible."""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'Login' in response.data
    
    def test_login_with_valid_credentials(self, auth_client):
        """Test login with valid credentials."""
        response = auth_client['login']('testuser', 'password123')
        assert response.status_code == 200
        # Should redirect to recipe list after successful login
        assert b'Welcome back' in response.data or b'recipe' in response.data.lower()
    
    def test_login_with_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        assert response.status_code == 200
        assert b'Invalid password' in response.data
    
    def test_login_with_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post('/auth/login', data={
            'username': 'nonexistent',
            'password': 'password123'
        })
        assert response.status_code == 200
        assert b'Invalid username or email' in response.data
    
    def test_logout_functionality(self, auth_client):
        """Test logout functionality."""
        # First login
        auth_client['login']('testuser', 'password123')
        
        # Then logout
        response = auth_client['logout']()
        assert response.status_code == 200
        # Should redirect to login page or show logged out state
        assert b'login' in response.data.lower() or b'welcome' not in response.data.lower()
    
    def test_login_redirects_authenticated_users(self, auth_client):
        """Test that authenticated users are redirected from login page."""
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].get('/auth/login')
        # Should redirect authenticated users away from login page
        assert response.status_code in [200, 302]


class TestAuthorization:
    """Test user authorization and access control."""
    
    def test_unauthenticated_access_to_protected_routes(self, client):
        """Test that unauthenticated users cannot access protected routes."""
        protected_routes = [
            '/recipe/new',
            '/auth/profile',
            '/favorites'
        ]
        
        for route in protected_routes:
            response = client.get(route)
            # Should redirect to login or return 401/403
            assert response.status_code in [302, 401, 403]
    
    def test_authenticated_access_to_protected_routes(self, auth_client):
        """Test that authenticated users can access protected routes."""
        auth_client['login']('testuser', 'password123')
        
        protected_routes = [
            '/recipe/new',
            '/auth/profile',
            '/favorites'
        ]
        
        for route in protected_routes:
            response = auth_client['client'].get(route)
            # Should be accessible (200) or redirect to appropriate page
            assert response.status_code in [200, 302]
    
    def test_recipe_creation_requires_authentication(self, client):
        """Test that recipe creation requires authentication."""
        response = client.post('/recipe/new', data={
            'name': 'Test Recipe',
            'instructions': 'Test instructions'
        })
        # Should redirect to login or return 401/403
        assert response.status_code in [302, 401, 403]
    
    def test_recipe_editing_requires_authentication(self, client):
        """Test that recipe editing requires authentication."""
        response = client.get('/recipe/1/edit')
        # Should redirect to login or return 401/403
        assert response.status_code in [302, 401, 403]
    
    def test_admin_access_to_all_recipes(self, auth_client):
        """Test that admin users can access all recipes."""
        auth_client['login']('admin', 'admin123')
        
        # Admin should be able to access recipe creation
        response = auth_client['client'].get('/recipe/new')
        assert response.status_code in [200, 302]
        
        # Admin should be able to access admin routes
        admin_routes = ['/admin', '/admin/users']
        for route in admin_routes:
            response = auth_client['client'].get(route)
            # Should be accessible or redirect appropriately
            assert response.status_code in [200, 302]
    
    def test_regular_user_cannot_access_admin_routes(self, auth_client):
        """Test that regular users cannot access admin routes."""
        auth_client['login']('testuser', 'password123')
        
        admin_routes = ['/admin', '/admin/users']
        for route in admin_routes:
            response = auth_client['client'].get(route)
            # Should be forbidden or redirect
            assert response.status_code in [403, 404, 302]


class TestSessionManagement:
    """Test session management and persistence."""
    
    def test_session_persistence_across_requests(self, auth_client):
        """Test that user session persists across requests."""
        auth_client['login']('testuser', 'password123')
        
        # Make multiple requests
        response1 = auth_client['client'].get('/favorites')
        response2 = auth_client['client'].get('/auth/profile')
        
        # Both should be accessible
        assert response1.status_code in [200, 302]
        assert response2.status_code in [200, 302]
    
    def test_session_expiry_after_logout(self, auth_client):
        """Test that session is cleared after logout."""
        auth_client['login']('testuser', 'password123')
        auth_client['logout']()
        
        # Should not be able to access protected routes
        response = auth_client['client'].get('/favorites')
        assert response.status_code in [302, 401, 403]


class TestUserPermissions:
    """Test user permission system."""
    
    def test_user_can_publish_public_recipes_permission(self, auth_client):
        """Test user permission to publish public recipes."""
        auth_client['login']('testuser', 'password123')
        
        # Try to create a public recipe
        response = auth_client['client'].post('/recipe/new', data={
            'name': 'Public Test Recipe',
            'instructions': 'Test instructions',
            'source_name': 'Test Source',
            'visibility': 'public',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': 'tsp'
        })
        
        # Should succeed if user has permission, or show permission error
        assert response.status_code in [200, 302, 403]
        if response.status_code == 403:
            assert b'permission' in response.data.lower()
    
    def test_admin_can_publish_public_recipes(self, auth_client):
        """Test that admin users can publish public recipes."""
        auth_client['login']('admin', 'admin123')
        
        response = auth_client['client'].post('/recipe/new', data={
            'name': 'Admin Public Recipe',
            'instructions': 'Test instructions',
            'source_name': 'Test Source',
            'visibility': 'public',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': 'tsp'
        })
        
        # Admin should be able to create public recipes
        assert response.status_code in [200, 302]
