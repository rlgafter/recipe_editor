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

class UserType(db.Model):
    """User type definitions with permissions."""
    __tablename__ = 'user_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(Text)
    can_view_recipes = db.Column(db.Boolean, default=True)
    can_create_recipes = db.Column(db.Boolean, default=False)
    can_edit_all_recipes = db.Column(db.Boolean, default=False)
    can_delete_all_recipes = db.Column(db.Boolean, default=False)
    can_manage_users = db.Column(db.Boolean, default=False)
    can_manage_system = db.Column(db.Boolean, default=False)
    can_share_recipes = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', back_populates='user_type')
    
    def __repr__(self):
        return f'<UserType {self.name}>'


class User(UserMixin, db.Model):
    """User account model."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(100))
    bio = db.Column(Text)
    avatar_url = db.Column(db.String(500))
    email_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)  # Keep for backward compatibility
    user_type_id = db.Column(db.Integer, db.ForeignKey('user_types.id'), default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    user_type = db.relationship('UserType', back_populates='users')
    recipes = db.relationship('Recipe', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    preferences = db.relationship('UserPreference', back_populates='user', uselist=False, cascade='all, delete-orphan')
    favorites = db.relationship('RecipeFavorite', back_populates='user', cascade='all, delete-orphan')
    ratings = db.relationship('RecipeRating', back_populates='user', cascade='all, delete-orphan')
    collections = db.relationship('Collection', back_populates='user', cascade='all, delete-orphan')
    meal_plans = db.relationship('MealPlan', back_populates='user', cascade='all, delete-orphan')
    stats = db.relationship('UserStats', back_populates='user', uselist=False, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    # Permission checking methods
    def can_view_recipes(self):
        """Check if user can view recipes."""
        return self.user_type.can_view_recipes if self.user_type else False
    
    def can_create_recipes(self):
        """Check if user can create recipes."""
        return self.user_type.can_create_recipes if self.user_type else False
    
    def can_edit_recipe(self, recipe):
        """Check if user can edit a specific recipe."""
        if not self.user_type:
            return False
        # Admin can edit all recipes
        if self.user_type.can_edit_all_recipes:
            return True
        # Others can edit their own recipes if they can create recipes
        return self.user_type.can_create_recipes and recipe.user_id == self.id
    
    def can_delete_recipe(self, recipe):
        """Check if user can delete a specific recipe."""
        if not self.user_type:
            return False
        # Admin can delete all recipes
        if self.user_type.can_delete_all_recipes:
            return True
        # Others can delete their own recipes if they can create recipes
        return self.user_type.can_create_recipes and recipe.user_id == self.id
    
    def can_manage_users(self):
        """Check if user can manage other users."""
        return self.user_type.can_manage_users if self.user_type else False
    
    def can_manage_system(self):
        """Check if user can manage system settings."""
        return self.user_type.can_manage_system if self.user_type else False
    
    def can_share_recipes(self):
        """Check if user can share recipes."""
        return self.user_type.can_share_recipes if self.user_type else False
    
    def is_admin(self):
        """Check if user is admin (backward compatibility)."""
        return self.user_type.name == 'admin' if self.user_type else False


class UserPreference(db.Model):
    """User preferences and settings."""
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    measurement_system = db.Column(db.Enum('metric', 'imperial'), default='imperial')
    dietary_restrictions = db.Column(JSON)
    allergens = db.Column(JSON)
    email_notifications = db.Column(db.Boolean, default=True)
    default_visibility = db.Column(db.Enum('private', 'public', 'unlisted'), default='private')
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
    unit = db.Column(db.String(50))
    preparation = db.Column(db.String(200))
    is_optional = db.Column(db.Boolean, default=False)
    notes = db.Column(Text)
    sort_order = db.Column(db.Integer, default=0)
    ingredient_group = db.Column(db.String(100))
    
    # Relationships
    recipe = db.relationship('Recipe', back_populates='recipe_ingredients')
    ingredient = db.relationship('Ingredient', back_populates='recipe_ingredients')
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'amount': self.amount or '',
            'unit': self.unit or '',
            'description': self.ingredient.name,
            'preparation': self.preparation or '',
            'is_optional': self.is_optional,
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
    visibility = db.Column(db.Enum('private', 'public', 'unlisted'), default='private')
    slug = db.Column(db.String(250), unique=True)
    meta_description = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = db.Column(db.DateTime)
    
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
    """Recipe tags."""
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(Text)
    tag_type = db.Column(db.Enum('cuisine', 'diet', 'meal_type', 'method', 'occasion', 'season', 'other'), default='other')
    icon = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    recipes = db.relationship('Recipe', secondary=recipe_tags, back_populates='tags')
    
    @property
    def recipe_count(self):
        """Get count of recipes with this tag."""
        return len(self.recipes)
    
    def __repr__(self):
        return f'<Tag {self.name}>'


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

