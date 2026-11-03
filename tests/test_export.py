"""Portable HTML retains local brand fonts without extra runtime files."""
from pathlib import Path
import tempfile
import unittest

from app.export import inline_assets


class ExportTests(unittest.TestCase):
    def test_brand_font_is_inlined_with_styles_in_browser_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            web = root / 'web'; web.mkdir()
            web.joinpath('index.html').write_text('''<!doctype html>
<html><head>
  <link rel="stylesheet" href="styles.css">
  <link rel="stylesheet" href="countries.css">
  <link rel="stylesheet" href="brand.css">
  <script defer src="model.js"></script>
  <script defer src="countries.js"></script>
  <script defer src="app.js"></script>
</head><body><div id="app"></div></body></html>''')
            web.joinpath('styles.css').write_text(':root{--base-color:navy}')
            web.joinpath('countries.css').write_text('.country-flag{width:24px}')
            font_css = '@font-face{font-family:KPMG;src:url(data:font/woff2;base64,d09GMg==) format("woff2")}'
            web.joinpath('brand.css').write_text(font_css)
            for name in ('model.js', 'countries.js', 'app.js'):
                web.joinpath(name).write_text('/* local ' + name + ' */')
            html = inline_assets({'source': {'filename': 'fictional.xlsx'}}, root)
        self.assertIn(font_css, html)
        self.assertLess(html.index('--base-color'), html.index('.country-flag'))
        self.assertLess(html.index('.country-flag'), html.index('@font-face'))
        self.assertNotIn('rel="stylesheet"', html)
        self.assertNotIn('defer src=', html)
        self.assertIn('window.DVT_DATA=', html)
        self.assertIn('/* local app.js */', html)


if __name__ == '__main__':
    unittest.main()
