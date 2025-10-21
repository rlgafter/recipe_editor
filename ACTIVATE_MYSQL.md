# MySQL Database Activation Guide

## Current Status
✅ MySQL schema ready  
✅ Python models ready  
✅ Migration scripts ready  
❌ MySQL server NOT installed  
❌ Database NOT initialized  

## Step-by-Step Activation

### Step 1: Install MySQL

You have two options:

#### Option A: Using Homebrew (Recommended)
```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install MySQL
brew install mysql

# Start MySQL service
brew services start mysql
```

#### Option B: Download MySQL Manually
1. Visit: https://dev.mysql.com/downloads/mysql/
2. Download MySQL Community Server for macOS
3. Install the DMG package
4. Start MySQL from System Preferences

### Step 2: Secure MySQL Installation

```bash
# Run MySQL secure installation
mysql_secure_installation
```

Follow the prompts:
- Set root password: **YES** (choose a strong password)
- Remove anonymous users: **YES**
- Disallow root login remotely: **YES**
- Remove test database: **YES**
- Reload privilege tables: **YES**

### Step 3: Create Database and User

```bash
# Connect to MySQL as root
mysql -u root -p
```

Then run these SQL commands:

```sql
-- Create the database
CREATE DATABASE recipe_editor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create the user
CREATE USER 'recipe_user'@'localhost' IDENTIFIED BY 'your_secure_password_here';

-- Grant privileges
GRANT ALL PRIVILEGES ON recipe_editor.* TO 'recipe_user'@'localhost';

-- Apply changes
FLUSH PRIVILEGES;

-- Verify
SHOW DATABASES;

-- Exit
EXIT;
```

### Step 4: Configure Environment Variables

```bash
cd /Users/rickileegafter/recipe_editor

# Create .env file
cat > .env << 'EOF'
# MySQL Configuration
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=recipe_user
export MYSQL_PASSWORD=your_secure_password_here
export MYSQL_DATABASE=recipe_editor

# Storage Backend
export STORAGE_BACKEND=mysql

# Optional: Enable SQL query logging for debugging
export SQL_ECHO=False
EOF

# Make sure it's not tracked by git (should already be in .gitignore)
echo ".env" >> .gitignore 2>/dev/null || true
```

### Step 5: Install Python MySQL Dependencies

```bash
cd /Users/rickileegafter/recipe_editor

# Activate virtual environment
source venv/bin/activate

# Install MySQL dependencies
pip install mysql-connector-python SQLAlchemy Flask-SQLAlchemy Flask-Login bcrypt
```

### Step 6: Initialize Database

```bash
cd /Users/rickileegafter/recipe_editor

# Source environment variables
source .env

# Initialize database with schema
python scripts/init_database.py
```

You should see:
```
✓ Connected to MySQL server
✓ Database created/verified
✓ Schema executed successfully
✓ Common ingredients inserted
✓ Database initialization complete!
```

### Step 7: Migrate Your JSON Data to MySQL

```bash
cd /Users/rickileegafter/recipe_editor

# Run migration script
python scripts/migrate_json_to_mysql.py
```

This will:
- Migrate all your recipes from JSON to MySQL
- Create normalized ingredients
- Set up tags
- Create a default admin user

### Step 8: Create Your User Account

```bash
cd /Users/rickileegafter/recipe_editor

# Create your user account
python scripts/create_user.py
```

Follow prompts:
- Username: (your username)
- Email: (your email)
- Password: (your password)
- Make admin? **yes**

### Step 9: Start MySQL-Enabled App

```bash
cd /Users/rickileegafter/recipe_editor

# Source environment variables
source .env

# Run MySQL version of the app
python app_mysql.py
```

Or use the server script:
```bash
./server start
```

### Step 10: Verify Everything Works

1. Open browser: http://localhost:5001
2. Log in with your credentials
3. Check that recipes appear
4. Try creating a new recipe
5. Verify tags and search work

## Troubleshooting

### MySQL won't start
```bash
# Check MySQL status
brew services list | grep mysql

# Check MySQL logs
tail -f /usr/local/var/mysql/*.err

# Restart MySQL
brew services restart mysql
```

### Can't connect to database
```bash
# Verify MySQL is running
mysql -u root -p

# Check user exists
mysql -u root -p
SELECT User, Host FROM mysql.user WHERE User='recipe_user';
EXIT;

# Test Python connection
python -c "import mysql.connector; print('MySQL connector OK')"
```

### Migration fails
```bash
# Check database exists
mysql -u recipe_user -p recipe_editor
SHOW TABLES;
EXIT;

# Re-run initialization
python scripts/init_database.py

# Try migration again
python scripts/migrate_json_to_mysql.py
```

### Import errors
```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

## Quick Reference Commands

```bash
# Start MySQL
brew services start mysql

# Stop MySQL
brew services stop mysql

# Connect to database
mysql -u recipe_user -p recipe_editor

# View recipes in MySQL
mysql -u recipe_user -p recipe_editor -e "SELECT id, name FROM recipes;"

# Backup database
mysqldump -u recipe_user -p recipe_editor > backup.sql

# Restore database
mysql -u recipe_user -p recipe_editor < backup.sql
```

## What Changes After Activation

### Before (JSON Mode):
- ✓ Simple single-user system
- ✓ Recipes stored in `data/recipes/*.json`
- ✓ No authentication required
- ✓ Limited search capabilities

### After (MySQL Mode):
- ✓ Multi-user support with authentication
- ✓ Recipes stored in MySQL database
- ✓ User profiles and permissions
- ✓ Advanced search and filtering
- ✓ Favorites and ratings
- ✓ Collections and meal planning
- ✓ Normalized ingredients with autocomplete
- ✓ Better performance and scalability

## Need Help?

If you run into issues:
1. Check the logs: `tail -f logs/app.log`
2. Check MySQL logs: `/usr/local/var/mysql/*.err`
3. Review error messages carefully
4. Make sure all environment variables are set

---

**Ready to activate? Start with Step 1!** 🚀

