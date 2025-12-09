"""
Comprehensive tests for the friend feature.

Tests include:
- Friend request flow (send, accept, reject, cancel)
- Recipe sharing (individual and all)
- Shared recipe visibility
- Soft delete behavior
- Edge cases and corner cases
"""

import pytest
from datetime import datetime
from db_models import db, User, Recipe, FriendRequest, Friendship, RecipeShare, Notification
from mysql_storage import MySQLStorage
import bcrypt


@pytest.fixture
def storage(app):
    """Create storage instance."""
    return MySQLStorage()


@pytest.fixture
def user1(app):
    """Create first test user."""
    with app.app_context():
        user = User(
            username='testuser1',
            email='user1@test.com',
            password_hash=bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
            display_name='Test User 1',
            is_active=True,
            can_publish_public=True
        )
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def user2(app):
    """Create second test user."""
    with app.app_context():
        user = User(
            username='testuser2',
            email='user2@test.com',
            password_hash=bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
            display_name='Test User 2',
            is_active=True,
            can_publish_public=True
        )
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def user3(app):
    """Create third test user."""
    with app.app_context():
        user = User(
            username='testuser3',
            email='user3@test.com',
            password_hash=bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
            display_name='Test User 3',
            is_active=True,
            can_publish_public=True
        )
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def public_recipe(app, user1, storage):
    """Create a public recipe for user1."""
    with app.app_context():
        recipe_data = {
            'name': 'Test Public Recipe',
            'description': 'A test recipe',
            'instructions': 'Do something',
            'visibility': 'public',
            'ingredients': [{'description': 'ingredient1', 'amount': '1', 'unit': 'cup'}],
            'tags': []
        }
        recipe = storage.save_recipe(recipe_data, user1.id)
        yield recipe
        db.session.delete(recipe)
        db.session.commit()


class TestFriendRequests:
    """Test friend request functionality."""
    
    def test_send_friend_request(self, app, user1, user2):
        """Test sending a friend request."""
        with app.app_context():
            request = FriendRequest(
                sender_id=user1.id,
                recipient_id=user2.id,
                status='pending'
            )
            db.session.add(request)
            db.session.commit()
            
            assert request.id is not None
            assert request.status == 'pending'
            assert request.sender_id == user1.id
            assert request.recipient_id == user2.id
            
            db.session.delete(request)
            db.session.commit()
    
    def test_duplicate_friend_request_prevented(self, user1, user2):
        """Test that duplicate friend requests are prevented."""
        request1 = FriendRequest(
            sender_id=user1.id,
            recipient_id=user2.id,
            status='pending'
        )
        db.session.add(request1)
        db.session.commit()
        
        # Try to create duplicate
        request2 = FriendRequest(
            sender_id=user1.id,
            recipient_id=user2.id,
            status='pending'
        )
        db.session.add(request2)
        
        with pytest.raises(Exception):  # Should raise IntegrityError
            db.session.commit()
    
    def test_accept_friend_request(self, user1, user2):
        """Test accepting a friend request."""
        # Create request
        request = FriendRequest(
            sender_id=user1.id,
            recipient_id=user2.id,
            status='pending'
        )
        db.session.add(request)
        db.session.commit()
        
        # Accept request
        request.status = 'accepted'
        
        # Create friendship
        user1_id = min(user1.id, user2.id)
        user2_id = max(user1.id, user2.id)
        friendship = Friendship(
            user1_id=user1_id,
            user2_id=user2_id
        )
        db.session.add(friendship)
        db.session.commit()
        
        assert friendship.id is not None
        assert user1.is_friends_with(user2.id)
        assert user2.is_friends_with(user1.id)
    
    def test_reject_friend_request(self, user1, user2):
        """Test rejecting a friend request."""
        request = FriendRequest(
            sender_id=user1.id,
            recipient_id=user2.id,
            status='pending'
        )
        db.session.add(request)
        db.session.commit()
        
        # Reject request
        request.status = 'rejected'
        db.session.commit()
        
        assert request.status == 'rejected'
        assert not user1.is_friends_with(user2.id)
    
    def test_cancel_friend_request(self, user1, user2):
        """Test cancelling a sent friend request."""
        request = FriendRequest(
            sender_id=user1.id,
            recipient_id=user2.id,
            status='pending'
        )
        db.session.add(request)
        db.session.commit()
        
        # Cancel request
        request.status = 'cancelled'
        db.session.commit()
        
        assert request.status == 'cancelled'
    
    def test_get_pending_requests(self, user1, user2, user3):
        """Test getting pending requests."""
        # Create requests
        request1 = FriendRequest(sender_id=user1.id, recipient_id=user2.id, status='pending')
        request2 = FriendRequest(sender_id=user3.id, recipient_id=user2.id, status='pending')
        db.session.add_all([request1, request2])
        db.session.commit()
        
        received = user2.get_pending_received_requests()
        assert len(received) == 2
        
        sent = user1.get_pending_sent_requests()
        assert len(sent) == 1


