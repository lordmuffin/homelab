"""
OneNote API client for recipe extraction using Microsoft Graph API.
"""
import logging
from typing import List, Dict, Optional, Any
import re
from dataclasses import dataclass
from datetime import datetime

import msal
from msgraph import GraphServiceClient
from msgraph.generated.models.notebook import Notebook
from msgraph.generated.models.onenote_page import OnenotePage
from msgraph.generated.models.onenote_section import OnenoteSection
from azure.identity import ClientSecretCredential
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class OneNoteRecipe:
    """Structured recipe data from OneNote."""
    title: str
    content: str
    ingredients: List[str]
    instructions: List[str]
    servings: Optional[str] = None
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    images: List[str] = None
    tags: List[str] = None
    source_url: str = ""
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    page_id: str = ""
    section_name: str = ""
    notebook_name: str = ""

    def __post_init__(self):
        if self.images is None:
            self.images = []
        if self.tags is None:
            self.tags = []


class OneNoteClient:
    """Microsoft Graph API client for OneNote operations."""
    
    def __init__(self, client_id: str, client_secret: str, tenant_id: str):
        """Initialize OneNote client with Microsoft Graph credentials."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self._graph_client = None
        self._setup_graph_client()
    
    def _setup_graph_client(self):
        """Initialize Microsoft Graph client with proper authentication."""
        try:
            # Use client credentials flow for application permissions
            credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            scopes = ['https://graph.microsoft.com/.default']
            self._graph_client = GraphServiceClient(credentials=credential, scopes=scopes)
            
            logger.info("Microsoft Graph client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Graph client: {e}")
            raise
    
    async def get_notebooks(self) -> List[Notebook]:
        """Retrieve all OneNote notebooks with fallback for personal accounts."""
        try:
            notebooks = await self._graph_client.me.onenote.notebooks.get()
            logger.info(f"Found {len(notebooks.value)} notebooks")
            return notebooks.value
        except Exception as e:
            logger.warning(f"Enterprise OneNote API failed: {e}")
            
            # If that fails with SharePoint license error, try alternative approaches
            if "SharePoint license" in str(e) or "30121" in str(e):
                logger.info("Attempting personal account fallback methods...")
                return await self._get_notebooks_personal_fallback()
            else:
                logger.error(f"Failed to retrieve notebooks: {e}")
                return []
    
    async def _get_notebooks_personal_fallback(self) -> List[Notebook]:
        """Fallback methods for personal Microsoft accounts without SharePoint."""
        logger.info("Trying alternative OneNote API endpoints for personal accounts...")
        
        try:
            # Method 1: Try consumer-specific Graph endpoint
            # Personal accounts might use a different endpoint structure
            logger.info("Attempting method 1: Direct OneDrive OneNote access...")
            
            # Try accessing through OneDrive root items
            drive_items = await self._graph_client.me.drive.root.children.get()
            onenote_items = [item for item in drive_items.value if item.name and 'onenote' in item.name.lower()]
            
            if onenote_items:
                logger.info(f"Found {len(onenote_items)} potential OneNote items in OneDrive")
                # Convert OneDrive items to notebook-like objects
                notebooks = []
                for item in onenote_items:
                    # Create a pseudo-notebook object
                    notebook = type('Notebook', (), {
                        'id': item.id,
                        'display_name': item.name,
                        'created_datetime': item.created_date_time,
                        'last_modified_datetime': item.last_modified_date_time
                    })()
                    notebooks.append(notebook)
                return notebooks
            
        except Exception as e:
            logger.warning(f"OneDrive fallback method failed: {e}")
        
        try:
            # Method 2: Try the beta Graph API endpoint
            logger.info("Attempting method 2: Beta Graph API endpoint...")
            
            # Some personal accounts work with beta endpoint
            import httpx
            
            # Get access token manually since we can't easily extract from Graph client
            # We'll use the ClientSecretCredential to get a fresh token
            from azure.identity import ClientSecretCredential
            credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            token = credential.get_token('https://graph.microsoft.com/.default')
            
            # Make direct HTTP request to beta endpoint
            headers = {
                'Authorization': f'Bearer {token.token}',
                'Accept': 'application/json'
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://graph.microsoft.com/beta/me/onenote/notebooks',
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'value' in data and data['value']:
                        logger.info(f"Beta API found {len(data['value'])} notebooks")
                        # Convert to notebook objects
                        notebooks = []
                        for nb_data in data['value']:
                            notebook = type('Notebook', (), {
                                'id': nb_data.get('id', ''),
                                'display_name': nb_data.get('displayName', 'Unknown'),
                                'created_datetime': nb_data.get('createdDateTime'),
                                'last_modified_datetime': nb_data.get('lastModifiedDateTime')
                            })()
                            notebooks.append(notebook)
                        return notebooks
                        
        except Exception as e:
            logger.warning(f"Beta API fallback method failed: {e}")
        
        # Method 3: Provide helpful information about the limitation
        logger.error("All OneNote access methods failed for personal account")
        logger.error("Personal Microsoft accounts have limitations accessing OneNote through Graph API")
        logger.error("This is due to SharePoint licensing requirements for the OneNote API")
        logger.error("Possible solutions:")
        logger.error("1. Use a work/school Microsoft account with Office 365")
        logger.error("2. Export OneNote notebooks manually and import to Tandoor")
        logger.error("3. Use OneNote's export functionality to create files for import")
        
        return []
    
    async def get_sections(self, notebook_id: str) -> List[OnenoteSection]:
        """Get all sections in a notebook."""
        try:
            sections = await self._graph_client.me.onenote.notebooks.by_notebook_id(notebook_id).sections.get()
            logger.info(f"Found {len(sections.value)} sections in notebook {notebook_id}")
            return sections.value
        except Exception as e:
            logger.error(f"Failed to retrieve sections for notebook {notebook_id}: {e}")
            return []
    
    async def get_pages(self, section_id: str) -> List[OnenotePage]:
        """Get all pages in a section."""
        try:
            pages = await self._graph_client.me.onenote.sections.by_section_id(section_id).pages.get()
            logger.info(f"Found {len(pages.value)} pages in section {section_id}")
            return pages.value
        except Exception as e:
            logger.error(f"Failed to retrieve pages for section {section_id}: {e}")
            return []
    
    async def get_page_content(self, page_id: str) -> str:
        """Get the HTML content of a OneNote page."""
        try:
            # Get page content in HTML format
            content = await self._graph_client.me.onenote.pages.by_page_id(page_id).content.get()
            if content:
                return content.decode('utf-8') if isinstance(content, bytes) else str(content)
            return ""
        except Exception as e:
            logger.error(f"Failed to retrieve content for page {page_id}: {e}")
            return ""
    
    async def find_recipe_pages(self, notebook_name: Optional[str] = None, 
                              page_name_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find pages that likely contain recipes.
        
        Args:
            notebook_name: Optional notebook name filter
            page_name_filter: Optional page name filter (e.g., "recipes")
        """
        recipe_pages = []
        
        try:
            notebooks = await self.get_notebooks()
            
            # Filter by notebook name if specified
            if notebook_name:
                notebooks = [nb for nb in notebooks if notebook_name.lower() in nb.display_name.lower()]
            
            for notebook in notebooks:
                logger.info(f"Scanning notebook: {notebook.display_name}")
                sections = await self.get_sections(notebook.id)
                
                for section in sections:
                    logger.info(f"Scanning section: {section.display_name}")
                    pages = await self.get_pages(section.id)
                    
                    for page in pages:
                        # Apply page name filter if specified
                        if page_name_filter:
                            if page_name_filter.lower() not in page.title.lower():
                                continue
                            logger.info(f"Found page matching filter '{page_name_filter}': {page.title}")
                        else:
                            # Check if page title suggests it's a recipe (only when no specific filter)
                            if not self._is_likely_recipe_page(page.title):
                                continue
                        
                        recipe_pages.append({
                            'page': page,
                            'section_name': section.display_name,
                            'notebook_name': notebook.display_name
                        })
                        logger.info(f"Added recipe page: {page.title}")
        
        except Exception as e:
            logger.error(f"Error finding recipe pages: {e}")
        
        return recipe_pages
    
    def _is_likely_recipe_page(self, title: str) -> bool:
        """Determine if a page title suggests it contains a recipe."""
        recipe_indicators = [
            'recipe', 'cooking', 'baking', 'dish', 'meal', 'food',
            'cake', 'bread', 'soup', 'sauce', 'chicken', 'beef',
            'pasta', 'salad', 'dessert', 'cookie', 'pie', 'casserole'
        ]
        
        title_lower = title.lower()
        return any(indicator in title_lower for indicator in recipe_indicators)
    
    async def extract_recipe_from_page(self, page_data: Dict[str, Any]) -> Optional[OneNoteRecipe]:
        """Extract structured recipe data from a OneNote page."""
        page = page_data['page']
        section_name = page_data['section_name']
        notebook_name = page_data['notebook_name']
        
        try:
            content = await self.get_page_content(page.id)
            if not content:
                logger.warning(f"No content found for page: {page.title}")
                return None
            
            # Parse the HTML content to extract recipe components
            recipe = self._parse_recipe_content(content, page, section_name, notebook_name)
            
            if recipe and recipe.ingredients and recipe.instructions:
                logger.info(f"Successfully extracted recipe: {recipe.title}")
                return recipe
            else:
                logger.warning(f"Could not extract complete recipe from page: {page.title}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to extract recipe from page {page.title}: {e}")
            return None
    
    def _parse_recipe_content(self, html_content: str, page: OnenotePage, 
                            section_name: str, notebook_name: str) -> OneNoteRecipe:
        """Parse HTML content to extract recipe components."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract text content
        text_content = soup.get_text()
        
        # Initialize recipe data
        recipe = OneNoteRecipe(
            title=page.title or "Untitled Recipe",
            content=text_content,
            ingredients=[],
            instructions=[],
            page_id=page.id,
            section_name=section_name,
            notebook_name=notebook_name,
            created_date=page.created_date_time,
            modified_date=page.last_modified_date_time,
            source_url=page.links.onenote_web_url.href if page.links and page.links.onenote_web_url else ""
        )
        
        # Extract ingredients
        recipe.ingredients = self._extract_ingredients(text_content)
        
        # Extract instructions
        recipe.instructions = self._extract_instructions(text_content)
        
        # Extract metadata
        recipe.servings = self._extract_servings(text_content)
        recipe.prep_time = self._extract_time(text_content, 'prep')
        recipe.cook_time = self._extract_time(text_content, 'cook')
        recipe.tags = self._extract_tags(text_content, page.title)
        
        # Extract images
        recipe.images = self._extract_images(soup)
        
        return recipe
    
    def _extract_ingredients(self, text: str) -> List[str]:
        """Extract ingredients from recipe text."""
        ingredients = []
        
        # Look for ingredients section
        lines = text.split('\n')
        in_ingredients_section = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for ingredients header
            if re.search(r'\b(ingredients?|what you need|shopping list)\b', line, re.IGNORECASE):
                in_ingredients_section = True
                continue
            
            # Check for end of ingredients section
            if in_ingredients_section and re.search(r'\b(instructions?|directions?|method|preparation|steps)\b', line, re.IGNORECASE):
                break
            
            # Extract ingredient lines
            if in_ingredients_section:
                # Clean up common formatting
                ingredient = re.sub(r'^[•\-\*\d+\.\)\s]+', '', line)
                if ingredient and len(ingredient) > 2:
                    ingredients.append(ingredient)
        
        return ingredients
    
    def _extract_instructions(self, text: str) -> List[str]:
        """Extract cooking instructions from recipe text."""
        instructions = []
        
        lines = text.split('\n')
        in_instructions_section = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for instructions header
            if re.search(r'\b(instructions?|directions?|method|preparation|steps|how to make)\b', line, re.IGNORECASE):
                in_instructions_section = True
                continue
            
            # Extract instruction lines
            if in_instructions_section:
                # Clean up common formatting
                instruction = re.sub(r'^[•\-\*\d+\.\)\s]+', '', line)
                if instruction and len(instruction) > 5:
                    instructions.append(instruction)
        
        return instructions
    
    def _extract_servings(self, text: str) -> Optional[str]:
        """Extract serving information."""
        patterns = [
            r'serves?\s*:?\s*(\d+(?:\-\d+)?)',
            r'(\d+(?:\-\d+)?)\s*servings?',
            r'makes?\s*:?\s*(\d+(?:\-\d+)?)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_time(self, text: str, time_type: str) -> Optional[str]:
        """Extract prep time or cook time."""
        patterns = [
            rf'{time_type}\s*time\s*:?\s*(\d+(?:\s*(?:hours?|hrs?|minutes?|mins?))?)',
            rf'{time_type}\s*:?\s*(\d+(?:\s*(?:hours?|hrs?|minutes?|mins?))?)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_tags(self, text: str, title: str) -> List[str]:
        """Extract tags based on recipe content and title."""
        tags = []
        
        # Common recipe categories
        categories = {
            'breakfast': ['breakfast', 'morning', 'cereal', 'pancake', 'waffle', 'toast'],
            'lunch': ['lunch', 'sandwich', 'salad', 'wrap'],
            'dinner': ['dinner', 'main', 'entree'],
            'dessert': ['dessert', 'sweet', 'cake', 'cookie', 'pie', 'ice cream'],
            'appetizer': ['appetizer', 'starter', 'snack'],
            'soup': ['soup', 'broth', 'chili', 'stew'],
            'vegetarian': ['vegetarian', 'veggie', 'meatless'],
            'quick': ['quick', 'fast', 'easy', '15 minutes', '30 minutes']
        }
        
        text_lower = (text + ' ' + title).lower()
        
        for category, keywords in categories.items():
            if any(keyword in text_lower for keyword in keywords):
                tags.append(category)
        
        return tags
    
    def _extract_images(self, soup: BeautifulSoup) -> List[str]:
        """Extract image URLs from OneNote HTML content."""
        images = []
        
        # Find all img tags
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                images.append(src)
        
        return images