#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from edgelab.edge_brain.semantic_debt_resolver import resolve_corpus_graph


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve every CerebroSSRN missing relation destination without fuzzy fabrication")
    parser.add_argument("corpus_root")
    parser.add_argument("output_dir")
    args = parser.parse_args()
    summary = resolve_corpus_graph(args.corpus_root, args.output_dir)
    print(json.dumps(summary.__dict__, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
