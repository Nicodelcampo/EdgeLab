"""One-shot operational diagnostic: no datasets, network, secrets or research."""
import json
import platform
from pathlib import Path


def main():
    root = Path("/kaggle/working")
    if not root.is_dir():
        raise RuntimeError("Kaggle environment required; do not execute on host")
    result = {
        "schema": "edgelab_execution_canary_v1",
        "status": "MINIMAL_PYTHON_EXECUTION_OK",
        "python_version": platform.python_version(),
        "market_data_read": False,
        "network_calls_made": 0,
        "signed_urls_used": False,
        "outcomes_computed": False,
        "pnl_computed": False,
        "audit_payload_executed": False,
        "diagnostic_scope": "Kaggle script execution only; not the blocked transport preparation",
    }
    dest = root / "diagnostic"
    dest.mkdir(exist_ok=True)
    (dest / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()