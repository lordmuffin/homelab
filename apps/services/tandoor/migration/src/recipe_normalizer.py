"""
Recipe data normalization and standardization for Tandoor compatibility.
"""
import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from fractions import Fraction
import unicodedata

from onenote_client import OneNoteRecipe

logger = logging.getLogger(__name__)


@dataclass
class NormalizedRecipe:
    """Standardized recipe format for Tandoor API."""
    name: str
    description: str
    ingredients: List[Dict[str, any]]
    steps: List[Dict[str, any]]
    keywords: List[str]
    servings: int = 1
    working_time: int = 0  # minutes
    waiting_time: int = 0  # minutes
    internal: bool = True
    source_url: str = ""
    image: Optional[str] = None


class RecipeNormalizer:
    """Normalizes OneNote recipes for Tandoor compatibility."""
    
    def __init__(self):
        """Initialize with measurement conversion tables."""
        self.unit_conversions = {
            # Volume conversions to ml
            'cup': 240, 'cups': 240, 'c': 240,
            'tablespoon': 15, 'tablespoons': 15, 'tbsp': 15, 'tbs': 15,
            'teaspoon': 5, 'teaspoons': 5, 'tsp': 5,
            'fluid ounce': 30, 'fluid ounces': 30, 'fl oz': 30, 'floz': 30,
            'pint': 480, 'pints': 480, 'pt': 480,
            'quart': 960, 'quarts': 960, 'qt': 960,
            'gallon': 3840, 'gallons': 3840, 'gal': 3840,
            'liter': 1000, 'liters': 1000, 'l': 1000,
            'milliliter': 1, 'milliliters': 1, 'ml': 1,
            
            # Weight conversions to grams
            'pound': 454, 'pounds': 454, 'lb': 454, 'lbs': 454,
            'ounce': 28, 'ounces': 28, 'oz': 28,
            'kilogram': 1000, 'kilograms': 1000, 'kg': 1000,
            'gram': 1, 'grams': 1, 'g': 1,
            
            # Common cooking units (approximate)
            'stick': 113,  # stick of butter
            'package': 1,  # generic package
            'can': 400,   # standard can
            'jar': 450,   # standard jar
            'bottle': 500, # standard bottle
        }
        
        self.time_patterns = [
            (r'(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)', 60),  # hours to minutes
            (r'(\d+(?:\.\d+)?)\s*(?:minutes?|mins?|m)', 1),  # minutes
        ]
    
    def normalize_recipe(self, onenote_recipe: OneNoteRecipe) -> NormalizedRecipe:
        """Convert OneNote recipe to normalized Tandoor format."""
        logger.info(f"Normalizing recipe: {onenote_recipe.title}")
        
        # Normalize basic info
        name = self._clean_text(onenote_recipe.title)
        description = self._create_description(onenote_recipe)
        
        # Normalize ingredients
        ingredients = self._normalize_ingredients(onenote_recipe.ingredients)
        
        # Normalize steps
        steps = self._normalize_steps(onenote_recipe.instructions)
        
        # Extract timing information
        working_time, waiting_time = self._extract_timing(onenote_recipe)
        
        # Normalize servings
        servings = self._normalize_servings(onenote_recipe.servings)
        
        # Process keywords/tags
        keywords = self._normalize_keywords(onenote_recipe.tags)
        
        # Select primary image
        image = onenote_recipe.images[0] if onenote_recipe.images else None
        
        return NormalizedRecipe(
            name=name,
            description=description,
            ingredients=ingredients,
            steps=steps,
            keywords=keywords,
            servings=servings,
            working_time=working_time,
            waiting_time=waiting_time,
            source_url=onenote_recipe.source_url,
            image=image
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Normalize unicode characters
        text = unicodedata.normalize('NFKD', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common formatting artifacts
        text = re.sub(r'^(recipe:?\s*)', '', text, flags=re.IGNORECASE)
        
        return text
    
    def _create_description(self, recipe: OneNoteRecipe) -> str:
        """Create recipe description from available metadata."""
        parts = []
        
        if recipe.prep_time:
            parts.append(f"Prep time: {recipe.prep_time}")
        
        if recipe.cook_time:
            parts.append(f"Cook time: {recipe.cook_time}")
        
        if recipe.servings:
            parts.append(f"Serves: {recipe.servings}")
        
        if recipe.section_name and recipe.section_name != "Quick Notes":
            parts.append(f"From: {recipe.section_name}")
        
        description = " | ".join(parts)
        
        # Add first few lines of content if no other description
        if not description and recipe.content:
            content_lines = recipe.content.split('\n')[:3]
            content_preview = ' '.join(line.strip() for line in content_lines if line.strip())
            if content_preview and len(content_preview) > 20:
                description = content_preview[:200] + "..." if len(content_preview) > 200 else content_preview
        
        return description or "Imported from OneNote"
    
    def _normalize_ingredients(self, ingredients: List[str]) -> List[Dict[str, any]]:
        """Convert ingredient strings to Tandoor ingredient format."""
        normalized = []
        
        for i, ingredient_text in enumerate(ingredients):
            if not ingredient_text.strip():
                continue
            
            # Parse ingredient components
            parsed = self._parse_ingredient(ingredient_text)
            
            ingredient_obj = {
                'id': i + 1,
                'ingredient': {
                    'name': parsed['name'],
                    'ignore_shopping': False
                },
                'unit': parsed['unit'],
                'amount': parsed['amount'],
                'note': parsed['note'],
                'order': i + 1
            }
            
            normalized.append(ingredient_obj)
        
        return normalized
    
    def _parse_ingredient(self, ingredient_text: str) -> Dict[str, any]:
        """Parse individual ingredient string into components."""
        ingredient_text = self._clean_text(ingredient_text)
        
        # Initialize components
        amount = 0.0
        unit = None
        name = ingredient_text
        note = ""
        
        # Pattern to match quantity, unit, and ingredient
        # Examples: "2 cups flour", "1/2 tsp salt", "3 large eggs"
        pattern = r'^(\d+(?:\/\d+|\.\d+)?)\s*([a-zA-Z]+)?\s+(.+)$'
        match = re.match(pattern, ingredient_text)
        
        if match:
            amount_str, unit_str, name = match.groups()
            
            # Parse amount (handle fractions)
            try:
                if '/' in amount_str:
                    amount = float(Fraction(amount_str))
                else:
                    amount = float(amount_str)
            except (ValueError, ZeroDivisionError):
                amount = 0.0
            
            # Normalize unit
            if unit_str:
                unit = self._normalize_unit(unit_str.lower())
            
            # Extract notes from ingredient name
            name, note = self._extract_ingredient_notes(name)
        
        else:
            # Try to extract just amount from beginning
            amount_match = re.match(r'^(\d+(?:\/\d+|\.\d+)?)\s+(.+)$', ingredient_text)
            if amount_match:
                amount_str, name = amount_match.groups()
                try:
                    if '/' in amount_str:
                        amount = float(Fraction(amount_str))
                    else:
                        amount = float(amount_str)
                except (ValueError, ZeroDivisionError):
                    amount = 0.0
                
                name, note = self._extract_ingredient_notes(name)
        
        return {
            'amount': amount,
            'unit': unit,
            'name': name.strip(),
            'note': note.strip()
        }
    
    def _normalize_unit(self, unit: str) -> Optional[Dict[str, any]]:
        """Normalize measurement unit."""
        if not unit:
            return None
        
        # Standard unit mappings for Tandoor
        unit_map = {
            'cup': {'name': 'cup', 'plural_name': 'cups'},
            'cups': {'name': 'cup', 'plural_name': 'cups'},
            'c': {'name': 'cup', 'plural_name': 'cups'},
            'tablespoon': {'name': 'tablespoon', 'plural_name': 'tablespoons'},
            'tablespoons': {'name': 'tablespoon', 'plural_name': 'tablespoons'},
            'tbsp': {'name': 'tablespoon', 'plural_name': 'tablespoons'},
            'teaspoon': {'name': 'teaspoon', 'plural_name': 'teaspoons'},
            'teaspoons': {'name': 'teaspoon', 'plural_name': 'teaspoons'},
            'tsp': {'name': 'teaspoon', 'plural_name': 'teaspoons'},
            'pound': {'name': 'pound', 'plural_name': 'pounds'},
            'pounds': {'name': 'pound', 'plural_name': 'pounds'},
            'lb': {'name': 'pound', 'plural_name': 'pounds'},
            'lbs': {'name': 'pound', 'plural_name': 'pounds'},
            'ounce': {'name': 'ounce', 'plural_name': 'ounces'},
            'ounces': {'name': 'ounce', 'plural_name': 'ounces'},
            'oz': {'name': 'ounce', 'plural_name': 'ounces'},
            'gram': {'name': 'gram', 'plural_name': 'grams'},
            'grams': {'name': 'gram', 'plural_name': 'grams'},
            'g': {'name': 'gram', 'plural_name': 'grams'},
            'kilogram': {'name': 'kilogram', 'plural_name': 'kilograms'},
            'kg': {'name': 'kilogram', 'plural_name': 'kilograms'},
            'liter': {'name': 'liter', 'plural_name': 'liters'},
            'l': {'name': 'liter', 'plural_name': 'liters'},
            'milliliter': {'name': 'milliliter', 'plural_name': 'milliliters'},
            'ml': {'name': 'milliliter', 'plural_name': 'milliliters'},
        }
        
        return unit_map.get(unit.lower())
    
    def _extract_ingredient_notes(self, name: str) -> Tuple[str, str]:
        """Extract notes from ingredient name (e.g., 'eggs, beaten' -> 'eggs', 'beaten')."""
        # Look for common note patterns
        note_patterns = [
            r',\s*(.+)$',  # Everything after comma
            r'\(([^)]+)\)',  # Content in parentheses
        ]
        
        note = ""
        clean_name = name
        
        for pattern in note_patterns:
            match = re.search(pattern, name)
            if match:
                note = match.group(1)
                clean_name = re.sub(pattern, '', name).strip()
                break
        
        return clean_name, note
    
    def _normalize_steps(self, instructions: List[str]) -> List[Dict[str, any]]:
        """Convert instruction strings to Tandoor step format."""
        steps = []
        
        for i, instruction in enumerate(instructions):
            if not instruction.strip():
                continue
            
            # Clean up instruction text
            clean_instruction = self._clean_text(instruction)
            
            # Remove step numbering if present
            clean_instruction = re.sub(r'^\d+\.\s*', '', clean_instruction)
            
            step = {
                'id': i + 1,
                'instruction': clean_instruction,
                'ingredients': [],  # Could be enhanced to link ingredients
                'time': 0,  # Could be enhanced to extract timing
                'order': i + 1
            }
            
            steps.append(step)
        
        return steps
    
    def _extract_timing(self, recipe: OneNoteRecipe) -> Tuple[int, int]:
        """Extract working time and waiting time in minutes."""
        working_time = 0
        waiting_time = 0
        
        # Parse prep time (working time)
        if recipe.prep_time:
            working_time = self._parse_time_string(recipe.prep_time)
        
        # Parse cook time (could be waiting time depending on recipe)
        if recipe.cook_time:
            cook_minutes = self._parse_time_string(recipe.cook_time)
            # For now, treat cook time as working time
            # Could be enhanced to detect passive cooking (waiting time)
            working_time += cook_minutes
        
        return working_time, waiting_time
    
    def _parse_time_string(self, time_str: str) -> int:
        """Parse time string and return minutes."""
        if not time_str:
            return 0
        
        total_minutes = 0
        
        for pattern, multiplier in self.time_patterns:
            matches = re.findall(pattern, time_str, re.IGNORECASE)
            for match in matches:
                try:
                    value = float(match)
                    total_minutes += int(value * multiplier)
                except (ValueError, TypeError):
                    continue
        
        return total_minutes
    
    def _normalize_servings(self, servings_str: Optional[str]) -> int:
        """Extract servings count as integer."""
        if not servings_str:
            return 1
        
        # Extract first number from servings string
        match = re.search(r'(\d+)', servings_str)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        
        return 1
    
    def _normalize_keywords(self, tags: List[str]) -> List[str]:
        """Normalize and clean keyword tags."""
        keywords = []
        
        for tag in tags:
            if tag and tag.strip():
                # Clean and standardize tag
                clean_tag = self._clean_text(tag.lower())
                if clean_tag and len(clean_tag) > 1:
                    keywords.append(clean_tag)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for keyword in keywords:
            if keyword not in seen:
                seen.add(keyword)
                unique_keywords.append(keyword)
        
        return unique_keywords