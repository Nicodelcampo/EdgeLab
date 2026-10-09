#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from edgelab.edge_brain.bibliographic_cortex import SSRNBibliographicCortex


def main() -> int:
    parser = argparse.ArgumentParser(description="CerebroSSRN Bibliographic Cortex CLI")
    subs = parser.add_subparsers(dest="command", required=True)
    audit = subs.add_parser("audit")
    audit.add_argument("corpus_root")
    audit.add_argument("--config", default=str(ROOT / "config/edge_brain/ssrn_corpus_v1.json"))
    audit.add_argument("--archive")
    search = subs.add_parser("search")
    search.add_argument("corpus_root")
    search.add_argument("query")
    search.add_argument("-k", "--limit", type=int, default=6)
    search.add_argument("--max-chars", type=int, default=12000)
    ingest = subs.add_parser("ingest")
    ingest.add_argument("corpus_root")
    ingest.add_argument("ledger_path")
    ingest.add_argument("--created-at-utc", default="2026-09-21T13:00:00Z")
    ingest.add_argument("--overwrite", action="store_true")
    custody = subs.add_parser("custody-manifest")
    custody.add_argument("corpus_root")
    custody.add_argument("out_path")
    custody.add_argument("--archive-sha256", required=True)
    args = parser.parse_args()
    cortex = SSRNBibliographicCortex(args.corpus_root)
    if args.command == "audit":
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        result = asdict(cortex.audit(config["expected"]))
        if args.archive:
            observed = cortex.sha256_file(args.archive)
            result["archive_sha256"] = observed
            result["archive_hash_matches"] = observed == config["archive_sha256"]
            if not result["archive_hash_matches"]:
                result["status"] = "INCOMPLETE"
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] == "VERIFIED_COMPLETE" else 1
    if args.command == "search":
        print(json.dumps(cortex.context_pack(args.query, args.limit, args.max_chars), indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "ingest":
        result = cortex.ingest_ledger(args.ledger_path, created_at_utc=args.created_at_utc, overwrite=args.overwrite)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    manifest = cortex.custody_manifest(args.archive_sha256, "2026-09-21T13:00:00Z")
    Path(args.out_path).write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"papers": len(manifest["papers"]), "aggregate": manifest["papers_aggregate_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
