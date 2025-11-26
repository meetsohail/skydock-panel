"""
SSH and command execution utilities for SkyDock Panel.
"""
import subprocess
import logging
from typing import Tuple, Optional, List
import paramiko
from django.conf import settings
from accounts.models import SSHProfile

logger = logging.getLogger(__name__)


class CommandExecutor:
    """Abstract command executor that can use local subprocess or SSH."""
    
    def __init__(self, use_ssh: bool = False, ssh_profile: Optional[SSHProfile] = None):
        """
        Initialize command executor.
        
        Args:
            use_ssh: Whether to use SSH for command execution
            ssh_profile: SSH profile to use for authentication
        """
        self.use_ssh = use_ssh
        self.ssh_profile = ssh_profile
        self.ssh_client: Optional[paramiko.SSHClient] = None
        
        if use_ssh and ssh_profile:
            self._connect_ssh()
    
    def _connect_ssh(self) -> None:
        """Establish SSH connection."""
        if not self.ssh_profile:
            raise ValueError("SSH profile is required for SSH connection")
        
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.ssh_profile.auth_type == SSHProfile.AUTH_TYPE_KEY:
                # Use private key authentication
                private_key = self.ssh_profile.get_private_key()
                if not private_key:
                    raise ValueError("Private key not found in SSH profile")
                
                # Try to load the key
                try:
                    key = paramiko.RSAKey.from_private_key_file(private_key)
                except:
                    # Try loading from string
                    import io
                    key = paramiko.RSAKey.from_private_key(io.StringIO(private_key))
                
                self.ssh_client.connect(
                    hostname='localhost',
                    username=self.ssh_profile.ssh_username,
                    pkey=key,
                    timeout=10
                )
            else:
                # Use password authentication
                password = self.ssh_profile.get_password()
                self.ssh_client.connect(
                    hostname='localhost',
                    username=self.ssh_profile.ssh_username,
                    password=password,
                    timeout=10
                )
            
            logger.info(f"SSH connection established for user {self.ssh_profile.ssh_username}")
        except Exception as e:
            logger.error(f"Failed to establish SSH connection: {e}")
            raise
    
    def run_command(self, cmd: List[str], sudo: bool = False) -> Tuple[int, str, str]:
        """
        Run a command and return exit code, stdout, and stderr.
        
        Args:
            cmd: Command as list of strings
            sudo: Whether to run with sudo
            
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if sudo:
            cmd = ['sudo'] + cmd
        
        if self.use_ssh and self.ssh_client:
            return self._run_ssh_command(cmd)
        else:
            return self._run_local_command(cmd)
    
    def _run_local_command(self, cmd: List[str]) -> Tuple[int, str, str]:
        """Run command locally using subprocess."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {' '.join(cmd)}")
            return 1, '', 'Command execution timeout'
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return 1, '', str(e)
    
    def _run_ssh_command(self, cmd: List[str]) -> Tuple[int, str, str]:
        """Run command via SSH."""
        if not self.ssh_client:
            raise ValueError("SSH client not connected")
        
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(' '.join(cmd))
            exit_code = stdout.channel.recv_exit_status()
            stdout_text = stdout.read().decode('utf-8')
            stderr_text = stderr.read().decode('utf-8')
            return exit_code, stdout_text, stderr_text
        except Exception as e:
            logger.error(f"SSH command execution error: {e}")
            return 1, '', str(e)
    
    def close(self) -> None:
        """Close SSH connection if open."""
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def run_command(cmd: List[str], sudo: bool = False, use_ssh: bool = False, 
                ssh_profile: Optional[SSHProfile] = None) -> Tuple[int, str, str]:
    """
    Convenience function to run a command.
    
    Args:
        cmd: Command as list of strings
        sudo: Whether to run with sudo
        use_ssh: Whether to use SSH
        ssh_profile: SSH profile for SSH execution
        
    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    with CommandExecutor(use_ssh=use_ssh, ssh_profile=ssh_profile) as executor:
        return executor.run_command(cmd, sudo=sudo)

