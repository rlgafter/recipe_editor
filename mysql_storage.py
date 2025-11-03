"""
MySQL Storage Implementation using SQLAlchemy.
Replaces JSON storage with MySQL database backend.
"""
import logging
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_

from db_models import (
    db, User, Recipe, RecipeIngredient, Ingredient, Tag, RecipeSource,
    RecipeFavorite, RecipeRating, Collection, CollectionRecipe,
    MealPlan, MealPlanRecipe, RecipeStats, UserStats, RecipeEmailLog
)

logger = logging.getLogger(__name__)


class MySQLStorage:
    """Storage implementation using MySQL database."""
    
    def __init__(self, db_session: Session = None):
        """Initialize storage with database session."""
        self.db = db_session or db.session
    
    # ========================================================================
    # RECIPE METHODS
    # ========================================================================
    
    def get_recipe(self, recipe_id: int, user_id: Optional[int] = None) -> Optional[Recipe]:
        """
        Get recipe by ID with permission check.
        
        Args:
            recipe_id: Recipe ID
            user_id: Current user ID (None for unauthenticated)
            
        Returns:
            Recipe object or None if not found/accessible
        """
        query = self.db.query(Recipe).options(
            joinedload(Recipe.owner),
            joinedload(Recipe.recipe_ingredients).joinedload(RecipeIngredient.ingredient),
            joinedload(Recipe.source),
            joinedload(Recipe.tags),
            joinedload(Recipe.stats)
        ).filter(Recipe.id == recipe_id)
        
        recipe = query.first()
        
        if not recipe:
            return None
        
        # Permission check using user types
        if not user_id:
            # Unauthenticated - only public recipes
            return recipe if recipe.visibility == 'public' else None
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # Admin can see everything
        if user.is_admin:
            return recipe
        
        # Public recipes are visible to all authenticated users
        if recipe.visibility == 'public':
            return recipe
        
        # Users can see their own recipes
        return recipe if recipe.user_id == user_id else None
    
    def get_all_recipes(self, user_id: Optional[int] = None) -> List[Recipe]:
        """
        Get all accessible recipes for a user.
        
        Args:
            user_id: Current user ID (None for unauthenticated)
            
        Returns:
            List of Recipe objects
        """
        if user_id:
            # Authenticated: show user's recipes + public recipes
            recipes = self.db.query(Recipe).filter(
                or_(
                    Recipe.user_id == user_id,
                    Recipe.visibility == 'public'
                )
            ).order_by(Recipe.updated_at.desc()).all()
        else:
            # Unauthenticated: only public recipes
            recipes = self.db.query(Recipe).filter(
                Recipe.visibility == 'public'
            ).order_by(Recipe.updated_at.desc()).all()
        
        return recipes
    
    def get_user_recipes(self, user_id: int, visibility: Optional[str] = None) -> List[Recipe]:
        """Get recipes owned by a specific user."""
        query = self.db.query(Recipe).filter(Recipe.user_id == user_id)
        
        if visibility:
            query = query.filter(Recipe.visibility == visibility)
        
        return query.order_by(Recipe.updated_at.desc()).all()
    
    def save_recipe(self, recipe_data: dict, user_id: int, recipe_id: Optional[int] = None) -> Recipe:
        """
        Save a recipe (create or update).
        
        Args:
            recipe_data: Dictionary with recipe information
            user_id: Owner user ID
            recipe_id: Existing recipe ID for updates, None for new
            
        Returns:
            Saved Recipe object
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise PermissionError("User not found")
        
        if recipe_id:
            # Update existing
            recipe = self.get_recipe(recipe_id, user_id)
            if not recipe:
                raise PermissionError("Recipe not found or access denied")
            
            if not user.can_edit_recipe(recipe):
                raise PermissionError("Cannot edit this recipe")
            
            recipe.name = recipe_data['name']
            recipe.description = recipe_data.get('description', '')
            recipe.instructions = recipe_data.get('instructions', '')
            recipe.notes = recipe_data.get('notes', '')
            recipe.prep_time = recipe_data.get('prep_time')
            recipe.cook_time = recipe_data.get('cook_time')
            recipe.servings = recipe_data.get('servings')
            recipe.difficulty = recipe_data.get('difficulty')
            recipe.visibility = recipe_data.get('visibility', 'private')
            recipe.ingredients_json = recipe_data.get('ingredients', [])  # Update ingredients JSON
            recipe.updated_at = datetime.utcnow()
            
            # Remove old ingredients
            for ri in recipe.recipe_ingredients:
                self.db.delete(ri)
        else:
            # Create new
            if not user.can_create_recipes():
                raise PermissionError("Cannot create recipes")
            
            recipe = Recipe(
                user_id=user_id,
                name=recipe_data['name'],
                description=recipe_data.get('description', ''),
                instructions=recipe_data.get('instructions', ''),
                notes=recipe_data.get('notes', ''),
                prep_time=recipe_data.get('prep_time'),
                cook_time=recipe_data.get('cook_time'),
                servings=recipe_data.get('servings'),
                difficulty=recipe_data.get('difficulty'),
                visibility=recipe_data.get('visibility', 'private'),
                ingredients_json=recipe_data.get('ingredients', [])  # Store ingredients as JSON
            )
            self.db.add(recipe)
            self.db.flush()  # Get recipe ID
        
        # Add ingredients
        for i, ing_data in enumerate(recipe_data.get('ingredients', [])):
            ingredient_name = ing_data.get('description', '').strip()
            if not ingredient_name:
                continue
            
            # Get or create ingredient
            ingredient = self.get_or_create_ingredient(ingredient_name)
            
            # Create recipe-ingredient relationship
            recipe_ing = RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id,
                amount=ing_data.get('amount', ''),
                unit=ing_data.get('unit', ''),
                notes=ing_data.get('notes', ''),
                sort_order=i
            )
            self.db.add(recipe_ing)
        
        # Update or create source
        source_data = recipe_data.get('source', {})
        if recipe.source:
            recipe.source.source_name = source_data.get('name', '')
            recipe.source.source_url = source_data.get('url', '')
            recipe.source.author = source_data.get('author', '')
            recipe.source.issue = source_data.get('issue', '')
        elif source_data.get('name'):
            source = RecipeSource(
                recipe_id=recipe.id,
                source_name=source_data.get('name', ''),
                source_url=source_data.get('url', ''),
                author=source_data.get('author', ''),
                issue=source_data.get('issue', '')
            )
            self.db.add(source)
        
        # Update tags
        recipe.tags.clear()
        for tag_name in recipe_data.get('tags', []):
            tag = self.get_or_create_tag(tag_name.upper().strip())
            recipe.tags.append(tag)
        
        self.db.commit()
        self.db.refresh(recipe)
        
        logger.info(f"Saved recipe {recipe.id}: {recipe.name}")
        return recipe
    
    def delete_recipe(self, recipe_id: int, user_id: int) -> bool:
        """
        Delete a recipe and cleanup orphaned tags.
        
        Args:
            recipe_id: Recipe ID to delete
            user_id: User requesting deletion
            
        Returns:
            True if deleted, False otherwise
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        recipe = self.get_recipe(recipe_id, user_id)
        if not recipe:
            return False
        
        if not user.can_delete_recipe(recipe):
            return False
        
        # Delete the recipe (cascade will remove recipe_tags associations)
        self.db.delete(recipe)
        self.db.commit()
        
        # Clean up orphaned tags (tags with no recipes)
        orphaned_tags = self.db.query(Tag).filter(
            ~Tag.recipes.any()
        ).all()
        
        if orphaned_tags:
            tag_names = [tag.name for tag in orphaned_tags]
            for tag in orphaned_tags:
                self.db.delete(tag)
            self.db.commit()
            logger.info(f"Deleted recipe {recipe_id} and cleaned up {len(orphaned_tags)} orphaned tags: {tag_names}")
        else:
            logger.info(f"Deleted recipe {recipe_id}")
        
        return True
    
    # ========================================================================
    # INGREDIENT METHODS
    # ========================================================================
    
    def get_or_create_ingredient(self, name: str) -> Ingredient:
        """Get existing ingredient or create new one."""
        name = name.strip().lower()
        
        # Search for exact match or alias match
        ingredient = self.db.query(Ingredient).filter(
            func.lower(Ingredient.name) == name
        ).first()
        
        if ingredient:
            return ingredient
        
        # Create new ingredient
        ingredient = Ingredient(
            name=name,
            is_common=False
        )
        self.db.add(ingredient)
        self.db.flush()
        
        logger.info(f"Created new ingredient: {name}")
        return ingredient
    
    def search_ingredients(self, query: str, limit: int = 20) -> List[Ingredient]:
        """Search ingredients by name."""
        query = query.strip()
        
        if not query:
            # Return common ingredients
            return self.db.query(Ingredient).filter(
                Ingredient.is_common == True
            ).order_by(Ingredient.name).limit(limit).all()
        
        # Search by name (case-insensitive)
        ingredients = self.db.query(Ingredient).filter(
            Ingredient.name.ilike(f'%{query}%')
        ).order_by(
            Ingredient.is_common.desc(),
            Ingredient.usage_count.desc(),
            Ingredient.name
        ).limit(limit).all()
        
        return ingredients
    
    def autocomplete_ingredients(self, partial: str, limit: int = 10) -> List[dict]:
        """Get ingredient suggestions for autocomplete."""
        ingredients = self.search_ingredients(partial, limit)
        
        return [
            {
                'id': ing.id,
                'name': ing.name,
                'category': ing.category,
                'is_common': ing.is_common
            }
            for ing in ingredients
        ]
    
    # ========================================================================
    # TAG METHODS
    # ========================================================================
    
    def get_all_tags(self) -> Dict[str, Dict]:
        """Get all tags with recipe counts."""
        from sqlalchemy import func
        from db_models import recipe_tags
        
        # Single query to get tag names and counts
        query = self.db.query(Tag.name, func.count(recipe_tags.c.recipe_id).label('count'))\
            .outerjoin(recipe_tags)\
            .group_by(Tag.id, Tag.name)\
            .all()
        
        return {tag_name: {'name': tag_name, 'count': count} for tag_name, count in query}
    
    def get_or_create_tag(self, name: str) -> Tag:
        """Get existing tag or create new one."""
        name = name.upper().strip()
        slug = name.lower().replace(' ', '-')
        
        tag = self.db.query(Tag).filter(Tag.name == name).first()
        
        if tag:
            return tag
        
        tag = Tag(name=name, slug=slug)
        self.db.add(tag)
        self.db.flush()
        
        logger.info(f"Created new tag: {name}")
        return tag
    
    def filter_recipes_by_tags(self, tag_names: List[str], match_all: bool = False, 
                               user_id: Optional[int] = None) -> List[Recipe]:
        """Filter recipes by tags."""
        if not tag_names:
            return self.get_all_recipes(user_id)
        
        # Get tag IDs
        tags = self.db.query(Tag).filter(Tag.name.in_(tag_names)).all()
        tag_ids = [tag.id for tag in tags]
        
        if not tag_ids:
            return []
        
        if match_all:
            # Must have ALL selected tags
            query = self.db.query(Recipe)
            
            for tag_id in tag_ids:
                query = query.filter(Recipe.tags.any(Tag.id == tag_id))
        else:
            # Must have ANY selected tag
            query = self.db.query(Recipe).filter(Recipe.tags.any(Tag.id.in_(tag_ids)))
        
        # Apply visibility filter
        if user_id:
            query = query.filter(or_(Recipe.user_id == user_id, Recipe.visibility == 'public'))
        else:
            query = query.filter(Recipe.visibility == 'public')
        
        return query.order_by(Recipe.updated_at.desc()).all()
    
    def delete_tag(self, tag_name: str) -> tuple[bool, str]:
        """Delete a tag if it has no recipes."""
        tag = self.db.query(Tag).filter(Tag.name == tag_name).first()
        
        if not tag:
            return False, f"Tag '{tag_name}' not found"
        
        if tag.recipe_count > 0:
            return False, f"Cannot delete tag '{tag_name}' - it has {tag.recipe_count} recipe(s)"
        
        self.db.delete(tag)
        self.db.commit()
        return True, f"Tag '{tag_name}' deleted"
    
    def update_tag_name(self, old_name: str, new_name: str) -> tuple[bool, str]:
        """Update a tag name."""
        tag = self.db.query(Tag).filter(Tag.name == old_name).first()
        
        if not tag:
            return False, f"Tag '{old_name}' not found"
        
        if tag.recipe_count > 0:
            return False, f"Cannot rename tag '{old_name}' - it has {tag.recipe_count} recipe(s)"
        
        new_name = new_name.upper().strip()
        tag.name = new_name
        tag.slug = new_name.lower().replace(' ', '-')
        
        self.db.commit()
        return True, f"Tag renamed to '{new_name}'"
    
    # ========================================================================
    # FAVORITE METHODS
    # ========================================================================
    
    def toggle_favorite(self, user_id: int, recipe_id: int) -> bool:
        """Toggle favorite status. Returns True if favorited, False if unfavorited."""
        favorite = self.db.query(RecipeFavorite).filter(
            RecipeFavorite.user_id == user_id,
            RecipeFavorite.recipe_id == recipe_id
        ).first()
        
        if favorite:
            # Remove favorite
            self.db.delete(favorite)
            self.db.commit()
            return False
        else:
            # Add favorite
            favorite = RecipeFavorite(user_id=user_id, recipe_id=recipe_id)
            self.db.add(favorite)
            self.db.commit()
            return True
    
    def get_user_favorites(self, user_id: int) -> List[Recipe]:
        """Get user's favorite recipes."""
        favorites = self.db.query(Recipe).join(RecipeFavorite).filter(
            RecipeFavorite.user_id == user_id
        ).order_by(RecipeFavorite.created_at.desc()).all()
        
        return favorites
    
    def is_favorited(self, user_id: int, recipe_id: int) -> bool:
        """Check if user has favorited a recipe."""
        favorite = self.db.query(RecipeFavorite).filter(
            RecipeFavorite.user_id == user_id,
            RecipeFavorite.recipe_id == recipe_id
        ).first()
        
        return favorite is not None
    
    # ========================================================================
    # COLLECTION METHODS
    # ========================================================================
    
    def create_collection(self, user_id: int, name: str, description: str = '') -> Collection:
        """Create a new collection."""
        collection = Collection(
            user_id=user_id,
            name=name,
            description=description
        )
        self.db.add(collection)
        self.db.commit()
        
        logger.info(f"Created collection '{name}' for user {user_id}")
        return collection
    
    def get_user_collections(self, user_id: int) -> List[Collection]:
        """Get user's collections."""
        return self.db.query(Collection).filter(
            Collection.user_id == user_id
        ).order_by(Collection.name).all()
    
    def add_recipe_to_collection(self, collection_id: int, recipe_id: int, user_id: int) -> bool:
        """Add recipe to collection."""
        # Verify ownership
        collection = self.db.query(Collection).filter(
            Collection.id == collection_id,
            Collection.user_id == user_id
        ).first()
        
        if not collection:
            return False
        
        # Check if already in collection
        existing = self.db.query(CollectionRecipe).filter(
            CollectionRecipe.collection_id == collection_id,
            CollectionRecipe.recipe_id == recipe_id
        ).first()
        
        if existing:
            return True  # Already added
        
        # Add to collection
        cr = CollectionRecipe(
            collection_id=collection_id,
            recipe_id=recipe_id,
            sort_order=len(collection.collection_recipes)
        )
        self.db.add(cr)
        self.db.commit()
        
        return True
    
    # ========================================================================
    # SEARCH & FILTER METHODS
    # ========================================================================
    
    def search_recipes(self, query: str, user_id: Optional[int] = None) -> List[Recipe]:
        """Full-text search for recipes."""
        search_query = self.db.query(Recipe)
        
        # Apply permission filter
        if user_id:
            search_query = search_query.filter(
                or_(Recipe.user_id == user_id, Recipe.visibility == 'public')
            )
        else:
            search_query = search_query.filter(Recipe.visibility == 'public')
        
        # Full-text search
        search_query = search_query.filter(
            or_(
                Recipe.name.ilike(f'%{query}%'),
                Recipe.description.ilike(f'%{query}%'),
                Recipe.instructions.ilike(f'%{query}%')
            )
        )
        
        return search_query.order_by(Recipe.updated_at.desc()).all()
    
    def find_recipes_by_ingredient(self, ingredient_name: str, user_id: Optional[int] = None) -> List[Recipe]:
        """Find all recipes containing a specific ingredient."""
        recipes = self.db.query(Recipe).join(RecipeIngredient).join(Ingredient).filter(
            func.lower(Ingredient.name) == ingredient_name.lower()
        )
        
        # Apply permission filter
        if user_id:
            recipes = recipes.filter(
                or_(Recipe.user_id == user_id, Recipe.visibility == 'public')
            )
        else:
            recipes = recipes.filter(Recipe.visibility == 'public')
        
        return recipes.distinct().all()
    
    # ========================================================================
    # STATISTICS METHODS
    # ========================================================================
    
    def increment_view_count(self, recipe_id: int):
        """Increment recipe view count."""
        stats = self.db.query(RecipeStats).filter(
            RecipeStats.recipe_id == recipe_id
        ).first()
        
        if stats:
            stats.view_count += 1
            stats.last_viewed_at = datetime.utcnow()
        else:
            stats = RecipeStats(recipe_id=recipe_id, view_count=1, last_viewed_at=datetime.utcnow())
            self.db.add(stats)
        
        self.db.commit()
    
    def log_email_share(self, recipe_id: int, user_id: Optional[int], 
                       recipient_email: str, recipient_name: str = '', message: str = ''):
        """Log an email share."""
        log_entry = RecipeEmailLog(
            recipe_id=recipe_id,
            sent_by_user_id=user_id,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            message=message
        )
        self.db.add(log_entry)
        
        # Update stats
        stats = self.db.query(RecipeStats).filter(
            RecipeStats.recipe_id == recipe_id
        ).first()
        
        if stats:
            stats.email_share_count += 1
        
        self.db.commit()
    
    def get_popular_recipes(self, limit: int = 10, user_id: Optional[int] = None) -> List[Recipe]:
        """Get popular recipes by favorites and ratings."""
        query = self.db.query(Recipe).join(RecipeStats).filter(
            Recipe.visibility == 'public'
        ).order_by(
            RecipeStats.favorite_count.desc(),
            RecipeStats.average_rating.desc()
        ).limit(limit)
        
        return query.all()


# Global storage instance (will be initialized by app)
mysql_storage = None


def init_storage(db_session):
    """Initialize global storage instance."""
    global mysql_storage
    mysql_storage = MySQLStorage(db_session)
    return mysql_storage

