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
