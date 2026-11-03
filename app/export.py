"""Produce a single portable HTML file; its filters need no server or Internet."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from .server import BASE_FILENAME, ROOT
from .workbook import parse_workbook


STYLESHEETS = ('styles.css', 'countries.css', 'brand.css')
SCRIPTS = ('model.js', 'countries.js', 'app.js')


def inline_assets(document: dict, root: Path = ROOT) -> str:
    """Bundle the same asset order as index.html, with no runtime external files."""
    template = (root / 'web' / 'index.html').read_text(encoding='utf-8')
    css = '\n'.join((root / 'web' / name).read_text(encoding='utf-8') for name in STYLESHEETS)
    sources = [(root / 'web' / name).read_text(encoding='utf-8') for name in SCRIPTS]
    # Excel cell strings may contain HTML, so never interpolate raw data in a script element.
    payload = json.dumps(document, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c')
    for name in STYLESHEETS:
        template = template.replace(f'  <link rel="stylesheet" href="{name}">', '')
    template = template.replace('</head>', '<style>' + css + '</style>\n</head>')
    for name in SCRIPTS:
        template = template.replace(f'  <script defer src="{name}"></script>', '')
    scripts = '\n'.join('<script>' + re.sub('</script', lambda _: '<\\/script', source, flags=re.IGNORECASE) + '</script>'
                        for source in ['window.DVT_DATA=' + payload + ';', *sources])
    return template.replace('</body>', scripts + '\n</body>')


def standalone_html(content: bytes, filename: str = BASE_FILENAME, root: Path = ROOT) -> str:
    return inline_assets(parse_workbook(content, filename), root)


def main():
    parser = argparse.ArgumentParser(description='Esporta Data Visualization Tool in un singolo HTML offline.')
    parser.add_argument('--input', type=Path, default=ROOT / 'data' / 'base.xlsx')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist' / 'Data-Visualization-Tool-remediation-offline.html')
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
