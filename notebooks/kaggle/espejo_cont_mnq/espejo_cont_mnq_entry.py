"""ESPEJO-CONT-TPSL en MNQ 25t (configuraciones C3N4 y C3N5) corrido en Kaggle con los datos de Lucid.

Pre-registro: docs/research/MANIFIESTO_ESPEJO_CONTINUACION_TPSL_20260928.md (enmienda 1), OK de Nico 28/09.
Mismo código que local (dataset privado edgelab-code-20260928, commit en CODE_COMMIT.txt); sólo cambian rutas:
- velas 25t: `tbzx_iter2._bars_session` sobre `edgelab-ticks-mnq-preholdout` (Lucid, pre-holdout), sesiones canónicas
  exportadas localmente (`sesiones_MNQ.json`, descubrimiento ≤ 2026-03-31);
- salidas en /kaggle/working.
"""
import json
import os
import sys
import time
import types
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

CODE = next(p for p in Path("/kaggle/input").rglob("CODE_COMMIT.txt")).parent
sys.path.insert(0, str(CODE)); sys.path.insert(0, str(CODE / "tools"))
TICKS = next(p for p in Path("/kaggle/input").rglob("MNQ_03-26_ticks.parquet")).parent
SES = json.loads(next(p for p in Path("/kaggle/input").rglob("sesiones_MNQ.json")).read_text(encoding="utf-8")) \
    if list(Path("/kaggle/input").rglob("sesiones_MNQ.json")) else json.loads(Path(__file__).with_name("sesiones_MNQ.json").read_text())
W = Path("/kaggle/working")
BARS = W / "bars_MNQ"

import tbz_e2 as TB  # noqa: E402
import tbzx_iter2 as T2  # noqa: E402


def sessions(inst):
    return [dict(trade_date=s["trade_date"], path=str(TICKS / s["file"]), contract=s["contract"], start=s["start"], end=s["end"])
            for s in SES["sessions"]]


T2.bars_dir = lambda inst: BARS
T2.canonical_sessions = sessions


def build_one(s):
    return T2._bars_session(("MNQ", s))


def run_config(cfg):
    import espejo_cont_tpsl as E
    E.T2.bars_dir = lambda inst: BARS
    E.T2.canonical_sessions = sessions
    E.OUT = W / "cont_tpsl"
    commit = (CODE / "CODE_COMMIT.txt").read_text().strip()
    E.subprocess = types.SimpleNamespace(run=lambda *a, **k: types.SimpleNamespace(stdout=commit if "rev-parse" in a[0] else ""))
    sys.argv = ["espejo_cont_tpsl.py", "--config", cfg]
    t0 = time.time(); E.main(); return cfg, round(time.time() - t0)


if __name__ == "__main__":
    t0 = time.time(); BARS.mkdir(parents=True, exist_ok=True)
    ss = sessions("MNQ")
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        st = list(ex.map(build_one, ss))
    print("velas", len(ss), "sesiones", {k: sum(1 for _, x in st if x == k) for k in {x for _, x in st}}, round(time.time() - t0), "s", flush=True)
    with ProcessPoolExecutor(max_workers=2) as ex:
        for cfg, secs in ex.map(run_config, ["C3N4", "C3N5"]):
            print("listo", cfg, secs, "s", flush=True)
    print("total", round(time.time() - t0), "s")
