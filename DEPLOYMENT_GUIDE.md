# Recipe Editor - Production Deployment Guide

This guide walks you through deploying the Recipe Editor application on a DreamHost VPS using Gunicorn + Nginx.

## Prerequisites

### 1. DreamHost VPS Setup
- **Minimum**: DreamHost VPS Basic ($10/month) - 1GB RAM, 30GB SSD
- **Recommended**: DreamHost VPS Standard ($20/month) - 2GB RAM, 60GB SSD
- **Domain**: Point your domain's A record to your VPS IP address

### 2. Server Access
- SSH access to your DreamHost VPS
- Sudo privileges
- Basic command line knowledge

## Quick Deployment (Automated)

### Step 1: Configure Deployment Script
Edit the deployment script with your details:

```bash
# Update these variables in deploy.sh
DOMAIN="yourdomain.com"
USERNAME="yourusername"
```

### Step 2: Run Deployment
```bash
# Upload the deployment script to your server
scp deploy.sh yourusername@your-server-ip:/home/yourusername/

# SSH into your server
ssh yourusername@your-server-ip

# Make script executable and run
chmod +x deploy.sh
./deploy.sh deploy
```

### Step 3: Configure Environment
After deployment, update your configuration:

```bash
# Edit the environment file
nano /home/yourusername/recipe_editor/.env

# Update these critical values:
MYSQL_PASSWORD=your_secure_password_here
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
GOOGLE_GEMINI_API_KEY=your-gemini-api-key-here
```

### Step 4: Create Admin User
```bash
cd /home/yourusername/recipe_editor
source venv/bin/activate
python scripts/create_user.py
```

## Manual Deployment (Step-by-Step)

If you prefer manual setup or need to troubleshoot:

### Step 1: System Update
```bash
sudo apt update && sudo apt upgrade -y
```

### Step 2: Install Required Packages
```bash
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
```

### Step 3: Setup MySQL Database
```bash
# Start MySQL
sudo systemctl start mysql
sudo systemctl enable mysql

# Secure MySQL installation
sudo mysql_secure_installation

# Create database and user
sudo mysql -e "
    CREATE DATABASE IF NOT EXISTS recipe_editor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    CREATE USER IF NOT EXISTS 'recipe_user'@'localhost' IDENTIFIED BY 'your_secure_password';
    GRANT ALL PRIVILEGES ON recipe_editor.* TO 'recipe_user'@'localhost';
    FLUSH PRIVILEGES;
"
```

### Step 4: Deploy Application
```bash
# Create application directory
mkdir -p /home/yourusername/recipe_editor
cd /home/yourusername/recipe_editor

# Clone repository
git clone https://github.com/rlgafter/recipe_editor.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

### Step 5: Configure Environment
```bash
# Create .env file
cat > .env << EOF
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
DEBUG=False
FLASK_ENV=production
STORAGE_BACKEND=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=recipe_user
MYSQL_PASSWORD=your_secure_password
MYSQL_DATABASE=recipe_editor
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=True
SENDER_EMAIL=your-email@gmail.com
SENDER_NAME=Recipe Editor
GOOGLE_GEMINI_API_KEY=your-gemini-api-key
HOST=127.0.0.1
PORT=8000
EOF
```

### Step 6: Setup Gunicorn
```bash
# Copy Gunicorn configuration
cp gunicorn.conf.py /home/yourusername/recipe_editor/

# Test Gunicorn
cd /home/yourusername/recipe_editor
source venv/bin/activate
gunicorn --config gunicorn.conf.py app_mysql:app
```

### Step 7: Setup Systemd Service
```bash
# Copy service file
sudo cp recipe-editor.service /etc/systemd/system/

# Update paths in service file
sudo sed -i "s|yourusername|$(whoami)|g" /etc/systemd/system/recipe-editor.service

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable recipe-editor
sudo systemctl start recipe-editor
```

### Step 8: Setup Nginx
```bash
# Copy Nginx configuration
sudo cp nginx.conf /etc/nginx/sites-available/recipe-editor

# Update domain and paths
sudo sed -i "s|yourdomain.com|yourdomain.com|g" /etc/nginx/sites-available/recipe-editor
sudo sed -i "s|yourusername|$(whoami)|g" /etc/nginx/sites-available/recipe-editor

# Enable site
sudo ln -s /etc/nginx/sites-available/recipe-editor /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Start Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Step 9: Setup SSL Certificate
```bash
# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Setup auto-renewal
sudo systemctl enable certbot.timer
```

### Step 10: Configure Firewall
```bash
# Configure UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Step 11: Initialize Database
```bash
cd /home/yourusername/recipe_editor
source venv/bin/activate

