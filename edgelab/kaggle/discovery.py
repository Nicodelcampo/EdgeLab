"""Single offline discovery entry; byte integrity never grants research access.

No credentials, network, optional dependencies, payload deserialization or
certificate creation. This frozen snapshot is a QA inventory, not a live search.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from importlib.resources import files
from pathlib import Path, PurePosixPath


class DiscoveryError(ValueError):
    """Missing/mismatched inputs or a use forbidden by this release."""


def load_discovery():
    """Return a fresh copy of the packaged, explicitly versioned snapshot."""
    return json.loads(files('edgelab.kaggle').joinpath('discovery.json').read_text())


def consumption_plan(purpose='discovery'):
    """Research is blocked, even if every mounted byte matches the inventory."""
    contract = load_discovery()
    if purpose not in contract['allowed_purposes']:
        raise DiscoveryError('BLOCKED_FOR_RESEARCH: ' + ', '.join(
            b['id'] for b in contract['blockers']))
    return contract


def verify_mounts(mounts):
    """Hash exact paths in explicitly supplied version-ref → directory mounts.

    No basename search, alternative substitution, downloads or silent omissions.
    Version labels alone prove nothing: every listed file must match byte count
    and SHA. Matching inputs still leaves every quality blocker intact.
    """
    contract = consumption_plan('structural_qa')
    expected = {d['version_ref'] for d in contract['datasets']}
    if not isinstance(mounts, dict) or set(mounts) != expected:
        raise DiscoveryError('mount map must contain exactly the pinned dataset versions')
    checked = 0
    for dataset in contract['datasets']:
        location = mounts[dataset['version_ref']]
        if not isinstance(location, str) or not location:
            raise DiscoveryError('mount directory must be a nonempty string')
        root = Path(location).resolve(strict=True)
        if not root.is_dir():
            raise DiscoveryError('mount is not a directory')
        for entry in dataset['files']:
            rel = PurePosixPath(entry['path'])
            if rel.is_absolute() or '..' in rel.parts or not rel.parts:
                raise DiscoveryError('unsafe path in discovery snapshot')
            path = (root / entry['path']).resolve(strict=True)
            if not path.is_relative_to(root) or not path.is_file():
                raise DiscoveryError('file escapes mount or is not a regular file')
            before = path.stat()
            if before.st_size != entry['bytes']:
                raise DiscoveryError('input size mismatch: ' + entry['path'])
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for batch in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(batch)
            after = path.stat()
            if (before.st_size, before.st_mtime_ns, before.st_ino) != (
                    after.st_size, after.st_mtime_ns, after.st_ino):
                raise DiscoveryError('input changed during verification')
            if digest.hexdigest() != entry['sha256']:
                raise DiscoveryError('input hash mismatch: ' + entry['path'])
            checked += 1
    return {'status': 'PASS_INPUT_BYTES_ONLY', 'files_checked': checked,
            'research_allowed': False, 'promotion_allowed': False,
            'quality_blockers': [b['id'] for b in contract['blockers']]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--purpose', choices=['discovery', 'structural_qa', 'research'],
                        default='discovery')
    parser.add_argument('--verify-mounts', type=Path,
                        help='JSON: exact version_ref → explicit dataset directory')
    args = parser.parse_args(argv)
    try:
        plan = consumption_plan(args.purpose)  # Reject research BEFORE any mount access.
        result = verify_mounts(json.loads(args.verify_mounts.read_text())) if args.verify_mounts else plan
    except (DiscoveryError, OSError, ValueError) as exc:
        print(json.dumps({'status': 'STOP', 'reason': str(exc), 'research_allowed': False}))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
