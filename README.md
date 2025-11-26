# SkyDock Panel

A modern, self-hosted VPS management panel that allows you to manage your server, services, and websites through a beautiful web interface.

![SkyDock Panel](https://img.shields.io/badge/SkyDock-Panel-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.11-blue)
![Django](https://img.shields.io/badge/django-5.0-green)

## Features

### 🖥️ Server Management
- **Real-time Monitoring**: View CPU, RAM, disk usage, and uptime
- **System Information**: Hostname, IP address, OS details, and hardware specs
- **Service Control**: Start, stop, and restart Nginx, Apache, and MySQL services
- **Service Logs**: View logs for all managed services

### 🌐 Website Management
- **PHP Applications**: Create and manage PHP websites with custom document roots
- **WordPress Sites**: One-click WordPress installation with automatic database setup
- **Web Server Support**: Choose between Nginx or Apache for each website
- **PHP Version Selection**: Support for multiple PHP versions (8.1, 8.2, 8.3)
- **Domain Management**: Easy domain configuration and virtual host management

### 🔐 Security
- **SSH-based Authentication**: Secure server access using SSH keys or passwords
- **Encrypted Credentials**: SSH passwords and keys are encrypted at rest
- **Session Management**: Secure Django session-based authentication

### 🎨 Modern UI
- **Stripe-like Design**: Clean, modern interface built with Tailwind CSS
- **Responsive Layout**: Mobile-friendly design that works on all devices
- **Dark Mode Support**: Built-in dark mode for comfortable viewing
- **Real-time Updates**: Live server metrics and status updates

## Tech Stack

- **Backend**: Django 5.0 (Python 3.11+)
- **Frontend**: Tailwind CSS, Alpine.js
- **Database**: SQLite (easily switchable to PostgreSQL)
- **Web Server**: Nginx (reverse proxy)
- **Application Server**: Gunicorn
- **System Management**: systemd

## Quick Start

### One-Line Installation

Install SkyDock Panel on a fresh Ubuntu server with a single command:

```bash
wget -O install.sh https://raw.githubusercontent.com/meetsohail/skydock-panel/main/scripts/install.sh && bash install.sh
```

### Manual Installation

1. **Clone the repository**:
```bash
git clone https://github.com/meetsohail/skydock-panel.git
cd skydock-panel
```

2. **Run the installer**:
```bash
sudo bash scripts/install.sh
```

3. **Access the panel**:
   - Open your browser and navigate to `http://your-server-ip`
   - Default admin credentials will be displayed after installation

## Requirements

- **OS**: Ubuntu 22.04 LTS or later
- **RAM**: Minimum 512MB (1GB+ recommended)
- **Disk**: Minimum 2GB free space
- **Python**: 3.11 or later
- **Root/Sudo Access**: Required for installation

## Installation Details

The installer script performs the following:

1. ✅ Updates system packages
2. ✅ Installs required dependencies (Python, Nginx, MySQL, etc.)
3. ✅ Creates dedicated `skydock` user
4. ✅ Clones the repository to `/opt/skydock-panel`
5. ✅ Sets up Python virtual environment
6. ✅ Configures Django application
7. ✅ Creates systemd service
8. ✅ Configures Nginx reverse proxy
9. ✅ Sets up firewall rules
10. ✅ Creates admin user with random password

## Usage

### Accessing the Panel

After installation, access the panel at:
- **URL**: `http://your-server-ip` or `http://your-domain.com`
- **Default Admin**: Email and password displayed during installation

### Creating a Website

1. Navigate to **Websites** in the sidebar
2. Click **Add Website**
3. Enter your domain name
4. Choose website type (PHP or WordPress)
5. Select web server (Nginx or Apache)
6. Choose PHP version
7. Click **Create**

For WordPress sites, the panel will:
- Create a MySQL database and user
- Download and install WordPress
- Configure `wp-config.php`
- Set up virtual host configuration
- Enable the site

### Managing Services

1. Navigate to **Services** in the sidebar
2. View status of Nginx, Apache, and MySQL
3. Use **Start**, **Stop**, or **Restart** buttons to control services

### Viewing Server Metrics

1. Navigate to **Dashboard**
2. View real-time metrics:
   - CPU usage
   - Memory usage
   - Disk usage
   - System uptime
   - Load average

### Configuring SSH Access

1. Navigate to **Settings**
2. Configure SSH profile:
   - SSH username (default: root)
   - Authentication type (Password or Private Key)
   - SSH password or private key
3. Click **Save SSH Profile**

## Project Structure

```
skydock-panel/
├── backend/                 # Django backend
│   ├── accounts/           # User authentication & SSH profiles
│   ├── servers/            # Server monitoring & service management
│   ├── websites/           # Website & WordPress management
│   ├── installer/         # Installation status endpoints
│   └── skydock_backend/   # Django project settings
├── frontend/              # Frontend templates
│   ├── templates/         # Django templates
│   └── static/            # Static files
├── scripts/               # Installation scripts
│   ├── install.sh        # Main installer
│   └── uninstall.sh      # Uninstaller
├── deploy/                # Deployment configs
│   ├── systemd/          # Systemd service files
│   └── nginx/            # Nginx configuration examples
└── .github/              # GitHub workflows
```

## Development

### Setting Up Development Environment

1. **Clone the repository**:
```bash
git clone https://github.com/meetsohail/skydock-panel.git
cd skydock-panel
```

2. **Set up Python virtual environment**:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. **Configure environment**:
```bash
cp env.example .env
# Edit .env with your settings
```

4. **Run migrations**:
```bash
python manage.py migrate
```

5. **Create superuser**:
```bash
python manage.py createsuperuser
```

6. **Run development server**:
```bash
python manage.py runserver
```

### Running Tests

```bash
cd backend
python manage.py test
```

## API Endpoints

### Authentication
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout
- `GET /api/auth/me/` - Get current user
- `GET/POST /api/auth/ssh-profile/` - Manage SSH profile

### Servers
- `GET /api/servers/metrics/` - Get server metrics
- `GET /api/servers/info/` - Get server information
- `GET /api/servers/services/` - List all services
- `POST /api/servers/services/control/` - Control a service
- `GET /api/servers/services/<service>/logs/` - Get service logs

### Websites
- `GET /api/websites/` - List all websites
- `POST /api/websites/` - Create a website
- `GET /api/websites/<id>/` - Get website details
- `PUT /api/websites/<id>/` - Update website
- `DELETE /api/websites/<id>/` - Delete website
- `POST /api/websites/<id>/toggle-status/` - Enable/disable website

## Configuration

### Environment Variables

Key environment variables (set in `.env` file):

- `DEBUG` - Django debug mode (default: False)
- `SECRET_KEY` - Django secret key
- `ALLOWED_HOSTS` - Allowed hostnames
- `SKYDOCK_PANEL_PORT` - Panel port (default: 8080)
- `SKYDOCK_WEB_ROOT` - Web root directory (default: /var/www)
- `SKYDOCK_ENCRYPTION_KEY` - Encryption key for SSH credentials

### Systemd Service

The panel runs as a systemd service. Manage it with:

```bash
# Check status
sudo systemctl status skydock-panel

# Start service
sudo systemctl start skydock-panel

# Stop service
sudo systemctl stop skydock-panel

# Restart service
sudo systemctl restart skydock-panel

# View logs
sudo journalctl -u skydock-panel -f
```

## Uninstallation

To remove SkyDock Panel:

```bash
sudo bash scripts/uninstall.sh
```

This will:
- Stop and disable the systemd service
- Remove Nginx configuration
- Remove installation directory
- Optionally remove the `skydock` user

## Security Considerations

1. **Change Default Credentials**: Immediately change the default admin password
2. **Use HTTPS**: Set up SSL/TLS certificates for production use
3. **Firewall**: Ensure only necessary ports are open
4. **SSH Keys**: Prefer SSH key authentication over passwords
5. **Regular Updates**: Keep the system and panel updated

## Troubleshooting

### Panel Not Accessible

1. Check if the service is running:
```bash
sudo systemctl status skydock-panel
```

2. Check Nginx status:
```bash
sudo systemctl status nginx
```

3. Check firewall:
```bash
sudo ufw status
```

4. View logs:
```bash
sudo journalctl -u skydock-panel -n 50
```

### Service Management Issues

- Ensure you have sudo privileges
- Check service status with `systemctl status <service>`
- View service logs with `journalctl -u <service>`

### Website Creation Fails

- Ensure web server (Nginx/Apache) is installed and running
- Check PHP-FPM is installed for the selected PHP version
- Verify MySQL is running for WordPress sites
- Check file permissions on `/var/www`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Write tests for new features
- Update documentation as needed
- Follow Django best practices

## Roadmap

- [ ] Multi-server management
- [ ] SSL certificate management (Let's Encrypt)
- [ ] Database management interface
- [ ] File manager
- [ ] Backup and restore functionality
- [ ] Email server management
- [ ] Docker container management
- [ ] Advanced monitoring and alerts

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/meetsohail/skydock-panel/issues)
- **Discussions**: [GitHub Discussions](https://github.com/meetsohail/skydock-panel/discussions)

## Acknowledgments

- Built with [Django](https://www.djangoproject.com/)
- Styled with [Tailwind CSS](https://tailwindcss.com/)
- Icons from [Heroicons](https://heroicons.com/)

## Screenshots

*Screenshots coming soon!*

---

**Made with ❤️ for the self-hosting community**

