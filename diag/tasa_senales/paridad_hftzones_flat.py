"""Paridad NT8 -> Python de HFTZonesESPureV2Flat, en DOS niveles.

El oraculo es irrepetible (Nico lo corrio una sola vez, 62 sesiones de ES 03-26). Por eso
la paridad se mide contra el snapshot congelado, no contra la base viva.

NIVEL A — PARIDAD DE ENTRADA
============================
Antes de comparar zonas hay que probar que los dos lados vieron **el mismo stream de
ticks**. Si el stream difiere, ningun puerto puede coincidir y una zona que no cuadra no
dice nada del algoritmo.

`hft_flow` guarda, por segundo: open/high/low/close, volume, buy_vol, sell_vol, delta y
**n_ticks**. Se reconstruye lo mismo desde el parquet de EdgeLab y se compara celda a
celda. `bar_ts = floor(unix_ms/1000)*1000`, epoch UTC.

NIVEL B — PARIDAD DE ALGORITMO
==============================
Se corre el puerto sobre los ticks de EdgeLab y se comparan las zonas contra `hft_zones`
emparejando por `start_ts`. EXACT exige que coincidan geometria (upper/lower), pasos,
valid_steps y las metricas de microestructura.

Sin outcomes. Sin P&L. Holdout: el oraculo entero es pre-firewall (auditoria 2026-08-20).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import subprocess
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge.kernels.hftzones_es_pure_v2_flat import Params, run  # noqa: E402
from edgelab.bridge.ticks import load_canonical_parquet  # noqa: E402
from edgelab.kaggle.sessions_cme import session_bounds_utc_ns, trade_date_ymd  # noqa: E402

SNAPSHOT = REPO / "runs" / "oraculo_espurev2flat_ES_snapshot.sqlite"
CONTRATO = "ES 03-26"
PARQUET = REPO / "data" / "nt8" / "ES_parquet" / "ES_03-26_ticks.parquet"
TOL = 1e-6


def sesiones_del_oraculo(con):
    ts = np.array([r[0] for r in con.execute(
        "SELECT DISTINCT bar_ts FROM hft_flow WHERE instrument=?", (CONTRATO,))],
        dtype=np.int64)
    return sorted(set(int(x) for x in trade_date_ymd(ts * 1_000_000)))


def flow_de_sesion(con, ini_ns, fin_ns):
    q = ("SELECT bar_ts, open, high, low, close, volume, buy_vol, sell_vol, delta, "
         "n_ticks FROM hft_flow WHERE instrument=? AND bar_ts>=? AND bar_ts<? "
         "ORDER BY bar_ts")
    return con.execute(q, (CONTRATO, ini_ns // 1_000_000, fin_ns // 1_000_000)).fetchall()


def nivel_a(flow, ts_ns, px, vol, skip=0):
    """Reconstruye los buckets de 1 s desde los ticks y compara celda a celda."""
    if not flow:
        return dict(estado="SIN_FLOW")
    seg = (ts_ns // 1_000_000_000) * 1000
    # side por tick-rule con arrastre, igual que el .cs
    d = np.diff(px, prepend=px[0])
    side = np.where(d > 0, 1, np.where(d < 0, -1, 0)).astype(np.int64)
    for i in range(len(side)):                      # arrastre de lastSide
        if side[i] == 0:
            side[i] = side[i - 1] if i else 1
        if side[i] == 0:
            side[i] = 1

    # `if (CurrentBars[1] < 5) return;` descarta los 5 primeros ticks de la CARGA
    # entera, asi que el desfase existe solo en el primer bucket de la primera sesion.
    if skip:
        seg, px, vol, side = seg[skip:], px[skip:], vol[skip:], side[skip:]

    ref = {r[0]: r for r in flow}
    bordes = np.flatnonzero(np.diff(seg)) + 1
    tramos = np.split(np.arange(len(seg)), bordes)

    n_ok = n_dif = 0
    solo_nt8 = len(ref)
    campos_mal = {k: 0 for k in
                  ("open", "high", "low", "close", "volume", "buy", "sell", "n_ticks")}
    primeras = []
    for tr in tramos:
        b = int(seg[tr[0]])
        r = ref.get(b)
        if r is None:
            continue
        solo_nt8 -= 1
        p, v, s = px[tr], vol[tr], side[tr]
        mio = dict(open=float(p[0]), high=float(p.max()), low=float(p.min()),
                   close=float(p[-1]), volume=float(v.sum()),
                   buy=float(v[s >= 0].sum()), sell=float(v[s < 0].sum()),
                   n_ticks=int(len(tr)))
        suyo = dict(open=r[1], high=r[2], low=r[3], close=r[4], volume=r[5],
                    buy=r[6], sell=r[7], n_ticks=r[9])
        mal = [k for k in mio if abs(float(mio[k]) - float(suyo[k])) > TOL]
        if mal:
            n_dif += 1
            for k in mal:
                campos_mal[k] += 1
            if len(primeras) < 3:
                primeras.append(dict(bar_ts=b, mio=mio, nt8=suyo, campos=mal))
        else:
            n_ok += 1
    tot = n_ok + n_dif
    return dict(estado="EXACT" if n_dif == 0 and solo_nt8 == 0 else "DIFF",
                n_buckets_nt8=len(ref), n_buckets_emparejados=tot,
                buckets_solo_nt8=solo_nt8, n_iguales=n_ok, n_distintos=n_dif,
                frac_iguales=round(n_ok / tot, 6) if tot else None,
                campos_con_diferencia=campos_mal, ejemplos=primeras)


def nivel_b(con, ini_ns, fin_ns, ts_ns, px, vol, tick_size, params):
    cols = ("start_ts,end_ts,bucket,dir,price_upper,price_lower,height_ticks,pasos,"
            "valid_steps,avg_ms,total_ms,vol_rate,total_vol,max_tick_vol,cvd_sweep,"
            "buy_vol,sell_vol,no_move_ticks,max_level_ticks")
    ref = con.execute(
        "SELECT %s FROM hft_zones WHERE instrument=? AND start_ts>=? AND start_ts<? "
        "ORDER BY start_ts" % cols,
        (CONTRATO, ini_ns // 1_000_000, fin_ns // 1_000_000)).fetchall()
    nombres = cols.split(",")

    # `start_ts` se persiste en MILISEGUNDOS y dentro de un burst hay hasta 182 ticks en
    # el mismo ms (medido en 20260102: 98% de los ticks comparten ms). O sea que start_ts
    # NO es clave unica: emparejar 1-a-1 por start_ts cruza zonas distintas y reporta
    # como "diferencia de algoritmo" lo que es una colision de clave. Se agrupa por
    # start_ts y dentro del grupo se emparejan primero los EXACTOS.
    suyas, mias = {}, {}
    for r in ref:
        suyas.setdefault(r[0], []).append(dict(zip(nombres, r)))
    for z in run(ts_ns, px, vol, tick_size, params):
        mias.setdefault(z.start_ts, []).append(z)

    def difiere(a, b):
        mal = []
        for n in nombres[1:]:
            u, v = a[n], getattr(b, n)
            if isinstance(u, str) or isinstance(v, str):
                if str(u) != str(v):
                    mal.append(n)
            elif abs(float(u) - float(v)) > 1e-6 * max(1.0, abs(float(u))):
                mal.append(n)
        return mal

    exact, difer, campos = 0, 0, {}
    ejemplos = []
    n_colisiones = sum(1 for k in suyas if len(suyas[k]) > 1)
    for k in sorted(set(suyas) | set(mias)):
        A, B = list(suyas.get(k, [])), list(mias.get(k, []))
        libres = list(B)
        for a in list(A):
            for b in list(libres):
                if not difiere(a, b):
                    exact += 1
                    A.remove(a); libres.remove(b)
                    break
        for a, b in zip(A, libres):          # sobrantes emparejables: diferencia real
            mal = difiere(a, b)
            difer += 1
            for n in mal:
                campos[n] = campos.get(n, 0) + 1
            if len(ejemplos) < 3:
                ejemplos.append(dict(start_ts=k, campos=mal,
                                     nt8={n: a[n] for n in mal},
                                     python={n: getattr(b, n) for n in mal}))
    tot_nt8 = sum(len(v) for v in suyas.values())
    tot_py = sum(len(v) for v in mias.values())
    return dict(estado=("EXACT" if difer == 0 and exact == tot_nt8 == tot_py else "DIFF"),
                n_nt8=tot_nt8, n_python=tot_py,
                start_ts_con_colision=n_colisiones,
                solo_nt8=tot_nt8 - exact - difer,
                solo_python=tot_py - exact - difer,
                exact=exact, con_diferencia=difer,
                campos_con_diferencia=campos, ejemplos=ejemplos)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=str(SNAPSHOT))
    ap.add_argument("--max-sesiones", type=int, default=0)
    ap.add_argument("--solo-nivel-a", action="store_true")
    ap.add_argument("--sesiones", default="", help="lista YYYYMMDD separada por comas")
    ap.add_argument("--out", default=str(REPO / "docs" / "research" / "paridad_flat.json"))
    a = ap.parse_args()

    con = sqlite3.connect("file:%s?mode=ro" % pathlib.Path(a.snapshot).as_posix(),
                          uri=True)
    ses = sesiones_del_oraculo(con)
    if a.sesiones:
        pedidas = {int(x) for x in a.sesiones.split(',')}
        ses = [t for t in ses if t in pedidas]
    if a.max_sesiones:
        ses = ses[:a.max_sesiones]
    print("paridad HFTZonesESPureV2Flat  -  %d sesiones  -  %s" % (len(ses), CONTRATO))

    params = Params()
    filas = []
    for td in ses:
        ini, fin = session_bounds_utc_ns(td)
        try:
            tk = load_canonical_parquet(PARQUET, start_utc_ns=ini, end_utc_ns=fin,
                                        instrument="ES")
        except ValueError:
            filas.append(dict(trade_date=td, estado="SIN_PARQUET"))
            print("  %d  SIN_PARQUET" % td)
            continue
        A = nivel_a(flow_de_sesion(con, ini, fin), tk.ts_ns,
                    tk.price_ticks * tk.tick_size, tk.volume,
                    skip=(5 if td == ses[0] else 0))
        f = dict(trade_date=td, n_ticks_edgelab=int(len(tk.ts_ns)), nivel_a=A)
        if not a.solo_nivel_a:
            f["nivel_b"] = nivel_b(con, ini, fin, tk.ts_ns,
                                   tk.price_ticks * tk.tick_size, tk.volume,
                                   tk.tick_size, params)
        filas.append(f)
        b = f.get("nivel_b", {})
        print("  %d  A:%-5s %s/%s buckets   B:%-5s nt8=%s py=%s exact=%s"
              % (td, A["estado"], A.get("n_iguales"), A.get("n_buckets_emparejados"),
                 b.get("estado", "-"), b.get("n_nt8", "-"), b.get("n_python", "-"),
                 b.get("exact", "-")))

    ok_a = sum(1 for f in filas if f.get("nivel_a", {}).get("estado") == "EXACT")
    ok_b = sum(1 for f in filas if f.get("nivel_b", {}).get("estado") == "EXACT")
    med = [f for f in filas if "nivel_b" in f]
    tot_nt8 = sum(f["nivel_b"]["n_nt8"] for f in med)
    tot_ex = sum(f["nivel_b"]["exact"] for f in med)

    sucios = [l[3:].strip() for l in subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines() if l]
    out = dict(
        schema_version="paridad_hftzones_es_pure_v2_flat_v1",
        indicador="HFTZonesESPureV2Flat",
        cs_sha256="4e80c24d873cd9009850e55d3e3b4a7492a77608e47dc8a41f0294cb226824e5",
        contrato=CONTRATO, snapshot=str(a.snapshot),
        outcomes_accessed=False, pnl_accessed=False, holdout_included=False,
        nota_warmup=("NT8 descarta los 5 primeros ticks de la carga (CurrentBars[1] < 5). Nivel A aplica el mismo skip SOLO en la primera sesion; sin eso el primer bucket discrepa en n_ticks por exactamente 5."),
        nota_serie=("el .cs corre sobre AddDataSeries(Tick, 1): la maquina de estados no "
                    "usa las velas de 25 Tick del chart, que son solo la serie de dibujo"),
        parametros=vars(params),
        resumen=dict(n_sesiones=len(filas),
                     nivel_a_exact=ok_a, nivel_b_exact=ok_b,
                     zonas_nt8=tot_nt8, zonas_exact=tot_ex,
                     frac_zonas_exact=round(tot_ex / tot_nt8, 6) if tot_nt8 else None),
        procedencia=dict(head_commit=subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
            archivos_sucios=sorted(sucios),
            medicion_comprometida=bool([x for x in sucios
                                        if x.startswith(("edgelab/", "diag/"))])),
        sesiones=filas)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print()
    print("  NIVEL A exact: %d/%d sesiones" % (ok_a, len(filas)))
    if med:
        print("  NIVEL B exact: %d/%d sesiones   zonas %d/%d"
              % (ok_b, len(med), tot_ex, tot_nt8))
    print("  escrito %s" % a.out)


if __name__ == "__main__":
    main()
