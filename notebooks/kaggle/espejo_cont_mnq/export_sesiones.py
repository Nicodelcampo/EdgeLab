"""Exporta la lista canónica de sesiones MNQ (descubrimiento) para el notebook de Kaggle. Correr localmente."""
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))
import tbz_e2 as TB  # noqa: E402
import tbzx_iter2 as T2  # noqa: E402

ss = [s for s in T2.canonical_sessions("MNQ") if s["trade_date"] <= TB.EXP_END]
files = {Path(s["path"]).name for s in ss}
print(len(ss), collections.Counter(s["contract"] for s in ss), files)
out = [dict(trade_date=s["trade_date"], contract=s["contract"], start=int(s["start"]), end=int(s["end"]),
            file=Path(s["path"]).name) for s in ss]
Path(__file__).with_name("sesiones_MNQ.json").write_text(
    json.dumps(dict(inst="MNQ", exp_end=TB.EXP_END, holdout_ns=int(TB.HOLDOUT_NS), sessions=out)), encoding="utf-8")
