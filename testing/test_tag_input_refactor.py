"""
Test suite for tag input refactor.

Tests cover:
- Tag input with comma delimiters
- Tag input with space delimiters
- Tag input with mixed delimiters
- Tag normalization to lowercase
- Tag filtering with ANY/ALL matching
- Case-insensitive tag matching
- Tag autocomplete functionality (via form submission)
"""

import pytest
from db_models import db, User, Recipe, Tag
from mysql_storage import MySQLStorage
from flask import url_for


class TestTagInputParsing:
    """Test tag input parsing with various delimiters."""
    
    def test_create_recipe_with_comma_delimited_tags(self, app, auth_client):
        """Test creating a recipe with tags separated by commas."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            storage = MySQLStorage(db.session)
            user = User.query.filter_by(username='testuser').first()
            
            # Create recipe with comma-delimited tags
            recipe_data = {
                'name': 'Comma Tag Recipe',
                'instructions': 'Test instructions for comma tags',
                'source': {
                    'name': 'Test Source',
                    'author': 'Test Author'
                },
                'tags': ['dessert', 'chocolate', 'quick'],
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'cocoa', 'amount': '3', 'unit': 'tbsp'}
                ],
                'visibility': 'private'
            }
            
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # Verify tags were created and normalized to lowercase
            assert recipe is not None
            assert len(recipe.tags) == 3
            
            tag_names = [tag.name for tag in recipe.tags]
            assert 'dessert' in tag_names
            assert 'chocolate' in tag_names
            assert 'quick' in tag_names
            
            # Verify tags are stored in lowercase
            for tag in recipe.tags:
                assert tag.name == tag.name.lower()
    
    def test_create_recipe_with_space_delimited_tags(self, app, auth_client):
        """Test creating a recipe with tags separated by spaces."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            storage = MySQLStorage(db.session)
            user = User.query.filter_by(username='testuser').first()
            
            # Create recipe with space-delimited tags
            recipe_data = {
                'name': 'Space Tag Recipe',
                'instructions': 'Test instructions for space tags',
                'source': {
                    'name': 'Test Source',
                    'author': 'Test Author'
                },
                'tags': ['breakfast', 'easy', 'healthy'],
                'ingredients': [
                    {'description': 'eggs', 'amount': '2', 'unit': ''},
                    {'description': 'bread', 'amount': '2', 'unit': 'slices'},
                    {'description': 'butter', 'amount': '1', 'unit': 'tbsp'}
                ],
                'visibility': 'private'
            }
            
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # Verify tags were created
            assert recipe is not None
            assert len(recipe.tags) == 3
            
            tag_names = [tag.name for tag in recipe.tags]
            assert 'breakfast' in tag_names
            assert 'easy' in tag_names
            assert 'healthy' in tag_names
    
    def test_create_recipe_with_mixed_delimiters(self, app, auth_client):
        """Test creating a recipe with mixed comma and space delimiters."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            storage = MySQLStorage(db.session)
            user = User.query.filter_by(username='testuser').first()
            
            # Create recipe with mixed delimiters
            recipe_data = {
                'name': 'Mixed Delimiter Recipe',
                'instructions': 'Test instructions for mixed delimiters',
                'source': {
                    'name': 'Test Source',
                    'author': 'Test Author'
                },
                'tags': ['dinner', 'pasta', 'italian'],
                'ingredients': [
                    {'description': 'pasta', 'amount': '1', 'unit': 'lb'},
                    {'description': 'sauce', 'amount': '2', 'unit': 'cups'},
                    {'description': 'cheese', 'amount': '1/2', 'unit': 'cup'}
                ],
                'visibility': 'private'
            }
            
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # Verify all tags were created
            assert recipe is not None
            assert len(recipe.tags) == 3
            
            tag_names = [tag.name for tag in recipe.tags]
            assert 'dinner' in tag_names
            assert 'pasta' in tag_names
            assert 'italian' in tag_names
    
    def test_tag_normalization_to_lowercase(self, app, auth_client):
        """Test that tags are normalized to lowercase regardless of input case."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            storage = MySQLStorage(db.session)
            user = User.query.filter_by(username='testuser').first()
            
            # Create recipe with mixed case tags
            recipe_data = {
                'name': 'Case Normalization Recipe',
                'instructions': 'Test case normalization',
                'source': {
                    'name': 'Test Source',
                    'author': 'Test Author'
                },
                'tags': ['DESSERT', 'Chocolate', 'QUICK'],
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'cocoa', 'amount': '3', 'unit': 'tbsp'}
                ],
                'visibility': 'private'
            }
            
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # Verify tags are stored in lowercase
            assert recipe is not None
            tag_names = [tag.name for tag in recipe.tags]
            
            # All tags should be lowercase
            for tag_name in tag_names:
                assert tag_name == tag_name.lower()
            
            # Verify specific tags exist (in lowercase)
            assert 'dessert' in tag_names
            assert 'chocolate' in tag_names
            assert 'quick' in tag_names


