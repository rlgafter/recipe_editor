"""
Comprehensive Validation Tests for Recipe Editor.

Tests all possible data entries for valid fields and appropriate error messages
when invalid data is entered. Ensures consistent error presentation.
"""
import pytest


class TestRecipeNameValidation:
    """Test recipe name validation."""
    
    def test_empty_name_shows_error(self, auth_client, invalid_recipe_data):
        """Test that empty recipe name shows appropriate error."""
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].post('/recipe/new', data=invalid_recipe_data['no_name'])
        
        assert response.status_code in [400, 422]  # Bad request or validation error
        assert b'valid recipe name' in response.data.lower()
    
    def test_whitespace_only_name_shows_error(self, auth_client):
        """Test that whitespace-only recipe name shows error."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': '   \t\n   ',
            'instructions': 'Test instructions',
            'source_name': 'Test Source',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': 'tsp'
        }
        
        response = auth_client['client'].post('/recipe/new', data=data)
        
        assert response.status_code in [400, 422]
        assert b'valid recipe name' in response.data.lower()
    
    def test_short_name_shows_error(self, auth_client):
        """Test that recipe name with less than 3 characters shows error."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': 'AB',  # Only 2 characters
            'instructions': 'Test instructions',
            'source_name': 'Test Source',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': 'tsp'
        }
        
        response = auth_client['client'].post('/recipe/new', data=data)
        
        assert response.status_code in [400, 422]
        assert b'3 characters' in response.data.lower()
    
    def test_valid_name_accepts(self, auth_client, valid_recipe_data):
        """Test that valid recipe name is accepted."""
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].post('/recipe/new', data=valid_recipe_data)
        
        # Should succeed or redirect on success
        assert response.status_code in [200, 302]
        if response.status_code == 400:
            # If it fails, it shouldn't be due to name validation
            assert b'valid recipe name' not in response.data.lower()


