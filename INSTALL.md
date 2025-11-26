# Installation Guide

## Quick Install

```bash
wget -O install.sh https://raw.githubusercontent.com/meetsohail/skydock-panel/master/scripts/install.sh && bash install.sh
```

## Manual Installation

1. **Clone or upload the project**:
```bash
git clone https://github.com/meetsohail/skydock-panel.git /opt/skydock-panel
# OR upload via SCP/SFTP to /opt/skydock-panel
```

2. **Run installer**:
```bash
cd /opt/skydock-panel
sudo bash scripts/install.sh
```

3. **Access panel**:
   - URL: `http://your-server-ip:2083`
   - Login with your system username and password

## What Gets Installed

- Nginx (reverse proxy on ports 80/443)
- Apache (backend on port 8080)
- MySQL/MariaDB
- PHP 8.1, 8.2, 8.3 with PHP-FPM
- Redis
- phpMyAdmin
- Python 3.11+ and dependencies
- SkyDock Panel service (port 2083)

## Post-Installation

### Access the Panel

- Open `http://your-server-ip:2083`
- Login with any system user account (username/password)

### Create Your First Website

1. Go to **Websites** → **Add Website**
2. Enter domain name
3. Choose PHP or WordPress
4. Click **Create**

### Service Management

- Go to **Services** to manage Nginx, Apache, MySQL, Redis
- Start, stop, or restart services from the web interface

## Troubleshooting

### Panel Not Accessible

```bash
# Check service status
sudo systemctl status skydock-panel

# View logs
sudo journalctl -u skydock-panel -f
```

### Installation Issues

```bash
# Re-run installer with verbose output
bash -x scripts/install.sh

# Check Python version (needs 3.11+)
python3 --version
```

## Uninstall

```bash
sudo bash /opt/skydock-panel/scripts/uninstall.sh
```
