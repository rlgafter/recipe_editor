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
        
        # Users can see their own recipes (if not soft-deleted)
        if recipe.user_id == user_id:
            return recipe if recipe.deleted_at is None else None
        
        # Check if recipe is shared with user (public recipes must be explicitly shared)
        from db_models import RecipeShare, Friendship
        # First check if there's a share
        share = self.db.query(RecipeShare).filter(
            RecipeShare.recipe_id == recipe_id,
            RecipeShare.shared_with_user_id == user_id
        ).first()
        
        # If share exists, verify friendship still exists
        if share:
            friendship = self.db.query(Friendship).filter(
                or_(
                    ((Friendship.user1_id == share.shared_by_user_id) & (Friendship.user2_id == user_id)),
                    ((Friendship.user1_id == user_id) & (Friendship.user2_id == share.shared_by_user_id))
                )
            ).first()
            
            if friendship and recipe.visibility == 'public':
                return recipe  # Shared recipe is visible even if soft-deleted by owner
        
        if share:
            return recipe  # Shared recipe is visible even if soft-deleted by owner
        
        # Users can see their own recipes (if not soft-deleted)
        if recipe.user_id == user_id:
            return recipe if recipe.deleted_at is None else None
        
        return None
    
    def get_all_recipes(self, user_id: Optional[int] = None) -> List[Recipe]:
        """
        Get all accessible recipes for a user (own recipes and shared recipes only).
        Public recipes are NOT automatically visible - they must be explicitly shared.
        
        Args:
            user_id: Current user ID (None for unauthenticated)
            
        Returns:
            List of Recipe objects
        """
        from db_models import RecipeShare, Friendship
        
        if user_id:
            # Authenticated: show user's own recipes + recipes shared with them
            # Get recipes shared with user
            shared_recipe_ids = self.db.query(RecipeShare.recipe_id).join(
                Friendship,
                or_(
                    ((Friendship.user1_id == RecipeShare.shared_by_user_id) & (Friendship.user2_id == user_id)),
                    ((Friendship.user1_id == user_id) & (Friendship.user2_id == RecipeShare.shared_by_user_id))
                )
            ).filter(
                RecipeShare.shared_with_user_id == user_id
            ).distinct()
            
            # Build main query - only own recipes and shared recipes
            query = self.db.query(Recipe).filter(
                or_(
                    # User's own recipes (excluding soft-deleted ones)
                    and_(
                        Recipe.user_id == user_id,
                        Recipe.deleted_at.is_(None)
                    ),
                    # Recipes shared with user (including soft-deleted ones if shared)
                    and_(
                        Recipe.id.in_(shared_recipe_ids),
                        Recipe.visibility == 'public'  # Only public recipes can be shared
                    )
                )
            ).order_by(Recipe.updated_at.desc())
            
            # Execute and remove duplicates
            all_recipes = query.all()
            seen = set()
            unique_recipes = []
            for recipe in all_recipes:
                if recipe.id not in seen:
                    seen.add(recipe.id)
                    unique_recipes.append(recipe)
            
            return unique_recipes
        else:
            # Unauthenticated: no recipes visible (redirected to home page)
            return []
    
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
            # Update URL confidence fields if present
            if 'url_confidence' in source_data:
                recipe.source.source_url_confidence = source_data.get('url_confidence')
            if 'url_detection_method' in source_data:
                recipe.source.source_url_detection_method = source_data.get('url_detection_method', 'manual')
        elif source_data.get('name'):
            source = RecipeSource(
                recipe_id=recipe.id,
                source_name=source_data.get('name', ''),
                source_url=source_data.get('url', ''),
                author=source_data.get('author', ''),
                issue=source_data.get('issue', ''),
                source_url_confidence=source_data.get('url_confidence'),
                source_url_detection_method=source_data.get('url_detection_method', 'manual')
            )
            self.db.add(source)
        
        # Check if recipe is being converted to public
        old_visibility = recipe.visibility if recipe_id else None
        new_visibility = recipe_data.get('visibility', 'private')
        converting_to_public = (old_visibility != 'public' and new_visibility == 'public')
        
        # Update tags
        recipe.tags.clear()
        personal_tag_names = []
        
        for tag_name in recipe_data.get('tags', []):
            tag_name = tag_name.lower().strip()  # Normalize to lowercase
            tag = self.get_or_create_tag(tag_name, user_id, 'personal')
            
            # If converting to public and tag is personal, save name for notes
            if converting_to_public and tag.is_personal:
                personal_tag_names.append(tag.name)
            else:
                recipe.tags.append(tag)
        
        # If converting to public and there are personal tags, add to notes
        if converting_to_public and personal_tag_names:
            personal_tags_note = f"\n\nPersonal Tags: {', '.join(personal_tag_names)}\n"
            recipe.notes = (recipe.notes or '').strip() + personal_tags_note
            logger.info(f"Converted {len(personal_tag_names)} personal tags to notes for public recipe")
        
        self.db.commit()
        self.db.refresh(recipe)
        
        # Cleanup orphaned personal tags for this user
        self.cleanup_orphaned_tags(user_id)
        
        logger.info(f"Saved recipe {recipe.id}: {recipe.name}")
        return recipe
    
    def delete_recipe(self, recipe_id: int, user_id: int) -> bool:
        """
        Delete a recipe (soft delete if has shares, hard delete otherwise) and cleanup orphaned tags.
        
        Args:
            recipe_id: Recipe ID to delete
            user_id: User requesting deletion
            
        Returns:
            True if deleted, False otherwise
        """
        from db_models import RecipeShare
        from datetime import datetime
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        recipe = self.get_recipe(recipe_id, user_id)
        if not recipe:
            return False
        
        if not user.can_delete_recipe(recipe):
            return False
        
        # Check if recipe has active shares
        has_shares = self.db.query(RecipeShare).filter(
            RecipeShare.recipe_id == recipe_id
        ).first() is not None
        
        if has_shares:
            # Soft delete: mark as deleted but keep in database for recipients
            recipe.deleted_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"Soft deleted recipe {recipe_id} (has active shares)")
        else:
            # Hard delete: actually remove from database
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
    
    def get_all_tags(self, user_id: Optional[int] = None) -> Dict[str, Dict]:
        """
        Get all tags available to a user with recipe counts.
        Returns system tags + user's personal tags.
        
        Args:
            user_id: User ID (None for system tags only, e.g., for admin viewing all)
            
        Returns:
            Dict mapping tag_name to tag info dict
        """
        from sqlalchemy import func
        from db_models import recipe_tags
        
        if user_id is None:
            # Return all tags (for admin interface)
            query = self.db.query(Tag, func.count(recipe_tags.c.recipe_id).label('count'))\
                .outerjoin(recipe_tags)\
                .group_by(Tag.id)\
                .all()
            
            return {
                tag.name: {
                    'id': tag.id,
                    'name': tag.name,
                    'count': count,
                    'scope': tag.tag_scope,
                    'user_id': tag.user_id,
                    'recipe_count': count
                } 
                for tag, count in query
            }
        
        # Get system tags + user's personal tags
        query = self.db.query(Tag, func.count(recipe_tags.c.recipe_id).label('count'))\
            .outerjoin(recipe_tags)\
            .filter(
                or_(
                    Tag.tag_scope == 'system',
                    and_(Tag.tag_scope == 'personal', Tag.user_id == user_id)
                )
            )\
            .group_by(Tag.id)\
            .all()
        
        return {
            tag.name: {
                'id': tag.id,
                'name': tag.name,
                'count': count,
                'scope': tag.tag_scope,
                'recipe_count': count
            } 
            for tag, count in query
        }
    
    def get_or_create_tag(self, name: str, user_id: int, tag_scope: str = 'personal') -> Tag:
        """
        Get existing tag or create new one.
        
        Args:
            name: Tag name
            user_id: User ID (for personal tags) or None (for system tags)
            tag_scope: 'system' or 'personal' (default: 'personal')
            
        Returns:
            Tag object
        """
        name = name.lower().strip()  # Normalize to lowercase
        slug = name.replace(' ', '-')
        
        # Look for existing tag (case-insensitive match for backward compatibility)
        if tag_scope == 'system':
            # System tags: match by name and scope only (case-insensitive)
            tag = self.db.query(Tag).filter(
                func.lower(Tag.name) == name,
                Tag.tag_scope == 'system'
            ).first()
        else:
            # Personal tags: match by name, user_id, and scope (case-insensitive)
            tag = self.db.query(Tag).filter(
                func.lower(Tag.name) == name,
                Tag.user_id == user_id,
                Tag.tag_scope == 'personal'
            ).first()
        
        if tag:
            return tag
        
        # Create new tag
        tag = Tag(
            name=name, 
            slug=slug,
            tag_scope=tag_scope,
            user_id=user_id if tag_scope == 'personal' else None
        )
        self.db.add(tag)
        self.db.flush()
        
        logger.info(f"Created new {tag_scope} tag: {name}" + (f" for user {user_id}" if tag_scope == 'personal' else ""))
        return tag
    
    def filter_recipes_by_tags(self, tag_names: List[str], match_all: bool = False, 
                               user_id: Optional[int] = None) -> List[Recipe]:
        """
        Filter recipes by tags.
        
        Args:
            tag_names: List of tag names to filter by
            match_all: If True, recipes must have ALL tags; if False, ANY tag
            user_id: Current user ID (used to resolve personal vs system tags)
            
        Returns:
            List of Recipe objects matching the filter
        """
        if not tag_names:
            return self.get_all_recipes(user_id)
        
        # Normalize tag names to lowercase for case-insensitive matching
        normalized_tag_names = [name.lower().strip() for name in tag_names]
        
        # Get tag IDs - look for system tags + user's personal tags (case-insensitive)
        if user_id:
            tags = self.db.query(Tag).filter(
                func.lower(Tag.name).in_(normalized_tag_names),
                or_(
                    Tag.tag_scope == 'system',
                    and_(Tag.tag_scope == 'personal', Tag.user_id == user_id)
                )
            ).all()
        else:
            # Unauthenticated users can only see system tags
            tags = self.db.query(Tag).filter(
                func.lower(Tag.name).in_(normalized_tag_names),
                Tag.tag_scope == 'system'
            ).all()
        
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
        
        # Apply visibility filter - only own recipes and shared recipes
        if user_id:
            # Get recipes shared with user
            from db_models import RecipeShare, Friendship
            shared_recipe_ids = self.db.query(RecipeShare.recipe_id).join(
                Friendship,
                or_(
                    ((Friendship.user1_id == RecipeShare.shared_by_user_id) & (Friendship.user2_id == user_id)),
                    ((Friendship.user1_id == user_id) & (Friendship.user2_id == RecipeShare.shared_by_user_id))
                )
            ).filter(
                RecipeShare.shared_with_user_id == user_id
            ).distinct()
            
            # Only show own recipes or shared recipes
            query = query.filter(
                or_(
                    Recipe.user_id == user_id,
                    Recipe.id.in_(shared_recipe_ids)
                )
            )
        else:
            # Unauthenticated: no recipes visible
            return []
        
        return query.order_by(Recipe.updated_at.desc()).all()
    
    def search_recipes(self, search_term: str, tag_names: Optional[List[str]] = None, 
                      match_all_tags: bool = False, user_id: Optional[int] = None) -> List[Recipe]:
        """
        Search recipes by term across multiple fields.
        
        Args:
            search_term: Search query string (multi-word searches use AND logic)
            tag_names: Optional list of tag names to filter by
            match_all_tags: If True, recipe must have ALL tags; if False, ANY tag
            user_id: Current user ID (None for unauthenticated)
            
        Returns:
            List of Recipe objects matching the search and filters
        """
        # Start with base query
        query = self.db.query(Recipe).options(
            joinedload(Recipe.owner),
            joinedload(Recipe.source),
            joinedload(Recipe.tags)
        )
        
        # Apply search term filter
        if search_term and search_term.strip():
            # Split search term into words for AND logic
            search_words = search_term.strip().split()
            
            for word in search_words:
                # Case-insensitive partial matching across multiple fields
                word_pattern = f"%{word}%"
                
                # Create OR condition for this word across all searchable fields
                word_condition = or_(
                    Recipe.name.ilike(word_pattern),
                    Recipe.description.ilike(word_pattern),
                    Recipe.instructions.ilike(word_pattern),
                    Recipe.notes.ilike(word_pattern),
                    # Search in ingredients JSON (cast to text for searching)
                    func.cast(Recipe.ingredients_json, db.Text).ilike(word_pattern),
                    # Search in tag names
                    Recipe.tags.any(Tag.name.ilike(word_pattern))
                )
                
                # Apply AND logic: recipe must match ALL search words
                query = query.filter(word_condition)
        
        # Apply tag filter if specified
        if tag_names:
            # Normalize tag names to lowercase for case-insensitive matching
            normalized_tag_names = [name.lower().strip() for name in tag_names]
            
            # Get tags considering user_id (system + user's personal tags) (case-insensitive)
            if user_id:
                tags = self.db.query(Tag).filter(
                    func.lower(Tag.name).in_(normalized_tag_names),
                    or_(
                        Tag.tag_scope == 'system',
                        and_(Tag.tag_scope == 'personal', Tag.user_id == user_id)
                    )
                ).all()
            else:
                tags = self.db.query(Tag).filter(
                    func.lower(Tag.name).in_(normalized_tag_names),
                    Tag.tag_scope == 'system'
                ).all()
            
            tag_ids = [tag.id for tag in tags]
            
            if tag_ids:
                if match_all_tags:
                    # Must have ALL selected tags
                    for tag_id in tag_ids:
                        query = query.filter(Recipe.tags.any(Tag.id == tag_id))
                else:
                    # Must have ANY selected tag
                    query = query.filter(Recipe.tags.any(Tag.id.in_(tag_ids)))
        
        # Apply visibility filter - only own recipes and shared recipes
        if user_id:
            # Get recipes shared with user
            from db_models import RecipeShare, Friendship
            shared_recipe_ids = self.db.query(RecipeShare.recipe_id).join(
                Friendship,
                or_(
                    ((Friendship.user1_id == RecipeShare.shared_by_user_id) & (Friendship.user2_id == user_id)),
                    ((Friendship.user1_id == user_id) & (Friendship.user2_id == RecipeShare.shared_by_user_id))
                )
            ).filter(
                RecipeShare.shared_with_user_id == user_id
            ).distinct()
            
            # Only show own recipes or shared recipes
            query = query.filter(
                or_(
                    Recipe.user_id == user_id,
                    Recipe.id.in_(shared_recipe_ids)
                )
            )
        else:
            # Unauthenticated: no recipes visible
            return []
        
        return query.order_by(Recipe.updated_at.desc()).all()
    
    def delete_tag(self, tag_id: int) -> tuple[bool, str]:
        """
        Delete a tag by ID (admin function).
        System tags cannot be deleted.
        
        Args:
            tag_id: Tag ID to delete
            
        Returns:
            Tuple of (success, message)
        """
        tag = self.db.query(Tag).filter(Tag.id == tag_id).first()
        
        if not tag:
            return False, "Tag not found"
        
        # System tags cannot be deleted
        if tag.tag_scope == 'system':
            return False, f"Cannot delete system tag '{tag.name}'. System tags are permanent."
        
        tag_name = tag.name
        scope = tag.tag_scope
        
        # Allow deletion of personal tags even if in use (admin override)
        self.db.delete(tag)
        self.db.commit()
        
        logger.info(f"Deleted {scope} tag: {tag_name} (ID: {tag_id})")
        return True, f"Tag '{tag_name}' deleted successfully"
    
    def update_tag(self, tag_id: int, new_name: Optional[str] = None, 
                   new_scope: Optional[str] = None) -> tuple[bool, str]:
        """
        Update a tag's properties (admin function).
        
        Args:
            tag_id: Tag ID to update
            new_name: New name (optional)
            new_scope: New scope ('system' or 'personal', optional)
            
        Returns:
            Tuple of (success, message)
        """
        tag = self.db.query(Tag).filter(Tag.id == tag_id).first()
        
        if not tag:
            return False, "Tag not found"
        
        old_name = tag.name
        
        if new_name:
            new_name = new_name.upper().strip()
            tag.name = new_name
            tag.slug = new_name.lower().replace(' ', '-')
        
        if new_scope and new_scope in ('system', 'personal'):
            old_scope = tag.tag_scope
            tag.tag_scope = new_scope
            
            # If converting to system, remove user_id
            if new_scope == 'system':
                tag.user_id = None
        
        self.db.commit()
        
        logger.info(f"Updated tag {old_name} (ID: {tag_id})")
        return True, f"Tag updated successfully"
    
    def convert_personal_to_system_tag(self, tag_name: str) -> tuple[bool, str]:
        """
        Convert all personal tags with a given name to a single system tag.
        Merges all personal tags with the same name into one system tag.
        
        Args:
            tag_name: Name of the tag to convert
            
        Returns:
            Tuple of (success, message)
        """
        tag_name = tag_name.upper().strip()
        
        # Find all personal tags with this name
        personal_tags = self.db.query(Tag).filter(
            Tag.name == tag_name,
            Tag.tag_scope == 'personal'
        ).all()
        
        if not personal_tags:
            return False, f"No personal tags found with name '{tag_name}'"
        
        # Check if system tag already exists
        system_tag = self.db.query(Tag).filter(
            Tag.name == tag_name,
            Tag.tag_scope == 'system'
        ).first()
        
        if not system_tag:
            # Create new system tag
            slug = tag_name.lower().replace(' ', '-')
            system_tag = Tag(
                name=tag_name,
                slug=slug,
                tag_scope='system',
                user_id=None
            )
            self.db.add(system_tag)
            self.db.flush()
            logger.info(f"Created new system tag: {tag_name}")
        
        # Update all recipe associations to point to system tag
        from db_models import recipe_tags
        
        for personal_tag in personal_tags:
            # Get all recipes using this personal tag
            recipes = personal_tag.recipes
            
            for recipe in recipes:
                # Remove personal tag
                if personal_tag in recipe.tags:
                    recipe.tags.remove(personal_tag)
                
                # Add system tag if not already present
                if system_tag not in recipe.tags:
                    recipe.tags.append(system_tag)
            
            # Delete the personal tag
            self.db.delete(personal_tag)
        
        self.db.commit()
        
        count = len(personal_tags)
        logger.info(f"Converted {count} personal '{tag_name}' tags to system tag")
        return True, f"Converted {count} personal tag(s) to system tag '{tag_name}'"
    
    def cleanup_orphaned_tags(self, user_id: Optional[int] = None) -> int:
        """
        Delete tags with no associated recipes.
        System tags are NEVER deleted, even if orphaned.
        
        Args:
            user_id: If provided, only cleanup this user's personal tags
            
        Returns:
            Number of tags deleted
        """
        if user_id:
            # Cleanup only user's personal tags
            orphaned = self.db.query(Tag).filter(
                Tag.user_id == user_id,
                Tag.tag_scope == 'personal',
                ~Tag.recipes.any()
            ).all()
        else:
            # Cleanup all orphaned PERSONAL tags only (admin function)
            # System tags are never deleted, even if orphaned
            orphaned = self.db.query(Tag).filter(
                Tag.tag_scope == 'personal',
                ~Tag.recipes.any()
            ).all()
        
        count = len(orphaned)
        
        for tag in orphaned:
            self.db.delete(tag)
        
        if count > 0:
            self.db.commit()
            logger.info(f"Cleaned up {count} orphaned personal tags" + (f" for user {user_id}" if user_id else ""))
        
        return count
    
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
    
    def find_recipes_by_ingredient(self, ingredient_name: str, user_id: Optional[int] = None) -> List[Recipe]:
        """Find all recipes containing a specific ingredient (only own and shared recipes)."""
        recipes = self.db.query(Recipe).join(RecipeIngredient).join(Ingredient).filter(
            func.lower(Ingredient.name) == ingredient_name.lower()
        )
        
        # Apply permission filter - only own recipes and shared recipes
        if user_id:
            # Get recipes shared with user
            from db_models import RecipeShare, Friendship
            shared_recipe_ids = self.db.query(RecipeShare.recipe_id).join(
                Friendship,
                or_(
                    ((Friendship.user1_id == RecipeShare.shared_by_user_id) & (Friendship.user2_id == user_id)),
                    ((Friendship.user1_id == user_id) & (Friendship.user2_id == RecipeShare.shared_by_user_id))
                )
            ).filter(
                RecipeShare.shared_with_user_id == user_id
            ).distinct()
            
            recipes = recipes.filter(
                or_(
                    Recipe.user_id == user_id,
                    Recipe.id.in_(shared_recipe_ids)
                )
            )
        else:
            # Unauthenticated: no recipes visible
            return []
        
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

