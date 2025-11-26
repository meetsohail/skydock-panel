# SkyDock Panel Backend

Django backend for SkyDock Panel - A self-hosted VPS management panel.

## Features

- **Accounts Management**: User authentication with SSH profile support
- **Server Monitoring**: Real-time server metrics (CPU, RAM, disk, uptime)
- **Service Management**: Start/stop/restart Nginx, Apache, MySQL
- **Website Management**: Create and manage PHP and WordPress sites
- **Database Management**: Automatic MySQL database creation for WordPress

## Installation

See the main [README.md](../README.md) for installation instructions.

## Development Setup

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy environment file:
```bash
cp env.example .env
# Edit .env with your settings
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Create superuser:
```bash
python manage.py createsuperuser
```

6. Run development server:
```bash
python manage.py runserver
```

## Project Structure

```
backend/
├── accounts/          # User authentication and SSH profiles
├── servers/           # Server monitoring and service management
├── websites/          # Website and WordPress management
├── installer/         # Installation status endpoints
└── skydock_backend/   # Django project settings
```

## API Endpoints

- `/api/auth/` - Authentication endpoints
- `/api/servers/` - Server metrics and service management
- `/api/websites/` - Website management
- `/api/installer/` - Installation status

## Testing

Run tests with:
```bash
python manage.py test
```

## License

MIT License - see LICENSE file for details.

