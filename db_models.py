"""
SQLAlchemy Database Models for Multi-User Recipe Application
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import Text, JSON, CheckConstraint, Index
from sqlalchemy.ext.hybrid import hybrid_property

db = SQLAlchemy()

# ============================================================================
# USER MANAGEMENT
# ============================================================================

# UserType model removed - using simplified permission system with is_admin flag


class User(UserMixin, db.Model):
    """User account model."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(100))
    avatar_url = db.Column(db.String(500))
    email_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)  # Keep for backward compatibility
    can_publish_public = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Password setup fields for admin-created accounts
    password_setup_token = db.Column(db.String(100), nullable=True)
    password_setup_expires = db.Column(db.DateTime, nullable=True)
    account_setup_completed = db.Column(db.Boolean, default=False)
    
    # Email change fields
    pending_email = db.Column(db.String(255), nullable=True)
    email_change_token = db.Column(db.String(100), nullable=True)
    email_change_expires = db.Column(db.DateTime, nullable=True)
    
    # Relationships (simplified - no user_type relationship)
    recipes = db.relationship('Recipe', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    preferences = db.relationship('UserPreference', back_populates='user', uselist=False, cascade='all, delete-orphan')
    favorites = db.relationship('RecipeFavorite', back_populates='user', cascade='all, delete-orphan')
    ratings = db.relationship('RecipeRating', back_populates='user', cascade='all, delete-orphan')
    collections = db.relationship('Collection', back_populates='user', cascade='all, delete-orphan')
    meal_plans = db.relationship('MealPlan', back_populates='user', cascade='all, delete-orphan')
    stats = db.relationship('UserStats', back_populates='user', uselist=False, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    # Permission checking methods (simplified)
    def can_view_recipes(self):
        """Check if user can view recipes."""
        return self.is_active  # All active users can view
    
    def can_create_recipes(self):
        """Check if user can create recipes."""
        return self.is_active  # All active users can create
    
    def can_edit_recipe(self, recipe):
        """Check if user can edit a specific recipe."""
        # Public recipes cannot be edited by anyone
        if recipe.visibility == 'public':
            return False
        # Admin can edit all non-public recipes
        if self.is_admin:
            return True
        # Users can edit their own recipes only if not public
        if recipe.user_id == self.id:
            return recipe.visibility in ['incomplete', 'private']
        return False
    
    def can_delete_recipe(self, recipe):
        """Check if user can delete a specific recipe."""
        # Admin can delete all recipes
        if self.is_admin:
            return True
        # Users can delete their own recipes only if not public
        if recipe.user_id == self.id:
            return recipe.visibility in ['incomplete', 'private']
        return False
    
    def can_manage_users(self):
        """Check if user can manage other users."""
        return self.is_admin
    
    def can_manage_system(self):
        """Check if user can manage system settings."""
        return self.is_admin
    
    def can_share_recipes(self):
        """Check if user can share recipes."""
        return self.is_active  # All active users can share
    
    def can_share_recipe(self, recipe):
        """Check if user can share a specific recipe."""
        # User must own the recipe
        if recipe.user_id != self.id:
            return False
        # Recipe must be public
        if recipe.visibility != 'public':
            return False
        # No need to check for friends - share button shown for all public recipes
        # User will be directed to find friends if needed
        return True
    
    def has_public_recipes(self):
        """Check if user has any public recipes."""
        return db.session.query(Recipe).filter(
            Recipe.user_id == self.id,
            Recipe.visibility == 'public',
            Recipe.deleted_at.is_(None)
        ).first() is not None
    
    def get_pending_shares_received(self):
        """Get all pending recipe shares received by this user."""
        return db.session.query(PendingRecipeShare).filter(
            PendingRecipeShare.shared_with_user_id == self.id,
            PendingRecipeShare.status == 'pending'
        ).all()
    
    def get_pending_shares_count(self):
        """Get count of pending recipe shares for this user."""
        return db.session.query(PendingRecipeShare).filter(
            PendingRecipeShare.shared_with_user_id == self.id,
            PendingRecipeShare.status == 'pending'
        ).count()
    
    def can_publish_public_recipes(self):
        """Check if user can publish public recipes."""
        return self.is_admin or self.can_publish_public
    
    def get_friends(self):
        """Get all friends of this user."""
        friendships = db.session.query(Friendship).filter(
            (Friendship.user1_id == self.id) | (Friendship.user2_id == self.id)
        ).all()
        
        friend_ids = []
        for friendship in friendships:
            if friendship.user1_id == self.id:
                friend_ids.append(friendship.user2_id)
            else:
                friend_ids.append(friendship.user1_id)
        
        if not friend_ids:
            return []
        
        return db.session.query(User).filter(User.id.in_(friend_ids)).all()
    
    def is_friends_with(self, user_id):
        """Check if this user is friends with another user."""
        if user_id == self.id:
            return False  # Can't be friends with yourself
        
        friendship = db.session.query(Friendship).filter(
            ((Friendship.user1_id == self.id) & (Friendship.user2_id == user_id)) |
            ((Friendship.user1_id == user_id) & (Friendship.user2_id == self.id))
        ).first()
        
        return friendship is not None
    
    def get_pending_sent_requests(self):
        """Get pending friend requests sent by this user."""
        return db.session.query(FriendRequest).filter(
            FriendRequest.sender_id == self.id,
            FriendRequest.status == 'pending'
        ).all()
    
    def get_pending_received_requests(self):
        """Get pending friend requests received by this user."""
        return db.session.query(FriendRequest).filter(
            FriendRequest.recipient_id == self.id,
            FriendRequest.status == 'pending'
        ).all()
    
    def get_unread_notification_count(self):
        """Get count of unread notifications."""
        return db.session.query(Notification).filter(
            Notification.user_id == self.id,
            Notification.read == False
        ).count()


class UserPreference(db.Model):
    """User preferences and settings."""
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    measurement_system = db.Column(db.Enum('metric', 'imperial'), default='imperial')
    dietary_restrictions = db.Column(JSON)
    allergens = db.Column(JSON)
    email_notifications = db.Column(db.Boolean, default=True)
    default_visibility = db.Column(db.Enum('private', 'public', 'incomplete'), default='incomplete')
    theme = db.Column(db.String(20), default='light')
    
    # Relationship
    user = db.relationship('User', back_populates='preferences')


class PasswordResetToken(db.Model):
    """Password reset tokens."""
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User')


# ============================================================================
# INGREDIENTS
# ============================================================================

class Ingredient(db.Model):
    """Master ingredient catalog."""
    __tablename__ = 'ingredients'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    plural_name = db.Column(db.String(200))
    category = db.Column(db.String(50))
    subcategory = db.Column(db.String(50))
    aliases = db.Column(JSON)
    is_common = db.Column(db.Boolean, default=False)
    allergen_info = db.Column(JSON)
    nutritional_data = db.Column(JSON)
    default_unit = db.Column(db.String(20))
    storage_tips = db.Column(Text)
    substitution_suggestions = db.Column(JSON)
    seasonal_info = db.Column(JSON)
    usage_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    recipe_ingredients = db.relationship('RecipeIngredient', back_populates='ingredient')
    
    def __repr__(self):
        return f'<Ingredient {self.name}>'


class RecipeIngredient(db.Model):
    """Recipe-ingredient junction with measurements."""
    __tablename__ = 'recipe_ingredients'
    
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id', ondelete='RESTRICT'), nullable=False)
    amount = db.Column(db.String(50))
    unit = db.Column(db.String(50))  # Matches DB schema
    preparation = db.Column(db.String(200))  # Matches DB schema
    is_optional = db.Column(db.Boolean, default=False)  # Matches DB schema
    notes = db.Column(Text)
    sort_order = db.Column(db.Integer, default=0)  # Matches DB schema
    ingredient_group = db.Column(db.String(100))  # Matches DB schema
    
    # Relationships
    recipe = db.relationship('Recipe', back_populates='recipe_ingredients')
    ingredient = db.relationship('Ingredient', back_populates='recipe_ingredients')
    
    @property
    def description(self):
        """Get ingredient name for template compatibility."""
        return self.ingredient.name if self.ingredient else ''
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'amount': self.amount or '',
            'unit': self.unit or '',
            'description': self.description,
            'notes': self.notes or ''
        }


class UserIngredientSubstitution(db.Model):
    """User's personal ingredient substitutions."""
    __tablename__ = 'user_ingredient_substitutions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    original_ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id', ondelete='CASCADE'), nullable=False)
    substitute_ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id', ondelete='CASCADE'), nullable=False)
    reason = db.Column(db.String(200))
    auto_apply = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User')
    original_ingredient = db.relationship('Ingredient', foreign_keys=[original_ingredient_id])
    substitute_ingredient = db.relationship('Ingredient', foreign_keys=[substitute_ingredient_id])


