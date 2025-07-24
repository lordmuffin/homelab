# OneNote to Tandoor Recipe Migration

Automated migration tool for transferring recipes from Microsoft OneNote to Tandoor Recipes.

## Architecture

```
OneNote → Microsoft Graph API → Recipe Parser → Tandoor API → Imported Recipes
```

## Features

- **Automated Discovery**: Scans OneNote notebooks for recipe content
- **Intelligent Parsing**: Extracts ingredients, instructions, and metadata
- **Batch Processing**: Handles multiple recipes efficiently
- **Error Recovery**: Robust error handling with retry logic
- **Progress Tracking**: Real-time migration status
- **Duplicate Detection**: Prevents importing duplicate recipes
- **Image Migration**: Transfers recipe photos from OneNote

## Quick Start

```bash
# Using Docker
docker run -it --env-file .env onenote-tandoor-migrator

# Using Python
pip install -r requirements.txt
python migrate.py --config config.yaml
```

## Configuration

Set environment variables or create `.env` file:

```env
# Microsoft Graph API
MICROSOFT_CLIENT_ID=your_client_id
MICROSOFT_CLIENT_SECRET=your_client_secret
MICROSOFT_TENANT_ID=your_tenant_id

# Tandoor API
TANDOOR_URL=https://recipes.yourdomain.com
TANDOOR_API_TOKEN=your_api_token

# Migration Settings
ONENOTE_NOTEBOOK_NAME=Recipes
BATCH_SIZE=10
DRY_RUN=false
```

## Usage Examples

```bash
# Dry run to preview what would be migrated
python migrate.py --dry-run

# Migrate specific notebook
python migrate.py --notebook "Family Recipes"

# Resume failed migration
python migrate.py --resume

# Migrate with custom mapping
python migrate.py --config custom-config.yaml
```

## Recipe Format Detection

The tool automatically detects recipes in OneNote using:
- Common recipe headers (Ingredients, Instructions, Directions)
- Structured lists and numbered steps
- Recipe-specific keywords and patterns
- Image content analysis

## Supported OneNote Formats

- Text-based recipes with clear structure
- Bulleted ingredient lists
- Numbered instruction steps
- Embedded images and photos
- Tables with ingredient measurements
- Handwritten notes (OCR processed)

## Output

- **Success Log**: Successfully migrated recipes
- **Error Log**: Failed migrations with reasons
- **Duplicate Log**: Skipped duplicate recipes
- **Summary Report**: Migration statistics and recommendations