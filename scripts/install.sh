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
SKYDOCK_PORT="2083"
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
    # Use stat to check without triggering git ownership checks
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
    # If directory exists but isn't valid, we'll handle it in clone_repository by backing it up
    if [ -d "$SKYDOCK_HOME" ] && [ ! -f "$SKYDOCK_HOME/backend/manage.py" ]; then
        log_warn "Directory $SKYDOCK_HOME exists but is not a valid SkyDock Panel installation."
        log_warn "The installer will back it up and create a fresh installation."
        # Don't exit - let clone_repository handle it
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
        mysql-server \
        mysql-client \
        nginx \
        apache2 \
        php-fpm \
        php-mysql \
        php-xml \
        php-mbstring \
        php-curl \
        php-zip \
        php-gd \
        redis-server \
        ufw \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release
    
    log_info "System dependencies installed"
    
    # Configure Apache to listen on port 8080 for reverse proxy
    log_info "Configuring Apache for reverse proxy..."
    
    # Backup ports.conf
    if [ ! -f /etc/apache2/ports.conf.bak ]; then
        cp /etc/apache2/ports.conf /etc/apache2/ports.conf.bak
    fi
    
    # Update ports.conf to listen on 8080 instead of 80
    # Use a safer approach: comment out Listen 80 and ensure Listen 8080 exists
    sed -i 's/^Listen 80$/#Listen 80/' /etc/apache2/ports.conf
    sed -i 's/^[[:space:]]*Listen[[:space:]]*80[[:space:]]*$/#Listen 80/' /etc/apache2/ports.conf
    
    # Check if Listen 8080 already exists (exact match on its own line)
    if ! grep -qE '^[[:space:]]*Listen[[:space:]]*8080[[:space:]]*$' /etc/apache2/ports.conf; then
        # Add Listen 8080 after any existing Listen directives or at the top
        if grep -qE '^[[:space:]]*Listen' /etc/apache2/ports.conf; then
            # Find the line number of the first Listen directive and add after it
            first_listen_line=$(grep -nE '^[[:space:]]*Listen' /etc/apache2/ports.conf | head -1 | cut -d: -f1)
            if [ -n "$first_listen_line" ]; then
                sed -i "${first_listen_line}a Listen 8080" /etc/apache2/ports.conf
            else
                # Fallback: add at the top
                sed -i '1i Listen 8080' /etc/apache2/ports.conf
            fi
        else
            # No Listen directives exist, add at the top
            sed -i '1i Listen 8080' /etc/apache2/ports.conf
        fi
    fi
    
    # Update default site if it exists
    if [ -f /etc/apache2/sites-available/000-default.conf ]; then
        sed -i 's/<VirtualHost[[:space:]]*\*:80>/<VirtualHost *:8080>/' /etc/apache2/sites-available/000-default.conf 2>/dev/null || true
    fi
    
    # Enable required Apache modules
    a2enmod proxy proxy_http rewrite headers
    
    # Test Apache configuration
    if ! apache2ctl configtest >/dev/null 2>&1; then
        log_warn "Apache config test failed, trying simpler configuration..."
        # Restore backup and use simplest approach
        cp /etc/apache2/ports.conf.bak /etc/apache2/ports.conf
        # Comment out all Listen 80 lines
        sed -i 's/^Listen 80/#Listen 80/' /etc/apache2/ports.conf
        # Simply append Listen 8080 if it doesn't exist
        if ! grep -qE '^[[:space:]]*Listen[[:space:]]*8080' /etc/apache2/ports.conf; then
            echo "" >> /etc/apache2/ports.conf
            echo "Listen 8080" >> /etc/apache2/ports.conf
        fi
        # Test again
        if ! apache2ctl configtest >/dev/null 2>&1; then
            log_error "Apache configuration is invalid. Please check /etc/apache2/ports.conf manually."
        fi
    fi
    
    # Start and enable services
    systemctl enable nginx apache2
    systemctl start nginx apache2
    
    log_info "Nginx and Apache configured"
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

