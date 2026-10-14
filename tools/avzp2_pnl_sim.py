#!/usr/bin/env python3
"""AVZP2-PNL-ES: simulador de brackets tick a tick (docs/research/AVZP2_PNL_MANIFIESTO_PROPUESTO_20261014.md).

`simulate_bracket` es una función pura (probada con fixtures). El runner `main` **se niega a ejecutar sobre retornos reales**
sin el archivo de aprobación de Nico (regla «STOP antes de correr búsqueda sobre retornos» de CLAUDE.md):
  NICO_PNL_OK=<ruta a un archivo cuyo contenido es el sha256 del manifiesto aprobado>
Precios en ticks (enteros). Convenciones:
- Entrada a mercado en el primer tick posterior a `entry_ns`: long compra al ask, short vende al bid.
- TP (límite): se llena sólo si el precio CRUZA el nivel (last > nivel para long, < nivel para short): conservador, sin fill por toque. Fill al nivel.
- SL (stop a mercado): se activa con last <= nivel (long) / >= nivel (short); fill al peor entre last y nivel, más `slip_stop` ticks adversos.
- Salida por tiempo: primer tick con ts >= max_ns, a mercado (bid para long, ask para short), sin slippage adicional.
- Barras consecutivas pueden compartir `end_ns` (≈1,5 % de las salidas en ES: ráfagas de ticks con el mismo timestamp); como la entrada es el primer tick con ts ESTRICTAMENTE posterior, la entrada se demora en esos casos: causal y conservador.
- Costos: `comm_ticks` (round-turn) restados del neto. Sin ticks suficientes tras la entrada: `NO_DATA` (se cuenta, no se descarta en silencio).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np


def simulate_bracket(ts, last, bid, ask, entry_ns, side, tp, sl, max_ns, slip_stop=1.0, comm_ticks=0.0):
    ts = np.asarray(ts); last = np.asarray(last)
    i0 = int(np.searchsorted(ts, entry_ns, side="right"))
    if i0 >= len(ts) - 1:
        return dict(reason="NO_DATA", gross=np.nan, net=np.nan, exit_idx=-1, entry=np.nan)
    entry = float(ask[i0] if side > 0 else bid[i0])
    if not np.isfinite(entry) or entry <= 0:
        return dict(reason="NO_QUOTE", gross=np.nan, net=np.nan, exit_idx=-1, entry=np.nan)
    j = np.arange(i0 + 1, len(ts))
    px = last[j]
    tp_lvl, sl_lvl = entry + side * tp, entry - side * sl
    hit_tp = (px > tp_lvl) if side > 0 else (px < tp_lvl)
    hit_sl = (px <= sl_lvl) if side > 0 else (px >= sl_lvl)
    hit_tm = ts[j] >= max_ns
    big = len(j)
    k_tp = int(np.argmax(hit_tp)) if hit_tp.any() else big
    k_sl = int(np.argmax(hit_sl)) if hit_sl.any() else big
    k_tm = int(np.argmax(hit_tm)) if hit_tm.any() else big
    k = min(k_tp, k_sl, k_tm)
    if k == big:
        return dict(reason="NO_EXIT_IN_DATA", gross=np.nan, net=np.nan, exit_idx=-1, entry=entry)
    if k == k_sl and k_sl <= k_tp:                      # en un mismo tick no pueden coexistir TP y SL; el SL manda si empatan por índice
        fill = min(px[k], sl_lvl) if side > 0 else max(px[k], sl_lvl)
        fill = fill - side * slip_stop
        reason = "SL"
    elif k == k_tp:
        fill, reason = tp_lvl, "TP"
    else:
        fill = float(bid[j[k]] if side > 0 else ask[j[k]])
        reason = "TIME"
    gross = side * (fill - entry)
    return dict(reason=reason, gross=float(gross), net=float(gross - comm_ticks), exit_idx=int(j[k]), entry=entry)


def run_events(events, ticks_for_session, params):
    """Corre el bracket de cada evento. `events`: DataFrame con session, te_end_ns, dir, cell, contract, t0.
    `ticks_for_session(contract, session) -> (ts, last, bid, ask)` (arrays ordenados). `params`: tp, sl, slip_stop, comm_ticks, max_seconds.
    Devuelve un DataFrame con una fila por evento (incluye NO_DATA/NO_QUOTE/NO_EXIT_IN_DATA: nada se descarta en silencio)."""
    import pandas as pd
    rows = []
    cache = {}
    for e in events.itertuples():
        key = (e.contract, int(e.session))
        if key not in cache:
            cache.clear()
            cache[key] = ticks_for_session(*key)
        ts, last, bid, ask = cache[key]
        r = simulate_bracket(ts, last, bid, ask, int(e.te_end_ns), int(e.dir), params["tp"], params["sl"],
                             int(e.te_end_ns) + int(params["max_seconds"] * 1e9), params["slip_stop"], params["comm_ticks"])
        rows.append(dict(cell=e.cell, contract=e.contract, session=int(e.session), t0=int(e.t0), side=int(e.dir), **r))
    return pd.DataFrame(rows)


def summarize(res):
    """Expectativa por operación en ticks (bruto y neto) sobre las operaciones con salida; cuenta el resto por separado."""
    ok = res[res.reason.isin(["TP", "SL", "TIME"])]
    out = dict(n_eventos=int(len(res)), n_operaciones=int(len(ok)), razones=res.reason.value_counts().to_dict())
    if len(ok):
        out.update(bruto_medio=float(ok.gross.mean()), neto_medio=float(ok.net.mean()), tasa_tp=float((ok.reason == "TP").mean()))
    return out


def manifest_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_approval(manifest_path):
    ok = os.environ.get("NICO_PNL_OK")
    if not ok or not Path(ok).exists():
        sys.exit("STOP: falta aprobación de Nico (NICO_PNL_OK). No se corre P&L sin manifiesto aprobado.")
    if Path(ok).read_text().strip() != manifest_sha(manifest_path):
        sys.exit("STOP: el sha256 aprobado no coincide con el manifiesto actual (¿cambió después de la aprobación?).")


def select_events(t, cells):
    """Regla (a) del manifiesto: una entrada por racimo real que sale en la sesión, a favor de la tendencia previa (dir == trend != 0)."""
    r = t[(t.kind == "real") & (t.te >= 0) & (t.trend != 0) & (t["dir"] == t.trend) & t.cell.isin(cells)]
    return r.drop_duplicates(["cell", "contract", "t0"])


def main():
    manifest = Path(__file__).resolve().parents[1] / "docs" / "research" / "AVZP2_PNL_MANIFIESTO_PROPUESTO_20261014.md"
    require_approval(manifest)
    print(json.dumps(dict(estado="aprobado", manifest_sha256=manifest_sha(manifest))))
    sys.exit("Aprobado, pero falta el archivo de parámetros congelados (tp, sl, comisión, max_seconds) y el loader de la release: "
             "se conectan con `run_events(select_events(...), loader, params)` al recibir las comisiones reales de Nico.")


if __name__ == "__main__":
    main()
