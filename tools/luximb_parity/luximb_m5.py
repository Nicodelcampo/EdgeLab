"""M5: vuelta al inicio cargado. Reglas: docs/research/luximb_parity_20261020/PREREGISTRO_M5_INICIO_CARGADO_LUXIMB_NQ_20261020.md
Uso: python tools/luximb_parity/luximb_m5.py <out.json> <bundle.json>:<impulsos.json> [...]"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from luximb_outcomes import REP_START, boot, carrera  # noqa: E402


def main():
    out_path = sys.argv[1]; rows = []
    for pair in sys.argv[2:]:
        bpath, ipath = pair.rsplit(":", 1)
        B = json.load(open(bpath, encoding="utf-8")); I = json.load(open(ipath, encoding="utf-8"))
        cl = np.array([c["close"] for c in B["bar_series"]["time_1m"]["candles"]]); T = B["bar_series"]["tick_25"]["candles"]
        t25 = np.array([c["time"] for c in T]); h25 = np.array([c["high"] for c in T]); l25 = np.array([c["low"] for c in T]); c25 = np.array([c["close"] for c in T])
        for grupo, evs in (("T", I["impulsos"]), ("C", I["control"])):
            for ev in evs:
                if ev["tc"] >= REP_START: raise SystemExit("evento fuera de descubrimiento")
                r = carrera(ev, t25, h25, l25, c25, cl, (0, 1, 2), tg_frac=0.75)
                ny = pd.Timestamp(ev["tc"], unit="s", tz="UTC").tz_convert("America/New_York")
                vac = (ev["reparto"][1] == 0) if grupo == "T" else None
                rows.append(dict(contrato=B["meta"]["contract"], grupo=grupo, esT=grupo == "T", dir=ev["dir"], dia=str(ny.date()),
                                 cash=bool(9.5 <= ny.hour + ny.minute / 60 < 11), resto_vacio=vac, rango=ev["rango"], **r))
        del B, T
    df = pd.DataFrame(rows); df["tg"] = (df.res == "Tg").astype(float); df["ex"] = (df.res == "Ex").astype(float)
    rng = np.random.default_rng(20261022); t = df[df.esT]; c = ~df.esT
    H = {"H1": boot(df, "tg", "esT", rng), "H2": boot(t, "pnl_fade_1", None, rng), "H3": boot(t, "pnl_cont_1", None, rng),
         "H4a_sube": boot(df[df.dir == "up"], "tg", "esT", rng), "H4b_baja": boot(df[df.dir == "down"], "tg", "esT", rng),
         "H5a_cash": boot(df[df.cash], "tg", "esT", rng), "H5b_resto": boot(df[~df.cash], "tg", "esT", rng),
         "H6a_vacio": boot(df[c | (df.resto_vacio == True)], "tg", "esT", rng), "H6b_no_vacio": boot(df[c | (df.resto_vacio == False)], "tg", "esT", rng)}
    fam = {"H1": H["H1"]["p"], "H2": H["H2"]["p"], "H3": H["H3"]["p"],
           "H4": min(1, 2 * min(H["H4a_sube"]["p"], H["H4b_baja"]["p"])), "H5": min(1, 2 * min(H["H5a_cash"]["p"], H["H5b_resto"]["p"])),
           "H6": min(1, 2 * min(H["H6a_vacio"]["p"], H["H6b_no_vacio"]["p"]))}
    order = sorted(fam, key=fam.get); holm = {}; run = 0.0
    for k, n in enumerate(order):
        run = max(run, min(1.0, (len(order) - k) * fam[n])); holm[n] = round(run, 4)
    desc = {g: dict(n=len(x), dias=x.dia.nunique(), P_Tg=round(x.tg.mean(), 4), P_Ex=round(x.ex.mean(), 4), P_tiempo=round((x.res == "tiempo").mean(), 4),
                    rango_p50=float(x.rango.median()), **{f"pnl_fade_{s}": round(x[f"pnl_fade_{s}"].mean(), 3) for s in (0, 1, 2)},
                    **{f"pnl_cont_{s}": round(x[f"pnl_cont_{s}"].mean(), 3) for s in (0, 1, 2)},
                    mfe_fade_R=[round(float(v), 3) for v in x.mfe_fade_R.quantile([.25, .5, .75])], mae_fade_R=[round(float(v), 3) for v in x.mae_fade_R.quantile([.25, .5, .75])])
            for g, x in df.groupby("grupo")}
    pc = df.groupby(["contrato", "grupo"]).agg(n=("tg", "size"), P_Tg=("tg", "mean"), pnl_fade_1=("pnl_fade_1", "mean")).round(3).reset_index().to_dict("records")
    out = dict(preregistro="PREREGISTRO_M5_INICIO_CARGADO_LUXIMB_NQ_20261020.md", descriptivo=desc, hipotesis=H, p_holm=holm,
               MDE80_H1_pp=round(2.8 * H["H1"]["se"] * 100, 1), por_contrato=pc)
    json.dump(out, open(out_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False); df.to_csv(out_path.replace(".json", "_eventos.csv"), index=False)
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
