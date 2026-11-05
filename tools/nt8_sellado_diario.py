#!/usr/bin/env python3
"""Ticks diarios de NT8 -> dataset sellado de Kaggle (2026-11-01, Nico: «para los ticks tengo NT8»; «el SV1 tiene que usar Kaggle»).

Corre en la PC de Nico, la que tiene NT8. Se agenda una vez por día después del cierre de CME
(docs/infra/LOGGER_NT8_DIARIO.md). Toma los `.Last.utc.txt` del logger en vivo (`nt8_tools/EdgeLabLiveTickLogger.cs`) y, para
rellenar huecos, los de EdgeLabTickHistory (mismo formato). Arma una sesión CME por archivo, `<INST>/<INST>_<yyyymmdd>_ticks.parquet`,
con el esquema que leen los kernels sellados (`fuentes_ticks.bloques_nq_sellado`). Después publica una versión nueva del dataset
sellado. La cartera del Debian lo lee en Kaggle al día siguiente (`edgelab/cartera/motor_kaggle.py`).

Reglas:
- Sólo sesiones desde la frontera del holdout (2026-10-01) y ya cerradas (16:10 de Chicago del día de la sesión).
- Una sesión INCOMPLETA no se sube: primer tick más de 15 min después de la apertura de las 17:00 CT, o último más de 15 min antes
  del cierre de las 16:00 CT. Esto deja afuera, por ejemplo, un NT8 caído a media sesión. `--forzar` la acepta, por ejemplo en un
  feriado con cierre temprano, y queda anotado en el manifiesto.
- Un día ya escrito no se reescribe (inmutable), salvo `--reemplazar`.
- Con dos contratos el mismo día (el roll), entra el de más volumen. Nunca se mezclan.
- No se lee ni se calcula ningún resultado: sólo ticks.

  python tools/nt8_sellado_diario.py iniciar   --espejo C:\\EdgeLab\\sellado            # una vez: baja el dataset actual
  python tools/nt8_sellado_diario.py convertir --espejo C:\\EdgeLab\\sellado --fuente C:\\EdgeLab\\tick_live [--fuente C:\\EdgeLab\\tick_history]
  python tools/nt8_sellado_diario.py subir     --espejo C:\\EdgeLab\\sellado
  python tools/nt8_sellado_diario.py diario    --espejo ... --fuente ...                 # convertir + subir (lo que agenda el Programador de tareas)
"""
from __future__ import annotations

import argparse
import glob
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from edgelab.holdout import HOLDOUT_PRIMERA_SESION_INT  # noqa: E402
from edgelab.research.fuentes_ticks import TICK_FUTURO, _td  # noqa: E402

DATASET = "nicolasbuttaro/edgelab-holdout-sellado"
INSTRUMENTOS = ("NQ", "ES", "YM", "GC")
TOL_MIN = 15
COLUMNAS = ["ts_utc_ns", "price_ticks", "volume", "trade_date", "contract", "bid_ticks", "ask_ticks"]


def leer_txt(f: Path) -> pd.DataFrame:
    """Un `.Last.utc.txt` (también abierto: la última línea a medio escribir se descarta) -> ts_utc_ns, last, bid, ask, volume."""
    from build_nt8_ticks import parsear_lote
    df = pd.read_csv(f, sep=";", header=None, dtype=str, on_bad_lines="skip", engine="python")
    if df.shape[1] < 5 or not len(df): return pd.DataFrame(columns=["ts_utc_ns", "last", "bid", "ask", "volume"])
    for k in (1, 2, 3, 4): df[k] = pd.to_numeric(df[k], errors="coerce")
    ts, last, bid, ask, vol, _ = parsear_lote(df)
    return pd.DataFrame(dict(ts_utc_ns=ts, last=last, bid=bid, ask=ask, volume=vol.astype(np.int64)))


def _ya_hechas(espejo) -> set:
    return {(p.name.split("_")[0], int(p.name.split("_")[1])) for p in Path(espejo).glob("*_*_ticks.parquet") if p.name.split("_")[1].isdigit()} if espejo else set()


def sesiones(fuentes, ahora_ns: int, hechas: set = frozenset()) -> dict:
    """{(inst, trade_date): {contrato: DataFrame}} de las sesiones cerradas >= frontera, desde todas las carpetas fuente. Un archivo
    del día UTC u sólo se lee si alguna de las sesiones que toca (u y u+1) falta en el espejo."""
    out = {}
    for raiz in fuentes:
        for carpeta in sorted(p for p in Path(raiz).iterdir() if p.is_dir()):
            contrato = carpeta.name.replace("_", " "); inst = contrato.split(" ")[0]
            if inst not in INSTRUMENTOS: continue
            sig = lambda u: int((pd.Timestamp(str(u)) + pd.Timedelta(days=1)).strftime("%Y%m%d"))
            fs = [f for f in sorted(carpeta.glob("*.Last.utc.txt")) if f.name[:8].isdigit() and int(f.name[:8]) >= HOLDOUT_PRIMERA_SESION_INT - 1
                  and not {(inst, int(f.name[:8])), (inst, sig(int(f.name[:8])))} <= hechas]
            partes = [leer_txt(f) for f in fs]
            t = pd.concat(partes, ignore_index=True) if partes else None
            if t is None or not len(t): continue
            t["trade_date"] = _td(t.ts_utc_ns.to_numpy())
            for td, g in t[t.trade_date >= HOLDOUT_PRIMERA_SESION_INT].groupby("trade_date"):
                if cierre_ns(int(td)) + 10 * 60 * 10**9 > ahora_ns: continue                     # sesión todavía abierta
                d = out.setdefault((inst, int(td)), {})
                d[contrato] = pd.concat([d[contrato], g]) if contrato in d else g
    return out


