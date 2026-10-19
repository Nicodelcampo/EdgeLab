"""Verify detached Ed25519 receipts against EXTERNALLY provisioned trust roots.
There is deliberately no production signing/key-generation API or default key.
The host owns roots, reviewer roles, revocation, clock and destination mapping.
"""
import base64
from .store import canonical, digest
from .post_run import _id, _sha


def verify_signed(pack, *, trusted_keys, role, now, max_age_seconds=86400):
    if type(pack) is not dict or set(pack) != {'payload', 'key_id', 'signature'}:
        raise ValueError('closed detached signature receipt required')
    if type(trusted_keys) is not dict or not trusted_keys:
        raise ValueError('external trust roots required; never trust keys in receipt')
    _id(pack['key_id'])
    root = trusted_keys.get(pack['key_id'])
    if type(root) is not dict or set(root) != {'public_key', 'principal', 'role'} or root['role'] != role:
        raise ValueError('untrusted key or authority role')
    _id(root['principal'])
    p = pack['payload']
    if type(p) is not dict or p.get('principal') != root['principal']:
        raise ValueError('key/principal binding mismatch')
    if type(now) is not int or now < 1:
        raise ValueError('trusted host clock required')
    if any(type(p.get(k)) is not int for k in ('issued_at', 'expires_at')):
        raise ValueError('integer signed clock bounds required')
    if p['issued_at']<1 or not p['issued_at'] <= now < p['expires_at'] or not 0 < p['expires_at']-p['issued_at'] <= max_age_seconds:
        raise ValueError('expired, future or overlong authority receipt')
    raw = canonical(p).encode()
    if len(raw) > 65536:
        raise ValueError('bounded signed receipt required')
    try:
        public = base64.b64decode(root['public_key'], validate=True)
        signature = base64.b64decode(pack['signature'], validate=True)
        if len(public) != 32 or len(signature) != 64:
            raise ValueError('Ed25519 lengths required')
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(public).verify(signature, raw)
    except Exception as exc:
        raise ValueError('signature verification failed') from exc
    return dict(payload=p, receipt_sha256=digest(pack), signer=root['principal'])