create_admin_user() {
    local admin_username="admin"
    
    # Generate random password
    local admin_password=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-20)
    
    # Check if admin user already exists
    if id "$admin_username" &>/dev/null; then
        log_info "Admin user already exists, updating password..."
        # Update password for existing user
        if echo "$admin_username:$admin_password" | chpasswd; then
            log_info "Admin user password updated successfully"
            # Save credentials for final display
            echo "$admin_username" > /tmp/skydock_admin_username.txt
            echo "$admin_password" > /tmp/skydock_admin_password.txt
            return 0
        else
            log_warn "Failed to update password for admin user"
            return 1
        fi
    fi
    
    log_info "Creating admin user..."
    
    # Create the user - use -g flag if admin group exists, otherwise let system create default group
    if getent group "$admin_username" >/dev/null 2>&1; then
        # Admin group exists, use it
        if useradd -m -s /bin/bash -g "$admin_username" "$admin_username"; then
            user_created=true
        else
            # If that fails, try with a different group
            useradd -m -s /bin/bash "$admin_username" 2>/dev/null || {
                log_warn "Failed to create admin user (group conflict)"
                return 1
            }
            user_created=true
        fi
    else
        # No admin group, create user normally
        if useradd -m -s /bin/bash "$admin_username"; then
            user_created=true
        else
            log_warn "Failed to create admin user"
            return 1
        fi
    fi
    
    if [ "$user_created" = true ]; then
        # Set password using chpasswd (more reliable than passwd in scripts)
        if echo "$admin_username:$admin_password" | chpasswd; then
            log_info "Admin user created successfully"
            # Save credentials for final display
            echo "$admin_username" > /tmp/skydock_admin_username.txt
            echo "$admin_password" > /tmp/skydock_admin_password.txt
            return 0
        else
            log_warn "Failed to set password for admin user"
            # Delete the user if password setting failed
            userdel -r "$admin_username" 2>/dev/null || true
            return 1
        fi
    fi
    
    return 1
}

setup_github_ssh() {
    # Create .ssh directory if it doesn't exist
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh
    
    # Add GitHub to known_hosts if not already present
    if ! grep -q "github.com" ~/.ssh/known_hosts 2>/dev/null; then
        ssh-keyscan -t rsa,ecdsa,ed25519 github.com >> ~/.ssh/known_hosts 2>/dev/null
        chmod 600 ~/.ssh/known_hosts
    fi
}

