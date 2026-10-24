"""M6: ruptura de escalonadas 150t sobre area cargada. Reglas:
docs/research/luximb_parity_20261020/PREREGISTRO_M6_ESCALONADAS_LUXIMB_NQ_20261020.md (no cambiar sin enmienda).
Uso: python tools/luximb_parity/luximb_m6.py <out.json> <bundle.json>:<escalonadas.json> [...]"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from luximb_outcomes import COMM, GAP_S, REP_START, TICK, TOPE_MIN, boot  # noqa: E402


def carrera(z, t25, h25, l25, c25, slips):
    s = -1 if z["kind"] == "H" else 1                       # direccion de la ruptura: techo -> abajo
    E = z["det_cierre"]
    rup = z["area_lo"] if s < 0 else z["area_hi"]
    rec = z["det_nivel"] + (TICK if s < 0 else -TICK)       # superar el ultimo pico conocido en 1 tick
    a = z["i25_post"]; b = a
    t_ini = t25[a] if a < len(t25) else 0
    while b < len(t25) and t25[b] <= t_ini + TOPE_MIN * 60 and (b == a or t25[b] - t25[b - 1] <= GAP_S):
        b += 1
    hh, ll = h25[a:b], l25[a:b]
    if (E - rup) * s >= 0:
        res, px = "ruptura", E
    else:
        hr = np.flatnonzero((ll <= rup) if s < 0 else (hh >= rup)); hx = np.flatnonzero((hh >= rec) if s < 0 else (ll <= rec))
        kr = hr[0] if len(hr) else 10**9; kx = hx[0] if len(hx) else 10**9
        if kr == kx == 10**9: res, px = "tiempo", (c25[b - 1] if b > a else E)
        elif kx <= kr: res, px = "rechazo", rec
        else: res, px = "ruptura", rup
    out = dict(res=res)
    for sl in slips:
        sp = sl * TICK
        ent = E + s * sp                                     # seguir la ruptura
        ex = rup if res == "ruptura" else (rec - s * sp if res == "rechazo" else px - s * sp)
        out[f"pnl_rup_{sl}"] = s * (ex - ent) - COMM
        ent2 = E - s * sp                                    # rechazo (espejo)
        ex2 = rec if res == "rechazo" else (rup + s * sp if res == "ruptura" else px + s * sp)
        out[f"pnl_rec_{sl}"] = -s * (ex2 - ent2) - COMM
    j = int(np.searchsorted(t25, t_ini + 3600, "left")); W = max(z["area_hi"] - z["area_lo"], TICK)
    if j > a:
        hi, lo = h25[a:j].max(), l25[a:j].min()
        out["mfe_rup_W"] = ((E - lo) if s < 0 else (hi - E)) / W; out["mae_rup_W"] = ((hi - E) if s < 0 else (E - lo)) / W
    return out


def main():
    out_path = sys.argv[1]; rows = []
    for pair in sys.argv[2:]:
        bpath, epath = pair.rsplit(":", 1)
        B = json.load(open(bpath, encoding="utf-8")); D = json.load(open(epath, encoding="utf-8"))
        T = B["bar_series"]["tick_25"]["candles"]
        t25 = np.array([c["time"] for c in T]); h25 = np.array([c["high"] for c in T]); l25 = np.array([c["low"] for c in T]); c25 = np.array([c["close"] for c in T])
        for z in D["zonas"]:
            if z["det_t"] >= REP_START: raise SystemExit("evento fuera de descubrimiento")
            if z["i25_post"] >= len(t25): continue
            ny = pd.Timestamp(z["det_t"], unit="s", tz="UTC").tz_convert("America/New_York")
            rows.append(dict(contrato=B["meta"]["contract"], esT=z["zonas_area"] >= 3, kind=z["kind"], dia=str(ny.date()),
                             cash=bool(9.5 <= ny.hour + ny.minute / 60 < 11), dens=z["dens_10pts"], zonas=z["zonas_area"],
                             **carrera(z, t25, h25, l25, c25, (0, 1, 2))))
        del B, T
    df = pd.DataFrame(rows); df["r"] = (df.res == "ruptura").astype(float)
    t = df[df.esT]; c = ~df.esT; md = float(t.dens.median()); rng = np.random.default_rng(20261023)
    H = {"H1": boot(df, "r", "esT", rng), "H2": boot(t, "pnl_rup_1", None, rng), "H3": boot(t, "pnl_rec_1", None, rng),
         "H4a_techo": boot(df[df.kind == "H"], "r", "esT", rng), "H4b_piso": boot(df[df.kind == "L"], "r", "esT", rng),
         "H5a_cash": boot(df[df.cash], "r", "esT", rng), "H5b_resto": boot(df[~df.cash], "r", "esT", rng),
         "H6a_dens_alta": boot(df[c | (df.esT & (df.dens >= md))], "r", "esT", rng), "H6b_dens_baja": boot(df[c | (df.esT & (df.dens < md))], "r", "esT", rng)}
    fam = {"H1": H["H1"]["p"], "H2": H["H2"]["p"], "H3": H["H3"]["p"], "H4": min(1, 2 * min(H["H4a_techo"]["p"], H["H4b_piso"]["p"])),
           "H5": min(1, 2 * min(H["H5a_cash"]["p"], H["H5b_resto"]["p"])), "H6": min(1, 2 * min(H["H6a_dens_alta"]["p"], H["H6b_dens_baja"]["p"]))}
    order = sorted(fam, key=fam.get); holm = {}; run = 0.0
    for k, n in enumerate(order):
        run = max(run, min(1.0, (len(order) - k) * fam[n])); holm[n] = round(run, 4)
    desc = {g: dict(n=len(x), dias=x.dia.nunique(), P_ruptura=round(x.r.mean(), 4), P_rechazo=round((x.res == "rechazo").mean(), 4),
                    P_tiempo=round((x.res == "tiempo").mean(), 4), **{f"pnl_rup_{s}": round(x[f"pnl_rup_{s}"].mean(), 3) for s in (0, 1, 2)},
                    **{f"pnl_rec_{s}": round(x[f"pnl_rec_{s}"].mean(), 3) for s in (0, 1, 2)},
                    mfe_rup_W=[round(float(v), 3) for v in x.mfe_rup_W.quantile([.25, .5, .75])], mae_rup_W=[round(float(v), 3) for v in x.mae_rup_W.quantile([.25, .5, .75])])
            for g, x in df.groupby(df.esT.map({True: "T", False: "C"}))}
    pc = df.groupby(["contrato", "esT"]).agg(n=("r", "size"), P_ruptura=("r", "mean"), pnl_rup_1=("pnl_rup_1", "mean")).round(3).reset_index().to_dict("records")
    out = dict(preregistro="PREREGISTRO_M6_ESCALONADAS_LUXIMB_NQ_20261020.md", descriptivo=desc, hipotesis=H, p_holm=holm,
               MDE80_H1_pp=round(2.8 * H["H1"]["se"] * 100, 1), mediana_dens_T=md, por_contrato=pc)
    json.dump(out, open(out_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str); df.to_csv(out_path.replace(".json", "_eventos.csv"), index=False)
    print(json.dumps(out, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
