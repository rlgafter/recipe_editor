# Recipe Editor - Design Documentation

## Overview
The Recipe Editor is a web-based application built with Python Flask that allows users to create, edit, view, and manage recipes. Recipes are stored as JSON files for simplicity and portability.

## Technology Stack

### Backend
- **Framework**: Flask 3.0+
- **Language**: Python 3.8+
- **Storage**: JSON file-based storage
- **Email**: SMTP (configurable for Gmail, SendGrid, or custom SMTP servers)
- **Logging**: Python's built-in logging module

### Frontend
- **Template Engine**: Jinja2 (Flask's default)
- **CSS Framework**: Bootstrap 5
- **JavaScript**: Vanilla JS for dynamic form elements
- **Icons**: Bootstrap Icons

## Architecture

### Application Structure
```
recipe_editor/
├── app.py                 # Main Flask application with routes
├── models.py             # Data models (Recipe, Tag)
├── storage.py            # JSON file storage management
├── config.py             # Configuration (SMTP, paths, etc.)
├── email_service.py      # Email sending functionality
├── utils.py              # Helper functions
├── templates/            # Jinja2 HTML templates
│   ├── base.html        # Base template with navigation
│   ├── recipe_form.html # Create/edit recipe form
│   ├── recipe_list.html # List all recipes with filtering
│   ├── recipe_view.html # Display single recipe
│   └── tag_manager.html # Manage tags
├── static/
│   ├── css/
│   │   └── style.css    # Custom styles
│   └── js/
│       └── app.js       # Client-side interactivity
├── data/
│   ├── recipes/         # JSON files for recipes
│   └── tags.json        # Tags file
├── logs/
│   └── app.log          # Application logs
├── requirements.txt      # Python dependencies
├── README.md            # User documentation
└── DESIGN.md            # This file
```

## Data Models

### Recipe Model
Each recipe is stored as a separate JSON file in `data/recipes/` directory.

```json
{
  "id": "recipe_001",
  "name": "Chocolate Chip Cookies",
  "ingredients": [
    {
      "amount": "1/2",
      "unit": "cup",
      "description": "butter, softened"
    },
    {
      "amount": "2",
      "unit": "cups",
      "description": "all-purpose flour"
    },
    {
      "amount": "",
      "unit": "pinch",
      "description": "salt"
    }
  ],
  "instructions": "1. Preheat oven to 350°F\n2. Mix butter and sugar\n3. Add flour gradually",
  "notes": "Best served warm. Can be frozen for up to 3 months.",
  "tags": ["dessert", "cookies", "baking"],
  "created_at": "2025-10-10T10:30:00",
  "updated_at": "2025-10-10T10:30:00",
  "user_id": null,
  "rating": null,
  "favorites": []
}
```

**Field Specifications**:
- `id` (string, required): Unique identifier (auto-generated)
- `name` (string, required): Recipe name
- `ingredients` (array, required): List of ingredient objects (minimum 1)
  - `amount` (string, optional): Numeric value or fraction (e.g., "1/2", "2.5")
  - `unit` (string, optional): Measurement unit (pinch, piece(s), cup(s), oz, TBS, tsp, can, etc.)
  - `description` (string, required): Ingredient description
- `instructions` (string, optional): Step-by-step instructions
- `notes` (string, optional): Additional notes
- `tags` (array): List of tag names (case-insensitive)
- `created_at` (string): ISO 8601 timestamp
- `updated_at` (string): ISO 8601 timestamp
- `user_id` (string, nullable): For future user authentication
- `rating` (float, nullable): For future rating feature
- `favorites` (array): For future favorites feature (list of user_ids)

### Tags Model
Tags are stored in a single `data/tags.json` file that maintains tag-to-recipe associations.

```json
{
  "dessert": {
    "recipes": ["recipe_001", "recipe_003", "recipe_007"],
    "created_at": "2025-10-10T10:30:00"
  },
  "cookies": {
    "recipes": ["recipe_001"],
    "created_at": "2025-10-10T10:30:00"
  },
  "vegan": {
    "recipes": ["recipe_003", "recipe_005"],
    "created_at": "2025-10-10T10:30:00"
  }
}
```

**Tag Rules**:
- Tag names are case-insensitive (stored in lowercase)
- Tag names must be unique
- Tags cannot be deleted or renamed if associated with any recipes
- Tags are automatically created when used in a recipe
- Tags are automatically removed when no recipes reference them

## Core Functionality

### 1. Recipe Management

#### Create Recipe (`/recipe/new`)
- Form with all recipe fields
- Dynamic ingredient list (add/remove rows)
- Tag selection with visual feedback
- Validation: name required, at least one ingredient required
- Auto-generates unique ID on save

#### Edit Recipe (`/recipe/<id>/edit`)
- Same form as create, pre-populated with existing data
- Updates `updated_at` timestamp
- Maintains `created_at` and `id`

#### View Recipe (`/recipe/<id>`)
- Displays formatted recipe
- Buttons: Edit, Delete, Print, Email
- Print button triggers browser print dialog with print-optimized CSS
- Email button opens email form

#### Delete Recipe (`/recipe/<id>/delete`)
- Confirmation prompt
- Removes recipe JSON file
- Updates tags.json to remove recipe from all tag associations
- Redirects to recipe list

### 2. Recipe List (`/` or `/recipes`)
- Displays all recipes as cards or table rows
- Each recipe shows: name, tags
- Recipe names are links to view page
- Tag-based filtering:
  - Multi-select tag filter
  - Supports AND/OR filtering logic
  - Updates list dynamically
- Search functionality (optional future enhancement)

### 3. Tag Management (`/tags`)
- List all tags with recipe counts
- Add new tag form
- Edit tag name (only if no recipes associated)
- Delete tag (only if no recipes associated)
- Visual indication of protected tags

### 4. Email Recipe
- Form to enter recipient email and optional message
- Sends formatted recipe via SMTP
- Configuration in `config.py` for SMTP settings
- Error handling for failed sends
- Success/failure feedback to user

## Configuration

### config.py
```python
import os

# Flask Configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
HOST = '0.0.0.0'
PORT = 5000

# Storage Configuration
DATA_DIR = 'data'
RECIPES_DIR = os.path.join(DATA_DIR, 'recipes')
TAGS_FILE = os.path.join(DATA_DIR, 'tags.json')
LOGS_DIR = 'logs'
LOG_FILE = os.path.join(LOGS_DIR, 'app.log')

# Email Configuration
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'True') == 'True'
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', SMTP_USERNAME)
SENDER_NAME = 'Recipe Editor'
```

## Logging

### Log Levels
- **INFO**: Normal operations (recipe created, edited, deleted, email sent)
- **WARNING**: Recoverable errors (invalid email configuration, missing optional fields)
- **ERROR**: Errors that prevent operations (file I/O errors, email send failures)
- **DEBUG**: Detailed information for troubleshooting

### Log Format
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### Log File
- Location: `logs/app.log`
- Rotation: Not implemented initially (can add RotatingFileHandler later)
- Both file and console logging enabled

## Frontend Design

### User Interface
- Clean, modern design using Bootstrap 5
- Responsive layout (mobile-friendly)
- Consistent navigation across all pages
- Form validation with user feedback
- Loading indicators for async operations

### Dynamic Elements (JavaScript)
1. **Ingredient Management**:
   - "Add Ingredient" button appends new row
   - "Remove" button on each row (except first)
   - Rows numbered automatically

2. **Tag Selection**:
   - Checkbox list or tag pills
   - Visual feedback for selected tags
   - Display count of selected tags

3. **Recipe Filtering**:
   - Live filtering as tags selected
   - Clear filters button
   - Recipe count display

4. **Email Form**:
   - Modal or separate form
   - Email validation
   - Send button with loading state

### Print Stylesheet
- Hide navigation, buttons, and non-essential UI
- Optimize layout for paper (A4/Letter)
- Ensure ingredient list and instructions are readable
- Page break handling for long recipes

## Error Handling

### Storage Errors
- Handle missing directories (create automatically)
- Handle corrupted JSON files (log error, skip file)
- Handle file permission issues

### Validation Errors
- Display user-friendly error messages
- Highlight invalid fields
- Preserve user input on validation failure

### Email Errors
- Handle SMTP connection failures
- Handle authentication errors
- Handle invalid recipient addresses
- Provide clear feedback to user

## Future Enhancements

### User Authentication (Planned)
- User registration and login
- Password hashing (bcrypt)
- Session management
- User-specific recipe lists
- Recipe ownership (only owner can edit/delete)

### User Features (Planned)
- User profile page
- "My Recipes" page (recipes created by user)
- "Favorite Recipes" (recipes marked as favorites)
- Recipe rating system (1-5 stars)
- Public vs. private recipes

### Data Model Changes for User Features
```json
{
  "user_id": "user_123",
  "rating": 4.5,
  "ratings_count": 12,
  "favorites": ["user_456", "user_789"],
  "is_public": true
}
```

### Additional Future Features
- Recipe import/export (CSV, PDF)
- Recipe sharing via link
- Recipe comments
- Ingredient shopping list generator
- Nutrition information
- Recipe photos/images
- Recipe search (full-text)
- Recipe categories (in addition to tags)
- Recipe duplication
- Recipe version history

## Security Considerations

### Current Implementation
- No user authentication yet
- SMTP credentials via environment variables (not hardcoded)
- Input sanitization for recipe fields
- No SQL injection risk (JSON file storage)

### For Future User Authentication
- Password hashing with bcrypt
- Session management with secure cookies
- CSRF protection
- Rate limiting for login attempts
- Email verification for new accounts
- Password reset functionality

## Testing Strategy

### Manual Testing (Initial)
- Create recipes with various ingredient combinations
- Edit existing recipes
- Delete recipes and verify tag cleanup
- Test tag management (create, edit, delete with constraints)
- Test email functionality with valid/invalid addresses
- Test filtering with multiple tags
- Test print functionality
- Test responsive design on different screen sizes

### Automated Testing (Future)
- Unit tests for models and storage layer
- Integration tests for routes
- UI tests with Selenium
- Email sending tests (mock SMTP)

## Deployment Considerations

### Development
- Run locally with Flask development server
- Debug mode enabled
- Use environment variables for configuration

### Production (Future)
- Use production WSGI server (Gunicorn, uWSGI)
- Set DEBUG=False
- Use proper secret key
- Configure proper SMTP service
- Set up SSL/TLS
- Use reverse proxy (nginx)
- Consider containerization (Docker)
- Database migration (SQLite/PostgreSQL) for scalability

## Performance Considerations

### Current Scale
- Suitable for <1000 recipes
- JSON file parsing overhead acceptable
- No caching needed initially

### Future Optimization
- Implement caching for recipe list
- Database migration for >1000 recipes
- Lazy loading for recipe list
- Pagination for large result sets
- Index on tags for faster filtering

## Accessibility

- Semantic HTML5 elements
- ARIA labels where appropriate
- Keyboard navigation support
- Color contrast compliance (WCAG 2.1)
- Alt text for images (when image feature added)
- Screen reader friendly

## Browser Compatibility

- Modern browsers (Chrome, Firefox, Safari, Edge)
- ES6 JavaScript support required
- CSS Grid and Flexbox support required

---

## Revision History

- **2025-10-10**: Initial design document created

