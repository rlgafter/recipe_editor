#!/bin/bash
# MySQL Database Activation Script
# This script helps you activate MySQL for the Recipe Editor

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Recipe Editor - MySQL Activation${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check if MySQL is installed
echo -e "${YELLOW}[1/10] Checking MySQL installation...${NC}"
if command -v mysql &> /dev/null; then
    echo -e "${GREEN}✓ MySQL is installed${NC}"
    mysql --version
else
    echo -e "${RED}✗ MySQL is not installed${NC}"
    echo -e "\n${YELLOW}Please install MySQL first:${NC}"
    echo -e "  brew install mysql"
    echo -e "  brew services start mysql"
    echo -e "\nOr download from: https://dev.mysql.com/downloads/mysql/"
    exit 1
fi

# Check if MySQL is running
echo -e "\n${YELLOW}[2/10] Checking if MySQL is running...${NC}"
if pgrep -x mysqld > /dev/null; then
    echo -e "${GREEN}✓ MySQL is running${NC}"
else
    echo -e "${YELLOW}⚠ MySQL is not running. Attempting to start...${NC}"
    if command -v brew &> /dev/null; then
        brew services start mysql
        sleep 3
        if pgrep -x mysqld > /dev/null; then
            echo -e "${GREEN}✓ MySQL started successfully${NC}"
        else
            echo -e "${RED}✗ Failed to start MySQL${NC}"
            exit 1
        fi
    else
        echo -e "${RED}✗ Please start MySQL manually${NC}"
        exit 1
    fi
fi

# Prompt for MySQL root password
echo -e "\n${YELLOW}[3/10] MySQL root credentials${NC}"
echo -e "Enter MySQL root password (press Enter if no password):"
read -s MYSQL_ROOT_PASSWORD

# Test root connection
if [ -z "$MYSQL_ROOT_PASSWORD" ]; then
    MYSQL_CMD="mysql -u root"
else
    MYSQL_CMD="mysql -u root -p${MYSQL_ROOT_PASSWORD}"
fi

if $MYSQL_CMD -e "SELECT 1;" &> /dev/null; then
    echo -e "${GREEN}✓ MySQL root connection successful${NC}"
else
    echo -e "${RED}✗ Failed to connect to MySQL with root credentials${NC}"
    exit 1
fi

# Prompt for recipe_user password
echo -e "\n${YELLOW}[4/10] Recipe database user setup${NC}"
echo -e "Enter password for 'recipe_user' (will be created):"
read -s RECIPE_PASSWORD
echo ""

if [ -z "$RECIPE_PASSWORD" ]; then
    echo -e "${RED}✗ Password cannot be empty${NC}"
    exit 1
fi

# Create database and user
echo -e "\n${YELLOW}[5/10] Creating database and user...${NC}"
$MYSQL_CMD <<EOF
-- Create database
CREATE DATABASE IF NOT EXISTS recipe_editor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create or update user
DROP USER IF EXISTS 'recipe_user'@'localhost';
CREATE USER 'recipe_user'@'localhost' IDENTIFIED BY '${RECIPE_PASSWORD}';

-- Grant privileges
GRANT ALL PRIVILEGES ON recipe_editor.* TO 'recipe_user'@'localhost';
FLUSH PRIVILEGES;
EOF

echo -e "${GREEN}✓ Database 'recipe_editor' created${NC}"
echo -e "${GREEN}✓ User 'recipe_user' created with privileges${NC}"

# Create .env file
echo -e "\n${YELLOW}[6/10] Creating .env file...${NC}"
cat > .env << EOF
# MySQL Configuration
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=recipe_user
export MYSQL_PASSWORD=${RECIPE_PASSWORD}
export MYSQL_DATABASE=recipe_editor

# Optional: Enable SQL query logging
export SQL_ECHO=False
EOF

chmod 600 .env  # Secure the file
echo -e "${GREEN}✓ Environment configuration created${NC}"

# Source environment
source .env

# Install Python dependencies
echo -e "\n${YELLOW}[7/10] Installing Python MySQL dependencies...${NC}"
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install -q mysql-connector-python SQLAlchemy Flask-SQLAlchemy Flask-Login bcrypt
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${RED}✗ Virtual environment not found${NC}"
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -q -r requirements.txt
    echo -e "${GREEN}✓ Virtual environment created and dependencies installed${NC}"
fi

# Initialize database
echo -e "\n${YELLOW}[8/10] Initializing database schema...${NC}"
python scripts/init_database.py

# Migrate JSON data
echo -e "\n${YELLOW}[9/10] Migrating JSON data to MySQL...${NC}"
echo -e "This will migrate your recipes from JSON files to MySQL."
echo -e "Continue? (y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    python scripts/migrate_json_to_mysql.py
    echo -e "${GREEN}✓ Data migration complete${NC}"
else
    echo -e "${YELLOW}⚠ Skipped data migration${NC}"
fi

# Create user account
echo -e "\n${YELLOW}[10/10] Creating your user account...${NC}"
echo -e "Would you like to create a user account now? (y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    python scripts/create_user.py
else
    echo -e "${YELLOW}⚠ Skipped user creation (you can run 'python scripts/create_user.py' later)${NC}"
fi

# Success message
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  ✓ MySQL Activation Complete!${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${BLUE}Next steps:${NC}"
echo -e "1. Start the MySQL-enabled app:"
echo -e "   ${YELLOW}source .env${NC}"
echo -e "   ${YELLOW}python app_mysql.py${NC}"
echo -e ""
echo -e "2. Or use the server script:"
echo -e "   ${YELLOW}./server start${NC}"
echo -e ""
echo -e "3. Access your app at:"
echo -e "   ${GREEN}http://localhost:5001${NC}"
echo -e ""
echo -e "${BLUE}Your environment is configured in:${NC} .env"
echo -e "${BLUE}Remember to source it before running the app:${NC}"
echo -e "   ${YELLOW}source .env${NC}"
echo -e ""


