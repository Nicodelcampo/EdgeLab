r"""Bundle de velas de N·25 ticks a partir del bundle de 25t (IPC macro, etiquetado).

Cada vela de 25t tiene exactamente 25 ticks y el constructor reinicia por sesión, así que
agrupar `mult` velas consecutivas dentro de cada sesión da exactamente velas de 25·mult ticks
(la última de cada sesión queda parcial, igual que en el constructor nativo). Sesión = hueco
de ≥ 45 min entre velas (pausa diaria CME). Sin zonas: es para etiquetar.

    .venv\Scripts\python tools\build_agg_tick_bundle.py --asset ES_03-26_202601_25T_HFT --mult 20
"""
import argparse
import json
from pathlib import Path

VIEW = Path(__file__).resolve().parents[1] / "viewer" / "nt8_bridge"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", required=True)
    ap.add_argument("--mult", type=int, default=20)
    a = ap.parse_args()
    src = json.loads((VIEW / "bundles" / f"{a.asset}.json").read_text(encoding="utf-8"))
    c25 = src["bar_series"]["tick_25"]["candles"]
    n_t = 25 * a.mult; key = f"tick_{n_t}"
    out, grp, sessions = [], [], 1

    def flush():
        if grp:
            out.append({"time": grp[-1]["time"], "open": grp[0]["open"], "high": max(g["high"] for g in grp),
                        "low": min(g["low"] for g in grp), "close": grp[-1]["close"], "volume": sum(g["volume"] for g in grp)})
            grp.clear()
    prev = None
    for c in c25:
        if prev is not None and c["time"] - prev >= 45 * 60:
            flush(); sessions += 1
        grp.append(c); prev = c["time"]
        if len(grp) == a.mult:
            flush()
    flush()
    aid = a.asset.replace("_25T_HFT", f"_{n_t}T")
    meta = dict(src["meta"], id=aid, n_zones=0, derived_from=a.asset, aggregation=f"{a.mult}x25t por sesion")
    bundle = {"meta": meta, "bar_series": {key: {"kind": key, "name": f"{n_t} Tick", "candles": out}},
              "runs": [{"id": f"none_{aid}", "name": f"sin zonas · {n_t} Tick", "bar_key": key, "zones": []}]}
    (VIEW / "bundles" / f"{aid}.json").write_text(json.dumps(bundle, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"asset": aid, "candles": len(out), "sessions": sessions, "por_sesion": round(len(out) / sessions)}))


if __name__ == "__main__":
    main()
