#!/usr/bin/env python3
"""Prepare an immutable NinjaScript artifact without changing semantics.

The raw artifact remains untouched. This tool verifies SHA-256, removes the
single generated NinjaScript tail, normalizes CRLF, and emits a candidate for a
real NT8 compile. Static preparation is not compilation or parity.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
import re

MARKER = "#region NinjaScript generated code"
LINE = re.compile(r"//[^\n]*")
BLOCK = re.compile(r"/\*.*?\*/", re.S)
STR = re.compile(r'"(?:[^"\\]|\\.)*"')
CHR = re.compile(r"'(?:[^'\\]|\\.)*'")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def load_artifact(path: str | Path, *, gzip_base64: bool = False) -> bytes:
    source = Path(path)
    manifest = None
    if source.suffix == ".json":
        manifest = json.loads(source.read_text(encoding="utf-8"))
        if manifest.get("format") != "gzip+base64-split-v1":
            raise ValueError("unsupported source manifest format")
        parts = manifest.get("parts")
        if not isinstance(parts, list) or not parts:
            raise ValueError("source manifest must list at least one part")
        chunks = []
        for part in parts:
            if not isinstance(part, str) or Path(part).name != part or Path(part).is_absolute():
                raise ValueError(f"unsafe source part path: {part!r}")
            chunks.append((source.parent / part).read_bytes().strip())
        data = b"".join(chunks)
        expected_encoded = manifest.get("encoded_sha256")
        if expected_encoded and sha256(data) != expected_encoded:
            raise ValueError("encoded source artifact sha256 mismatch")
        gzip_base64 = True
    else:
        data = source.read_bytes()
    if not gzip_base64:
        return data
    try:
        raw = gzip.decompress(base64.b64decode(data, validate=True))
    except Exception as exc:
        raise ValueError(f"invalid gzip+base64 source artifact: {exc}") from exc
    if manifest and manifest.get("raw_sha256") and sha256(raw) != manifest["raw_sha256"]:
        raise ValueError("decoded source artifact sha256 mismatch")
    return raw


def _without_literals(text: str) -> str:
    return STR.sub('""', CHR.sub("' '", BLOCK.sub(" ", LINE.sub(" ", text))))


def prepare_source(raw: bytes, *, expected_sha256: str, class_name: str) -> bytes:
    actual = sha256(raw)
    if actual != expected_sha256:
        raise ValueError(f"source sha256 mismatch: {actual} != {expected_sha256}")
    text = raw.decode("utf-8-sig")
    marker_count = text.count(MARKER)
    if marker_count != 1:
        raise ValueError(f"expected exactly one generated region marker, found {marker_count}")
    text = text.split(MARKER, 1)[0].rstrip("\r\n") + "\n"
    class_pattern = rf"class\s+{re.escape(class_name)}\s*:\s*Indicator\b"
    if len(re.findall(class_pattern, text)) != 1:
        raise ValueError(f"expected exactly one {class_name} : Indicator declaration")
    stripped = _without_literals(text)
    if stripped.count("{") != stripped.count("}"):
        raise ValueError("unbalanced braces after generated-tail removal")
    if stripped.count("(") != stripped.count(")"):
        raise ValueError("unbalanced parentheses after generated-tail removal")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
    prepared = normalized.encode("utf-8")
    if prepared.count(b"\n") != prepared.count(b"\r\n"):
        raise AssertionError("prepared source contains lone LF")
    return prepared


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--expected-sha256", required=True)
    ap.add_argument("--class-name", required=True)
    ap.add_argument("--output")
    ap.add_argument("--gzip-base64", action="store_true", help="decode deterministic gzip+base64 artifact")
    args = ap.parse_args(argv)
    raw = load_artifact(args.input, gzip_base64=args.gzip_base64)
    prepared = prepare_source(raw, expected_sha256=args.expected_sha256, class_name=args.class_name)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(prepared)
    print(f"raw_sha256={sha256(raw)}")
    print(f"prepared_sha256={sha256(prepared)}")
    print(f"prepared_bytes={len(prepared)}")
    print(f"output={args.output or '<check-only>'}")
    print("status=STATIC_PREPARED_NOT_COMPILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
