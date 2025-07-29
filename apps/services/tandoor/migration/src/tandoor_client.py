"""
Tandoor Recipes API client for uploading normalized recipes.
"""
import logging
import requests
from typing import List, Dict, Optional, Any
import time
from dataclasses import asdict
import json

from recipe_normalizer import NormalizedRecipe

logger = logging.getLogger(__name__)


class TandoorAPIError(Exception):
    """Custom exception for Tandoor API errors."""
    pass


class TandoorClient:
    """Client for interacting with Tandoor Recipes API."""
    
    def __init__(self, base_url: str, api_token: str):
        """Initialize Tandoor client with API credentials."""
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.session = requests.Session()
        
        # Set up authentication headers
        self.session.headers.update({
            'Authorization': f'Token {api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test API connection and authentication."""
        try:
            response = self.session.get(f'{self.base_url}/api/user/')
            response.raise_for_status()
            logger.info("Successfully connected to Tandoor API")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Tandoor API: {e}")
            raise TandoorAPIError(f"Connection test failed: {e}")
    
    def create_recipe(self, recipe: NormalizedRecipe) -> Dict[str, Any]:
        """Create a new recipe in Tandoor."""
        logger.info(f"Creating recipe: {recipe.name}")
        
        try:
            # Prepare recipe data for API
            recipe_data = self._prepare_recipe_data(recipe)
            
            # Create the recipe
            response = self.session.post(
                f'{self.base_url}/api/recipe/',
                json=recipe_data
            )
            response.raise_for_status()
            
            created_recipe = response.json()
            logger.info(f"Successfully created recipe ID: {created_recipe.get('id')}")
            
            return created_recipe
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create recipe {recipe.name}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise TandoorAPIError(f"Recipe creation failed: {e}")
    
    def check_recipe_exists(self, recipe_name: str) -> Optional[Dict[str, Any]]:
        """Check if a recipe with the given name already exists."""
        try:
            response = self.session.get(
                f'{self.base_url}/api/recipe/',
                params={'search': recipe_name}
            )
            response.raise_for_status()
            
            recipes = response.json().get('results', [])
            
            # Look for exact name match (case insensitive)
            for recipe in recipes:
                if recipe.get('name', '').lower() == recipe_name.lower():
                    logger.info(f"Found existing recipe: {recipe_name}")
                    return recipe
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to search for recipe {recipe_name}: {e}")
            return None
    
    def get_or_create_keyword(self, keyword_name: str) -> Dict[str, Any]:
        """Get existing keyword or create new one."""
        try:
            # Search for existing keyword
            response = self.session.get(
                f'{self.base_url}/api/keyword/',
                params={'search': keyword_name}
            )
            response.raise_for_status()
            
            keywords = response.json().get('results', [])
            
            # Look for exact match
            for keyword in keywords:
                if keyword.get('name', '').lower() == keyword_name.lower():
                    return keyword
            
            # Create new keyword if not found
            keyword_data = {
                'name': keyword_name,
                'description': f'Imported from OneNote: {keyword_name}'
            }
            
            response = self.session.post(
                f'{self.base_url}/api/keyword/',
                json=keyword_data
            )
            response.raise_for_status()
            
            created_keyword = response.json()
            logger.info(f"Created new keyword: {keyword_name}")
            return created_keyword
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get/create keyword {keyword_name}: {e}")
            # Return a minimal keyword object to continue processing
            return {'id': None, 'name': keyword_name}
    
    def get_or_create_food(self, food_name: str) -> Dict[str, Any]:
        """Get existing food item or create new one."""
        try:
            # Search for existing food
            response = self.session.get(
                f'{self.base_url}/api/food/',
                params={'search': food_name}
            )
            response.raise_for_status()
            
            foods = response.json().get('results', [])
            
            # Look for exact match
            for food in foods:
                if food.get('name', '').lower() == food_name.lower():
                    return food
            
            # Create new food if not found
            food_data = {
                'name': food_name,
                'ignore_shopping': False
            }
            
            response = self.session.post(
                f'{self.base_url}/api/food/',
                json=food_data
            )
            response.raise_for_status()
            
            created_food = response.json()
            logger.info(f"Created new food: {food_name}")
            return created_food
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get/create food {food_name}: {e}")
            # Return a minimal food object to continue processing
            return {'id': None, 'name': food_name}
    
    def get_or_create_unit(self, unit_name: str, plural_name: str = None) -> Dict[str, Any]:
        """Get existing unit or create new one."""
        if not unit_name:
            return None
        
        try:
            # Search for existing unit
            response = self.session.get(
                f'{self.base_url}/api/unit/',
                params={'search': unit_name}
            )
            response.raise_for_status()
            
            units = response.json().get('results', [])
            
            # Look for exact match
            for unit in units:
                if unit.get('name', '').lower() == unit_name.lower():
                    return unit
            
            # Create new unit if not found
            unit_data = {
                'name': unit_name,
                'plural_name': plural_name or f"{unit_name}s",
                'description': f'Imported from OneNote: {unit_name}'
            }
            
            response = self.session.post(
                f'{self.base_url}/api/unit/',
                json=unit_data
            )
            response.raise_for_status()
            
            created_unit = response.json()
            logger.info(f"Created new unit: {unit_name}")
            return created_unit
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get/create unit {unit_name}: {e}")
            # Return a minimal unit object to continue processing
            return {'id': None, 'name': unit_name}
    
    def upload_image(self, image_url: str, recipe_id: int) -> Optional[str]:
        """Upload image from URL to recipe."""
        if not image_url:
            return None
        
        try:
            # Download image from OneNote
            image_response = requests.get(image_url, timeout=30)
            image_response.raise_for_status()
            
            # Prepare multipart form data
            files = {
                'image': ('recipe_image.jpg', image_response.content, 'image/jpeg')
            }
            
            # Upload to Tandoor (without Content-Type header for multipart)
            upload_session = requests.Session()
            upload_session.headers.update({
                'Authorization': f'Token {self.api_token}'
            })
            
            response = upload_session.patch(
                f'{self.base_url}/api/recipe/{recipe_id}/',
                files=files
            )
            response.raise_for_status()
            
            updated_recipe = response.json()
            image_url = updated_recipe.get('image')
            
            if image_url:
                logger.info(f"Successfully uploaded image for recipe {recipe_id}")
                return image_url
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to upload image for recipe {recipe_id}: {e}")
        
        return None
    
    def _prepare_recipe_data(self, recipe: NormalizedRecipe) -> Dict[str, Any]:
        """Prepare recipe data for Tandoor API format."""
        # Process keywords
        keyword_objects = []
        for keyword_name in recipe.keywords:
            keyword = self.get_or_create_keyword(keyword_name)
            if keyword.get('id'):
                keyword_objects.append(keyword['id'])
        
        # Process ingredients with proper food and unit references
        processed_ingredients = []
        for ingredient in recipe.ingredients:
            # Get or create food item
            food_name = ingredient['ingredient']['name']
            food = self.get_or_create_food(food_name)
            
            # Get or create unit if specified
            unit_data = ingredient.get('unit')
            unit = None
            if unit_data:
                unit = self.get_or_create_unit(
                    unit_data['name'], 
                    unit_data.get('plural_name')
                )
            
            processed_ingredient = {
                'food': food.get('id') if food.get('id') else None,
                'amount': ingredient['amount'],
                'unit': unit.get('id') if unit and unit.get('id') else None,
                'note': ingredient.get('note', ''),
                'order': ingredient['order']
            }
            
            # Only add ingredient if we have valid food
            if processed_ingredient['food']:
                processed_ingredients.append(processed_ingredient)
            else:
                logger.warning(f"Skipping ingredient {food_name} - could not create food item")
        
        # Process steps
        processed_steps = []
        for step in recipe.steps:
            processed_step = {
                'instruction': step['instruction'],
                'order': step['order'],
                'time': step.get('time', 0),
                'ingredients': []  # Add empty ingredients list for each step
            }
            processed_steps.append(processed_step)
        
        # Prepare final recipe data
        recipe_data = {
            'name': recipe.name,
            'description': recipe.description,
            'servings': recipe.servings,
            'working_time': recipe.working_time,
            'waiting_time': recipe.waiting_time,
            'internal': recipe.internal,
            'source_url': recipe.source_url,
            'keywords': keyword_objects,
            'steps': processed_steps
        }
        
        # Add ingredients if we have any valid ones
        if processed_ingredients:
            recipe_data['recipeingredient_set'] = processed_ingredients
        
        return recipe_data
    
    def batch_upload_recipes(self, recipes: List[NormalizedRecipe], 
                           skip_duplicates: bool = True, 
                           delay_between_requests: float = 1.0) -> Dict[str, List]:
        """Upload multiple recipes with batch processing."""
        results = {
            'success': [],
            'failed': [],
            'skipped': []
        }
        
        logger.info(f"Starting batch upload of {len(recipes)} recipes")
        
        for i, recipe in enumerate(recipes, 1):
            logger.info(f"Processing recipe {i}/{len(recipes)}: {recipe.name}")
            
            try:
                # Check for duplicates if requested
                if skip_duplicates:
                    existing = self.check_recipe_exists(recipe.name)
                    if existing:
                        logger.info(f"Skipping duplicate recipe: {recipe.name}")
                        results['skipped'].append({
                            'recipe': recipe.name,
                            'reason': 'Duplicate found',
                            'existing_id': existing.get('id')
                        })
                        continue
                
                # Create the recipe
                created_recipe = self.create_recipe(recipe)
                
                # Upload image if available
                if recipe.image and created_recipe.get('id'):
                    image_url = self.upload_image(recipe.image, created_recipe['id'])
                    if image_url:
                        created_recipe['uploaded_image'] = image_url
                
                results['success'].append({
                    'recipe': recipe.name,
                    'id': created_recipe.get('id'),
                    'url': f"{self.base_url}/recipe/view/{created_recipe.get('id')}"
                })
                
                # Rate limiting delay
                if delay_between_requests > 0:
                    time.sleep(delay_between_requests)
                
            except Exception as e:
                logger.error(f"Failed to process recipe {recipe.name}: {e}")
                results['failed'].append({
                    'recipe': recipe.name,
                    'error': str(e)
                })
        
        # Log summary
        logger.info(f"Batch upload completed:")
        logger.info(f"  Success: {len(results['success'])}")
        logger.info(f"  Failed: {len(results['failed'])}")
        logger.info(f"  Skipped: {len(results['skipped'])}")
        
        return results