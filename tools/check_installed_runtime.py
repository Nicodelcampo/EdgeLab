"""Installed-wheel import smoke. No market-data read; run outside source tree."""
import importlib
import importlib.metadata
import json
from pathlib import Path

MODULES = ("edgelab.engine", "edgelab.config", "edgelab.bridge.ticks", "edgelab.bridge.store", "edgelab.bridge.kernels.bigtrap2_port", "edgelab.bridge.indicators.hftzones_universal", "edgelab.data.nt8_contract", "edgelab.edge_brain.hippocampus_store", "edgelab.funnel.runner", "validation.harness")


def main():
    roots = []
    for name in MODULES:
        module = importlib.import_module(name)
        roots.append({"module": name, "path": str(Path(module.__file__).resolve())})
    from edgelab.bridge.indicators import hftzones_universal
    profile = Path(hftzones_universal.__file__).with_name("hftzones_universal_profiles.json")
    if not profile.is_file() or not isinstance(json.loads(profile.read_text()), dict):
        raise RuntimeError("Missing or invalid packaged indicator profiles")
    print(json.dumps({"status": "PASS_INSTALLED_IMPORTS_ONLY", "version": importlib.metadata.version("edgelab"), "imports": roots, "profiles_present": True, "research_authorized": False}, indent=2))

if __name__ == "__main__":
    main()