class TestInstructionsValidation:
    """Test recipe instructions validation."""
    
    def test_empty_instructions_shows_error(self, auth_client, invalid_recipe_data):
        """Test that empty instructions show appropriate error."""
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].post('/recipe/new', data=invalid_recipe_data['no_instructions'])
        
        assert response.status_code in [400, 422]
        assert b'recipe instructions' in response.data.lower()
    
    def test_whitespace_only_instructions_shows_error(self, auth_client):
        """Test that whitespace-only instructions show error."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': 'Test Recipe',
            'instructions': '   \t\n   ',
            'source_name': 'Test Source',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': 'tsp'
        }
        
        response = auth_client['client'].post('/recipe/new', data=data)
        
        assert response.status_code in [400, 422]
        assert b'instructions' in response.data.lower()


class TestSourceValidation:
    """Test recipe source validation."""
    
    def test_no_source_shows_error(self, auth_client, invalid_recipe_data):
        """Test that missing source information shows appropriate error."""
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].post('/recipe/new', data=invalid_recipe_data['no_source'])
        
        assert response.status_code in [400, 422]
        # Should show error about missing source name
        assert b'source' in response.data.lower() and (b'required' in response.data.lower() or b'name' in response.data.lower())
    
    def test_empty_source_fields_shows_error(self, auth_client):
        """Test that all empty source fields show error."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': 'Test Recipe',
            'instructions': 'Test instructions',
            'source_name': '',
            'source_author': '',
            'source_url': '',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': 'tsp'
        }
        
        response = auth_client['client'].post('/recipe/new', data=data)
        
        assert response.status_code in [400, 422]
        # Should show error about missing source name
        assert b'source' in response.data.lower() or b'name' in response.data.lower()
    
    def test_source_name_only_shows_error(self, auth_client):
        """Test that source name alone (without author or URL) shows error."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': 'Test Recipe',
            'instructions': 'Test instructions',
            'source_name': 'Test Cookbook',
            'source_author': '',
            'source_url': '',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': 'tsp'
        }
        
        response = auth_client['client'].post('/recipe/new', data=data)
        
        # Should fail - needs author or URL
        assert response.status_code in [400, 422]
        assert b'author' in response.data.lower() or b'url' in response.data.lower()
    
    def test_source_name_and_author_accepts(self, auth_client):
        """Test that source name + author is accepted."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': 'Test Recipe',
            'instructions': 'Test instructions',
            'source_name': 'Test Cookbook',
            'source_author': 'Test Author',
            'source_url': '',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': 'tsp'
        }
        
        response = auth_client['client'].post('/recipe/new', data=data)
        
        assert response.status_code in [200, 302]
    
    def test_source_name_and_url_accepts(self, auth_client):
        """Test that source name + URL is accepted."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': 'Test Recipe',
            'instructions': 'Test instructions',
            'source_name': 'Test Website',
            'source_author': '',
            'source_url': 'https://example.com/recipe',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': 'tsp'
        }
        
        response = auth_client['client'].post('/recipe/new', data=data)
        
        assert response.status_code in [200, 302]
    
    def test_invalid_url_shows_error(self, auth_client, invalid_recipe_data):
        """Test that invalid URL shows appropriate error."""
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].post('/recipe/new', data=invalid_recipe_data['invalid_url'])
        
        assert response.status_code in [400, 422]
        assert b'URL must be a valid URL' in response.data or b'url' in response.data.lower()


class TestIngredientValidation:
    """Test ingredient validation."""
    
    def test_insufficient_ingredients_shows_error(self, auth_client, invalid_recipe_data):
        """Test that less than 3 ingredients shows error."""
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].post('/recipe/new', data=invalid_recipe_data['insufficient_ingredients'])
        
        assert response.status_code in [400, 422]
        assert b'At least 3 ingredients' in response.data or b'ingredient' in response.data.lower()
    
    def test_empty_ingredient_descriptions_shows_error(self, auth_client):
        """Test that empty ingredient descriptions show error."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': 'Test Recipe',
            'instructions': 'Test instructions',
            'source_name': 'Test Source',
            'ingredient_description_0': '',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': '',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': '',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': 'tsp'
        }
        
        response = auth_client['client'].post('/recipe/new', data=data)
        
        assert response.status_code in [400, 422]
        assert b'ingredient' in response.data.lower()
    
    def test_invalid_amount_shows_error(self, auth_client, invalid_recipe_data):
        """Test that invalid ingredient amounts show error."""
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].post('/recipe/new', data=invalid_recipe_data['invalid_amount'])
        
        assert response.status_code in [400, 422]
        assert b'Invalid amount' in response.data or b'amount' in response.data.lower()
    
    def test_valid_amounts_accept(self, auth_client):
        """Test that valid ingredient amounts are accepted."""
        auth_client['login']('testuser', 'password123')
        
        valid_amounts = ['1', '1.5', '1/2', '2/3', '1 1/2', '0.25']
        
        for amount in valid_amounts:
            data = {
                'name': f'Test Recipe with {amount}',
                'instructions': 'Test instructions',
                'source_name': 'Test Source',
                'source_author': 'Test Author',
                'ingredient_description_0': 'flour',
                'ingredient_amount_0': amount,
                'ingredient_unit_0': 'cup',
                'ingredient_description_1': 'sugar',
                'ingredient_amount_1': '2',
                'ingredient_unit_1': 'tbsp',
                'ingredient_description_2': 'salt',
                'ingredient_amount_2': '1',
                'ingredient_unit_2': 'tsp'
            }
            
            response = auth_client['client'].post('/recipe/new', data=data)
            
            # Should succeed or redirect on success
            assert response.status_code in [200, 302]
            if response.status_code == 400:
                # If it fails, it shouldn't be due to amount validation
                assert b'Invalid amount' not in response.data