# ============================================================================
# RECIPES
# ============================================================================

class Recipe(db.Model):
    """Main recipe model."""
    __tablename__ = 'recipes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(Text)
    instructions = db.Column(Text, nullable=False)
    notes = db.Column(Text)
    prep_time = db.Column(db.Integer)
    cook_time = db.Column(db.Integer)
    servings = db.Column(db.String(50))
    difficulty = db.Column(db.Enum('easy', 'medium', 'hard'))
    visibility = db.Column(db.Enum('private', 'public', 'incomplete'), default='incomplete')
    slug = db.Column(db.String(250), unique=True)
    meta_description = db.Column(db.String(300))
    ingredients_json = db.Column(JSON)  # Store ingredients as JSON to preserve empty positions
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = db.Column(db.DateTime)
    deleted_at = db.Column(db.DateTime, nullable=True)  # Soft delete support for shared recipes
    
    # Relationships
    recipe_ingredients = db.relationship('RecipeIngredient', back_populates='recipe', 
                                        cascade='all, delete-orphan', 
                                        order_by='RecipeIngredient.sort_order')
    source = db.relationship('RecipeSource', back_populates='recipe', uselist=False, cascade='all, delete-orphan')
    photos = db.relationship('RecipePhoto', back_populates='recipe', cascade='all, delete-orphan')
    tags = db.relationship('Tag', secondary='recipe_tags', back_populates='recipes')
    favorites = db.relationship('RecipeFavorite', back_populates='recipe', cascade='all, delete-orphan')
    ratings = db.relationship('RecipeRating', back_populates='recipe', cascade='all, delete-orphan')
    stats = db.relationship('RecipeStats', back_populates='recipe', uselist=False, cascade='all, delete-orphan')
    
    @hybrid_property
    def total_time(self):
        """Calculate total time."""
        prep = self.prep_time or 0
        cook = self.cook_time or 0
        return prep + cook
    
    @property
    def ingredients(self):
        """Get ingredients from JSON field, preserving empty positions."""
        if self.ingredients_json:
            return self.ingredients_json
        # Fallback to old recipe_ingredients for backward compatibility
        return [ing.to_dict() for ing in self.recipe_ingredients]
    
    def can_view(self, user):
        """Check if a user can view this recipe."""
        # Public recipes visible to all logged-in users
        if self.visibility == 'public' and user:
            return True
        # Users can always view their own recipes (private and incomplete)
        if user and (user.id == self.user_id or user.is_admin):
            return True
        return False
    
    def can_set_visibility_to(self, visibility_level, user):
        """Check if user can set this visibility level."""
        if not user:
            return False
        if user.is_admin:
            return True
        if user.id != self.user_id:
            return False
        # Only users with permission can make recipes public
        if visibility_level == 'public':
            return user.can_publish_public_recipes()
        # If recipe has active shares, cannot change from public to non-public
        if self.visibility == 'public' and visibility_level != 'public':
            if self.has_active_shares():
                return False
        return True  # Anyone can set private or incomplete
    
    def has_active_shares(self):
        """Check if recipe has any active shares."""
        from sqlalchemy import func
        return db.session.query(func.count(RecipeShare.id)).filter(
            RecipeShare.recipe_id == self.id
        ).scalar() > 0
    
    def is_shared_with(self, user_id):
        """Check if recipe is shared with a specific user."""
        return db.session.query(RecipeShare).filter(
            RecipeShare.recipe_id == self.id,
            RecipeShare.shared_with_user_id == user_id
        ).first() is not None
    
    def get_shared_with_friends(self):
        """Get list of friends this recipe is shared with."""
        shares = db.session.query(RecipeShare).filter(
            RecipeShare.recipe_id == self.id
        ).all()
        friend_ids = [share.shared_with_user_id for share in shares]
        return db.session.query(User).filter(User.id.in_(friend_ids)).all() if friend_ids else []
    
    def get_shared_by_friend(self, user_id):
        """Get the friend who shared this recipe with the given user."""
        share = db.session.query(RecipeShare).filter(
            RecipeShare.recipe_id == self.id,
            RecipeShare.shared_with_user_id == user_id
        ).first()
        if share:
            return db.session.query(User).filter(User.id == share.shared_by_user_id).first()
        return None
    
    def __repr__(self):
        return f'<Recipe {self.name}>'


