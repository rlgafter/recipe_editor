"""
Comprehensive tests for the recipe entry form to ensure all parts are present and functioning.
"""
import pytest
from flask import url_for
from unittest.mock import patch, Mock


class TestRecipeFormStructure:
    """Test that all form sections are present and properly structured."""
    
    def test_new_recipe_form_has_all_sections(self, client):
        """Test that the new recipe form contains all required sections."""
        response = client.get('/recipe/new')
        assert response.status_code == 302  # Redirects to login
        
        # Test with authenticated user
        client.post('/auth/login', data={'username': 'testuser', 'password': 'password123'})
        response = client.get('/recipe/new')
        assert response.status_code == 200
        
        # Check for main form structure
        assert b'<form method="POST"' in response.data
        assert b'id="recipeForm"' in response.data
        
        # Check for all major sections
        sections = [
            b'Recipe Name',  # Basic info
            b'Source Information',  # Source section
            b'Time & Serving Information',  # Time/serving section
            b'Ingredients',  # Ingredients section
            b'Instructions',  # Instructions section
            b'Notes',  # Notes section
            b'Visibility',  # Visibility section
            b'Tags',  # Tags section
        ]
        
        for section in sections:
            assert section in response.data, f"Missing section: {section.decode()}"
    
    def test_import_section_present_when_gemini_configured(self, client):
        """Test that import section appears when Gemini is configured."""
        with patch('gemini_service.gemini_service.is_configured', return_value=True):
            client.post('/auth/login', data={'username': 'testuser', 'password': 'password123'})
            response = client.get('/recipe/new')
            assert response.status_code == 200
            
            # Check for import section elements
            import_elements = [
                b'Import Recipe',
                b'From URL',
                b'From File',
                b'drag & drop file here',
                b'Supported: .txt, .pdf',
                b'id="importUrl"',
                b'id="importFile"',
                b'id="dropZone"',
            ]
            
            for element in import_elements:
                assert element in response.data, f"Missing import element: {element.decode()}"
    
    def test_import_section_hidden_when_gemini_not_configured(self, client):
        """Test that import section is hidden when Gemini is not configured."""
        with patch('gemini_service.gemini_service.is_configured', return_value=False):
            client.post('/auth/login', data={'username': 'testuser', 'password': 'password123'})
            response = client.get('/recipe/new')
            assert response.status_code == 200
            
            # Import section should not be present
            assert b'Import Recipe' not in response.data
            assert b'id="importSection"' not in response.data
    
    def test_edit_recipe_form_has_all_sections(self, auth_client, test_recipes):
        """Test that the edit recipe form contains all required sections."""
        if not test_recipes:
            pytest.skip("No test recipes available")
        
        auth_client['login']('testuser', 'password123')
        recipe = test_recipes[0]  # Use first recipe
        
        response = auth_client['client'].get(f'/recipe/{recipe["id"]}/edit')
        assert response.status_code == 200
        
        # Check for main form structure
        assert b'<form method="POST"' in response.data
        assert b'id="recipeForm"' in response.data
        
        # Check for all major sections (same as new recipe)
        sections = [
            b'Recipe Name',
            b'Source Information',
            b'Time & Serving Information',
            b'Ingredients',
            b'Instructions',
            b'Notes',
            b'Visibility',
            b'Tags',
        ]
        
        for section in sections:
            assert section in response.data, f"Missing section: {section.decode()}"
    
    def test_edit_form_does_not_show_import_section(self, auth_client, test_recipes):
        """Test that edit form never shows import section."""
        if not test_recipes:
            pytest.skip("No test recipes available")
        
        auth_client['login']('testuser', 'password123')
        recipe = test_recipes[0]
        
        response = auth_client['client'].get(f'/recipe/{recipe["id"]}/edit')
        assert response.status_code == 200
        
        # Import section should not be present in edit mode
        assert b'Import Recipe' not in response.data
        assert b'id="importSection"' not in response.data


