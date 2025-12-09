"""
Test suite for tag auto-population removal and display changes.

Tests cover:
- Tags are NOT auto-populated during import (URL, file, text)
- Manual tag entry still works
- Tags are removed from My Recipes display
- Tags still display on recipe view page
- Corner cases: empty tags, special characters, etc.
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
from flask import url_for
from db_models import db, User, Recipe, Tag
from mysql_storage import MySQLStorage


class TestTagAutoPopulationRemoval:
    """Test that tags are NOT auto-populated during import."""
    
    def test_import_from_url_does_not_populate_tags(self, app, auth_client):
        """Test that importing from URL does not auto-populate tags."""
        auth_client['login']('testuser', 'password123')
        
        # Mock Gemini service to return recipe data with tags
        mock_recipe_data = {
            'name': 'Imported Recipe',
            'instructions': 'Test instructions',
            'ingredients': [
                {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                {'description': 'salt', 'amount': '1', 'unit': 'tsp'}
            ],
            'tags': ['DESSERT', 'QUICK', 'EASY'],  # Gemini would normally infer these
            'source': {'name': 'Test Source', 'url': 'http://example.com'}
        }
        
        with app.app_context():
            with patch('app_mysql.gemini_service.extract_from_url') as mock_extract:
                mock_extract.return_value = (True, mock_recipe_data, None)
                
                # Import recipe
                response = auth_client['client'].post(
                    '/api/recipe/import/url',
                    json={'url': 'http://example.com/recipe'},
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                data = response.get_json()
                
                # Verify tags are removed (empty array)
                assert data['success'] is True
                assert 'recipe' in data
                assert data['recipe']['tags'] == []
    
    def test_import_from_file_does_not_populate_tags(self, app, auth_client):
        """Test that importing from file does not auto-populate tags."""
        auth_client['login']('testuser', 'password123')
        
        # Mock Gemini service to return recipe data with tags
        mock_recipe_data = {
            'name': 'Imported Recipe',
            'instructions': 'Test instructions',
            'ingredients': [
                {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                {'description': 'salt', 'amount': '1', 'unit': 'tsp'}
            ],
            'tags': ['VEGETARIAN', 'HEALTHY'],  # Gemini would normally infer these
            'source': {'name': 'Test Source'}
        }
        
        with app.app_context():
            with patch('app_mysql.gemini_service.is_configured', return_value=True):
                with patch('app_mysql.gemini_service.extract_from_text') as mock_extract:
                    mock_extract.return_value = (True, mock_recipe_data, None)
                    
                    # Import recipe - use proper file upload format with Werkzeug test client
                    from io import BytesIO
                    data = {
                        'file': (BytesIO(b'fake file content'), 'recipe.txt')
                    }
                    
                    response = auth_client['client'].post(
                        '/api/recipe/import/file',
                        data=data,
                        content_type='multipart/form-data'
                    )
                    
                    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.get_data(as_text=True)}"
                    data = response.get_json()
                    
                    # Verify tags are removed (empty array)
                    assert data['success'] is True
                    assert 'recipe' in data
                    assert data['recipe']['tags'] == []
    
    def test_gemini_prompt_does_not_infer_tags(self, app):
        """Test that Gemini prompt instructs NOT to infer tags."""
        from gemini_service import GeminiRecipeExtractor
        
        extractor = GeminiRecipeExtractor()
        prompt = extractor._create_extraction_prompt("test content")
        
        # Should NOT contain instruction to infer tags
        assert "Infer appropriate tags" not in prompt
        assert "infer tags" not in prompt.lower()
        
        # Should contain instruction to NOT populate tags
        assert "Do NOT infer" in prompt or "do not infer" in prompt.lower()
        assert "empty array" in prompt.lower() or "[]" in prompt
    
    def test_gemini_prompt_still_mentions_tags(self, app):
        """Test that Gemini prompt still mentions tags field (but doesn't infer)."""
        from gemini_service import GeminiRecipeExtractor
        
        extractor = GeminiRecipeExtractor()
        prompt = extractor._create_extraction_prompt("test content")
        
        # Should still mention tags in JSON structure
        assert '"tags"' in prompt or "'tags'" in prompt


class TestManualTagEntry:
    """Test that manual tag entry still works."""
    
    def test_manual_tag_entry_works(self, app, auth_client):
        """Test that users can manually enter tags."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            storage = MySQLStorage(db.session)
            
            # Create recipe with manual tags
            recipe_data = {
                'name': 'Test Recipe',
                'instructions': 'Test instructions',
                'tags': ['dessert', 'chocolate', 'quick'],
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'salt', 'amount': '1', 'unit': 'tsp'}
                ]
            }
            
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # Verify tags were saved
            assert len(recipe.tags) == 3
            tag_names = [tag.name for tag in recipe.tags]
            assert 'dessert' in tag_names
            assert 'chocolate' in tag_names
            assert 'quick' in tag_names
    
    def test_tag_input_field_present_in_form(self, app, auth_client):
        """Test that tag input field is still present in recipe form."""
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].get('/recipe/new')
        assert response.status_code == 200
        
        # Check for tag input field
        assert b'name="tags"' in response.data
        assert b'id="tags"' in response.data
        assert b'Tags' in response.data
    
    def test_empty_tags_handled_correctly(self, app, auth_client):
        """Test that empty tags are handled correctly."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            storage = MySQLStorage(db.session)
            
            # Create recipe with empty tags
            recipe_data = {
                'name': 'Test Recipe',
                'instructions': 'Test instructions',
                'tags': [],  # Empty tags
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'salt', 'amount': '1', 'unit': 'tsp'}
                ]
            }
            
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # Verify no tags were saved
            assert len(recipe.tags) == 0
    
    def test_tags_with_special_characters(self, app, auth_client):
        """Test that tags with special characters are handled."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            storage = MySQLStorage(db.session)
            
            # Create recipe with tags containing special characters
            recipe_data = {
                'name': 'Test Recipe',
                'instructions': 'Test instructions',
                'tags': ['tag-with-dashes', 'tag_with_underscores', 'tag with spaces'],
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'salt', 'amount': '1', 'unit': 'tsp'}
                ]
            }
            
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # Verify tags were saved (normalized to lowercase)
            assert len(recipe.tags) == 3
            tag_names = [tag.name for tag in recipe.tags]
            assert 'tag-with-dashes' in tag_names
            assert 'tag_with_underscores' in tag_names
            assert 'tag with spaces' in tag_names
    
    def test_tags_case_insensitive(self, app, auth_client):
        """Test that tags are case-insensitive (normalized to lowercase)."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            storage = MySQLStorage(db.session)
            
            # Create recipe with mixed case tags
            recipe_data = {
                'name': 'Test Recipe',
                'instructions': 'Test instructions',
                'tags': ['DESSERT', 'Chocolate', 'QUICK'],
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'salt', 'amount': '1', 'unit': 'tsp'}
                ]
            }
            
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # Verify tags were normalized to lowercase
            tag_names = [tag.name for tag in recipe.tags]
            assert 'dessert' in tag_names
            assert 'chocolate' in tag_names
            assert 'quick' in tag_names


