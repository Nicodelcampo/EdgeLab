#!/usr/bin/env python3
"""Read-only repository navigation. No market data, network or module imports."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "component_registry.json"
CATEGORIES = {"core", "experimental", "campaign", "integration_pending", "historical", "planned"}
LOCATIONS = {"local", "other_branch", "not_pushed"}
REQUIRED = {"id", "name", "purpose", "category", "location", "paths", "inputs", "outputs", "dependencies", "limitations", "entrypoint", "related_prs", "certification"}

def validate(data, root):
    errors = []
    if data.get("schema_version") != 1:
        errors.append("Unsupported schema_version")
    modules = data.get("modules")
    if not isinstance(modules, list) or not modules:
        return errors + ["modules must be a nonempty list"]
    seen = set()
    for m in modules:
        if not isinstance(m, dict):
            errors.append("Module must be an object")
            continue
        ident = m.get("id", "<missing>")
        if not isinstance(ident, str) or not ident or ident in seen:
            errors.append("Invalid or duplicate module id")
        if isinstance(ident, str):
            seen.add(ident)
        if REQUIRED - m.keys():
            errors.append(f"{ident}: missing fields")
        for key in ("name", "purpose", "certification"):
            if not isinstance(m.get(key), str) or not m[key].strip():
                errors.append(f"{ident}: {key} must be nonempty text")
        if m.get("category") not in CATEGORIES:
            errors.append(f"{ident}: invalid category")
        if m.get("location") not in LOCATIONS:
            errors.append(f"{ident}: invalid location")
        for key in ("paths", "inputs", "outputs", "dependencies", "limitations"):
            value = m.get(key)
            if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
                errors.append(f"{ident}: invalid {key}")
        if not isinstance(m.get("related_prs"), list) or any(type(n) is not int or n < 1 for n in m.get("related_prs", [])):
            errors.append(f"{ident}: invalid related_prs")
        if m.get("entrypoint") is not None and not isinstance(m["entrypoint"], str):
            errors.append(f"{ident}: invalid entrypoint")
        paths = m.get("paths", [])
        if m.get("location") == "local" and not paths:
            errors.append(f"{ident}: local module needs paths")
        if isinstance(paths, list):
            for path in paths:
                if not isinstance(path, str):
                    continue
                candidate = (root / path).resolve()
                if Path(path).is_absolute() or not candidate.is_relative_to(root.resolve()):
                    errors.append(f"{ident}: path escapes repository")
                elif m.get("location") == "local" and not candidate.exists():
                    errors.append(f"{ident}: missing local path {path}")
    return errors

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("list", "show", "check"))
    parser.add_argument("module_id", nargs="?")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    if args.command == "show" and not args.module_id:
        parser.error("show requires module_id")
    if args.command != "show" and args.module_id:
        parser.error("module_id is only valid for show")
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        errors = validate(data, ROOT)
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False))
        return 2
    if errors:
        print(json.dumps({"status": "BLOCKED", "errors": errors}, ensure_ascii=False, indent=2))
        return 2
    if args.command == "check":
        result = {"status": "PASS_NAVIGATION_ONLY", "module_count": len(data["modules"]), "snapshot_date": data["snapshot_date"], "research_authorized": False, "runtime_tested": False, "data_read": False}
    elif args.command == "show":
        result = next((m for m in data["modules"] if m["id"] == args.module_id), None)
        if result is None:
            print(json.dumps({"status": "BLOCKED", "error": "Unknown module id"}))
            return 2
    else:
        result = [{k: m[k] for k in ("id", "name", "category", "location")} for m in data["modules"]]
    if args.as_json or args.command == "check":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "list":
        for m in result:
            print(f"{m['id']:20} {m['location']:14} {m['category']:20} {m['name']}")
    else:
        for key, value in result.items():
            print(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
