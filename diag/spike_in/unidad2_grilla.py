# -*- coding: utf-8 -*-
"""UNIDAD 2 -- la grilla de magnitudes, el MDE, y la variante B.

Semántica de tasa IDÉNTICA a producción (`atlas_asimetrico.py:407-411`):
    S = # anclas con `objetivo primero`
    T = # anclas con la clave presente  <-- INCLUYE las que no tocan ninguna
        barrera dentro del horizonte
o sea `p_favorable = S/T` cuenta como no-acierto al ancla que no llegó a nada.
Es la lectura económica correcta: no pasó nada no es ganar.

Diseño APAREADO: todos los `m` comparten las mismas anclas (mismo `ronda`,
misma semilla). El bootstrap remuestrea DÍAS y calcula la diferencia
`p_m - p_0` dentro de cada réplica, que es mucho más potente que bootstrapear
cada brazo por separado.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from spike_in import (A0, CFG, DATA_DIR, REPO, _senal_ticks,  # noqa: E402
                      dias_del_atlas_sellado, geometrias)

M_GRILLA = [0.0, 0.1, 0.2, 0.5, 1.0, 2.0, 4.0]
RONDAS = int(os.environ.get("SPIKE_RONDAS", "25"))
BOOT_REPS = 2000
SEED_BOOT = 20260801            # misma semilla que usa bootstrap_tasas (CFG.seed) NO:
                                # se declara aparte para no colisionar con el atlas
FORMA = "rampa"


def procesar_dia_multi(args):
    """Un día-ronda, TODOS los `m` de la grilla, con UNA sola carga de parquet.

    Las anclas y `direccion` se calculan una vez y se comparten entre los `m`:
    ese apareo es lo que hace potente la comparación.
    """
    archivo, contrato, fecha, data_dir, ronda, m_lista, variante, forma = args
    try:
        import duckdb
        from zoneinfo import ZoneInfo
        CT = ZoneInfo("America/Chicago")
        p = os.path.join(data_dir, archivo).replace("\\", "/")
        d0 = datetime.strptime(fecha, "%Y-%m-%d").replace(tzinfo=CT)
        a = int(d0.timestamp() * 1e9)
        b = int((d0 + timedelta(days=1)).timestamp() * 1e9)
        con = duckdb.connect()
        df = con.execute(
            "select ts_utc_ns, price_ticks from read_parquet('%s') "
            "where ts_utc_ns>=%d and ts_utc_ns<%d order by ts_utc_ns" % (p, a, b)).df()
        if len(df) < 5000:
            return None
        ts = df.ts_utc_ns.values.astype(np.int64)
        px = df.price_ticks.values.astype(np.int64)
        del df

        hmax = max(CFG["horizontes_min"])
        sep_ns = CFG["sep_min_minutos"] * 60 * 10**9
        vol_ns = CFG["vol_lookback_min"] * 60 * 10**9
        r = A0._rng(CFG["seed"], contrato, fecha, "anclas", ronda)
        t_lo, t_hi = int(ts[0]) + vol_ns, int(ts[-1]) - hmax * 60 * 10**9
        if t_hi <= t_lo:
            return None
        cand = np.sort(r.integers(t_lo, t_hi, size=CFG["anclas_por_dia"] * 4))
        anclas, ultimo = [], None
        for t in cand:
            t = int(t)
            if ultimo is None or t - ultimo >= sep_ns:
                anclas.append(t); ultimo = t
            if len(anclas) >= CFG["anclas_por_dia"]:
                break
        if not anclas:
            return None

        # acc[m][g] = [S, T]
        acc = {m: {g: [0, 0] for g in geometrias()} for m in m_lista}
        signos = []
        direcciones = []
        idx = np.searchsorted(ts, anclas, side="right") - 1
        for k, i in enumerate(idx):
            if i < 1:
                continue
            t0, p0 = int(ts[i]), int(px[i])
            j = np.searchsorted(ts, t0 - vol_ns, side="left")
            if i - j < 50:
                continue
            rd = A0._rng(CFG["seed"], contrato, fecha, ronda, k)
            direccion = 1 if rd.integers(0, 2) == 0 else -1
            if variante == "B":
                rs = A0._rng(CFG["seed"], contrato, fecha, ronda, k, "spike_signo")
                signo = 1 if rs.integers(0, 2) == 0 else -1
            else:
                signo = 1
            signos.append(signo); direcciones.append(direccion)

            for H in CFG["horizontes_min"]:
                e = np.searchsorted(ts, t0 + H * 60 * 10**9, side="right")
                fut = px[i + 1:e]
                if len(fut) == 0:
                    continue
                base = (fut - p0) * direccion
                ts_fut = ts[i + 1:e]
                for m in m_lista:
                    delta = base + _senal_ticks(ts_fut, t0, H, m, signo, forma)
                    for (P, N) in CFG["pares_pn"]:
                        g = "H%d_P%d_N%d" % (H, P, N)
                        fav = np.flatnonzero(delta >= P)
                        adv = np.flatnonzero(delta <= -N)
                        f0 = int(fav[0]) if len(fav) else -1
                        a0 = int(adv[0]) if len(adv) else -1
                        if f0 < 0 and a0 < 0:
                            v = 0
                        elif a0 < 0 or (f0 >= 0 and f0 < a0):
                            v = 1
                        else:
                            v = -1
                        acc[m][g][1] += 1                 # T: la clave existe
                        if v == 1:
                            acc[m][g][0] += 1             # S
        return dict(fecha=fecha, acc=acc,
                    corr_signo=(signos, direcciones))
    except Exception as e:
        return dict(fecha=fecha, error=str(e))


def correr(dias, rondas, m_lista, variante, forma=FORMA, workers=None):
    import multiprocessing as mp
    tareas = [(arch, con, f, DATA_DIR, ronda, m_lista, variante, forma)
              for (arch, con, f) in dias for ronda in range(rondas)]
    workers = workers or max(1, min(mp.cpu_count() - 2, 10))
    # S[m][g][fecha] = [S, T]
    tot = {m: {g: {} for g in geometrias()} for m in m_lista}
    signos_all, dirs_all = [], []
    t0 = time.time()
    with mp.Pool(workers) as pool:
        for n, res in enumerate(pool.imap_unordered(procesar_dia_multi, tareas, chunksize=4)):
            if not res or "error" in res:
                continue
            f = res["fecha"]
            for m in m_lista:
                for g, (S, T) in res["acc"][m].items():
                    cur = tot[m][g].setdefault(f, [0, 0])
                    cur[0] += S; cur[1] += T
            s, d = res["corr_signo"]
            signos_all.extend(s); dirs_all.extend(d)
            if (n + 1) % 500 == 0:
                print("   %d/%d tareas (%.0fs)" % (n + 1, len(tareas), time.time() - t0), flush=True)
    return tot, np.array(signos_all), np.array(dirs_all)


def bootstrap_diferencia(tot, g, m_lista, reps=BOOT_REPS, seed=SEED_BOOT):
    """Bootstrap APAREADO por bloques de DÍA de `p_m - p_0`."""
    fechas = sorted(tot[0.0][g])
    if len(fechas) < 3:
        return None
    S = {m: np.array([tot[m][g].get(f, [0, 0])[0] for f in fechas], float) for m in m_lista}
    T = {m: np.array([tot[m][g].get(f, [0, 0])[1] for f in fechas], float) for m in m_lista}
    rng = np.random.default_rng(seed)
    out = {}
    idxs = [rng.choice(len(fechas), size=len(fechas), replace=True) for _ in range(reps)]
    p0_obs = S[0.0].sum() / T[0.0].sum() if T[0.0].sum() else float("nan")
    for m in m_lista:
        pm_obs = S[m].sum() / T[m].sum() if T[m].sum() else float("nan")
        difs = []
        for i in idxs:
            t0_, tm_ = T[0.0][i].sum(), T[m][i].sum()
            if t0_ and tm_:
                difs.append(S[m][i].sum() / tm_ - S[0.0][i].sum() / t0_)
        difs = np.array(difs)
        out[m] = dict(p=pm_obs, delta=pm_obs - p0_obs,
                      ic95=[float(np.percentile(difs, 2.5)), float(np.percentile(difs, 97.5))],
                      n_dias=len(fechas))
    return out, p0_obs


if __name__ == "__main__":
    variante = sys.argv[1] if len(sys.argv) > 1 else "A"
    dias, _ = dias_del_atlas_sellado()
    print("=== UNIDAD 2 -- grilla, variante %s ===" % variante)
    print("dias=%d  rondas=%d  m=%s  forma=%s" % (len(dias), RONDAS, M_GRILLA, FORMA))
    tot, signos, dirs = correr(dias, RONDAS, M_GRILLA, variante)

    if variante == "B":
        if len(signos) > 2 and signos.std() > 0 and dirs.std() > 0:
            c = float(np.corrcoef(signos, dirs)[0, 1])
        else:
            c = 0.0
        print("\nCHEQUEO OBLIGATORIO corr(s_k, direccion) = %+.5f  (n=%d)" % (c, len(signos)))
        print("  %s" % ("OK: streams independientes" if abs(c) < 0.05 else
                        "ALARMA: streams correlacionados, B degenero en A"))

    filas = []
    print("\n%-14s %8s |" % ("geometria", "p(m=0)"), end="")
    for m in M_GRILLA[1:]:
        print(" %16s" % ("m=%.1f" % m), end="")
    print()
    for g in geometrias():
        r = bootstrap_diferencia(tot, g, M_GRILLA)
        if not r:
            continue
        res, p0 = r
        print("%-14s %8.4f |" % (g, p0), end="")
        for m in M_GRILLA[1:]:
            d = res[m]
            sig = "*" if (d["ic95"][0] > 0 or d["ic95"][1] < 0) else " "
            print(" %+7.4f%s[%+.3f]" % (d["delta"], sig, d["ic95"][0]), end="")
        print()
        for m in M_GRILLA:
            filas.append(dict(geometria=g, m=m, p=res[m]["p"], delta=res[m]["delta"],
                              ic95=res[m]["ic95"], n_dias=res[m]["n_dias"], p0=p0))
    out = os.path.join(AQUI, "resultado_%s.json" % variante)
    json.dump(dict(variante=variante, rondas=RONDAS, m_grilla=M_GRILLA, forma=FORMA,
                   seed_bootstrap=SEED_BOOT, boot_reps=BOOT_REPS, filas=filas),
              open(out, "w", encoding="utf-8"), indent=1)
    print("\nescrito:", out)
