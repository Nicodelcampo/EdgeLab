"""REGLA CONGELADA para el holdout (>= 2026-10-01): fade "fin de caja -> inicio de zona" de LUX-IMB en NQ.
Candidato: docs/research/luximb_parity_20261020/CANDIDATO_HOLDOUT_REGLA_VISOR_NQ_20261021.md. NO MODIFICAR: cualquier
cambio invalida la apertura (la regla debe ser identica a la congelada; el sha256 de este archivo esta en el candidato).

Regla:
- Impulsos: luximb_impulsos.py --modo inicio --p-rango 60 --min-ini 3 --share-ini 0.5 --rango-min-abs 60 (detector con el
  fix de supervivencia del 21/10). Zonas LUX-IMB OG+VI M1, vida 500 min.
- Entrada: cierre de la vela M1 de confirmacion, 1 tick en contra. Direccion: en contra del impulso (hacia A).
- TP = A (inicio de la zona), orden limite sin slippage. SL = entrada + 1/5 de la distancia entrada-A (del otro lado), +1 tick.
- Sin break even. Tope 240 min o fin de sesion (hueco > 30 min): cierre al ultimo precio +1 tick.
- Simulacion en velas 25t desde la primera vela con hora >= cierre de la confirmacion; misma vela SL y TP -> SL.
- Costos NQ: $4,50 RT = 0,225 pts.

Uso: python tools/luximb_parity/luximb_holdout_regla_visor.py <out.json> <bundle_holdout.json> [...]
(los bundles deben contener SOLO sesiones >= 2026-10-01; se verifica).
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; REPO = HERE.parents[1]; sys.path.insert(0, str(HERE))
from luximb_m11 import sim  # noqa: E402
from luximb_outcomes import GAP_S, TOPE_MIN  # noqa: E402

TICK, COMM, F_SL = 0.25, 0.225, 0.2
HOLDOUT_DESDE = int(pd.Timestamp("2026-10-01", tz="America/Chicago").value // 10**9) - 7 * 3600   # sesion CME del 1-oct
ARGS_IMP = ["--modo", "inicio", "--p-rango", "60", "--min-ini", "3", "--share-ini", "0.5", "--rango-min-abs", "60"]
NB = 10000


def main():
    rows = []
    for bp in map(Path, sys.argv[2:]):
        B = json.load(open(bp, encoding="utf-8"))
        cd = B["bar_series"]["time_1m"]["candles"]
        if cd[0]["time"] < HOLDOUT_DESDE: raise SystemExit(f"{bp.name}: contiene datos anteriores al holdout")
        ip = bp.with_name("holdout_imp_" + bp.name)
        subprocess.run([sys.executable, "-X", "utf8", str(HERE / "luximb_impulsos.py"), str(bp), str(ip)] + ARGS_IMP, check=True, cwd=REPO, capture_output=True)
        I = json.load(open(ip, encoding="utf-8")); cl = np.array([x["close"] for x in cd]); T = B["bar_series"]["tick_25"]["candles"]
        t = np.array([x["time"] for x in T]); h = np.array([x["high"] for x in T]); l = np.array([x["low"] for x in T]); c = np.array([x["close"] for x in T])
        del B, T, cd
        for ev in I["impulsos"]:
            s = 1 if ev["dir"] == "up" else -1; A = ev["p0"]; E = cl[ev["ic"]] - s * TICK; D = s * (E - A)
            if D <= 0: continue
            i = int(np.searchsorted(t, ev["tc"], "left")); b = i
            while b < len(t) and t[b] <= ev["tc"] + TOPE_MIN * 60 and (b == i or t[b] - t[b - 1] <= GAP_S): b += 1
            ex, why = sim(s, E, A, E + s * F_SL * D, None, h[i:b], l[i:b], c[i:b], TICK)
            rows.append(dict(dia=str(pd.Timestamp(ev["tc"], unit="s", tz="UTC").tz_convert("America/New_York").date()), pnl=-s * (ex - E) - COMM, why=why))
    df = pd.DataFrame(rows); rng = np.random.default_rng(20261021)
    days = df.dia.unique(); ix = {k: np.flatnonzero(df.dia.values == k) for k in days}; v = df.pnl.values
    bs = np.array([v[np.concatenate([ix[k] for k in rng.choice(days, len(days))])].mean() for _ in range(NB)])
    out = dict(n=len(df), dias=len(days), media_pts=round(float(v.mean()), 3), ic95=[round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)],
               p_unilateral=float(np.mean(bs <= 0)), acierto=round(float((df.why == "TP").mean()), 3), por_motivo=df.why.value_counts().to_dict(),
               pf=round(float(v[v > 0].sum() / -v[v < 0].sum()), 3) if (v < 0).any() else None)
    out["veredicto"] = "CONFIRMA" if (out["n"] >= 150 and out["ic95"][0] > 0) else ("REFUTA" if out["n"] >= 150 and out["media_pts"] <= 0 else "NO_CONCLUYENTE")
    json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), indent=1, default=str); print(json.dumps(out, default=str))


if __name__ == "__main__":
    main()