class TestFormFields:
    """Test that all form fields are present with correct attributes."""
    
    def test_recipe_name_field(self, auth_client):
        """Test recipe name field is present and properly configured."""
        auth_client['login']('testuser', 'password123')
        response = auth_client['client'].get('/recipe/new')
        assert response.status_code == 200
        
        # Check for name field
        assert b'name="name"' in response.data
        assert b'id="name"' in response.data
        assert b'required' in response.data
        assert b'maxlength="200"' in response.data
        assert b'placeholder' in response.data or b'Recipe Name' in response.data
    
    def test_source_information_fields(self, auth_client):
        """Test source information fields are present."""
        auth_client['login']('testuser', 'password123')
        response = auth_client['client'].get('/recipe/new')
        assert response.status_code == 200
        
        # Check for source fields
        source_fields = [
            b'name="source_name"',
            b'name="source_author"',
            b'name="source_url"',
            b'name="source_issue"',
        ]
        
        for field in source_fields:
            assert field in response.data, f"Missing source field: {field.decode()}"
    
    def test_time_and_serving_fields(self, auth_client):
        """Test time and serving fields are present."""
        auth_client['login']('testuser', 'password123')
        response = auth_client['client'].get('/recipe/new')
        assert response.status_code == 200
        
        # Check for time/serving fields
        time_fields = [
            b'name="prep_time"',
            b'name="cook_time"',
            b'name="servings"',
        ]
        
        for field in time_fields:
            assert field in response.data, f"Missing time field: {field.decode()}"
        
        # Check for proper input types
        assert b'type="number"' in response.data  # For prep_time and cook_time
        assert b'min="0"' in response.data
        assert b'max="9999"' in response.data
    
    def test_ingredients_fields(self, auth_client):
        """Test ingredients fields are present and properly configured."""
        auth_client['login']('testuser', 'password123')
        response = auth_client['client'].get('/recipe/new')
        assert response.status_code == 200
        
        # Check for ingredient fields (should have 5 default rows)
        ingredient_patterns = [
            b'name="ingredient_amount_0"',
            b'name="ingredient_unit_0"',
            b'name="ingredient_description_0"',
            b'name="ingredient_amount_1"',
            b'name="ingredient_unit_1"',
            b'name="ingredient_description_1"',
        ]
        
        for pattern in ingredient_patterns:
            assert pattern in response.data, f"Missing ingredient field: {pattern.decode()}"
        
        # Check for add ingredient button
        assert b'onclick="addIngredient()"' in response.data
        assert b'Add Ingredient' in response.data
    
    def test_instructions_field(self, auth_client):
        """Test instructions field is present."""
        auth_client['login']('testuser', 'password123')
        response = auth_client['client'].get('/recipe/new')
        assert response.status_code == 200
        
        # Check for instructions field
        assert b'name="instructions"' in response.data
        assert b'id="instructions"' in response.data
        assert b'<textarea' in response.data
        assert b'rows="8"' in response.data
    
    def test_notes_field(self, auth_client):
        """Test notes field is present."""
        auth_client['login']('testuser', 'password123')
        response = auth_client['client'].get('/recipe/new')
        assert response.status_code == 200
        
        # Check for notes field
        assert b'name="notes"' in response.data
        assert b'id="notes"' in response.data
        assert b'<textarea' in response.data
        assert b'rows="4"' in response.data  # Notes field has 4 rows, not 3
    
    def test_visibility_field(self, auth_client):
        """Test visibility field is present."""
        auth_client['login']('testuser', 'password123')
        response = auth_client['client'].get('/recipe/new')
        assert response.status_code == 200
        
        # Check for visibility field
        assert b'name="visibility"' in response.data
        assert b'id="visibility"' in response.data
        assert b'<select' in response.data
        
        # Check for visibility options
        visibility_options = [b'incomplete', b'private', b'public']
        for option in visibility_options:
            assert option in response.data, f"Missing visibility option: {option.decode()}"
    
    def test_tags_field(self, auth_client):
        """Test tags field is present."""
        auth_client['login']('testuser', 'password123')
        response = auth_client['client'].get('/recipe/new')
        assert response.status_code == 200
        
        # Check for tags field
        assert b'name="tags"' in response.data
        assert b'id="tags"' in response.data
        assert b'placeholder="e.g., dessert, chocolate, quick"' in response.data


