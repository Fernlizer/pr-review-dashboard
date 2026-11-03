"""Build-time install of pinned, checksum-verified upstream scanner binaries."""
import hashlib
import io
import platform
import tarfile
from pathlib import Path
from urllib.request import urlopen

arch = 'arm64' if platform.machine() in {'aarch64', 'arm64'} else 'amd64'
gitleaks = {
    'arm64': ('arm64', 'e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080'),
    'amd64': ('x64', '551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb'),
}
osv = {'arm64': '4061ef4c021ed3c47f203b818f337e351336cc5cd67c0274fc36bd1dfc728dd7',
       'amd64': '160c6253e2922e9e0a6a9771c5c4c40a4b3c6090b34a3cdd5e80c96cc2e4218b'}

def download(url, digest):
    with urlopen(url, timeout=120) as response:
        content = response.read(200_000_001)
    if len(content) > 200_000_000 or hashlib.sha256(content).hexdigest() != digest:
        raise RuntimeError('Scanner download failed checksum/size verification')
    return content

suffix, digest = gitleaks[arch]
archive = download(f'https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_{suffix}.tar.gz', digest)
with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tar:
    content = tar.extractfile('gitleaks').read()
p = Path('/usr/local/bin/gitleaks'); p.write_bytes(content); p.chmod(0o755)
content = download(f'https://github.com/google/osv-scanner/releases/download/v2.7.0/osv-scanner_linux_{arch}', osv[arch])
p = Path('/usr/local/bin/osv-scanner'); p.write_bytes(content); p.chmod(0o755)
