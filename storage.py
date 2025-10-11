"""
Storage management for recipes and tags using JSON files.
"""
import json
import os
import logging
from typing import List, Optional, Dict, Any
from models import Recipe, Tag, Ingredient
import config

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages reading and writing recipes and tags to JSON files."""
    
    def __init__(self):
        """Initialize storage manager and ensure directories exist."""
        self._ensure_directories()
        self._ensure_tags_file()
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        os.makedirs(config.RECIPES_DIR, exist_ok=True)
        os.makedirs(config.LOGS_DIR, exist_ok=True)
        logger.info(f"Ensured directories exist: {config.RECIPES_DIR}, {config.LOGS_DIR}")
    
    def _ensure_tags_file(self):
        """Create tags file if it doesn't exist."""
        if not os.path.exists(config.TAGS_FILE):
            with open(config.TAGS_FILE, 'w') as f:
                json.dump({}, f)
            logger.info(f"Created tags file: {config.TAGS_FILE}")
    
    def _generate_recipe_id(self) -> str:
        """Generate a unique recipe ID."""
        existing_ids = []
        if os.path.exists(config.RECIPES_DIR):
            for filename in os.listdir(config.RECIPES_DIR):
                if filename.endswith('.json'):
                    recipe_id = filename[:-5]  # Remove .json extension
                    if recipe_id.startswith('recipe_'):
                        try:
                            num = int(recipe_id.split('_')[1])
                            existing_ids.append(num)
                        except (IndexError, ValueError):
                            continue
        
        next_id = max(existing_ids) + 1 if existing_ids else 1
        return f"recipe_{next_id:03d}"
    
    def _get_recipe_filepath(self, recipe_id: str) -> str:
        """Get the full filepath for a recipe JSON file."""
        return os.path.join(config.RECIPES_DIR, f"{recipe_id}.json")
    
    def save_recipe(self, recipe: Recipe) -> Recipe:
        """
        Save a recipe to disk. If recipe has no ID, generates one.
        Returns the saved recipe with its ID.
        """
        if not recipe.id:
            recipe.id = self._generate_recipe_id()
            logger.info(f"Generated new recipe ID: {recipe.id}")
        
        filepath = self._get_recipe_filepath(recipe.id)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(recipe.to_dict(), f, indent=2)
            logger.info(f"Saved recipe {recipe.id}: {recipe.name}")
            
            # Update tags
            self._update_tags_for_recipe(recipe)
            
            return recipe
        except Exception as e:
            logger.error(f"Error saving recipe {recipe.id}: {str(e)}")
            raise
    
    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        """Load a recipe from disk by ID."""
        filepath = self._get_recipe_filepath(recipe_id)
        
        if not os.path.exists(filepath):
            logger.warning(f"Recipe not found: {recipe_id}")
            return None
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            recipe = Recipe.from_dict(data)
            logger.debug(f"Loaded recipe {recipe_id}: {recipe.name}")
            return recipe
        except Exception as e:
            logger.error(f"Error loading recipe {recipe_id}: {str(e)}")
            return None
    
    def get_all_recipes(self) -> List[Recipe]:
        """Load all recipes from disk."""
        recipes = []
        
        if not os.path.exists(config.RECIPES_DIR):
            return recipes
        
        for filename in sorted(os.listdir(config.RECIPES_DIR)):
            if filename.endswith('.json'):
                recipe_id = filename[:-5]
                recipe = self.get_recipe(recipe_id)
                if recipe:
                    recipes.append(recipe)
        
        logger.info(f"Loaded {len(recipes)} recipes")
        return recipes
    
    def delete_recipe(self, recipe_id: str) -> bool:
        """Delete a recipe from disk and update tags."""
        filepath = self._get_recipe_filepath(recipe_id)
        
        if not os.path.exists(filepath):
            logger.warning(f"Cannot delete, recipe not found: {recipe_id}")
            return False
        
        # Get recipe tags before deleting
        recipe = self.get_recipe(recipe_id)
        
        try:
            os.remove(filepath)
            logger.info(f"Deleted recipe {recipe_id}")
            
            # Remove recipe from all tags
            if recipe:
                self._remove_recipe_from_tags(recipe_id, recipe.tags)
            
            return True
        except Exception as e:
            logger.error(f"Error deleting recipe {recipe_id}: {str(e)}")
            return False
    
    def _update_tags_for_recipe(self, recipe: Recipe):
        """Update tag associations for a recipe."""
        try:
            # Load current tags
            with open(config.TAGS_FILE, 'r') as f:
                tags_data = json.load(f)
            
            # Remove recipe from all tags first
            for tag_name in list(tags_data.keys()):
                if recipe.id in tags_data[tag_name].get('recipes', []):
                    tags_data[tag_name]['recipes'].remove(recipe.id)
                    # Remove tag if no recipes remain
                    if not tags_data[tag_name]['recipes']:
                        del tags_data[tag_name]
            
            # Add recipe to its current tags
            for tag_name in recipe.tags:
                tag_name = tag_name.lower().strip()
                if tag_name:
                    if tag_name not in tags_data:
                        tag = Tag(tag_name)
                        tags_data[tag_name] = tag.to_dict()
                    
                    if recipe.id not in tags_data[tag_name]['recipes']:
                        tags_data[tag_name]['recipes'].append(recipe.id)
            
            # Save updated tags
            with open(config.TAGS_FILE, 'w') as f:
                json.dump(tags_data, f, indent=2)
            
            logger.debug(f"Updated tags for recipe {recipe.id}")
        except Exception as e:
            logger.error(f"Error updating tags for recipe {recipe.id}: {str(e)}")
            raise
    
    def _remove_recipe_from_tags(self, recipe_id: str, tag_names: List[str]):
        """Remove a recipe from specified tags."""
        try:
            with open(config.TAGS_FILE, 'r') as f:
                tags_data = json.load(f)
            
            for tag_name in tag_names:
                tag_name = tag_name.lower().strip()
                if tag_name in tags_data:
                    if recipe_id in tags_data[tag_name].get('recipes', []):
                        tags_data[tag_name]['recipes'].remove(recipe_id)
                    
                    # Remove tag if no recipes remain
                    if not tags_data[tag_name]['recipes']:
                        del tags_data[tag_name]
                        logger.info(f"Removed empty tag: {tag_name}")
            
            with open(config.TAGS_FILE, 'w') as f:
                json.dump(tags_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error removing recipe {recipe_id} from tags: {str(e)}")
    
    def get_all_tags(self) -> Dict[str, Tag]:
        """Load all tags from disk."""
        try:
            with open(config.TAGS_FILE, 'r') as f:
                tags_data = json.load(f)
            
            tags = {}
            for tag_name, tag_data in tags_data.items():
                tags[tag_name] = Tag.from_dict(tag_name, tag_data)
            
            logger.debug(f"Loaded {len(tags)} tags")
            return tags
        except Exception as e:
            logger.error(f"Error loading tags: {str(e)}")
            return {}
    
    def get_tag(self, tag_name: str) -> Optional[Tag]:
        """Get a specific tag by name."""
        tag_name = tag_name.lower().strip()
        tags = self.get_all_tags()
        return tags.get(tag_name)
    
    def update_tag_name(self, old_name: str, new_name: str) -> tuple[bool, str]:
        """
        Update a tag's name. Only allowed if tag has no recipes.
        Returns (success, error_message)
        """
        old_name = old_name.lower().strip()
        new_name = new_name.lower().strip()
        
        if not new_name:
            return False, "Tag name cannot be empty"
        
        if old_name == new_name:
            return True, ""  # No change needed
        
        try:
            with open(config.TAGS_FILE, 'r') as f:
                tags_data = json.load(f)
            
            if old_name not in tags_data:
                return False, f"Tag '{old_name}' not found"
            
            if tags_data[old_name].get('recipes'):
                return False, "Cannot rename tag that has recipes associated"
            
            if new_name in tags_data:
                return False, f"Tag '{new_name}' already exists"
            
            # Rename tag
            tags_data[new_name] = tags_data[old_name]
            del tags_data[old_name]
            
            with open(config.TAGS_FILE, 'w') as f:
                json.dump(tags_data, f, indent=2)
            
            logger.info(f"Renamed tag '{old_name}' to '{new_name}'")
            return True, ""
        except Exception as e:
            logger.error(f"Error renaming tag: {str(e)}")
            return False, "Error updating tag"
    
    def delete_tag(self, tag_name: str) -> tuple[bool, str]:
        """
        Delete a tag. Only allowed if tag has no recipes.
        Returns (success, error_message)
        """
        tag_name = tag_name.lower().strip()
        
        try:
            with open(config.TAGS_FILE, 'r') as f:
                tags_data = json.load(f)
            
            if tag_name not in tags_data:
                return False, f"Tag '{tag_name}' not found"
            
            if tags_data[tag_name].get('recipes'):
                return False, "Cannot delete tag that has recipes associated"
            
            del tags_data[tag_name]
            
            with open(config.TAGS_FILE, 'w') as f:
                json.dump(tags_data, f, indent=2)
            
            logger.info(f"Deleted tag '{tag_name}'")
            return True, ""
        except Exception as e:
            logger.error(f"Error deleting tag: {str(e)}")
            return False, "Error deleting tag"
    
    def filter_recipes_by_tags(self, tag_names: List[str], match_all: bool = False) -> List[Recipe]:
        """
        Filter recipes by tags.
        
        Args:
            tag_names: List of tag names to filter by
            match_all: If True, recipe must have ALL tags. If False, recipe must have ANY tag.
        
        Returns:
            List of matching recipes
        """
        if not tag_names:
            return self.get_all_recipes()
        
        tag_names = [name.lower().strip() for name in tag_names]
        all_recipes = self.get_all_recipes()
        
        if match_all:
            # Recipe must have all specified tags
            return [r for r in all_recipes if all(tag in r.tags for tag in tag_names)]
        else:
            # Recipe must have at least one of the specified tags
            return [r for r in all_recipes if any(tag in r.tags for tag in tag_names)]


# Global storage instance
storage = StorageManager()