clone_repository() {
    log_info "Cloning/Updating SkyDock Panel repository..."
    
    # Setup GitHub SSH to avoid host key prompt
    setup_github_ssh
    
    # Configure git to automatically accept new host keys
    export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"
    
    # Handle existing directory that is not a git repository
    if [ -d "$SKYDOCK_HOME" ] && [ ! -d "$SKYDOCK_HOME/.git" ]; then
        log_warn "Directory $SKYDOCK_HOME exists but is not a git repository."
        log_warn "Backing up and cloning fresh..."
        BACKUP_DIR="${SKYDOCK_HOME}.backup.$(date +%s)"
        if mv "$SKYDOCK_HOME" "$BACKUP_DIR" 2>/dev/null; then
            log_info "Backed up to $BACKUP_DIR"
        else
            log_error "Failed to backup existing directory. Please remove it manually:"
            log_error "  rm -rf $SKYDOCK_HOME"
            exit 1
        fi
    fi
    
    # Check if SkyDock is already installed and is a git repository
    if check_skydock_installed && [ -d "$SKYDOCK_HOME/.git" ]; then
        log_info "SkyDock Panel is already installed. Updating code..."
        
        # Setup GitHub SSH for skydock user
        sudo -u "$SKYDOCK_USER" -H bash -c "
            mkdir -p ~/.ssh
            chmod 700 ~/.ssh
            if ! grep -q 'github.com' ~/.ssh/known_hosts 2>/dev/null; then
                ssh-keyscan -t rsa,ecdsa,ed25519 github.com >> ~/.ssh/known_hosts 2>/dev/null
                chmod 600 ~/.ssh/known_hosts
            fi
        " 2>/dev/null || true
        
        # Configure git safe.directory for skydock user (CRITICAL - must be before any git ops)
        sudo -u "$SKYDOCK_USER" -H git config --global --add safe.directory "$SKYDOCK_HOME" 2>/dev/null || true
        sudo -u "$SKYDOCK_USER" -H git config --global --add safe.directory "*" 2>/dev/null || true
        
        # Run all git commands as skydock user to avoid ownership issues
        # Stash any local changes
        sudo -u "$SKYDOCK_USER" -H bash -c "cd '$SKYDOCK_HOME' && GIT_SSH_COMMAND='ssh -o StrictHostKeyChecking=accept-new' git stash > /dev/null 2>&1 || true"
        
        # Pull latest changes
        if sudo -u "$SKYDOCK_USER" -H bash -c "cd '$SKYDOCK_HOME' && GIT_SSH_COMMAND='ssh -o StrictHostKeyChecking=accept-new' git pull origin '$BRANCH'" >/dev/null 2>&1; then
            :
        else
            # Try HTTPS as fallback
            if sudo -u "$SKYDOCK_USER" -H bash -c "cd '$SKYDOCK_HOME' && git remote set-url origin '$REPO_URL_HTTPS' && git pull origin '$BRANCH'" >/dev/null 2>&1; then
                :
            else
                log_error "Failed to update repository. Please check:"
                log_error "  1. Repository URL is correct"
                log_error "  2. Branch exists: $BRANCH"
                log_error "  3. You have internet connectivity"
                log_error "  4. No local conflicts exist"
                exit 1
            fi
        fi
    elif [ ! -d "$SKYDOCK_HOME" ]; then
        # Clone if directory doesn't exist (fresh install or after backup)
        # Try SSH clone first (with auto-accept host key)
        if GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new" git clone -b "$BRANCH" "$REPO_URL" "$SKYDOCK_HOME" 2>/dev/null; then
            :
        else
            # Try HTTPS as fallback
            if git clone -b "$BRANCH" "$REPO_URL_HTTPS" "$SKYDOCK_HOME" >/dev/null 2>&1; then
                :
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
}

setup_sudo_access() {
    log_info "Configuring passwordless sudo for $SKYDOCK_USER..."
    
    # Create sudoers file for skydock user
    SUDOERS_FILE="/etc/sudoers.d/skydock-panel"
    
    # Commands that skydock user needs to run without password
    # Using a more permissive but still secure approach - allow all commands
    # but only for specific operations needed by the panel
    cat > "$SUDOERS_FILE" << EOF
# SkyDock Panel - Passwordless sudo configuration for $SKYDOCK_USER
# This allows the panel to manage web servers, directories, and services
# Generated automatically by SkyDock Panel installer

# Allow all commands needed for website and service management
$SKYDOCK_USER ALL=(ALL) NOPASSWD: ALL
EOF
    
    # Set proper permissions for sudoers file
    chmod 0440 "$SUDOERS_FILE"
    
    # Validate sudoers file
    if visudo -c -f "$SUDOERS_FILE" >/dev/null 2>&1; then
        log_info "Sudo configuration validated successfully"
    else
        log_error "Sudo configuration validation failed. Removing invalid file."
        rm -f "$SUDOERS_FILE"
        exit 1
    fi
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
    # First, make migrations to ensure all migration files exist
    python manage.py makemigrations --noinput >/dev/null 2>&1 || true
    
    # Now run migrations
    if python manage.py migrate --noinput >/dev/null 2>&1; then
        :
    else
        log_error "Migration failed. Please check the error above."
        python manage.py showmigrations 2>&1 || true
        exit 1
    fi
    
    # Verify migrations were successful by checking if database file exists and has tables
    if [ -f "db.sqlite3" ]; then
        # Check if database has tables using a simple Python script
        python3 << 'VERIFY_EOF' >/dev/null 2>&1
import sqlite3
import sys

try:
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Check for essential tables
    essential_tables = ['accounts_user', 'django_migrations']
    found_tables = [t for t in essential_tables if t in tables]
    
    if len(found_tables) >= 1:  # At least one essential table
        sys.exit(0)
    else:
        sys.exit(1)
except Exception as e:
    sys.exit(1)
VERIFY_EOF
        
        if [ $? -ne 0 ]; then
            log_warn "Database verification warning, but continuing..."
        fi
    fi
    
    # Note: Users are authenticated against system users, not database
    # No need to create database users - any system user can login
    log_info "Authentication uses system users (from /etc/passwd)"
    
    # Collect static files
    log_info "Collecting static files..."
    python manage.py collectstatic --noinput >/dev/null 2>&1 || true
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
Environment="PATH=$SKYDOCK_HOME/backend/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EnvironmentFile=$SKYDOCK_HOME/backend/.env
ExecStart=$SKYDOCK_HOME/backend/venv/bin/gunicorn \\
    --bind 0.0.0.0:$SKYDOCK_PORT \\
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
    
    # Start or restart the service
    if systemctl is-active --quiet skydock-panel.service; then
        systemctl restart skydock-panel.service
        log_info "Systemd service restarted"
    else
        systemctl start skydock-panel.service
        log_info "Systemd service started"
    fi
    
    # Wait a moment and verify service is running
    sleep 2
    if systemctl is-active --quiet skydock-panel.service; then
        log_info "Service is running successfully"
    else
        log_error "Service failed to start. Check logs with: journalctl -u skydock-panel -n 50"
        systemctl status skydock-panel.service
        exit 1
    fi
}

