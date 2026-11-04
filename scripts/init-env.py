#!/usr/bin/env python3
"""Prepare a private local PostgreSQL secret, without overwriting configuration."""
import os
from pathlib import Path
import secrets


def initialize(root):
    root = Path(root)
    env = root / '.env'
    directory = root / 'deploy' / 'secrets'
    password = directory / 'postgres_password'
    if env.exists():
        if password.is_file():
            return False
        raise ValueError('.env esiste già: configurare il file segreto senza sovrascriverlo.')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != 'nt': directory.chmod(0o700)
    if not password.exists():
        descriptor = os.open(password, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as target:
            target.write(secrets.token_urlsafe(36) + '\n')
    if not password.is_file() or not password.read_text().strip():
        raise ValueError('Il file della password è vuoto o non valido.')
    # Compose file-backed secrets do not remap UIDs: the host parent remains
    # private (0700), while the bind-mounted file is readable by container UIDs.
    if os.name != 'nt': password.chmod(0o444)
    with env.open('x') as target:
        target.write((root / '.env.example').read_text())
    if os.name != 'nt': env.chmod(0o600)
    return True


if __name__ == '__main__':
    try:
        changed = initialize(Path(__file__).resolve().parents[1])
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
    print('Configurazione locale creata.' if changed else 'Configurazione esistente conservata.')