def _chicago_ns(yyyymmdd: int, hora: int, dias: int = 0) -> int:
    d = pd.Timestamp(str(yyyymmdd)) + pd.Timedelta(days=dias)
    return pd.Timestamp(d.year, d.month, d.day, hora, tz="America/Chicago").value


def apertura_ns(td: int) -> int: return _chicago_ns(td, 17, -1)
def cierre_ns(td: int) -> int: return _chicago_ns(td, 16)


def armar(inst: str, td: int, por_contrato: dict) -> tuple:
    """(DataFrame canónico de la sesión, chequeo de cobertura). Si hay varios contratos, entra el de más volumen."""
    contrato = max(por_contrato, key=lambda c: int(por_contrato[c].volume.sum()))
    g = por_contrato[contrato].drop_duplicates().sort_values("ts_utc_ns", kind="stable")       # dos fuentes con el mismo tick: una vez
    tk = TICK_FUTURO[inst]
    q = lambda x: np.where(x > 0, np.round(x / tk), 0).astype(np.int64)
    df = pd.DataFrame(dict(ts_utc_ns=g.ts_utc_ns.to_numpy(np.int64), price_ticks=np.round(g["last"].to_numpy() / tk).astype(np.int64),
                           volume=g.volume.to_numpy(np.int64), trade_date=np.full(len(g), td, np.int64), contract=contrato,
                           bid_ticks=q(g.bid.to_numpy()), ask_ticks=q(g.ask.to_numpy())))
    tol = TOL_MIN * 60 * 10**9
    cob = dict(primero_utc_ns=int(df.ts_utc_ns.min()), ultimo_utc_ns=int(df.ts_utc_ns.max()),
               tarde_min=round((df.ts_utc_ns.min() - apertura_ns(td)) / 6e10, 1), temprano_min=round((cierre_ns(td) - df.ts_utc_ns.max()) / 6e10, 1))
    cob["completa"] = bool(df.ts_utc_ns.min() <= apertura_ns(td) + tol and df.ts_utc_ns.max() >= cierre_ns(td) - tol)
    cob["contratos"] = {c: int(v.volume.sum()) for c, v in por_contrato.items()}
    return df, cob


def convertir(espejo: Path, fuentes, forzar=(), reemplazar=False, ahora_ns=None) -> list:
    ahora_ns = ahora_ns or datetime.now(timezone.utc).timestamp() * 1e9
    if not (espejo / "SELLADO.txt").exists(): raise SystemExit(f"{espejo} no es el espejo del dataset sellado (falta SELLADO.txt): correr `iniciar`")
    hechos = []
    for (inst, td), por_contrato in sorted(sesiones(fuentes, int(ahora_ns), set() if reemplazar else _ya_hechas(espejo)).items()):
        dest = espejo / f"{inst}_{td}_ticks.parquet"                                         # plano, como los exports por contrato
        if dest.exists() and not reemplazar: continue
        df, cob = armar(inst, td, por_contrato)
        fila = dict(instrumento=inst, sesion=td, ticks=len(df), contrato=df.contract.iloc[0], **cob)
        if not cob["completa"] and td not in forzar:
            fila["estado"] = "INCOMPLETA_NO_SUBIDA"; hechos.append(fila); continue
        dest.parent.mkdir(parents=True, exist_ok=True); tmp = dest.with_suffix(".tmp")
        df[COLUMNAS].to_parquet(tmp, index=False, compression="zstd"); tmp.replace(dest)
        fila["estado"] = "FORZADA" if not cob["completa"] else "OK"; hechos.append(fila)
    if hechos:
        with open(espejo / "SELLADO_DIARIO.jsonl", "a", encoding="utf-8") as fh:
            for f in hechos: fh.write(json.dumps(dict(f, ts=datetime.now(timezone.utc).isoformat(timespec="seconds")), default=int) + "\n")
    return hechos


def kaggle(*args) -> str:
    r = subprocess.run(["kaggle", *args], capture_output=True, text=True)
    if r.returncode != 0: raise SystemExit(f"kaggle {' '.join(args[:2])} falló: {(r.stdout + r.stderr)[-400:]}")
    return r.stdout


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("iniciar", "convertir", "subir", "diario"))
    ap.add_argument("--espejo", required=True, type=Path); ap.add_argument("--fuente", action="append", default=[])
    ap.add_argument("--dataset", default=DATASET); ap.add_argument("--forzar", type=int, action="append", default=[])
    ap.add_argument("--reemplazar", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "iniciar":
        a.espejo.mkdir(parents=True, exist_ok=True); kaggle("datasets", "download", a.dataset, "-p", str(a.espejo), "--unzip")
        kaggle("datasets", "metadata", a.dataset, "-p", str(a.espejo))
        print("espejo listo:", sorted(p.name for p in a.espejo.iterdir())); return
    if a.cmd in ("convertir", "diario"):
        if not a.fuente: raise SystemExit("falta --fuente (carpeta del logger)")
        h = convertir(a.espejo, a.fuente, set(a.forzar), a.reemplazar)
        for f in h: print(f["estado"], f["instrumento"], f["sesion"], f["ticks"], "ticks", f["contrato"], f"tarde {f['tarde_min']} min, temprano {f['temprano_min']} min")
        if a.cmd == "convertir": return
        if not any(f["estado"] != "INCOMPLETA_NO_SUBIDA" for f in h): print("nada nuevo para subir"); return
    if not (a.espejo / "dataset-metadata.json").exists(): raise SystemExit("falta dataset-metadata.json en el espejo: correr `iniciar`")
    print(kaggle("datasets", "version", "-p", str(a.espejo), "-m", f"sesiones NT8 {datetime.now(timezone.utc):%Y-%m-%d}", "--dir-mode", "zip"))


if __name__ == "__main__":
    main()
