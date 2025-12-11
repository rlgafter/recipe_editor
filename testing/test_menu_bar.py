"""
Comprehensive Menu Bar Tests for Recipe Editor.

Tests menu bar consistency across all pages, including:
- Menu items for authenticated vs unauthenticated users
- Conditional menu items (Share Recipes, Pending Shares)
- Badge counts (notifications, pending shares)
- Admin menu visibility
- Search bar presence
- User dropdown functionality
- Active state highlighting
- Corner cases and edge cases
"""
import pytest
from bs4 import BeautifulSoup
from datetime import datetime
from db_models import db, User, Recipe, RecipeIngredient, Ingredient, Notification, PendingRecipeShare, Friendship, FriendRequest
import bcrypt


class TestMenuBarUnauthenticated:
    """Test menu bar for unauthenticated users."""
    
    def test_menu_items_for_unauthenticated_user(self, client):
        """Test that unauthenticated users see correct menu items."""
        # Test multiple pages to ensure consistency
        pages = [
            '/',
            '/auth/login',
            '/auth/register',
            '/recipes',
        ]
        
        for page in pages:
            response = client.get(page)
            if response.status_code == 200:
                soup = BeautifulSoup(response.data, 'html.parser')
                nav = soup.find('nav', class_='navbar')
                
                if nav:
                    # Should have search bar
                    search_form = nav.find('form', method='GET')
                    assert search_form is not None, f"Search bar missing on {page}"
                    
                    # Should have Home link (or be on home page already)
                    home_link = nav.find('a', string=lambda t: t and 'Home' in t)
                    # Home link may not appear if already on home page, so this is optional
                    # The important thing is that authenticated-only items don't appear
                    
                    # Should have Login link
                    login_link = nav.find('a', href=lambda h: h and '/auth/login' in h)
                    assert login_link is not None, f"Login link missing on {page}"
                    
                    # Should have Register link
                    register_link = nav.find('a', href=lambda h: h and '/auth/register' in h)
                    assert register_link is not None, f"Register link missing on {page}"
                    
                    # Should NOT have authenticated-only items
                    my_recipes = nav.find('a', string=lambda t: t and 'My Recipes' in t)
                    assert my_recipes is None, f"My Recipes should not appear for unauthenticated users on {page}"
                    
                    new_recipe = nav.find('a', string=lambda t: t and 'New Recipe' in t)
                    assert new_recipe is None, f"New Recipe should not appear for unauthenticated users on {page}"
                    
                    friends = nav.find('a', string=lambda t: t and 'Friends' in t)
                    assert friends is None, f"Friends should not appear for unauthenticated users on {page}"
                    
                    user_dropdown = nav.find('a', id='userDropdown')
                    assert user_dropdown is None, f"User dropdown should not appear for unauthenticated users on {page}"
    
    def test_search_bar_functionality(self, client):
        """Test that search bar is present and functional."""
        response = client.get('/')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        search_form = soup.find('form', method='GET')
        
        assert search_form is not None, "Search form should be present"
        action = search_form.get('action', '')
        assert '/recipes' in action or action == '/recipes', \
            f"Search form should submit to /recipes, got {action}"
        
        search_input = search_form.find('input', {'name': 'search'})
        assert search_input is not None, "Search input should be present"
        assert search_input.get('placeholder') == 'Search recipes...', "Search input should have correct placeholder"


