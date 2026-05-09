#!/usr/bin/env python3
"""
Encrypted Credential Vault for auto-login scripts.

Vault file: .auth.vault (encrypted, safe-ish to commit but gitignored anyway)
Master password: provided via MASTER_PASSWORD env var or interactive prompt

Usage:
    # Setup — add credentials to vault (creates or updates)
    python3 scripts/auth-vault.py set higgsfield
    python3 scripts/auth-vault.py set google

    # Read — decrypt and print (for scripting)
    python3 scripts/auth-vault.py get higgsfield email
    python3 scripts/auth-vault.py get google password

    # List services
    python3 scripts/auth-vault.py list

    # Delete a service
    python3 scripts/auth-vault.py delete higgsfield
"""

import os
import sys
import json
import getpass
import base64
import hashlib

VAULT_PATH = os.path.join(os.path.dirname(__file__), '..', '.auth.vault')

# Use cryptography.fernet for symmetric encryption
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def _derive_key(master_password: str, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key from master password using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,  # OWASP recommended minimum
    )
    key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
    return key


def _get_master_password(confirm: bool = False) -> str:
    """Get master password from env or prompt."""
    pw = os.environ.get("MASTER_PASSWORD")
    if pw:
        return pw
    pw = getpass.getpass("Master password: ")
    if confirm:
        pw2 = getpass.getpass("Confirm master password: ")
        if pw != pw2:
            print("ERROR: Passwords don't match.")
            sys.exit(1)
    return pw


def _load_vault(master_password: str) -> dict:
    """Decrypt and load the vault. Returns empty dict if vault doesn't exist."""
    if not os.path.exists(VAULT_PATH):
        return {}
    with open(VAULT_PATH, 'rb') as f:
        data = f.read()
    # First 16 bytes = salt, rest = encrypted payload
    salt = data[:16]
    ciphertext = data[16:]
    key = _derive_key(master_password, salt)
    try:
        fernet = Fernet(key)
        plaintext = fernet.decrypt(ciphertext)
        return json.loads(plaintext)
    except Exception:
        print("ERROR: Wrong master password or corrupted vault.")
        sys.exit(1)


def _save_vault(master_password: str, vault: dict):
    """Encrypt and save the vault."""
    salt = os.urandom(16)
    key = _derive_key(master_password, salt)
    fernet = Fernet(key)
    plaintext = json.dumps(vault, indent=2).encode()
    ciphertext = fernet.encrypt(plaintext)
    with open(VAULT_PATH, 'wb') as f:
        f.write(salt + ciphertext)
    os.chmod(VAULT_PATH, 0o600)  # Owner read/write only


def cmd_set(service: str):
    """Add or update credentials for a service."""
    master = _get_master_password(confirm=not os.path.exists(VAULT_PATH))
    vault = _load_vault(master)

    print(f"\nSetting credentials for: {service}")
    print("Press Enter to keep existing value.\n")

    existing = vault.get(service, {})

    email = input(f"  Email [{existing.get('email', '')}]: ").strip()
    if not email:
        email = existing.get('email', '')

    password = getpass.getpass(f"  Password [{'*' * len(existing.get('password', ''))}]: ")
    if not password:
        password = existing.get('password', '')

    totp_secret = input(f"  TOTP Secret [{existing.get('totp_secret', '')}]: ").strip()
    if not totp_secret:
        totp_secret = existing.get('totp_secret', '')

    vault[service] = {
        "email": email,
        "password": password,
        "totp_secret": totp_secret,
    }

    _save_vault(master, vault)
    print(f"\n  Saved credentials for '{service}' to vault.")


def cmd_get(service: str, field: str):
    """Decrypt and print a specific field (for scripting)."""
    master = _get_master_password()
    vault = _load_vault(master)

    if service not in vault:
        print(f"ERROR: Service '{service}' not found in vault.", file=sys.stderr)
        sys.exit(1)

    creds = vault[service]
    if field in creds:
        print(creds[field])
    else:
        print(f"ERROR: Field '{field}' not found.", file=sys.stderr)
        sys.exit(1)


