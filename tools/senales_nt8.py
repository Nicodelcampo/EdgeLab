#!/usr/bin/env python3
"""Señales de una regla congelada para NT8 Market Replay (`nt8/strategies/EdgeLabSignalReplay.cs`) y comparación de llenados.

Mide paridad de EJECUCIÓN y fricción real (spread + llenado) sin portar el indicador: la señal sale de Python (puede venir de un CFD)
y NT8 sólo opera el futuro. Reutiliza `remedir_canasta_causal._cargar` (estado + acta de la regla) y la etapa ANALIZAR_REGLA.

  python tools/senales_nt8.py lanzar  CVGAP-CFD-NQ            # DESC y réplica, con precios absolutos (Kaggle)
  python tools/senales_nt8.py traer   CVGAP-CFD-NQ            # escribe docs/research/nt8_replay/<cid>/senales.csv
  python tools/senales_nt8.py comparar CVGAP-CFD-NQ <csv_nt8> # paridad de ejecución y fricción, a <cid>/COMPARACION.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from remedir_canasta_causal import _cargar  # noqa: E402

SAL = ROOT / "docs/research/nt8_replay"


def lanzar(cid: str):
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None); cs = run.cuentas(); st, acta = _cargar(cid); sp = st["spec"]; r = acta["regla"]
    d = SAL / cid; d.mkdir(parents=True, exist_ok=True); hf = d / "handles.json"; hs = json.loads(hf.read_text()) if hf.exists() else {}
    for i, (tramo, per) in enumerate((("desc", sp["desc"]), ("oos", sp["oos"]))):
        if tramo in hs: continue
        spec = dict(sp, cid=f"{cid}-NT8-{tramo}", cuenta_kaggle=cs[i % len(cs)])
        params = dict(cortes=acta.get("cortes") or st.get("cortes"), celdas=[r["celda"]], tope=r.get("tope"), operaciones=True, precios=True)
        hs[tramo] = dict(handle=run.lanzar(spec, "ANALIZAR_REGLA", params, [int(per[0]), int(per[1])]), periodo=per, celda=r["celda"],
                         tope=r.get("tope"), ts=time.time())
        hf.write_text(json.dumps(hs, indent=1)); print("lanzada", cid, tramo, hs[tramo]["handle"])


def traer(cid: str) -> pd.DataFrame | None:
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None); d = SAL / cid; hs = json.loads((d / "handles.json").read_text()); partes = []
    for tramo, h in hs.items():
        f = d / f"{tramo}.json"
        if not f.exists():
            e = run.estado(h["handle"]); print(cid, tramo, e)
            if e != "complete": continue
            f.write_text(json.dumps(run.traer(h["handle"]), default=float))
        o = json.loads(f.read_text()).get("operaciones") or {}
        if o: partes.append(pd.DataFrame(o).assign(tramo=tramo))
    if len(partes) < len(hs): return None
    S = pd.concat(partes, ignore_index=True).sort_values("t", kind="stable").reset_index(drop=True)
    S.insert(0, "id", [f"{cid}-{i:04d}" for i in range(len(S))])
    S.to_csv(d / "operaciones_python.csv", index=False)
    S[["id", "t", "lado", "limite", "entrada", "stop", "objetivo"]].astype({"t": "int64"}).to_csv(d / "senales.csv", index=False)
    print(f"{len(S)} señales -> {d / 'senales.csv'} (de {pd.to_datetime(S.t.min(), unit='s')} a {pd.to_datetime(S.t.max(), unit='s')})")
    return S


def comparar(cid: str, csv_nt8: str) -> dict:
    """Une cada señal con su ENTRADA y SALIDA de NT8. Fricción de entrada en puntos = (llenado NT8 − entrada Python) × lado (positivo =
    peor para nosotros); de salida, contra el nivel de stop u objetivo cuando sale por ellos. Paridad = mismo motivo de salida."""
    from edgelab.research.embudo_runners import friccion
    d = SAL / cid; P = pd.read_csv(d / "operaciones_python.csv"); N = pd.read_csv(csv_nt8)
    N["id"] = N["id"].fillna("").astype(str)
    vacio = (N.evento == "ENTRADA") & (N["id"] == "")                          # v1.0 de la estrategia: el id quedó en `motivo`
    N.loc[vacio, "id"] = N.loc[vacio, "motivo"]
    st, _ = _cargar(cid); ejec = st["spec"].get("ejecucion") or st["spec"]["sensor"]; fr_base, _ = friccion(ejec)
    ent = N[N.evento == "ENTRADA"].drop_duplicates("id").set_index("id"); sal = N[N.evento == "SALIDA"].groupby("id").last()
    omit = set(N.loc[N.evento.isin(["OMITIDA", "CANCELADA"]), "id"])
    M = P.set_index("id").join(ent[["precio", "t_utc"]].rename(columns={"precio": "e_nt8", "t_utc": "tf_nt8"}))
    M = M.join(sal[["precio", "motivo", "t_utc"]].rename(columns={"precio": "x_nt8", "t_utc": "tx_nt8"}))
    M = M[M.index.isin(N.loc[N.evento == "SEÑAL", "id"])]                      # sólo las fechas que se corrieron en el replay
    ok = M.e_nt8.notna() & M.x_nt8.notna()
    m = M[ok].copy()
    m["slip_entrada"] = (m.e_nt8 - m.entrada) * m.lado
    nivel = np.where(m.motivo == "STOP", m.stop, np.where(m.motivo == "OBJETIVO", m.objetivo, np.nan))
    m["slip_salida"] = (nivel - m.x_nt8) * m.lado                              # positivo = salió peor que el nivel
    m["pnl_nt8"] = (m.x_nt8 - m.e_nt8) * m.lado
    out = dict(cid=cid, senales_en_replay=int(len(M)), operadas=int(ok.sum()), omitidas_o_canceladas=int(M.index.isin(omit).sum()),
               friccion_canonica_rt_pts=fr_base,
               slip_entrada_pts=dict(media=float(m.slip_entrada.mean()), mediana=float(m.slip_entrada.median()), p90=float(m.slip_entrada.quantile(.9))),
               slip_salida_stop_pts=float(m.loc[m.motivo == "STOP", "slip_salida"].mean()) if (m.motivo == "STOP").any() else None,
               slip_salida_objetivo_pts=float(m.loc[m.motivo == "OBJETIVO", "slip_salida"].mean()) if (m.motivo == "OBJETIVO").any() else None,
               motivos_nt8=m.motivo.value_counts().to_dict(),
               pnl_nt8_bruto_pts_medio=float(m.pnl_nt8.mean()), neto_python_pts_medio=float(m.neto.mean()),
               nota="slip en puntos del futuro; sumar entrada + salida y comparar con la fricción canónica (que además incluye comisión)")
    (d / "COMPARACION.json").write_text(json.dumps(out, indent=1, default=float)); m.to_csv(d / "comparacion_por_operacion.csv")
    print(json.dumps(out, indent=1, default=float)); return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("lanzar", "traer", "comparar")); ap.add_argument("cid"); ap.add_argument("csv", nargs="?")
    a = ap.parse_args()
    lanzar(a.cid) if a.cmd == "lanzar" else (traer(a.cid) if a.cmd == "traer" else comparar(a.cid, a.csv))
