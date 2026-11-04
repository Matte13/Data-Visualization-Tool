#!/usr/bin/env python3
"""Configure access to an existing Azure SQL database; never generate a password."""
import argparse
import getpass
import os
from pathlib import Path


def initialize(root, password=None, username='fuddos'):
    root = Path(root)
    env = root / '.env.azuresql'
    directory = root / 'deploy' / 'secrets'
    secret = directory / 'azure_sql_password'
    if env.exists():
        if secret.is_file() and secret.read_text().strip():
            return False
        raise ValueError('.env.azuresql esiste già: configurare il secret senza sovrascrivere il file.')
    if not password or not username or any(c in username for c in '\r\n\x00'):
        raise ValueError('Indicare utente e password del database Azure SQL esistente.')
    if secret.exists():
        raise ValueError('Il file password esiste già: conservarlo e configurare .env.azuresql manualmente.')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != 'nt':directory.chmod(0o700)
    descriptor = os.open(secret, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as target:target.write(password)
    # Compose bind-mounts secrets without UID remapping; the parent stays 0700.
    if os.name != 'nt':secret.chmod(0o444)
    text = (root / '.env.example').read_text()
    quoted_user = "'" + username.replace("'", "\\'") + "'"
    text = text.replace('AZURE_SQL_USER=fuddos', 'AZURE_SQL_USER='+quoted_user)
    with env.open('x') as target:target.write(text)
    if os.name != 'nt':env.chmod(0o600)
    return True


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--user', default='fuddos')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    try:
        password=None if (root/'.env.azuresql').exists() else getpass.getpass('Password Azure SQL esistente (non visualizzata): ')
        changed=initialize(root,password,args.user)
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
    print('Configurazione Azure SQL creata.' if changed else 'Configurazione esistente conservata.')
