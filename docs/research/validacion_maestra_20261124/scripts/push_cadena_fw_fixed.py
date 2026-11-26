import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\EdgeLab-fundedsync")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import fundedsync_cadena as fc

hasta = "20261123"
fin = (dt.date(int(hasta[:4]), int(hasta[4:6]), int(hasta[6:])) + dt.timedelta(days=1)).isoformat()
acta = dict(
    acta="docs/research/fundedsyncstack_20261115/PREREGISTRO_TANDA2.md",
    commit="c523d256",
    familia="FUNDEDSYNC",
    cid="FUNDEDSYNC::forward_TZR",
)

k = fc.construir()
txt = k.read_text(encoding="utf-8")
# Patch _s.__dict__ injection in construir output so paridad_vendedor resolves __file__ cleanly on Kaggle
old = "_s = types.ModuleType('edgelab.research.fundedsyncstack.paridad_vendedor');"
new = "_s = types.ModuleType('edgelab.research.fundedsyncstack.paridad_vendedor'); _s.__dict__['__file__'] = '/kaggle/src/edgelab/research/fundedsyncstack/paridad_vendedor.py';"
assert old in txt, "paridad_vendedor block not found"
txt = txt.replace(old, new, 1)

header = (
    "import os\n"
    "os.environ.update(SELLADO='1', HASTA=" + repr(hasta) + ", FIN=" + repr(fin)
    + ", FW_DESDE='2026-11-14', FW_ZBANDA='1', ACTA_JSON=" + repr(json.dumps(acta)) + ")\n"
)
out_script = Path(r"C:\Users\Usuario\.gemini\antigravity\brain\6d51dfbd-ecbb-4249-894c-b2e8b3258c4b\scratch\fundedsync_kernel_fw20261123.py")
out_script.write_text(header + txt, encoding="utf-8")
print("Wrote patched script:", out_script, out_script.stat().st_size, "bytes")

subprocess.run(
    [
        sys.executable,
        "tools/kaggle_kernel.py",
        "push",
        "--slug",
        f"{fc.KS}-fw{hasta}",
        "--title",
        f"edgelab fundedsync cadena fw{hasta}",
        "--script",
        str(out_script),
        "--dataset",
        "nicolasbuttaro/edgelab-sqx-m1",
        "--dataset",
        "nicolasbuttaro/edgelab-holdout-sellado",
    ],
    cwd=ROOT,
    check=True,
)
