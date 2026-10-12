#!/usr/bin/env python3
"""Chequeo previo al arranque del autopilot en el Debian (solo lectura). Sale con 0 si todo lo imprescindible está bien.
  python tools/autopilot_doctor.py --config /etc/edgelab/autopilot.json [--root /var/lib/edgelab-autopilot/state/autopilot_runs]"""
import argparse, json, os, shutil, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
R = []
def chk(name, ok, detail="", fatal=True): R.append((name, ok, detail, fatal)); print(("PASS " if ok else ("FAIL " if fatal else "WARN ")) + name + (f": {detail}" if detail else ""))
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--config", required=True); ap.add_argument("--root"); a = ap.parse_args()
    chk("python>=3.10", sys.version_info >= (3, 10), sys.version.split()[0])
    for m in ("numpy", "pandas", "pyarrow", "scipy"):
        try: __import__(m); chk(f"import {m}", True)
        except Exception as e: chk(f"import {m}", False, str(e))
    try: cfg = json.loads(Path(a.config).read_text()); chk("config JSON", True)
    except Exception as e: chk("config JSON", False, str(e)); return fin()
    chk("modo", cfg.get("mode") in ("propose", "execute"), cfg.get("mode"))
    for k in ("registry", "evidence_runtime", "brain_ledger"):
        p = cfg.get(k); chk(f"{k} escribible", bool(p) and os.access(Path(p).parent if Path(p).parent.exists() else ".", os.W_OK), str(p), fatal=False)
    prot = cfg.get("protected"); 
    if prot:
        from edgelab.autopilot.guard import check_protected
        bad = check_protected(Path(prot), ROOT); chk("archivos protegidos sin cambios", not bad, "; ".join(bad[:3]))
    st = subprocess.run(["git", "status", "--porcelain", "--", "tools", "edgelab", "config"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    chk("código del repo limpio (lo lanzado queda atado a un commit)", not st, st[:120], fatal=False)
    chk("git", bool(shutil.which("git"))); chk("curl", bool(shutil.which("curl")))
    netrc = Path.home() / ".netrc"; chk("credencial de Kaggle (~/.netrc 0600 o KAGGLE_KEY)", (netrc.exists() and oct(netrc.stat().st_mode)[-3:] == "600" and "kaggle.com" in netrc.read_text()) or bool(os.environ.get("KAGGLE_KEY")), "")
    r = subprocess.run(["curl", "-sS", "-m", "30", "-o", "/dev/null", "-w", "%{http_code}", "https://www.kaggle.com/api/v1/kernels/list?user=nicolasbuttaro&pageSize=1"], capture_output=True, text=True)
    chk("API de Kaggle responde con credencial", r.stdout.strip() == "200", "HTTP " + r.stdout.strip())
    kill = Path(cfg.get("kill_switch", "PAUSE")); chk("kill switch no activo", not kill.exists(), str(kill), fatal=False)
    if a.root and (Path(a.root) / "heartbeat.json").exists():
        import time; hb = json.loads((Path(a.root) / "heartbeat.json").read_text()); age = time.time() - hb["ts"]; chk("latido reciente (< 30 min)", age < 1800, f"{age:.0f} s", fatal=False)
    fin()
def fin():
    bad = [n for n, ok, _, f in R if not ok and f]; print("\nRESULTADO:", "LISTO" if not bad else "FALTA: " + ", ".join(bad)); sys.exit(1 if bad else 0)
if __name__ == "__main__":
    main()
