#!/bin/bash
# Recipe Editor - Production Deployment Script
# This script automates the deployment process for DreamHost VPS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - UPDATE THESE VALUES
DOMAIN="yourdomain.com"
USERNAME="yourusername"
APP_DIR="/home/$USERNAME/recipe_editor"
SERVICE_NAME="recipe-editor"
NGINX_SITE="recipe-editor"

# Print colored message
print_msg() {
    echo -e "${2}${1}${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_msg "This script should not be run as root. Please run as a regular user with sudo privileges." "$RED"
        exit 1
    fi
}

# Update system packages
update_system() {
    print_msg "Updating system packages..." "$BLUE"
    sudo apt update && sudo apt upgrade -y
    print_msg "System updated successfully" "$GREEN"
}

# Install required packages
install_packages() {
    print_msg "Installing required packages..." "$BLUE"
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        nginx \
        mysql-server \
        mysql-client \
        certbot \
        python3-certbot-nginx \
        ufw \
        git \
        curl \
        wget \
        unzip \
        build-essential \
        libssl-dev \
        libffi-dev \
        libmysqlclient-dev \
        pkg-config
    print_msg "Packages installed successfully" "$GREEN"
}

# Configure MySQL
setup_mysql() {
    print_msg "Configuring MySQL..." "$BLUE"
    
    # Start and enable MySQL
    sudo systemctl start mysql
    sudo systemctl enable mysql
    
    # Create database and user
    print_msg "Creating MySQL database and user..." "$YELLOW"
    sudo mysql -e "
        CREATE DATABASE IF NOT EXISTS recipe_editor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        CREATE USER IF NOT EXISTS 'recipe_user'@'localhost' IDENTIFIED BY 'your_secure_password_here';
        GRANT ALL PRIVILEGES ON recipe_editor.* TO 'recipe_user'@'localhost';
        FLUSH PRIVILEGES;
    "
    
    print_msg "MySQL configured successfully" "$GREEN"
    print_msg "IMPORTANT: Update the MySQL password in your .env file!" "$YELLOW"
}

# Setup application directory
setup_app_directory() {
    print_msg "Setting up application directory..." "$BLUE"
    
    # Create app directory if it doesn't exist
    if [ ! -d "$APP_DIR" ]; then
        mkdir -p "$APP_DIR"
    fi
    
    # Clone repository if not already present
    if [ ! -f "$APP_DIR/app.py" ]; then
        print_msg "Cloning repository..." "$YELLOW"
        git clone https://github.com/rlgafter/recipe_editor.git "$APP_DIR"
    fi
    
    cd "$APP_DIR"
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        print_msg "Creating virtual environment..." "$YELLOW"
        python3 -m venv venv
    fi
    
    # Activate virtual environment and install dependencies
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install gunicorn
    
    print_msg "Application directory setup complete" "$GREEN"
}

# Create environment file
create_env_file() {
    print_msg "Creating environment configuration..." "$BLUE"
    
    cd "$APP_DIR"
    
    cat > .env << EOF
# Flask Configuration
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
DEBUG=False
FLASK_ENV=production

# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=recipe_user
MYSQL_PASSWORD=your_secure_password_here
MYSQL_DATABASE=recipe_editor

# Email Configuration (Update with your SMTP settings)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=True
SENDER_EMAIL=your-email@gmail.com
SENDER_NAME=Recipe Editor

# Google Gemini API (Optional - for AI recipe import)
GOOGLE_GEMINI_API_KEY=your-gemini-api-key-here

# Server Configuration
HOST=127.0.0.1
PORT=8000
EOF
    
    print_msg "Environment file created at $APP_DIR/.env" "$GREEN"
    print_msg "IMPORTANT: Update the configuration values in .env file!" "$YELLOW"
}

# Setup systemd service
setup_systemd_service() {
    print_msg "Setting up systemd service..." "$BLUE"
    
    # Copy service file
    sudo cp "$APP_DIR/recipe-editor.service" "/etc/systemd/system/"
    
    # Update service file with correct paths
    sudo sed -i "s|yourusername|$USERNAME|g" "/etc/systemd/system/recipe-editor.service"
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable recipe-editor
    
    print_msg "Systemd service configured" "$GREEN"
}

# Setup Nginx
setup_nginx() {
    print_msg "Setting up Nginx..." "$BLUE"
    
    # Copy nginx configuration
    sudo cp "$APP_DIR/nginx.conf" "/etc/nginx/sites-available/$NGINX_SITE"
    
    # Update configuration with correct domain and paths
    sudo sed -i "s|yourdomain.com|$DOMAIN|g" "/etc/nginx/sites-available/$NGINX_SITE"
    sudo sed -i "s|yourusername|$USERNAME|g" "/etc/nginx/sites-available/$NGINX_SITE"
    
    # Enable site
    sudo ln -sf "/etc/nginx/sites-available/$NGINX_SITE" "/etc/nginx/sites-enabled/"
    
    # Remove default site
    sudo rm -f "/etc/nginx/sites-enabled/default"
    
    # Test nginx configuration
    sudo nginx -t
    
    # Start and enable nginx
    sudo systemctl start nginx
    sudo systemctl enable nginx
    
    print_msg "Nginx configured successfully" "$GREEN"
}

