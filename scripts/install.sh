#!/bin/bash

###############################################################################
# SkyDock Panel Installation Script
# This script installs SkyDock Panel on a fresh Ubuntu server
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SKYDOCK_USER="skydock"
SKYDOCK_HOME="/opt/skydock-panel"
SKYDOCK_PORT="8080"
REPO_URL="https://github.com/meetsohail/skydock-panel.git"
BRANCH="main"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Please run as root or with sudo"
        exit 1
    fi
}

check_os() {
    if [ ! -f /etc/os-release ]; then
        log_error "Cannot detect OS. This script supports Ubuntu LTS only."
        exit 1
    fi
    
    . /etc/os-release
    
    if [ "$ID" != "ubuntu" ]; then
        log_error "This script supports Ubuntu only. Detected: $ID"
        exit 1
    fi
    
    log_info "Detected OS: $PRETTY_NAME"
}

install_dependencies() {
    log_info "Updating package list..."
    apt-get update -qq
    
    log_info "Installing system dependencies..."
    apt-get install -y \
        git \
        curl \
        wget \
        python3 \
        python3-venv \
        python3-pip \
        python3-dev \
        build-essential \
        nginx \
        mysql-server \
        mysql-client \
        ufw \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release
    
    log_info "System dependencies installed"
}

create_skydock_user() {
    if id "$SKYDOCK_USER" &>/dev/null; then
        log_warn "User $SKYDOCK_USER already exists"
    else
        log_info "Creating user $SKYDOCK_USER..."
        useradd -r -m -s /bin/bash -d "$SKYDOCK_HOME" "$SKYDOCK_USER"
        log_info "User $SKYDOCK_USER created"
    fi
}

clone_repository() {
    log_info "Cloning SkyDock Panel repository..."
    
    if [ -d "$SKYDOCK_HOME" ]; then
        log_warn "Directory $SKYDOCK_HOME already exists. Updating..."
        cd "$SKYDOCK_HOME"
        git pull origin "$BRANCH" || log_warn "Could not update repository"
    else
        git clone -b "$BRANCH" "$REPO_URL" "$SKYDOCK_HOME"
        log_info "Repository cloned"
    fi
    
    chown -R "$SKYDOCK_USER:$SKYDOCK_USER" "$SKYDOCK_HOME"
}

setup_python_venv() {
    log_info "Setting up Python virtual environment..."
    
    cd "$SKYDOCK_HOME/backend"
    
    if [ -d "venv" ]; then
        log_warn "Virtual environment already exists"
    else
        python3 -m venv venv
        log_info "Virtual environment created"
    fi
    
    source venv/bin/activate
    
    log_info "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    log_info "Python dependencies installed"
}

setup_django() {
    log_info "Setting up Django..."
    
    cd "$SKYDOCK_HOME/backend"
    source venv/bin/activate
    
    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        log_info "Creating .env file..."
        cat > .env << EOF
DEBUG=False
SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
ALLOWED_HOSTS=*
SKYDOCK_PANEL_PORT=$SKYDOCK_PORT
SKYDOCK_WEB_ROOT=/var/www
SKYDOCK_NGINX_SITES_AVAILABLE=/etc/nginx/sites-available
SKYDOCK_NGINX_SITES_ENABLED=/etc/nginx/sites-enabled
SKYDOCK_APACHE_SITES_AVAILABLE=/etc/apache2/sites-available
SKYDOCK_APACHE_SITES_ENABLED=/etc/apache2/sites-enabled
SKYDOCK_ENCRYPTION_KEY=$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
EOF
        chown "$SKYDOCK_USER:$SKYDOCK_USER" .env
        log_info ".env file created"
    fi
    
    # Run migrations
    log_info "Running Django migrations..."
    python manage.py migrate --noinput
    
    # Create superuser if it doesn't exist
    log_info "Creating admin user..."
    ADMIN_EMAIL="admin@skydock.local"
    ADMIN_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    
    python manage.py shell << EOF
from accounts.models import User
if not User.objects.filter(email='$ADMIN_EMAIL').exists():
    User.objects.create_superuser('$ADMIN_EMAIL', '$ADMIN_PASSWORD')
    print('Admin user created')
else:
    print('Admin user already exists')
EOF
    
    # Collect static files
    log_info "Collecting static files..."
    python manage.py collectstatic --noinput
    
    log_info "Django setup complete"
    log_info "Admin credentials:"
    log_info "  Email: $ADMIN_EMAIL"
    log_info "  Password: $ADMIN_PASSWORD"
}

