"""Packaging excludes client data and credentials; local setup is non-destructive."""
import importlib.util
from pathlib import Path
import os
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
def load(name,filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/filename)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
INIT=load('dvt_init_env','init-env.py')
PACKAGE=load('dvt_package','package-release.py')


class ContainerSetupTests(unittest.TestCase):
    def test_initialize_creates_private_secret_without_putting_it_in_env(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'.env.example').write_text('DVT_PORT=8000\n')
            self.assertTrue(INIT.initialize(root))
            secret=(root/'deploy/secrets/postgres_password').read_text()
            self.assertGreaterEqual(len(secret.strip()),40)
            self.assertNotIn(secret.strip(),(root/'.env').read_text())
            self.assertFalse(INIT.initialize(root))
            self.assertEqual((root/'deploy/secrets/postgres_password').read_text(),secret)
            if os.name!='nt':self.assertEqual((root/'deploy/secrets').stat().st_mode&0o777,0o700)

    def test_existing_operator_env_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'.env').write_text('KEEP=original\n')
            with self.assertRaises(ValueError):INIT.initialize(root)
            self.assertEqual((root/'.env').read_text(),'KEEP=original\n')

    def test_archive_contains_runtime_and_deployment_but_no_private_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            examples=['app/server.py','web/app.js','infra/azure/main.bicep',
                      'app/assets/presentation-style.pptx','.env.example',
                      'data/client.xlsx','runtime/projects.json','deploy/secrets/password',
                      '.env','infra/azure/password.local.json','docs/data-audit.md','private.m4a']
            for name in examples:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(name)
            output=root/'dist/release.zip';PACKAGE.package(root,output)
            with ZipFile(output) as archive:
                names=archive.namelist();self.assertIsNone(archive.testzip())
            self.assertIn('data-visualization-tool/app/server.py',names)
            self.assertIn('data-visualization-tool/app/assets/presentation-style.pptx',names)
            self.assertEqual(len(names),5)
            self.assertTrue(output.with_suffix('.zip.sha256').exists())
