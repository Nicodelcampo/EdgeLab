"""Exporta ticks y barras para el visor «normal» de `viewer/hz2a/`.

POR QUE LAS BARRAS SE EXPORTAN Y NO SE ARMAN EN JS
==================================================
Agregar ticks a barras en JavaScript seria un SEGUNDO IMPLEMENTADOR del mismo objeto.
El proyecto ya tiene `build_time_bars` y `build_tick_bars` en `edgelab/bridge/bars.py`,
y `build_tick_bars` no es trivial: reinicia el contador en cada frontera de sesion,
porque NT8 lo hace (TICKBAR-001). Un `arange(n) // N` en la pagina daria barras
distintas de las que mide el motor, y el que diverge seria el que se mira.

Asi que cada resolucion se construye ACA, con el motor, y la pagina solo dibuja.

DOS EJES DISTINTOS, ETIQUETADOS COMO TALES
==========================================
`CLAUDE.md`: «`ticks_per_row` y `bar_spec` son ejes distintos — no confundir un
parametro del indicador con la resolucion de barra sobre la que corre». Por eso el
artefacto separa `tiempo` de `ticks` y la UI no los mezcla en un solo desplegable.

TAMANO
======
Los ticks van con codificacion delta (dt en ms, dprecio en ticks enteros): la enorme
mayoria de los deltas son 0, 1 o -1, asi que el JSON queda chico sin comprimir nada.

Target-free: precio y volumen, nada mas. Sin outcomes, sin holdout.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import pathlib
import subprocess
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge.bars import build_tick_bars, build_time_bars, session_ids  # noqa: E402
from edgelab.bridge.ticks import TickSeries, load_canonical_parquet  # noqa: E402
from edgelab.kaggle.sessions_cme import session_bounds_utc_ns  # noqa: E402

SCHEMA_VERSION = "visor_barras_v1"

MINUTOS = (1, 5, 15, 60)          # eje TIEMPO
TICKS_POR_BARRA = (100, 500, 2000)  # eje TICKS -- otro eje, no otra unidad del mismo
MAX_TICKS = 90_000                # techo del payload; se dice cuanto se recorto

HOLDOUT_FIRST_TRADE_DATE = 20260701
FIREWALL_CUTOFF_NS = session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)[0]


def sha256_archivo(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolver_dir(instrumento, explicito):
    if explicito:
        return pathlib.Path(explicito)
    base = REPO / "data" / "nt8"
    for cand in (base / instrumento, base / ("%s_parquet" % instrumento)):
        if cand.is_dir() and any(cand.glob("%s_*ticks*.parquet" % instrumento)):
            return cand
    raise SystemExit("ABORTA: sin parquets de %s" % instrumento)


def serie_de_barras(bars):
    """BarSeries -> dict de listas planas. Precios en TICKS ENTEROS, sin float."""
    return dict(
        start_ns=[int(x) for x in bars.start_ns],
        end_ns=[int(x) for x in bars.end_ns],
        o=[int(x) for x in bars.open_t], h=[int(x) for x in bars.high_t],
        l=[int(x) for x in bars.low_t], c=[int(x) for x in bars.close_t],
        v=[float(x) for x in bars.volume], n=len(bars.close_t))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrumento", default="6E")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--sesiones", type=int, default=2,
                    help="cuantas sesiones (las ULTIMAS antes del firewall)")
    ap.add_argument("--out", default=str(REPO / "viewer" / "hz2a" / "barras.js"))
    a = ap.parse_args()

    d_in = _resolver_dir(a.instrumento, a.dir)
    print("visor de barras  ·  %s  ·  %s" % (SCHEMA_VERSION, a.instrumento))

    hashes, cols = {}, {k: [] for k in ("ts", "px", "vol", "bid", "ask", "seq")}
    tick_size = None
    for f in sorted(d_in.glob("%s_*ticks*.parquet" % a.instrumento)):
        hashes[f.name] = dict(sha256=sha256_archivo(f))
        p = load_canonical_parquet(f, instrument=a.instrumento)
        for k, v in (("ts", p.ts_ns), ("px", p.price_ticks), ("vol", p.volume),
                     ("bid", p.bid_ticks), ("ask", p.ask_ticks), ("seq", p.sequence)):
            cols[k].append(v)
        tick_size = p.tick_size
        del p
    for k in list(cols):
        cols[k] = np.concatenate(cols[k])
    gc.collect()
    orden = np.argsort(cols["ts"], kind="stable")
    for k in list(cols):
        cols[k] = cols[k][orden]
    del orden
    keep = cols["ts"] < FIREWALL_CUTOFF_NS
    for k in list(cols):
        cols[k] = cols[k][keep]
    print("  ticks tras firewall: %d" % len(cols["ts"]))

    # ultimas N sesiones antes del firewall
    ses = session_ids(cols["ts"])
    ultimas = np.unique(ses)[-a.sesiones:]
    sel = np.isin(ses, ultimas)
    for k in list(cols):
        cols[k] = cols[k][sel]
    n_ses = len(cols["ts"])
    recortado = 0
    if n_ses > MAX_TICKS:
        recortado = n_ses - MAX_TICKS
        for k in list(cols):
            cols[k] = cols[k][-MAX_TICKS:]
    print("  %d sesiones -> %d ticks%s"
          % (len(ultimas), len(cols["ts"]),
             "  (recortados %d por el techo)" % recortado if recortado else ""))

    tk = TickSeries(cols["ts"], cols["px"], cols["vol"], cols["bid"], cols["ask"],
                    cols["seq"], tick_size, a.instrumento, "%s_VISOR" % a.instrumento)

    barras = {"tiempo": {}, "ticks": {}}
    for m in MINUTOS:
        b = build_time_bars(tk, minutes=m)
        barras["tiempo"]["%dm" % m] = serie_de_barras(b)
        print("    %-6s %6d barras" % ("%dm" % m, b.close_t.size))
    for n in TICKS_POR_BARRA:
        b = build_tick_bars(tk, ticks_per_bar=n)
        barras["ticks"]["%dt" % n] = serie_de_barras(b)
        print("    %-6s %6d barras" % ("%dt" % n, b.close_t.size))

    # ticks con codificacion delta: casi todos los deltas son 0, 1 o -1
    ts, px, vl = cols["ts"], cols["px"], cols["vol"]
    ticks = dict(
        t0=int(ts[0]), p0=int(px[0]),
        dt_ms=[int(x) for x in np.diff(ts, prepend=ts[0]) // 1_000_000],
        dp=[int(x) for x in np.diff(px, prepend=px[0])],
        v=[float(x) for x in vl], n=len(ts))

    porcelain = subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines()
    sucios = [l[3:].strip() for l in porcelain if l[:2] != "??"]

    out = dict(
        schema=SCHEMA_VERSION, instrumento=a.instrumento, tick_size=tick_size,
        outcomes_accessed=False, pnl_accessed=False, holdout_included=False,
        nota=("las barras las construye el MOTOR (build_time_bars / build_tick_bars), "
              "no la pagina: `build_tick_bars` reinicia el contador en cada frontera de "
              "sesion (TICKBAR-001) y un `arange(n)//N` en JS daria barras distintas"),
        ejes=("`tiempo` y `ticks` son EJES DISTINTOS (CLAUDE.md), no dos unidades de lo "
              "mismo; la UI no los mezcla en un solo desplegable"),
        sesiones=[int(s) for s in ultimas], ticks_recortados=recortado,
        resoluciones=dict(tiempo=["%dm" % m for m in MINUTOS],
                          ticks=["%dt" % n for n in TICKS_POR_BARRA]),
        procedencia=dict(contratos=hashes, archivos_sucios=sorted(sucios),
                         head_commit=subprocess.check_output(
                             ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()),
        ticks=ticks, barras=barras)

    destino = pathlib.Path(a.out)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("window.BARRAS = " + json.dumps(out) + ";", encoding="utf-8")
    print("  escrito %s  (%.1f MB)" % (destino, destino.stat().st_size / 2**20))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
