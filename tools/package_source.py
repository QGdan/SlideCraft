"""Build a GitHub source ZIP without local dependencies or historical artifacts."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    '.git', '.venv', '.mcp-venv', 'node_modules', '__pycache__',
    '.tmp', '.npm-cache', '.pip-cache', '.npm', '.pytest_cache',
    '.ruff_cache', '.idea', '.vscode', 'runs', 'experiments', 'online-cache',
}
SKIP_SUFFIXES = {'.pyc', '.pyo', '.zip', '.7z', '.tgz', '.tmp', '.key', '.pfx', '.p12'}


def source_files():
    for name in ('.gitignore', 'README.md', 'CONTRIBUTING.md'):
        yield ROOT / name
    for folder in ('ppt-workflow', 'docs', 'tools'):
        for path in sorted((ROOT / folder).rglob('*')):
            rel = path.relative_to(ROOT)
            if not path.is_file() or set(rel.parts) & SKIP_DIRS:
                continue
            if path.is_symlink():
                raise ValueError(f'Symlinks are not supported: {rel}')
            is_zip_fixture = rel.parts[:3] == ('ppt-workflow', 'tests', 'fixtures') and path.suffix.lower() == '.zip'
            if (path.suffix.lower() in SKIP_SUFFIXES and not is_zip_fixture) or path.name.startswith(('~$', '.env')):
                continue
            if path.name in {'.npmrc', '.pypirc', 'credentials.json', 'installation.json'}:
                continue
            if path.name.endswith('install-report.json'):
                continue
            if rel.parts[:3] == ('ppt-workflow', 'templates', 'imported') and path.name != 'README.md':
                continue
            yield path


def main():
    out = ROOT / 'dist'
    out.mkdir(exist_ok=True)
    archive = out / 'ppt-workflow-github-source.zip'
    manifest = []
    with ZipFile(archive, 'w', ZIP_DEFLATED) as z:
        for path in source_files():
            data = path.read_bytes()
            name = path.relative_to(ROOT).as_posix()
            manifest.append({'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
            z.writestr('ppt-workflow-project/' + name, data)
        z.writestr('ppt-workflow-project/SOURCE_MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    with ZipFile(archive) as z:
        if z.testzip() is not None:
            raise RuntimeError('ZIP integrity check failed')
    report = {
        'archive': archive.name, 'files': len(manifest),
        'source_bytes': sum(row['bytes'] for row in manifest),
        'archive_bytes': archive.stat().st_size,
        'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
    }
    (out / 'package-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