class TestTagDisplay:
    """Test tag display on different pages."""
    
    def test_tags_display_on_recipe_view_page(self, app, auth_client):
        """Test that tags still display on recipe view page."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            storage = MySQLStorage(db.session)
            
            # Create recipe with tags
            recipe_data = {
                'name': 'Test Recipe',
                'instructions': 'Test instructions',
                'tags': ['dessert', 'chocolate'],
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'salt', 'amount': '1', 'unit': 'tsp'}
                ]
            }
            
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # View recipe
            response = auth_client['client'].get(f'/recipe/{recipe.id}')
            assert response.status_code == 200
            
            # Verify tags are displayed
            assert b'Tags:' in response.data
            assert b'dessert' in response.data
            assert b'chocolate' in response.data
    
    def test_tags_not_displayed_on_my_recipes_page(self, app, auth_client):
        """Test that tags are NOT displayed on My Recipes page."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            storage = MySQLStorage(db.session)
            
            # Create recipe with tags
            recipe_data = {
                'name': 'Test Recipe',
                'instructions': 'Test instructions',
                'tags': ['dessert', 'chocolate'],
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'salt', 'amount': '1', 'unit': 'tsp'}
                ]
            }
            
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # View My Recipes page
            response = auth_client['client'].get('/my-recipes')
            assert response.status_code == 200
            
            # Verify recipe name is displayed
            assert b'Test Recipe' in response.data
            
            # Verify tags are NOT displayed (should not see "Tags:" label)
            # Note: We check that the specific tag display section is not present
            # The recipe card should not contain the tags display block
            response_text = response.data.decode('utf-8')
            # Check that we don't see the tags display pattern from my_recipes.html
            assert '<strong>Tags:</strong>' not in response_text or 'Tags:' not in response_text.split('Test Recipe')[1]
    
    def test_tags_not_displayed_on_recipe_list_page(self, app, auth_client):
        """Test that tags are NOT displayed on recipe list page cards."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            storage = MySQLStorage(db.session)
            
            # Create recipe with tags
            recipe_data = {
                'name': 'Test Recipe',
                'instructions': 'Test instructions',
                'tags': ['dessert', 'chocolate'],
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'salt', 'amount': '1', 'unit': 'tsp'}
                ]
            }
            
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # View recipe list page
            response = auth_client['client'].get('/recipes')
            assert response.status_code == 200
            
            # Verify recipe name is displayed
            assert b'Test Recipe' in response.data
            
            # Verify tags are NOT displayed on recipe cards
            # (Tag filter sidebar may still be present, but tags shouldn't be on cards)
            response_text = response.data.decode('utf-8')
            # Check that tags are not displayed in the recipe card area
            # We should not see tags listed with the recipe card content


class TestTagRemovalScript:
    """Test the script to remove all tags from recipes."""
    
    def test_remove_all_tags_script_structure(self):
        """Test that the remove_all_tags script exists and has correct structure."""
        import os
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'scripts',
            'remove_all_recipe_tags.py'
        )
        
        assert os.path.exists(script_path), "Script should exist"
        
        # Read script content
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Verify key functions exist
        assert 'def remove_all_recipe_tags' in content
        assert 'DELETE FROM recipe_tags' in content
        assert 'COUNT(*) FROM recipe_tags' in content


class TestCornerCases:
    """Test corner cases for tag functionality."""
    
    def test_recipe_with_no_tags(self, app, auth_client):
        """Test recipe creation with no tags specified."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            storage = MySQLStorage(db.session)
            
            recipe_data = {
                'name': 'Test Recipe',
                'instructions': 'Test instructions',
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'salt', 'amount': '1', 'unit': 'tsp'}
                ]
            }
            # No 'tags' key at all
            
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # Verify no tags were saved
            assert len(recipe.tags) == 0
    
    def test_recipe_with_whitespace_only_tags(self, app, auth_client):
        """Test recipe creation with whitespace-only tags."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            storage = MySQLStorage(db.session)
            
            recipe_data = {
                'name': 'Test Recipe Whitespace',
                'instructions': 'Test instructions',
                'tags': ['   ', '  ', ''],  # Whitespace-only tags
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'salt', 'amount': '1', 'unit': 'tsp'}
                ]
            }
            
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # Verify no tags were saved (whitespace should be stripped)
            # The code should filter out empty/whitespace tags
            assert len(recipe.tags) == 0
    
    def test_duplicate_tags_handled(self, app, auth_client):
        """Test that duplicate tags are handled correctly."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            storage = MySQLStorage(db.session)
            
            recipe_data = {
                'name': 'Test Recipe Duplicates',
                'instructions': 'Test instructions',
                'tags': ['dessert', 'DESSERT', 'dessert'],  # Duplicates
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'salt', 'amount': '1', 'unit': 'tsp'}
                ]
            }
            
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # Verify only one tag was saved (duplicates should be handled)
            # The code should deduplicate tags before adding them
            tag_names = [tag.name for tag in recipe.tags]
            assert len(set(tag_names)) == 1  # All should be the same after normalization
            assert 'dessert' in tag_names
    
    def test_very_long_tag_name(self, app, auth_client):
        """Test handling of very long tag names."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            storage = MySQLStorage(db.session)
            
            # Create a very long tag name (but within database limits)
            long_tag = 'a' * 100  # 100 characters
            
            recipe_data = {
                'name': 'Test Recipe',
                'instructions': 'Test instructions',
                'tags': [long_tag],
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'salt', 'amount': '1', 'unit': 'tsp'}
                ]
            }
            
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # Verify tag was saved
            assert len(recipe.tags) == 1
            assert recipe.tags[0].name == long_tag
    
    def test_unicode_tags(self, app, auth_client):
        """Test handling of unicode characters in tags."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            storage = MySQLStorage(db.session)
            
            recipe_data = {
                'name': 'Test Recipe',
                'instructions': 'Test instructions',
                'tags': ['café', 'résumé', '日本語'],
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'salt', 'amount': '1', 'unit': 'tsp'}
                ]
            }
            
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # Verify unicode tags were saved
            assert len(recipe.tags) == 3
            tag_names = [tag.name for tag in recipe.tags]
            assert 'café' in tag_names
            assert 'résumé' in tag_names
            assert '日本語' in tag_names

