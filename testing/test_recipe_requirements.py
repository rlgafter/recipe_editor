"""
Recipe Requirements Tests for Recipe Editor.

Tests that all recipe entries contain:
- A name
- A source (name, author, or URL)
- At least 3 ingredients with instructions
"""
import pytest


class TestRecipeMinimumRequirements:
    """Test that recipes meet minimum requirements."""
    
    def test_recipe_must_have_name(self, auth_client):
        """Test that recipe must have a name."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': '',  # No name
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
        assert b'Recipe name is required' in response.data
    
    def test_recipe_must_have_source(self, auth_client):
        """Test that recipe must have source information."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': 'Test Recipe',
            'instructions': 'Test instructions',
            'source_name': '',  # No source name
            'source_author': '',  # No source author
            'source_url': '',  # No source URL
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
        assert b'source' in response.data.lower()
    
    def test_recipe_must_have_at_least_three_ingredients(self, auth_client):
        """Test that recipe must have at least 3 ingredients."""
        auth_client['login']('testuser', 'password123')
        
        # Test with only 2 ingredients
        data = {
            'name': 'Test Recipe',
            'instructions': 'Test instructions',
            'source_name': 'Test Source',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp'
            # Missing third ingredient
        }
        
        response = auth_client['client'].post('/recipe/new', data=data)
        
        assert response.status_code in [400, 422]
        assert b'ingredient' in response.data.lower()
    
    def test_recipe_must_have_instructions(self, auth_client):
        """Test that recipe must have instructions."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': 'Test Recipe',
            'instructions': '',  # No instructions
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


class TestSourceRequirements:
    """Test source information requirements."""
    
    def test_source_name_satisfies_requirement(self, auth_client):
        """Test that source name satisfies source requirement."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': 'Test Recipe',
            'instructions': 'Test instructions',
            'source_name': 'Test Cookbook',  # Has source name
            'source_author': '',  # No author
            'source_url': '',  # No URL
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
        
        # Should succeed
        assert response.status_code in [200, 302]
    
    def test_source_author_satisfies_requirement(self, auth_client):
        """Test that source author satisfies source requirement."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': 'Test Recipe',
            'instructions': 'Test instructions',
            'source_name': '',  # No name
            'source_author': 'Test Author',  # Has author
            'source_url': '',  # No URL
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
        
        # Should succeed
        assert response.status_code in [200, 302]
    
    def test_source_url_satisfies_requirement(self, auth_client):
        """Test that source URL satisfies source requirement."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': 'Test Recipe',
            'instructions': 'Test instructions',
            'source_name': '',  # No name
            'source_author': '',  # No author
            'source_url': 'https://example.com/recipe',  # Has URL
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
        
        # Should succeed
        assert response.status_code in [200, 302]
    
    def test_multiple_source_fields_satisfy_requirement(self, auth_client):
        """Test that having multiple source fields satisfies requirement."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': 'Test Recipe',
            'instructions': 'Test instructions',
            'source_name': 'Test Cookbook',  # Has name
            'source_author': 'Test Author',  # Has author
            'source_url': 'https://example.com/recipe',  # Has URL
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
        
        # Should succeed
        assert response.status_code in [200, 302]


class TestIngredientRequirements:
    """Test ingredient requirements."""
    
    def test_exactly_three_ingredients_satisfies_requirement(self, auth_client):
        """Test that exactly 3 ingredients satisfies requirement."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': 'Test Recipe',
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
        
        # Should succeed
        assert response.status_code in [200, 302]
    
    def test_more_than_three_ingredients_satisfies_requirement(self, auth_client):
        """Test that more than 3 ingredients satisfies requirement."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': 'Test Recipe',
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
            'ingredient_unit_2': 'tsp',
            'ingredient_description_3': 'butter',
            'ingredient_amount_3': '1/4',
            'ingredient_unit_3': 'cup'
        }
        
        response = auth_client['client'].post('/recipe/new', data=data)
        
        # Should succeed
        assert response.status_code in [200, 302]
    
    def test_ingredients_must_have_descriptions(self, auth_client):
        """Test that ingredients must have descriptions."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': 'Test Recipe',
            'instructions': 'Test instructions',
            'source_name': 'Test Source',
            'ingredient_description_0': '',  # Empty description
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
        assert b'ingredient' in response.data.lower()
    
    def test_ingredients_can_have_empty_amounts(self, auth_client):
        """Test that ingredients can have empty amounts."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': 'Test Recipe',
            'instructions': 'Test instructions',
            'source_name': 'Test Source',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '',  # Empty amount - should be OK
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '',  # Empty amount - should be OK
            'ingredient_unit_1': 'tbsp',
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '',  # Empty amount - should be OK
            'ingredient_unit_2': 'tsp'
        }
        
        response = auth_client['client'].post('/recipe/new', data=data)
        
        # Should succeed - empty amounts are allowed
        assert response.status_code in [200, 302]
    
    def test_ingredients_can_have_empty_units(self, auth_client):
        """Test that ingredients can have empty units."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': 'Test Recipe',
            'instructions': 'Test instructions',
            'source_name': 'Test Source',
            'ingredient_description_0': 'flour',
            'ingredient_amount_0': '1',
            'ingredient_unit_0': '',  # Empty unit - should be OK
            'ingredient_description_1': 'sugar',
            'ingredient_amount_1': '2',
            'ingredient_unit_1': '',  # Empty unit - should be OK
            'ingredient_description_2': 'salt',
            'ingredient_amount_2': '1',
            'ingredient_unit_2': ''  # Empty unit - should be OK
        }
        
        response = auth_client['client'].post('/recipe/new', data=data)
        
        # Should succeed - empty units are allowed
        assert response.status_code in [200, 302]


