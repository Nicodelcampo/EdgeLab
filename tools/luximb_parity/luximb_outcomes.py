"""Desenlaces M1/M2/M3 de los impulsos LUX-IMB segun
`docs/research/luximb_parity_20261020/PREREGISTRO_M1_M2_M3_LUXIMB_NQ_20261020.md` (no cambiar reglas aca sin enmienda).

Uso: python tools/luximb_parity/luximb_outcomes.py <out.json> <bundle.json>:<impulsos.json> [...]
Solo descubrimiento (HOLDOUT-A3): el script rechaza eventos >= 2026-04-01.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

TICK, COMM = 0.25, 0.225
REP_START = int(pd.Timestamp("2026-04-01", tz="America/Chicago").value // 10**9) - 7 * 3600   # sesion CME del 1-abr abre 17:00 CT del 31-mar
TOPE_MIN, GAP_S, NB = 240, 1800, 10000


def carrera(ev, t25, h25, l25, c25, cl_m1, slips):
    s = 1 if ev["dir"] == "up" else -1
    A, X = ev["p0"], ev["p1"]; R = abs(X - A); E = cl_m1[ev["ic"]]
    tg, ex = X - 0.5 * R * s, X + 0.25 * R * s
    a = int(np.searchsorted(t25, ev["tc"], "left")); b = a
    while b < len(t25) and t25[b] <= ev["tc"] + TOPE_MIN * 60 and (b == a or t25[b] - t25[b - 1] <= GAP_S):
        b += 1
    hh, ll = h25[a:b], l25[a:b]
    if (E - tg) * s <= 0:
        res, k, px = "Tg", a, E
    else:
        hit_ex = np.flatnonzero((hh >= ex) if s > 0 else (ll <= ex)); hit_tg = np.flatnonzero((ll <= tg) if s > 0 else (hh >= tg))
        ke = hit_ex[0] if len(hit_ex) else 10**9; kt = hit_tg[0] if len(hit_tg) else 10**9
        if ke == kt == 10**9: res, px = "tiempo", (c25[b - 1] if b > a else E)
        elif ke <= kt: res, px = "Ex", ex
        else: res, px = "Tg", tg
    out = dict(res=res, R=R, E=E)
    for sl in slips:
        sp = sl * TICK
        ent_f = E - s * sp                                           # fade: vende si s=+1
        exit_f = tg if res == "Tg" else (ex + s * sp if res == "Ex" else px + s * sp)
        out[f"pnl_fade_{sl}"] = -s * (exit_f - ent_f) - COMM
        ent_c = E + s * sp
        exit_c = ex if res == "Ex" else (tg - s * sp if res == "Tg" else px - s * sp)
        out[f"pnl_cont_{sl}"] = s * (exit_c - ent_c) - COMM
    j = int(np.searchsorted(t25, ev["tc"] + 3600, "left"))
    if j > a and R > 0:
        hi, lo = h25[a:j].max(), l25[a:j].min()
        out["mfe_fade_R"] = ((E - lo) if s > 0 else (hi - E)) / R
        out["mae_fade_R"] = ((hi - E) if s > 0 else (E - lo)) / R
    return out


def boot(df, col, grp=None, rng=None):
    """Media (o diferencia T - C si grp) con bootstrap por dia. Devuelve est, lo, hi, p_unilateral(<=0), se."""
    days = df.dia.unique(); idx = {d: np.flatnonzero(df.dia.values == d) for d in days}
    v = df[col].to_numpy(float); g = df[grp].to_numpy() if grp else None

    def est(ii):
        if grp is None: return np.nanmean(v[ii])
        gi = g[ii]; return np.nanmean(v[ii][gi]) - np.nanmean(v[ii][~gi])
    full = est(np.arange(len(df)))
    bs = np.empty(NB)
    for k in range(NB):
        pick = rng.choice(days, len(days)); bs[k] = est(np.concatenate([idx[d] for d in pick]))
    return dict(est=round(float(full), 4), ic95=[round(float(np.nanpercentile(bs, 2.5)), 4), round(float(np.nanpercentile(bs, 97.5)), 4)],
                p=float(np.mean(bs <= 0)), se=float(np.nanstd(bs)), n=int(len(df)), dias=int(len(days)))


def main():
    out_path = sys.argv[1]; rows = []
    for pair in sys.argv[2:]:
        bpath, ipath = pair.rsplit(":", 1)
        B = json.load(open(bpath, encoding="utf-8")); I = json.load(open(ipath, encoding="utf-8"))
        Z = {z["id"]: z for z in B["runs"][0]["zones"]}
        cl = np.array([c["close"] for c in B["bar_series"]["time_1m"]["candles"]])
        T = B["bar_series"]["tick_25"]["candles"]
        t25 = np.array([c["time"] for c in T]); h25 = np.array([c["high"] for c in T]); l25 = np.array([c["low"] for c in T]); c25 = np.array([c["close"] for c in T])
        for grupo, evs in (("T", I["impulsos"]), ("C", I["control"])):
            for ev in evs:
                if ev["tc"] >= REP_START:
                    raise SystemExit(f"evento en replicacion/holdout: {ev['tc']}")
                r = carrera(ev, t25, h25, l25, c25, cl, (0, 1, 2))
                ny = pd.Timestamp(ev["tc"], unit="s", tz="UTC").tz_convert("America/New_York")
                fop = np.mean([("BULL" in Z[i]["kind"]) != (ev["dir"] == "up") for i in ev["zona_ids"]]) if grupo == "T" else np.nan
                rows.append(dict(contrato=B["meta"]["contract"], grupo=grupo, dir=ev["dir"], tc=ev["tc"], dia=str(ny.date()),
                                 cash=bool(9.5 <= ny.hour + ny.minute / 60 < 11), frac_op=fop, zonas=ev["zonas"], rango=ev["rango"], **r))
        del B, T
    df = pd.DataFrame(rows)
    df["tg"] = (df.res == "Tg").astype(float); df["ex"] = (df.res == "Ex").astype(float); df["esT"] = df.grupo == "T"
    rng = np.random.default_rng(20261020)
    Tdf = df[df.esT]
    H = {}
    H["H1_PTg_T_menos_C"] = boot(df, "tg", "esT", rng)
    H["H2_pnl_fade_T_1tick"] = boot(Tdf, "pnl_fade_1", None, rng)
    H["H3_pnl_cont_T_1tick"] = boot(Tdf, "pnl_cont_1", None, rng)
    H["H4a_PTg_T_menos_C_sube"] = boot(df[df.dir == "up"], "tg", "esT", rng)
    H["H4b_PTg_T_menos_C_baja"] = boot(df[df.dir == "down"], "tg", "esT", rng)
    H["H5a_PTg_T_menos_C_cash"] = boot(df[df.cash], "tg", "esT", rng)
    H["H5b_PTg_T_menos_C_resto"] = boot(df[~df.cash], "tg", "esT", rng)
    H["H6a_PTg_Topuestas<0.5_menos_C"] = boot(df[(~df.esT) | (df.frac_op < 0.5)], "tg", "esT", rng)
    H["H6b_PTg_Topuestas>=0.5_menos_C"] = boot(df[(~df.esT) | (df.frac_op >= 0.5)], "tg", "esT", rng)
    H["H7_pnl_fade_T_menos_C_1tick"] = boot(df, "pnl_fade_1", "esT", rng)
    # Holm sobre la familia preregistrada de 7 (H4-H6: se toma el menor p de cada par, ya penalizado x2)
    fam = {"H1": H["H1_PTg_T_menos_C"]["p"], "H2": H["H2_pnl_fade_T_1tick"]["p"], "H3": H["H3_pnl_cont_T_1tick"]["p"],
           "H4": min(1, 2 * min(H["H4a_PTg_T_menos_C_sube"]["p"], H["H4b_PTg_T_menos_C_baja"]["p"])),
           "H5": min(1, 2 * min(H["H5a_PTg_T_menos_C_cash"]["p"], H["H5b_PTg_T_menos_C_resto"]["p"])),
           "H6": min(1, 2 * min(H["H6a_PTg_Topuestas<0.5_menos_C"]["p"], H["H6b_PTg_Topuestas>=0.5_menos_C"]["p"])),
           "H7": H["H7_pnl_fade_T_menos_C_1tick"]["p"]}
    order = sorted(fam, key=fam.get); holm = {}; run = 0.0
    for k, name in enumerate(order):
        run = max(run, min(1.0, (len(order) - k) * fam[name])); holm[name] = round(run, 4)
    desc = {}
    for gname, g in df.groupby("grupo"):
        desc[gname] = dict(n=len(g), dias=g.dia.nunique(), P_Tg=round(g.tg.mean(), 4), P_Ex=round(g.ex.mean(), 4), P_tiempo=round((g.res == "tiempo").mean(), 4),
                           rango_p50=float(g.rango.median()),
                           **{f"pnl_fade_{s}_media": round(g[f"pnl_fade_{s}"].mean(), 3) for s in (0, 1, 2)},
                           **{f"pnl_cont_{s}_media": round(g[f"pnl_cont_{s}"].mean(), 3) for s in (0, 1, 2)},
                           mfe_fade_R_p25_50_75=[round(float(x), 3) for x in g.mfe_fade_R.quantile([.25, .5, .75])],
                           mae_fade_R_p25_50_75=[round(float(x), 3) for x in g.mae_fade_R.quantile([.25, .5, .75])])
    porcontrato = df.groupby(["contrato", "grupo"]).agg(n=("tg", "size"), P_Tg=("tg", "mean"), pnl_fade_1=("pnl_fade_1", "mean")).round(3).reset_index().to_dict("records")
    res = dict(preregistro="PREREGISTRO_M1_M2_M3_LUXIMB_NQ_20261020.md", descriptivo=desc, hipotesis=H, p_holm=holm,
               MDE80_H1_pp=round(2.8 * H["H1_PTg_T_menos_C"]["se"] * 100, 1), por_contrato=porcontrato)
    json.dump(res, open(out_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    df.to_csv(out_path.replace(".json", "_eventos.csv"), index=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
