#!/usr/bin/env python3
"""Corre tests estilo pytest (funciones a nivel de modulo) sin pytest instalado.

El repo tiene 134 archivos con `def test_` a nivel de modulo y solo 3 con
unittest.TestCase. `python3 -m unittest` recolecta CERO de esos 134, asi que no
sirve como puerta de verificacion. Este runner los ejecuta de verdad.

Uso: python3 run_pytest_style.py <ROOT> <archivo_de_test> [...]
"""
import importlib.util
import inspect
import sys
import traceback
from pathlib import Path


def run_file(root: Path, path: Path):
    results = []
    name = "t_" + path.stem
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        return [(path.name, "<import>", "ERROR", "no loader")]
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        return [(path.name, "<import>", "ERROR", traceback.format_exc(limit=3))]
    for attr in sorted(dir(module)):
        if not attr.startswith("test_"):
            continue
        fn = getattr(module, attr)
        if not callable(fn):
            continue
        try:
            params = inspect.signature(fn).parameters
        except (TypeError, ValueError):
            params = {}
        required = [
            p for p in params.values()
            if p.default is inspect.Parameter.empty
            and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
        ]
        if required:
            results.append((path.name, attr, "SKIP_FIXTURES", ",".join(p.name for p in required)))
            continue
        try:
            fn()
            results.append((path.name, attr, "PASS", ""))
        except Exception:
            results.append((path.name, attr, "FAIL", traceback.format_exc(limit=4)))
    return results


def main(argv):
    root = Path(argv[0]).resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    all_results = []
    for raw in argv[1:]:
        all_results.extend(run_file(root, Path(raw).resolve()))
    counts = {"PASS": 0, "FAIL": 0, "ERROR": 0, "SKIP_FIXTURES": 0}
    for _file, _test, status, _detail in all_results:
        counts[status] = counts.get(status, 0) + 1
    for file_name, test_name, status, detail in all_results:
        if status in ("FAIL", "ERROR"):
            print("=" * 70)
            print(status, file_name + "::" + test_name)
            print(detail)
    for file_name, test_name, status, detail in all_results:
        if status == "SKIP_FIXTURES":
            print("SKIP_FIXTURES", file_name + "::" + test_name, "needs:", detail)
    print("-" * 70)
    print("collected", len(all_results), counts)
    return 0 if counts["FAIL"] == 0 and counts["ERROR"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