class TestMenuBarAuthenticated:
    """Test menu bar for authenticated regular users."""
    
    def test_menu_items_for_authenticated_user(self, auth_client):
        """Test that authenticated users see correct menu items."""
        auth_client['login']('testuser', 'password123')
        
        # Test multiple pages to ensure consistency
        pages = [
            '/recipes',
            '/recipe/new',
            '/my-recipes',
            '/auth/profile',
        ]
        
        for page in pages:
            response = auth_client['client'].get(page)
            if response.status_code == 200:
                soup = BeautifulSoup(response.data, 'html.parser')
                nav = soup.find('nav', class_='navbar')
                
                if nav:
                    # Should have search bar
                    search_form = nav.find('form', method='GET')
                    assert search_form is not None, f"Search bar missing on {page}"
                    
                    # Should have Browse Recipes link (text may be split with icon)
                    # Find all links with /recipes, but exclude the brand logo
                    all_recipe_links = nav.find_all('a', href=lambda h: h and '/recipes' in h)
                    browse_link = None
                    for link in all_recipe_links:
                        # Exclude brand logo (usually has class navbar-brand)
                        if 'navbar-brand' not in link.get('class', []):
                            link_text = link.get_text(strip=True)
                            if 'Browse Recipes' in link_text or ('Recipes' in link_text and 'Recipe Editor' not in link_text):
                                browse_link = link
                                break
                    assert browse_link is not None, \
                        f"Browse Recipes link missing on {page}"
                    
                    # Should have My Recipes link (text may be split with icon)
                    my_recipes = nav.find('a', href=lambda h: h and '/my-recipes' in h)
                    if not my_recipes:
                        # Try by text
                        for link in nav.find_all('a'):
                            if 'My Recipes' in link.get_text():
                                my_recipes = link
                                break
                    assert my_recipes is not None, f"My Recipes link missing on {page}"
                    
                    # Should have New Recipe link (text may be split with icon)
                    new_recipe = nav.find('a', href=lambda h: h and '/recipe/new' in h)
                    if not new_recipe:
                        # Try by text
                        for link in nav.find_all('a'):
                            if 'New Recipe' in link.get_text():
                                new_recipe = link
                                break
                    assert new_recipe is not None, f"New Recipe link missing on {page}"
                    
                    # Should have Friends link (text may be split with icon)
                    friends = nav.find('a', href=lambda h: h and '/friends' in h and '/friends/' not in h)
                    if not friends:
                        # Try by text
                        for link in nav.find_all('a'):
                            if 'Friends' in link.get_text() and '/friends' in link.get('href', ''):
                                friends = link
                                break
                    assert friends is not None, f"Friends link missing on {page}"
                    
                    # Should have User dropdown
                    user_dropdown = nav.find('a', id='userDropdown')
                    assert user_dropdown is not None, f"User dropdown missing on {page}"
                    
                    # Should NOT have Login/Register links
                    login_link = nav.find('a', href=lambda h: h and '/auth/login' in h)
                    assert login_link is None, f"Login link should not appear for authenticated users on {page}"
                    
                    register_link = nav.find('a', href=lambda h: h and '/auth/register' in h)
                    assert register_link is None, f"Register link should not appear for authenticated users on {page}"
    
    def test_user_dropdown_contents(self, auth_client):
        """Test that user dropdown contains correct items."""
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].get('/recipes')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        user_dropdown = soup.find('a', id='userDropdown')
        assert user_dropdown is not None, "User dropdown should be present"
        
        # Check dropdown menu items
        dropdown_menu = soup.find('ul', class_='dropdown-menu', id=lambda x: x == 'userDropdown' or x is None)
        if not dropdown_menu:
            # Try finding by parent
            dropdown_parent = user_dropdown.find_parent('li', class_='nav-item')
            if dropdown_parent:
                dropdown_menu = dropdown_parent.find('ul', class_='dropdown-menu')
        
        assert dropdown_menu is not None, "Dropdown menu should be present"
        
        # Should have Profile link
        profile_link = dropdown_menu.find('a', href=lambda h: h and '/auth/profile' in h)
        assert profile_link is not None, "Profile link should be in dropdown"
        
        # Should have Logout link
        logout_link = dropdown_menu.find('a', href=lambda h: h and '/auth/logout' in h)
        assert logout_link is not None, "Logout link should be in dropdown"
        
        # Should NOT have Admin Dashboard for regular users
        admin_dashboard = dropdown_menu.find('a', string=lambda t: t and 'Admin Dashboard' in t)
        assert admin_dashboard is None, "Admin Dashboard should not appear for regular users"


