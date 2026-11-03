"""PowerPoint exports use one explicit project and never change stored data."""
from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zipfile import ZipFile

from pptx import Presentation
from app.server import ExplorerServer, WorkbookStore
from fixtures import make_workbook


class PresentationHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = WorkbookStore(self.root)
        self.first = self.store.create(make_workbook(name_prefix='First', compact=True, include_ot=False), 'first.xlsx', 'First project')
        self.second = self.store.create(make_workbook(name_prefix='Second', compact=True, include_ot=False), 'second.xlsx', 'Second project')
        self.server = ExplorerServer(('127.0.0.1', 0), self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=3)
        self.temp.cleanup()

    def snapshot_request(self):
        rows = self.first['rows'][:2]
        return {'projectId': self.first['project']['id'], 'rowKeys': [row['key'] for row in rows],
                'entities': ['First Entity 01'], 'scope': 'all',
                'filters': {'years': ['2027', '2028'], 'entities': ['First Entity 01']},
                'countryRows': {'First Entity 01': [row['key'] for row in rows]}}

    def request(self, payload=None, *, raw=None, headers=None):
        data = raw if raw is not None else json.dumps(self.snapshot_request() if payload is None else payload).encode()
        request_headers = {'Content-Type': 'application/json', 'Origin': self.origin}
        request_headers.update(headers or {})
        return urlopen(Request(self.origin+'/api/presentation', data=data, headers=request_headers, method='POST'), timeout=30)

    def assert_status(self, expected, payload=None, **kwargs):
        before = self.store.catalog()
        with self.assertRaises(HTTPError) as error:
            self.request(payload, **kwargs)
        self.assertEqual(error.exception.code, expected, error.exception.read())
        self.assertEqual(self.store.catalog(), before)

    def test_download_is_valid_pptx_for_explicit_project_while_another_is_active(self):
        before = self.store.catalog()
        with self.request() as response:
            content = response.read()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers['Content-Type'], 'application/vnd.openxmlformats-officedocument.presentationml.presentation')
            self.assertIn('.pptx', response.headers['Content-Disposition'])
            self.assertIn('attachment;', response.headers['Content-Disposition'])
        with ZipFile(BytesIO(content)) as archive:
            self.assertIsNone(archive.testzip())
            self.assertIn('ppt/presentation.xml', archive.namelist())
        deck = Presentation(BytesIO(content))
        text = '\n'.join(shape.text for slide in deck.slides for shape in slide.shapes if shape.has_text_frame)
        notes = '\n'.join(slide.notes_slide.notes_text_frame.text for slide in deck.slides)
        self.assertIn('First project', text)
        self.assertIn('First governance', text+notes)
        self.assertIn('First backup', text+notes)
        self.assertNotIn('Second governance', text+notes)
        self.assertNotIn('First insurance', text+notes)
        self.assertEqual(self.store.catalog(), before)
        self.assertEqual(self.store.active_project_id, self.second['project']['id'])

    def test_json_must_be_valid_utf8_and_finite(self):
        for content in [b'not json', b'\xff', b'{"value":NaN}', b'']:
            with self.subTest(content=content):
                self.assert_status(400, raw=content)

    def test_snapshot_must_be_object_with_explicit_project(self):
        self.assert_status(422, [])
        self.assert_status(422, {})

    def test_missing_project_returns_404_without_fallback(self):
        payload = self.snapshot_request();payload['projectId'] = '00000000-0000-0000-0000-000000000000'
        self.assert_status(404, payload)

    def test_unknown_and_duplicate_source_rows_are_rejected(self):
        payload = self.snapshot_request();payload['rowKeys'] = ['Remediations:9999']
        self.assert_status(422, payload)
        payload = self.snapshot_request();payload['rowKeys'] = [payload['rowKeys'][0]]*2
        self.assert_status(422, payload)

    def test_export_has_same_origin_protection(self):
        self.assert_status(403, headers={'Origin': 'https://example.invalid'})

    def test_export_request_size_is_bounded_before_reading_body(self):
        self.assert_status(413, raw=b'{}', headers={'Content-Length': str(2*1024*1024+1)})

    def test_missing_presentation_dependency_has_actionable_error(self):
        with patch.dict(sys.modules, {'app.presentation': None}):
            self.assert_status(503)


if __name__ == '__main__':
    unittest.main()
