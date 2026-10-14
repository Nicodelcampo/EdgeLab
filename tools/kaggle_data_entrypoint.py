#!/usr/bin/env python3
"""Offline Kaggle dataset discovery; no secret handling or research approval."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.kaggle.discovery import main

if __name__ == '__main__':
    raise SystemExit(main())
