#!/usr/bin/env python3
r"""Bundle de velas Nt a partir de un bundle 25t, agrupando de a k velas DENTRO de cada sesión (como el 100t del visor).

    python tools/agregar_velas.py --src MNQ_03-26_202602_25T_HFT --k 6     # → MNQ_03-26_202602_150T
"""
import argparse
import json
from pathlib import Path

VIEW = Path(__file__).resolve().parents[1] / "viewer" / "nt8_bridge" / "bundles"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--src", required=True); ap.add_argument("--k", type=int, required=True); a = ap.parse_args()
    b = json.loads((VIEW / f"{a.src}.json").read_text(encoding="utf-8"))
    man = json.loads((VIEW / f"{a.src}.manifest.json").read_text(encoding="utf-8"))
    c = b["bar_series"]["tick_25"]["candles"]
    out, i = [], 0
    for s in man["sessions"]:
        n = int(s["tick25_bars"]); seg = c[i:i + n]; i += n
        for j in range(0, len(seg), a.k):
            g = seg[j:j + a.k]
            out.append(dict(time=g[0]["time"], open=g[0]["open"], high=max(x["high"] for x in g), low=min(x["low"] for x in g),
                            close=g[-1]["close"], volume=sum(x.get("volume", 0) for x in g)))
    assert i == len(c)
    nt = 25 * a.k; base = a.src.rsplit("_25T", 1)[0]; aid = f"{base}_{nt}T"
    meta = {k: v for k, v in b["meta"].items() if not isinstance(v, (list, dict))}
    meta.update(id=aid, n_zones=0, derived_from=a.src, aggregation=f"{a.k}x25t por sesion")
    (VIEW / f"{aid}.json").write_text(json.dumps(dict(meta=meta, bar_series={f"tick_{nt}": dict(candles=out)}, runs=[]), separators=(",", ":")), encoding="utf-8")
    sm = dict(man); sm["asset_id"] = aid; sm["sessions"] = [dict(s, tick25_bars=int(s["tick25_bars"]), **{f"tick{nt}_bars": -(-int(s["tick25_bars"]) // a.k)}) for s in man["sessions"]]
    (VIEW / f"{aid}.manifest.json").write_text(json.dumps(sm), encoding="utf-8")
    print(aid, len(out))


if __name__ == "__main__":
    main()
