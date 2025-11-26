"""
Utilities for website management (creating sites, configuring web servers, etc.).
"""
import os
import secrets
import string
import logging
import subprocess
from typing import Dict, Optional
from django.conf import settings
from .models import Website, DatabaseCredential
from servers.ssh_utils import run_command

logger = logging.getLogger(__name__)


def generate_password(length: int = 16) -> str:
    """Generate a random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_directory(path: str, owner_user: Optional[str] = None) -> bool:
    """Create directory with proper permissions.
    
    Args:
        path: Directory path to create
        owner_user: Username to set as owner (defaults to www-data for web server access)
    """
    try:
        os.makedirs(path, exist_ok=True)
        
        # Set ownership - prefer owner_user if provided, otherwise use www-data
        if owner_user:
            # Set owner to the user, group to www-data for web server access
            exit_code, _, _ = run_command(['chown', '-R', f'{owner_user}:www-data', path], sudo=True)
            if exit_code != 0:
                # Fallback to user:user if www-data group doesn't exist
                run_command(['chown', '-R', f'{owner_user}:{owner_user}', path], sudo=True)
        else:
            # Default: www-data ownership for web server
            exit_code, _, _ = run_command(['chown', '-R', 'www-data:www-data', path], sudo=True)
            if exit_code != 0:
                # Try with current user if www-data doesn't exist
                import getpass
                current_user = getpass.getuser()
                run_command(['chown', '-R', f'{current_user}:{current_user}', path], sudo=True)
        
        run_command(['chmod', '-R', '755', path], sudo=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {path}: {e}")
        return False


def create_php_site(website: Website) -> Dict[str, any]:
    """Create a PHP website."""
    try:
        # Create document root with website owner as owner
        owner_username = website.user.username if website.user else None
        if not create_directory(website.root_path, owner_user=owner_username):
            return {'success': False, 'error': 'Failed to create document root'}
        
        # Create example index.php
        index_content = f"""<?php