class TestTagFormSubmission:
    """Test tag input through form submission."""
    
    def test_form_submission_with_comma_tags(self, app, auth_client):
        """Test form submission with comma-delimited tags."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            client = auth_client['client']
            
            # Submit form with comma-delimited tags
            response = client.post('/recipe/new', data={
                'name': 'Form Comma Tags Recipe',
                'instructions': 'Test form submission with comma tags',
                'source_name': 'Test Source',
                'source_author': 'Test Author',
                'tags': 'dessert, chocolate, quick',
                'ingredient_description_0': 'flour',
                'ingredient_amount_0': '1',
                'ingredient_unit_0': 'cup',
                'ingredient_description_1': 'sugar',
                'ingredient_amount_1': '2',
                'ingredient_unit_1': 'tbsp',
                'ingredient_description_2': 'cocoa',
                'ingredient_amount_2': '3',
                'ingredient_unit_2': 'tbsp',
                'visibility': 'private'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verify recipe was created with tags
            user = User.query.filter_by(username='testuser').first()
            recipe = Recipe.query.filter_by(name='Form Comma Tags Recipe', user_id=user.id).first()
            
            assert recipe is not None
            assert len(recipe.tags) == 3
            
            tag_names = [tag.name for tag in recipe.tags]
            assert 'dessert' in tag_names
            assert 'chocolate' in tag_names
            assert 'quick' in tag_names
    
    def test_form_submission_with_space_tags(self, app, auth_client):
        """Test form submission with space-delimited tags."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            client = auth_client['client']
            
            # Submit form with space-delimited tags
            response = client.post('/recipe/new', data={
                'name': 'Form Space Tags Recipe',
                'instructions': 'Test form submission with space tags',
                'source_name': 'Test Source',
                'source_author': 'Test Author',
                'tags': 'breakfast easy healthy',
                'ingredient_description_0': 'eggs',
                'ingredient_amount_0': '2',
                'ingredient_unit_0': '',
                'ingredient_description_1': 'bread',
                'ingredient_amount_1': '2',
                'ingredient_unit_1': 'slices',
                'ingredient_description_2': 'butter',
                'ingredient_amount_2': '1',
                'ingredient_unit_2': 'tbsp',
                'visibility': 'private'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verify recipe was created with tags
            user = User.query.filter_by(username='testuser').first()
            recipe = Recipe.query.filter_by(name='Form Space Tags Recipe', user_id=user.id).first()
            
            assert recipe is not None
            assert len(recipe.tags) == 3
            
            tag_names = [tag.name for tag in recipe.tags]
            assert 'breakfast' in tag_names
            assert 'easy' in tag_names
            assert 'healthy' in tag_names
    
    def test_form_submission_with_mixed_delimiters(self, app, auth_client):
        """Test form submission with mixed comma and space delimiters."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            client = auth_client['client']
            
            # Submit form with mixed delimiters: "dinner, pasta italian"
            response = client.post('/recipe/new', data={
                'name': 'Form Mixed Tags Recipe',
                'instructions': 'Test form submission with mixed delimiters',
                'source_name': 'Test Source',
                'source_author': 'Test Author',
                'tags': 'dinner, pasta italian',
                'ingredient_description_0': 'pasta',
                'ingredient_amount_0': '1',
                'ingredient_unit_0': 'lb',
                'ingredient_description_1': 'sauce',
                'ingredient_amount_1': '2',
                'ingredient_unit_1': 'cups',
                'ingredient_description_2': 'cheese',
                'ingredient_amount_2': '1/2',
                'ingredient_unit_2': 'cup',
                'visibility': 'private'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verify recipe was created with all tags
            user = User.query.filter_by(username='testuser').first()
            recipe = Recipe.query.filter_by(name='Form Mixed Tags Recipe', user_id=user.id).first()
            
            assert recipe is not None
            assert len(recipe.tags) == 3
            
            tag_names = [tag.name for tag in recipe.tags]
            assert 'dinner' in tag_names
            assert 'pasta' in tag_names
            assert 'italian' in tag_names


class TestTagFiltering:
    """Test tag filtering functionality."""
    
    def test_filter_recipes_by_tags_any_match(self, app, auth_client):
        """Test filtering recipes with ANY tag matching."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            storage = MySQLStorage(db.session)
            user = User.query.filter_by(username='testuser').first()
            
            # Create recipes with different tags
            recipe1_data = {
                'name': 'Dessert Recipe',
                'instructions': 'Test dessert recipe',
                'source': {'name': 'Test Source', 'author': 'Test Author'},
                'tags': ['dessert', 'chocolate'],
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'cocoa', 'amount': '3', 'unit': 'tbsp'}
                ],
                'visibility': 'private'
            }
            
            recipe2_data = {
                'name': 'Breakfast Recipe',
                'instructions': 'Test breakfast recipe',
                'source': {'name': 'Test Source', 'author': 'Test Author'},
                'tags': ['breakfast', 'easy'],
                'ingredients': [
                    {'description': 'eggs', 'amount': '2', 'unit': ''},
                    {'description': 'bread', 'amount': '2', 'unit': 'slices'},
                    {'description': 'butter', 'amount': '1', 'unit': 'tbsp'}
                ],
                'visibility': 'private'
            }
            
            recipe3_data = {
                'name': 'Chocolate Recipe',
                'instructions': 'Test chocolate recipe',
                'source': {'name': 'Test Source', 'author': 'Test Author'},
                'tags': ['chocolate', 'quick'],
                'ingredients': [
                    {'description': 'chocolate', 'amount': '1', 'unit': 'cup'},
                    {'description': 'milk', 'amount': '2', 'unit': 'cups'},
                    {'description': 'sugar', 'amount': '1', 'unit': 'tbsp'}
                ],
                'visibility': 'private'
            }
            
            storage.save_recipe(recipe1_data, user.id)
            storage.save_recipe(recipe2_data, user.id)
            storage.save_recipe(recipe3_data, user.id)
            
            # Filter by 'chocolate' - should match recipe1 and recipe3 (ANY match)
            filtered = storage.filter_recipes_by_tags(['chocolate'], match_all=False, user_id=user.id)
            
            assert len(filtered) == 2
            recipe_names = [r.name for r in filtered]
            assert 'Dessert Recipe' in recipe_names
            assert 'Chocolate Recipe' in recipe_names
            assert 'Breakfast Recipe' not in recipe_names
    
    def test_filter_recipes_by_tags_all_match(self, app, auth_client):
        """Test filtering recipes with ALL tags matching."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            storage = MySQLStorage(db.session)
            user = User.query.filter_by(username='testuser').first()
            
            # Create recipes with different tags
            recipe1_data = {
                'name': 'Dessert Chocolate Recipe',
                'instructions': 'Test dessert chocolate recipe',
                'source': {'name': 'Test Source', 'author': 'Test Author'},
                'tags': ['dessert', 'chocolate', 'quick'],
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'cocoa', 'amount': '3', 'unit': 'tbsp'}
                ],
                'visibility': 'private'
            }
            
            recipe2_data = {
                'name': 'Dessert Only Recipe',
                'instructions': 'Test dessert only recipe',
                'source': {'name': 'Test Source', 'author': 'Test Author'},
                'tags': ['dessert'],
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'eggs', 'amount': '2', 'unit': ''}
                ],
                'visibility': 'private'
            }
            
            recipe3_data = {
                'name': 'Chocolate Quick Recipe',
                'instructions': 'Test chocolate quick recipe',
                'source': {'name': 'Test Source', 'author': 'Test Author'},
                'tags': ['chocolate', 'quick'],
                'ingredients': [
                    {'description': 'chocolate', 'amount': '1', 'unit': 'cup'},
                    {'description': 'milk', 'amount': '2', 'unit': 'cups'},
                    {'description': 'sugar', 'amount': '1', 'unit': 'tbsp'}
                ],
                'visibility': 'private'
            }
            
            storage.save_recipe(recipe1_data, user.id)
            storage.save_recipe(recipe2_data, user.id)
            storage.save_recipe(recipe3_data, user.id)
            
            # Filter by 'dessert' AND 'chocolate' - should match only recipe1 (ALL match)
            filtered = storage.filter_recipes_by_tags(['dessert', 'chocolate'], match_all=True, user_id=user.id)
            
            assert len(filtered) == 1
            assert filtered[0].name == 'Dessert Chocolate Recipe'
    
    def test_filter_with_case_insensitive_matching(self, app, auth_client):
        """Test that tag filtering is case-insensitive."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            storage = MySQLStorage(db.session)
            user = User.query.filter_by(username='testuser').first()
            
            # Create recipe with lowercase tags
            recipe_data = {
                'name': 'Case Test Recipe',
                'instructions': 'Test case insensitive matching',
                'source': {'name': 'Test Source', 'author': 'Test Author'},
                'tags': ['dessert', 'chocolate'],
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'cocoa', 'amount': '3', 'unit': 'tbsp'}
                ],
                'visibility': 'private'
            }
            
            storage.save_recipe(recipe_data, user.id)
            
            # Filter with uppercase tag name - should still match
            filtered = storage.filter_recipes_by_tags(['DESSERT'], match_all=False, user_id=user.id)
            
            assert len(filtered) == 1
            assert filtered[0].name == 'Case Test Recipe'
            
            # Filter with mixed case - should still match
            filtered2 = storage.filter_recipes_by_tags(['Chocolate'], match_all=False, user_id=user.id)
            
            assert len(filtered2) == 1
            assert filtered2[0].name == 'Case Test Recipe'