class RecipeSource(db.Model):
    """Recipe source/attribution."""
    __tablename__ = 'recipe_sources'
    
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False, unique=True)
    source_name = db.Column(db.String(200))
    source_url = db.Column(Text)
    author = db.Column(db.String(200))
    issue = db.Column(db.String(100))
    imported_from = db.Column(db.Enum('manual', 'url', 'pdf', 'text_file', 'api'), default='manual')
    imported_at = db.Column(db.DateTime)
    source_url_confidence = db.Column(db.Numeric(3, 2))  # Confidence score 0.00-1.00 for auto-detected URLs
    source_url_detection_method = db.Column(db.Enum('manual', 'gemini_suggested', 'search_api', 'user_provided'), default='manual')
    
    # Relationship
    recipe = db.relationship('Recipe', back_populates='source')


class RecipePhoto(db.Model):
    """Recipe photos."""
    __tablename__ = 'recipe_photos'
    
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False)
    photo_url = db.Column(db.String(500), nullable=False)
    photo_type = db.Column(db.Enum('main', 'step', 'result', 'gallery'), default='gallery')
    caption = db.Column(Text)
    step_number = db.Column(db.Integer)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    recipe = db.relationship('Recipe', back_populates='photos')


# ============================================================================
# TAGS
# ============================================================================

