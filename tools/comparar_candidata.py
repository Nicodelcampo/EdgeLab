"""Compara una corrida de `EdgeLabCandidataFS` en NT8 contra la referencia Python (`tools/candidata_referencia.py`).

Mide, descontando el calentamiento inicial de NT8 (`--calentamiento-meses`, la historia previa no se reproduce):
  1. paridad: entradas por minuto y lado (exactas, ±1 min, sólo en NT8, sólo en Python) y diferencia de salida;
  2. veto de noticias: operaciones que Python anula o cierra con el veto y cuántas cierra NT8 por `NEWS_VETO`;
  3. sizing: contratos y riesgo USD real / objetivo por año (lo que NT8 hizo con el precio y la volatilidad de cada época);
  4. frecuencia: operaciones por mes en NT8 y en Python.

  python tools/comparar_candidata.py --nt8 <csv de NT8> --py <PY_variante_inst.csv> --inst NQ --out <carpeta>

Target-free respecto de la decisión: no elige parámetros; reporta coincidencias y diferencias.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from edgelab import veto_noticias as VN  # noqa: E402

NY = "America/New_York"


def leer_nt8(p: Path) -> pd.DataFrame:
    d = pd.read_csv(p)
    d["en_ns"] = pd.to_datetime(d["en_ny"]).dt.tz_localize(NY, ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC").dt.as_unit("ns").astype("int64")
    d["ex_ns"] = pd.to_datetime(d["ex_ny"]).dt.tz_localize(NY, ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC").dt.as_unit("ns").astype("int64")
    return d


def aperturas(inst: str, desde_ns: int, hasta_ns: int) -> pd.Series:
    pq = ROOT / "data" / "m1nt8" / f"{inst}_M1_nonadj_utc.parquet"
    d = pd.read_parquet(pq, columns=["open"], filters=[("datetime", ">=", pd.Timestamp(desde_ns, unit="ns")),
                                                        ("datetime", "<=", pd.Timestamp(hasta_ns, unit="ns"))])
    s = d["open"]; s.index = pd.DatetimeIndex(s.index).tz_localize("UTC")
    return s


def py_con_veto(py: pd.DataFrame, inst: str) -> tuple[pd.DataFrame, dict]:
    ap = aperturas(inst, int(py.en_ns.min()) - 60 * 10**9, int(py.ex_ns.max()) + 60 * 10**9)
    idx = ap.index.as_unit("ns").asi8
    k = np.clip(np.searchsorted(idx, py.en_ns.to_numpy(np.int64), side="right") - 1, 0, len(idx) - 1)
    ent = ap.to_numpy(float)[k]                                       # la entrada se llena en la apertura de su vela
    ops = pd.DataFrame({"entrada_ns": py.en_ns.to_numpy(np.int64), "salida_ns": py.ex_ns.to_numpy(np.int64),
                        "lado": py.side.to_numpy(int), "precio_entrada": ent,
                        "precio_salida": ent + py.side.to_numpy(float) * py.pnl_pts.to_numpy(float)})
    o = VN.aplicar_veto(ops, ap)
    out = py.copy()
    out["veto"] = o["veto"].to_numpy(); out["ex_ns_veto"] = o["salida_ns"].to_numpy(); out["pnl_pts_veto"] = o["pts"].to_numpy()
    return out, VN.resumen(o)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nt8", type=Path, required=True)
    ap.add_argument("--py", type=Path, required=True)
    ap.add_argument("--inst", default="NQ")
    ap.add_argument("--calentamiento-meses", type=int, default=12)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    nt = leer_nt8(a.nt8)
    py, veto_py = py_con_veto(pd.read_csv(a.py), a.inst)
    t_ini = pd.Timestamp(int(nt.en_ns.min()), unit="ns", tz="UTC") + pd.DateOffset(months=a.calentamiento_meses)
    t_fin = pd.Timestamp(int(nt.en_ns.max()), unit="ns", tz="UTC")
    win = lambda d: d[(d.en_ns >= t_ini.value) & (d.en_ns <= t_fin.value)]
    ntw, pyw = win(nt), win(py[py.veto != "anulada"])
    # 1. paridad de entradas (minuto + lado)
    key = lambda d: set(zip((d.en_ns // 60_000_000_000).astype(np.int64), d.side.astype(int)))
    kn, kp = key(ntw), key(pyw)
    exactas = kn & kp
    cerca = {x for x in kn - kp if (x[0] - 1, x[1]) in kp or (x[0] + 1, x[1]) in kp}
    # 2. veto
    veto_nt8 = int((ntw.exit_name == "NEWS_VETO").sum())
    # 3. sizing por año (NT8)
    ntw = ntw.assign(anio=pd.to_datetime(ntw.en_ns, utc=True).dt.year,
                     ratio=ntw.riesgo_usd_real / ntw.riesgo_usd_objetivo.replace(0, np.nan))
    siz = ntw.groupby("anio").agg(n=("ratio", "size"), contratos_med=("contratos", "median"), contratos_max=("contratos", "max"),
                                  riesgo_obj=("riesgo_usd_objetivo", "median"), riesgo_real_med=("riesgo_usd_real", "median"),
                                  ratio_p10=("ratio", lambda x: x.quantile(0.1)), ratio_med=("ratio", "median"),
                                  ratio_p90=("ratio", lambda x: x.quantile(0.9)), riesgo_pts_med=("riesgo_pts", "median")).round(2)
    # 4. frecuencia
    meses = max(1, (t_fin - t_ini).days / 30.44)
    res = dict(
        ventana=[str(t_ini.date()), str(t_fin.date())], calentamiento_meses=a.calentamiento_meses,
        n_nt8=len(ntw), n_python=len(pyw), ops_mes_nt8=round(len(ntw) / meses, 2), ops_mes_python=round(len(pyw) / meses, 2),
        entradas_exactas=len(exactas), entradas_a_1_min=len(cerca), solo_nt8=len(kn - kp - cerca), solo_python=len(kp - kn),
        pct_paridad_exacta=round(100 * len(exactas) / max(1, len(kp)), 2),
        veto_python=veto_py, cierres_news_veto_nt8=veto_nt8,
        pnl_pts_nt8=round(float(ntw.pnl_pts.sum()), 2), pnl_pts_python_con_veto=round(float(pyw.pnl_pts_veto.sum()), 2),
        sizing_por_anio=siz.reset_index().to_dict("records"))
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "COMPARACION.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "sizing_por_anio"}, indent=1, default=str))
    print(siz.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