# Run database migrations
python scripts/init_database.py
python migrate_add_recipe_visibility.py
python migrate_add_ingredients_json.py
python migrate_add_source.py
```

### Step 12: Create Admin User
```bash
python scripts/create_user.py
```

## Configuration Details

### Environment Variables (.env file)

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | Auto-generated |
| `DEBUG` | Debug mode | `False` |
| `STORAGE_BACKEND` | Database backend | `mysql` |
| `MYSQL_HOST` | MySQL host | `localhost` |
| `MYSQL_USER` | MySQL username | `recipe_user` |
| `MYSQL_PASSWORD` | MySQL password | `your_secure_password` |
| `MYSQL_DATABASE` | Database name | `recipe_editor` |
| `SMTP_SERVER` | SMTP server | `smtp.gmail.com` |
| `SMTP_USERNAME` | Email username | `your-email@gmail.com` |
| `SMTP_PASSWORD` | Email password | `your-app-password` |
| `GOOGLE_GEMINI_API_KEY` | Gemini API key | `your-api-key` |

### Gunicorn Configuration

The `gunicorn.conf.py` file configures:
- **Workers**: CPU cores × 2 + 1
- **Bind**: 127.0.0.1:8000
- **Timeout**: 120 seconds
- **Logging**: Access and error logs
- **Process management**: Auto-restart workers

### Nginx Configuration

The `nginx.conf` file provides:
- **SSL termination**: HTTPS with Let's Encrypt
- **Static file serving**: CSS, JS, images
- **Proxy pass**: Forward requests to Gunicorn
- **Security headers**: HSTS, XSS protection
- **Gzip compression**: Reduce bandwidth usage

### Systemd Service

The `recipe-editor.service` file:
- **Auto-start**: Starts on boot
- **Restart policy**: Always restart on failure
- **User/Group**: Runs as www-data
- **Security**: Limited privileges
- **Dependencies**: Waits for MySQL

## Management Commands

### Service Management
```bash
# Check service status
sudo systemctl status recipe-editor

# Start/stop/restart service
sudo systemctl start recipe-editor
sudo systemctl stop recipe-editor
sudo systemctl restart recipe-editor

# View logs
sudo journalctl -u recipe-editor -f
```

### Application Updates
```bash
# Update application code
cd /home/yourusername/recipe_editor
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart recipe-editor
```

### Database Management
```bash
# Access MySQL
mysql -u recipe_user -p recipe_editor

# Backup database
mysqldump -u recipe_user -p recipe_editor > backup.sql

# Restore database
mysql -u recipe_user -p recipe_editor < backup.sql
```

### SSL Certificate Management
```bash
# Renew certificate
sudo certbot renew

# Check certificate status
sudo certbot certificates
```

## Troubleshooting

### Common Issues

**1. Service won't start**
```bash
# Check service status
sudo systemctl status recipe-editor

# Check logs
sudo journalctl -u recipe-editor -n 50

# Test configuration
cd /home/yourusername/recipe_editor
source venv/bin/activate
python app_mysql.py
```

**2. Database connection errors**
```bash
# Test MySQL connection
mysql -u recipe_user -p recipe_editor

# Check MySQL status
sudo systemctl status mysql

# Check MySQL logs
sudo journalctl -u mysql -n 50
```

**3. Nginx errors**
```bash
# Test Nginx configuration
sudo nginx -t

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log

# Check Nginx status
sudo systemctl status nginx
```

**4. SSL certificate issues**
```bash
# Check certificate status
sudo certbot certificates

# Renew certificate manually
sudo certbot renew --dry-run
```

### Performance Optimization

**1. Increase Gunicorn workers**
```bash
# Edit gunicorn.conf.py
workers = 4  # Adjust based on CPU cores
```

**2. Enable Nginx caching**
```bash
# Add to nginx.conf
location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

**3. Database optimization**
```bash
# Add to MySQL configuration
[mysqld]
innodb_buffer_pool_size = 256M
query_cache_size = 32M
```

## Security Considerations

### 1. Firewall Configuration
- Only allow necessary ports (22, 80, 443)
- Consider changing SSH port
- Use fail2ban for additional protection

### 2. SSL/TLS Security
- Use strong cipher suites
- Enable HSTS headers
- Regular certificate renewal

### 3. Application Security
- Strong secret keys
- Secure database passwords
- Regular security updates

### 4. File Permissions
```bash
# Set proper permissions
chmod 755 /home/yourusername/recipe_editor
chmod 644 /home/yourusername/recipe_editor/.env
chmod 755 /home/yourusername/recipe_editor/venv
```

## Monitoring and Maintenance

### 1. Log Monitoring
```bash
# Application logs
sudo journalctl -u recipe-editor -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# MySQL logs
sudo tail -f /var/log/mysql/error.log
```

### 2. Performance Monitoring
```bash
# System resources
htop
df -h
free -h

# Application metrics
curl https://yourdomain.com/health
```

### 3. Regular Maintenance
- Update system packages monthly
- Renew SSL certificates automatically
- Backup database weekly
- Monitor disk space
- Review logs for errors

## Support and Resources

### DreamHost Support
- **Knowledge Base**: https://help.dreamhost.com/
- **Community Forum**: https://discussion.dreamhost.com/
- **Support Tickets**: Via DreamHost panel

### Application Resources
- **GitHub Repository**: https://github.com/rlgafter/recipe_editor
- **Documentation**: README.md and DESIGN.md
- **Issues**: GitHub Issues page

### External Resources
- **Gunicorn Documentation**: https://docs.gunicorn.org/
- **Nginx Documentation**: https://nginx.org/en/docs/
- **Let's Encrypt**: https://letsencrypt.org/docs/
- **MySQL Documentation**: https://dev.mysql.com/doc/

---

**Deployment Complete!** 🎉

Your Recipe Editor should now be accessible at `https://yourdomain.com`

For any issues, check the logs and refer to the troubleshooting section above.
