"""
Server utilities for collecting system information and managing services.
"""
import psutil
import platform
import socket
import logging
from typing import Dict, Optional, List, Tuple
from .ssh_utils import run_command
from django.conf import settings

logger = logging.getLogger(__name__)


def get_system_info() -> Dict:
    """Collect system information."""
    try:
        # Get CPU info
        cpu_count = psutil.cpu_count()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get memory info
        memory = psutil.virtual_memory()
        total_ram = memory.total
        available_ram = memory.available
        used_ram = memory.used
        ram_percent = memory.percent
        
        # Get disk info
        disk = psutil.disk_usage('/')
        total_disk = disk.total
        used_disk = disk.used
        free_disk = disk.free
        disk_percent = disk.percent
        
        # Get uptime
        import time
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        
        # Get load average (Unix only)
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
        
        # Get OS info
        os_name = platform.system()
        os_version = platform.release()
        hostname = socket.gethostname()
        
        # Get IP address
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip_address = s.getsockname()[0]
            s.close()
        except Exception:
            ip_address = '127.0.0.1'
        
        return {
            'hostname': hostname,
            'ip_address': ip_address,
            'os_name': os_name,
            'os_version': os_version,
            'cpu': {
                'count': cpu_count,
                'percent': cpu_percent,
                'load_average': {
                    '1min': load_avg[0],
                    '5min': load_avg[1],
                    '15min': load_avg[2],
                }
            },
            'memory': {
                'total': total_ram,
                'used': used_ram,
                'available': available_ram,
                'percent': ram_percent,
            },
            'disk': {
                'total': total_disk,
                'used': used_disk,
                'free': free_disk,
                'percent': disk_percent,
            },
            'uptime': {
                'seconds': uptime_seconds,
                'days': int(uptime_seconds / 86400),
                'hours': int((uptime_seconds % 86400) / 3600),
                'minutes': int((uptime_seconds % 3600) / 60),
            }
        }
    except Exception as e:
        logger.error(f"Error collecting system info: {e}")
        raise


def check_service_status(service_name: str) -> Dict[str, any]:
    """
    Check if a service is installed and running.
    
    Args:
        service_name: Name of the service (e.g., 'nginx', 'apache2', 'mysql')
        
    Returns:
        Dict with 'installed', 'running', and 'status' keys
    """
    try:
        # Check if service exists
        exit_code, stdout, stderr = run_command(['which', service_name], sudo=False)
        installed = exit_code == 0
        
        if not installed:
            return {
                'installed': False,
                'running': False,
                'status': 'not_installed'
            }
        
        # Check service status using systemctl
        exit_code, stdout, stderr = run_command(
            ['systemctl', 'is-active', service_name],
            sudo=False
        )
        
        is_active = exit_code == 0
        
        # Get detailed status
        exit_code, stdout, stderr = run_command(
            ['systemctl', 'status', service_name, '--no-pager'],
            sudo=False
        )
        
        status_text = stdout if exit_code == 0 else stderr
        
        return {
            'installed': True,
            'running': is_active,
            'status': 'running' if is_active else 'stopped',
            'status_text': status_text
        }
    except Exception as e:
        logger.error(f"Error checking service status for {service_name}: {e}")
        return {
            'installed': False,
            'running': False,
            'status': 'error',
            'error': str(e)
        }


def manage_service(service_name: str, action: str) -> Dict[str, any]:
    """
    Manage a service (start, stop, restart).
    
    Args:
        service_name: Name of the service
        action: Action to perform ('start', 'stop', 'restart', 'reload')
        
    Returns:
        Dict with 'success', 'message', and 'status' keys
    """
    valid_actions = ['start', 'stop', 'restart', 'reload']
    if action not in valid_actions:
        return {
            'success': False,
            'message': f'Invalid action. Must be one of: {", ".join(valid_actions)}'
        }
    
    try:
        exit_code, stdout, stderr = run_command(
            ['systemctl', action, service_name],
            sudo=True
        )
        
        if exit_code == 0:
            # Check new status
            status_info = check_service_status(service_name)
            return {
                'success': True,
                'message': f'Service {service_name} {action}ed successfully',
                'status': status_info
            }
        else:
            return {
                'success': False,
                'message': f'Failed to {action} service: {stderr}',
                'error': stderr
            }
    except Exception as e:
        logger.error(f"Error managing service {service_name}: {e}")
        return {
            'success': False,
            'message': f'Error managing service: {str(e)}',
            'error': str(e)
        }


def get_service_logs(service_name: str, lines: int = 50) -> str:
    """
    Get last N lines of service logs.
    
    Args:
        service_name: Name of the service
        lines: Number of lines to retrieve
        
    Returns:
        Log output as string
    """
    try:
        exit_code, stdout, stderr = run_command(
            ['journalctl', '-u', service_name, '-n', str(lines), '--no-pager'],
            sudo=False
        )
        
        if exit_code == 0:
            return stdout
        else:
            return stderr
    except Exception as e:
        logger.error(f"Error getting logs for {service_name}: {e}")
        return f"Error retrieving logs: {str(e)}"

