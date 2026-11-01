#!/usr/bin/env python3
"""Curvas de equity IS + OOS de las celdas congeladas (pistas/candidatas) de campañas del embudo (2026-11-01, pedido de Nico: «de las
que mejor salieron en las corridas recientes aunque no pasen todos los filtros, hacé backtesting con la herramienta y pasame las equity
curves incluyendo IS y OOS, con polars»).

Reutiliza la etapa ANALIZAR_REGLA (mismo motor que eligió las celdas: llenado, tope, ticks) con `operaciones=True`, como
`tools/analizar_embudo.py` y `tools/variante_tau_actas.py`. Período: inicio del DESC → 2026-09-30 (nunca el holdout). EXPLORATORIO:
las celdas ya se miraron; nada se promueve desde acá.

  python tools/equity_pistas.py lanzar CID [CID ...]
  python tools/equity_pistas.py traer
  python tools/equity_pistas.py graficar          # polars + matplotlib -> PNG y CSV por campaña
"""
import argparse
import glob
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
SALIDA = ROOT / "docs/research/equity_pistas_20261101"
HASTA = 20260930
SERIE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]   # dataviz: categóricas en orden fijo


def _estado(cid):
    f = sorted(glob.glob(str(ROOT / f"docs/research/*/embudo/{cid}/estado.json")))
    if not f: raise SystemExit(f"sin estado.json de {cid}")
    return json.loads(Path(f[0]).read_text(encoding="utf-8"))


def celdas(st) -> list:
    pr = st.get("pistas_replica") or {}
    out = [list(c) for c in (st.get("candidatas") or [])] + [list(c) for c in (pr.get("celdas") or [])]
    return [list(c) for c in dict.fromkeys(tuple(c) for c in out)]


def lanzar(cids):
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None); SALIDA.mkdir(parents=True, exist_ok=True); hf = SALIDA / "handles.json"
    hs = json.loads(hf.read_text()) if hf.exists() else {}; cuentas = run.cuentas()
    for cid in cids:
        if cid in hs: continue
        st = _estado(cid); sp = dict(st["spec"], cid=cid + "-EQ"); cs = celdas(st)
        params = dict(cortes=st["cortes"], celdas=cs, operaciones=True); per = [int(st["spec"]["desc"][0]), HASTA]; h = None
        for i in range(len(cuentas)):
            sp["cuenta_kaggle"] = cuentas[(len(hs) + i) % len(cuentas)]
            try: h = run.lanzar(sp, "ANALIZAR_REGLA", params, per); break
            except RuntimeError as e: print("no se lanzó", cid, sp["cuenta_kaggle"], str(e)[-150:])
        if h is None: continue
        hs[cid] = dict(handle=h, periodo=per, n_celdas=len(cs), oos=st["spec"]["oos"], ts=time.time())
        hf.write_text(json.dumps(hs, indent=1)); print("lanzada", cid, len(cs), "celdas", h)


def traer():
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None); hf = SALIDA / "handles.json"; hs = json.loads(hf.read_text())
    for cid, h in hs.items():
        if (SALIDA / f"{cid}.json").exists(): continue
        e = run.estado(h["handle"]); print(cid, e)
        if e == "complete": (SALIDA / f"{cid}.json").write_text(json.dumps(run.traer(h["handle"]), indent=1, default=float))


def curvas(r: dict, oos_desde: int):
    """Canasta igual-ponderada (media por pista y sesión, como `escalera.canasta_pistas`) y su equity acumulada, IS y OOS."""
    import polars as pl
    o = pl.DataFrame(r["operaciones"]).with_columns(pl.col("ses").cast(pl.Int64), pl.col("celda").cast(pl.Int64))
    k = len(r["reportes"])
    s = (o.group_by("ses").agg((pl.col("neto").sum() / k).alias("canasta"), pl.len().alias("ops")).sort("ses")
         .with_columns(pl.col("canasta").cum_sum().alias("equity"), (pl.col("ses") >= oos_desde).alias("oos")))
    return s


def graficar():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import polars as pl
    hs = json.loads((SALIDA / "handles.json").read_text())
    listos = [c for c in hs if (SALIDA / f"{c}.json").exists()]
    fig, axes = plt.subplots(len(listos), 1, figsize=(10, 2.6 * len(listos)), squeeze=False)
    resumen = []
    for ax, cid in zip(axes[:, 0], listos):
        r = json.loads((SALIDA / f"{cid}.json").read_text()); oos0 = int(hs[cid]["oos"][0])
        s = curvas(r, oos0); s.write_csv(SALIDA / f"{cid}_equity.csv")
        fechas = [str(x) for x in s["ses"].to_list()]; x = list(range(len(fechas)))
        ax.plot(x, s["equity"].to_list(), color=SERIE[0], lw=2)
        i0 = next((i for i, v in enumerate(s["oos"].to_list()) if v), len(x))
        ax.axvspan(i0, len(x), color="#e8e7e1", zorder=0); ax.axhline(0, color="#9b9a91", lw=0.8)
        ax.text(i0 + 1, ax.get_ylim()[1], " OOS", va="top", fontsize=8, color="#5f5e57")
        ax.text(1, ax.get_ylim()[1], "IS (DESC)", va="top", fontsize=8, color="#5f5e57")
        tic = list(range(0, len(x), max(1, len(x) // 6))); ax.set_xticks(tic, [fechas[i] for i in tic], fontsize=8)
        ist, oos = s.filter(~pl.col("oos")), s.filter(pl.col("oos"))
        fila = dict(cid=cid, pistas=len(r["reportes"]), sesiones_is=ist.height, media_is=round(ist["canasta"].mean() or 0, 2),
                    sesiones_oos=oos.height, media_oos=round(oos["canasta"].mean() or 0, 2), total_is=round(ist["canasta"].sum(), 1),
                    total_oos=round(oos["canasta"].sum(), 1))
        resumen.append(fila)
        ax.set_title(f"{cid}: canasta de {fila['pistas']} celda(s), pts/sesión — IS {fila['media_is']:+.2f} · OOS {fila['media_oos']:+.2f}",
                     fontsize=10, loc="left")
        ax.spines[["top", "right"]].set_visible(False); ax.grid(axis="y", color="#e8e7e1", lw=0.6)
    fig.suptitle("Equity acumulada (puntos netos de costos), desarrollo hasta 2026-09-30 — exploratorio, celdas ya miradas", fontsize=11, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(SALIDA / "EQUITY_IS_OOS.png", dpi=130)
    pl.DataFrame(resumen).write_csv(SALIDA / "RESUMEN.csv"); print(pl.DataFrame(resumen))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("lanzar", "traer", "graficar")); ap.add_argument("cids", nargs="*")
    a = ap.parse_args()
    {"lanzar": lambda: lanzar(a.cids), "traer": traer, "graficar": graficar}[a.cmd]()


if __name__ == "__main__":
    main()
