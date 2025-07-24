# OneNote Manual Export Migration Guide

Since personal Microsoft accounts cannot access OneNote through the Graph API due to SharePoint licensing requirements, this guide provides alternative approaches to migrate your recipes from OneNote to Tandoor.

## Method 1: OneNote Web Export (Recommended)

### Step 1: Export from OneNote Web
1. Go to [OneNote Online](https://onenote.com) and sign in with your personal account
2. Open your recipes notebook
3. Navigate to each recipe page you want to export
4. Use **File → Export → Export as Word Document (.docx)** or **Export as PDF**
5. Save each recipe to a local folder (e.g., `exported_recipes/`)

### Step 2: Convert Exported Files
The migration tool can be enhanced to parse exported Word documents or PDFs:

```bash
# Process exported files
python migrate.py --import-files exported_recipes/ --dry-run
```

## Method 2: OneNote Desktop Export

### Step 1: Export from OneNote Desktop
1. Open OneNote desktop application
2. Navigate to your recipes notebook/section
3. Select all recipe pages
4. Use **File → Export → Export as Web Page (.html)** or **Word Document (.docx)**
5. Choose "Export all" or select specific pages

### Step 2: Process HTML/Word Files
```bash
# Process HTML exports
python migrate.py --import-html exported_recipes/ --page-filter "recipes" --dry-run

# Process Word exports  
python migrate.py --import-docx exported_recipes/ --page-filter "recipes" --dry-run
```

## Method 3: Copy-Paste Approach

### Step 1: Manual Copy
1. Open OneNote in web browser
2. Navigate to each recipe page
3. Select all content (Ctrl+A)
4. Copy to clipboard (Ctrl+C)
5. Paste into a text file or Word document
6. Save with recipe name as filename

### Step 2: Process Text Files
```bash
# Process text files
python migrate.py --import-text exported_recipes/ --dry-run
```

## Method 4: Screenshot to OCR (Last Resort)

If other methods don't work:
1. Take screenshots of recipe pages
2. Use OCR tools to extract text
3. Manually format into recipe structure
4. Import as text files

## Enhanced Migration Tool Features

The migration tool will be enhanced to support:

- **Document Parsing**: Parse Word documents (.docx) for recipe content
- **HTML Processing**: Extract recipes from exported HTML files  
- **Text Recognition**: Parse plain text files with recipe detection
- **Content Normalization**: Clean and structure extracted content
- **Batch Processing**: Handle multiple files automatically

## Configuration

Update your `.env` file to skip OneNote API and use file import:

```env
# Skip OneNote API (use file import instead)
USE_ONENOTE_API=false

# File import settings
IMPORT_DIRECTORY=exported_recipes/
IMPORT_FORMAT=docx  # or html, text, pdf
RECIPE_DETECTION_KEYWORDS=recipe,ingredients,instructions,directions
```

## Tandoor Integration

The Tandoor integration remains the same - the tool will:
1. Parse exported files instead of OneNote API
2. Normalize recipe data
3. Upload to Tandoor with Microsoft middleware authentication
4. Generate migration reports

## Next Steps

1. Choose your preferred export method
2. Export your OneNote recipes
3. Run the enhanced migration tool with file import
4. Review and validate imported recipes in Tandoor

This approach bypasses the SharePoint licensing limitation while preserving all your recipe data.