# Setup SSL certificate
setup_ssl() {
    print_msg "Setting up SSL certificate..." "$BLUE"
    
    # Get SSL certificate
    sudo certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" --non-interactive --agree-tos --email "admin@$DOMAIN"
    
    # Setup auto-renewal
    sudo systemctl enable certbot.timer
    
    print_msg "SSL certificate configured" "$GREEN"
}

# Configure firewall
setup_firewall() {
    print_msg "Configuring firewall..." "$BLUE"
    
    # Reset UFW to defaults
    sudo ufw --force reset
    
    # Set default policies
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    # Allow SSH, HTTP, and HTTPS
    sudo ufw allow 22/tcp
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    
    # Enable firewall
    sudo ufw --force enable
    
    print_msg "Firewall configured" "$GREEN"
}

# Initialize database
init_database() {
    print_msg "Initializing database..." "$BLUE"
    
    cd "$APP_DIR"
    source venv/bin/activate
    
    # Run database initialization scripts
    python scripts/init_database.py
    python migrate_add_recipe_visibility.py
    python migrate_add_ingredients_json.py
    python migrate_add_source.py
    
    print_msg "Database initialized" "$GREEN"
}

# Start services
start_services() {
    print_msg "Starting services..." "$BLUE"
    
    # Start MySQL
    sudo systemctl start mysql
    
    # Start application
    sudo systemctl start recipe-editor
    
    # Restart Nginx
    sudo systemctl restart nginx
    
    print_msg "Services started successfully" "$GREEN"
}

# Show status
show_status() {
    print_msg "Checking service status..." "$BLUE"
    
    echo
    print_msg "=== Service Status ===" "$YELLOW"
    sudo systemctl status mysql --no-pager -l
    echo
    sudo systemctl status recipe-editor --no-pager -l
    echo
    sudo systemctl status nginx --no-pager -l
    
    echo
    print_msg "=== Application URLs ===" "$YELLOW"
    print_msg "Application: https://$DOMAIN" "$GREEN"
    print_msg "Admin Panel: https://$DOMAIN/admin" "$GREEN"
    
    echo
    print_msg "=== Next Steps ===" "$YELLOW"
    print_msg "1. Update configuration in $APP_DIR/.env" "$BLUE"
    print_msg "2. Create an admin user: python scripts/create_user.py" "$BLUE"
    print_msg "3. Test the application at https://$DOMAIN" "$BLUE"
    print_msg "4. Check logs: sudo journalctl -u recipe-editor -f" "$BLUE"
}

# Main deployment function
deploy() {
    print_msg "Starting Recipe Editor deployment..." "$GREEN"
    print_msg "Domain: $DOMAIN" "$BLUE"
    print_msg "User: $USERNAME" "$BLUE"
    print_msg "App Directory: $APP_DIR" "$BLUE"
    echo
    
    check_root
    update_system
    install_packages
    setup_mysql
    setup_app_directory
    create_env_file
    setup_systemd_service
    setup_nginx
    setup_firewall
    init_database
    start_services
    show_status
    
    print_msg "Deployment completed successfully!" "$GREEN"
}

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  deploy     - Run full deployment"
    echo "  update     - Update application code"
    echo "  restart    - Restart services"
    echo "  status     - Show service status"
    echo "  logs       - Show application logs"
    echo "  ssl        - Setup SSL certificate only"
    echo "  help       - Show this help"
    echo
    echo "Configuration:"
    echo "  Update DOMAIN, USERNAME, and other variables at the top of this script"
}

# Update application
update_app() {
    print_msg "Updating application..." "$BLUE"
    
    cd "$APP_DIR"
    
    # Pull latest changes
    git pull origin main
    
    # Update dependencies
    source venv/bin/activate
    pip install -r requirements.txt
    
    # Restart service
    sudo systemctl restart recipe-editor
    
    print_msg "Application updated successfully" "$GREEN"
}

# Restart services
restart_services() {
    print_msg "Restarting services..." "$BLUE"
    
    sudo systemctl restart recipe-editor
    sudo systemctl restart nginx
    
    print_msg "Services restarted" "$GREEN"
}

# Show logs
show_logs() {
    print_msg "Showing application logs (Ctrl+C to exit)..." "$BLUE"
    sudo journalctl -u recipe-editor -f
}

# Main script
case "${1:-deploy}" in
    deploy)
        deploy
        ;;
    update)
        update_app
        ;;
    restart)
        restart_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    ssl)
        setup_ssl
        ;;
    help)
        usage
        ;;
    *)
        print_msg "Unknown option: $1" "$RED"
        usage
        exit 1
        ;;
esac
