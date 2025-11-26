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


def create_directory(path: str, owner_user: Optional[str] = None) -> Dict[str, any]:
    """Create directory with proper permissions.
    
    Args:
        path: Directory path to create
        owner_user: Username to set as owner (defaults to www-data for web server access)
    
    Returns:
        Dict with 'success' bool and optional 'error' message
    """
    try:
        # Ensure web root exists first
        web_root = settings.SKYDOCK_WEB_ROOT
        if not os.path.exists(web_root):
            logger.info(f"Creating web root directory: {web_root}")
            exit_code, stdout, stderr = run_command(['mkdir', '-p', web_root], sudo=True)
            if exit_code != 0:
                error_msg = f"Failed to create web root {web_root}: {stderr}"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            # Set web root permissions
            run_command(['chown', '-R', 'www-data:www-data', web_root], sudo=True)
            run_command(['chmod', '755', web_root], sudo=True)
        
        # Create parent directories if they don't exist
        parent_dir = os.path.dirname(path)
        if parent_dir and parent_dir != path and not os.path.exists(parent_dir):
            logger.info(f"Creating parent directory: {parent_dir}")
            # Try to create parent directory with sudo
            exit_code, stdout, stderr = run_command(['mkdir', '-p', parent_dir], sudo=True)
            if exit_code != 0:
                error_msg = f"Failed to create parent directory {parent_dir}: {stderr}"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            # Set parent directory ownership (we'll verify user exists later)
            run_command(['chmod', '755', parent_dir], sudo=True)
        
        # Create the directory itself with sudo
        if not os.path.exists(path):
            logger.info(f"Creating directory: {path}")
            exit_code, stdout, stderr = run_command(['mkdir', '-p', path], sudo=True)
            if exit_code != 0:
                error_msg = f"Failed to create directory {path}: {stderr}"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
        else:
            logger.info(f"Directory already exists: {path}")
        
        # Verify owner_user exists if provided
        if owner_user:
            exit_code, stdout, stderr = run_command(['id', owner_user], sudo=False)
            if exit_code != 0:
                logger.warning(f"User {owner_user} does not exist, using www-data instead")
                # Try to set parent directory ownership to www-data
                if parent_dir and parent_dir != path:
                    run_command(['chown', '-R', 'www-data:www-data', parent_dir], sudo=True)
                owner_user = None
            else:
                # User exists, set parent directory ownership
                if parent_dir and parent_dir != path:
                    run_command(['chown', '-R', f'{owner_user}:www-data', parent_dir], sudo=True)
        
        # Set ownership - prefer owner_user if provided, otherwise use www-data
        if owner_user:
            # Set owner to the user, group to www-data for web server access
            exit_code, stdout, stderr = run_command(['chown', '-R', f'{owner_user}:www-data', path], sudo=True)
            if exit_code != 0:
                logger.warning(f"Failed to chown to {owner_user}:www-data: {stderr}, trying {owner_user}:{owner_user}")
                # Fallback to user:user if www-data group doesn't exist
                exit_code, stdout, stderr = run_command(['chown', '-R', f'{owner_user}:{owner_user}', path], sudo=True)
                if exit_code != 0:
                    logger.warning(f"Failed to chown directory {path} to {owner_user}: {stderr}, using www-data")
                    # Final fallback to www-data
                    run_command(['chown', '-R', 'www-data:www-data', path], sudo=True)
        else:
            # Default: www-data ownership for web server
            exit_code, stdout, stderr = run_command(['chown', '-R', 'www-data:www-data', path], sudo=True)
            if exit_code != 0:
                logger.warning(f"Failed to chown to www-data:www-data: {stderr}")
                # Try with current user if www-data doesn't exist
                import getpass
                current_user = getpass.getuser()
                exit_code, stdout, stderr = run_command(['chown', '-R', f'{current_user}:{current_user}', path], sudo=True)
                if exit_code != 0:
                    logger.warning(f"Failed to chown directory {path}: {stderr}, but continuing")
        
        # Set permissions
        exit_code, stdout, stderr = run_command(['chmod', '-R', '755', path], sudo=True)
        if exit_code != 0:
            logger.warning(f"Failed to chmod directory {path}: {stderr}, but continuing")
            # Don't fail on chmod errors, as ownership might be sufficient
        
        logger.info(f"Successfully created and configured directory: {path}")
        return {'success': True}
    except PermissionError as e:
        error_msg = f"Permission denied creating directory {path}: {e}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}
    except OSError as e:
        error_msg = f"OS error creating directory {path}: {e}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}
    except Exception as e:
        error_msg = f"Error creating directory {path}: {e}"
        logger.error(error_msg, exc_info=True)
        return {'success': False, 'error': error_msg}


