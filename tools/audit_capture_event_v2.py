"""CLI mínima para auditar un TSV de CaptureEventProbeV2."""
from __future__ import annotations

import argparse

from edgelab.data.capture_tsv import CaptureTsvError, audit_capture_tsv


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audita transporte y schema de captura NT8")
    parser.add_argument("tsv", help="ruta al capture_event_v2*.tsv")
    args = parser.parse_args(argv)
    try:
        report = audit_capture_tsv(args.tsv)
    except (OSError, CaptureTsvError) as exc:
        parser.error(str(exc))
    print(report.to_json())
    return 0 if report.transport_ok and report.schema_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
