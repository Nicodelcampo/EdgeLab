#!/usr/bin/env python3
r"""Bundle liviano para ver espejos en el visor (28/09, pedido de Nico): toma un bundle mensual de 25t y conserva las
últimas sesiones completas hasta ~MAX_BARS velas, sin zonas HFT. El visor calcula los espejos en el navegador y deriva
las velas de 100t (4 × 25t por sesión) a partir de las de 25t. Sólo visualización (target-free).

    .venv\Scripts\python tools\build_espejo_slice_bundle.py NQ_03-26_202602_25T_HFT YM_03-26_202602_25T_HFT
"""
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
B = REPO / "viewer" / "nt8_bridge" / "bundles"
MANIFEST = B / "manifest.js"
MAX_BARS = 100_000


def build(src_id):
    b = json.loads((B / f"{src_id}.json").read_text(encoding="utf-8"))
    cd = b["bar_series"]["tick_25"]["candles"]
    t = np.array([c["time"] for c in cd])
    starts = np.r_[0, np.flatnonzero(np.diff(t) > 1800) + 1]
    keep = len(cd)
    for s in starts[::-1]:
        if len(cd) - s > MAX_BARS:
            break
        keep = s
    sl = cd[keep:]
    inst, contract = b["meta"]["instrument"], b["meta"]["contract"]
    new_id = src_id.replace("_25T_HFT", "_ESPEJO")
    meta = dict(b["meta"]); meta["id"] = new_id; meta["n_zones"] = 0
    meta.setdefault("precision", 2); meta["name"] = f"{contract} · Espejo (25t / 100t)"
    meta["nota"] = f"recorte para ver espejos: últimas sesiones de {src_id} ({len(sl)} velas 25t)"
    out = dict(meta=meta, bar_series={"tick_25": dict(kind="tick_25", name="25 Tick (Micro Sesión)", candles=sl)}, runs=[])
    (B / f"{new_id}.json").write_text(json.dumps(out), encoding="utf-8")
    entry = dict(id=new_id, name=f"{contract} · Espejo (25t / 100t) · {src_id[-12:-8]}", group=f"{inst} (Espejo Impulsos)",
                 instrument=inst, contract=contract, tick_size=b["meta"]["tick_size"], precision=b["meta"].get("precision", 2),
                 candles=len(sl), zones=0, rolls=0, parity_status="PARITY_ABSTAIN")
    content = MANIFEST.read_text(encoding="utf-8")
    if f'"{new_id}"' not in content:
        head = "window.ASSET_CATALOG = [\n"; i = content.find(head) + len(head)
        content = content[:i] + "  " + json.dumps(entry, indent=2, ensure_ascii=False).replace("\n", "\n  ") + ",\n" + content[i:]
        MANIFEST.write_text(content, encoding="utf-8")
    print(new_id, len(sl), "velas 25t", "desde", t[keep], "sesiones", int(np.sum(starts >= keep)))


if __name__ == "__main__":
    for a in sys.argv[1:]:
        build(a)
