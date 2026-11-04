"""Validated runtime settings, with Docker/Azure secret-file support.

Desktop use keeps filesystem persistence. A configured PostgreSQL deployment
never falls back to disk, and exception messages never contain credentials.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Mapping


class ConfigurationError(ValueError):
    """A configuration error safe to show in startup logs."""


def _secret(environment: Mapping[str, str], name: str) -> str | None:
    value = environment.get(name)
    filename = environment.get(name + '_FILE')
    if value and filename:
        raise ConfigurationError(f'Configurare soltanto {name} oppure {name}_FILE.')
    if filename:
        try:
            value = Path(filename).read_text(encoding='utf-8').rstrip('\r\n')
        except (OSError, UnicodeError):
            raise ConfigurationError(f'Impossibile leggere {name}_FILE.') from None
        if not value:
            raise ConfigurationError(f'{name}_FILE non può essere vuoto.')
    return value or None


def _boolean(value: str | None, name: str) -> bool:
    if value is None or value.strip().lower() in ('', '0', 'false', 'no', 'off'):
        return False
    if value.strip().lower() in ('1', 'true', 'yes', 'on'):
        return True
    raise ConfigurationError(f'{name} deve essere true oppure false.')


@dataclass(frozen=True)
class RuntimeConfig:
    database_url: str | None = field(default=None, repr=False)
    database_options: dict | None = field(default=None, repr=False)
    require_postgres: bool = False

    @classmethod
    def from_environ(cls, environment: Mapping[str, str] | None = None):
        environment = os.environ if environment is None else environment
        required = _boolean(environment.get('REQUIRE_POSTGRES'), 'REQUIRE_POSTGRES')
        url = _secret(environment, 'DATABASE_URL')
        if url:
            return cls(database_url=url, require_postgres=required)
        keys = ('PGHOST', 'PGPORT', 'PGDATABASE', 'PGUSER', 'PGPASSWORD',
                'PGPASSWORD_FILE', 'PGSSLMODE', 'PGSSLROOTCERT')
        configured = any(environment.get(name) for name in keys)
        if not configured:
            if required:
                raise ConfigurationError('REQUIRE_POSTGRES=true: configurare PostgreSQL prima dell’avvio.')
            return cls()
        missing = [name for name in ('PGHOST', 'PGDATABASE', 'PGUSER') if not environment.get(name)]
        if missing:
            raise ConfigurationError('Configurazione PostgreSQL incompleta: ' + ', '.join(missing) + '.')
        password = _secret(environment, 'PGPASSWORD')
        if password is None:
            raise ConfigurationError('Configurare PGPASSWORD oppure PGPASSWORD_FILE.')
        try:
            port = int(environment.get('PGPORT', '5432'))
            if not 1 <= port <= 65535:
                raise ValueError('port')
        except ValueError:
            raise ConfigurationError('PGPORT deve essere un numero tra 1 e 65535.') from None
        sslmode = environment.get('PGSSLMODE', 'prefer')
        if sslmode not in ('disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'):
            raise ConfigurationError('PGSSLMODE non è valido.')
        options = {'host': environment['PGHOST'], 'port': port,
                   'dbname': environment['PGDATABASE'], 'user': environment['PGUSER'],
                   'password': password, 'sslmode': sslmode}
        if environment.get('PGSSLROOTCERT'):
            options['sslrootcert'] = environment['PGSSLROOTCERT']
        return cls(database_options=options, require_postgres=required)
