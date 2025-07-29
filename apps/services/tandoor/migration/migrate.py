#!/usr/bin/env python3
"""
OneNote to Tandoor Recipe Migration Tool

This script migrates recipes from Microsoft OneNote to Tandoor Recipes
using the Microsoft Graph API and Tandoor REST API.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import yaml
from dotenv import load_dotenv
import click
from rich.console import Console
from rich.progress import Progress, TaskID
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from onenote_client import OneNoteClient, OneNoteRecipe
from onenote_auth_client import create_onenote_client
from recipe_normalizer import RecipeNormalizer, NormalizedRecipe
from tandoor_client import TandoorClient, TandoorAPIError
from tandoor_simple_auth import create_tandoor_client
from file_importer import create_file_importer

console = Console()
logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages the complete migration process from OneNote to Tandoor."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize migration manager with configuration."""
        self.config = self._load_config(config_path)
        self._setup_logging()
        
        # Initialize clients
        self.onenote_client = None
        self.tandoor_client = None
        self.normalizer = RecipeNormalizer()
        
        # Statistics
        self.stats = {
            'pages_scanned': 0,
            'recipes_found': 0,
            'recipes_normalized': 0,
            'recipes_uploaded': 0,
            'recipes_failed': 0,
            'recipes_skipped': 0
        }
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file with environment variable substitution."""
        load_dotenv()  # Load .env file
        
        if not Path(config_path).exists():
            console.print(f"[red]Configuration file not found: {config_path}[/red]")
            sys.exit(1)
        
        with open(config_path, 'r') as f:
            config_content = f.read()
        
        # Substitute environment variables
        import re
        def env_substitution(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) else ""
            return os.getenv(var_name, default_value)
        
        # Pattern: ${VAR_NAME:-default_value} or ${VAR_NAME}
        config_content = re.sub(r'\$\{([^}:]+)(?::-([^}]*))?\}', env_substitution, config_content)
        
        return yaml.safe_load(config_content)
    
    def _setup_logging(self):
        """Configure logging based on configuration."""
        log_config = self.config.get('logging', {})
        
        # Set log level
        log_level = getattr(logging, log_config.get('level', 'INFO').upper())
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(log_config.get('format', 
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
        # Console handler
        if log_config.get('console', True):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # File handler
        log_file = log_config.get('file')
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
    
    def _initialize_clients(self):
        """Initialize OneNote and Tandoor API clients."""
        # Check if using file import mode
        use_file_import = os.getenv('USE_FILE_IMPORT', 'false').lower() == 'true'
        
        if use_file_import:
            # Initialize file importer instead of OneNote client
            import_directory = os.getenv('IMPORT_FILES_DIRECTORY', 'exported_recipes')
            self.file_importer = create_file_importer(import_directory)
            self.onenote_client = None
            logger.info(f"File importer initialized for directory: {import_directory}")
        else:
            # Initialize OneNote client with delegated authentication
            microsoft_config = self.config['microsoft']
            self.onenote_client = create_onenote_client(
                client_id=microsoft_config['client_id'],
                client_secret=microsoft_config['client_secret'],
                tenant_id=microsoft_config['tenant_id'],
                use_interactive_auth=microsoft_config.get('use_interactive_auth', True)
            )
            self.file_importer = None
        
        # Initialize Tandoor client with Microsoft authentication support
        tandoor_config = self.config['tandoor']
        self.tandoor_client = create_tandoor_client(
            base_url=tandoor_config['url'],
            api_token=tandoor_config['api_token'],
            msft_username=tandoor_config.get('msft_username'),
            msft_password=tandoor_config.get('msft_password'),
            skip_msft_auth=tandoor_config.get('skip_msft_auth', False)
        )
        
        logger.info("API clients initialized successfully")
    
    async def scan_onenote_recipes(self) -> List[OneNoteRecipe]:
        """Scan OneNote for recipe pages and extract recipe data."""
        # Check if using file import mode
        if self.file_importer:
            return self._import_from_files()
        
        console.print("[blue]Scanning OneNote for recipes...[/blue]")
        
        notebook_name = self.config['migration'].get('notebook_name')
        page_name_filter = self.config['migration'].get('page_name_filter')
        
        # Log filtering settings
        if notebook_name:
            console.print(f"[blue]Filtering by notebook: {notebook_name}[/blue]")
        if page_name_filter:
            console.print(f"[blue]Filtering by page name: '{page_name_filter}'[/blue]")
        else:
            console.print("[blue]Using automatic recipe detection[/blue]")
        
        recipe_pages = await self.onenote_client.find_recipe_pages(notebook_name, page_name_filter)
        
        self.stats['pages_scanned'] = len(recipe_pages)
        console.print(f"Found {len(recipe_pages)} potential recipe pages")
        
        recipes = []
        
        with Progress() as progress:
            task = progress.add_task("Extracting recipes...", total=len(recipe_pages))
            
            for page_data in recipe_pages:
                try:
                    recipe = await self.onenote_client.extract_recipe_from_page(page_data)
                    if recipe and self._validate_recipe(recipe):
                        recipes.append(recipe)
                        self.stats['recipes_found'] += 1
                        logger.info(f"Extracted recipe: {recipe.title}")
                    
                except Exception as e:
                    logger.error(f"Failed to extract recipe from page: {e}")
                
                progress.update(task, advance=1)
        
        console.print(f"[green]Successfully extracted {len(recipes)} recipes[/green]")
        return recipes
    
    def _import_from_files(self) -> List[OneNoteRecipe]:
        """Import recipes from exported files."""
        console.print("[blue]Importing recipes from files...[/blue]")
        
        page_name_filter = self.config['migration'].get('page_name_filter')
        
        if page_name_filter:
            console.print(f"[blue]Filtering files by name: '{page_name_filter}'[/blue]")
        else:
            console.print("[blue]Processing all supported files[/blue]")
        
        try:
            recipes = self.file_importer.import_recipes(page_name_filter)
            
            # Update statistics
            self.stats['pages_scanned'] = len(self.file_importer.scan_directory())
            self.stats['recipes_found'] = len(recipes)
            
            console.print(f"[green]Successfully imported {len(recipes)} recipes from files[/green]")
            return recipes
            
        except Exception as e:
            logger.error(f"Failed to import from files: {e}")
            console.print(f"[red]File import failed: {e}[/red]")
            return []
    
    def _validate_recipe(self, recipe: OneNoteRecipe) -> bool:
        """Validate recipe meets minimum requirements."""
        processing_config = self.config.get('recipe_processing', {})
        
        min_ingredients = self.config['migration'].get('min_ingredients', 2)
        min_instructions = self.config['migration'].get('min_instructions', 2)
        
        if len(recipe.ingredients) < min_ingredients:
            logger.warning(f"Recipe {recipe.title} has too few ingredients ({len(recipe.ingredients)})")
            return False
        
        if len(recipe.instructions) < min_instructions:
            logger.warning(f"Recipe {recipe.title} has too few instructions ({len(recipe.instructions)})")
            return False
        
        return True
    
    def normalize_recipes(self, onenote_recipes: List[OneNoteRecipe]) -> List[NormalizedRecipe]:
        """Normalize OneNote recipes for Tandoor compatibility."""
        console.print("[blue]Normalizing recipes for Tandoor...[/blue]")
        
        normalized_recipes = []
        
        with Progress() as progress:
            task = progress.add_task("Normalizing...", total=len(onenote_recipes))
            
            for recipe in onenote_recipes:
                try:
                    normalized = self.normalizer.normalize_recipe(recipe)
                    normalized_recipes.append(normalized)
                    self.stats['recipes_normalized'] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to normalize recipe {recipe.title}: {e}")
                    self.stats['recipes_failed'] += 1
                
                progress.update(task, advance=1)
        
        console.print(f"[green]Normalized {len(normalized_recipes)} recipes[/green]")
        return normalized_recipes
    
    async def upload_recipes(self, recipes: List[NormalizedRecipe]) -> Dict[str, List]:
        """Upload normalized recipes to Tandoor."""
        if self.config['migration'].get('dry_run', False):
            console.print("[yellow]DRY RUN MODE - No recipes will be uploaded[/yellow]")
            return self._simulate_upload(recipes)
        
        console.print("[blue]Uploading recipes to Tandoor...[/blue]")
        
        migration_config = self.config['migration']
        
        results = self.tandoor_client.batch_upload_recipes(
            recipes=recipes,
            skip_duplicates=migration_config.get('skip_duplicates', True),
            delay_between_requests=migration_config.get('delay_between_requests', 1.0)
        )
        
        # Update statistics
        self.stats['recipes_uploaded'] = len(results['success'])
        self.stats['recipes_failed'] += len(results['failed'])
        self.stats['recipes_skipped'] = len(results['skipped'])
        
        return results
    
    def _simulate_upload(self, recipes: List[NormalizedRecipe]) -> Dict[str, List]:
        """Simulate upload for dry run mode."""
        results = {
            'success': [],
            'failed': [],
            'skipped': []
        }
        
        for recipe in recipes:
            # Simulate checking for duplicates
            results['success'].append({
                'recipe': recipe.name,
                'id': 'DRY_RUN',
                'url': 'DRY_RUN_MODE'
            })
        
        self.stats['recipes_uploaded'] = len(recipes)
        return results
    
    def generate_reports(self, upload_results: Dict[str, List]):
        """Generate migration reports."""
        output_config = self.config.get('output', {})
        
        # Success report
        if output_config.get('create_success_report', True):
            success_file = output_config.get('success_report_file', 'migration_success.json')
            with open(success_file, 'w') as f:
                json.dump({
                    'timestamp': str(Path().absolute()),
                    'statistics': self.stats,
                    'successful_uploads': upload_results['success']
                }, f, indent=2)
            
            console.print(f"[green]Success report saved to: {success_file}[/green]")
        
        # Error report
        if upload_results['failed'] or upload_results['skipped']:
            error_file = output_config.get('error_report_file', 'migration_errors.json')
            with open(error_file, 'w') as f:
                json.dump({
                    'timestamp': str(Path().absolute()),
                    'failed_uploads': upload_results['failed'],
                    'skipped_uploads': upload_results['skipped']
                }, f, indent=2)
            
            console.print(f"[yellow]Error report saved to: {error_file}[/yellow]")
    
    def print_summary(self, upload_results: Dict[str, List]):
        """Print migration summary."""
        # Create summary table
        table = Table(title="Migration Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="magenta")
        
        table.add_row("Pages Scanned", str(self.stats['pages_scanned']))
        table.add_row("Recipes Found", str(self.stats['recipes_found']))
        table.add_row("Recipes Normalized", str(self.stats['recipes_normalized']))
        table.add_row("Recipes Uploaded", str(self.stats['recipes_uploaded']))
        table.add_row("Recipes Failed", str(self.stats['recipes_failed']))
        table.add_row("Recipes Skipped", str(self.stats['recipes_skipped']))
        
        console.print(table)
        
        # Show successful recipes
        if upload_results['success']:
            console.print("\n[green]Successfully Uploaded Recipes:[/green]")
            for result in upload_results['success'][:10]:  # Show first 10
                console.print(f"  • {result['recipe']} (ID: {result['id']})")
            
            if len(upload_results['success']) > 10:
                console.print(f"  ... and {len(upload_results['success']) - 10} more")
        
        # Show failed recipes
        if upload_results['failed']:
            console.print("\n[red]Failed Uploads:[/red]")
            for result in upload_results['failed'][:5]:  # Show first 5
                console.print(f"  • {result['recipe']}: {result['error']}")
    
    async def run_migration(self):
        """Execute the complete migration process."""
        try:
            console.print(Panel.fit("OneNote to Tandoor Recipe Migration", style="bold blue"))
            
            # Initialize clients
            self._initialize_clients()
            
            # Scan OneNote for recipes
            onenote_recipes = await self.scan_onenote_recipes()
            
            if not onenote_recipes:
                console.print("[yellow]No recipes found in OneNote. Exiting.[/yellow]")
                return
            
            # Normalize recipes
            normalized_recipes = self.normalize_recipes(onenote_recipes)
            
            if not normalized_recipes:
                console.print("[yellow]No recipes could be normalized. Exiting.[/yellow]")
                return
            
            # Upload to Tandoor
            upload_results = await self.upload_recipes(normalized_recipes)
            
            # Generate reports
            self.generate_reports(upload_results)
            
            # Print summary
            self.print_summary(upload_results)
            
            console.print("\n[green]Migration completed![/green]")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            console.print(f"[red]Migration failed: {e}[/red]")
            sys.exit(1)


@click.command()
@click.option('--config', default='config.yaml', help='Configuration file path')
@click.option('--dry-run', is_flag=True, help='Preview mode - no actual uploads')
@click.option('--notebook', help='Specific OneNote notebook to migrate')
@click.option('--page-filter', help='Filter pages by name (e.g., "recipes")')
@click.option('--no-browser', is_flag=True, help='Use device code auth instead of browser')
@click.option('--auth-code', help='Authorization code from Microsoft authentication')
@click.option('--skip-tandoor-auth', is_flag=True, help='Skip Tandoor authentication (for testing OneNote only)')
@click.option('--import-files', help='Import from files instead of OneNote API (directory path)')
@click.option('--verbose', is_flag=True, help='Enable verbose logging')
def main(config: str, dry_run: bool, notebook: str, page_filter: str, no_browser: bool, auth_code: str, skip_tandoor_auth: bool, import_files: str, verbose: bool):
    """OneNote to Tandoor Recipe Migration Tool."""
    
    # Override config with command line options
    if dry_run:
        os.environ['DRY_RUN'] = 'true'
    
    if notebook:
        os.environ['ONENOTE_NOTEBOOK_NAME'] = notebook
    
    if page_filter:
        os.environ['ONENOTE_PAGE_NAME_FILTER'] = page_filter
    
    if no_browser:
        os.environ['MICROSOFT_USE_INTERACTIVE_AUTH'] = 'false'
    
    if verbose:
        os.environ['LOG_LEVEL'] = 'DEBUG'
    
    if auth_code:
        os.environ['MICROSOFT_AUTH_CODE'] = auth_code
    
    if skip_tandoor_auth:
        os.environ['TANDOOR_SKIP_MSFT_AUTH'] = 'true'
    
    if import_files:
        os.environ['IMPORT_FILES_DIRECTORY'] = import_files
        os.environ['USE_FILE_IMPORT'] = 'true'
    
    # Create and run migration manager
    migration_manager = MigrationManager(config)
    
    # Run async migration
    asyncio.run(migration_manager.run_migration())


if __name__ == '__main__':
    main()