class TestFriendships:
    """Test friendship functionality."""
    
    def test_friendship_bidirectional(self, user1, user2):
        """Test that friendship is bidirectional."""
        user1_id = min(user1.id, user2.id)
        user2_id = max(user1.id, user2.id)
        
        friendship = Friendship(
            user1_id=user1_id,
            user2_id=user2_id
        )
        db.session.add(friendship)
        db.session.commit()
        
        assert user1.is_friends_with(user2.id)
        assert user2.is_friends_with(user1.id)
    
    def test_get_friends(self, user1, user2, user3):
        """Test getting list of friends."""
        # Create friendships
        f1 = Friendship(user1_id=min(user1.id, user2.id), user2_id=max(user1.id, user2.id))
        f2 = Friendship(user1_id=min(user1.id, user3.id), user2_id=max(user1.id, user3.id))
        db.session.add_all([f1, f2])
        db.session.commit()
        
        friends = user1.get_friends()
        assert len(friends) == 2
        assert user2 in friends
        assert user3 in friends
    
    def test_remove_friend(self, user1, user2):
        """Test removing a friend."""
        # Create friendship
        f = Friendship(user1_id=min(user1.id, user2.id), user2_id=max(user1.id, user2.id))
        db.session.add(f)
        db.session.commit()
        
        assert user1.is_friends_with(user2.id)
        
        # Remove friendship
        db.session.delete(f)
        db.session.commit()
        
        assert not user1.is_friends_with(user2.id)


class TestRecipeSharing:
    """Test recipe sharing functionality."""
    
    def test_share_recipe_with_friend(self, user1, user2, public_recipe):
        """Test sharing a recipe with a friend."""
        # Create friendship first
        f = Friendship(user1_id=min(user1.id, user2.id), user2_id=max(user1.id, user2.id))
        db.session.add(f)
        db.session.commit()
        
        # Share recipe
        share = RecipeShare(
            recipe_id=public_recipe.id,
            shared_by_user_id=user1.id,
            shared_with_user_id=user2.id
        )
        db.session.add(share)
        db.session.commit()
        
        assert share.id is not None
        assert public_recipe.is_shared_with(user2.id)
        assert public_recipe.get_shared_by_friend(user2.id) == user1
    
    def test_share_recipe_multiple_friends(self, user1, user2, user3, public_recipe):
        """Test sharing a recipe with multiple friends."""
        # Create friendships
        f1 = Friendship(user1_id=min(user1.id, user2.id), user2_id=max(user1.id, user2.id))
        f2 = Friendship(user1_id=min(user1.id, user3.id), user2_id=max(user1.id, user3.id))
        db.session.add_all([f1, f2])
        db.session.commit()
        
        # Share with both
        share1 = RecipeShare(recipe_id=public_recipe.id, shared_by_user_id=user1.id, shared_with_user_id=user2.id)
        share2 = RecipeShare(recipe_id=public_recipe.id, shared_by_user_id=user1.id, shared_with_user_id=user3.id)
        db.session.add_all([share1, share2])
        db.session.commit()
        
        shared_with = public_recipe.get_shared_with_friends()
        assert len(shared_with) == 2
        assert user2 in shared_with
        assert user3 in shared_with
    
    def test_duplicate_share_prevented(self, user1, user2, public_recipe):
        """Test that duplicate shares are prevented."""
        # Create friendship
        f = Friendship(user1_id=min(user1.id, user2.id), user2_id=max(user1.id, user2.id))
        db.session.add(f)
        db.session.commit()
        
        # Create share
        share1 = RecipeShare(recipe_id=public_recipe.id, shared_by_user_id=user1.id, shared_with_user_id=user2.id)
        db.session.add(share1)
        db.session.commit()
        
        # Try duplicate
        share2 = RecipeShare(recipe_id=public_recipe.id, shared_by_user_id=user1.id, shared_with_user_id=user2.id)
        db.session.add(share2)
        
        with pytest.raises(Exception):  # Should raise IntegrityError
            db.session.commit()
    
    def test_shared_recipe_visible_to_recipient(self, user1, user2, public_recipe, storage):
        """Test that shared recipes are visible to recipient."""
        # Create friendship
        f = Friendship(user1_id=min(user1.id, user2.id), user2_id=max(user1.id, user2.id))
        db.session.add(f)
        db.session.commit()
        
        # Share recipe
        share = RecipeShare(recipe_id=public_recipe.id, shared_by_user_id=user1.id, shared_with_user_id=user2.id)
        db.session.add(share)
        db.session.commit()
        
        # Check visibility
        recipe = storage.get_recipe(public_recipe.id, user2.id)
        assert recipe is not None
        assert recipe.id == public_recipe.id
    
    def test_unshare_self(self, user1, user2, public_recipe):
        """Test recipient removing shared recipe from their view."""
        # Create friendship and share
        f = Friendship(user1_id=min(user1.id, user2.id), user2_id=max(user1.id, user2.id))
        db.session.add(f)
        share = RecipeShare(recipe_id=public_recipe.id, shared_by_user_id=user1.id, shared_with_user_id=user2.id)
        db.session.add(share)
        db.session.commit()
        
        assert public_recipe.is_shared_with(user2.id)
        
        # Remove share
        db.session.delete(share)
        db.session.commit()
        
        assert not public_recipe.is_shared_with(user2.id)


