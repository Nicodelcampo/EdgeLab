"""M8 — variables de franjas (adelante / interior / atras) por vida de zona + contexto + desenlaces, por impulso.
Reglas: docs/research/luximb_parity_20261020/MANIFIESTO_M8_FRANJAS_DESBALANCE_LUXIMB_20261020.md (no cambiar sin enmienda).
Uso: python tools/luximb_parity/luximb_m8_features.py <out.csv> <INSTR>:<bundle.json>:<impulsos.json> [...]
"""
from __future__ import annotations

import sys
from pathlib import Path

import json
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from luximb_outcomes import REP_START, carrera  # noqa: E402

VIDAS = (100, 200, 500, 1000)


def main():
    out = sys.argv[1]; rows = []
    for trip in sys.argv[2:]:
        inst, bpath, ipath = trip.split(":", 2)
        B = json.load(open(bpath, encoding="utf-8")); I = json.load(open(ipath, encoding="utf-8"))
        cd = B["bar_series"]["time_1m"]["candles"]
        t = np.array([c["time"] for c in cd]); h = np.array([c["high"] for c in cd]); l = np.array([c["low"] for c in cd]); cl = np.array([c["close"] for c in cd])
        idx = {int(x): i for i, x in enumerate(t)}
        Z = B["runs"][0]["zones"]
        zi = np.array([idx[z["available_ts"] - 60] for z in Z]); zmid = np.array([(z["top"] + z["bottom"]) / 2 for z in Z])
        zog = np.array(["OG" in z["kind"] for z in Z]); zbull = np.array(["BULL" in z["kind"] for z in Z])
        T25 = B["bar_series"]["tick_25"]["candles"]
        t25 = np.array([c["time"] for c in T25]); h25 = np.array([c["high"] for c in T25]); l25 = np.array([c["low"] for c in T25]); c25 = np.array([c["close"] for c in T25])
        del B, T25, cd
        pc = np.r_[cl[0], cl[:-1]]; tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
        for ev in I["impulsos"]:
            if ev["tc"] >= REP_START: raise SystemExit("evento fuera de descubrimiento")
            kb = ev["ic"]; s = 1 if ev["dir"] == "up" else -1; A, X = ev["p0"], ev["p1"]; R = abs(X - A)
            if R <= 0: continue
            a25 = int(np.searchsorted(t25, ev["tc"], "left")); p25 = int(np.searchsorted(t25, ev["tc"] - 3600, "left"))
            vol_pre = float(h25[p25:a25].max() - l25[p25:a25].min()) if a25 > p25 else np.nan
            j25 = int(np.searchsorted(t25, ev["tc"] + 3600, "left"))
            rec = float(h25[a25:j25].max() - l25[a25:j25].min()) if j25 > a25 else np.nan
            r = carrera(ev, t25, h25, l25, c25, cl, (1,), tg_frac=0.5)
            ny = pd.Timestamp(ev["tc"], unit="s", tz="UTC").tz_convert("America/New_York")
            row = dict(inst=inst, contrato=I["bundle"], dia=str(ny.date()), hora=ny.hour + ny.minute / 60, cash=bool(9.5 <= ny.hour + ny.minute / 60 < 11),
                       dir=s, R=R, velas25=ev["velas"], velas_m1=ev["velas_m1"], vol_pre=vol_pre, atr14=float(tr[max(0, kb - 14):kb].mean()) if kb > 0 else np.nan,
                       y1_tg=int(r["res"] == "Tg"), res=r["res"], recorrido=rec, y2=rec / vol_pre if vol_pre and vol_pre > 0 else np.nan)
            i0 = ev["i0"]; w0 = max(0, i0 - 500)                  # M10b: cobertura de franjas por las 500 velas previas a A
            if i0 > w0:
                lo5, hi5 = l[w0:i0].min(), h[w0:i0].max()
                fa = sorted((X, X + s * R)); fb = sorted((A - s * R, A))
                row["cob_ad"] = max(0.0, min(hi5, fa[1]) - max(lo5, fa[0])) / R; row["cob_at"] = max(0.0, min(hi5, fb[1]) - max(lo5, fb[0])) / R
            else:
                row["cob_ad"] = row["cob_at"] = np.nan
            pos = s * (zmid - X) / R                              # >0 adelante de X; <-1 atras de A; [-1,0] interior
            for v in VIDAS:
                viva = (zi <= kb) & (kb - zi <= v)
                ad = viva & (pos > 0) & (pos <= 1); at = viva & (pos < -1) & (pos >= -2); it = viva & (pos >= -1) & (pos <= 0)
                na, nt, ni = int(ad.sum()), int(at.sum()), int(it.sum())
                row.update({f"n_ad_{v}": na, f"n_at_{v}": nt, f"n_in_{v}": ni, f"D_{v}": (na - nt) / (na + nt + 1),
                            f"fog_ad_{v}": float(zog[ad].mean()) if na else -1.0,
                            f"dist_ad_{v}": float(pos[ad].min()) if na else 2.0, f"dist_at_{v}": float((-1 - pos[at]).min()) if nt else 2.0})
            rows.append(row)
        print(inst, I["bundle"], len(I["impulsos"]), flush=True)
    pd.DataFrame(rows).to_csv(out, index=False)


if __name__ == "__main__":
    main()
