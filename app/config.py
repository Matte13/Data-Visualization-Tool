"""Validated runtime settings, with Docker/Azure secret-file support.

Desktop use keeps filesystem persistence. A configured SQL deployment
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
    azure_sql_connection_string: str | None = field(default=None, repr=False)
    azure_sql_schema: str = 'dbo'

    @classmethod
    def from_environ(cls, environment: Mapping[str, str] | None = None):
        environment = os.environ if environment is None else environment
        sql_keys = ('AZURE_SQL_SERVER', 'AZURE_SQL_PORT', 'AZURE_SQL_DATABASE',
                    'AZURE_SQL_USER', 'AZURE_SQL_PASSWORD', 'AZURE_SQL_PASSWORD_FILE',
                    'AZURE_SQL_SCHEMA', 'AZURE_SQL_TRUST_SERVER_CERTIFICATE')
        backend = environment.get('STORAGE_BACKEND', '').strip().lower()
        if backend not in ('', 'local', 'azuresql', 'postgres'):
            raise ConfigurationError('STORAGE_BACKEND deve essere local, azuresql oppure postgres.')
        has_postgres = any(environment.get(key) for key in (
            'DATABASE_URL', 'DATABASE_URL_FILE', 'PGHOST', 'PGPORT', 'PGDATABASE',
            'PGUSER', 'PGPASSWORD', 'PGPASSWORD_FILE', 'PGSSLMODE', 'PGSSLROOTCERT'))
        has_sql = any(environment.get(key) for key in sql_keys)
        if (has_sql and has_postgres) or (backend == 'azuresql' and has_postgres) or (backend == 'postgres' and has_sql):
            raise ConfigurationError('Configurare un solo database: rimuovere i parametri del backend precedente.')
        if backend == 'local' and (has_sql or has_postgres):
            raise ConfigurationError('STORAGE_BACKEND=local non accetta parametri di database esterni.')
        if backend == 'azuresql' or has_sql:
            import re
            missing = [key for key in ('AZURE_SQL_SERVER', 'AZURE_SQL_DATABASE', 'AZURE_SQL_USER')
                       if not environment.get(key)]
            if missing:
                raise ConfigurationError('Configurazione Azure SQL incompleta: ' + ', '.join(missing) + '.')
            password = _secret(environment, 'AZURE_SQL_PASSWORD')
            if password is None:
                raise ConfigurationError('Configurare AZURE_SQL_PASSWORD oppure AZURE_SQL_PASSWORD_FILE.')
            try:
                port = int(environment.get('AZURE_SQL_PORT', '1433'))
                if not 1 <= port <= 65535:
                    raise ValueError('port')
            except ValueError:
                raise ConfigurationError('AZURE_SQL_PORT deve essere un numero tra 1 e 65535.') from None
            schema = environment.get('AZURE_SQL_SCHEMA', 'dbo')
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,62}', schema):
                raise ConfigurationError('AZURE_SQL_SCHEMA deve essere un identificatore SQL semplice (massimo 63 caratteri).')
            trust = _boolean(environment.get('AZURE_SQL_TRUST_SERVER_CERTIFICATE'),
                             'AZURE_SQL_TRUST_SERVER_CERTIFICATE')
            def odbc(value):
                if '\x00' in value:
                    raise ConfigurationError('La configurazione Azure SQL contiene un carattere non valido.')
                return '{' + value.replace('}', '}}') + '}'
            settings = {
                'DRIVER': 'ODBC Driver 18 for SQL Server',
                'SERVER': 'tcp:' + environment['AZURE_SQL_SERVER'] + ',' + str(port),
                'DATABASE': environment['AZURE_SQL_DATABASE'],
                'UID': environment['AZURE_SQL_USER'], 'PWD': password,
                'Encrypt': 'yes', 'TrustServerCertificate': 'yes' if trust else 'no',
                'APP': 'Data Visualization Tool',
            }
            connection = ';'.join(key + '=' + odbc(value) for key, value in settings.items()) + ';'
            return cls(azure_sql_connection_string=connection, azure_sql_schema=schema)
        required = _boolean(environment.get('REQUIRE_POSTGRES'), 'REQUIRE_POSTGRES')
        if backend == 'postgres':
            required = True
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
