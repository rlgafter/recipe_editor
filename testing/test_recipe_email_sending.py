"""
Comprehensive tests for recipe email sending functionality.

Tests that recipe emails are sent correctly with Recipe objects,
properly accessing RecipeSource, Tag, and Ingredient relationships.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestRecipeEmailSending:
    """Test recipe email sending with Recipe objects."""
    
    @pytest.fixture
    def mock_email_service(self):
        """Create a mock email service with configuration."""
        with patch('email_service.config') as mock_config:
            mock_config.SMTP_SERVER = 'smtp.gmail.com'
            mock_config.SMTP_PORT = 587
            mock_config.SMTP_USERNAME = 'test@example.com'
            mock_config.SMTP_PASSWORD = 'test-password'
            mock_config.SMTP_USE_TLS = True
            mock_config.SENDER_EMAIL = 'test@example.com'
            mock_config.SENDER_NAME = 'Test Sender'
            mock_config.BASE_URL = 'http://localhost:5000'
            
            from email_service import EmailService
            service = EmailService()
            yield service
    
    @pytest.fixture
    def mock_recipe(self):
        """Create a mock Recipe object with all relationships."""
        # Mock Recipe object
        recipe = Mock()
        recipe.id = 1
        recipe.name = "Test Recipe"
        recipe.instructions = "Step 1: Mix ingredients\nStep 2: Bake"
        recipe.notes = "Best served warm"
        
        # Mock RecipeSource
        recipe_source = Mock()
        recipe_source.source_name = "Test Cookbook"
        recipe_source.author = "Test Author"
        recipe_source.issue = "Issue 1"
        recipe_source.source_url = "http://example.com/cookbook"
        recipe.source = recipe_source
        
        # Mock ingredients (as list of dicts from JSON)
        recipe.ingredients = [
            {'amount': '2', 'unit': 'cups', 'description': 'flour'},
            {'amount': '1', 'unit': 'cup', 'description': 'sugar'},
            {'amount': '', 'unit': 'pinch', 'description': 'salt'}
        ]
        
        # Mock tags (as Tag objects)
        tag1 = Mock()
        tag1.name = "Dessert"
        tag2 = Mock()
        tag2.name = "Baking"
        recipe.tags = [tag1, tag2]
        
        return recipe
    
    @pytest.fixture
    def mock_recipe_no_source(self):
        """Create a mock Recipe object without source."""
        recipe = Mock()
        recipe.id = 2
        recipe.name = "Simple Recipe"
        recipe.instructions = "Simple instructions"
        recipe.notes = None
        recipe.source = None
        recipe.ingredients = [{'amount': '1', 'unit': 'cup', 'description': 'water'}]
        recipe.tags = []
        return recipe
    
    def test_format_recipe_email_with_source(self, mock_email_service, mock_recipe):
        """Test formatting recipe email with source information."""
        html = mock_email_service.format_recipe_email(mock_recipe, "Enjoy this recipe!")
        
        assert "Test Recipe" in html
        assert "Test Cookbook" in html
        assert "Test Author" in html
        assert "Issue 1" in html
        assert "http://example.com/cookbook" in html
        assert "Enjoy this recipe!" in html
        assert "flour" in html
        assert "sugar" in html
        assert "salt" in html
        assert "Dessert" in html
        assert "Baking" in html
        assert "Step 1: Mix ingredients" in html
        assert "Best served warm" in html
    
    def test_format_recipe_email_without_source(self, mock_email_service, mock_recipe_no_source):
        """Test formatting recipe email without source."""
        html = mock_email_service.format_recipe_email(mock_recipe_no_source)
        
        assert "Simple Recipe" in html
        assert "Simple instructions" in html
        assert "water" in html
        # Should not have source section
        assert "Source:" not in html or "Test Cookbook" not in html
    
    def test_format_recipe_email_handles_none_source(self, mock_email_service, mock_recipe):
        """Test that None source is handled correctly."""
        mock_recipe.source = None
        html = mock_email_service.format_recipe_email(mock_recipe)
        
        assert "Test Recipe" in html
        assert "Source:" not in html or "Test Cookbook" not in html
    
    def test_format_recipe_text_with_source(self, mock_email_service, mock_recipe):
        """Test formatting recipe as text with source."""
        text = mock_email_service._format_recipe_text(mock_recipe, "Test message")
        
        assert "Test Recipe" in text
        assert "Test Cookbook" in text
        assert "Test Author" in text
        assert "Test message" in text
        assert "INGREDIENTS" in text
        assert "flour" in text
        assert "INSTRUCTIONS" in text
        assert "NOTES" in text
        assert "Dessert" in text
        assert "Baking" in text
    
    def test_format_recipe_text_without_source(self, mock_email_service, mock_recipe_no_source):
        """Test formatting recipe as text without source."""
        text = mock_email_service._format_recipe_text(mock_recipe_no_source)
        
        assert "Simple Recipe" in text
        assert "INGREDIENTS" in text
        assert "water" in text
        # Should not have source info
        assert "Source:" not in text
    
    @patch('email_service.smtplib.SMTP')
    def test_send_recipe_with_recipe_object(self, mock_smtp, mock_email_service, mock_recipe):
        """Test sending recipe email with Recipe object."""
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        mock_server.__enter__ = Mock(return_value=mock_server)
        mock_server.__exit__ = Mock(return_value=None)
        
        success, error = mock_email_service.send_recipe(
            recipe=mock_recipe,
            recipient_email='recipient@example.com',
            recipient_name='Recipient Name',
            custom_message='Try this recipe!'
        )
        
        assert success is True
        assert error == ""
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()
        
        # Verify email subject contains recipe name
        sent_message = mock_server.send_message.call_args[0][0]
        assert sent_message['Subject'] == "Recipe: Test Recipe"
        assert 'Recipient Name' in sent_message['To'] or 'recipient@example.com' in sent_message['To']
    
    def test_send_recipe_not_configured(self, mock_recipe):
        """Test sending recipe when email service not configured."""
        with patch('email_service.config') as mock_config:
            mock_config.SMTP_SERVER = None
            mock_config.SMTP_USERNAME = None
            mock_config.SMTP_PASSWORD = None
            mock_config.SENDER_EMAIL = None
            
            from email_service import EmailService
            service = EmailService()
            
            success, error = service.send_recipe(
                recipe=mock_recipe,
                recipient_email='recipient@example.com'
            )
            
            assert success is False
            assert "not configured" in error.lower()
    
    def test_format_recipe_email_handles_recipe_ingredient_objects(self, mock_email_service):
        """Test formatting with RecipeIngredient objects (backward compatibility)."""
        recipe = Mock()
        recipe.name = "Ingredient Object Recipe"
        recipe.instructions = "Instructions"
        recipe.notes = None
        recipe.source = None
        
        # Mock RecipeIngredient objects
        ing1 = Mock()
        ing1.to_dict.return_value = {'amount': '2', 'unit': 'cups', 'description': 'flour'}
        ing2 = Mock()
        ing2.to_dict.return_value = {'amount': '1', 'unit': 'tbsp', 'description': 'sugar'}
        
        # Mock the ingredients property to return objects
        recipe.ingredients = [ing1, ing2]
        recipe.tags = []
        
        # This should work with the ingredients property
        # But format_recipe_email expects the property to return dicts
        # So we need to check if it's a dict first
        html = mock_email_service.format_recipe_email(recipe)
        
        assert "Ingredient Object Recipe" in html
        # The ingredient formatting should handle this
    
    def test_format_recipe_email_empty_tags(self, mock_email_service, mock_recipe):
        """Test formatting recipe with no tags."""
        mock_recipe.tags = []
        html = mock_email_service.format_recipe_email(mock_recipe)
        
        assert "Test Recipe" in html
        # Should not crash with empty tags
    
    def test_format_recipe_email_empty_ingredients(self, mock_email_service, mock_recipe):
        """Test formatting recipe with no ingredients."""
        mock_recipe.ingredients = []
        html = mock_email_service.format_recipe_email(mock_recipe)
        
        assert "Test Recipe" in html
        assert "Ingredients" in html
    
    def test_format_recipe_text_empty_values(self, mock_email_service):
        """Test formatting recipe text with empty/null values."""
        recipe = Mock()
        recipe.name = "Empty Recipe"
        recipe.instructions = ""
        recipe.notes = None
        recipe.source = None
        recipe.ingredients = []
        recipe.tags = []
        
        text = mock_email_service._format_recipe_text(recipe)
        
        assert "Empty Recipe" in text
        assert "INGREDIENTS" in text


class TestRecipeEmailIntegration:
    """Integration tests for recipe email sending in app routes."""
    
    def test_recipe_email_route_passes_recipe_object(self, app, auth_client):
        """Test that recipe_email route passes Recipe object, not dict."""
        from db_models import Recipe, RecipeSource, User, db
        from unittest.mock import patch
        
        # Login first
        auth_client['client'].post('/auth/login', data={
            'username': 'testuser',
            'password': 'password123'
        }, follow_redirects=True)
        
        with app.app_context():
            # Get test user
            user = User.query.filter_by(username='testuser').first()
            assert user is not None
            
            # Create a test recipe
            recipe = Recipe(
                user_id=user.id,
                name="Email Test Recipe",
                instructions="Test instructions",
                visibility='public',
                ingredients_json=[{'amount': '1', 'unit': 'cup', 'description': 'flour'}]
            )
            db.session.add(recipe)
            db.session.flush()
            
            # Add source
            source = RecipeSource(
                recipe_id=recipe.id,
                source_name="Test Source",
                author="Test Author"
            )
            db.session.add(source)
            db.session.commit()
            
            # Mock email service
            with patch('app_mysql.email_service.is_configured', return_value=True), \
                 patch('app_mysql.email_service.send_recipe') as mock_send:
                mock_send.return_value = (True, "")
                
                response = auth_client['client'].post(
                    f'/recipe/{recipe.id}/email',
                    data={
                        'recipient_email': 'test@example.com',
                        'recipient_name': 'Test Recipient',
                        'message': 'Test message'
                    },
                    headers={'X-Requested-With': 'XMLHttpRequest'}
                )
                
                # Verify send_recipe was called
                assert mock_send.called, "send_recipe should have been called"
                
                # Verify it was called with Recipe object (not dict)
                call_args = mock_send.call_args
                recipe_arg = call_args[0][0] if call_args[0] else call_args[1]['recipe']
                
                # Should be Recipe object, not dict
                assert hasattr(recipe_arg, 'name'), "Recipe should be an object with name attribute"
                assert hasattr(recipe_arg, 'source'), "Recipe should have source attribute"
                assert recipe_arg.name == "Email Test Recipe"
                assert isinstance(recipe_arg.source, RecipeSource) or recipe_arg.source is None
                
                # Verify response is successful
                assert response.status_code == 200
                data = response.get_json()
                assert data['success'] is True