class TestFormValidation:
    """Test form validation and error handling."""
    
    def test_recipe_name_required_validation(self, auth_client):
        """Test that recipe name is required."""
        auth_client['login']('testuser', 'password123')
        
        # Submit form without recipe name
        response = auth_client['client'].post('/recipe/new', data={
            'name': '',  # Empty name
            'instructions': 'Test instructions',
            'visibility': 'incomplete'
        })
        
        assert response.status_code == 400
        assert b'Please provide a valid recipe name' in response.data
    
    def test_minimum_ingredients_validation(self, auth_client):
        """Test that at least 3 ingredients are required."""
        auth_client['login']('testuser', 'password123')
        
        # Submit form with only 1 ingredient
        response = auth_client['client'].post('/recipe/new', data={
            'name': 'Test Recipe',
            'ingredient_description_0': 'Only one ingredient',
            'instructions': 'Test instructions',
            'visibility': 'incomplete'
        })
        
        assert response.status_code == 400
        assert b'Recipes must have at least three ingredients' in response.data
    
    def test_url_validation(self, auth_client):
        """Test URL validation for source URL."""
        auth_client['login']('testuser', 'password123')
        
        # Submit form with invalid URL
        response = auth_client['client'].post('/recipe/new', data={
            'name': 'Test Recipe',
            'ingredient_description_0': 'Ingredient 1',
            'ingredient_description_1': 'Ingredient 2', 
            'ingredient_description_2': 'Ingredient 3',
            'source_url': 'not-a-valid-url',
            'instructions': 'Test instructions',
            'visibility': 'incomplete'
        })
        
        assert response.status_code == 400
        assert b'Please enter a valid URL (must start with http:// or https://)' in response.data


class TestFormActions:
    """Test form action buttons and functionality."""
    
    def test_form_action_buttons(self, auth_client):
        """Test that all form action buttons are present."""
        auth_client['login']('testuser', 'password123')
        response = auth_client['client'].get('/recipe/new')
        assert response.status_code == 200
        
        # Check for action buttons
        action_buttons = [
            b'type="submit"',
            b'Create Recipe',  # Button text is "Create Recipe" for new recipes
            b'Cancel',
        ]
        
        for button in action_buttons:
            assert button in response.data, f"Missing action button: {button.decode()}"
    
    def test_edit_form_has_delete_button(self, auth_client, test_recipes):
        """Test that edit form has delete button for user's own recipes."""
        if not test_recipes:
            pytest.skip("No test recipes available")
        
        auth_client['login']('testuser', 'password123')
        recipe = test_recipes[0]  # User's own recipe
        
        response = auth_client['client'].get(f'/recipe/{recipe["id"]}/edit')
        assert response.status_code == 200
        
        # Check for delete button and modal
        assert b'Delete Recipe' in response.data
        assert b'data-bs-toggle="modal"' in response.data
        assert b'data-bs-target="#deleteModal"' in response.data
        assert b'id="deleteModal"' in response.data
    
    def test_edit_form_no_delete_button_for_other_users_recipes(self, auth_client):
        """Test that edit form doesn't have delete button for other users' recipes."""
        auth_client['login']('testuser', 'password123')
        
        # Try to edit a recipe that doesn't belong to the user
        response = auth_client['client'].get('/recipe/999/edit')
        assert response.status_code in [302, 403, 404]  # Should redirect or deny access