# Association table for recipe-tag many-to-many
recipe_tags = db.Table('recipe_tags',
    db.Column('recipe_id', db.Integer, db.ForeignKey('recipes.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
    mysql_engine='InnoDB',
    mysql_charset='utf8mb4'
)

class Tag(db.Model):
    """Recipe tags - can be system-wide or personal to a user."""
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), nullable=False)
    tag_scope = db.Column(db.Enum('system', 'personal'), default='personal', nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    description = db.Column(Text)
    tag_type = db.Column(db.Enum('cuisine', 'diet', 'meal_type', 'method', 'occasion', 'season', 'other'), default='other')
    icon = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    recipes = db.relationship('Recipe', secondary=recipe_tags, back_populates='tags')
    user = db.relationship('User', backref='tags')
    
    @property
    def recipe_count(self):
        """Get count of recipes with this tag."""
        return len(self.recipes)
    
    @property
    def is_system(self):
        """Check if this is a system tag."""
        return self.tag_scope == 'system'
    
    @property
    def is_personal(self):
        """Check if this is a personal tag."""
        return self.tag_scope == 'personal'
    
    def __repr__(self):
        scope = f" ({self.tag_scope})" if self.tag_scope else ""
        owner = f" [User:{self.user_id}]" if self.user_id else ""
        return f'<Tag {self.name}{scope}{owner}>'


# ============================================================================
# USER INTERACTIONS
# ============================================================================

class RecipeFavorite(db.Model):
    """User favorites."""
    __tablename__ = 'recipe_favorites'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False)
    personal_notes = db.Column(Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='favorites')
    recipe = db.relationship('Recipe', back_populates='favorites')
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'recipe_id', name='unique_favorite'),
    )


