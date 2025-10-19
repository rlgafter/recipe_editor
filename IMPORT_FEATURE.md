# Recipe Import Feature

## Overview

The Recipe Editor now supports importing recipes from external sources using Google's Gemini AI. This feature automatically extracts recipe information and populates the recipe form, saving you time when adding recipes from websites, text files, or PDFs.

## Setup

### 1. Get a Gemini API Key

1. Visit [Google AI Studio](https://ai.google.dev/)
2. Sign in with your Google account
3. Get an API key

### 2. Configure the API Key

Create a `.env` file in the project root (or source it in your shell):

```bash
export GOOGLE_GEMINI_API_KEY="your_api_key_here"
```

Or create a `.env` file:

```
GOOGLE_GEMINI_API_KEY=your_api_key_here
```

Then source it:

```bash
source .env
```

## Usage

### Import from URL

1. Navigate to "New Recipe" page
2. In the "Import Recipe" section at the top, enter a URL in the "Import from URL" field
3. Click "Import" button
4. The recipe will be automatically extracted and populated in the form
5. Review and edit the extracted information as needed
6. Click "Create Recipe" to save

**Supported URL formats:**
- Recipe websites (e.g., AllRecipes, Food Network, etc.)
- Blog posts containing recipes
- Any webpage with recipe content

### Import from File

#### Drag and Drop

1. Navigate to "New Recipe" page
2. Drag a text file (.txt) or PDF file (.pdf) containing a recipe
3. Drop it onto the "Import from File" drop zone
4. The recipe will be automatically extracted and populated in the form

#### Select File

1. Navigate to "New Recipe" page
2. Click "Select File" button in the "Import from File" section
3. Choose a .txt or .pdf file
4. The recipe will be automatically extracted and populated in the form

**Supported file formats:**
- Text files (.txt, .text)
- PDF files (.pdf)

### Drag and Drop URLs

You can also drag a URL from your browser's address bar directly onto the drop zone, and it will be imported automatically.

## Features

### Automatic Extraction

The Gemini AI automatically extracts:

- Recipe name
- Ingredients (with amounts, units, and descriptions)
- Cooking instructions
- Notes and tips
- Recipe tags (e.g., "DESSERT", "QUICK", "VEGETARIAN")
- Source information (name, URL, author, publication)

### Source Attribution

The import feature automatically:
- Captures the URL as the source when importing from a webpage
- Uses the filename as the source when importing from a file
- Attempts to extract author information from the content
- Preserves attribution to respect recipe creators

### Review and Edit

After import:
- All extracted information appears in the recipe form
- You can review and edit any field before saving
- The form validates all required fields
- You can add or remove ingredients as needed

## Testing

A sample test recipe file is provided at `tmp/test_recipe.txt`. You can use this to test the file import functionality.

### Test the Import Feature

1. Start the server:
   ```bash
   source venv/bin/activate
   source .env  # Make sure your API key is set
   ./server start
   ```

2. Navigate to http://localhost:5000/recipe/new

3. Try importing:
   - **Test file**: Drag and drop `tmp/test_recipe.txt` onto the drop zone
   - **Test URL**: Try importing from a recipe website like:
     - https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/
     - https://www.foodnetwork.com/recipes/

## Troubleshooting

### "Gemini API is not configured" error

- Make sure you've set the `GOOGLE_GEMINI_API_KEY` environment variable
- Verify the API key is valid
- Restart the server after setting the environment variable

### "Could not extract recipe" error

- The content might not contain a clear recipe format
- Try a different source or file
- Check that the PDF is text-based (not scanned images)

### API Rate Limits

- Gemini API has rate limits based on your plan
- If you hit rate limits, wait a few minutes before trying again
- Consider upgrading your API plan if needed

## API Endpoints

The feature adds two new API endpoints:

### POST `/api/recipe/import/url`

Import a recipe from a URL.

**Request:**
```json
{
  "url": "https://example.com/recipe"
}
```

**Response:**
```json
{
  "success": true,
  "recipe": {
    "name": "Recipe Name",
    "ingredients": [...],
    "instructions": "...",
    "notes": "...",
    "tags": [...],
    "source": {...}
  }
}
```

### POST `/api/recipe/import/file`

Import a recipe from a file upload.

**Request:** multipart/form-data with `file` field

**Response:**
```json
{
  "success": true,
  "recipe": {
    "name": "Recipe Name",
    "ingredients": [...],
    "instructions": "...",
    "notes": "...",
    "tags": [...],
    "source": {...}
  }
}
```

## Privacy and Data

- Recipe content is sent to Google's Gemini API for extraction
- No recipe data is stored by the API beyond processing
- See Google's privacy policy for more information
- The API key is stored locally and never shared

## Future Enhancements

Potential future additions:
- Support for more file formats (Word docs, images with OCR)
- Batch import of multiple recipes
- Import from popular recipe management apps
- Custom extraction rules for specific websites