setup_systemd() {
    log_info "Setting up systemd service..."
    
    # Create systemd service file
    cat > /etc/systemd/system/skydock-panel.service << EOF
[Unit]
Description=SkyDock Panel - VPS Management Panel
After=network.target mysql.service

[Service]
Type=notify
User=$SKYDOCK_USER
Group=$SKYDOCK_USER
WorkingDirectory=$SKYDOCK_HOME/backend
Environment="PATH=$SKYDOCK_HOME/backend/venv/bin"
EnvironmentFile=$SKYDOCK_HOME/backend/.env
ExecStart=$SKYDOCK_HOME/backend/venv/bin/gunicorn \\
    --bind 127.0.0.1:$SKYDOCK_PORT \\
    --workers 3 \\
    --timeout 120 \\
    --access-logfile $SKYDOCK_HOME/logs/access.log \\
    --error-logfile $SKYDOCK_HOME/logs/error.log \\
    skydock_backend.wsgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Create logs directory
    mkdir -p "$SKYDOCK_HOME/logs"
    chown -R "$SKYDOCK_USER:$SKYDOCK_USER" "$SKYDOCK_HOME/logs"
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable skydock-panel.service
    systemctl start skydock-panel.service
    
    log_info "Systemd service configured and started"
}

setup_nginx() {
    log_info "Configuring Nginx reverse proxy..."
    
    # Create Nginx configuration
    cat > /etc/nginx/sites-available/skydock-panel << EOF
server {
    listen 80;
    server_name _;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://127.0.0.1:$SKYDOCK_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
    }
    
    location /static/ {
        alias $SKYDOCK_HOME/backend/staticfiles/;
    }
}
EOF
    
    # Enable site
    ln -sf /etc/nginx/sites-available/skydock-panel /etc/nginx/sites-enabled/
    
    # Remove default site if it exists
    rm -f /etc/nginx/sites-enabled/default
    
    # Test and reload Nginx
    nginx -t
    systemctl reload nginx
    
    log_info "Nginx configured"
}

setup_firewall() {
    log_info "Configuring firewall..."
    
    if command -v ufw &> /dev/null; then
        ufw allow 22/tcp
        ufw allow 80/tcp
        ufw allow 443/tcp
        ufw --force enable
        log_info "Firewall configured"
    else
        log_warn "UFW not found, skipping firewall configuration"
    fi
}

create_web_root() {
    log_info "Creating web root directory..."
    mkdir -p /var/www
    chown -R www-data:www-data /var/www
    chmod 755 /var/www
}

main() {
    log_info "Starting SkyDock Panel installation..."
    
    check_root
    check_os
    install_dependencies
    create_skydock_user
    clone_repository
    setup_python_venv
    setup_django
    setup_systemd
    setup_nginx
    setup_firewall
    create_web_root
    
    log_info ""
    log_info "=========================================="
    log_info "SkyDock Panel installation complete!"
    log_info "=========================================="
    log_info ""
    log_info "Access the panel at: http://$(hostname -I | awk '{print $1}')"
    log_info ""
    log_info "Admin credentials:"
    log_info "  Email: admin@skydock.local"
    log_info "  Password: (check output above)"
    log_info ""
    log_info "Service status: systemctl status skydock-panel"
    log_info "View logs: journalctl -u skydock-panel -f"
    log_info ""
}

# Run main function
main "$@"