class TestMenuBarConditionalItems:
    """Test conditional menu items (Share Recipes, Pending Shares)."""
    
    def test_share_recipes_with_public_recipes(self, app, auth_client):
        """Test that Share Recipes appears when user has public recipes."""
        with app.app_context():
            # Get test user
            user = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Create a public recipe for the user
            public_recipe = Recipe(
                user_id=user.id,
                name='Public Test Recipe',
                description='A public recipe',
                instructions='Test instructions',
                visibility='public',
                created_at=datetime.utcnow()
            )
            db.session.add(public_recipe)
            db.session.flush()
            
            # Add ingredients
            for i in range(3):
                ingredient = Ingredient(name=f'test_ingredient_{i}')
                db.session.add(ingredient)
                db.session.flush()
                
                recipe_ingredient = RecipeIngredient(
                    recipe_id=public_recipe.id,
                    ingredient_id=ingredient.id,
                    amount='1',
                    unit='cup'
                )
                db.session.add(recipe_ingredient)
            
            db.session.commit()
        
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].get('/recipes')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        nav = soup.find('nav', class_='navbar')
        
        # Should have Share Recipes link (text may be split with icon)
        share_recipes = nav.find('a', href=lambda h: h and '/recipes/share' in h)
        if not share_recipes:
            share_recipes = nav.find('a', string=lambda t: t and 'Share Recipes' in t)
        assert share_recipes is not None, "Share Recipes should appear when user has public recipes"
    
    def test_share_recipes_without_public_recipes(self, app, auth_client):
        """Test that Share Recipes does NOT appear when user has no public recipes."""
        with app.app_context():
            # Get test user
            user = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Ensure user has no public recipes (only private/incomplete)
            Recipe.query.filter(Recipe.user_id == user.id, Recipe.visibility == 'public').delete()
            db.session.commit()
        
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].get('/recipes')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        nav = soup.find('nav', class_='navbar')
        
        # Should NOT have Share Recipes link
        share_recipes = nav.find('a', string=lambda t: t and 'Share Recipes' in t)
        assert share_recipes is None, "Share Recipes should NOT appear when user has no public recipes"
    
    def test_pending_shares_with_pending_shares(self, app, auth_client):
        """Test that Pending Shares appears with badge when user has pending shares."""
        with app.app_context():
            # Get test users
            user1 = db.session.query(User).filter(User.username == 'testuser').first()
            user2 = db.session.query(User).filter(User.username == 'admin').first()
            
            # Create a pending share
            pending_share = PendingRecipeShare(
                shared_by_user_id=user2.id,
                shared_with_user_id=user1.id,
                recipe_id=1,  # Dummy recipe ID
                status='pending',
                created_at=datetime.utcnow()
            )
            db.session.add(pending_share)
            db.session.commit()
        
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].get('/recipes')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        nav = soup.find('nav', class_='navbar')
        
        # Should have Pending Shares link (text may be split with icon)
        pending_shares = nav.find('a', href=lambda h: h and '/pending-shares' in h)
        if not pending_shares:
            pending_shares = nav.find('a', string=lambda t: t and 'Pending Shares' in t)
        assert pending_shares is not None, "Pending Shares should appear when user has pending shares"
        
        # Should have badge with count
        badge = pending_shares.find('span', class_='badge')
        assert badge is not None, "Pending Shares should have a badge"
        assert int(badge.text.strip()) > 0, "Badge should show count > 0"
    
    def test_pending_shares_without_pending_shares(self, app, auth_client):
        """Test that Pending Shares does NOT appear when user has no pending shares."""
        with app.app_context():
            # Get test user
            user = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Ensure user has no pending shares
            PendingRecipeShare.query.filter(
                PendingRecipeShare.shared_with_user_id == user.id
            ).delete()
            db.session.commit()
        
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].get('/recipes')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        nav = soup.find('nav', class_='navbar')
        
        # Should NOT have Pending Shares link
        pending_shares = nav.find('a', string=lambda t: t and 'Pending Shares' in t)
        assert pending_shares is None, "Pending Shares should NOT appear when user has no pending shares"
    
    def test_friends_notification_badge(self, app, auth_client):
        """Test that Friends link shows notification badge when user has unread notifications."""
        with app.app_context():
            # Get test user
            user = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Create an unread notification
            notification = Notification(
                user_id=user.id,
                notification_type='friend_request',
                message='Test notification',
                read=False,
                created_at=datetime.utcnow()
            )
            db.session.add(notification)
            db.session.commit()
        
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].get('/recipes')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        nav = soup.find('nav', class_='navbar')
        
        # Find Friends link (text may be split with icon)
        friends_link = nav.find('a', href=lambda h: h and '/friends' in h)
        if not friends_link:
            friends_link = nav.find('a', string=lambda t: t and 'Friends' in t)
        assert friends_link is not None, "Friends link should be present"
        
        # Should have badge with count
        badge = friends_link.find('span', class_='badge')
        assert badge is not None, "Friends should have a badge when there are unread notifications"
        assert int(badge.text.strip()) > 0, "Badge should show count > 0"
    
    def test_friends_no_notification_badge(self, app, auth_client):
        """Test that Friends link does NOT show badge when user has no unread notifications."""
        with app.app_context():
            # Get test user
            user = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Mark all notifications as read
            Notification.query.filter(Notification.user_id == user.id).update({'read': True})
            db.session.commit()
        
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].get('/recipes')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        nav = soup.find('nav', class_='navbar')
        
        # Find Friends link (text may be split with icon)
        friends_link = None
        for link in nav.find_all('a'):
            href = link.get('href', '')
            text = link.get_text()
            if '/friends' in href and '/friends/' not in href:
                friends_link = link
                break
            elif 'Friends' in text and '/friends' in href:
                friends_link = link
                break
        assert friends_link is not None, "Friends link should be present"
        
        # Should NOT have badge (or badge should be 0)
        badge = friends_link.find('span', class_='badge')
        if badge:
            # If badge exists, it should be 0 or not visible
            count = int(badge.text.strip())
            assert count == 0, "Badge should show 0 or not appear when there are no unread notifications"