// SkyDock Panel - {website.domain}
echo "<h1>Welcome to {website.domain}</h1>";
echo "<p>This is a PHP application managed by SkyDock Panel.</p>";
phpinfo();
"""
        index_path = os.path.join(website.root_path, 'index.php')
        with open(index_path, 'w') as f:
            f.write(index_content)
        
        # Set permissions (already set by create_directory, but ensure consistency)
        owner_username = website.user.username if website.user else 'www-data'
        run_command(['chown', '-R', f'{owner_username}:www-data', website.root_path], sudo=True)
        run_command(['chmod', '-R', '755', website.root_path], sudo=True)
        
        # Generate web server configuration - always use Apache with Nginx reverse proxy
        # Create Apache config first
        apache_result = create_apache_config(website)
        if not apache_result['success']:
            return apache_result
        
        # Create Nginx reverse proxy config
        nginx_result = create_nginx_reverse_proxy_config(website)
        if not nginx_result['success']:
            return nginx_result
        
        # Enable site and reload web servers
        enable_result = enable_website(website)
        if not enable_result['success']:
            return enable_result
        
        return {'success': True, 'message': f'PHP site {website.domain} created successfully'}
    except Exception as e:
        logger.error(f"Error creating PHP site: {e}")
        return {'success': False, 'error': str(e)}


def create_wordpress_site(website: Website, wp_email: str, wp_username: str, wp_password: str) -> Dict[str, any]:
    """Create a WordPress website."""
    try:
        # Create document root with website owner as owner
        owner_username = website.user.username if website.user else None
        if not create_directory(website.root_path, owner_user=owner_username):
            return {'success': False, 'error': 'Failed to create document root'}
        
        # Create database and user
        db_name = f"wp_{website.domain.replace('.', '_').replace('-', '_')}"
        db_user = db_name[:16]  # MySQL username limit
        db_password = generate_password()
        
        # Create database
        db_result = create_mysql_database(db_name, db_user, db_password)
        if not db_result['success']:
            return db_result
        
        # Save database credentials
        DatabaseCredential.objects.create(
            website=website,
            db_name=db_name,
            db_user=db_user,
            db_password=db_password,
            db_host='localhost'
        )
        
        # Download WordPress
        wp_result = download_wordpress(website.root_path)
        if not wp_result['success']:
            return wp_result
        
        # Create wp-config.php
        wp_config_result = create_wp_config(website, db_name, db_user, db_password)
        if not wp_config_result['success']:
            return wp_config_result
        
        # Auto-install WordPress with admin credentials
        install_result = install_wordpress(website, wp_email, wp_username, wp_password)
        if not install_result['success']:
            return install_result
        
        # Generate web server configuration - always use Apache with Nginx reverse proxy
        # Create Apache config first
        apache_result = create_apache_config(website)
        if not apache_result['success']:
            return apache_result
        
        # Create Nginx reverse proxy config
        nginx_result = create_nginx_reverse_proxy_config(website)
        if not nginx_result['success']:
            return nginx_result
        
        # Enable site and reload web servers
        enable_result = enable_website(website)
        if not enable_result['success']:
            return enable_result
        
        return {
            'success': True,
            'message': f'WordPress site {website.domain} created successfully',
            'database': {
                'name': db_name,
                'user': db_user,
                'password': db_password
            }
        }
    except Exception as e:
        logger.error(f"Error creating WordPress site: {e}")
        return {'success': False, 'error': str(e)}


def create_mysql_database(db_name: str, db_user: str, db_password: str) -> Dict[str, any]:
    """Create MySQL database and user."""
    try:
        # Create database
        exit_code, stdout, stderr = run_command([
            'mysql', '-e', f'CREATE DATABASE IF NOT EXISTS {db_name};'
        ], sudo=True)
        
        if exit_code != 0:
            return {'success': False, 'error': f'Failed to create database: {stderr}'}
        
        # Create user and grant privileges
        grant_sql = f"GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'localhost' IDENTIFIED BY '{db_password}'; FLUSH PRIVILEGES;"
        exit_code, stdout, stderr = run_command([
            'mysql', '-e', grant_sql
        ], sudo=True)
        
        if exit_code != 0:
            return {'success': False, 'error': f'Failed to create database user: {stderr}'}
        
        return {'success': True}
    except Exception as e:
        logger.error(f"Error creating MySQL database: {e}")
        return {'success': False, 'error': str(e)}


def download_wordpress(destination: str) -> Dict[str, any]:
    """Download and extract WordPress."""
    try:
        # Download WordPress
        wp_url = 'https://wordpress.org/latest.tar.gz'
        wp_archive = '/tmp/wordpress-latest.tar.gz'
        
        exit_code, stdout, stderr = run_command([
            'wget', '-q', '-O', wp_archive, wp_url
        ], sudo=False)
        
        if exit_code != 0:
            return {'success': False, 'error': f'Failed to download WordPress: {stderr}'}
        
        # Extract WordPress
        exit_code, stdout, stderr = run_command([
            'tar', '-xzf', wp_archive, '-C', destination, '--strip-components=1'
        ], sudo=True)
        
        if exit_code != 0:
            return {'success': False, 'error': f'Failed to extract WordPress: {stderr}'}
        
        # Clean up
        run_command(['rm', wp_archive], sudo=False)
        
        return {'success': True}
    except Exception as e:
        logger.error(f"Error downloading WordPress: {e}")
        return {'success': False, 'error': str(e)}


def create_wp_config(website: Website, db_name: str, db_user: str, db_password: str) -> Dict[str, any]:
    """Create wp-config.php file."""
    try:
        wp_config_path = os.path.join(website.root_path, 'wp-config.php')
        
        # Generate WordPress salts
        salt_keys = [
            'AUTH_KEY', 'SECURE_AUTH_KEY', 'LOGGED_IN_KEY', 'NONCE_KEY',
            'AUTH_SALT', 'SECURE_AUTH_SALT', 'LOGGED_IN_SALT', 'NONCE_SALT'
        ]
        salts = {}
        for key in salt_keys:
            salts[key] = generate_password(64)
        
        wp_config_content = f"""<?php
/**
 * SkyDock Panel - WordPress Configuration
 * Generated for {website.domain}
 */

define('DB_NAME', '{db_name}');
define('DB_USER', '{db_user}');
define('DB_PASSWORD', '{db_password}');
define('DB_HOST', 'localhost');
define('DB_CHARSET', 'utf8mb4');
define('DB_COLLATE', '');

define('AUTH_KEY',         '{salts["AUTH_KEY"]}');
define('SECURE_AUTH_KEY',  '{salts["SECURE_AUTH_KEY"]}');
define('LOGGED_IN_KEY',    '{salts["LOGGED_IN_KEY"]}');
define('NONCE_KEY',        '{salts["NONCE_KEY"]}');
define('AUTH_SALT',        '{salts["AUTH_SALT"]}');
define('SECURE_AUTH_SALT', '{salts["SECURE_AUTH_SALT"]}');
define('LOGGED_IN_SALT',   '{salts["LOGGED_IN_SALT"]}');
define('NONCE_SALT',       '{salts["NONCE_SALT"]}');

