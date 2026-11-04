"""Deployment settings reject silent fallback and never expose credentials."""
from pathlib import Path
import tempfile
import unittest
from app.config import RuntimeConfig, ConfigurationError


class RuntimeConfigTests(unittest.TestCase):
    def test_desktop_default_and_required_postgres(self):
        self.assertIsNone(RuntimeConfig.from_environ({}).database_url)
        with self.assertRaises(ConfigurationError):
            RuntimeConfig.from_environ({'REQUIRE_POSTGRES':'true'})
        with self.assertRaises(ConfigurationError):
            RuntimeConfig.from_environ({'PGHOST':'db'})

    def test_secret_file_and_keyword_connection_preserve_special_characters(self):
        with tempfile.TemporaryDirectory() as directory:
            secret=Path(directory)/'secret';secret.write_text('p@ss:/?# with spaces\n')
            config=RuntimeConfig.from_environ({'PGHOST':'db','PGDATABASE':'remediation',
                'PGUSER':'explorer','PGPASSWORD_FILE':str(secret),'PGSSLMODE':'verify-full',
                'PGSSLROOTCERT':'/etc/ssl/certs/ca-certificates.crt','REQUIRE_POSTGRES':'true'})
        self.assertEqual(config.database_options['password'],'p@ss:/?# with spaces')
        self.assertEqual(config.database_options['sslmode'],'verify-full')
        self.assertNotIn('p@ss',repr(config))
        self.assertTrue(config.require_postgres)

    def test_url_priority_and_secret_conflict(self):
        config=RuntimeConfig.from_environ({'DATABASE_URL':'postgresql://user:secret@db/test','PGHOST':'ignored'})
        self.assertIsNone(config.database_options)
        self.assertNotIn('secret',repr(config))
        with self.assertRaises(ConfigurationError):
            RuntimeConfig.from_environ({'DATABASE_URL':'private','DATABASE_URL_FILE':'unused'})

    def test_invalid_ports_ssl_and_empty_secret_do_not_print_values(self):
        base={'PGHOST':'db','PGDATABASE':'test','PGUSER':'user','PGPASSWORD':'TOP-SECRET'}
        for patch in ({'PGPORT':'0'},{'PGPORT':'65536'},{'PGPORT':'oops'},{'PGSSLMODE':'unsafe'}):
            with self.subTest(patch=patch),self.assertRaises(ConfigurationError) as error:
                RuntimeConfig.from_environ({**base,**patch})
            self.assertNotIn('TOP-SECRET',str(error.exception))

    def test_azure_sql_credentials_are_escaped_and_tls_is_verified_by_default(self):
        config=RuntimeConfig.from_environ({'STORAGE_BACKEND':'azuresql',
            'AZURE_SQL_SERVER':'dbservertil.database.windows.net',
            'AZURE_SQL_DATABASE':'data-visualization-tool-db','AZURE_SQL_USER':'fuddos',
            'AZURE_SQL_PASSWORD':'p;ass} Encrypt=no; secret'})
        self.assertIn('PWD={p;ass}} Encrypt=no; secret}',config.azure_sql_connection_string)
        self.assertIn('Encrypt={yes};TrustServerCertificate={no};',config.azure_sql_connection_string)
        self.assertIn('DATABASE={data-visualization-tool-db}',config.azure_sql_connection_string)
        self.assertNotIn('secret',repr(config))
        self.assertIsNone(config.database_url)

    def test_azure_sql_secret_file_is_read_without_an_embedded_password(self):
        with tempfile.TemporaryDirectory() as directory:
            secret=Path(directory)/'password';secret.write_text('fictional-password\n')
            config=RuntimeConfig.from_environ({'AZURE_SQL_SERVER':'sqlserver',
                'AZURE_SQL_DATABASE':'test','AZURE_SQL_USER':'user',
                'AZURE_SQL_PASSWORD_FILE':str(secret)})
        self.assertIn('PWD={fictional-password}',config.azure_sql_connection_string)

    def test_incomplete_or_mixed_azure_sql_never_falls_back(self):
        base={'STORAGE_BACKEND':'azuresql','AZURE_SQL_SERVER':'sqlserver',
              'AZURE_SQL_DATABASE':'test','AZURE_SQL_USER':'user','AZURE_SQL_PASSWORD':'PRIVATE'}
        for values in ({'STORAGE_BACKEND':'azuresql'}, {'AZURE_SQL_SERVER':'server'},
                       {**base,'DATABASE_URL':'postgresql://ignored'},
                       {**base,'AZURE_SQL_PORT':'0'}, {**base,'AZURE_SQL_SCHEMA':'dbo]; DROP TABLE x;--'},
                       {**base,'STORAGE_BACKEND':'local'}):
            with self.subTest(values=list(values)),self.assertRaises(ConfigurationError) as error:
                RuntimeConfig.from_environ(values)
            self.assertNotIn('PRIVATE',str(error.exception))
