"""Tablero del visor (simulacion visual) recalculado por contrato de NQ, mas la version realista de M11.
Visor: entrada en X, TP en A, SL 1/5 del TP, sin costos, sin tope de tiempo (hasta 20.000 velas 25t), misma vela -> SL.
Realista: entrada al cierre de la vela de marca -1 tick, comision 0,225, tope 240 min / fin de sesion (reglas de M11).
Uso: python tools/luximb_parity/luximb_dash_periodos.py <out.json> <bundle.json> [...]"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; REPO = HERE.parents[1]; sys.path.insert(0, str(HERE))
from luximb_m11 import sim  # noqa: E402
from luximb_outcomes import GAP_S, TOPE_MIN  # noqa: E402

TICK, COMM = 0.25, 0.225


def main():
    res = {}
    for bp in sys.argv[2:]:
        bp = Path(bp); ip = bp.with_name("imp_" + bp.name)
        subprocess.run([sys.executable, "-X", "utf8", str(HERE / "luximb_impulsos.py"), str(bp), str(ip), "--modo", "inicio", "--p-rango", "60",
                        "--min-ini", "3", "--share-ini", "0.5", "--rango-min-abs", "60"], check=True, cwd=REPO, capture_output=True)
        B = json.load(open(bp, encoding="utf-8")); I = json.load(open(ip, encoding="utf-8"))
        cl = np.array([x["close"] for x in B["bar_series"]["time_1m"]["candles"]]); T = B["bar_series"]["tick_25"]["candles"]
        t = np.array([x["time"] for x in T]); h = np.array([x["high"] for x in T]); l = np.array([x["low"] for x in T]); c = np.array([x["close"] for x in T])
        meta = B["meta"]; del B, T
        v = dict(n=0, TP=0, SL=0, abiertas=0, R=0.0, pts=0.0); r = dict(n=0, TP=0, SL=0, tiempo=0, pts=0.0)
        for ev in I["impulsos"]:
            s = 1 if ev["dir"] == "up" else -1; A, X = ev["p0"], ev["p1"]; d = abs(X - A); sl = X + s * d / 5
            i = int(np.searchsorted(t, ev["tc"], "left")); v["n"] += 1; res_v = "abierta"
            for k in range(i, min(len(t), i + 20000)):                       # reglas del visor
                if (h[k] >= sl if s > 0 else l[k] <= sl): res_v = "SL"; break
                if (l[k] <= A if s > 0 else h[k] >= A): res_v = "TP"; break
            if res_v == "TP": v["TP"] += 1; v["R"] += 5; v["pts"] += d
            elif res_v == "SL": v["SL"] += 1; v["R"] -= 1; v["pts"] -= d / 5
            else: v["abiertas"] += 1
            E = cl[ev["ic"]] - s * TICK; D = s * (E - A)                       # realista (M11, TP 1,0 / SL 0,2 / sin BE)
            if D <= 0: continue
            b = i
            while b < len(t) and t[b] <= ev["tc"] + TOPE_MIN * 60 and (b == i or t[b] - t[b - 1] <= GAP_S): b += 1
            ex, why = sim(s, E, A, E + s * 0.2 * D, None, h[i:b], l[i:b], c[i:b], TICK)
            r["n"] += 1; r[why] = r.get(why, 0) + 1; r["pts"] += -s * (ex - E) - COMM
        cc = v["TP"] + v["SL"]
        v.update(acierto=round(100 * v["TP"] / cc, 1) if cc else None, R_por_op=round(v["R"] / cc, 3) if cc else None, pts=round(v["pts"], 1))
        r.update(acierto=round(100 * r["TP"] / r["n"], 1) if r["n"] else None, pts=round(r["pts"], 1), pts_por_op=round(r["pts"] / r["n"], 2) if r["n"] else None)
        res[meta["id"]] = dict(contrato=meta["contract"], desde=meta.get("ventana_trade_date"), visor=v, realista=r)
        print(meta["id"], meta.get("ventana_trade_date"), "VISOR", v, "| REALISTA", r, flush=True)
    json.dump(res, open(sys.argv[1], "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