$table_prefix = 'wp_';

define('WP_DEBUG', false);

if ( !defined('ABSPATH') )
    define('ABSPATH', dirname(__FILE__) . '/');

require_once ABSPATH . 'wp-settings.php';
"""
        with open(wp_config_path, 'w') as f:
            f.write(wp_config_content)
        
        run_command(['chown', 'www-data:www-data', wp_config_path], sudo=True)
        run_command(['chmod', '600', wp_config_path], sudo=True)
        
        return {'success': True}
    except Exception as e:
        logger.error(f"Error creating wp-config.php: {e}")
        return {'success': False, 'error': str(e)}


def create_nginx_config(website: Website) -> Dict[str, any]:
    """Create Nginx virtual host configuration."""
    try:
        # Use raw string to avoid escape sequence warnings
        config_content = f"""server {{
    listen 80;
    server_name {website.domain} www.{website.domain};
    root {website.root_path};
    index index.php index.html index.htm;

    access_log /var/log/nginx/{website.domain}-access.log;
    error_log /var/log/nginx/{website.domain}-error.log;

    location / {{
        try_files $uri $uri/ /index.php?$args;
    }}

    location ~ \\.php$ {{
        fastcgi_pass unix:/var/run/php/php{website.php_version.replace(".", "")}-fpm.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }}

    location ~ /\\.ht {{
        deny all;
    }}
}}
"""
        config_path = os.path.join(settings.SKYDOCK_NGINX_SITES_AVAILABLE, website.domain)
        
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        return {'success': True, 'config_path': config_path}
    except Exception as e:
        logger.error(f"Error creating Nginx config: {e}")
        return {'success': False, 'error': str(e)}


def create_apache_config(website: Website) -> Dict[str, any]:
    """Create Apache virtual host configuration (runs on port 8080 for Nginx reverse proxy)."""
    try:
        config_content = f"""<VirtualHost *:8080>
    ServerName {website.domain}
    ServerAlias www.{website.domain}
    DocumentRoot {website.root_path}

    <Directory {website.root_path}>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog ${{APACHE_LOG_DIR}}/{website.domain}-error.log
    CustomLog ${{APACHE_LOG_DIR}}/{website.domain}-access.log combined