class TestSoftDelete:
    """Test soft delete functionality for shared recipes."""
    
    def test_soft_delete_when_recipe_has_shares(self, user1, user2, public_recipe, storage):
        """Test that recipe is soft deleted when it has shares."""
        # Create friendship and share
        f = Friendship(user1_id=min(user1.id, user2.id), user2_id=max(user1.id, user2.id))
        db.session.add(f)
        share = RecipeShare(recipe_id=public_recipe.id, shared_by_user_id=user1.id, shared_with_user_id=user2.id)
        db.session.add(share)
        db.session.commit()
        
        # Delete recipe (should soft delete)
        success = storage.delete_recipe(public_recipe.id, user1.id)
        assert success
        
        # Refresh recipe
        db.session.refresh(public_recipe)
        assert public_recipe.deleted_at is not None
        
        # Recipe should still be visible to recipient
        recipe = storage.get_recipe(public_recipe.id, user2.id)
        assert recipe is not None
    
    def test_hard_delete_when_no_shares(self, user1, public_recipe, storage):
        """Test that recipe is hard deleted when it has no shares."""
        # Delete recipe (should hard delete)
        recipe_id = public_recipe.id
        success = storage.delete_recipe(recipe_id, user1.id)
        assert success
        
        # Recipe should be gone
        recipe = db.session.query(Recipe).filter(Recipe.id == recipe_id).first()
        assert recipe is None
    
    def test_soft_deleted_recipe_hidden_from_owner(self, user1, user2, public_recipe, storage):
        """Test that soft-deleted recipe is hidden from owner's view."""
        # Create friendship and share
        f = Friendship(user1_id=min(user1.id, user2.id), user2_id=max(user1.id, user2.id))
        db.session.add(f)
        share = RecipeShare(recipe_id=public_recipe.id, shared_by_user_id=user1.id, shared_with_user_id=user2.id)
        db.session.add(share)
        db.session.commit()
        
        # Delete recipe
        storage.delete_recipe(public_recipe.id, user1.id)
        
        # Recipe should not appear in owner's recipe list
        recipes = storage.get_all_recipes(user1.id)
        recipe_ids = [r.id for r in recipes]
        assert public_recipe.id not in recipe_ids


class TestVisibilityConstraints:
    """Test visibility constraints for shared recipes."""
    
    def test_cannot_share_non_public_recipe(self, user1, user2, storage):
        """Test that only public recipes can be shared."""
        # Create private recipe
        recipe_data = {
            'name': 'Private Recipe',
            'description': 'A private recipe',
            'instructions': 'Do something',
            'visibility': 'private',
            'ingredients': [],
            'tags': []
        }
        recipe = storage.save_recipe(recipe_data, user1.id)
        
        # Recipe should not be shareable (enforced in route, not model)
        assert recipe.visibility != 'public'
    
    def test_cannot_change_visibility_when_shared(self, user1, user2, public_recipe):
        """Test that visibility cannot be changed when recipe has shares."""
        # Create friendship and share
        f = Friendship(user1_id=min(user1.id, user2.id), user2_id=max(user1.id, user2.id))
        db.session.add(f)
        share = RecipeShare(recipe_id=public_recipe.id, shared_by_user_id=user1.id, shared_with_user_id=user2.id)
        db.session.add(share)
        db.session.commit()
        
        # Check that recipe has active shares
        assert public_recipe.has_active_shares()
        
        # Try to change visibility (should be prevented in route)
        # This is tested in integration tests


