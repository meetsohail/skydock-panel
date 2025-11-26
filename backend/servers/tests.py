"""
Tests for servers app.
"""
from django.test import TestCase
from unittest.mock import patch, MagicMock
from .models import Server
from .utils import get_system_info, check_service_status, manage_service


class ServerModelTest(TestCase):
    """Test Server model."""
    
    def test_create_server(self):
        """Test server creation."""
        server = Server.objects.create(
            hostname='test-server',
            ip_address='192.168.1.1',
            os_name='Ubuntu',
            os_version='22.04',
            total_ram=8589934592,  # 8GB
            total_disk=107374182400,  # 100GB
            cpu_count=4,
            is_local=True
        )
        self.assertEqual(server.hostname, 'test-server')
        self.assertTrue(server.is_local)


class ServerUtilsTest(TestCase):
    """Test server utilities."""
    
    @patch('servers.utils.psutil')
    @patch('servers.utils.platform')
    @patch('servers.utils.socket')
    def test_get_system_info(self, mock_socket, mock_platform, mock_psutil):
        """Test system info collection."""
        # Mock psutil
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 25.5
        mock_psutil.virtual_memory.return_value = MagicMock(
            total=8589934592,
            available=4294967296,
            used=4294967296,
            percent=50.0
        )
        mock_psutil.disk_usage.return_value = MagicMock(
            total=107374182400,
            used=53687091200,
            free=53687091200,
            percent=50.0
        )
        mock_psutil.boot_time.return_value = 1000000
        mock_psutil.getloadavg.return_value = (1.0, 0.5, 0.3)
        
        # Mock platform
        mock_platform.system.return_value = 'Linux'
        mock_platform.release.return_value = '5.15.0'
        
        # Mock socket
        mock_platform.socket.return_value = MagicMock()
        mock_socket.gethostname.return_value = 'test-host'
        
        import time
        with patch('servers.utils.time.time', return_value=2000000):
            info = get_system_info()
        
        self.assertEqual(info['cpu']['count'], 4)
        self.assertEqual(info['os_name'], 'Linux')
    
    @patch('servers.utils.run_command')
    def test_check_service_status(self, mock_run_command):
        """Test service status check."""
        # Mock installed and running
        mock_run_command.side_effect = [
            (0, '/usr/sbin/nginx', ''),  # which command
            (0, 'active', ''),  # systemctl is-active
            (0, 'Status output', '')  # systemctl status
        ]
        
        status = check_service_status('nginx')
        self.assertTrue(status['installed'])
        self.assertTrue(status['running'])
    
    @patch('servers.utils.run_command')
    @patch('servers.utils.check_service_status')
    def test_manage_service(self, mock_check_status, mock_run_command):
        """Test service management."""
        mock_run_command.return_value = (0, 'Success', '')
        mock_check_status.return_value = {
            'installed': True,
            'running': True,
            'status': 'running'
        }
        
        result = manage_service('nginx', 'restart')
        self.assertTrue(result['success'])

