#!/usr/bin/env python3
"""
Helper script to verify system user password.
This script runs as a separate process to avoid TTY issues.
Uses multiple methods to verify password.
"""
import sys
import pexpect
import os
import warnings

# Suppress deprecation warnings for crypt/spwd (they still work)
warnings.filterwarnings('ignore', category=DeprecationWarning)

try:
    import crypt
    import spwd
except ImportError:
    crypt = None
    spwd = None

if len(sys.argv) != 3:
    sys.stderr.write("Usage: verify_password.py <username> <password>\n")
    sys.exit(1)

username = sys.argv[1]
password = sys.argv[2]

# Method 1: Try using crypt with /etc/shadow (requires root or proper permissions)
if crypt and spwd:
    try:
        shadow_entry = spwd.getspnam(username)
        hashed = shadow_entry.sp_pwd
        
        # Skip locked accounts
        if hashed in ['!', '*', 'x']:
            sys.stderr.write("Account is locked\n")
            sys.exit(1)
        
        # Verify using crypt
        if crypt.crypt(password, hashed) == hashed:
            sys.exit(0)
        else:
            sys.stderr.write("Password does not match (crypt method)\n")
    except (KeyError, PermissionError):
        # User not in shadow or no permission - fall back to su method
        sys.stderr.write("Cannot access shadow file, using su method\n")
        pass
    except Exception as e:
        sys.stderr.write(f"Crypt method error: {str(e)}\n")
        pass

# Method 2: Use su with pexpect (fallback)
try:
    # Set environment
    env = os.environ.copy()
    env['LANG'] = 'C'
    env['LC_ALL'] = 'C'
    
    # Use su to verify password - use full path
    # Try common locations for su
    su_paths = ['/bin/su', '/usr/bin/su', 'su']
    su_path = None
    
    for path in su_paths:
        if os.path.exists(path) or path == 'su':
            su_path = path
            break
    
    if not su_path:
        sys.stderr.write("su command not found\n")
        sys.exit(1)
    
    # Try different su command formats
    su_commands = [
        [su_path, '-c', 'true', username],  # Standard format: su -c 'command' username
        [su_path, username, '-c', 'true'],   # Alternative format
    ]
    
    for su_cmd in su_commands:
        try:
            child = pexpect.spawn(
                su_cmd[0],
                su_cmd[1:],
                timeout=10,
                encoding='utf-8',
                echo=False,
                env=env
            )
            
            # Wait for password prompt - try multiple patterns
            patterns = [
                'Password:',
                'password:',
                'Password for',
                'password for',
                'su:',
                pexpect.EOF,
                pexpect.TIMEOUT
            ]
            
            try:
                index = child.expect(patterns, timeout=10)
                
                # If we got EOF or TIMEOUT before prompt, try next command format
                if index >= len(patterns) - 2:
                    sys.stderr.write(f"No password prompt found (index: {index}), trying next format\n")
                    child.close(force=True)
                    continue
                
                # Send password
                child.sendline(password)
                
                # Wait for command to complete
                child.expect(pexpect.EOF, timeout=10)
                
                # Get exit status - handle None (which means success in some cases)
                exit_status = child.exitstatus
                child.close()
                
                # Exit with su's exit status (0 = success, None = success, non-zero = failure)
                if exit_status == 0 or exit_status is None:
                    sys.exit(0)
                else:
                    sys.stderr.write(f"su command failed with exit status: {exit_status}\n")
                    # Try next command format
                    continue
                    
            except pexpect.TIMEOUT:
                sys.stderr.write("Timeout waiting for password prompt, trying next format\n")
                child.close(force=True)
                continue
            except pexpect.EOF:
                # Sometimes EOF happens but exit status is still valid
                try:
                    exit_status = child.exitstatus
                    child.close()
                    if exit_status == 0 or exit_status is None:
                        sys.exit(0)
                    else:
                        sys.stderr.write(f"Unexpected EOF, exit status: {exit_status}, trying next format\n")
                        continue
                except:
                    continue
                    
        except Exception as e:
            sys.stderr.write(f"Error with su command format: {str(e)}, trying next format\n")
            continue
    
    # All methods failed
    sys.stderr.write("All su command formats failed\n")
    sys.exit(1)
        
except Exception as e:
    sys.stderr.write(f"Error spawning su command: {str(e)}\n")
    sys.exit(1)
