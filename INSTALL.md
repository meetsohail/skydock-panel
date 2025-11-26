# Installation Guide

## Quick Installation

Install SkyDock Panel with a single command:

```bash
wget -O install.sh https://raw.githubusercontent.com/meetsohail/skydock-panel/master/scripts/install.sh && bash install.sh
```

## Manual Installation (Current Method)

Since the repository may not be published yet, follow these steps:

### Step 1: Upload Project Files

Upload the entire `skydock-panel` directory to your server. You can use:

**Option A: Using SCP (from your local machine)**
```bash
scp -r skydock-panel root@your-server-ip:/opt/
```

**Option B: Using Git (if you have a private repo)**
```bash
git clone https://github.com/meetsohail/skydock-panel.git /opt/skydock-panel
```

**Option C: Using tar/zip**
```bash
# On your local machine
tar -czf skydock-panel.tar.gz skydock-panel/
scp skydock-panel.tar.gz root@your-server-ip:/opt/

# On the server
cd /opt
tar -xzf skydock-panel.tar.gz
```

### Step 2: Run the Installer

```bash
cd /opt/skydock-panel
sudo bash scripts/install.sh
```

The installer will:
- Install all system dependencies
- Set up Python virtual environment
- Configure Django
- Create systemd service
- Set up Nginx
- Create admin user

### Step 3: Access the Panel

After installation completes, you'll see:
- Panel URL: `http://your-server-ip`
- Admin email: `admin@skydock.local`
- Admin password: (displayed in installation output)

## Troubleshooting

### 404 Error on wget

If you get a 404 error, it means:
1. The repository hasn't been published to GitHub yet, OR
2. The repository URL is incorrect

**Solution**: Use manual installation method above.

### Installation Fails

Check the logs:
```bash
# View installation output
# (re-run with verbose output)
bash -x scripts/install.sh

# Check systemd service status
systemctl status skydock-panel

# View service logs
journalctl -u skydock-panel -f
```

### Permission Errors

Ensure you're running as root:
```bash
sudo bash scripts/install.sh
```

### Python/Django Errors

Check Python version:
```bash
python3 --version  # Should be 3.11+
```

Reinstall dependencies:
```bash
cd /opt/skydock-panel/backend
source venv/bin/activate
pip install -r requirements.txt
```

## Post-Installation

### Change Admin Password

1. Log in to the panel
2. Go to Settings
3. Or use Django admin:
```bash
cd /opt/skydock-panel/backend
source venv/bin/activate
python manage.py changepassword admin@skydock.local
```

### Configure Domain

1. Point your domain to the server IP
2. Update Nginx configuration:
```bash
sudo nano /etc/nginx/sites-available/skydock-panel
# Change server_name from _ to your-domain.com
sudo nginx -t
sudo systemctl reload nginx
```

### Set Up SSL (HTTPS)

Install Certbot:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Uninstallation

To remove SkyDock Panel:

```bash
sudo bash /opt/skydock-panel/scripts/uninstall.sh
```

