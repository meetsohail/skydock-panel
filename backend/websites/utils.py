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


def create_directory(path: str) -> bool:
    """Create directory with proper permissions."""
    try:
        os.makedirs(path, exist_ok=True)
        # Set ownership to www-data (or current user)
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
        # Create document root
        if not create_directory(website.root_path):
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
        
        # Set permissions
        run_command(['chown', '-R', 'www-data:www-data', website.root_path], sudo=True)
        run_command(['chmod', '-R', '755', website.root_path], sudo=True)
        
        # Generate web server configuration
        if website.web_server == Website.WEB_SERVER_NGINX:
            config_result = create_nginx_config(website)
        else:
            config_result = create_apache_config(website)
        
        if not config_result['success']:
            return config_result
        
        # Enable site and reload web server
        enable_result = enable_website(website)
        if not enable_result['success']:
            return enable_result
        
        return {'success': True, 'message': f'PHP site {website.domain} created successfully'}
    except Exception as e:
        logger.error(f"Error creating PHP site: {e}")
        return {'success': False, 'error': str(e)}


def create_wordpress_site(website: Website) -> Dict[str, any]:
    """Create a WordPress website."""
    try:
        # Create document root
        if not create_directory(website.root_path):
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
        
        # Generate web server configuration
        if website.web_server == Website.WEB_SERVER_NGINX:
            config_result = create_nginx_config(website)
        else:
            config_result = create_apache_config(website)
        
        if not config_result['success']:
            return config_result
        
        # Enable site and reload web server
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

    location ~ \.php$ {{
        fastcgi_pass unix:/var/run/php/php{website.php_version.replace(".", "")}-fpm.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }}

    location ~ /\.ht {{
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
    """Create Apache virtual host configuration."""
    try:
        config_content = f"""<VirtualHost *:80>
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


def enable_website(website: Website) -> Dict[str, any]:
    """Enable website by creating symlink and reloading web server."""
    try:
        if website.web_server == Website.WEB_SERVER_NGINX:
            # Create symlink for Nginx
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
        else:
            # Enable Apache site
            exit_code, stdout, stderr = run_command([
                'a2ensite', f"{website.domain}.conf"
            ], sudo=True)
            
            if exit_code != 0:
                return {'success': False, 'error': f'Failed to enable Apache site: {stderr}'}
            
            exit_code, stdout, stderr = run_command(['systemctl', 'reload', 'apache2'], sudo=True)
            if exit_code != 0:
                return {'success': False, 'error': f'Failed to reload Apache: {stderr}'}
        
        return {'success': True}
    except Exception as e:
        logger.error(f"Error enabling website: {e}")
        return {'success': False, 'error': str(e)}


def disable_website(website: Website) -> Dict[str, any]:
    """Disable website by removing symlink and reloading web server."""
    try:
        if website.web_server == Website.WEB_SERVER_NGINX:
            target = os.path.join(settings.SKYDOCK_NGINX_SITES_ENABLED, website.domain)
            if os.path.exists(target):
                os.remove(target)
            
            exit_code, stdout, stderr = run_command(['systemctl', 'reload', 'nginx'], sudo=True)
            if exit_code != 0:
                return {'success': False, 'error': f'Failed to reload Nginx: {stderr}'}
        else:
            exit_code, stdout, stderr = run_command([
                'a2dissite', f"{website.domain}.conf"
            ], sudo=True)
            
            if exit_code != 0:
                return {'success': False, 'error': f'Failed to disable Apache site: {stderr}'}
            
            exit_code, stdout, stderr = run_command(['systemctl', 'reload', 'apache2'], sudo=True)
            if exit_code != 0:
                return {'success': False, 'error': f'Failed to reload Apache: {stderr}'}
        
        return {'success': True}
    except Exception as e:
        logger.error(f"Error disabling website: {e}")
        return {'success': False, 'error': str(e)}

