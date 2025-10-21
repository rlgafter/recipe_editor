# MySQL Migration Guide - Recipe Editor

## Overview

This guide will walk you through migrating from JSON file storage to a MySQL database with multi-user support, normalized ingredients, and advanced features.

---

## Prerequisites

### 1. MySQL Server

You need MySQL 5.7+ or MariaDB 10.2+ installed.

**Install MySQL on macOS:**
```bash
# Using Homebrew
brew install mysql

# Start MySQL service
brew services start mysql

# Secure installation (set root password)
mysql_secure_installation
```

**Install MySQL on Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
sudo mysql_secure_installation
```

### 2. Python Dependencies

Already installed via requirements.txt:
- mysql-connector-python
- SQLAlchemy
- Flask-SQLAlchemy
- Flask-Login
- bcrypt

---

## Setup Steps

### Step 1: Create MySQL Database User

Connect to MySQL as root:
```bash
mysql -u root -p
```

Create database and user:
```sql
CREATE DATABASE recipe_editor 
    DEFAULT CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

CREATE USER 'recipe_user'@'localhost' IDENTIFIED BY 'your_secure_password';

GRANT ALL PRIVILEGES ON recipe_editor.* TO 'recipe_user'@'localhost';

FLUSH PRIVILEGES;

EXIT;
```

### Step 2: Configure Environment Variables

Create or update your `.env` file:

```bash
# MySQL Configuration
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=recipe_user
export MYSQL_PASSWORD=your_secure_password
export MYSQL_DATABASE=recipe_editor

# Optional: Enable SQL query logging for debugging
export SQL_ECHO=False

# Load environment variables
source .env
```

### Step 3: Initialize Database Schema

Run the initialization script:

```bash
cd /Users/rickileegafter/recipe_editor
source venv/bin/activate
source .env
python scripts/init_database.py
```

This will:
- Create the database (if it doesn't exist)
- Create all 14 tables
- Set up triggers for statistics
- Insert common ingredients
- Create database views

**Expected output:**
```
======================================================================
Recipe Editor - Database Initialization
======================================================================

MySQL Configuration:
  Host: localhost
  Port: 3306
  User: recipe_user
  Database: recipe_editor

[1/4] Connecting to MySQL server...
✓ Connected to MySQL server

[2/4] Creating database 'recipe_editor'...
✓ Database 'recipe_editor' ready

[3/4] Executing schema SQL...
✓ Executed 50+ SQL statements

[4/4] Verifying database structure...
✓ Found 14 tables:
   - collection_recipes
   - collections
   - ingredients
   ... (and 11 more)

======================================================================
✅ Database initialization complete!
======================================================================
```

### Step 4: Migrate Existing JSON Data

**IMPORTANT:** Back up your JSON data first!

```bash
# Backup your data
cp -r data data_backup_$(date +%Y%m%d)
```

Run the migration:

```bash
python scripts/migrate_json_to_mysql.py
```

This will:
- Create a default admin user (username: `admin`, password: `migration123`)
- Parse your JSON recipes
- Extract and normalize ingredients
- Create ingredient catalog entries
- Link recipes to normalized ingredients
- Migrate tags
- Create recipe stats

**Expected output:**
```
[1/5] Creating default migration user...
✓ Created user 'admin' (ID: 1)
  Default password: migration123 (CHANGE THIS!)

[2/5] Found 5 recipe files to migrate

[3/5] Migrating recipes...
✓ Migrated: Classic Chocolate Chip Cookies (recipe_001.json)
✓ Migrated: Creamy Tomato Soup (recipe_002.json)
...

[4/5] Updating statistics...

[5/5] Migration Summary:
  ✓ Recipes migrated: 5
  ✗ Errors: 0

======================================================================
✅ Migration complete!
======================================================================
```

### Step 5: Create Your User Account

Change the default admin password or create a new user:

```bash
python scripts/create_user.py
```

Follow the prompts:
```
Username: yourname
Email: you@example.com
Password: ********
Confirm password: ********

Make this user an admin? (y/N): y

✅ User created successfully!
```

### Step 6: Update Application Configuration

The application needs to know to use MySQL. We'll create this in the next phase, but for now, verify your setup works:

```bash
# Test database connection
python -c "import db_config; success, msg = db_config.test_connection(); print(msg)"
```

Should output:
```
Database connection successful
```

---

## Database Structure

### Tables Overview (14 total):

**User Management (3):**
- `users` - User accounts
- `user_preferences` - Settings and preferences
- `password_reset_tokens` - Password recovery

**Ingredients (3):**
- `ingredients` - Master ingredient catalog
- `recipe_ingredients` - Recipe-ingredient junction
- `user_ingredient_substitutions` - Personal substitutions

**Recipes (3):**
- `recipes` - Main recipe data
- `recipe_sources` - Attribution info
- `recipe_photos` - Multiple photos per recipe

**Organization (2):**
- `tags` - Recipe tags
- `recipe_tags` - Recipe-tag relationships

**Interactions (3):**
- `recipe_favorites` - User favorites
- `recipe_ratings` - Ratings and reviews
- `collections` + `collection_recipes` - Cookbooks

**Planning (2):**
- `meal_plans` - Meal planning
- `meal_plan_recipes` - Planned recipes

**Tracking (1):**
- `recipe_stats` - Cached statistics
- `user_stats` - User statistics
- `recipe_email_log` - Email sharing log

---

## Key Features

### Normalized Ingredients
- Search for recipes by ingredient name
- Autocomplete ingredients from catalog
- Track ingredient usage across all recipes
- Allergen information per ingredient
- User-specific ingredient substitutions

### Multi-User Support
- User registration and authentication
- Personal recipe collections
- Public/private/unlisted recipes
- User profiles and preferences

### Organization
- Collections/cookbooks
- Favorites with personal notes
- Meal planning calendar
- Tag system with categories

### Analytics
- Recipe view counts
- Ratings and reviews
- Popular recipes
- User statistics

---

## Common Operations

### View Database Tables
```bash
mysql -u recipe_user -p recipe_editor
```

```sql
-- Show all tables
SHOW TABLES;

