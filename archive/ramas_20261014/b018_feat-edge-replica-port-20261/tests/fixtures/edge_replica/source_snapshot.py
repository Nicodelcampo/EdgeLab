"""Byte-exact C# snapshot; no compilation or execution of the source."""
import base64,hashlib,lzma
from pathlib import Path
def source_bytes():
    root=Path(__file__).parent
    text=''.join((root/f'EdgeReplica.cs.xz.b64.{i}').read_text().strip() for i in range(8))
    assert len(text)==4668,'incomplete snapshot'
    raw=lzma.decompress(base64.b64decode(text,validate=True))
    assert hashlib.sha256(raw).hexdigest()=='3afb40ff37523be65476bc0dc6c15fd7826aaff1dc5f895f8f6e3041a6f76a5c','source identity mismatch'
    return raw
