"""Fetch a version-pinned road archive; never overwrite an existing dataset."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
from urllib.request import urlopen


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def relative_name(name):
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or '\\' in name or p.as_posix() != name:
        raise ValueError(f'unsafe archive path: {name!r}')
    return p


def unpack(archive, spec, stage):
    root = relative_name(spec['root'])
    if len(root.parts) != 1:
        raise ValueError('archive root must be one directory')
    with tarfile.open(archive, 'r:gz') as tar:
        members = {}
        for member in tar.getmembers():
            p = relative_name(member.name.rstrip('/') if member.isdir() else member.name)
            if p.parts[0] != str(root) or not (member.isfile() or member.isdir()):
                raise ValueError(f'unsupported archive member: {member.name}')
            if member.name in members:
                raise ValueError('duplicate archive member')
            members[member.name] = member
        manifest_name = f'{root}/manifest.json'
        item = members.get(manifest_name)
        if item is None or not item.isfile():
            raise ValueError('missing archive manifest')
        manifest_bytes = tar.extractfile(item).read()
        if hashlib.sha256(manifest_bytes).hexdigest() != spec['manifest_sha256']:
            raise ValueError('manifest hash mismatch')
        manifest = json.loads(manifest_bytes)
        expected = {}
        for name, entry in manifest['files'].items():
            relative_name(name)
            if name == 'manifest.json':
                raise ValueError('manifest cannot hash itself')
            expected[f'{root}/{name}'] = entry
        files = {name for name, member in members.items() if member.isfile()}
        if files != set(expected) | {manifest_name}:
            raise ValueError('archive files differ from manifest')
        for name in sorted(files):
            member = members[name]
            if name in expected and member.size != expected[name]['bytes']:
                raise ValueError(f'file size mismatch: {name}')
            output = stage / name
            output.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as source, output.open('xb') as target:
                shutil.copyfileobj(source, target)
            if name in expected and digest(output) != expected[name]['sha256']:
                raise ValueError(f'file hash mismatch: {name}')
    return stage / str(root), len(files)


def fetch(config, destination, *, archive=None):
    """Verify archive and every member before publishing a new local directory."""
    spec = json.loads(Path(config).read_text())
    target = Path(destination)
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    if archive is None and not spec.get('url'):
        raise ValueError('road archive is not published; supply a verified local --archive')
    # Single-user research workflow: private temporary directory on the target filesystem.
    with tempfile.TemporaryDirectory(prefix='.roads-', dir=target.parent) as temporary:
        stage = Path(temporary)
        source = Path(archive) if archive is not None else stage / 'download.tar.gz'
        if archive is None:
            with urlopen(spec['url'], timeout=60) as response, source.open('xb') as output:
                shutil.copyfileobj(response, output)
        if source.stat().st_size != spec['bytes'] or digest(source) != spec['sha256']:
            raise ValueError('archive size/hash mismatch')
        extracted, count = unpack(source, spec, stage)
        if target.exists() or target.is_symlink():
            raise FileExistsError(target)
        extracted.rename(target)
    return {'version': spec['version'], 'files': count, 'sha256': spec['sha256'],
            'destination': str(target)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', default='road_data.json')
    parser.add_argument('--output', required=True)
    parser.add_argument('--archive', help='Use an existing local archive without downloading')
    args = parser.parse_args()
    print(json.dumps(fetch(args.manifest, args.output, archive=args.archive), indent=2))


if __name__ == '__main__':
    main()
