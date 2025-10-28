#!/bin/bash
# Recipe Editor - SSL and Security Configuration Script
# This script sets up SSL certificates and security hardening

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="yourdomain.com"
EMAIL="admin@yourdomain.com"

# Print colored message
print_msg() {
    echo -e "${2}${1}${NC}"
}

# Install Certbot
install_certbot() {
    print_msg "Installing Certbot..." "$BLUE"
    
    sudo apt update
    sudo apt install -y certbot python3-certbot-nginx
    
    print_msg "Certbot installed successfully" "$GREEN"
}

# Setup SSL Certificate
setup_ssl_certificate() {
    print_msg "Setting up SSL certificate for $DOMAIN..." "$BLUE"
    
    # Stop nginx temporarily for certificate generation
    sudo systemctl stop nginx
    
    # Generate certificate
    sudo certbot certonly --standalone \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        -d "$DOMAIN" \
        -d "www.$DOMAIN"
    
    # Start nginx
    sudo systemctl start nginx
    
    print_msg "SSL certificate generated successfully" "$GREEN"
}

# Configure SSL with Nginx
configure_ssl_nginx() {
    print_msg "Configuring SSL with Nginx..." "$BLUE"
    
    # Backup original nginx config
    sudo cp /etc/nginx/sites-available/recipe-editor /etc/nginx/sites-available/recipe-editor.backup
    
    # Update nginx configuration with SSL
    sudo tee /etc/nginx/sites-available/recipe-editor > /dev/null << EOF
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    
    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/$DOMAIN/chain.pem;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self';" always;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;
    
    # Client settings
    client_max_body_size 10M;
    
    # Static files
    location /static {
        alias /home/$(whoami)/recipe_editor/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options nosniff always;
        add_header X-Frame-Options DENY always;
    }
    
    # Favicon
    location /favicon.ico {
        alias /home/$(whoami)/recipe_editor/static/favicon.ico;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Robots.txt
    location /robots.txt {
        alias /home/$(whoami)/recipe_editor/static/robots.txt;
        expires 1d;
    }
    
    # Main application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
        proxy_max_temp_file_size 0;
    }
    
    # Health check
    location /health {
        access_log off;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Deny access to sensitive files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
    
    location ~ \.(env|log|pid|conf)$ {
        deny all;
        access_log off;
        log_not_found off;
    }
    
    # Error pages
    error_page 404 /404.html;
    error_page 500 502 503 504 /500.html;
    
    # Logging
    access_log /var/log/nginx/recipe_editor_access.log;
    error_log /var/log/nginx/recipe_editor_error.log;
}
EOF
    
    # Test nginx configuration
    sudo nginx -t
    
    # Reload nginx
    sudo systemctl reload nginx
    
    print_msg "SSL configuration updated successfully" "$GREEN"
}

# Setup SSL auto-renewal
setup_ssl_renewal() {
    print_msg "Setting up SSL auto-renewal..." "$BLUE"
    
    # Enable certbot timer
    sudo systemctl enable certbot.timer
    sudo systemctl start certbot.timer
    
    # Create renewal script
    sudo tee /etc/cron.d/certbot-renewal > /dev/null << EOF
# Renew SSL certificates twice daily
0 12 * * * root certbot renew --quiet --post-hook "systemctl reload nginx"
0 0 * * * root certbot renew --quiet --post-hook "systemctl reload nginx"
EOF
    
    print_msg "SSL auto-renewal configured" "$GREEN"
}

# Configure Firewall
configure_firewall() {
    print_msg "Configuring firewall..." "$BLUE"
    
    # Reset UFW
    sudo ufw --force reset
    
    # Set default policies
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    # Allow essential services
    sudo ufw allow 22/tcp comment 'SSH'
    sudo ufw allow 80/tcp comment 'HTTP'
    sudo ufw allow 443/tcp comment 'HTTPS'
    
    # Enable firewall
    sudo ufw --force enable
    
    print_msg "Firewall configured successfully" "$GREEN"
}

# Install Fail2Ban
install_fail2ban() {
    print_msg "Installing Fail2Ban..." "$BLUE"
    
    sudo apt install -y fail2ban
    
    # Create fail2ban configuration
    sudo tee /etc/fail2ban/jail.local > /dev/null << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3
backend = systemd

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
maxretry = 3

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 10
EOF
    
    # Start and enable fail2ban
    sudo systemctl start fail2ban
    sudo systemctl enable fail2ban
    
    print_msg "Fail2Ban installed and configured" "$GREEN"
}

# Configure SSH Security
configure_ssh_security() {
    print_msg "Configuring SSH security..." "$BLUE"
    
    # Backup SSH config
    sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup
    
    # Update SSH configuration
    sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
    sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
    sudo sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
    
    # Add security settings
    sudo tee -a /etc/ssh/sshd_config > /dev/null << EOF

# Security settings
Protocol 2
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
UseDNS no
EOF
    
    # Test SSH configuration
    sudo sshd -t
    
    print_msg "SSH security configured" "$GREEN"
    print_msg "IMPORTANT: Ensure you have SSH key authentication set up before restarting SSH!" "$YELLOW"
}

# Setup Log Rotation
setup_log_rotation() {
    print_msg "Setting up log rotation..." "$BLUE"
    
    # Create logrotate configuration
    sudo tee /etc/logrotate.d/recipe-editor > /dev/null << EOF
/var/log/nginx/recipe_editor_*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        systemctl reload nginx
    endscript
}

