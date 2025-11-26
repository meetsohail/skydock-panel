#!/bin/bash

###############################################################################
# SkyDock Panel Installation Script
# This script installs SkyDock Panel on a fresh Ubuntu server
###############################################################################

# Don't use set -e, we'll handle errors with trap
set -o pipefail  # Fail on pipe errors

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SKYDOCK_USER="skydock"
SKYDOCK_HOME="/opt/skydock-panel"
SKYDOCK_PORT="8080"
REPO_URL="git@github.com:meetsohail/skydock-panel.git"
REPO_URL_HTTPS="https://github.com/meetsohail/skydock-panel.git"
BRANCH="master"

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

check_skydock_installed() {
    # Check if SkyDock Panel is already installed
    if [ -d "$SKYDOCK_HOME" ] && [ -f "$SKYDOCK_HOME/backend/manage.py" ]; then
        return 0  # Installed
    fi
    return 1  # Not installed
}

check_fresh_server() {
    log_info "Checking server status..."
    
    local is_fresh=true
    local warnings=()
    local skydock_installed=false
    
    # Check if SkyDock Panel is already installed
    if check_skydock_installed; then
        skydock_installed=true
        log_info "SkyDock Panel is already installed. Will update the installation."
        return 0  # Allow update
    fi
    
    # Check for incomplete SkyDock installation
    if [ -d "$SKYDOCK_HOME" ] && [ ! -f "$SKYDOCK_HOME/backend/manage.py" ]; then
        log_error "=========================================="
        log_error "ERROR: Incomplete SkyDock Panel installation detected!"
        log_error "=========================================="
        log_error ""
        log_error "Directory $SKYDOCK_HOME exists but is not a valid SkyDock Panel installation."
        log_error "Please remove it manually and try again:"
        log_error "  rm -rf $SKYDOCK_HOME"
        log_error ""
        exit 1
    fi
    
    # Check for other web panels or conflicting applications
    if systemctl list-units --type=service --state=running | grep -qiE "(cpanel|plesk|vestacp|cyberpanel|aaapanel)"; then
        warnings+=("Another control panel is detected (cPanel/Plesk/VestaCP/CyberPanel/aaPanel)")
        is_fresh=false
    fi
    
    # Check for other Python web applications (excluding SkyDock)
    if systemctl list-units --type=service --state=running | grep -qiE "(gunicorn|uwsgi)" | grep -v "skydock-panel"; then
        warnings+=("Other Python web applications detected")
        is_fresh=false
    fi
    
    # Check for existing websites in /var/www (only if not SkyDock)
    if [ -d "/var/www" ]; then
        website_count=$(find /var/www -mindepth 1 -maxdepth 1 -type d ! -empty 2>/dev/null | wc -l)
        if [ "$website_count" -gt 0 ]; then
            # Check if these are SkyDock-managed sites
            skydock_sites=$(find /var/www -mindepth 1 -maxdepth 1 -type d -exec test -f {}/.skydock \; -print 2>/dev/null | wc -l)
            if [ "$website_count" -gt "$skydock_sites" ]; then
                warnings+=("Existing websites found in /var/www (not managed by SkyDock)")
                is_fresh=false
            fi
        fi
    fi
    
    if [ "$is_fresh" = false ]; then
        log_error "=========================================="
        log_error "ERROR: Server is not suitable for fresh installation!"
        log_error "=========================================="
        log_error ""
        log_error "This installer is designed for FRESH Ubuntu servers only."
        log_error "The following conflicts were detected:"
        log_error ""
        for warning in "${warnings[@]}"; do
            log_error "  - $warning"
        done
        log_error ""
        log_error "For safety reasons, installation cannot proceed on a server"
        log_error "with conflicting web services or applications."
        log_error ""
        log_error "Please use a fresh Ubuntu server, or if SkyDock is already installed,"
        log_error "the installer will update it automatically."
        log_error ""
        exit 1
    fi
    
    log_info "Server appears to be fresh. Proceeding with installation..."
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

setup_github_ssh() {
    log_info "Setting up GitHub SSH host key..."
    
    # Create .ssh directory if it doesn't exist
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh
    
    # Add GitHub to known_hosts if not already present
    if ! grep -q "github.com" ~/.ssh/known_hosts 2>/dev/null; then
        log_info "Adding GitHub to known_hosts..."
        ssh-keyscan -t rsa,ecdsa,ed25519 github.com >> ~/.ssh/known_hosts 2>/dev/null
        chmod 600 ~/.ssh/known_hosts
        log_info "GitHub SSH host key added"
    fi
}

clone_repository() {
    log_info "Cloning/Updating SkyDock Panel repository..."
    
    # Setup GitHub SSH to avoid host key prompt
    setup_github_ssh
    
    # Configure git to automatically accept new host keys
    export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"
    
    # Pre-configure safe.directory for root user to avoid ownership issues
    git config --global --add safe.directory "$SKYDOCK_HOME" 2>/dev/null || true
    
    # Check if SkyDock is already installed
    if check_skydock_installed; then
        log_info "SkyDock Panel is already installed. Updating code..."
        
        # Fix Git ownership issue - add to safe.directory BEFORE any git operations
        log_info "Configuring Git safe directory..."
        git config --global --add safe.directory "$SKYDOCK_HOME" 2>/dev/null || {
            # If --add fails, try --replace-all
            git config --global --replace-all safe.directory "$SKYDOCK_HOME" 2>/dev/null || true
        }
        
        cd "$SKYDOCK_HOME" || {
            log_error "Failed to change to $SKYDOCK_HOME"
            exit 1
        }
        
        # Check if it's a git repository
        if [ -d ".git" ]; then
            # Ensure safe.directory is set (multiple methods for compatibility)
            git config --global --add safe.directory "$SKYDOCK_HOME" 2>/dev/null || true
            git config --global --add safe.directory "*" 2>/dev/null || true
            
            # Stash any local changes (using -c flag to override safe.directory check)
            git -c safe.directory="$SKYDOCK_HOME" stash > /dev/null 2>&1 || true
            
            # Pull latest changes (using -c flag to override safe.directory check)
            if git -c safe.directory="$SKYDOCK_HOME" pull origin "$BRANCH"; then
                log_info "Repository updated successfully"
            else
                log_error "Failed to update repository. Please check:"
                log_error "  1. Repository URL is correct"
                log_error "  2. Branch exists: $BRANCH"
                log_error "  3. You have internet connectivity"
                log_error "  4. No local conflicts exist"
                exit 1
            fi
        else
            log_warn "Installation directory exists but is not a git repository."
            log_warn "Backing up and cloning fresh..."
            BACKUP_DIR="${SKYDOCK_HOME}.backup.$(date +%s)"
            if mv "$SKYDOCK_HOME" "$BACKUP_DIR" 2>/dev/null; then
                log_info "Backed up to $BACKUP_DIR"
                # Continue to clone below
            else
                log_error "Failed to backup existing directory. Please remove it manually:"
                log_error "  rm -rf $SKYDOCK_HOME"
                exit 1
            fi
        fi
    fi
    
    # Clone if directory doesn't exist or was backed up
    if [ ! -d "$SKYDOCK_HOME" ] || [ ! -d "$SKYDOCK_HOME/.git" ]; then
        # Try SSH clone first (with auto-accept host key)
        log_info "Attempting to clone via SSH..."
        if GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new" git clone -b "$BRANCH" "$REPO_URL" "$SKYDOCK_HOME" 2>/dev/null; then
            log_info "Repository cloned via SSH"
        else
            log_warn "SSH clone failed, trying HTTPS..."
            if git clone -b "$BRANCH" "$REPO_URL_HTTPS" "$SKYDOCK_HOME"; then
                log_info "Repository cloned via HTTPS"
            else
                log_error "Failed to clone repository. Please check:"
                log_error "  1. Repository URL is correct"
                log_error "  2. Branch exists: $BRANCH"
                log_error "  3. You have internet connectivity"
                log_error "  4. SSH keys are set up (for SSH) or repository is public (for HTTPS)"
                exit 1
            fi
        fi
    fi
    
    # Verify the backend directory exists
    if [ ! -d "$SKYDOCK_HOME/backend" ]; then
        log_error "Repository structure is invalid. Backend directory not found."
        log_error "Please ensure the repository contains the correct structure."
        log_error "Expected: $SKYDOCK_HOME/backend/"
        exit 1
    fi
    
    # Verify manage.py exists
    if [ ! -f "$SKYDOCK_HOME/backend/manage.py" ]; then
        log_error "Repository structure is invalid. manage.py not found."
        log_error "Please ensure the repository contains the correct Django structure."
        exit 1
    fi
    
    # Fix Git ownership issue - add to safe.directory before operations
    git config --global --add safe.directory "$SKYDOCK_HOME" 2>/dev/null || true
    
    chown -R "$SKYDOCK_USER:$SKYDOCK_USER" "$SKYDOCK_HOME"
    log_info "Repository setup complete"
}

setup_python_venv() {
    log_info "Setting up Python virtual environment..."
    
    # Verify backend directory exists
    if [ ! -d "$SKYDOCK_HOME/backend" ]; then
        log_error "Backend directory not found at $SKYDOCK_HOME/backend"
        log_error "Please ensure the repository was cloned correctly."
        exit 1
    fi
    
    cd "$SKYDOCK_HOME/backend" || {
        log_error "Failed to change to backend directory"
        exit 1
    }
    
    if [ -d "venv" ]; then
        log_warn "Virtual environment already exists"
    else
        python3 -m venv venv
        log_info "Virtual environment created"
    fi
    
    source venv/bin/activate
    
    # Check if requirements.txt exists
    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txt not found in backend directory"
        exit 1
    fi
    
    log_info "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    log_info "Python dependencies installed"
}

setup_django() {
    log_info "Setting up Django..."
    
    cd "$SKYDOCK_HOME/backend" || {
        log_error "Failed to change to backend directory"
        exit 1
    }
    
    source venv/bin/activate
    
    local is_update=false
    if [ -f .env ] && [ -f db.sqlite3 ]; then
        is_update=true
        log_info "Detected existing Django installation. Updating..."
    fi
    
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
    else
        log_info "Using existing .env file"
    fi
    
    # Run migrations
    log_info "Running Django migrations..."
    if python manage.py migrate --noinput; then
        log_info "Migrations completed successfully"
    else
        log_error "Migration failed. Please check the error above."
        exit 1
    fi
    
    # Create superuser only if it doesn't exist (new installation)
    if [ "$is_update" = false ]; then
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
        
        log_info "Admin credentials:"
        log_info "  Email: $ADMIN_EMAIL"
        log_info "  Password: $ADMIN_PASSWORD"
    else
        log_info "Skipping admin user creation (update mode)"
    fi
    
    # Collect static files
    log_info "Collecting static files..."
    if python manage.py collectstatic --noinput; then
        log_info "Static files collected"
    else
        log_warn "Static file collection had warnings, but continuing..."
    fi
    
    log_info "Django setup complete"
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

handle_error() {
    local line_number=$1
    local error_code=$2
    log_error ""
    log_error "=========================================="
    log_error "ERROR: Installation failed!"
    log_error "=========================================="
    log_error ""
    log_error "Installation failed at line $line_number with exit code $error_code"
    log_error ""
    log_error "Please check the error messages above and try again."
    log_error ""
    log_error "If the issue persists, you can:"
    log_error "  1. Check logs: journalctl -u skydock-panel -f"
    log_error "  2. Remove incomplete installation: rm -rf $SKYDOCK_HOME"
    log_error "  3. Review the installation guide in README.md"
    log_error ""
    exit $error_code
}

main() {
    # Set error trap
    trap 'handle_error $LINENO $?' ERR
    
    log_info "Starting SkyDock Panel installation..."
    
    # Check if updating existing installation
    local is_update=false
    if check_skydock_installed; then
        is_update=true
        log_info "Detected existing SkyDock Panel installation. Updating..."
    fi
    
    check_root
    check_os
    
    if [ "$is_update" = false ]; then
        check_fresh_server
    fi
    
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
    if [ "$is_update" = true ]; then
        log_info "SkyDock Panel update complete!"
    else
        log_info "SkyDock Panel installation complete!"
    fi
    log_info "=========================================="
    log_info ""
    log_info "Access the panel at: http://$(hostname -I | awk '{print $1}')"
    log_info ""
    if [ "$is_update" = false ]; then
        log_info "Admin credentials:"
        log_info "  Email: admin@skydock.local"
        log_info "  Password: (check output above)"
        log_info ""
    fi
    log_info "Service status: systemctl status skydock-panel"
    log_info "View logs: journalctl -u skydock-panel -f"
    log_info ""
    
    # Disable error trap on success
    trap - ERR
}

# Run main function
main "$@"

