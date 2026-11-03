"""Produce a single portable HTML file; its filters need no server or Internet."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .server import BASE_FILENAME, ROOT
from .workbook import parse_workbook


def standalone_html(content: bytes, filename: str = BASE_FILENAME, root: Path = ROOT) -> str:
    document = parse_workbook(content, filename)
    template = (root / 'web' / 'index.html').read_text(encoding='utf-8')
    css = (root / 'web' / 'styles.css').read_text(encoding='utf-8')
    model = (root / 'web' / 'model.js').read_text(encoding='utf-8')
    app = (root / 'web' / 'app.js').read_text(encoding='utf-8')
    # Excel cell strings may contain HTML, so never interpolate raw data in a script element.
    payload = json.dumps(document, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c')
    template = template.replace('  <link rel="stylesheet" href="styles.css">', '<style>' + css + '</style>')
    template = template.replace('  <script defer src="model.js"></script>', '')
    template = template.replace('  <script defer src="app.js"></script>', '')
    scripts = '\n'.join('<script>' + source.replace('</script', '<\\/script') + '</script>'
                        for source in ['window.ATLAS_DATA=' + payload + ';', model, app])
    return template.replace('</body>', scripts + '\n</body>')


def main():
    parser = argparse.ArgumentParser(description='Esporta Atlas in un singolo HTML offline.')
    parser.add_argument('--input', type=Path, default=ROOT / 'data' / 'base.xlsx')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist' / 'Atlas-remediation-offline.html')
    args = parser.parse_args()
    filename = BASE_FILENAME if args.input == ROOT / 'data' / 'base.xlsx' else args.input.name
    try:
        html = standalone_html(args.input.read_bytes(), filename)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(html, encoding='utf-8')
    except (ValueError, OSError) as error:
        parser.exit(1, str(error) + '\n')
    print(f'HTML offline creato: {args.output}')


if __name__ == '__main__':
    main()