def cmd_get_all(service: str):
    """Decrypt and export all fields for a service as env exports."""
    master = _get_master_password()
    vault = _load_vault(master)

    if service not in vault:
        print(f"ERROR: Service '{service}' not found in vault.", file=sys.stderr)
        sys.exit(1)

    creds = vault[service]
    # Output as export commands (safe for shell eval)
    for key, val in creds.items():
        safe_val = val.replace("'", "'\\''")
        print(f"export AUTH_{key.upper()}='{safe_val}'")


def cmd_list():
    """List all services in the vault (no passwords shown)."""
    master = _get_master_password()
    vault = _load_vault(master)

    if not vault:
        print("Vault is empty.")
        return

    print("Services in vault:")
    for service, creds in vault.items():
        email = creds.get('email', '(no email)')
        has_totp = "TOTP" if creds.get('totp_secret') else "no TOTP"
        has_pw = "***" if creds.get('password') else "(no password)"
        print(f"  {service}: {email} | {has_pw} | {has_totp}")


def cmd_delete(service: str):
    """Remove a service from the vault."""
    master = _get_master_password()
    vault = _load_vault(master)

    if service not in vault:
        print(f"Service '{service}' not found.")
        return

    del vault[service]
    _save_vault(master, vault)
    print(f"Deleted '{service}' from vault.")


def cmd_import_chrome(csv_path: str, domain: str, service: str, username_match: str | None = None):
    """
    Import a credential from a Chrome Passwords CSV export into the vault.

    - csv_path: path to the Chrome Passwords CSV (`name,url,username,password,note`).
    - domain: substring matched against the `url` column (e.g. `facebook.com`).
    - service: key to store under in the vault (e.g. `facebook`).
    - username_match: if given, only pick rows whose `username` equals this (used
      when the CSV has multiple accounts for the same domain).

    The selected row's values never print to stdout.
    """
    import csv as _csv
    master = _get_master_password(confirm=not os.path.exists(VAULT_PATH))
    vault = _load_vault(master)

    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        rows = list(_csv.DictReader(f))

    candidates = [r for r in rows if domain in (r.get('url') or '')]
    if username_match:
        candidates = [r for r in candidates if (r.get('username') or '') == username_match]
    if not candidates:
        print(f"ERROR: no rows matched domain='{domain}'"
              + (f" username='{username_match}'" if username_match else ''),
              file=sys.stderr)
        sys.exit(1)

    # Prefer the row with a non-empty username + password.
    candidates.sort(key=lambda r: (not r.get('username'), not r.get('password')))
    chosen = candidates[0]

    vault[service] = {
        "email": chosen.get('username') or '',
        "password": chosen.get('password') or '',
        "totp_secret": (vault.get(service) or {}).get('totp_secret', ''),
        "source_url": chosen.get('url') or '',
        "imported_from": os.path.abspath(csv_path),
    }
    _save_vault(master, vault)

    # Never print password. Confirmation shows only counts and username.
    print(f"Imported '{service}' from Chrome CSV.")
    print(f"  matched rows: {len(candidates)}  (chose first with non-empty creds)")
    print(f"  username: {vault[service]['email']}")
    print(f"  password length: {len(vault[service]['password'])}")
    print(f"  source_url: {vault[service]['source_url']}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "set" and len(sys.argv) >= 3:
        cmd_set(sys.argv[2])
    elif cmd == "get" and len(sys.argv) >= 4:
        cmd_get(sys.argv[2], sys.argv[3])
    elif cmd == "getall" and len(sys.argv) >= 3:
        cmd_get_all(sys.argv[2])
    elif cmd == "list":
        cmd_list()
    elif cmd == "delete" and len(sys.argv) >= 3:
        cmd_delete(sys.argv[2])
    elif cmd == "import-chrome" and len(sys.argv) >= 5:
        # import-chrome <csv-path> <domain-substring> <service-name> [username-match]
        username_match = sys.argv[5] if len(sys.argv) >= 6 else None
        cmd_import_chrome(sys.argv[2], sys.argv[3], sys.argv[4], username_match)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
