"""
File-based OneNote content importer for personal Microsoft accounts.

This module handles importing recipes from exported OneNote files when
the Graph API is not available due to SharePoint licensing limitations.
"""
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import re
from dataclasses import dataclass
from datetime import datetime

# File processing imports
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

from onenote_client import OneNoteRecipe

logger = logging.getLogger(__name__)


@dataclass
class ImportedFile:
    """Represents an imported file with metadata."""
    path: Path
    filename: str
    content: str
    format: str
    size: int
    modified_time: datetime


class FileImporter:
    """Import recipes from exported OneNote files."""
    
    def __init__(self, import_directory: str, supported_formats: List[str] = None):
        """
        Initialize file importer.
        
        Args:
            import_directory: Directory containing exported files
            supported_formats: List of supported file formats
        """
        self.import_directory = Path(import_directory)
        self.supported_formats = supported_formats or ['txt', 'html', 'docx', 'md']
        
        # Recipe detection patterns
        self.recipe_keywords = [
            'recipe', 'ingredients', 'instructions', 'directions', 
            'preparation', 'cooking', 'serves', 'servings', 'yield'
        ]
        
        # Common ingredient patterns
        self.ingredient_patterns = [
            r'^\d+\s*(cups?|tbsp|tsp|lbs?|oz|ml|grams?|kg)',  # Measurements
            r'^\d+/\d+\s*(cups?|tbsp|tsp)',  # Fractions
            r'^\d+\s*-\s*\d+\s*(cups?|tbsp|tsp)',  # Ranges
            r'^\s*[-•*]\s*',  # Bullet points
            r'^\d+\.\s*',  # Numbered lists
        ]
        
        # Instruction patterns
        self.instruction_patterns = [
            r'^\d+\.\s*',  # Numbered steps
            r'^Step\s*\d+:?\s*',  # Step labels
            r'^\s*[-•*]\s*',  # Bullet points
        ]

    def scan_directory(self) -> List[ImportedFile]:
        """Scan import directory for supported files."""
        if not self.import_directory.exists():
            logger.error(f"Import directory does not exist: {self.import_directory}")
            return []
        
        files = []
        for file_path in self.import_directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower().lstrip('.') in self.supported_formats:
                try:
                    imported_file = ImportedFile(
                        path=file_path,
                        filename=file_path.name,
                        content="",  # Will be loaded when needed
                        format=file_path.suffix.lower().lstrip('.'),
                        size=file_path.stat().st_size,
                        modified_time=datetime.fromtimestamp(file_path.stat().st_mtime)
                    )
                    files.append(imported_file)
                except Exception as e:
                    logger.warning(f"Could not process file {file_path}: {e}")
        
        logger.info(f"Found {len(files)} files to import")
        return files

    def load_file_content(self, imported_file: ImportedFile) -> str:
        """Load content from a file based on its format."""
        try:
            if imported_file.format == 'txt':
                return self._load_text_file(imported_file.path)
            elif imported_file.format == 'html':
                return self._load_html_file(imported_file.path)
            elif imported_file.format == 'docx':
                return self._load_docx_file(imported_file.path)
            elif imported_file.format == 'md':
                return self._load_text_file(imported_file.path)  # Markdown as text
            else:
                logger.warning(f"Unsupported file format: {imported_file.format}")
                return ""
        except Exception as e:
            logger.error(f"Failed to load {imported_file.path}: {e}")
            return ""

    def _load_text_file(self, file_path: Path) -> str:
        """Load plain text file."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    def _load_html_file(self, file_path: Path) -> str:
        """Load and parse HTML file."""
        if not BS4_AVAILABLE:
            logger.error("BeautifulSoup4 not available for HTML parsing")
            return self._load_text_file(file_path)
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        return '\n'.join(line for line in lines if line)

    def _load_docx_file(self, file_path: Path) -> str:
        """Load and parse Word document."""
        if not DOCX_AVAILABLE:
            logger.error("python-docx not available for DOCX parsing")
            return ""
        
        doc = Document(file_path)
        paragraphs = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                paragraphs.append(paragraph.text.strip())
        
        return '\n'.join(paragraphs)

    def detect_recipes(self, files: List[ImportedFile]) -> List[ImportedFile]:
        """Filter files that likely contain recipes."""
        recipe_files = []
        
        for file in files:
            content = self.load_file_content(file)
            if self._is_recipe_content(content, file.filename):
                file.content = content
                recipe_files.append(file)
                logger.info(f"Detected recipe in: {file.filename}")
            else:
                logger.debug(f"No recipe detected in: {file.filename}")
        
        return recipe_files

    def _is_recipe_content(self, content: str, filename: str) -> bool:
        """Determine if content contains a recipe."""
        content_lower = content.lower()
        filename_lower = filename.lower()
        
        # Check filename for recipe keywords
        filename_score = sum(1 for keyword in self.recipe_keywords 
                           if keyword in filename_lower)
        
        # Check content for recipe keywords
        content_score = sum(1 for keyword in self.recipe_keywords 
                          if keyword in content_lower)
        
        # Look for ingredient patterns
        ingredient_score = sum(1 for pattern in self.ingredient_patterns 
                             if re.search(pattern, content, re.MULTILINE | re.IGNORECASE))
        
        # Look for instruction patterns
        instruction_score = sum(1 for pattern in self.instruction_patterns 
                              if re.search(pattern, content, re.MULTILINE | re.IGNORECASE))
        
        total_score = filename_score + content_score + ingredient_score + instruction_score
        
        logger.debug(f"Recipe detection for {filename}: "
                    f"filename={filename_score}, content={content_score}, "
                    f"ingredients={ingredient_score}, instructions={instruction_score}, "
                    f"total={total_score}")
        
        return total_score >= 1  # Threshold for recipe detection

    def parse_recipe(self, imported_file: ImportedFile) -> Optional[OneNoteRecipe]:
        """Parse a recipe from imported file content."""
        if not imported_file.content:
            imported_file.content = self.load_file_content(imported_file)
        
        try:
            # Extract title from filename or content
            title = self._extract_title(imported_file)
            
            # Extract ingredients
            ingredients = self._extract_ingredients(imported_file.content)
            
            # Extract instructions
            instructions = self._extract_instructions(imported_file.content)
            
            # Extract metadata
            servings = self._extract_servings(imported_file.content)
            prep_time = self._extract_time(imported_file.content, 'prep')
            cook_time = self._extract_time(imported_file.content, 'cook')
            
            if not ingredients and not instructions:
                logger.warning(f"No recipe data found in {imported_file.filename}")
                return None
            
            # Use content as fallback if no structured data found
            if not ingredients:
                ingredients = [imported_file.content[:200] + "..."]
            if not instructions:
                instructions = [imported_file.content]
            
            return OneNoteRecipe(
                title=title,
                content=imported_file.content,
                ingredients=ingredients,
                instructions=instructions,
                servings=servings,
                prep_time=prep_time,
                cook_time=cook_time,
                created_date=imported_file.modified_time,
                modified_date=imported_file.modified_time,
                source_url=f"file://{imported_file.path}",
                page_id=str(imported_file.path),
                section_name="Imported",
                notebook_name="File Import"
            )
            
        except Exception as e:
            logger.error(f"Failed to parse recipe from {imported_file.filename}: {e}")
            return None

    def _extract_title(self, imported_file: ImportedFile) -> str:
        """Extract recipe title from the first line of the file."""
        # Use the first non-empty line as the title
        lines = imported_file.content.split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) > 2:
                return line
        
        # Fallback to filename if no content
        title = imported_file.path.stem
        title = re.sub(r'[_-]', ' ', title)
        return title.title()

    def _extract_ingredients(self, content: str) -> List[str]:
        """Extract ingredients list from content."""
        ingredients = []
        lines = content.split('\n')
        
        # Look for lines that contain ingredient patterns
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip obvious instruction lines
            if re.search(r'\b(bake|cook|heat|mix|stir|combine|add|pour|place|roll|cut|serve)\b', line, re.IGNORECASE) and len(line) > 50:
                continue
                
            # Look for ingredient patterns (quantity + unit + ingredient)
            for pattern in self.ingredient_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Clean up the ingredient line
                    ingredient = re.sub(r'^\s*[-•*]\s*', '', line)
                    ingredient = re.sub(r'^\d+\.\s*', '', ingredient)
                    if ingredient and len(ingredient) > 2 and len(ingredient) < 100:
                        ingredients.append(ingredient.strip())
                    break
        
        return ingredients

    def _extract_instructions(self, content: str) -> List[str]:
        """Extract instructions list from content."""
        instructions = []
        lines = content.split('\n')
        
        # Look for lines that look like instructions (longer sentences with action verbs)
        for line in lines:
            line = line.strip()
            if not line or len(line) < 20:  # Skip short lines
                continue
            
            # Skip ingredient lines (contain measurements)
            if re.search(r'\b\d+\s*(cups?|tbsp|tsp|pounds?|oz|lbs?)\b', line, re.IGNORECASE):
                continue
                
            # Look for instruction patterns (action verbs, cooking methods)
            if re.search(r'\b(bake|cook|heat|mix|stir|combine|add|pour|place|roll|cut|serve|refrigerate|cool|reduce|temp)\b', line, re.IGNORECASE):
                # Clean up the instruction line
                instruction = re.sub(r'^\s*[-•*]\s*', '', line)
                instruction = re.sub(r'^Step\s*\d+:?\s*', '', instruction, flags=re.IGNORECASE)
                instruction = re.sub(r'^\d+\.\s*', '', instruction)
                if instruction and len(instruction) > 10:
                    instructions.append(instruction.strip())
        
        return instructions

    def _extract_servings(self, content: str) -> Optional[str]:
        """Extract serving information."""
        patterns = [
            r'serves?\s*:?\s*(\d+)',
            r'yield\s*:?\s*(\d+)',
            r'portions?\s*:?\s*(\d+)',
            r'servings?\s*:?\s*(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

    def _extract_time(self, content: str, time_type: str) -> Optional[str]:
        """Extract prep or cook time."""
        patterns = [
            rf'{time_type}\s*time\s*:?\s*(\d+\s*(?:hours?|hrs?|minutes?|mins?))',
            rf'{time_type}\s*:?\s*(\d+\s*(?:hours?|hrs?|minutes?|mins?))',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

    def import_recipes(self, page_name_filter: Optional[str] = None) -> List[OneNoteRecipe]:
        """Import all recipes from the directory."""
        # Scan for files
        files = self.scan_directory()
        
        # Filter by name if specified
        if page_name_filter:
            files = [f for f in files if page_name_filter.lower() in f.filename.lower()]
            logger.info(f"Filtered to {len(files)} files matching '{page_name_filter}'")
        
        # Detect recipe files
        recipe_files = self.detect_recipes(files)
        
        # Parse recipes
        recipes = []
        for file in recipe_files:
            recipe = self.parse_recipe(file)
            if recipe:
                recipes.append(recipe)
        
        logger.info(f"Successfully imported {len(recipes)} recipes from {len(recipe_files)} files")
        return recipes


def create_file_importer(import_directory: str, supported_formats: List[str] = None) -> FileImporter:
    """Factory function to create file importer."""
    return FileImporter(import_directory, supported_formats)