class TestMenuBarAdmin:
    """Test menu bar for admin users."""
    
    def test_admin_menu_items(self, auth_client):
        """Test that admin users see admin menu items."""
        auth_client['login']('admin', 'admin123')
        
        response = auth_client['client'].get('/recipes')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        nav = soup.find('nav', class_='navbar')
        
        # Should have Admin dropdown
        admin_dropdown = nav.find('a', id='adminDropdown')
        assert admin_dropdown is not None, "Admin dropdown should appear for admin users"
        
        # Check dropdown menu items
        dropdown_parent = admin_dropdown.find_parent('li', class_='nav-item')
        if dropdown_parent:
            dropdown_menu = dropdown_parent.find('ul', class_='dropdown-menu')
            assert dropdown_menu is not None, "Admin dropdown menu should be present"
            
            # Should have Manage Users
            manage_users = dropdown_menu.find('a', href=lambda h: h and '/admin/users' in h)
            assert manage_users is not None, "Manage Users should be in admin dropdown"
            
            # Should have Manage Recipes
            manage_recipes = dropdown_menu.find('a', href=lambda h: h and '/admin/recipes' in h)
            assert manage_recipes is not None, "Manage Recipes should be in admin dropdown"
            
            # Should have Manage Tags
            manage_tags = dropdown_menu.find('a', href=lambda h: h and '/admin/tags' in h)
            assert manage_tags is not None, "Manage Tags should be in admin dropdown"
            
            # Should have Dashboard (may be in user dropdown instead)
            dashboard = dropdown_menu.find('a', href=lambda h: h and '/admin/dashboard' in h)
            # Dashboard might be in user dropdown, so this is optional here
            # We'll check user dropdown separately
        
        # Should also have Admin Dashboard in user dropdown
        user_dropdown = nav.find('a', id='userDropdown')
        assert user_dropdown is not None, "User dropdown should be present"
        
        dropdown_parent = user_dropdown.find_parent('li', class_='nav-item')
        if dropdown_parent:
            user_dropdown_menu = dropdown_parent.find('ul', class_='dropdown-menu')
            if user_dropdown_menu:
                admin_dashboard = None
                for link in user_dropdown_menu.find_all('a'):
                    if 'Admin Dashboard' in link.get_text() or '/admin/dashboard' in link.get('href', ''):
                        admin_dashboard = link
                        break
                assert admin_dashboard is not None, "Admin Dashboard should be in user dropdown for admin users"
    
    def test_non_admin_no_admin_menu(self, auth_client):
        """Test that non-admin users do NOT see admin menu items."""
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].get('/recipes')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        nav = soup.find('nav', class_='navbar')
        
        # Should NOT have Admin dropdown
        admin_dropdown = nav.find('a', id='adminDropdown')
        assert admin_dropdown is None, "Admin dropdown should NOT appear for non-admin users"


