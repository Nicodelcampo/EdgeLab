"""M11: grilla SL/TP/BE del fade "fin de caja -> inicio de zona", IS/OOS/ES.
Reglas: docs/research/luximb_parity_20261020/MANIFIESTO_M11_GRILLA_SLTP_FADE_20261020.md (no cambiar sin enmienda).
Uso: python tools/luximb_parity/luximb_m11.py <out.json>"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; REPO = HERE.parents[1]; sys.path.insert(0, str(HERE))
from luximb_outcomes import GAP_S, REP_START, TOPE_MIN  # noqa: E402

BUN = REPO / "viewer/nt8_bridge/bundles"; D5 = REPO / "docs/research/luximb_parity_20261020/desc_m5"; D11 = REPO / "docs/research/luximb_parity_20261020/desc_m11"
F_TP = (0.5, 0.75, 1.0, 1.25); F_SL = (0.1, 0.2, 0.33, 0.5, 1.0); BE = (False, True); NB = 2000
CFG = {"NQ": dict(tick=0.25, comm=0.225), "ES": dict(tick=0.25, comm=0.09)}
TRAMOS = [("NQ", "09-25", "IS"), ("NQ", "12-25", "IS"), ("NQ", "03-26", "OOS"), ("NQ", "06-26", "OOS"),
          ("ES", "09-25", "ES"), ("ES", "12-25", "ES"), ("ES", "03-26", "ES"), ("ES", "06-26", "ES")]


def sim(s, E, tp, sl, be_lvl, hh, ll, cc, tick):
    """Fade: s=+1 impulso alcista -> venta. Devuelve (precio de salida, motivo)."""
    stop = sl; be_on = False
    for k in range(len(hh)):
        hit_sl = hh[k] >= stop if s > 0 else ll[k] <= stop
        hit_tp = ll[k] <= tp if s > 0 else hh[k] >= tp
        if hit_sl: return stop + s * tick, ("BE" if be_on else "SL")
        if hit_tp: return tp, "TP"
        if be_lvl is not None and not be_on and ((ll[k] <= be_lvl) if s > 0 else (hh[k] >= be_lvl)):
            stop = E; be_on = True
    return (cc[-1] if len(cc) else E) + s * tick, "tiempo"


def main():
    D11.mkdir(parents=True, exist_ok=True); rows = []
    for inst, c, part in TRAMOS:
        bid = f"{inst}_{c}_M1_LUXIMB"
        if inst == "NQ":
            ip = D5 / f"imp_NQ_{c}.json"
        else:
            ip = D11 / f"imp_{bid}.json"
            if not ip.exists():
                subprocess.run([sys.executable, "-X", "utf8", str(HERE / "luximb_impulsos.py"), str(BUN / f"{bid}.json"), str(ip), "--modo", "inicio",
                                "--p-rango", "60", "--min-ini", "3", "--share-ini", "0.5", "--rango-min-rel", "1.3"], check=True, cwd=REPO, capture_output=True)
        B = json.load(open(BUN / f"{bid}.json", encoding="utf-8")); I = json.load(open(ip, encoding="utf-8"))
        cl = np.array([x["close"] for x in B["bar_series"]["time_1m"]["candles"]]); T = B["bar_series"]["tick_25"]["candles"]
        t25 = np.array([x["time"] for x in T]); h25 = np.array([x["high"] for x in T]); l25 = np.array([x["low"] for x in T]); c25 = np.array([x["close"] for x in T])
        del B, T
        tick, comm = CFG[inst]["tick"], CFG[inst]["comm"]
        for ev in I["impulsos"]:
            if ev["tc"] >= REP_START: raise SystemExit("fuera de descubrimiento")
            s = 1 if ev["dir"] == "up" else -1; A, X = ev["p0"], ev["p1"]
            a = int(np.searchsorted(t25, ev["tc"], "left")); b = a
            while b < len(t25) and t25[b] <= ev["tc"] + TOPE_MIN * 60 and (b == a or t25[b] - t25[b - 1] <= GAP_S): b += 1
            hh, ll, cc = h25[a:b], l25[a:b], c25[a:b]
            dia = str(pd.Timestamp(ev["tc"], unit="s", tz="UTC").tz_convert("America/New_York").date())
            for modo in ("realista", "optimista"):
                E = (cl[ev["ic"]] - s * tick) if modo == "realista" else X           # venta si s=+1: 1 tick peor
                D = s * (E - A)
                if D <= 0: continue
                for ft in F_TP:
                    tp = E - s * ft * D; dtp = ft * D
                    for fs in F_SL:
                        sl = E + s * fs * dtp
                        for be in BE:
                            ex, why = sim(s, E, tp, sl, (E - s * 0.5 * dtp) if be else None, hh, ll, cc, tick if modo == "realista" else 0.0)
                            pnl = -s * (ex - E) - (comm if modo == "realista" else 0.0)
                            rows.append(dict(part=part, inst=inst, dia=dia, modo=modo, f_tp=ft, f_sl=fs, be=be, pnl=pnl, R=pnl / (fs * dtp), why=why))
        print(inst, c, part, len(I["impulsos"]), flush=True)
    df = pd.DataFrame(rows); df.to_csv(Path(sys.argv[1]).with_suffix(".csv"), index=False)
    rng = np.random.default_rng(20261030); celdas = []
    for (modo, ft, fs, be), g in df.groupby(["modo", "f_tp", "f_sl", "be"]):
        rec = dict(modo=modo, f_tp=ft, f_sl=fs, be=bool(be))
        for part in ("IS", "OOS", "ES"):
            x = g[g.part == part]
            if x.empty: continue
            days = x.dia.unique(); ix = {k: np.flatnonzero(x.dia.values == k) for k in days}; v = x.pnl.values
            bs = [v[np.concatenate([ix[k] for k in rng.choice(days, len(days))])].mean() for _ in range(NB)] if modo == "realista" else [np.nan]
            gp, gl = v[v > 0].sum(), -v[v < 0].sum()
            rec[part] = dict(n=len(x), acierto=round(float((x.why == "TP").mean()), 3), media_pts=round(float(v.mean()), 3), media_R=round(float(x.R.mean()), 3),
                             ic95=[round(float(np.nanpercentile(bs, 2.5)), 3), round(float(np.nanpercentile(bs, 97.5)), 3)], pf=round(float(gp / gl), 3) if gl else None)
        celdas.append(rec)
    real = [c for c in celdas if c["modo"] == "realista"]
    top = sorted(real, key=lambda c: -c["IS"]["media_pts"])[:3]
    isv = np.array([c["IS"]["media_pts"] for c in real]); oosv = np.array([c["OOS"]["media_pts"] for c in real]); esv = np.array([c["ES"]["media_pts"] for c in real])
    sobreviven = [c for c in top if c["OOS"]["ic95"][0] > 0 and c["ES"]["media_pts"] > 0]
    out = dict(manifiesto="MANIFIESTO_M11_GRILLA_SLTP_FADE_20261020.md", celdas=celdas, top3_IS=top, sobreviven=sobreviven,
               diagnostico=dict(corr_IS_OOS=round(float(np.corrcoef(isv, oosv)[0, 1]), 3), corr_IS_ES=round(float(np.corrcoef(isv, esv)[0, 1]), 3),
                                mediana_celdas_IS=float(np.median(isv)), mediana_celdas_OOS=float(np.median(oosv)), mediana_celdas_ES=float(np.median(esv)),
                                celdas_OOS_positivas=int((oosv > 0).sum()), celdas_ES_positivas=int((esv > 0).sum()), n_celdas=len(real)))
    json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
    print(json.dumps(out["diagnostico"]), json.dumps(top, default=str))


if __name__ == "__main__":
    main()
