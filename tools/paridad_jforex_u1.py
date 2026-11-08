#!/usr/bin/env python3
"""Paridad JForex ↔ Python de la señal U1-CRUZADO causal (2026-11-02).

`nt8_tools/jforex/EdgeLabU1Cruzado.java` escribe los ticks que usó (`ticks_USATECHIDXUSD_YYYYMMDD.csv`, también el calentamiento)
y sus señales (`senales_U1_USATECHIDXUSD.csv`). Acá se rearman las velas M1 con esos mismos ticks (mismo mid redondeado y misma
marca de cierre que `fuentes_ticks`), se corre `u1_cruzado.senales` (causal) y se comparan las señales una por una.

  python tools/paridad_jforex_u1.py comparar --ticks "<carpeta>/ticks_USATECHIDXUSD_*.csv" --senales <carpeta>/senales_U1_USATECHIDXUSD.csv
  python tools/paridad_jforex_u1.py java --ticks ticks.csv [--ah 4]   # compila el núcleo Java acá y compara (sin JForex)

Antes no existía: `tools/paridad_oraculo.py` y `paridad_luximb.py` comparan zonas de NT8, no las señales de U1 sobre ticks de JForex.
Sale 1 si alguna señal no coincide.
"""
from __future__ import annotations

import argparse
import glob
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
JAVA = ROOT / "nt8_tools/jforex/EdgeLabU1Cruzado.java"
CLAVE = ["t_cierre_s", "lado"]
NUM = ["lo", "hi", "E", "A"]


def leer_ticks(patron: str) -> pd.DataFrame:
    fs = sorted(glob.glob(patron))
    if not fs: raise FileNotFoundError(patron)
    T = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
    return T.sort_values("time_ms", kind="stable", ignore_index=True)


def contexto(T: pd.DataFrame) -> dict:
    """Mismo armado que `fuentes_ticks._usatech_df` + `grilla_generica.contexto_m1`, con un solo segmento continuo."""
    from edgelab.research.fuentes_ticks import _por_dia, _td
    from edgelab.research.grilla_generica import contexto_m1
    ns = T.time_ms.to_numpy(np.int64) * 1_000_000
    mid = np.round(((T.bid.to_numpy(float) + T.ask.to_numpy(float)) / 2) / 0.01) * 0.01
    vol = (T.bid_vol.to_numpy(float) + T.ask_vol.to_numpy(float))
    return contexto_m1(list(_por_dia(ns, mid, vol, _td(ns))), 0.01)


def senales_python(T: pd.DataFrame, ah_min: float = 8.0) -> pd.DataFrame:
    from edgelab.research import u1_cruzado as U1C
    from edgelab.research import u1_indaga as U
    ctx = contexto(T)
    D = U.disparos(ctx)                                             # causal
    if len(D):
        D = D[(D.ni == U1C.CELDA_U1["ni"]) & (D.xi == U1C.CELDA_U1["xi"]) & (D.A_H >= ah_min)]
    if not len(D): return pd.DataFrame(columns=CLAVE + NUM)
    return pd.DataFrame(dict(t_cierre_s=ctx["t"][D.k.to_numpy()].astype(np.int64), lado=D.lado.astype(int).to_numpy(),
                             lo=D.lo.to_numpy(float), hi=D.hi.to_numpy(float), E=D.E.to_numpy(float), A=D.A.to_numpy(float)))


def comparar(py: pd.DataFrame, jf: pd.DataFrame, desde_s: int | None = None) -> dict:
    """Coincidencia exacta por (cierre, lado, lo, hi) y diferencias numéricas. `desde_s`: ignora las señales anteriores (el
    calentamiento de JForex puede empezar distinto que el archivo)."""
    k = CLAVE + ["lo", "hi"]
    py = py[k + ["E", "A"]].copy(); jf = jf[k + ["E", "A"]].copy()
    if desde_s is not None: py, jf = py[py.t_cierre_s >= desde_s], jf[jf.t_cierre_s >= desde_s]
    for d in (py, jf): d["lo"] = d.lo.round(6); d["hi"] = d.hi.round(6)
    M = py.merge(jf, on=k, how="outer", suffixes=("_py", "_jf"), indicator=True)
    ambas = M[M._merge == "both"]
    dif = float(np.nanmax(np.abs(np.r_[ambas.E_py - ambas.E_jf, ambas.A_py - ambas.A_jf]))) if len(ambas) else 0.0
    return dict(python=len(py), jforex=len(jf), iguales=int(len(ambas)), solo_python=M[M._merge == "left_only"][k].to_dict("records"),
                solo_jforex=M[M._merge == "right_only"][k].to_dict("records"), max_dif_E_A=dif,
                ok=bool(len(ambas) == len(py) == len(jf) and dif < 1e-6))


def nucleo_java(ticks_csv: str, ah_min: float = 8.0) -> pd.DataFrame:
    """Extrae `U1Nucleo` del archivo de la estrategia, lo compila y lo corre sobre `ticks_csv` (sin la API de JForex)."""
    src = JAVA.read_text(encoding="utf-8")
    cuerpo = src.split("// === NUCLEO INICIO ===", 1)[1].split("// === NUCLEO FIN ===", 1)[0].split("\n", 1)[1]
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "U1Nucleo.java").write_text("import java.io.*;\nimport java.util.*;\n" + cuerpo.replace("final class U1Nucleo", "public final class U1Nucleo", 1),
                                               encoding="utf-8")
        subprocess.run(["javac", "-encoding", "UTF-8", "-d", d, str(Path(d) / "U1Nucleo.java")], check=True)
        r = subprocess.run(["java", "-cp", d, "U1Nucleo", ticks_csv, str(ah_min)], check=True, capture_output=True, text=True)
    from io import StringIO
    return pd.read_csv(StringIO(r.stdout))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("comparar", "java"))
    ap.add_argument("--ticks", required=True); ap.add_argument("--senales"); ap.add_argument("--ah", type=float, default=8.0)
    ap.add_argument("--desde-s", type=int)
    a = ap.parse_args()
    T = leer_ticks(a.ticks); py = senales_python(T, a.ah)
    if a.cmd == "java":
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f: T.to_csv(f.name, index=False)
        jf = nucleo_java(f.name, a.ah)
    else:
        jf = pd.read_csv(a.senales, header=None, names=["t_cierre_s", "lado", "lo", "hi", "H", "E", "A", "D", "c", "t_area_s", "fase"])
    r = comparar(py, jf, a.desde_s)
    print({k: (v if not isinstance(v, list) else v[:10]) for k, v in r.items()})
    sys.exit(0 if r["ok"] else 1)


if __name__ == "__main__":
    main()