/home/$(whoami)/recipe_editor/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $(whoami) $(whoami)
    postrotate
        systemctl reload recipe-editor
    endscript
}
EOF
    
    print_msg "Log rotation configured" "$GREEN"
}

# Create Security Monitoring Script
create_security_monitor() {
    print_msg "Creating security monitoring script..." "$BLUE"
    
    sudo tee /usr/local/bin/security-monitor.sh > /dev/null << 'EOF'
#!/bin/bash
# Security monitoring script

LOG_FILE="/var/log/security-monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Check for failed login attempts
FAILED_LOGINS=$(grep "Failed password" /var/log/auth.log | wc -l)
if [ $FAILED_LOGINS -gt 10 ]; then
    echo "$DATE: WARNING - High number of failed login attempts: $FAILED_LOGINS" >> $LOG_FILE
fi

# Check SSL certificate expiration
CERT_EXPIRY=$(openssl x509 -enddate -noout -in /etc/letsencrypt/live/yourdomain.com/cert.pem | cut -d= -f2)
CERT_EXPIRY_EPOCH=$(date -d "$CERT_EXPIRY" +%s)
CURRENT_EPOCH=$(date +%s)
DAYS_UNTIL_EXPIRY=$(( (CERT_EXPIRY_EPOCH - CURRENT_EPOCH) / 86400 ))

if [ $DAYS_UNTIL_EXPIRY -lt 30 ]; then
    echo "$DATE: WARNING - SSL certificate expires in $DAYS_UNTIL_EXPIRY days" >> $LOG_FILE
fi

# Check disk space
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "$DATE: WARNING - Disk usage is ${DISK_USAGE}%" >> $LOG_FILE
fi

# Check service status
if ! systemctl is-active --quiet recipe-editor; then
    echo "$DATE: ERROR - Recipe Editor service is not running" >> $LOG_FILE
fi

if ! systemctl is-active --quiet nginx; then
    echo "$DATE: ERROR - Nginx service is not running" >> $LOG_FILE
fi

if ! systemctl is-active --quiet mysql; then
    echo "$DATE: ERROR - MySQL service is not running" >> $LOG_FILE
fi
EOF
    
    sudo chmod +x /usr/local/bin/security-monitor.sh
    
    # Add to crontab
    (crontab -l 2>/dev/null; echo "0 */6 * * * /usr/local/bin/security-monitor.sh") | crontab -
    
    print_msg "Security monitoring script created" "$GREEN"
}

# Test SSL Configuration
test_ssl_configuration() {
    print_msg "Testing SSL configuration..." "$BLUE"
    
    # Test SSL certificate
    echo "Testing SSL certificate..."
    openssl s_client -connect $DOMAIN:443 -servername $DOMAIN < /dev/null 2>/dev/null | openssl x509 -noout -dates
    
    # Test SSL Labs (if curl is available)
    if command -v curl &> /dev/null; then
        echo "Testing SSL configuration with SSL Labs..."
        curl -s "https://api.ssllabs.com/api/v3/analyze?host=$DOMAIN" | grep -o '"status":"[^"]*"' || echo "SSL Labs test initiated (may take a few minutes)"
    fi
    
    print_msg "SSL configuration test completed" "$GREEN"
}

# Main security setup function
setup_security() {
    print_msg "Starting security configuration..." "$GREEN"
    print_msg "Domain: $DOMAIN" "$BLUE"
    print_msg "Email: $EMAIL" "$BLUE"
    echo
    
    install_certbot
    setup_ssl_certificate
    configure_ssl_nginx
    setup_ssl_renewal
    configure_firewall
    install_fail2ban
    configure_ssh_security
    setup_log_rotation
    create_security_monitor
    test_ssl_configuration
    
    print_msg "Security configuration completed successfully!" "$GREEN"
    echo
    print_msg "=== Security Summary ===" "$YELLOW"
    print_msg "✓ SSL certificate installed and configured" "$GREEN"
    print_msg "✓ Firewall configured (UFW)" "$GREEN"
    print_msg "✓ Fail2Ban installed for intrusion prevention" "$GREEN"
    print_msg "✓ SSH security hardened" "$GREEN"
    print_msg "✓ Log rotation configured" "$GREEN"
    print_msg "✓ Security monitoring script created" "$GREEN"
    echo
    print_msg "IMPORTANT: Review SSH configuration before restarting SSH service!" "$YELLOW"
    print_msg "Run: sudo systemctl restart ssh" "$BLUE"
}

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  setup      - Run full security setup"
    echo "  ssl        - Setup SSL certificate only"
    echo "  firewall   - Configure firewall only"
    echo "  fail2ban   - Install Fail2Ban only"
    echo "  test       - Test SSL configuration"
    echo "  help       - Show this help"
    echo
    echo "Configuration:"
    echo "  Update DOMAIN and EMAIL variables at the top of this script"
}

# Main script
case "${1:-setup}" in
    setup)
        setup_security
        ;;
    ssl)
        install_certbot
        setup_ssl_certificate
        configure_ssl_nginx
        setup_ssl_renewal
        ;;
    firewall)
        configure_firewall
        ;;
    fail2ban)
        install_fail2ban
        ;;
    test)
        test_ssl_configuration
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