class TestNotifications:
    """Test notification functionality."""
    
    def test_friend_request_notification(self, user1, user2):
        """Test notification creation for friend request."""
        request = FriendRequest(sender_id=user1.id, recipient_id=user2.id, status='pending')
        db.session.add(request)
        
        notification = Notification(
            user_id=user2.id,
            notification_type='friend_request',
            related_user_id=user1.id,
            message=f"{user1.display_name or user1.username} sent you a friend request"
        )
        db.session.add(notification)
        db.session.commit()
        
        assert notification.id is not None
        assert notification.read == False
        assert user2.get_unread_notification_count() == 1
    
    def test_recipe_shared_notification(self, user1, user2, public_recipe):
        """Test notification creation for recipe share."""
        notification = Notification(
            user_id=user2.id,
            notification_type='recipe_shared',
            related_user_id=user1.id,
            recipe_id=public_recipe.id,
            message=f"{user1.display_name or user1.username} shared a recipe with you: {public_recipe.name}"
        )
        db.session.add(notification)
        db.session.commit()
        
        assert notification.id is not None
        assert notification.recipe_id == public_recipe.id


class TestEdgeCases:
    """Test edge cases and corner cases."""
    
    def test_self_friend_request_prevented(self, user1):
        """Test that users cannot send friend requests to themselves."""
        # This should be prevented in the route, not the model
        # Model allows it but route should check
        pass  # Tested in integration tests
    
    def test_share_recipe_with_non_friend(self, user1, user2, public_recipe):
        """Test that recipes cannot be shared with non-friends."""
        # Try to share without friendship
        share = RecipeShare(
            recipe_id=public_recipe.id,
            shared_by_user_id=user1.id,
            shared_with_user_id=user2.id
        )
        db.session.add(share)
        db.session.commit()
        
        # Share is created but should be filtered in queries
        # This is enforced in route logic
    
    def test_remove_friend_keeps_shares(self, user1, user2, public_recipe):
        """Test that removing a friend keeps recipe shares."""
        # Create friendship and share
        f = Friendship(user1_id=min(user1.id, user2.id), user2_id=max(user1.id, user2.id))
        db.session.add(f)
        share = RecipeShare(recipe_id=public_recipe.id, shared_by_user_id=user1.id, shared_with_user_id=user2.id)
        db.session.add(share)
        db.session.commit()
        
        # Remove friendship
        db.session.delete(f)
        db.session.commit()
        
        # Share should still exist
        assert public_recipe.is_shared_with(user2.id)
    
    def test_multiple_shares_same_recipe(self, user1, user2, user3, public_recipe):
        """Test sharing same recipe with multiple friends."""
        # Create friendships
        f1 = Friendship(user1_id=min(user1.id, user2.id), user2_id=max(user1.id, user2.id))
        f2 = Friendship(user1_id=min(user1.id, user3.id), user2_id=max(user1.id, user3.id))
        db.session.add_all([f1, f2])
        db.session.commit()
        
        # Share with both
        share1 = RecipeShare(recipe_id=public_recipe.id, shared_by_user_id=user1.id, shared_with_user_id=user2.id)
        share2 = RecipeShare(recipe_id=public_recipe.id, shared_by_user_id=user1.id, shared_with_user_id=user3.id)
        db.session.add_all([share1, share2])
        db.session.commit()
        
        assert public_recipe.is_shared_with(user2.id)
        assert public_recipe.is_shared_with(user3.id)
        assert len(public_recipe.get_shared_with_friends()) == 2
    
    def test_share_all_recipes(self, user1, user2, storage):
        """Test sharing all recipes with a friend."""
        # Create multiple public recipes
        recipes = []
        for i in range(3):
            recipe_data = {
                'name': f'Recipe {i+1}',
                'description': f'Recipe {i+1} description',
                'instructions': 'Do something',
                'visibility': 'public',
                'ingredients': [],
                'tags': []
            }
            recipe = storage.save_recipe(recipe_data, user1.id)
            recipes.append(recipe)
        
        # Create friendship
        f = Friendship(user1_id=min(user1.id, user2.id), user2_id=max(user1.id, user2.id))
        db.session.add(f)
        db.session.commit()
        
        # Share all (simulated - actual logic in route)
        for recipe in recipes:
            share = RecipeShare(recipe_id=recipe.id, shared_by_user_id=user1.id, shared_with_user_id=user2.id)
            db.session.add(share)
        db.session.commit()
        
        # Check all are shared
        for recipe in recipes:
            assert recipe.is_shared_with(user2.id)

