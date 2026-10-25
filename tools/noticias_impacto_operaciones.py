"""Cuenta (target-free) cuántas operaciones/eventos ya publicados cruzan una ventana de noticia (`edgelab.noticias`).

Sólo tiempos: no lee ni agrega columnas de P&L. Escribe `docs/research/noticias_20261025/IMPACTO_FILTRO_NOTICIAS.json`.

- U1-CRUZADO (`docs/research/areas_expansion_20261022/u1/U1_CRUZADO_*_operaciones.csv`): el CSV trae `t` (cierre de la
  vela de decisión, s UTC) y `ses`, pero NO la hora de salida. Se dan dos cotas: **entrada** (el instante `t`: la orden E1A
  se llena en el primer tick de la vela siguiente) y **tenencia máxima** ([t, min(t + 241 min, cierre 16:00 CT de `ses`)],
  el tope de 240 barras de `areas_expansion.simular` más la vela de llenado). El cruce real está entre las dos.
- LUX-IMB: no hay CSV de operaciones con entrada y salida. Se cuentan los **eventos de decisión** de los archivos de
  features (`desc_m8/feat_*.csv`, `desc_m10/feat_*.csv`: `dia` + `hora` decimal en America/New_York, cierre de la vela
  de confirmación) cuyo instante cae en una ventana.

Uso: `python tools/noticias_impacto_operaciones.py`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from edgelab import noticias  # noqa: E402
from edgelab.holdout import HOLDOUT_APERTURA_UTC_NS  # noqa: E402

U1 = ROOT / "docs" / "research" / "areas_expansion_20261022" / "u1"
LUX = ROOT / "docs" / "research" / "luximb_parity_20261020"
SALIDA = ROOT / "docs" / "research" / "noticias_20261025" / "IMPACTO_FILTRO_NOTICIAS.json"
NS = 1_000_000_000
VENTANAS = [(1, 1), (2, 2), (5, 5)]
IMPACTOS = {"tier1": ("tier1",), "tier1+tier2": ("tier1", "tier2")}
COLUMNAS_U1 = ["k_us", "t", "ses", "ejecucion", "motivo", "j_nq"]       # sólo tiempos e identidad: nada de P&L


def _cierre_sesion_ns(ses: pd.Series) -> np.ndarray:
    d = pd.to_datetime(ses.astype(str), format="%Y%m%d")
    return (d + pd.Timedelta(hours=16)).dt.tz_localize("America/Chicago").dt.tz_convert("UTC").dt.as_unit("ns").astype("int64").to_numpy()


def _eventos_tocados(a, b, w) -> dict:
    """Qué eventos explican los cruces (cuenta de operaciones por tramo de ventana tocado)."""
    ini, fin, ev = w["inicio_ns"].to_numpy(), w["fin_ns"].to_numpy(), w["eventos"].to_numpy()
    out: dict[str, int] = {}
    for x, y in zip(a, b):
        i = np.searchsorted(fin, x, side="left")
        while i < len(ini) and ini[i] <= y:
            for e in ev[i].split("+"):
                out[e] = out.get(e, 0) + 1
            i += 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def u1() -> dict:
    res = {}
    for f in sorted(U1.glob("U1_CRUZADO_*_operaciones.csv")):
        df = pd.read_csv(f, usecols=COLUMNAS_U1, dtype={"motivo": str}, keep_default_na=False)
        t_ns = df["t"].to_numpy(np.int64) * NS
        assert (t_ns < HOLDOUT_APERTURA_UTC_NS).all(), "operación en el holdout"
        operada = (df["motivo"] == "") & (df["j_nq"].astype(str) != "")
        fin_max = np.minimum(t_ns + 241 * 60 * NS, _cierre_sesion_ns(df["ses"]))
        fin_max = np.maximum(fin_max, t_ns)
        bloque = {}
        for ej, g in df.groupby("ejecucion"):
            m = (df["ejecucion"] == ej).to_numpy()
            mo = m & operada.to_numpy()
            fila = dict(filas=int(m.sum()), operadas=int(mo.sum()), sesiones_operadas=int(df.loc[mo, "ses"].nunique()))
            for nom, imp in IMPACTOS.items():
                for an, de in VENTANAS:
                    w = noticias.ventanas_bloqueadas(an, de, impactos=imp)
                    ent = noticias.cruza_noticia(t_ns[mo], t_ns[mo], ventanas=w)
                    ten = noticias.cruza_noticia(t_ns[mo], fin_max[mo], ventanas=w)
                    clave = f"{nom}_pm{an}" if an == de else f"{nom}_{an}_{de}"
                    fila[clave] = dict(entrada_en_ventana=int(ent.sum()), prop_entrada=round(float(ent.mean()), 4) if mo.any() else None,
                                       tenencia_max_cruza=int(ten.sum()), prop_tenencia_max=round(float(ten.mean()), 4) if mo.any() else None)
                    if nom == "tier1" and an == 1:
                        fila[clave]["eventos_tenencia_max"] = _eventos_tocados(t_ns[mo], fin_max[mo], w)
            bloque[ej] = fila
        res[f.name] = dict(desde=str(pd.to_datetime(t_ns.min(), utc=True)), hasta=str(pd.to_datetime(t_ns.max(), utc=True)), por_ejecucion=bloque)
    return res


def luximb() -> dict:
    res = {}
    archivos = [f for f in sorted(LUX.glob("desc_m8/feat_*.csv")) + sorted(LUX.glob("desc_m10/feat_*.csv"))
                if f.name != "feat_NQ_ES.csv"]      # feat_NQ_ES = feat_NQ + feat_ES (no contar dos veces)
    for f in archivos:
        df = pd.read_csv(f, usecols=["inst", "dia", "hora"])
        minutos = np.round(df["hora"].to_numpy(float) * 60).astype(int)
        ts = (pd.to_datetime(df["dia"]) + pd.to_timedelta(minutos, unit="m")).dt.tz_localize("America/New_York", ambiguous="NaT",
                                                                                          nonexistent="NaT")
        ok = ts.notna().to_numpy()
        t_ns = ts[ok].dt.tz_convert("UTC").dt.as_unit("ns").astype("int64").to_numpy()
        dentro = t_ns < HOLDOUT_APERTURA_UTC_NS
        t_ns = t_ns[dentro]
        for inst, g in pd.Series(t_ns).groupby(df["inst"][ok][dentro].to_numpy()):
            x = g.to_numpy(np.int64)
            fila = dict(archivo=str(f.relative_to(ROOT)), eventos=int(len(x)), sin_hora_valida=int((~ok).sum()),
                        desde=str(pd.to_datetime(x.min(), utc=True).date()), hasta=str(pd.to_datetime(x.max(), utc=True).date()))
            for nom, imp in IMPACTOS.items():
                for an, de in VENTANAS:
                    w = noticias.ventanas_bloqueadas(an, de, impactos=imp)
                    c = noticias.cruza_noticia(x, x, ventanas=w)
                    fila[f"{nom}_pm{an}"] = dict(decision_en_ventana=int(c.sum()), prop=round(float(c.mean()), 4))
            res[f"{f.parent.name}/{f.name}:{inst}"] = fila
    return res


def main() -> int:
    out = dict(generado_por="tools/noticias_impacto_operaciones.py", calendario=str(noticias.RUTA.relative_to(ROOT)),
               nota="target-free: sólo tiempos; ninguna columna de P&L leída", u1_cruzado=u1(), luximb_eventos=luximb())
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(SALIDA.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