-- Count recipes
SELECT COUNT(*) FROM recipes;

-- Count ingredients
SELECT COUNT(*) FROM ingredients;

-- View users
SELECT id, username, email, is_admin FROM users;

-- Most used ingredients
SELECT name, usage_count 
FROM ingredients 
ORDER BY usage_count DESC 
LIMIT 10;
```

### Backup Database
```bash
mysqldump -u recipe_user -p recipe_editor > backup_$(date +%Y%m%d).sql
```

### Restore Database
```bash
mysql -u recipe_user -p recipe_editor < backup_20251021.sql
```

---

## Troubleshooting

### "Access denied for user"
- Check MySQL user exists: `SELECT user FROM mysql.user WHERE user='recipe_user';`
- Check grants: `SHOW GRANTS FOR 'recipe_user'@'localhost';`
- Verify password in .env file

### "Can't connect to MySQL server"
- Check MySQL is running: `brew services list` (macOS) or `systemctl status mysql` (Linux)
- Check port: `mysql -u root -p -e "SHOW VARIABLES LIKE 'port';"`
- Check hostname: try `127.0.0.1` instead of `localhost`

### "Database does not exist"
- Run `python scripts/init_database.py` first
- Or create manually: `mysql -u root -p -e "CREATE DATABASE recipe_editor;"`

### "Table already exists"
- Normal during re-runs of init_database.py
- To start fresh: `DROP DATABASE recipe_editor; CREATE DATABASE recipe_editor;`

### "Incorrect password"
- Update .env file with correct password
- Or reset: `ALTER USER 'recipe_user'@'localhost' IDENTIFIED BY 'new_password';`

### Migration Errors
- Check JSON files are valid: `python -m json.tool data/recipes/recipe_001.json`
- Check logs for specific errors
- Backup data before retrying

---

## Next Steps

After successful migration:

1. **Change default admin password**
   ```bash
   # Login to MySQL
   mysql -u recipe_user -p recipe_editor
   
   # Update password (using bcrypt hash from Python)
   ```

2. **Test the application** (next phase of implementation)
   - User authentication will be added
   - Recipe CRUD with normalized ingredients
   - Multi-user features

3. **Configure for production**
   - Use strong MySQL passwords
   - Enable MySQL SSL if remote
   - Set up regular backups
   - Configure firewall rules

---

## Advanced Configuration

### Performance Tuning

For large datasets, optimize MySQL:

```sql
-- Add more indexes if needed
CREATE INDEX idx_recipe_updated ON recipes(updated_at DESC);
CREATE INDEX idx_ingredient_category ON ingredients(category, is_common);

-- Analyze tables for query optimization
ANALYZE TABLE recipes, recipe_ingredients, ingredients;

-- Monitor slow queries
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;
```

### Monitoring

```sql
-- Check database size
SELECT 
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size (MB)'
FROM information_schema.TABLES
WHERE table_schema = 'recipe_editor'
ORDER BY (data_length + index_length) DESC;

-- Check row counts
SELECT 
    table_name,
    table_rows
FROM information_schema.TABLES
WHERE table_schema = 'recipe_editor'
ORDER BY table_rows DESC;
```

---

## Migration Rollback

If you need to rollback to JSON:

1. Your JSON files are still in `data/` directory (untouched by migration)
2. Simply don't configure MySQL in the app
3. Or restore from `data_backup_YYYYMMDD/`

**The migration is non-destructive** - your JSON files remain intact!

---

## Database Maintenance

### Regular Tasks

**Weekly:**
- Backup database
- Check disk space
- Review slow query log

**Monthly:**
- Optimize tables: `OPTIMIZE TABLE recipes, ingredients;`
- Update statistics: `ANALYZE TABLE recipes;`
- Clean up old password reset tokens

**As Needed:**
- Merge duplicate ingredients
- Curate ingredient categories
- Clean up unused tags

---

## Support

For issues:
1. Check this guide
2. Check MySQL error logs: `/usr/local/var/mysql/*.err` (macOS)
3. Test connection: `python -c "import db_config; print(db_config.test_connection())"`
4. Check application logs: `logs/app.log`

---

## Summary

You've successfully:
✅ Installed MySQL
✅ Created database and user
✅ Initialized schema (14 tables)
✅ Migrated JSON recipes to MySQL
✅ Set up normalized ingredients
✅ Created admin user account

**Next:** Implement the application layer to use MySQL! 🚀

