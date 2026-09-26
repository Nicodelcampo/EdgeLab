#!/usr/bin/env python3
"""TICKBAR-001 B2b — comparador que CLASIFICA la causa del mismatch en tick bars.

Lee el ledger de `nt8/TickBarDiag.cs` y reconstruye lo mismo del lado Python
sobre el parquet canónico F2. Devuelve **una** clasificación:

    STREAM_MISMATCH       H1 — no ven la misma secuencia de trades
    BAR_BUILDER_MISMATCH  H2 — mismo stream, cortes de barra distintos
    ATTRIBUTION_MISMATCH  H3 — mismos cortes, tick fronterizo mal atribuido
    MIXED_MISMATCH        H4 — más de una firma a la vez
    NO_MISMATCH           los dos ledgers coinciden

**No implementa ningún fix** (§B3 del manifiesto: prohibido arreglar antes de
clasificar). Sólo diagnostica.

Uso:
    python tools/tickbar_diag.py oracles/tickbar_diag.csv \
        --parquet data/nt8/6E/6E_09-26_ticks.parquet --contract "6E 09-26" --tick-n 25
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from edgelab.bridge import bars as bars_mod, ticks as ticks_mod   # noqa: E402

FNV_BASIS = 1469598103934665603
MIX = 1000003
MASK = (1 << 64) - 1


def mix(h, x):
    """Espejo EXACTO de `Mix` del .cs: aritmética ulong con wrap natural."""
    return (h * MIX + (x & MASK)) & MASK


def stream_digest(price_ticks, vol_ints):
    h = FNV_BASIS
    for p, v in zip(price_ticks, vol_ints):
        h = mix(mix(h, int(p)), int(v))
    return h


def fp_digest(ask, bid):
    h = FNV_BASIS
    for k in sorted(set(ask) | set(bid)):
        h = mix(h, int(k))
        h = mix(h, int(round(ask.get(k, 0.0) * 100)))
        h = mix(h, int(round(bid.get(k, 0.0) * 100)))
    return h


def read_ledger(path):
    """Devuelve (eventos, barras, meta) del CSV de TickBarDiag."""
    ev, ba, meta = [], [], {}
    for ln in open(path, encoding="utf-8-sig"):
        ln = ln.rstrip("\n")
        if ln.startswith("#"):
            for kv in ln.lstrip("# ").split(","):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    meta[k.strip()] = v.strip()
            continue
        f = ln.split(",")
        if f[0] == "E":
            ev.append(dict(seq=int(f[1]), ts_ticks=int(f[2]), ts_iso=f[3],
                           price_tick=int(f[4]), vol_int=int(f[5]),
                           session=int(f[6]), digest=int(f[7])))
        elif f[0] == "B":
            ba.append(dict(bar=int(f[1]), seq_first=int(f[2]), seq_last=int(f[3]),
                           n_events=int(f[4]), ts_ticks=int(f[5]), ts_iso=f[6],
                           o=int(f[7]), h=int(f[8]), l=int(f[9]), c=int(f[10]),
                           vol_bar=int(f[11]), vol_fp=int(f[12]),
                           digest_fp=int(f[13]), session=int(f[14])))
    return ev, ba, meta


def _ns(iso):
    return int(dt.datetime.fromisoformat(iso[:26]).replace(
        tzinfo=dt.timezone.utc).timestamp() * 1e9)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Clasificador de mismatch en tick bars")
    ap.add_argument("ledger")
    ap.add_argument("--parquet", required=True)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--tick-n", type=int, required=True)
    ap.add_argument("--tz-shift-hours", type=float, default=0.0,
                    help="offset del reloj del chart NT8 respecto de UTC")
    a = ap.parse_args(argv)

    ev, ba, meta = read_ledger(a.ledger)
    if not ev or not ba:
        print("FRENAR: el ledger no tiene eventos (%d) o barras (%d)" % (len(ev), len(ba)))
        return 1
    print("=" * 78)
    print("TICKBAR-001 — clasificacion de la causa del mismatch en barras de tick")
    print("=" * 78)
    print("ledger: %s" % a.ledger)

    # --- El ledger DEBE declarar la misma resolucion que se pide comparar -----
    # Incidente 2026-07-25: se corrio --tick-n 25 sobre un ledger de 10 ticks
    # (el .cs v1.0 habia pisado la captura de 25t al cambiar el chart). El
    # resultado fue un BAR_BUILDER_MISMATCH espurio: comparaba barras Python de
    # 25 contra barras NT8 de 10. Sin este gate, un archivo mal rotulado se lee
    # como un hallazgo.
    per = meta.get("bars_period", "?")
    val = meta.get("bars_value", "?")
    if per != "Tick":
        print("FRENAR: el ledger declara bars_period=%r; TICKBAR-001 compara "
              "barras de TICK." % per)
        return 1
    if str(val) != str(a.tick_n):
        print("FRENAR: el ledger declara bars_value=%s pero se pidio --tick-n %d."
              % (val, a.tick_n))
        print("        Un ledger mal rotulado produce una clasificacion FALSA.")
        print("        Verificar la captura antes de reintentar; no forzar el parametro.")
        return 1
    print("  meta: %s" % {k: meta[k] for k in list(meta)[:6]})
    print("  eventos NT8: %d   barras NT8: %d (bar %d..%d)"
          % (len(ev), len(ba), ba[0]["bar"], ba[-1]["bar"]))

    shift = int(a.tz_shift_hours * 3600 * 1e9)
    w0 = _ns(ev[0]["ts_iso"]) + shift
    w1 = _ns(ev[-1]["ts_iso"]) + shift + 1
    tk = ticks_mod.load_canonical_parquet(a.parquet, contract=a.contract,
                                          start_utc_ns=w0, end_utc_ns=w1)
    print("  ventana UTC: %s -> %s   ticks Python en ventana: %d"
          % (ev[0]["ts_iso"], ev[-1]["ts_iso"], len(tk)))

    # ---------------- H1: el STREAM ---------------------------------------- #
    py_p = tk.price_ticks.astype(np.int64)
    py_v = np.round(tk.volume * 100).astype(np.int64)
    nt_p = np.array([e["price_tick"] for e in ev], dtype=np.int64)
    nt_v = np.array([e["vol_int"] for e in ev], dtype=np.int64)
    n = min(len(py_p), len(nt_p))
    same_len = len(py_p) == len(nt_p)
    first_div = None
    if n:
        d = np.flatnonzero((py_p[:n] != nt_p[:n]) | (py_v[:n] != nt_v[:n]))
        if len(d):
            first_div = int(d[0])
    stream_ok = same_len and first_div is None
    print("\n[H1] STREAM")
    print("    eventos: NT8=%d  Python=%d  %s" % (
        len(nt_p), len(py_p), "IGUALES" if same_len else "DIFIEREN"))
    if first_div is None:
        print("    primer indice divergente: ninguno en los %d comunes" % n)
    else:
        i = first_div
        print("    primer indice divergente: %d" % i)
        print("       NT8   price_tick=%d vol_int=%d" % (nt_p[i], nt_v[i]))
        print("       Python price_tick=%d vol_int=%d" % (py_p[i], py_v[i]))
    dg_nt = ev[-1]["digest"]
    dg_py = stream_digest(py_p[:len(nt_p)], py_v[:len(nt_p)])
    print("    digest acumulado: NT8=%d  Python=%d  %s" % (
        dg_nt, dg_py, "IGUAL" if dg_nt == dg_py else "DIFIERE"))
    print("    -> H1 %s" % ("DESCARTADA" if stream_ok else "CONFIRMADA"))

    # ---------------- H2: los CORTES de barra ------------------------------- #
    bars = bars_mod.build_tick_bars(tk, a.tick_n)
    py_first = np.searchsorted(bars.tick_bar_idx, np.arange(len(bars)), "left")
    py_last = np.searchsorted(bars.tick_bar_idx, np.arange(len(bars)), "right") - 1
    # alinear por la primera barra NT8 registrada (offset constante esperado)
    off = None
    if len(bars) and len(ba):
        cand = [k for k in range(0, max(1, len(bars) - len(ba) + 1))]
        best, bestn = 0, -1
        for k in cand[:5000]:
            m = min(len(ba), len(bars) - k)
            if m <= 0:
                continue
            eq = int(np.sum([ba[i]["n_events"] == (py_last[k + i] - py_first[k + i] + 1)
                             for i in range(min(m, 200))]))
            if eq > bestn:
                bestn, best = eq, k
        off = best
    m = min(len(ba), len(bars) - (off or 0))
    drift = []
    cuts_equal = 0
    for i in range(m):
        j = i + (off or 0)
        nt_n = ba[i]["n_events"]
        py_n = int(py_last[j] - py_first[j] + 1)
        if nt_n == py_n:
            cuts_equal += 1
        drift.append(nt_n - py_n)
    drift = np.array(drift, dtype=np.int64)
    cum = np.cumsum(drift)
    monotone = bool(len(cum) > 2 and (np.all(np.diff(cum) >= 0) or np.all(np.diff(cum) <= 0))
                    and abs(int(cum[-1])) > 1)
    cuts_ok = cuts_equal == m and m > 0
    print("\n[H2] CORTES DE BARRA   (offset NT8->Python = %s, %d barras comparadas)"
          % (off, m))
    print("    barras con el MISMO numero de eventos: %d/%d" % (cuts_equal, m))
    print("    drift acumulado final: %+d   monotono: %s"
          % (int(cum[-1]) if len(cum) else 0, monotone))
    print("    -> H2 %s" % ("DESCARTADA" if cuts_ok else
                            ("CONFIRMADA (drift monotono)" if monotone else "CONFIRMADA")))

    # ---------------- H3: ATRIBUCION del tick fronterizo -------------------- #
    # Solo tiene sentido si los cortes coinciden: si las barras agrupan eventos
    # distintos, el footprint difiere por construccion y no informa nada.
    if not (stream_ok and cuts_ok):
        print("\n[H3] ATRIBUCION DEL FOOTPRINT")
        print("    NO EVALUABLE: requiere H1 y H2 descartadas (stream=%s, cortes=%s)."
              % ("OK" if stream_ok else "MISMATCH", "OK" if cuts_ok else "MISMATCH"))
        attr_ok, attr_diff, border_only = None, None, None
        fps = None
    else:
        fps = bars_mod.build_footprints(tk, bars)
    attr_diff = 0
    border_only = 0
    for i in range(m if fps is not None else 0):
        j = i + (off or 0)
        d_py = fp_digest(fps.ask[j], fps.bid[j])
        if d_py != ba[i]["digest_fp"]:
            attr_diff += 1
            dv = abs(ba[i]["vol_fp"] - int(round(float(np.sum(
                list(fps.ask[j].values()) + list(fps.bid[j].values()))) * 100)))
            # firma de H3: la diferencia de volumen es la de UN solo evento
            if 0 < dv <= int(np.max(py_v[:200]) if len(py_v) else 10 ** 9):
                border_only += 1
    if fps is not None:
        attr_ok = attr_diff == 0
        print("\n[H3] ATRIBUCION DEL FOOTPRINT")
        print("    barras con digest de footprint distinto: %d/%d" % (attr_diff, m))
        print("    de esas, con diferencia del tamano de UN evento (borde): %d"
              % border_only)
        print("    -> H3 %s" % ("DESCARTADA" if attr_ok else "CONFIRMADA"))
    else:
        attr_ok = None

    # ---------------- clasificación ----------------------------------------- #
    firmas = []
    if not stream_ok:
        firmas.append("STREAM")
    if not cuts_ok:
        firmas.append("BAR_BUILDER")
    if stream_ok and cuts_ok and not attr_ok:
        firmas.append("ATTRIBUTION")
    if not firmas:
        verdict = "NO_MISMATCH"
    elif len(firmas) > 1:
        verdict = "MIXED_MISMATCH"
    else:
        verdict = firmas[0] + "_MISMATCH"

    print("\n" + "=" * 78)
    print("CLASIFICACION: %s" % verdict)
    print("=" * 78)
    print("H1 stream      : %s" % ("OK" if stream_ok else "MISMATCH"))
    print("H2 cortes      : %s" % ("OK" if cuts_ok else "MISMATCH"))
    print("H3 atribucion  : %s" % ("OK" if attr_ok else
                                   ("MISMATCH" if stream_ok and cuts_ok
                                    else "no evaluable (H1/H2 primero)")))
    print("\nPROHIBIDO implementar un fix sin esta clasificacion (TICKBAR-001 §6).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
