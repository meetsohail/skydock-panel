#!/bin/bash

###############################################################################
# SkyDock Panel Uninstallation Script
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SKYDOCK_USER="skydock"
SKYDOCK_HOME="/opt/skydock-panel"

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

main() {
    check_root
    
    log_warn "This will remove SkyDock Panel from your system."
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        log_info "Uninstallation cancelled"
        exit 0
    fi
    
    log_info "Stopping services..."
    systemctl stop skydock-panel.service 2>/dev/null || true
    systemctl disable skydock-panel.service 2>/dev/null || true
    
    log_info "Removing systemd service..."
    rm -f /etc/systemd/system/skydock-panel.service
    systemctl daemon-reload
    
    log_info "Removing Nginx configuration..."
    rm -f /etc/nginx/sites-enabled/skydock-panel
    rm -f /etc/nginx/sites-available/skydock-panel
    systemctl reload nginx 2>/dev/null || true
    
    log_info "Removing installation directory..."
    rm -rf "$SKYDOCK_HOME"
    
    log_info "Removing user (optional)..."
    read -p "Remove user $SKYDOCK_USER? (yes/no): " remove_user
    if [ "$remove_user" = "yes" ]; then
        userdel -r "$SKYDOCK_USER" 2>/dev/null || true
    fi
    
    log_info "SkyDock Panel has been uninstalled"
}

main "$@"