class RecipeRating(db.Model):
    """User ratings and reviews."""
    __tablename__ = 'recipe_ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False)
    rating = db.Column(db.Numeric(2, 1), nullable=False)
    review = db.Column(Text)
    modifications = db.Column(Text)
    would_make_again = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='ratings')
    recipe = db.relationship('Recipe', back_populates='ratings')
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'recipe_id', name='unique_rating'),
        CheckConstraint('rating >= 0 AND rating <= 5', name='rating_range'),
    )


class Collection(db.Model):
    """User collections/cookbooks."""
    __tablename__ = 'collections'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(Text)
    cover_photo_url = db.Column(db.String(500))
    visibility = db.Column(db.Enum('private', 'public'), default='private')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='collections')
    collection_recipes = db.relationship('CollectionRecipe', back_populates='collection', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Collection {self.name}>'


class CollectionRecipe(db.Model):
    """Recipes in collections."""
    __tablename__ = 'collection_recipes'
    
    collection_id = db.Column(db.Integer, db.ForeignKey('collections.id', ondelete='CASCADE'), primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id', ondelete='CASCADE'), primary_key=True)
    sort_order = db.Column(db.Integer, default=0)
    personal_notes = db.Column(Text)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    collection = db.relationship('Collection', back_populates='collection_recipes')
    recipe = db.relationship('Recipe')


# ============================================================================
# MEAL PLANNING
# ============================================================================

class MealPlan(db.Model):
    """Meal plans."""
    __tablename__ = 'meal_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(200))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    notes = db.Column(Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='meal_plans')
    meal_plan_recipes = db.relationship('MealPlanRecipe', back_populates='meal_plan', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<MealPlan {self.name}>'


class MealPlanRecipe(db.Model):
    """Recipes in meal plans."""
    __tablename__ = 'meal_plan_recipes'
    
    id = db.Column(db.Integer, primary_key=True)
    meal_plan_id = db.Column(db.Integer, db.ForeignKey('meal_plans.id', ondelete='CASCADE'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False)
    planned_date = db.Column(db.Date, nullable=False)
    meal_type = db.Column(db.Enum('breakfast', 'lunch', 'dinner', 'snack', 'dessert', 'other'))
    servings_planned = db.Column(db.Integer)
    notes = db.Column(Text)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    meal_plan = db.relationship('MealPlan', back_populates='meal_plan_recipes')
    recipe = db.relationship('Recipe')


# ============================================================================
# STATISTICS
# ============================================================================

class RecipeStats(db.Model):
    """Recipe statistics (cached)."""
    __tablename__ = 'recipe_stats'
    
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id', ondelete='CASCADE'), primary_key=True)
    view_count = db.Column(db.Integer, default=0)
    unique_view_count = db.Column(db.Integer, default=0)
    favorite_count = db.Column(db.Integer, default=0)
    rating_count = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Numeric(3, 2), default=0)
    review_count = db.Column(db.Integer, default=0)
    email_share_count = db.Column(db.Integer, default=0)
    print_count = db.Column(db.Integer, default=0)
    last_viewed_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    recipe = db.relationship('Recipe', back_populates='stats')


class UserStats(db.Model):
    """User statistics (cached)."""
    __tablename__ = 'user_stats'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    recipe_count = db.Column(db.Integer, default=0)
    public_recipe_count = db.Column(db.Integer, default=0)
    private_recipe_count = db.Column(db.Integer, default=0)
    collection_count = db.Column(db.Integer, default=0)
    total_recipe_views = db.Column(db.Integer, default=0)
    total_recipe_favorites = db.Column(db.Integer, default=0)
    average_recipe_rating = db.Column(db.Numeric(3, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', back_populates='stats')


# ============================================================================
# EMAIL SHARING
# ============================================================================

class RecipeEmailLog(db.Model):
    """Track recipe emails sent."""
    __tablename__ = 'recipe_email_log'
    
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False)
    sent_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    recipient_email = db.Column(db.String(255), nullable=False)
    recipient_name = db.Column(db.String(100))
    message = db.Column(Text)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    recipe = db.relationship('Recipe')
    sent_by = db.relationship('User')


# ============================================================================
# FRIEND FEATURE
# ============================================================================

class FriendRequest(db.Model):
    """Friend requests between users."""
    __tablename__ = 'friend_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.Enum('pending', 'accepted', 'rejected', 'cancelled'), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_friend_requests')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_friend_requests')
    
    __table_args__ = (
        db.UniqueConstraint('sender_id', 'recipient_id', name='unique_request'),
    )
    
    def __repr__(self):
        return f'<FriendRequest {self.sender_id} -> {self.recipient_id} ({self.status})>'


class Friendship(db.Model):
    """Established friendships between users."""
    __tablename__ = 'friendships'
    
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user1 = db.relationship('User', foreign_keys=[user1_id], backref='friendships_as_user1')
    user2 = db.relationship('User', foreign_keys=[user2_id], backref='friendships_as_user2')
    
    __table_args__ = (
        db.UniqueConstraint('user1_id', 'user2_id', name='unique_friendship'),
        db.CheckConstraint('user1_id < user2_id', name='check_user_order'),
    )
    
    def get_other_user(self, user_id):
        """Get the other user in this friendship."""
        if self.user1_id == user_id:
            return self.user2
        elif self.user2_id == user_id:
            return self.user1
        return None
    
    def __repr__(self):
        return f'<Friendship {self.user1_id} <-> {self.user2_id}>'


class RecipeShare(db.Model):
    """Tracks recipes shared with friends."""
    __tablename__ = 'recipe_shares'
    
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False)
    shared_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    shared_with_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    recipe = db.relationship('Recipe', backref='shares')
    shared_by = db.relationship('User', foreign_keys=[shared_by_user_id], backref='recipes_shared')
    shared_with = db.relationship('User', foreign_keys=[shared_with_user_id], backref='recipes_received')
    
    __table_args__ = (
        db.UniqueConstraint('recipe_id', 'shared_by_user_id', 'shared_with_user_id', name='unique_share'),
    )
    
    def __repr__(self):
        return f'<RecipeShare recipe={self.recipe_id} by={self.shared_by_user_id} with={self.shared_with_user_id}>'


class PendingRecipeShare(db.Model):
    """Tracks pending recipe shares (before friendship or account creation)."""
    __tablename__ = 'pending_recipe_shares'
    
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False)
    shared_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    shared_with_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    recipient_email = db.Column(db.String(255), nullable=True)  # For non-users
    friend_request_id = db.Column(db.Integer, db.ForeignKey('friend_requests.id', ondelete='CASCADE'), nullable=True)
    token = db.Column(db.String(255), nullable=True, unique=True)  # For email share links
    status = db.Column(db.Enum('pending', 'accepted', 'rejected'), default='pending', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    recipe = db.relationship('Recipe', backref='pending_shares')
    shared_by_user = db.relationship('User', foreign_keys=[shared_by_user_id], backref='pending_shares_sent')
    shared_with_user = db.relationship('User', foreign_keys=[shared_with_user_id], backref='pending_shares_received')
    friend_request = db.relationship('FriendRequest', backref='pending_shares')
    
    __table_args__ = (
        db.Index('idx_pending_share_email', 'recipient_email'),
        db.Index('idx_pending_share_token', 'token'),
        db.Index('idx_pending_share_status', 'status'),
    )
    
    def __repr__(self):
        return f'<PendingRecipeShare recipe={self.recipe_id} by={self.shared_by_user_id} status={self.status}>'


class Notification(db.Model):
    """In-app notifications for users."""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    notification_type = db.Column(db.Enum('friend_request', 'recipe_shared'), nullable=False)
    related_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id', ondelete='CASCADE'), nullable=True)
    message = db.Column(Text)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='notifications')
    related_user = db.relationship('User', foreign_keys=[related_user_id])
    recipe = db.relationship('Recipe')
    
    def __repr__(self):
        return f'<Notification {self.notification_type} for user {self.user_id} (read={self.read})>'

