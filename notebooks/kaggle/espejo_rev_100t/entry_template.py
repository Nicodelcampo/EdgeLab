"""ESPEJO-REV-100T en {INST} (lucid), Kaggle. Pedido de Nico 28/09.
Manifiesto: docs/research/MANIFIESTO_ESPEJO_REV_100T_20260928.md. Código: dataset edgelab-code-20260928
(commit en CODE_COMMIT.txt). Velas 25t con `tbzx_iter2._bars_session` (mismo código que local) → 100t en el runner.
Los 5 niveles corren en paralelo; al final, reporte del instrumento (máximo estadístico sobre todas sus celdas).
"""
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

INST = "{INST}"
CODE = next(p for p in Path("/kaggle/input").rglob("CODE_COMMIT.txt")).parent
sys.path.insert(0, str(CODE)); sys.path.insert(0, str(CODE / "tools"))
SES = json.loads((CODE / "sesiones" / f"sesiones_{INST}.json").read_text(encoding="utf-8"))
FILES = {p.name: p for p in Path("/kaggle/input").rglob("*.parquet") if p.name.startswith(INST + "_")}
W = Path("/kaggle/working"); BARS = W / f"bars_{INST}"; OUT = W / "out"

import tbzx_iter2 as T2  # noqa: E402
import espejo_rev_100t as E0  # noqa: E402
E_CFG = list(E0.CONFIGS[INST])

T2.bars_dir = lambda inst: BARS


def build_one(s):
    return T2._bars_session((INST, dict(trade_date=s["trade_date"], path=str(FILES[s["file"]]), contract=s["contract"],
                                         start=s["start"], end=s["end"])))


def run_level(n):
    import espejo_rev_100t as E
    t0 = time.time(); E.run(INST, n, BARS, OUT); return n, round(time.time() - t0)


if __name__ == "__main__":
    t0 = time.time(); BARS.mkdir(parents=True, exist_ok=True)
    faltan = [s["file"] for s in SES["sessions"] if s["file"] not in FILES]
    print(INST, SES["fuente"], "sesiones", len(SES["sessions"]), "archivos faltantes", sorted(set(faltan)), flush=True)
    ss = [s for s in SES["sessions"] if s["file"] in FILES]
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        st = list(ex.map(build_one, ss))
    print("velas", {k: sum(1 for _, x in st if x == k) for k in {x for _, x in st}}, round(time.time() - t0), "s", flush=True)
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        for n, secs in ex.map(run_level, list(E_CFG)):
            print("nivel", n, "listo", secs, "s", flush=True)
    import espejo_rev_100t as E
    E.report(OUT)
    print("total", round(time.time() - t0), "s")
