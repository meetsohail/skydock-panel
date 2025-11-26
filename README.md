# SkyDock Panel

A modern, open-source VPS management panel for managing servers, services, and websites through a web interface.

## Features

- **Server Management**: Monitor CPU, RAM, disk usage, and manage services (Nginx, Apache, MySQL, Redis)
- **Website Management**: Create PHP applications and WordPress sites with automatic database setup
- **Service Control**: Start, stop, and restart services from the web interface
- **Modern UI**: Clean, responsive design with dark mode support

## Installation

### Quick Install (One Command)

```bash
wget -O install.sh https://raw.githubusercontent.com/meetsohail/skydock-panel/master/scripts/install.sh && bash install.sh
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
   - Open `http://your-server-ip:2083` in your browser
   - Login with your system username and password

## Requirements

- Ubuntu 22.04 LTS or later
- Root/sudo access
- Minimum 512MB RAM, 2GB disk space

## What It Does

Once installed, SkyDock Panel:

- Runs on port **2083** (accessible via `http://your-server-ip:2083`)
- Uses **system user authentication** (login with your server username/password)
- Manages websites with **Apache** (port 8080) behind **Nginx** reverse proxy (ports 80/443)
- Automatically installs: Nginx, Apache, MySQL/MariaDB, PHP 8.1/8.2/8.3, Redis, phpMyAdmin
- Creates websites in `/var/www/username/domain/`
- Each user can manage their own websites independently

## Usage

### Creating a Website

1. Go to **Websites** → **Add Website**
2. Enter domain name
3. Choose type: PHP or WordPress
4. For WordPress: Enter admin email, username, and password
5. Click **Create**

The panel automatically:
- Creates document root directory
- Sets up Apache virtual host (port 8080)
- Configures Nginx reverse proxy (ports 80/443)
- For WordPress: Creates database and installs WordPress

### Managing Services

Go to **Services** to start, stop, or restart:
- Nginx
- Apache
- MySQL
- Redis

## Development

```bash
# Clone repository
git clone https://github.com/meetsohail/skydock-panel.git
cd skydock-panel

# Setup backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp env.example .env
# Edit .env with your settings

# Run migrations
python manage.py migrate

# Run server
python manage.py runserver
```

## Contributing

Contributions are welcome! Here's how:

1. **Fork the repository**
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** and commit:
   ```bash
   git commit -m 'Add your feature'
   ```
4. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
5. **Open a Pull Request** on GitHub

### Guidelines

- Follow PEP 8 for Python code
- Write tests for new features
- Update documentation as needed
- Keep commits focused and descriptive

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/meetsohail/skydock-panel/issues)
- **Pull Requests**: [GitHub Pull Requests](https://github.com/meetsohail/skydock-panel/pulls)