class TestFormJavaScript:
    """Test JavaScript functionality in the form."""
    
    def test_javascript_functions_present(self, auth_client):
        """Test that required JavaScript functions are present."""
        auth_client['login']('testuser', 'password123')
        response = auth_client['client'].get('/recipe/new')
        assert response.status_code == 200
        
        # Check for JavaScript functions
        js_functions = [
            b'function addIngredient()',
            b'function removeIngredient(',
            b'function toggleAdditionalIngredients()',
        ]
        
        for func in js_functions:
            assert func in response.data, f"Missing JavaScript function: {func.decode()}"
    
    def test_ingredient_toggle_functionality(self, auth_client):
        """Test that ingredient toggle button is present."""
        auth_client['login']('testuser', 'password123')
        response = auth_client['client'].get('/recipe/new')
        assert response.status_code == 200
        
        # Check for toggle button
        assert b'id="toggleIngredientsBtn"' in response.data
        assert b'onclick="toggleAdditionalIngredients()"' in response.data
        assert b'Show 3 more ingredients' in response.data
        assert b'id="additionalIngredients"' in response.data
    
    def test_tooltips_present(self, auth_client):
        """Test that tooltips are configured for form fields."""
        auth_client['login']('testuser', 'password123')
        response = auth_client['client'].get('/recipe/new')
        assert response.status_code == 200
        
        # Check for tooltip attributes
        assert b'data-bs-toggle="tooltip"' in response.data
        assert b'data-bs-placement="top"' in response.data
        assert b'bi-question-circle' in response.data


class TestFormAccessibility:
    """Test form accessibility features."""
    
    def test_form_labels_present(self, auth_client):
        """Test that all form fields have proper labels."""
        auth_client['login']('testuser', 'password123')
        response = auth_client['client'].get('/recipe/new')
        assert response.status_code == 200
        
        # Check for form labels
        labels = [
            b'<label for="name"',
            b'<label for="prep_time"',
            b'<label for="cook_time"',
            b'<label for="servings"',
            b'<label for="instructions"',
            b'<label for="notes"',
            b'<label for="visibility"',
            b'<label for="tags"',
        ]
        
        for label in labels:
            assert label in response.data, f"Missing form label: {label.decode()}"
    
    def test_required_field_indicators(self, auth_client):
        """Test that required fields are properly marked."""
        auth_client['login']('testuser', 'password123')
        response = auth_client['client'].get('/recipe/new')
        assert response.status_code == 200
        
        # Check for required field indicators
        assert b'<span class="text-danger">*</span>' in response.data
        assert b'required' in response.data
    
    def test_form_autocomplete_attributes(self, auth_client):
        """Test that form fields have appropriate autocomplete attributes."""
        auth_client['login']('testuser', 'password123')
        response = auth_client['client'].get('/recipe/new')
        assert response.status_code == 200
        
        # Check for autocomplete attributes
        assert b'autocomplete="off"' in response.data
        assert b'autocomplete="url"' in response.data  # For source_url


class TestFormResponsiveness:
    """Test form responsiveness and mobile optimization."""
    
    def test_mobile_css_present(self, auth_client):
        """Test that mobile CSS optimizations are present."""
        auth_client['login']('testuser', 'password123')
        response = auth_client['client'].get('/recipe/new')
        assert response.status_code == 200
        
        # Check for mobile CSS
        mobile_css = [
            b'@media (max-width: 768px)',
            b'.ingredient-row',
            b'.btn-sm',
            b'#toggleIngredientsBtn',
        ]
        
        for css in mobile_css:
            assert css in response.data, f"Missing mobile CSS: {css.decode()}"
    
    def test_bootstrap_classes_present(self, auth_client):
        """Test that Bootstrap classes are used for responsiveness."""
        auth_client['login']('testuser', 'password123')
        response = auth_client['client'].get('/recipe/new')
        assert response.status_code == 200
        
        # Check for Bootstrap responsive classes
        bootstrap_classes = [
            b'col-lg-8',
            b'col-md-6',
            b'col-md-2',
            b'col-md-7',
            b'col-md-1',
            b'col-md-4',
        ]
        
        for class_name in bootstrap_classes:
            assert class_name in response.data, f"Missing Bootstrap class: {class_name.decode()}"
