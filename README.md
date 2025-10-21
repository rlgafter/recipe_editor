# Recipe Editor

A web-based recipe management application built with Python Flask. Create, edit, organize, and share your favorite recipes with ease.

## Features

- 📝 **Recipe Management**: Create, edit, view, and delete recipes
- 🤖 **AI-Powered Import**: Import recipes from URLs, text files, or PDFs using Google Gemini AI
- 🏷️ **Tag System**: Organize recipes with custom tags
- 🔍 **Smart Filtering**: Filter recipes by single or multiple tags
- 📧 **Email Sharing**: Send beautifully formatted recipes via email
- 🖨️ **Print Support**: Print-optimized recipe layout
- 📱 **Responsive Design**: Works on desktop, tablet, and mobile devices
- 💾 **Flexible Storage**: JSON file-based storage (default) or MySQL database
- 👥 **Multi-User Ready**: MySQL backend supports user authentication and personal recipe collections

## Table of Contents

- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Running the Application](#running-the-application)
- [Usage Guide](#usage-guide)
  - [Importing Recipes (AI-Powered)](#importing-recipes-ai-powered)
  - [Creating Recipes](#creating-recipes)
  - [Managing Tags](#managing-tags)
  - [Filtering Recipes](#filtering-recipes)
  - [Emailing Recipes](#emailing-recipes)
- [Project Structure](#project-structure)
- [Configuration Options](#configuration-options)
- [Troubleshooting](#troubleshooting)
- [Future Features](#future-features)

## Getting Started

### Prerequisites

- **Python 3.8 or higher**: [Download Python](https://www.python.org/downloads/)
- **pip**: Python package installer (usually comes with Python)
- **Git**: For cloning the repository

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/rlgafter/recipe_editor.git
   cd recipe_editor
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate

   # On Windows
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation**:
   ```bash
   python --version  # Should be 3.8 or higher
   pip list          # Should show Flask and dependencies
   ```

### Configuration

The application uses environment variables for configuration. You can set these in your shell or create a `.env` file (requires `python-dotenv`).

#### Basic Configuration

No configuration is needed for basic usage. The app will run with default settings.

#### Recipe Import Configuration (Optional)

To enable AI-powered recipe import, configure Google Gemini API:

```bash
# Get your API key from https://ai.google.dev/
export GOOGLE_GEMINI_API_KEY=your_api_key_here
```

See [IMPORT_FEATURE.md](IMPORT_FEATURE.md) for detailed setup instructions.

#### Email Configuration (Optional)

To enable email functionality, configure SMTP settings:

```bash
# Example for Gmail
export SMTP_SERVER=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USERNAME=your-email@gmail.com
export SMTP_PASSWORD=your-app-specific-password
export SENDER_EMAIL=your-email@gmail.com
export SENDER_NAME="Recipe Editor"
```

**Gmail Setup**:
1. Enable 2-factor authentication on your Google account
2. Generate an "App Password" at https://myaccount.google.com/apppasswords
3. Use the app password as `SMTP_PASSWORD`

**Other Email Providers**:
- **Outlook/Hotmail**: `smtp.office365.com`, port `587`
- **Yahoo**: `smtp.mail.yahoo.com`, port `587`
- **SendGrid**: `smtp.sendgrid.net`, port `587`

#### Advanced Configuration

```bash
# Flask Settings
export SECRET_KEY=your-secret-key-here
export DEBUG=False
export HOST=0.0.0.0
export PORT=5000

# SMTP Settings (with TLS)
export SMTP_USE_TLS=True
```

### Running the Application

1. **Start the server**:
   ```bash
   python app.py
   ```

2. **Access the application**:
   - Open your web browser
   - Navigate to: `http://localhost:5000`
   - You should see the Recipe Editor interface

3. **Stop the server**:
   - Press `Ctrl+C` in the terminal

## Usage Guide

### Importing Recipes (AI-Powered)

> **Note**: Recipe import requires a Google Gemini API key (see [Configuration](#configuration))

The Recipe Editor can automatically extract recipes from websites, text files, and PDFs using AI.

#### Import from URL

1. Click **"New Recipe"** in the navigation bar
2. In the "Import Recipe" section, enter a recipe URL
3. Click **"Import"**
4. The recipe is automatically extracted and populated in the form
5. Review and edit as needed, then click **"Create Recipe"**

**Example URLs**:
- `https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/`
- Any recipe blog or website

#### Import from File

1. Click **"New Recipe"**
2. **Drag and drop** a text or PDF file onto the drop zone, OR
3. Click **"Select File"** to browse for a file
4. The recipe is automatically extracted and populated
5. Review and edit as needed, then click **"Create Recipe"**

**Supported formats**: `.txt`, `.pdf`

#### What Gets Extracted

The AI automatically extracts:
- Recipe name
- Ingredients (amounts, units, descriptions)
- Instructions
- Notes and tips
- Tags (e.g., DESSERT, VEGETARIAN)
- Source attribution (URL, author, publication)

For detailed documentation, see [IMPORT_FEATURE.md](IMPORT_FEATURE.md).

### Creating Recipes

1. Click **"New Recipe"** in the navigation bar or on the recipes page
2. Fill in the recipe details:
   - **Name** (required): Enter the recipe name
   - **Ingredients** (at least one required):
     - Amount: Optional, supports fractions (e.g., `1/2`, `1 1/2`, `2.5`)
     - Unit: Optional (e.g., `cup`, `tsp`, `oz`)
     - Description: Required (e.g., `all-purpose flour`)
     - Click "Add Ingredient" for more ingredients
   - **Instructions**: Optional, step-by-step cooking instructions
   - **Notes**: Optional, additional tips or information
   - **Tags**: Optional, select existing tags or enter new ones (comma-separated)
3. Click **"Create Recipe"**
4. Your recipe is saved and displayed

### Editing Recipes

1. Navigate to a recipe (click on its name in the recipe list)
2. Click the **"Edit"** button
3. Make your changes
4. Click **"Update Recipe"**

### Deleting Recipes

1. Navigate to a recipe
2. Click the **"Delete"** button
3. Confirm deletion in the modal dialog

### Managing Tags

Tags help organize and categorize your recipes.

1. Click **"Manage Tags"** in the navigation bar
2. View all existing tags with their recipe counts
3. **Create a tag**: Enter a name and click "Add Tag" (optional, tags are auto-created)
4. **Edit a tag**: Click "Edit" (only available for tags with no recipes)
5. **Delete a tag**: Click "Delete" (only available for tags with no recipes)

**Tag Rules**:
- Tag names are case-insensitive (stored as uppercase)
- Tags must be unique
- Tags with associated recipes cannot be edited or deleted
- Unused tags are automatically removed

### Filtering Recipes

1. On the **Recipes** page, use the left sidebar to filter
2. Select one or more tags using checkboxes
3. Choose match type:
   - **Any selected tag**: Shows recipes with at least one selected tag
   - **All selected tags**: Shows recipes with all selected tags
4. Click **"Apply Filter"**
5. Click **"Clear Filter"** to see all recipes again

### Viewing Recipes

1. Click on any recipe name in the recipe list
2. View the full recipe with ingredients, instructions, and notes
3. Available actions:
   - **Edit**: Modify the recipe
   - **Print**: Open print dialog with print-optimized layout
   - **Email**: Send recipe via email (if configured)
   - **Delete**: Remove the recipe

### Emailing Recipes

> **Note**: Email functionality requires SMTP configuration (see [Configuration](#configuration))

1. Navigate to a recipe
2. Click the **"Email"** button
3. Fill in the email form:
   - Recipient email (required)
   - Recipient name (optional)
   - Personal message (optional)
4. Click **"Send Email"**
5. The recipe will be sent as a formatted HTML email

### Printing Recipes

1. Navigate to a recipe
2. Click the **"Print"** button
3. Your browser's print dialog will open
4. The recipe is automatically formatted for printing (no navigation, buttons, etc.)
5. Print or save as PDF

## Project Structure

```
recipe_editor/
├── app.py                    # Main Flask application
├── models.py                 # Data models (Recipe, Ingredient, Tag)
├── storage.py                # JSON storage management
├── config.py                 # Configuration settings
├── email_service.py          # Email functionality
├── gemini_service.py         # AI-powered recipe extraction
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── DESIGN.md                 # Design documentation
├── IMPORT_FEATURE.md         # Recipe import documentation
│
├── templates/                # HTML templates (Jinja2)
│   ├── base.html            # Base template with navigation
│   ├── recipe_list.html     # Recipe list with filtering
│   ├── recipe_view.html     # Single recipe display
│   ├── recipe_form.html     # Create/edit recipe form
│   ├── recipe_email.html    # Email recipe form
│   ├── tag_manager.html     # Tag management
│   ├── 404.html             # Not found page
│   └── 500.html             # Error page
│
├── static/                   # Static assets
│   ├── css/
│   │   └── style.css        # Custom styles
│   └── js/
│       └── app.js           # Client-side JavaScript
│
├── data/                     # Data storage (created automatically)
│   ├── recipes/             # Recipe JSON files
│   │   ├── recipe_001.json
│   │   ├── recipe_002.json
│   │   └── ...
│   └── tags.json            # Tag associations
│
└── logs/                     # Application logs (created automatically)
    └── app.log              # Log file
```

## Configuration Options

All configuration is done via environment variables or in `config.py`.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key for sessions | `dev-secret-key-change-in-production` |
| `DEBUG` | Enable debug mode | `True` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `5000` |
| `SMTP_SERVER` | SMTP server address | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USERNAME` | SMTP username/email | ` ` |
| `SMTP_PASSWORD` | SMTP password | ` ` |
| `SMTP_USE_TLS` | Use TLS encryption | `True` |
| `SENDER_EMAIL` | From email address | Same as `SMTP_USERNAME` |
| `SENDER_NAME` | From name | `Recipe Editor` |
| `GOOGLE_GEMINI_API_KEY` | Google Gemini API key for recipe import | ` ` |

### Setting Environment Variables

**macOS/Linux**:
```bash
export VARIABLE_NAME=value
```

**Windows (Command Prompt)**:
```cmd
set VARIABLE_NAME=value
```

**Windows (PowerShell)**:
```powershell
$env:VARIABLE_NAME="value"
```

## Data Storage

### JSON Storage (Default)

Recipes are stored as JSON files in the `data/recipes/` directory. Each recipe has its own file (e.g., `recipe_001.json`). Tags and their associations are stored in `data/tags.json`.

### MySQL Storage (Optional - Multi-User)

For multi-user support with advanced features, you can migrate to MySQL. See [MYSQL_MIGRATION.md](MYSQL_MIGRATION.md) for complete setup instructions.

**MySQL features:**
- User authentication and profiles
- Normalized ingredient catalog
- Search recipes by ingredient
- Collections/cookbooks
- Meal planning
- Favorites and ratings
- Public/private recipes
- Advanced analytics

### Backup

To backup your recipes:
```bash
# Copy the entire data directory
cp -r data data_backup_$(date +%Y%m%d)
```

### Restore

To restore from backup:
```bash
# Replace data directory with backup
rm -rf data
cp -r data_backup_YYYYMMDD data
```

## Troubleshooting

### Application won't start

**Error**: `ModuleNotFoundError: No module named 'flask'`
- **Solution**: Install dependencies: `pip install -r requirements.txt`

**Error**: `Address already in use`
- **Solution**: Another application is using port 5000. Either:
  - Stop the other application
  - Change the port: `export PORT=8000`

### Email not working

**Error**: `Email service is not configured`
- **Solution**: Set SMTP environment variables (see [Email Configuration](#email-configuration-optional))

**Error**: `SMTP authentication failed`
- **Solution**: 
  - Check your username and password
  - For Gmail, use an app-specific password
  - Ensure 2FA is enabled (for Gmail)

**Error**: `Connection refused` or `timed out`
- **Solution**:
  - Check your internet connection
  - Verify SMTP server and port
  - Check firewall settings

### Recipes not displaying

1. Check `data/recipes/` directory exists and contains JSON files
2. Check `logs/app.log` for errors
3. Verify JSON files are not corrupted

### Tags not working

1. Check `data/tags.json` exists
2. Verify the file contains valid JSON
3. Check logs for errors

### Recipe import not working

**Error**: `Gemini API is not configured`
- **Solution**: Set `GOOGLE_GEMINI_API_KEY` environment variable (see [IMPORT_FEATURE.md](IMPORT_FEATURE.md))

**Error**: `Could not extract recipe`
- **Solution**: 
  - Ensure the content contains a clear recipe format
  - Try a different source or file
  - For PDFs, ensure they contain text (not just images)

### Performance issues

If you have many recipes (>1000):
- Consider migrating to a database (see [DESIGN.md](DESIGN.md))
- Reduce logging level in `config.py`

## Development

### Running in Debug Mode

Debug mode provides detailed error messages and auto-reloads on code changes:

```bash
export DEBUG=True
python app.py
```

### Viewing Logs

```bash
# View recent logs
tail -f logs/app.log

# View all logs
cat logs/app.log
```

### Testing Email Without SMTP

To test email functionality without SMTP, check `logs/app.log` for email content (in debug mode).

## Future Features

The following features are planned for future releases:

- **User Authentication**: User registration, login, and sessions
- **User Profiles**: Personal recipe collections and favorites
- **Recipe Ratings**: 5-star rating system
- **Recipe Photos**: Upload and display images
- **Recipe Search**: Full-text search functionality
- **Import/Export**: CSV and PDF export
- **Recipe Sharing**: Public links for sharing
- **Nutrition Info**: Calorie and nutrition tracking
- **Shopping Lists**: Generate ingredient lists
- **Database Backend**: SQLite/PostgreSQL for better performance
- **Enhanced Import**: Image recognition (OCR) for scanned recipes, batch imports

See [DESIGN.md](DESIGN.md) for detailed design documentation and future planning.

## Contributing

This is a personal project, but suggestions and bug reports are welcome! Please open an issue on GitHub.

## License

This project is open source and available for personal use.

## Support

For issues, questions, or suggestions:
1. Check this README and [DESIGN.md](DESIGN.md)
2. Check the logs: `logs/app.log`
3. Open an issue on GitHub: https://github.com/rlgafter/recipe_editor/issues

---

**Enjoy your recipe management!** 🍳📖
