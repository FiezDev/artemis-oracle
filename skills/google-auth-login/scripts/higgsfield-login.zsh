#!/bin/zsh
# Higgsfield.ai Login Helper
# Sources credentials and runs the Python login script

export HIGGSFIELD_EMAIL="ittipolbiz@gmail.com"
export HIGGSFIELD_PASSWORD='=-^w&ZTn(&(C==F@'
export HIGGSFIELD_TOTP_SECRET="fvdsbwm5eeixo5qrffb6q5bwmkwos7yp"

SCRIPT_DIR="${0:A:h}"
VENV_PYTHON="${SCRIPT_DIR}/../.venv/bin/python3"

if [[ ! -f "$VENV_PYTHON" ]]; then
    echo "ERROR: venv not found. Run: python3 -m venv .venv && .venv/bin/pip install pyotp playwright"
    exit 1
fi

"$VENV_PYTHON" "${SCRIPT_DIR}/higgsfield-login.py" "$@"