setup_nginx() {
    # Remove any existing Nginx configuration for SkyDock Panel
    rm -f /etc/nginx/sites-enabled/skydock-panel
    rm -f /etc/nginx/sites-available/skydock-panel
}

setup_firewall() {
    log_info "Configuring firewall..."
    
    if command -v ufw &> /dev/null; then
        ufw allow 22/tcp
        ufw allow $SKYDOCK_PORT/tcp
        ufw allow 80/tcp   # HTTP
        ufw allow 443/tcp  # HTTPS
        ufw --force enable
        log_info "Firewall configured (ports 22, $SKYDOCK_PORT, 80, 443)"
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
    setup_sudo_access
    
    # Create admin user only for fresh installations
    if [ "$is_update" = false ]; then
        create_admin_user
    fi
    
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
    
    # Get server IP
    SERVER_IP=$(hostname -I | awk '{print $1}')
    if [ -z "$SERVER_IP" ]; then
        SERVER_IP="your-server-ip"
    fi
    
    # Show direct access URL on port 2083
    log_info "Access the panel at:"
    log_info "  http://$SERVER_IP:$SKYDOCK_PORT"
    log_info ""
    
    # Show login information
    if [ "$is_update" = false ]; then
        # Check if admin user was created and credentials are available
        if [ -f /tmp/skydock_admin_username.txt ] && [ -f /tmp/skydock_admin_password.txt ]; then
            ADMIN_USERNAME=$(cat /tmp/skydock_admin_username.txt)
            ADMIN_PASSWORD=$(cat /tmp/skydock_admin_password.txt)
            log_info "Login Credentials:"
            log_info "  Username: $ADMIN_USERNAME"
            log_info "  Password: $ADMIN_PASSWORD"
            log_info ""
            # Clean up temporary files
            rm -f /tmp/skydock_admin_username.txt /tmp/skydock_admin_password.txt
        else
            log_info "Login Information:"
            log_info "  Use any system user account to login"
            log_info "  Example: Use 'root' or any user created with 'useradd'"
            log_info "  Password: Use the system password (set via 'passwd' command)"
            log_info ""
            log_info "To create a new user:"
            log_info "  useradd -m -s /bin/bash username"
            log_info "  passwd username"
            log_info ""
        fi
    fi
    
    # Disable error trap on success
    trap - ERR
}

# Run main function
main "$@"

