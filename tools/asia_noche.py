#!/usr/bin/env python3
"""ASIA-NQ y la «noche movida», versión causal (pre-registro docs/research/asia_noche_20261118/PREREGISTRO.md).

La variable `noche` de `papel_regimen.variables` (rango 18:00→09:00 NY de la sesión, tercil contra los 250 previos) es causal para
reglas que entran después de las 09:00 (OTR930), pero NO para ASIA, que entra entre las 18:00 y las 09:00 de esa misma noche: mira el
futuro. La versión causal es la noche ANTERIOR (`noche_previa` = noche de la sesión d−1, conocida a las 09:00 de d−1).

  python tools/asia_noche.py dev       # descriptivo en el desarrollo (ticks reales, ago-25 → sep-26): efecto y desvío para la potencia
  python tools/asia_noche.py correr [INST ...]  # ASIA congelada sobre M1 de futuros (NT8) en los datos no mirados (local, tools/datos.py)
  python tools/asia_noche.py analizar  # prueba única pre-registrada -> docs/research/asia_noche_20261118/RESULTADO.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/asia_noche_20261118"; PRE = DIR / "PREREGISTRO.md"; RES = ROOT / "docs/research/papel_m1_20261115/resultados"
FICHA = "ASIA-NQ-CANASTA"
LIMPIOS = {"NQ": (20060106, 20111230), "ES": (20060106, 20111230), "YM": (20060106, 20111230), "EMD": (20060109, 20250731), "RTY": (20170710, 20250731)}
FAMILIA, RESERVA = "ASIA_NOCHE_PREVIA", "CONF_20261118"


def variables(inst: str) -> pd.DataFrame:
    """`papel_regimen.variables` con D1/H1 construidos del M1 de futuros de NT8 (copia verificada de tools/datos.py), más `noche_previa`."""
    import pyarrow.parquet as pq
    from datos import ruta
    from edgelab.research import papel_regimen as PR
    D = pq.read_table(Path(ruta("M1NT8")) / f"{inst}_M1_nonadj_utc.parquet").to_pandas()
    t = pd.to_datetime(D.index if "datetime" not in D else D["datetime"]).tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
    X = pd.DataFrame(dict(open=D.open.to_numpy(), high=D.high.to_numpy(), low=D.low.to_numpy(), close=D.close.to_numpy()), index=t)
    H1 = X.resample("1h").agg(dict(open="first", high="max", low="min", close="last")).dropna()
    H1.index = H1.index + pd.Timedelta(hours=7)                                   # PR.variables espera hora del servidor (NY+7)
    ses = (X.index + pd.Timedelta(hours=6)).normalize()
    D1 = X.close.groupby(ses).last().to_frame("close"); D1 = D1[D1.index.dayofweek < 5]
    V = PR.variables(D1, H1)
    V["noche_previa"] = V.noche.shift(1)                                          # la noche de d−1: conocida antes de que ASIA opere en d
    return V


def _canasta_R(ops: dict, k: int) -> pd.Series:
    """R neto por sesión con la agregación de la ficha (`canasta_por_sesion`: suma / número de celdas), R = neto / riesgo inicial."""
    from edgelab.cartera.papel import canasta_por_sesion
    r = np.asarray(ops["neto"], float) / np.asarray(ops["riesgo"], float); ok = np.isfinite(r)    # riesgo inicial indefinido: fuera la OPERACIÓN (k > 0)
    s = pd.Series(dict(canasta_por_sesion(zip(np.asarray(ops["ses"])[ok], r[ok]), k)))
    s.index = pd.to_datetime(s.index.astype(str), format="%Y%m%d"); return s


def _k():
    from papel_m1 import _ficha
    return len(_ficha(FICHA)["regla"]["celdas"])


def _tabla(inst, archivo) -> pd.DataFrame:
    ops = json.loads(Path(archivo).read_text(encoding="utf-8"))["operaciones"]
    s = _canasta_R(ops, _k()); V = variables(inst).reindex(s.index)
    return pd.DataFrame(dict(R=s.values, noche=V.noche.values, noche_previa=V.noche_previa.values, inst=inst), index=s.index)


def _contraste(T, var):
    from edgelab.research import a5 as A5
    ses = (T.index.strftime("%Y%m%d").astype(np.int64)).to_numpy()
    alto = (T[var] == 2).to_numpy(); bajo = (T[var] == 0).to_numpy()
    d, se, p = A5.diferencia(ses[alto], T.R.to_numpy(float)[alto], ses[bajo], T.R.to_numpy(float)[bajo])
    por_t = {int(k): dict(n=int(len(g)), R=float(g.R.mean())) for k, g in T.groupby(var)}
    yr = T.index.year.to_numpy(); anios = sorted(set(yr[alto]) & set(yr[bajo]))
    pos = [a for a in anios if T.R.to_numpy()[alto & (yr == a)].mean() - T.R.to_numpy()[bajo & (yr == a)].mean() > 0]
    return dict(dif=d, se=se, p=p, terciles=por_t, anios=len(anios), anios_pos=len(pos), frac_anios_pos=len(pos) / max(len(anios), 1))


def dev():
    T = _tabla("NQ", RES / f"FUTNQ__{FICHA}_20250801_20260929.json")
    out = {v: _contraste(T.dropna(subset=[v]), v) for v in ("noche", "noche_previa")}
    out["sd_R_sesion"] = float(T.R.std()); out["n_sesiones"] = int(len(T))
    (DIR / "DEV.json").write_text(json.dumps(out, indent=1, default=float)); print(json.dumps(out, default=float, indent=1))


def correr(solo=None):
    from a5_campana import _commiteado
    from edgelab import costos as C
    import papel_m1 as PM
    if not _commiteado(PRE): raise SystemExit("el pre-registro no está commiteado")
    with C.estimados_permitidos(str(PRE.relative_to(ROOT))):                    # EMD: costo estimado declarado (K33)
        for inst, (a, b) in LIMPIOS.items():
            if solo and inst not in solo: continue
            dst = RES / f"{PM._pref('M1NT8:' + inst)}{FICHA}_{a}_{b}.json"
            if dst.exists(): print("ya está", dst.name); continue
            PM.local(FICHA, "M1NT8:" + inst, [f"{a}-{b}"])


def analizar():
    from edgelab.funnel.libro_lord import LibroLord
    import papel_m1 as PM
    T = pd.concat([_tabla(i, RES / f"{PM._pref('M1NT8:' + i)}{FICHA}_{a}_{b}.json") for i, (a, b) in LIMPIOS.items()])
    P = T.dropna(subset=["noche_previa"])
    prim = _contraste(P, "noche_previa")
    res = LibroLord().reservar(FAMILIA, RESERVA, "noche previa alta − baja en ASIA, datos no mirados")
    dec = LibroLord().resolver(FAMILIA, RESERVA, [("noche_previa", prim["p"])])
    from edgelab.research import a5 as A5
    alto = P[P.noche_previa == 2]
    m, se, p = A5.cluster(alto.index.strftime("%Y%m%d").astype(np.int64).to_numpy(), alto.R.to_numpy(float))
    econ = dict(n=int(len(alto)), R_neto=m, se=se, p=p)
    conf = bool(dec.get("rechazo") and prim["dif"] > 0 and prim["frac_anios_pos"] >= 0.6)
    ver = "CONFIRMADA" if conf else ("REFUTADA" if prim["dif"] <= 0 or prim["dif"] + 1.645 * prim["se"] < MDE else "NO_CONFIRMADA")
    out = dict(preregistro=str(PRE.relative_to(ROOT)), primaria=prim, lord=dec, reserva=res, economico_noche_previa_alta=econ,
               operable=bool(conf and m > 0 and p <= 0.05), veredicto=ver,
               por_instrumento={i: _contraste(g.dropna(subset=["noche_previa"]), "noche_previa") for i, g in T.groupby("inst")},
               descriptivo_noche_misma_sesion_NO_CAUSAL=_contraste(T.dropna(subset=["noche"]), "noche"),
               R_siempre=float(T.R.mean()), n_sesiones=int(len(T)))
    (DIR / "RESULTADO.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("veredicto", "operable")}, default=float), json.dumps(prim, default=float))


MDE = 0.04   # efecto mínimo útil del contraste (R por sesión), fijado en el pre-registro antes de correr


if __name__ == "__main__":
    {"dev": dev, "correr": lambda: correr(sys.argv[2:]), "analizar": analizar}[sys.argv[1]]()
