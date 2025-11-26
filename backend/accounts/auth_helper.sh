#!/bin/bash
# Helper script to verify system user password
# Usage: auth_helper.sh username password
# Returns 0 if password is correct, 1 otherwise

USERNAME="$1"
PASSWORD="$2"

if [ -z "$USERNAME" ] || [ -z "$PASSWORD" ]; then
    exit 1
fi

# Use expect to verify password with su
expect << EOF
set timeout 5
spawn su -c "exit 0" "$USERNAME"
expect {
    "Password:" {
        send "$PASSWORD\r"
        expect {
            eof {
                set exit_code [wait]
                exit [lindex \$exit_code 3]
            }
            timeout {
                exit 1
            }
        }
    }
    "password:" {
        send "$PASSWORD\r"
        expect {
            eof {
                set exit_code [wait]
                exit [lindex \$exit_code 3]
            }
            timeout {
                exit 1
            }
        }
    }
    eof {
        exit 1
    }
    timeout {
        exit 1
    }
}
EOF

