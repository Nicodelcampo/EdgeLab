"""Control empírico del nulo de CONT/REV — caso GC_rev_W100 (GC, Lucid). Pedido de Nico 28/09. Código: tools/espejo_null_control.py."""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

INST, CASE = "GC", "GC_rev_W100"
CODE = next(p for p in Path("/kaggle/input").rglob("CODE_COMMIT.txt")).parent
sys.path.insert(0, str(CODE)); sys.path.insert(0, str(CODE / "tools"))
SES = json.loads((CODE / "sesiones" / f"sesiones_GC.json").read_text(encoding="utf-8"))
FILES = {p.name: p for p in Path("/kaggle/input").rglob("*.parquet") if p.name.startswith(INST + "_")}
W = Path("/kaggle/working"); BARS = W / f"bars_GC"
import tbzx_iter2 as T2  # noqa: E402
T2.bars_dir = lambda inst: BARS


def build_one(s):
    return T2._bars_session((INST, dict(trade_date=s["trade_date"], path=str(FILES[s["file"]]), contract=s["contract"], start=s["start"], end=s["end"])))


if __name__ == "__main__":
    BARS.mkdir(parents=True, exist_ok=True)
    ss = [s for s in SES["sessions"] if s["file"] in FILES]
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        st = list(ex.map(build_one, ss))
    print("velas", {k: sum(1 for _, x in st if x == k) for k in {x for _, x in st}}, flush=True)
    import espejo_null_control as E
    E.run(CASE, BARS, W / "out")