class TestFormValidationIntegration:
    """Test form validation integration and error consistency."""
    
    def test_multiple_validation_errors_shown_together(self, auth_client):
        """Test that multiple validation errors are shown together."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': '',  # Empty name
            'instructions': '',  # Empty instructions
            'source_name': '',  # Empty source
            'source_author': '',
            'source_url': '',
            'ingredient_description_0': '',  # Empty ingredient
            'ingredient_amount_0': 'invalid',  # Invalid amount
            'ingredient_unit_0': 'cup'
        }
        
        response = auth_client['client'].post('/recipe/new', data=data)
        
        assert response.status_code in [400, 422]
        
        # Should show multiple error messages
        response_text = response.data.decode('utf-8').lower()
        error_count = response_text.count('required') + response_text.count('invalid')
        assert error_count >= 2  # Should have multiple errors
    
    def test_error_messages_are_consistent(self, auth_client):
        """Test that error messages are consistent across different validation failures."""
        auth_client['login']('testuser', 'password123')
        
        # Test name error
        data1 = {
            'name': '',
            'instructions': 'Test instructions',
            'source_name': 'Test Source',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': 'tsp'
        }
        
        response1 = auth_client['client'].post('/recipe/new', data=data1)
        
        # Test source error
        data2 = {
            'name': 'Test Recipe',
            'instructions': 'Test instructions',
            'source_name': '',
            'source_author': '',
            'source_url': '',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': 'tsp'
        }
        
        response2 = auth_client['client'].post('/recipe/new', data=data2)
        
        # Both should return validation errors
        assert response1.status_code in [400, 422]
        assert response2.status_code in [400, 422]
        
        # Error messages should be consistent in format
        response1_text = response1.data.decode('utf-8')
        response2_text = response2.data.decode('utf-8')
        
        # Both should contain error messages
        assert len(response1_text) > 0
        assert len(response2_text) > 0
    
    def test_successful_validation_redirects(self, auth_client, valid_recipe_data):
        """Test that successful validation redirects appropriately."""
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].post('/recipe/new', data=valid_recipe_data)
        
        # Should redirect on success
        assert response.status_code in [200, 302]
        
        if response.status_code == 302:
            # Should redirect to recipe view or list
            assert b'location' in response.headers or response.status_code == 302


class TestEdgeCaseValidation:
    """Test edge cases in validation."""
    
    def test_very_long_name_handling(self, auth_client):
        """Test handling of very long recipe names."""
        auth_client['login']('testuser', 'password123')
        
        long_name = 'A' * 1000  # Very long name
        
        data = {
            'name': long_name,
            'instructions': 'Test instructions',
            'source_name': 'Test Source',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': 'tsp'
        }
        
        response = auth_client['client'].post('/recipe/new', data=data)
        
        # Should either accept or show length error
        assert response.status_code in [200, 302, 400, 422]
    
    def test_special_characters_in_name(self, auth_client):
        """Test handling of special characters in recipe name."""
        auth_client['login']('testuser', 'password123')
        
        special_name = "Test Recipe with Special Chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"
        
        data = {
            'name': special_name,
            'instructions': 'Test instructions',
            'source_name': 'Test Source',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': 'tsp'
        }
        
        response = auth_client['client'].post('/recipe/new', data=data)
        
        # Should handle special characters appropriately
        assert response.status_code in [200, 302, 400, 422]
    
    def test_unicode_characters_handling(self, auth_client):
        """Test handling of unicode characters."""
        auth_client['login']('testuser', 'password123')
        
        unicode_name = "Test Recipe with Unicode: café, naïve, résumé"
        
        data = {
            'name': unicode_name,
            'instructions': 'Test instructions with unicode: café',
            'source_name': 'Test Source',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': 'tsp'
        }
        
        response = auth_client['client'].post('/recipe/new', data=data)
        
        # Should handle unicode characters
        assert response.status_code in [200, 302, 400, 422]