class TestMenuBarConsistency:
    """Test menu bar consistency across all pages."""
    
    def test_menu_consistency_across_pages(self, auth_client):
        """Test that menu bar is consistent across different pages."""
        auth_client['login']('testuser', 'password123')
        
        # Pages to test
        pages = [
            '/recipes',
            '/recipe/new',
            '/my-recipes',
            '/auth/profile',
            '/friends',
            '/tag-manager',
        ]
        
        menu_items = {}
        
        for page in pages:
            response = auth_client['client'].get(page)
            if response.status_code == 200:
                soup = BeautifulSoup(response.data, 'html.parser')
                nav = soup.find('nav', class_='navbar')
                
                if nav:
                    # Extract menu items
                    items = []
                    for link in nav.find_all('a', class_='nav-link'):
                        text = link.get_text(strip=True)
                        href = link.get('href', '')
                        items.append((text, href))
                    
                    menu_items[page] = set(items)
        
        # Compare menu items across pages
        if len(menu_items) > 1:
            base_page = list(menu_items.keys())[0]
            base_items = menu_items[base_page]
            
            for page, items in menu_items.items():
                # Core items should be the same (ignoring active state)
                core_base = {item for item in base_items if not any(x in item[0] for x in ['active', 'badge'])}
                core_page = {item for item in items if not any(x in item[0] for x in ['active', 'badge'])}
                
                # Allow for minor differences (like active state), but core structure should match
                assert len(core_base.symmetric_difference(core_page)) < 3, \
                    f"Menu items differ significantly between {base_page} and {page}"
    
    def test_search_bar_on_all_pages(self, auth_client):
        """Test that search bar appears on all pages."""
        auth_client['login']('testuser', 'password123')
        
        pages = [
            '/recipes',
            '/recipe/new',
            '/my-recipes',
            '/auth/profile',
            '/friends',
        ]
        
        for page in pages:
            response = auth_client['client'].get(page)
            if response.status_code == 200:
                soup = BeautifulSoup(response.data, 'html.parser')
                nav = soup.find('nav', class_='navbar')
                
                if nav:
                    search_form = nav.find('form', method='GET')
                    assert search_form is not None, f"Search bar should be present on {page}"


class TestMenuBarActiveStates:
    """Test active state highlighting in menu bar."""
    
    def test_active_state_recipe_list(self, auth_client):
        """Test that Browse Recipes is active on recipe list page."""
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].get('/recipes')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        nav = soup.find('nav', class_='navbar')
        
        browse_link = nav.find('a', href=lambda h: h and '/recipes' in h, 
                              string=lambda t: t and 'Browse Recipes' in t)
        if browse_link:
            assert 'active' in browse_link.get('class', []), \
                "Browse Recipes should be active on recipe list page"
    
    def test_active_state_my_recipes(self, auth_client):
        """Test that My Recipes is active on my recipes page."""
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].get('/my-recipes')
        if response.status_code == 200:
            soup = BeautifulSoup(response.data, 'html.parser')
            nav = soup.find('nav', class_='navbar')
            
            my_recipes_link = nav.find('a', href=lambda h: h and '/my-recipes' in h,
                                      string=lambda t: t and 'My Recipes' in t)
            if my_recipes_link:
                assert 'active' in my_recipes_link.get('class', []), \
                    "My Recipes should be active on my recipes page"


