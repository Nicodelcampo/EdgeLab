"""Paridad de EdgeLabCartera fuera de NT8 (2026-11-25).

1. Exporta velas M1 de NT8 (data/m1nt8, parquet) a CSV con sello = cierre (como NT8).
2. Compila el arnes C# (tools/nt8_cartera_harness/Harness.cs) con los MISMOS .cs del motor que se instalan en NT8.
3. Corre la cartera en modo virtual y en modo broker y compara cada estrategia contra su corrida NT8 individual
   (docs/research/candidatas_nt8_20261125): operaciones emparejadas por hora de entrada, igualdad de entrada/salida y
   diferencia de P&L.

  python tools/nt8_cartera_paridad.py --comp "NQ:T=1,R=1,Z=1,V=1,RQ5=1,FR=1;ES:RQ5=1,ES5N=1" --out docs/research/cartera_nt8_20261125/paridad

Nunca lee el holdout terminal: las velas cortan en 2026-09-30.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
NT8 = ROOT / "nt8" / "strategies"
H = ROOT / "tools" / "nt8_cartera_harness"
CAND = ROOT / "docs" / "research" / "candidatas_nt8_20261125"
NUE = CAND / "corridas_nt8_nuevas"
REF = {  # (raiz, modulo en el CSV del arnes) -> corrida NT8 individual
    ("NQ", "T_stop100_BE15R_calFalse"): CAND / "T" / "NT8_T_NQ_fijo1.csv",
    ("NQ", "R_osc30_end660_ATR50"): CAND / "R" / "NT8_R_NQ_fijo1.csv",
    ("NQ", "Z_b15_e20_eff40_ATR50"): CAND / "Z" / "NT8_Z_NQ_fijo1.csv",
    ("NQ", "V_nm25_noCap_mae30"): CAND / "V" / "NT8_V_NQ_fijo1.csv",
    ("NQ", "SOM_sin_finde"): CAND / "SOM_sin_finde" / "NT8_SOM_sin_finde_NQ_fijo1.csv",
    ("NQ", "SOMEOD_ext_NQ"): CAND / "SOMEOD" / "NT8_SOMEOD_NQ_fijo1.csv",
    ("NQ", "RQ5"): NUE / "NT8_RQ5_NQ.csv", ("ES", "RQ5"): NUE / "NT8_RQ5_ES.csv",
    ("NQ", "FRANKLIN"): NUE / "NT8_Franklin_NQ.csv", ("ES", "ES5N"): NUE / "NT8_ES5N_ES.csv",
    ("NQ", "C2_VZ"): NUE / "NT8_C2_VZ_NQ.csv", ("ES", "C2_VZ"): NUE / "NT8_C2_VZ_ES.csv",
}


def exportar(root: str, desde: str, hasta: str, dst: Path) -> Path:
    f = dst / f"{root}_{desde}_{hasta}.csv"
    if f.exists():
        return f
    d = pd.read_parquet(ROOT / "data" / "m1nt8" / f"{root}_M1_nonadj_utc.parquet",
                        filters=[("datetime", ">=", pd.Timestamp(desde)), ("datetime", "<", pd.Timestamp(hasta))])
    t = (pd.DatetimeIndex(d.index).as_unit("s").asi8 + 60)          # sello = cierre de la vela
    pd.DataFrame({"t": t, "o": d.open, "h": d.high, "l": d.low, "c": d.close, "v": d.volume}).to_csv(f, index=False)
    return f


def compilar() -> Path:
    import shutil
    import sync_ctrader_mt5_bots as S
    exe = H / "Harness.exe"
    srcs = [NT8 / "EdgeLabFundedSyncCore.cs", NT8 / "EdgeLabCarteraEngines.cs", NT8 / "EdgeLabCarteraBook.cs", H / "Harness.cs"]
    csc = str(S.CSC_EXE) if S.CSC_EXE.exists() else shutil.which("mcs")      # Linux: mono mcs (2026-11-27)
    if csc is None:
        raise SystemExit("no hay compilador C# (csc de .NET Framework o mono mcs)")
    cmd = [csc, "/nologo", "/target:exe", "/optimize+", f"/out:{exe}", "/r:System.dll", "/r:System.Core.dll", *map(str, srcs)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(r.stdout + r.stderr)
    return exe


def cboe_csv(dst: Path) -> Path:
    nt8 = Path.home() / "Documents" / "NinjaTrader 8" / "EdgeLab" / "datos" / "cboe_vol_diario.csv"
    if nt8.exists():                      # el mismo archivo que leyeron las corridas NT8 (tools/exportar_vix_nt8.py)
        return nt8
    f = dst / "cboe_vol_diario.csv"
    if not f.exists():                    # mismo formato que tools/exportar_vix_nt8.py (fecha,vix_close,vxn_close,vix9d_close)
        from exportar_vix_nt8 import build_cboe_df
        out = build_cboe_df(); out.insert(0, "fecha", out.index.strftime("%Y-%m-%d"))
        out.to_csv(f, index=False, float_format="%.4f")
    return f


def comparar(sim: pd.DataFrame, ref: pd.DataFrame) -> dict:
    a = sim.assign(k=pd.to_datetime(sim.en_ny).dt.floor("min")); b = ref.assign(k=pd.to_datetime(ref.en_ny).dt.floor("min"))
    a = a[(a.k >= "2019-07-01") & (a.k < "2026-10-01")]; b = b[(b.k >= "2019-07-01") & (b.k < "2026-10-01")]
    m = a.merge(b, on="k", suffixes=("_s", "_r"))
    eq_ent = (m.entry_price_s - m.entry_price_r).abs() < 1e-6
    eq_sal = (m.exit_price_s - m.exit_price_r).abs() < 1e-6
    return dict(n_arnes=len(a), n_nt8=len(b), emparejadas=len(m), pct_emparejadas_nt8=round(100 * len(m) / max(len(b), 1), 1),
                misma_entrada_pct=round(100 * eq_ent.mean(), 1) if len(m) else None,
                misma_salida_pct=round(100 * eq_sal.mean(), 1) if len(m) else None,
                pnl_pts_arnes=round(float(a.pnl_pts.sum()), 1), pnl_pts_nt8=round(float(b.pnl_pts.sum()), 1),
                dif_pnl_pts_emparejadas=round(float((m.pnl_pts_s - m.pnl_pts_r).sum()), 1))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--comp", required=True); ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--desde", default="2018-12-01"); ap.add_argument("--hasta", default="2026-09-30")
    ap.add_argument("--interdia", action="store_true"); ap.add_argument("--modos", default="virtual,broker")
    a = ap.parse_args(argv); a.out.mkdir(parents=True, exist_ok=True)
    tmp = ROOT / "data" / "harness_bars"; tmp.mkdir(parents=True, exist_ok=True)
    roots = [b.split(":")[0] for b in a.comp.split(";")]
    barras = [f"{r}={exportar(r, a.desde, a.hasta, tmp)}" for r in roots]
    exe = compilar()
    news = ROOT / "config" / "noticias" / "calendario_usd_tier1.csv"
    vol = cboe_csv(tmp)
    res = {}
    for modo in a.modos.split(","):
        r = subprocess.run([*([] if sys.platform == "win32" else ["mono"]), str(exe), modo, str(a.out), str(news), str(vol), "1" if a.interdia else "0", a.comp, *barras],
                           capture_output=True, text=True)
        print(r.stdout.strip()); print(r.stderr.strip()[-2000:])
        for root in roots:
            f = a.out / f"{modo}_{root}.csv"
            if not f.exists():
                continue
            sim = pd.read_csv(f)
            for mod, g in sim.groupby("modulo"):
                ref = REF.get((root, mod))
                if ref is None or not ref.exists():
                    continue
                c = comparar(g, pd.read_csv(ref)); res[f"{modo}|{root}|{mod}"] = c
                print(modo, root, mod, c, flush=True)
    (a.out / "PARIDAD.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    for f in a.out.glob("*.csv"):                     # salidas del arnes comprimidas (repo)
        pd.read_csv(f).to_csv(f.with_suffix(".csv.gz"), index=False); f.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
