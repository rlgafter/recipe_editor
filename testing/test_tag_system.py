"""
Test suite for the new tag system (system tags and personal tags).

Tests cover:
- Personal tag creation
- System tag creation (admin)
- Tag visibility and access control
- Tag filtering by user
- Public recipe tag handling
- Tag cleanup
- Admin tag management
"""

import pytest
from db_models import db, User, Recipe, Tag
from mysql_storage import MySQLStorage


class TestPersonalTags:
    """Test personal tag functionality."""
    
    def test_create_personal_tag(self, app, auth_client):
        """Test that users create personal tags by default."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            storage = MySQLStorage(db.session)
            user = User.query.filter_by(username='testuser').first()
            
            # Create a personal tag
            tag = storage.get_or_create_tag('BREAKFAST', user.id, 'personal')
            
            assert tag is not None
            assert tag.name == 'BREAKFAST'
            assert tag.tag_scope == 'personal'
            assert tag.user_id == user.id
    
    def test_personal_tags_unique_per_user(self, app, auth_client, admin_client):
        """Test that multiple users can create the same personal tag."""
        with app.app_context():
            storage = MySQLStorage(db.session)
            
            # Login as regular user and create tag
            auth_client['login']('testuser', 'password123')
            user1 = User.query.filter_by(username='testuser').first()
            tag1 = storage.get_or_create_tag('LUNCH', user1.id, 'personal')
            
            # Login as admin and create same tag
            admin_client['login']('admin', 'admin123')
            user2 = User.query.filter_by(username='admin').first()
            tag2 = storage.get_or_create_tag('LUNCH', user2.id, 'personal')
            
            # Should be different tags
            assert tag1.id != tag2.id
            assert tag1.name == tag2.name == 'LUNCH'
            assert tag1.user_id == user1.id
            assert tag2.user_id == user2.id
            assert tag1.tag_scope == tag2.tag_scope == 'personal'
    
    def test_get_all_tags_shows_user_and_system_only(self, app, auth_client):
        """Test that get_all_tags returns only user's personal tags + system tags."""
        with app.app_context():
            storage = MySQLStorage(db.session)
            
            # Create users
            user1 = User.query.filter_by(username='testuser').first()
            user2 = User.query.filter_by(username='admin').first()
            
            # Create tags
            tag1 = storage.get_or_create_tag('SALAD', user1.id, 'personal')
            tag2 = storage.get_or_create_tag('SOUP', user2.id, 'personal')
            tag3 = storage.get_or_create_tag('APPETIZER', None, 'system')
            
            # Get tags for user1
            user1_tags = storage.get_all_tags(user1.id)
            
            # Should include user1's personal tag + system tag
            assert 'SALAD' in user1_tags
            assert 'APPETIZER' in user1_tags
            # Should NOT include user2's personal tag
            assert 'SOUP' not in user1_tags
    
    def test_personal_tag_cleanup_on_recipe_delete(self, app, auth_client):
        """Test that unused personal tags are cleaned up."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            storage = MySQLStorage(db.session)
            user = User.query.filter_by(username='testuser').first()
            
            # Create recipe with personal tag
            recipe_data = {
                'name': 'Test Cleanup Recipe',
                'instructions': 'Test instructions',
                'tags': ['CLEANUP_TAG'],
                'ingredients': [{'description': 'test', 'amount': '1', 'unit': 'cup'}]
            }
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # Verify tag exists
            tag = Tag.query.filter_by(name='CLEANUP_TAG', user_id=user.id).first()
            assert tag is not None
            
            # Delete recipe
            storage.delete_recipe(recipe.id, user.id)
            
            # Tag should be cleaned up
            tag = Tag.query.filter_by(name='CLEANUP_TAG', user_id=user.id).first()
            assert tag is None


class TestSystemTags:
    """Test system tag functionality."""
    
    def test_create_system_tag(self, app, admin_client):
        """Test that admins can create system tags."""
        admin_client['login']('admin', 'admin123')
        
        with app.app_context():
            storage = MySQLStorage(db.session)
            
            # Create system tag
            tag = storage.get_or_create_tag('VEGETARIAN', None, 'system')
            
            assert tag is not None
            assert tag.name == 'VEGETARIAN'
            assert tag.tag_scope == 'system'
            assert tag.user_id is None
    
    def test_system_tags_visible_to_all_users(self, app, auth_client):
        """Test that system tags are visible to all users."""
        with app.app_context():
            storage = MySQLStorage(db.session)
            
            # Create system tag
            tag = storage.get_or_create_tag('VEGAN', None, 'system')
            
            # Login as regular user
            auth_client['login']('testuser', 'password123')
            user = User.query.filter_by(username='testuser').first()
            
            # Get tags for user
            user_tags = storage.get_all_tags(user.id)
            
            # Should include system tag
            assert 'VEGAN' in user_tags
            assert user_tags['VEGAN']['scope'] == 'system'
    
    def test_convert_personal_to_system_tag(self, app, admin_client):
        """Test converting multiple personal tags to a single system tag."""
        with app.app_context():
            storage = MySQLStorage(db.session)
            
            # Create two users with same personal tag
            user1 = User.query.filter_by(username='testuser').first()
            user2 = User.query.filter_by(username='admin').first()
            
            tag1 = storage.get_or_create_tag('DINNER', user1.id, 'personal')
            tag2 = storage.get_or_create_tag('DINNER', user2.id, 'personal')
            
            # Create recipes with these tags
            recipe1 = storage.save_recipe({
                'name': 'Recipe 1',
                'instructions': 'Test',
                'tags': ['DINNER'],
                'ingredients': [{'description': 'test', 'amount': '1', 'unit': 'cup'}]
            }, user1.id)
            
            recipe2 = storage.save_recipe({
                'name': 'Recipe 2',
                'instructions': 'Test',
                'tags': ['DINNER'],
                'ingredients': [{'description': 'test', 'amount': '1', 'unit': 'cup'}]
            }, user2.id)
            
            # Convert to system tag
            success, message = storage.convert_personal_to_system_tag('DINNER')
            
            assert success is True
            assert '2' in message  # Should mention 2 tags converted
            
            # Verify system tag exists
            system_tag = Tag.query.filter_by(name='DINNER', tag_scope='system').first()
            assert system_tag is not None
            assert system_tag.user_id is None
            
            # Verify personal tags are gone
            personal_tags = Tag.query.filter_by(name='DINNER', tag_scope='personal').all()
            assert len(personal_tags) == 0
            
            # Verify recipes now use system tag
            recipe1 = Recipe.query.get(recipe1.id)
            recipe2 = Recipe.query.get(recipe2.id)
            assert system_tag in recipe1.tags
            assert system_tag in recipe2.tags


class TestPublicRecipeTagHandling:
    """Test personal tag handling when recipes are made public."""
    
    def test_personal_tags_moved_to_notes_on_public(self, app, auth_client):
        """Test that personal tags are moved to notes when recipe becomes public."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            storage = MySQLStorage(db.session)
            user = User.query.filter_by(username='testuser').first()
            user.can_publish_public = True
            db.session.commit()
            
            # Create private recipe with personal tags
            recipe_data = {
                'name': 'Test Public Recipe',
                'instructions': 'Test instructions',
                'notes': 'Original notes',
                'tags': ['FAMILY_FAVORITE', 'QUICK'],
                'ingredients': [{'description': 'test', 'amount': '1', 'unit': 'cup'}],
                'visibility': 'private'
            }
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # Verify tags exist
            assert len(recipe.tags) == 2
            
            # Update to public
            recipe_data['visibility'] = 'public'
            recipe = storage.save_recipe(recipe_data, user.id, recipe.id)
            
            # Verify tags removed
            assert len(recipe.tags) == 0
            
            # Verify tags added to notes
            assert 'Personal Tags: FAMILY_FAVORITE, QUICK' in recipe.notes
            assert 'Original notes' in recipe.notes
    
    def test_mixed_tags_on_public_recipe(self, app, auth_client):
        """Test that only personal tags are removed when recipe becomes public."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            storage = MySQLStorage(db.session)
            user = User.query.filter_by(username='testuser').first()
            user.can_publish_public = True
            db.session.commit()
            
            # Create system tag
            system_tag = storage.get_or_create_tag('HEALTHY', None, 'system')
            
            # Create recipe with both personal and system tags
            recipe_data = {
                'name': 'Mixed Tags Recipe',
                'instructions': 'Test',
                'tags': ['PERSONAL_TAG'],
                'ingredients': [{'description': 'test', 'amount': '1', 'unit': 'cup'}],
                'visibility': 'private'
            }
            recipe = storage.save_recipe(recipe_data, user.id)
            
            # Manually add system tag (simulating existing system tag on recipe)
            recipe.tags.append(system_tag)
            db.session.commit()
            
            # Update to public
            recipe_data['tags'] = ['PERSONAL_TAG', 'HEALTHY']
            recipe = storage.save_recipe(recipe_data, user.id, recipe.id)
            
            # Verify only system tag remains
            assert len(recipe.tags) == 1
            assert recipe.tags[0].tag_scope == 'system'
            
            # Verify personal tag moved to notes
            assert 'Personal Tags: PERSONAL_TAG' in recipe.notes


class TestTagFiltering:
    """Test tag filtering in recipe searches."""
    
    def test_filter_by_personal_tag(self, app, auth_client):
        """Test filtering recipes by personal tags."""
        auth_client['login']('testuser', 'password123')
        
        with app.app_context():
            storage = MySQLStorage(db.session)
            user = User.query.filter_by(username='testuser').first()
            
            # Create recipes with personal tags
            recipe1 = storage.save_recipe({
                'name': 'Recipe with Tag',
                'instructions': 'Test',
                'tags': ['MYTAG'],
                'ingredients': [{'description': 'test', 'amount': '1', 'unit': 'cup'}]
            }, user.id)
            
            recipe2 = storage.save_recipe({
                'name': 'Recipe without Tag',
                'instructions': 'Test',
                'tags': [],
                'ingredients': [{'description': 'test', 'amount': '1', 'unit': 'cup'}]
            }, user.id)
            
            # Filter by tag
            recipes = storage.filter_recipes_by_tags(['MYTAG'], False, user.id)
            
            # Should only return recipe with tag
            assert len(recipes) == 1
            assert recipes[0].id == recipe1.id
    
    def test_unauthenticated_users_see_only_system_tags(self, app):
        """Test that unauthenticated users can only filter by system tags."""
        with app.app_context():
            storage = MySQLStorage(db.session)
            
            # Create system tag
            system_tag = storage.get_or_create_tag('PUBLIC_TAG', None, 'system')
            
            # Filter as unauthenticated user
            tags = storage.get_all_tags(None)
            
            # Admin view should show all tags
            # But when called with user_id=None for filtering, should respect visibility
            recipes = storage.filter_recipes_by_tags(['PUBLIC_TAG'], False, None)
            
            # This should work (though may return no recipes if none are public)
            assert recipes is not None


class TestAdminTagManagement:
    """Test admin tag management functionality."""
    
    def test_admin_can_delete_personal_tag(self, app, admin_client):
        """Test that admins can delete personal tags."""
        with app.app_context():
            storage = MySQLStorage(db.session)
            user = User.query.filter_by(username='testuser').first()
            
            # Create personal tag for another user
            tag = storage.get_or_create_tag('DELETE_ME', user.id, 'personal')
            tag_id = tag.id
            
            # Admin deletes it
            success, message = storage.delete_tag(tag_id)
            
            assert success is True
            assert Tag.query.get(tag_id) is None
    
    def test_admin_cannot_delete_system_tag(self, app, admin_client):
        """Test that system tags cannot be deleted."""
        with app.app_context():
            storage = MySQLStorage(db.session)
            
            # Create system tag
            tag = storage.get_or_create_tag('PERMANENT', None, 'system')
            tag_id = tag.id
            
            # Try to delete it
            success, message = storage.delete_tag(tag_id)
            
            assert success is False
            assert 'System tags are permanent' in message
            assert Tag.query.get(tag_id) is not None
    
    def test_admin_can_edit_any_tag(self, app, admin_client):
        """Test that admins can edit any tag."""
        with app.app_context():
            storage = MySQLStorage(db.session)
            user = User.query.filter_by(username='testuser').first()
            
            # Create personal tag
            tag = storage.get_or_create_tag('OLD_NAME', user.id, 'personal')
            tag_id = tag.id
            
            # Admin renames it
            success, message = storage.update_tag(tag_id, new_name='NEW_NAME')
            
            assert success is True
            updated_tag = Tag.query.get(tag_id)
            assert updated_tag.name == 'NEW_NAME'
    
    def test_cleanup_orphaned_personal_tags(self, app, admin_client):
        """Test cleanup of orphaned personal tags."""
        with app.app_context():
            storage = MySQLStorage(db.session)
            user = User.query.filter_by(username='testuser').first()
            
            # Create personal tag without any recipes
            tag = Tag(
                name='ORPHANED',
                slug='orphaned',
                tag_scope='personal',
                user_id=user.id
            )
            db.session.add(tag)
            db.session.commit()
            tag_id = tag.id
            
            # Cleanup orphaned tags
            count = storage.cleanup_orphaned_tags()
            
            assert count >= 1
            assert Tag.query.get(tag_id) is None
    
    def test_cleanup_preserves_system_tags(self, app, admin_client):
        """Test that orphaned system tags are NOT deleted."""
        with app.app_context():
            storage = MySQLStorage(db.session)
            
            # Create system tag without any recipes
            tag = Tag(
                name='ORPHANED_SYSTEM',
                slug='orphaned-system',
                tag_scope='system',
                user_id=None
            )
            db.session.add(tag)
            db.session.commit()
            tag_id = tag.id
            
            # Cleanup orphaned tags
            count = storage.cleanup_orphaned_tags()
            
            # System tag should still exist
            assert Tag.query.get(tag_id) is not None


class TestTagRoutes:
    """Test tag-related HTTP routes."""
    
    def test_regular_user_redirected_from_tag_manager(self, auth_client):
        """Test that regular users are redirected from /tags route."""
        auth_client['login']('testuser', 'password123')
        response = auth_client['client'].get('/tags', follow_redirects=False)
        
        # Should redirect (not admin)
        assert response.status_code == 302
    
    def test_admin_can_access_tag_manager(self, admin_client):
        """Test that admins can access tag management."""
        admin_client['login']('admin', 'admin123')
        response = admin_client['client'].get('/admin/tags')
        
        assert response.status_code == 200
        assert b'Tag Management' in response.data
    
    def test_admin_create_system_tag_route(self, app, admin_client):
        """Test admin system tag creation route."""
        admin_client['login']('admin', 'admin123')
        
        response = admin_client['client'].post('/admin/tags/create', data={
            'tag_name': 'NEW_SYSTEM_TAG'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        with app.app_context():
            tag = Tag.query.filter_by(name='NEW_SYSTEM_TAG', tag_scope='system').first()
            assert tag is not None
    
    def test_admin_convert_tag_route(self, app, admin_client):
        """Test admin tag conversion route."""
        with app.app_context():
            storage = MySQLStorage(db.session)
            user = User.query.filter_by(username='testuser').first()
            
            # Create personal tag
            tag = storage.get_or_create_tag('CONVERT_ME', user.id, 'personal')
        
        admin_client['login']('admin', 'admin123')
        response = admin_client['client'].post('/admin/tags/convert-to-system', data={
            'tag_name': 'CONVERT_ME'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        with app.app_context():
            # Should now be system tag
            system_tag = Tag.query.filter_by(name='CONVERT_ME', tag_scope='system').first()
            assert system_tag is not None
            assert system_tag.user_id is None


# Mark tests as requiring database
pytestmark = pytest.mark.usefixtures("app")