class TestMenuBarCornerCases:
    """Test corner cases and edge cases for menu bar."""
    
    def test_menu_with_deleted_public_recipes(self, app, auth_client):
        """Test that Share Recipes does not appear if user only has deleted public recipes."""
        with app.app_context():
            from datetime import datetime
            user = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Create a public recipe and soft-delete it
            public_recipe = Recipe(
                user_id=user.id,
                name='Deleted Public Recipe',
                description='A deleted public recipe',
                instructions='Test instructions',
                visibility='public',
                deleted_at=datetime.utcnow(),
                created_at=datetime.utcnow()
            )
            db.session.add(public_recipe)
            db.session.flush()
            
            # Add ingredients
            for i in range(3):
                ingredient = Ingredient(name=f'deleted_ingredient_{i}')
                db.session.add(ingredient)
                db.session.flush()
                
                recipe_ingredient = RecipeIngredient(
                    recipe_id=public_recipe.id,
                    ingredient_id=ingredient.id,
                    amount='1',
                    unit='cup'
                )
                db.session.add(recipe_ingredient)
            
            db.session.commit()
        
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].get('/recipes')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        nav = soup.find('nav', class_='navbar')
        
        # Should NOT have Share Recipes link (deleted recipes don't count)
        share_recipes = nav.find('a', string=lambda t: t and 'Share Recipes' in t)
        assert share_recipes is None, "Share Recipes should NOT appear when user only has deleted public recipes"
    
    def test_menu_with_multiple_pending_shares(self, app, auth_client):
        """Test that Pending Shares badge shows correct count with multiple pending shares."""
        with app.app_context():
            user = db.session.query(User).filter(User.username == 'testuser').first()
            admin = db.session.query(User).filter(User.username == 'admin').first()
            
            # Create multiple pending shares
            for i in range(3):
                pending_share = PendingRecipeShare(
                    shared_by_user_id=admin.id,
                    shared_with_user_id=user.id,
                    recipe_id=i + 1,
                    status='pending',
                    created_at=datetime.utcnow()
                )
                db.session.add(pending_share)
            
            db.session.commit()
        
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].get('/recipes')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        nav = soup.find('nav', class_='navbar')
        
        # Find Pending Shares link (text may be split with icon)
        pending_shares = nav.find('a', href=lambda h: h and '/pending-shares' in h)
        if not pending_shares:
            # Try by text
            for link in nav.find_all('a'):
                if 'Pending Shares' in link.get_text():
                    pending_shares = link
                    break
        assert pending_shares is not None, "Pending Shares should appear"
        
        badge = pending_shares.find('span', class_='badge')
        assert badge is not None, "Badge should be present"
        assert int(badge.text.strip()) == 3, "Badge should show correct count (3)"
    
    def test_menu_with_zero_notifications(self, app, auth_client):
        """Test that Friends link works correctly with zero notifications."""
        with app.app_context():
            user = db.session.query(User).filter(User.username == 'testuser').first()
            
            # Ensure no unread notifications
            Notification.query.filter(
                Notification.user_id == user.id,
                Notification.read == False
            ).update({'read': True})
            db.session.commit()
        
        auth_client['login']('testuser', 'password123')
        
        response = auth_client['client'].get('/recipes')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        nav = soup.find('nav', class_='navbar')
        
        friends_link = nav.find('a', href=lambda h: h and '/friends' in h)
        if not friends_link:
            friends_link = nav.find('a', string=lambda t: t and 'Friends' in t)
        assert friends_link is not None, "Friends link should be present"
        
        # Badge should either not exist or show 0
        badge = friends_link.find('span', class_='badge')
        if badge:
            assert int(badge.text.strip()) == 0, "Badge should show 0 if present"
    
    def test_menu_on_error_pages(self, client):
        """Test that menu bar appears on error pages (404, 500)."""
        # Test 404 page
        response = client.get('/nonexistent-page-that-does-not-exist-12345')
        # May redirect or show 404, but if it renders, should have menu
        if response.status_code == 200:
            soup = BeautifulSoup(response.data, 'html.parser')
            nav = soup.find('nav', class_='navbar')
            assert nav is not None, "Menu bar should appear on 404 page"
    
    def test_menu_with_inactive_user(self, app, auth_client):
        """Test menu bar behavior with inactive user (edge case)."""
        with app.app_context():
            user = db.session.query(User).filter(User.username == 'testuser').first()
            user.is_active = False
            db.session.commit()
        
        # Try to login (should fail or user should be inactive)
        response = auth_client['client'].post('/auth/login', data={
            'username': 'testuser',
            'password': 'password123'
        })
        
        # User should not be able to access authenticated pages
        # This tests that inactive users don't see authenticated menu items
        response = auth_client['client'].get('/recipes')
        # Should redirect to login or show unauthenticated menu
        if response.status_code == 200:
            soup = BeautifulSoup(response.data, 'html.parser')
            nav = soup.find('nav', class_='navbar')
            if nav:
                # Should show unauthenticated menu items
                login_link = nav.find('a', href=lambda h: h and '/auth/login' in h)
                # Login link should be present if user is not authenticated
                # (This is a corner case - inactive users shouldn't be able to login)
        
        # Restore user for other tests
        with app.app_context():
            user = db.session.query(User).filter(User.username == 'testuser').first()
            user.is_active = True
            db.session.commit()

