"""NQ-CRUCE25-CLIMA (pre-registro docs/research/MANIFIESTO_NQ_CRUCE25_POR_CLIMA_L2_20260929.md). NO LANZAR sin auditoría.
Velas 25t desde los ticks NT8 de NQ jul–sep (catálogo NQ_ext_2026q3) con el mismo código; luego tools/nq_cruce25_clima.py."""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

CODE = next(p for p in Path("/kaggle/input").rglob("CODE_COMMIT.txt")).parent
sys.path.insert(0, str(CODE)); sys.path.insert(0, str(CODE / "tools"))
DATA = next(p for p in Path("/kaggle/input").rglob("l2_contexts_NQ_labels.parquet")).parent
CAT = json.loads(next(DATA.rglob("NQ_ext_2026q3_sessions_catalog.json")).read_text(encoding="utf-8"))
FILES = {p.name: p for p in DATA.rglob("*_ticks_ext.parquet")}
W = Path("/kaggle/working"); BARS = W / "bars_NQ"
import tbzx_iter2 as T2  # noqa: E402
T2.bars_dir = lambda inst: BARS


def build_one(s):
    return T2._bars_session(("NQ", dict(trade_date=s["trade_date"], path=str(FILES[Path(s["path"]).name]), contract=s["contract"],
                                        start=int(s["start"]), end=int(s["end"]))))


if __name__ == "__main__":
    import tbz_e2 as TB
    TB.HOLDOUT_NS = 1790805600000000000          # A3: jul–sep es desarrollo; el holdout arranca en la sesión del 1-oct
    BARS.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        st = list(ex.map(build_one, CAT["sessions"]))
    print("velas", {k: sum(1 for _, x in st if x == k) for k in {x for _, x in st}}, flush=True)
    sys.argv = ["nq_cruce25_clima.py", "--bars", str(BARS), "--labels", str(DATA / "l2_contexts_NQ_labels.parquet"), "--out", str(W / "out")]
    import nq_cruce25_clima as R
    R.main()
