"""
Integration tests for the friend feature using the Flask test client.

Tests the full flow including routes, database operations, and edge cases.
"""

import pytest
from db_models import db, User, Recipe, FriendRequest, Friendship, RecipeShare, Notification
from mysql_storage import MySQLStorage
import bcrypt


class TestFriendFeatureIntegration:
    """Integration tests for friend feature."""
    
    def test_find_friend_flow(self, app, client, auth_client):
        """Test the complete friend finding and requesting flow."""
        with app.app_context():
            # Create a second user
            user2 = User(
                username='frienduser',
                email='friend@test.com',
                password_hash=bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                display_name='Friend User',
                is_active=True
            )
            db.session.add(user2)
            db.session.commit()
            
            # Login as testuser
            auth_client['login']('testuser', 'password123')
            
            # Send friend request
            response = client.post('/friends/find', data={
                'email': 'friend@test.com'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            assert b'If a user with that email exists' in response.data
            
            # Check that request was created
            request = db.session.query(FriendRequest).filter(
                FriendRequest.recipient_id == user2.id
            ).first()
            assert request is not None
            assert request.status == 'pending'
            
            # Check notification was created
            notification = db.session.query(Notification).filter(
                Notification.user_id == user2.id,
                Notification.notification_type == 'friend_request'
            ).first()
            assert notification is not None
            
            # Cleanup
            db.session.delete(notification)
            db.session.delete(request)
            db.session.delete(user2)
            db.session.commit()
    
    def test_accept_friend_request_flow(self, app, client):
        """Test accepting a friend request."""
        with app.app_context():
            # Create two users
            user1 = User(
                username='user1',
                email='user1@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True
            )
            user2 = User(
                username='user2',
                email='user2@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True
            )
            db.session.add_all([user1, user2])
            db.session.commit()
            
            # Create friend request
            request = FriendRequest(
                sender_id=user1.id,
                recipient_id=user2.id,
                status='pending'
            )
            db.session.add(request)
            db.session.commit()
            
            # Login as user2
            client.post('/auth/login', data={
                'username': 'user2',
                'password': 'pass123'
            }, follow_redirects=True)
            
            # Accept request
            response = client.post(f'/friends/requests/{request.id}/accept', follow_redirects=True)
            assert response.status_code == 200
            
            # Check friendship was created
            friendship = db.session.query(Friendship).filter(
                ((Friendship.user1_id == user1.id) & (Friendship.user2_id == user2.id)) |
                ((Friendship.user1_id == user2.id) & (Friendship.user2_id == user1.id))
            ).first()
            assert friendship is not None
            
            # Check request status updated
            db.session.refresh(request)
            assert request.status == 'accepted'
            
            # Cleanup
            db.session.delete(friendship)
            db.session.delete(request)
            db.session.delete(user1)
            db.session.delete(user2)
            db.session.commit()
    
    def test_share_recipe_with_friend(self, app, client, auth_client, test_recipes):
        """Test sharing a recipe with a friend."""
        with app.app_context():
            # Get test user and create friend
            test_user = db.session.query(User).filter(User.username == 'testuser').first()
            friend = User(
                username='friend',
                email='friend@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True
            )
            db.session.add(friend)
            db.session.commit()
            
            # Create friendship
            user1_id = min(test_user.id, friend.id)
            user2_id = max(test_user.id, friend.id)
            friendship = Friendship(user1_id=user1_id, user2_id=user2_id)
            db.session.add(friendship)
            db.session.commit()
            
            # Get public recipe
            public_recipe = db.session.query(Recipe).filter(
                Recipe.visibility == 'public'
            ).first()
            
            if public_recipe:
                # Login as test user
                auth_client['login']('testuser', 'password123')
                
                # Share recipe
                response = client.post(f'/recipe/{public_recipe.id}/share', data={
                    'friend_ids': [str(friend.id)]
                }, follow_redirects=True)
                
                assert response.status_code == 200
                
                # Check share was created
                share = db.session.query(RecipeShare).filter(
                    RecipeShare.recipe_id == public_recipe.id,
                    RecipeShare.shared_with_user_id == friend.id
                ).first()
                assert share is not None
                
                # Check notification
                notification = db.session.query(Notification).filter(
                    Notification.user_id == friend.id,
                    Notification.notification_type == 'recipe_shared'
                ).first()
                assert notification is not None
                
                # Cleanup
                db.session.delete(notification)
                db.session.delete(share)
            
            db.session.delete(friendship)
            db.session.delete(friend)
            db.session.commit()
    
    def test_shared_recipe_visibility(self, app, client, auth_client, test_recipes):
        """Test that shared recipes are visible to recipients."""
        with app.app_context():
            test_user = db.session.query(User).filter(User.username == 'testuser').first()
            friend = User(
                username='friend2',
                email='friend2@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True
            )
            db.session.add(friend)
            db.session.commit()
            
            # Create friendship
            user1_id = min(test_user.id, friend.id)
            user2_id = max(test_user.id, friend.id)
            friendship = Friendship(user1_id=user1_id, user2_id=user2_id)
            db.session.add(friendship)
            db.session.commit()
            
            # Get public recipe and share it
            public_recipe = db.session.query(Recipe).filter(
                Recipe.visibility == 'public'
            ).first()
            
            if public_recipe:
                share = RecipeShare(
                    recipe_id=public_recipe.id,
                    shared_by_user_id=test_user.id,
                    shared_with_user_id=friend.id
                )
                db.session.add(share)
                db.session.commit()
                
                # Login as friend
                client.post('/auth/login', data={
                    'username': 'friend2',
                    'password': 'pass123'
                }, follow_redirects=True)
                
                # Check recipe is visible
                response = client.get(f'/recipe/{public_recipe.id}')
                assert response.status_code == 200
                assert bytes(public_recipe.name, 'utf-8') in response.data
                
                # Check it appears in recipe list
                response = client.get('/recipes')
                assert response.status_code == 200
                assert bytes(public_recipe.name, 'utf-8') in response.data
                
                # Cleanup
                db.session.delete(share)
            
            db.session.delete(friendship)
            db.session.delete(friend)
            db.session.commit()
    
    def test_soft_delete_with_shares(self, app, client, auth_client, test_recipes, storage):
        """Test that recipes with shares are soft deleted."""
        with app.app_context():
            test_user = db.session.query(User).filter(User.username == 'testuser').first()
            friend = User(
                username='friend3',
                email='friend3@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True
            )
            db.session.add(friend)
            db.session.commit()
            
            # Create friendship
            user1_id = min(test_user.id, friend.id)
            user2_id = max(test_user.id, friend.id)
            friendship = Friendship(user1_id=user1_id, user2_id=user2_id)
            db.session.add(friendship)
            db.session.commit()
            
            # Get public recipe and share it
            public_recipe = db.session.query(Recipe).filter(
                Recipe.visibility == 'public'
            ).first()
            
            if public_recipe:
                share = RecipeShare(
                    recipe_id=public_recipe.id,
                    shared_by_user_id=test_user.id,
                    shared_with_user_id=friend.id
                )
                db.session.add(share)
                db.session.commit()
                
                # Login as owner and delete recipe
                auth_client['login']('testuser', 'password123')
                response = client.post(f'/recipe/{public_recipe.id}/delete', follow_redirects=True)
                assert response.status_code == 200
                
                # Check recipe is soft deleted
                db.session.refresh(public_recipe)
                assert public_recipe.deleted_at is not None
                
                # Recipe should still be visible to friend
                client.post('/auth/logout')
                client.post('/auth/login', data={
                    'username': 'friend3',
                    'password': 'pass123'
                }, follow_redirects=True)
                
                response = client.get(f'/recipe/{public_recipe.id}')
                assert response.status_code == 200
                
                # Cleanup
                db.session.delete(share)
            
            db.session.delete(friendship)
            db.session.delete(friend)
            db.session.commit()
    
    def test_cannot_change_visibility_when_shared(self, app, client, auth_client, test_recipes):
        """Test that visibility cannot be changed when recipe has shares."""
        with app.app_context():
            test_user = db.session.query(User).filter(User.username == 'testuser').first()
            friend = User(
                username='friend4',
                email='friend4@test.com',
                password_hash=bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                is_active=True
            )
            db.session.add(friend)
            db.session.commit()
            
            # Create friendship
            user1_id = min(test_user.id, friend.id)
            user2_id = max(test_user.id, friend.id)
            friendship = Friendship(user1_id=user1_id, user2_id=user2_id)
            db.session.add(friendship)
            db.session.commit()
            
            # Get public recipe and share it
            public_recipe = db.session.query(Recipe).filter(
                Recipe.visibility == 'public'
            ).first()
            
            if public_recipe:
                share = RecipeShare(
                    recipe_id=public_recipe.id,
                    shared_by_user_id=test_user.id,
                    shared_with_user_id=friend.id
                )
                db.session.add(share)
                db.session.commit()
                
                # Login as owner and try to change visibility
                auth_client['login']('testuser', 'password123')
                
                # Try to edit recipe and change visibility to private
                response = client.post(f'/recipe/{public_recipe.id}/edit', data={
                    'name': public_recipe.name,
                    'instructions': public_recipe.instructions,
                    'visibility': 'private',
                    'ingredient_description_0': 'test',
                    'ingredient_amount_0': '1',
                    'ingredient_unit_0': 'cup'
                }, follow_redirects=True)
                
                # Should show error
                assert b'Cannot change visibility' in response.data or response.status_code == 400
                
                # Recipe should still be public
                db.session.refresh(public_recipe)
                assert public_recipe.visibility == 'public'
                
                # Cleanup
                db.session.delete(share)
            
            db.session.delete(friendship)
            db.session.delete(friend)
            db.session.commit()