class TestTagSearch:
    """Test tag search functionality."""
    
    def test_search_recipes_with_tag_filter(self, app, auth_client):
        """Test searching recipes with tag filter."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            storage = MySQLStorage(db.session)
            user = User.query.filter_by(username='testuser').first()
            
            # Create recipes
            recipe1_data = {
                'name': 'Chocolate Cake',
                'instructions': 'Bake a chocolate cake',
                'source': {'name': 'Test Source', 'author': 'Test Author'},
                'tags': ['dessert', 'chocolate'],
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'cocoa', 'amount': '3', 'unit': 'tbsp'}
                ],
                'visibility': 'private'
            }
            
            recipe2_data = {
                'name': 'Vanilla Cake',
                'instructions': 'Bake a vanilla cake',
                'source': {'name': 'Test Source', 'author': 'Test Author'},
                'tags': ['dessert', 'vanilla'],
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'vanilla', 'amount': '1', 'unit': 'tsp'}
                ],
                'visibility': 'private'
            }
            
            storage.save_recipe(recipe1_data, user.id)
            storage.save_recipe(recipe2_data, user.id)
            
            # Search with tag filter - should find only chocolate recipes
            results = storage.search_recipes(
                search_term='cake',
                tag_names=['chocolate'],
                match_all_tags=False,
                user_id=user.id
            )
            
            assert len(results) == 1
            assert results[0].name == 'Chocolate Cake'


class TestTagEdit:
    """Test editing recipes with tags."""
    
    def test_edit_recipe_preserves_tags(self, app, auth_client):
        """Test that editing a recipe preserves existing tags."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            storage = MySQLStorage(db.session)
            user = User.query.filter_by(username='testuser').first()
            
            # Create recipe with tags
            recipe_data = {
                'name': 'Original Recipe',
                'instructions': 'Original instructions',
                'source': {'name': 'Test Source', 'author': 'Test Author'},
                'tags': ['dessert', 'chocolate'],
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'cocoa', 'amount': '3', 'unit': 'tbsp'}
                ],
                'visibility': 'private'
            }
            
            recipe = storage.save_recipe(recipe_data, user.id)
            recipe_id = recipe.id
            
            # Verify original tags
            assert len(recipe.tags) == 2
            tag_names = [tag.name for tag in recipe.tags]
            assert 'dessert' in tag_names
            assert 'chocolate' in tag_names
            
            # Edit recipe with new tags
            updated_data = {
                'name': 'Updated Recipe',
                'instructions': 'Updated instructions',
                'source': {'name': 'Test Source', 'author': 'Test Author'},
                'tags': ['dessert', 'quick'],  # Changed from chocolate to quick
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'cocoa', 'amount': '3', 'unit': 'tbsp'}
                ],
                'visibility': 'private'
            }
            
            updated_recipe = storage.save_recipe(updated_data, user.id, recipe_id=recipe_id)
            
            # Verify tags were updated
            assert updated_recipe.id == recipe_id
            assert len(updated_recipe.tags) == 2
            updated_tag_names = [tag.name for tag in updated_recipe.tags]
            assert 'dessert' in updated_tag_names
            assert 'quick' in updated_tag_names
            assert 'chocolate' not in updated_tag_names
    
    def test_edit_recipe_with_form_submission(self, app, auth_client):
        """Test editing recipe tags through form submission."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            storage = MySQLStorage(db.session)
            user = User.query.filter_by(username='testuser').first()
            
            # Create recipe
            recipe_data = {
                'name': 'Form Edit Recipe',
                'instructions': 'Original instructions',
                'source': {'name': 'Test Source', 'author': 'Test Author'},
                'tags': ['original', 'tag'],
                'ingredients': [
                    {'description': 'flour', 'amount': '1', 'unit': 'cup'},
                    {'description': 'sugar', 'amount': '2', 'unit': 'tbsp'},
                    {'description': 'cocoa', 'amount': '3', 'unit': 'tbsp'}
                ],
                'visibility': 'private'
            }
            
            recipe = storage.save_recipe(recipe_data, user.id)
            recipe_id = recipe.id
            
            # Edit via form submission
            client = auth_client['client']
            response = client.post(f'/recipe/{recipe_id}/edit', data={
                'name': 'Form Edit Recipe',
                'instructions': 'Updated instructions',
                'source_name': 'Test Source',
                'source_author': 'Test Author',
                'tags': 'updated, new tags',
                'ingredient_description_0': 'flour',
                'ingredient_amount_0': '1',
                'ingredient_unit_0': 'cup',
                'ingredient_description_1': 'sugar',
                'ingredient_amount_1': '2',
                'ingredient_unit_1': 'tbsp',
                'ingredient_description_2': 'cocoa',
                'ingredient_amount_2': '3',
                'ingredient_unit_2': 'tbsp',
                'visibility': 'private'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verify tags were updated
            updated_recipe = Recipe.query.get(recipe_id)
            assert updated_recipe is not None
            assert len(updated_recipe.tags) == 3  # 'updated', 'new', 'tags'
            
            tag_names = [tag.name for tag in updated_recipe.tags]
            assert 'updated' in tag_names
            assert 'new' in tag_names
            assert 'tags' in tag_names




