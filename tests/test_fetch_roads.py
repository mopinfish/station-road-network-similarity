"""Small real archives pin preservation, integrity and local download behavior."""
import functools
import hashlib
import http.server
import io
import json
import tarfile
import threading

import pytest


def bundle(tmp_path, *, extra=None, bad_file_digest=False):
    payload = b'road geometry fixture\n'
    manifest = {'files': {'roads.json': {'bytes': len(payload), 'sha256':
                 '0' * 64 if bad_file_digest else hashlib.sha256(payload).hexdigest()}}}
    manifest_bytes = (json.dumps(manifest) + '\n').encode()
    archive = tmp_path / 'input.tar.gz'
    with tarfile.open(archive, 'w:gz') as tar:
        for name, data in [('v1/roads.json', payload), ('v1/manifest.json', manifest_bytes)]:
            info = tarfile.TarInfo(name); info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        if extra:
            info = tarfile.TarInfo(extra[0])
            if extra[1] == 'symlink':
                info.type = tarfile.SYMTYPE; info.linkname = '/outside'
                tar.addfile(info)
            else:
                info.size = 1; tar.addfile(info, io.BytesIO(b'x'))
    spec = {'version': 'v1', 'root': 'v1', 'url': None,
            'bytes': archive.stat().st_size,
            'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest()}
    config = tmp_path / 'download.json'; config.write_text(json.dumps(spec))
    return archive, config, spec


def test_verified_local_extract_and_existing_target_preserved(tmp_path):
    from paper1.fetch_roads import fetch
    archive, config, _ = bundle(tmp_path)
    target = tmp_path / 'installed'
    result = fetch(config, target, archive=archive)
    assert result['files'] == 2
    assert (target / 'roads.json').read_bytes() == b'road geometry fixture\n'
    (target / 'keep').write_text('preserve')
    with pytest.raises(FileExistsError):
        fetch(config, target, archive=archive)
    assert (target / 'keep').read_text() == 'preserve'


def test_unpublished_url_refuses_before_download(tmp_path):
    from paper1.fetch_roads import fetch
    _, config, _ = bundle(tmp_path)
    with pytest.raises(ValueError, match='not published'):
        fetch(config, tmp_path / 'installed')
    assert not (tmp_path / 'installed').exists()


@pytest.mark.parametrize('mutation', ['archive_hash', 'archive_size', 'manifest_hash', 'file_hash'])
def test_integrity_failure_leaves_no_installation(tmp_path, mutation):
    from paper1.fetch_roads import fetch
    archive, config, spec = bundle(tmp_path, bad_file_digest=mutation == 'file_hash')
    if mutation == 'archive_hash': spec['sha256'] = '0' * 64
    if mutation == 'archive_size': spec['bytes'] += 1
    if mutation == 'manifest_hash': spec['manifest_sha256'] = '0' * 64
    config.write_text(json.dumps(spec))
    with pytest.raises(ValueError):
        fetch(config, tmp_path / 'installed', archive=archive)
    assert not (tmp_path / 'installed').exists()
    assert archive.exists()


@pytest.mark.parametrize('extra', [('v1/../escape', 'file'), ('/absolute', 'file'),
                                  ('v1/link', 'symlink'), ('v1/unlisted', 'file')])
def test_unsafe_or_unlisted_archive_member_rejected(tmp_path, extra):
    from paper1.fetch_roads import fetch
    archive, config, _ = bundle(tmp_path, extra=extra)
    with pytest.raises(ValueError):
        fetch(config, tmp_path / 'installed', archive=archive)
    assert not (tmp_path / 'installed').exists()
    assert not (tmp_path / 'escape').exists()


def test_local_http_download_matches_fixed_archive(tmp_path):
    from paper1.fetch_roads import fetch
    _, config, spec = bundle(tmp_path)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_): pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
              functools.partial(Quiet, directory=str(tmp_path)))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        spec['url'] = f'http://127.0.0.1:{server.server_port}/input.tar.gz'
        config.write_text(json.dumps(spec))
        fetch(config, tmp_path / 'installed')
        assert (tmp_path / 'installed' / 'roads.json').read_bytes() == b'road geometry fixture\n'
    finally:
        server.shutdown(); server.server_close(); thread.join()