class TestCompleteRecipeRequirements:
    """Test complete recipe requirements together."""
    
    def test_complete_recipe_with_all_requirements_succeeds(self, auth_client, valid_recipe_data):
        """Test that a complete recipe with all requirements succeeds."""
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].post('/recipe/new', data=valid_recipe_data)
        
        # Should succeed
        assert response.status_code in [200, 302]
    
    def test_recipe_missing_multiple_requirements_shows_multiple_errors(self, auth_client):
        """Test that recipe missing multiple requirements shows multiple errors."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': '',  # Missing name
            'instructions': '',  # Missing instructions
            'source_name': '',  # Missing source
            'source_author': '',
            'source_url': '',
            'ingredient_description_0': 'flour',  # Only 1 ingredient
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup'
            # Missing 2 more ingredients
        }
        
        response = auth_client['client'].post('/recipe/new', data=data)
        
        assert response.status_code in [400, 422]
        
        # Should show multiple error messages
        response_text = response.data.decode('utf-8').lower()
        error_count = response_text.count('required') + response_text.count('ingredient')
        assert error_count >= 3  # Should have multiple errors
    
    def test_minimal_valid_recipe_succeeds(self, auth_client):
        """Test that a minimal valid recipe succeeds."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': 'Minimal Recipe',
            'instructions': 'Mix ingredients and cook.',
            'source_name': 'Minimal Cookbook',
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
        
        # Should succeed
        assert response.status_code in [200, 302]


class TestRecipeRequirementsEdgeCases:
    """Test edge cases for recipe requirements."""
    
    def test_recipe_with_whitespace_only_fields_fails(self, auth_client):
        """Test that recipe with whitespace-only required fields fails."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': '   \t\n   ',  # Whitespace-only name
            'instructions': '   \t\n   ',  # Whitespace-only instructions
            'source_name': '   \t\n   ',  # Whitespace-only source
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
        assert b'required' in response.data.lower()
    
    def test_recipe_with_mixed_valid_invalid_fields(self, auth_client):
        """Test recipe with mix of valid and invalid fields."""
        auth_client['login']('testuser', 'password123')
        
        data = {
            'name': 'Valid Recipe Name',  # Valid name
            'instructions': '',  # Invalid - no instructions
            'source_name': 'Valid Source',  # Valid source
            'ingredient_description_0': 'flour',  # Valid ingredient
            'ingredient_amount_0': '1',
            'ingredient_unit_0': 'cup',
            'ingredient_description_1': 'sugar',  # Valid ingredient
            'ingredient_amount_1': '2',
            'ingredient_unit_1': 'tbsp'
            # Missing third ingredient
        }
        
        response = auth_client['client'].post('/recipe/new', data=data)
        
        assert response.status_code in [400, 422]
        # Should fail due to missing instructions and third ingredient
        response_text = response.data.decode('utf-8').lower()
        assert b'instructions' in response_text or b'ingredient' in response_text
