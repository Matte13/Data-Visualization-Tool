#!/usr/bin/env python3
"""Create a source/deployment archive from an explicit allowlist, without data."""
import hashlib
from pathlib import Path
import stat
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT_FILES={'.env.example','.dockerignore','.gitignore','Dockerfile','compose.yaml',
            'compose.postgres.yaml','README.md','requirements.txt','requirements-postgres.txt',
            'requirements-dev.txt','requirements-azuresql.txt','compose.azuresql.yaml'}
DOCS={'docs/deployment.md','docs/azure-portal.md','docs/workbook-format.md','docs/release-notes.md',
      'data/README.md','web/THIRD_PARTY_NOTICES.md'}
ASSETS={'app/assets/presentation-style.pptx','app/assets/kpmg-footer-logo.xml'}


def selected(relative):
    name=relative.as_posix()
    if any(part in {'__pycache__','secrets','.git','runtime','dist'} for part in relative.parts):return False
    if name in ROOT_FILES|DOCS|ASSETS:return True
    return ((name.startswith('app/') and relative.suffix=='.py') or
            (name.startswith('web/') and relative.suffix in {'.js','.css','.html'}) or
            (name.startswith('tests/') and relative.suffix in {'.py','.cjs'}) or
            (name.startswith('scripts/') and relative.suffix in {'.py','.sh'}) or
            (name.startswith('.github/workflows/') and relative.suffix in {'.yml','.yaml'}) or
            (name.startswith('infra/azure/') and (relative.suffix=='.bicep' or relative.name=='parameters.example.json')))


def package(root, output):
    root=Path(root).resolve();output=Path(output)
    files=sorted(path for path in root.rglob('*') if path.is_file() and not path.is_symlink()
                 and selected(path.relative_to(root)))
    output.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(output,'w',ZIP_DEFLATED) as archive:
        for path in files:
            relative=path.relative_to(root)
            entry=ZipInfo('data-visualization-tool/'+relative.as_posix(),date_time=(2026,1,1,0,0,0))
            entry.compress_type=ZIP_DEFLATED
            mode=0o755 if relative.suffix=='.sh' else 0o644
            entry.external_attr=(stat.S_IFREG|mode)<<16
            archive.writestr(entry,path.read_bytes())
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix+'.sha256').write_text(digest+'  '+output.name+'\n')
    return len(files)


if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    output=root/'dist/data-visualization-tool-deploy.zip'
    print(f'Pacchetto creato: {output} ({package(root,output)} file; checksum SHA-256 separato).')