def create_php_site(website: Website) -> Dict[str, any]:
    """Create a PHP website."""
    try:
        # Create document root with website owner as owner
        owner_username = website.user.username if website.user else None
        dir_result = create_directory(website.root_path, owner_user=owner_username)
        if not dir_result['success']:
            return {'success': False, 'error': dir_result.get('error', 'Failed to create document root')}
        
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
        dir_result = create_directory(website.root_path, owner_user=owner_username)
        if not dir_result['success']:
            error_msg = dir_result.get('error', 'Failed to create document root')
            logger.error(f"Failed to create document root for WordPress site: {error_msg}")
            return {'success': False, 'error': error_msg}
        
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
    """Create MySQL database and user (compatible with MySQL 5.7+ and 8.0+)."""
    try:
        import shlex
        
        # Create database
        exit_code, stdout, stderr = run_command([
            'mysql', '-e', f'CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;'
        ], sudo=True)
        
        if exit_code != 0:
            return {'success': False, 'error': f'Failed to create database: {stderr}'}
        
        # Check if user exists, drop if exists (for idempotency)
        exit_code, stdout, stderr = run_command([
            'mysql', '-e', f"DROP USER IF EXISTS '{db_user}'@'localhost';"
        ], sudo=True)
        # Ignore errors for DROP USER IF EXISTS
        
        # Create user (MySQL 8.0+ compatible syntax)
        create_user_sql = f"CREATE USER IF NOT EXISTS '{db_user}'@'localhost' IDENTIFIED BY '{db_password}';"
        exit_code, stdout, stderr = run_command([
            'mysql', '-e', create_user_sql
        ], sudo=True)
        
        if exit_code != 0:
            # Try older syntax for MySQL 5.7
            create_user_sql_old = f"CREATE USER '{db_user}'@'localhost' IDENTIFIED BY '{db_password}';"
            exit_code, stdout, stderr = run_command([
                'mysql', '-e', create_user_sql_old
            ], sudo=True)
            if exit_code != 0:
                return {'success': False, 'error': f'Failed to create database user: {stderr}'}
        
        # Grant privileges
        grant_sql = f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'localhost';"
        exit_code, stdout, stderr = run_command([
            'mysql', '-e', grant_sql
        ], sudo=True)
        
        if exit_code != 0:
            return {'success': False, 'error': f'Failed to grant privileges: {stderr}'}
        
        # Flush privileges
        exit_code, stdout, stderr = run_command([
            'mysql', '-e', 'FLUSH PRIVILEGES;'
        ], sudo=True)
        
        if exit_code != 0:
            logger.warning(f"Failed to flush privileges: {stderr}, but continuing")
        
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
        # Write to temporary file first, then copy with sudo to avoid permission issues
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.php') as tmp_file:
            tmp_file.write(wp_config_content)
            tmp_file_path = tmp_file.name
        
        try:
            # Copy temp file to destination with sudo
            exit_code, stdout, stderr = run_command([
                'cp', tmp_file_path, wp_config_path
            ], sudo=True)
            
            if exit_code != 0:
                return {'success': False, 'error': f'Failed to create wp-config.php: {stderr}'}
            
            # Set proper permissions and ownership
            owner_username = website.user.username if website.user else 'www-data'
            run_command(['chown', f'{owner_username}:www-data', wp_config_path], sudo=True)
            run_command(['chmod', '644', wp_config_path], sudo=True)
            
            return {'success': True}
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_file_path)
            except:
                pass
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

