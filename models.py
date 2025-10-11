"""
Data models for Recipe and Tag entities.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
import re


class Ingredient:
    """Represents a single ingredient in a recipe."""
    
    def __init__(self, amount: str = "", unit: str = "", description: str = ""):
        self.amount = amount.strip()
        self.unit = unit.strip()
        self.description = description.strip()
    
    def to_dict(self) -> Dict[str, str]:
        """Convert ingredient to dictionary format."""
        return {
            "amount": self.amount,
            "unit": self.unit,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'Ingredient':
        """Create ingredient from dictionary."""
        return cls(
            amount=data.get("amount", ""),
            unit=data.get("unit", ""),
            description=data.get("description", "")
        )
    
    def is_valid(self) -> bool:
        """Validate ingredient has at least a description."""
        return bool(self.description.strip())
    
    def __str__(self) -> str:
        """Format ingredient as string."""
        parts = []
        if self.amount:
            parts.append(self.amount)
        if self.unit:
            parts.append(self.unit)
        parts.append(self.description)
        return " ".join(parts)


class Recipe:
    """Represents a recipe with all its details."""
    
    def __init__(
        self,
        name: str,
        ingredients: List[Ingredient],
        instructions: str = "",
        notes: str = "",
        tags: List[str] = None,
        recipe_id: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        user_id: Optional[str] = None,
        rating: Optional[float] = None,
        favorites: List[str] = None
    ):
        self.id = recipe_id
        self.name = name.strip()
        self.ingredients = ingredients or []
        self.instructions = instructions.strip()
        self.notes = notes.strip()
        self.tags = [tag.upper().strip() for tag in (tags or [])]
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
        self.user_id = user_id
        self.rating = rating
        self.favorites = favorites or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert recipe to dictionary format for JSON storage."""
        return {
            "id": self.id,
            "name": self.name,
            "ingredients": [ing.to_dict() for ing in self.ingredients],
            "instructions": self.instructions,
            "notes": self.notes,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "user_id": self.user_id,
            "rating": self.rating,
            "favorites": self.favorites
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Recipe':
        """Create recipe from dictionary."""
        ingredients = [
            Ingredient.from_dict(ing) for ing in data.get("ingredients", [])
        ]
        return cls(
            name=data.get("name", ""),
            ingredients=ingredients,
            instructions=data.get("instructions", ""),
            notes=data.get("notes", ""),
            tags=data.get("tags", []),
            recipe_id=data.get("id"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            user_id=data.get("user_id"),
            rating=data.get("rating"),
            favorites=data.get("favorites", [])
        )
    
    def validate(self) -> tuple[bool, List[str]]:
        """
        Validate recipe data.
        Returns (is_valid, error_messages)
        """
        errors = []
        
        if not self.name:
            errors.append("Recipe name is required")
        
        if not self.ingredients:
            errors.append("At least one ingredient is required")
        else:
            valid_ingredients = [ing for ing in self.ingredients if ing.is_valid()]
            if not valid_ingredients:
                errors.append("At least one ingredient with a description is required")
        
        # Validate amount field if present (should be numeric or fraction)
        for i, ing in enumerate(self.ingredients):
            if ing.amount and not self._is_valid_amount(ing.amount):
                errors.append(f"Ingredient {i+1}: Invalid amount '{ing.amount}'. Use numbers or fractions (e.g., 1/2, 2.5)")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def _is_valid_amount(amount: str) -> bool:
        """Validate amount is a number or fraction."""
        amount = amount.strip()
        if not amount:
            return True
        
        # Check for simple number (integer or decimal)
        if re.match(r'^\d+\.?\d*$', amount):
            value = float(amount)
            return 0 <= value <= 1000
        
        # Check for fraction (e.g., 1/2, 3/4)
        if re.match(r'^\d+/\d+$', amount):
            parts = amount.split('/')
            numerator = int(parts[0])
            denominator = int(parts[1])
            if denominator == 0:
                return False
            value = numerator / denominator
            return 0 <= value <= 1000
        
        # Check for mixed number (e.g., 1 1/2)
        if re.match(r'^\d+\s+\d+/\d+$', amount):
            parts = amount.split()
            whole = int(parts[0])
            frac_parts = parts[1].split('/')
            numerator = int(frac_parts[0])
            denominator = int(frac_parts[1])
            if denominator == 0:
                return False
            value = whole + (numerator / denominator)
            return 0 <= value <= 1000
        
        return False
    
    def update_timestamp(self):
        """Update the updated_at timestamp to current time."""
        self.updated_at = datetime.now().isoformat()


class Tag:
    """Represents a tag that can be associated with recipes."""
    
    def __init__(self, name: str, recipes: List[str] = None, created_at: Optional[str] = None):
        self.name = name.upper().strip()
        self.recipes = recipes or []
        self.created_at = created_at or datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tag to dictionary format."""
        return {
            "recipes": self.recipes,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> 'Tag':
        """Create tag from dictionary."""
        return cls(
            name=name,
            recipes=data.get("recipes", []),
            created_at=data.get("created_at")
        )
    
    def add_recipe(self, recipe_id: str):
        """Add a recipe to this tag."""
        if recipe_id not in self.recipes:
            self.recipes.append(recipe_id)
    
    def remove_recipe(self, recipe_id: str):
        """Remove a recipe from this tag."""
        if recipe_id in self.recipes:
            self.recipes.remove(recipe_id)
    
    def has_recipes(self) -> bool:
        """Check if tag has any recipes associated."""
        return len(self.recipes) > 0
    
    def recipe_count(self) -> int:
        """Get count of recipes with this tag."""
        return len(self.recipes)

