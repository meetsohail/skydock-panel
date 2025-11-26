#!/usr/bin/env python3
"""
Helper script to verify system user password.
This script runs as a separate process to avoid TTY issues.
"""
import sys
import pexpect
import os

if len(sys.argv) != 3:
    sys.exit(1)

username = sys.argv[1]
password = sys.argv[2]

try:
    # Set environment
    env = os.environ.copy()
    env['LANG'] = 'C'
    env['LC_ALL'] = 'C'
    
    # Use su to verify password
    child = pexpect.spawn(
        'su',
        ['-c', 'exit 0', username],
        timeout=15,
        encoding='utf-8',
        echo=False,
        env=env
    )
    
    # Wait for password prompt
    patterns = [
        'Password:',
        'password:',
        'Password for',
        'password for',
        pexpect.EOF,
        pexpect.TIMEOUT
    ]
    
    index = child.expect(patterns, timeout=15)
    
    # If we got EOF or TIMEOUT before prompt, fail
    if index >= len(patterns) - 2:
        child.close(force=True)
        sys.exit(1)
    
    # Send password
    child.sendline(password)
    
    # Wait for command to complete
    child.expect(pexpect.EOF, timeout=15)
    
    # Get exit status
    exit_status = child.exitstatus
    child.close()
    
    # Exit with su's exit status
    sys.exit(exit_status)
    
except Exception as e:
    sys.exit(1)