</VirtualHost>
"""
        config_path = os.path.join(settings.SKYDOCK_APACHE_SITES_AVAILABLE, f"{website.domain}.conf")
        
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        return {'success': True, 'config_path': config_path}
    except Exception as e:
        logger.error(f"Error creating Apache config: {e}")
        return {'success': False, 'error': str(e)}


def create_nginx_reverse_proxy_config(website: Website) -> Dict[str, any]:
    """Create Nginx reverse proxy configuration (proxies to Apache on port 8080)."""
    try:
        config_content = f"""server {{
    listen 80;
    server_name {website.domain} www.{website.domain};
    
    access_log /var/log/nginx/{website.domain}-access.log;
    error_log /var/log/nginx/{website.domain}-error.log;

    location / {{
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
    }}
}}
"""
        config_path = os.path.join(settings.SKYDOCK_NGINX_SITES_AVAILABLE, website.domain)
        
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        return {'success': True, 'config_path': config_path}
    except Exception as e:
        logger.error(f"Error creating Nginx reverse proxy config: {e}")
        return {'success': False, 'error': str(e)}


def install_wordpress(website: Website, wp_email: str, wp_username: str, wp_password: str) -> Dict[str, any]:
    """Auto-install WordPress using WP-CLI or direct database setup."""
    try:
        # Check if WP-CLI is available
        wp_cli_path = '/usr/local/bin/wp'
        if not os.path.exists(wp_cli_path):
            # Try to find wp in PATH
            exit_code, stdout, stderr = run_command(['which', 'wp'], sudo=False)
            if exit_code == 0:
                wp_cli_path = stdout.strip()
            else:
                # Install WP-CLI
                logger.info("Installing WP-CLI...")
                install_wp_cli_result = install_wp_cli()
                if not install_wp_cli_result['success']:
                    return {'success': False, 'error': 'Failed to install WP-CLI'}
                wp_cli_path = '/usr/local/bin/wp'
        
        # Run WordPress installation via WP-CLI
        install_cmd = [
            wp_cli_path,
            'core',
            'install',
            '--url=http://' + website.domain,
            '--title=' + website.domain,
            '--admin_user=' + wp_username,
            '--admin_password=' + wp_password,
            '--admin_email=' + wp_email,
            '--path=' + website.root_path,
            '--allow-root'
        ]
        
        exit_code, stdout, stderr = run_command(install_cmd, sudo=True, cwd=website.root_path)
        
        if exit_code != 0:
            logger.error(f"WP-CLI install failed: {stderr}")
            return {'success': False, 'error': f'WordPress installation failed: {stderr}'}
        
        logger.info(f"WordPress installed successfully for {website.domain}")
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Error installing WordPress: {e}")
        return {'success': False, 'error': str(e)}


def install_wp_cli() -> Dict[str, any]:
    """Install WP-CLI if not already installed."""
    try:
        wp_cli_path = '/usr/local/bin/wp'
        if os.path.exists(wp_cli_path):
            return {'success': True}
        
        # Download WP-CLI
        exit_code, stdout, stderr = run_command([
            'curl', '-O', 'https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar'
        ], sudo=True, cwd='/tmp')
        
        if exit_code != 0:
            return {'success': False, 'error': 'Failed to download WP-CLI'}
        
        # Make executable and move to /usr/local/bin
        run_command(['chmod', '+x', '/tmp/wp-cli.phar'], sudo=True)
        run_command(['mv', '/tmp/wp-cli.phar', wp_cli_path], sudo=True)
        
        return {'success': True}
    except Exception as e:
        logger.error(f"Error installing WP-CLI: {e}")
        return {'success': False, 'error': str(e)}


def enable_website(website: Website) -> Dict[str, any]:
    """Enable website by creating symlinks and reloading web servers (Nginx + Apache)."""
    try:
        # Always enable both Nginx (reverse proxy) and Apache (backend)
        
        # Enable Apache site
        exit_code, stdout, stderr = run_command([
            'a2ensite', f"{website.domain}.conf"
        ], sudo=True)
        
        if exit_code != 0:
            return {'success': False, 'error': f'Failed to enable Apache site: {stderr}'}
        
        # Test and reload Apache
        exit_code, stdout, stderr = run_command(['apache2ctl', 'configtest'], sudo=True)
        if exit_code != 0:
            return {'success': False, 'error': f'Apache config test failed: {stderr}'}
        
        exit_code, stdout, stderr = run_command(['systemctl', 'reload', 'apache2'], sudo=True)
        if exit_code != 0:
            return {'success': False, 'error': f'Failed to reload Apache: {stderr}'}
        
        # Enable Nginx site (reverse proxy)
        source = os.path.join(settings.SKYDOCK_NGINX_SITES_AVAILABLE, website.domain)
        target = os.path.join(settings.SKYDOCK_NGINX_SITES_ENABLED, website.domain)
        
        if os.path.exists(target):
            os.remove(target)
        os.symlink(source, target)
        
        # Test and reload Nginx
        exit_code, stdout, stderr = run_command(['nginx', '-t'], sudo=True)
        if exit_code != 0:
            return {'success': False, 'error': f'Nginx config test failed: {stderr}'}
        
        exit_code, stdout, stderr = run_command(['systemctl', 'reload', 'nginx'], sudo=True)
        if exit_code != 0:
            return {'success': False, 'error': f'Failed to reload Nginx: {stderr}'}
        
        return {'success': True}
    except Exception as e:
        logger.error(f"Error enabling website: {e}")
        return {'success': False, 'error': str(e)}


def disable_website(website: Website) -> Dict[str, any]:
    """Disable website by removing symlinks and reloading web servers (Nginx + Apache)."""
    try:
        # Disable Apache site
        exit_code, stdout, stderr = run_command([
            'a2dissite', f"{website.domain}.conf"
        ], sudo=True)
        
        if exit_code != 0:
            return {'success': False, 'error': f'Failed to disable Apache site: {stderr}'}
        
        exit_code, stdout, stderr = run_command(['systemctl', 'reload', 'apache2'], sudo=True)
        if exit_code != 0:
            return {'success': False, 'error': f'Failed to reload Apache: {stderr}'}
        
        # Disable Nginx site
        target = os.path.join(settings.SKYDOCK_NGINX_SITES_ENABLED, website.domain)
        if os.path.exists(target):
            os.remove(target)
        
        exit_code, stdout, stderr = run_command(['systemctl', 'reload', 'nginx'], sudo=True)
        if exit_code != 0:
            return {'success': False, 'error': f'Failed to reload Nginx: {stderr}'}
        
        return {'success': True}
    except Exception as e:
        logger.error(f"Error disabling website: {e}")
        return {'success': False, 'error': str(e)}

