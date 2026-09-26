# -*- coding: utf-8 -*-
"""UNIDAD 3 -- deflación por N_eff, y el estadístico con signo.

Cierra los puntos 2 y 3 de la revisión:

  2. El MDE placebo NO se compara directo contra el break-even. Hay que
     deflactarlo por la razón de tamaños efectivos:
         MDE_real ≈ MDE_placebo · sqrt(N_eff_placebo / N_eff_real)
     `N_eff` se MIDE con el mismo bootstrap de bloques de día que usa
     producción, vía el efecto de diseño DEFF = Var_bloque / Var_iid, y
     N_eff = n_anclas / DEFF. No se asume del conteo bruto.

  3. `p_favorable` es convexa en la deriva (Jensen). Entonces la volatilidad
     SOLA la infla, sin dirección. Se cuantifica esa contaminación y se corre
     un estadístico CON SIGNO (expectativa neta en ticks por ancla), que bajo
     una señal de media cero debe dar ~0.

Guarda S/T y ticks netos POR DÍA, que es lo que faltaba para poder medir
todo esto.
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

from spike_in import (A0, CFG, DATA_DIR, _senal_ticks,  # noqa: E402
                      dias_del_atlas_sellado, geometrias)

M_LISTA = [0.0, 2.0, 4.0]
RONDAS = int(os.environ.get("SPIKE_RONDAS", "25"))


def procesar(args):
    """Por día: S, T y SUMA DE TICKS NETOS, por geometría y por m."""
    archivo, contrato, fecha, data_dir, ronda, m_lista, variante = args
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

        # acc[m][g] = [S, T, suma_ticks_netos]
        acc = {m: {g: [0, 0, 0.0] for g in geometrias()} for m in m_lista}
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
            for H in CFG["horizontes_min"]:
                e = np.searchsorted(ts, t0 + H * 60 * 10**9, side="right")
                fut = px[i + 1:e]
                if len(fut) == 0:
                    continue
                base = (fut - p0) * direccion
                ts_fut = ts[i + 1:e]
                for m in m_lista:
                    delta = base + _senal_ticks(ts_fut, t0, H, m, signo, "rampa")
                    for (P, N) in CFG["pares_pn"]:
                        g = "H%d_P%d_N%d" % (H, P, N)
                        fav = np.flatnonzero(delta >= P)
                        adv = np.flatnonzero(delta <= -N)
                        f0 = int(fav[0]) if len(fav) else -1
                        a0 = int(adv[0]) if len(adv) else -1
                        if f0 < 0 and a0 < 0:
                            v, ticks = 0, float(delta[-1])   # marcado a mercado
                        elif a0 < 0 or (f0 >= 0 and f0 < a0):
                            v, ticks = 1, float(P)
                        else:
                            v, ticks = -1, float(-N)
                        acc[m][g][0] += (v == 1)
                        acc[m][g][1] += 1
                        acc[m][g][2] += ticks
        return dict(fecha=fecha, acc=acc)
    except Exception:
        return None


def correr(dias, rondas, m_lista, variante):
    import multiprocessing as mp
    tareas = [(ar, co, f, DATA_DIR, rd, m_lista, variante)
              for (ar, co, f) in dias for rd in range(rondas)]
    tot = {m: {g: {} for g in geometrias()} for m in m_lista}
    t0 = time.time()
    with mp.Pool(max(1, min(mp.cpu_count() - 2, 10))) as pool:
        for n, res in enumerate(pool.imap_unordered(procesar, tareas, chunksize=4)):
            if not res:
                continue
            for m in m_lista:
                for g, (S, T, tk) in res["acc"][m].items():
                    c = tot[m][g].setdefault(res["fecha"], [0, 0, 0.0])
                    c[0] += S; c[1] += T; c[2] += tk
            if (n + 1) % 1000 == 0:
                print("   %d/%d (%.0fs)" % (n + 1, len(tareas), time.time() - t0), flush=True)
    return tot


def deff_y_neff(tot, g, m=0.0, reps=2000, seed=20260801):
    """DEFF = Var_bloque / Var_iid  ;  N_eff = n_anclas / DEFF.

    Var_iid es la binomial p(1-p)/n que se tendría si las anclas fueran
    independientes. Var_bloque sale del MISMO remuestreo por día que usa
    `bootstrap_tasas` en producción.
    """
    fechas = sorted(tot[m][g])
    S = np.array([tot[m][g][f][0] for f in fechas], float)
    T = np.array([tot[m][g][f][1] for f in fechas], float)
    n = T.sum()
    p = S.sum() / n
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(reps):
        i = rng.choice(len(fechas), size=len(fechas), replace=True)
        t = T[i].sum()
        if t:
            vals.append(S[i].sum() / t)
    var_bloque = float(np.var(vals, ddof=1))
    var_iid = p * (1 - p) / n
    deff = var_bloque / var_iid if var_iid > 0 else float("nan")
    return dict(p=p, n_anclas=int(n), n_dias=len(fechas),
                anclas_por_dia=n / len(fechas),
                var_bloque=var_bloque, var_iid=var_iid,
                deff=deff, n_eff=n / deff if deff > 0 else float("nan"))


def estadistico_con_signo(tot, g, m_lista, reps=2000, seed=20260801):
    """Expectativa neta en TICKS por ancla, con IC bootstrap por bloques de día."""
    fechas = sorted(tot[0.0][g])
    out = {}
    rng = np.random.default_rng(seed)
    idxs = [rng.choice(len(fechas), size=len(fechas), replace=True) for _ in range(reps)]
    TK = {m: np.array([tot[m][g][f][2] for f in fechas], float) for m in m_lista}
    T = {m: np.array([tot[m][g][f][1] for f in fechas], float) for m in m_lista}
    base = TK[0.0].sum() / T[0.0].sum()
    for m in m_lista:
        obs = TK[m].sum() / T[m].sum()
        dif = []
        for i in idxs:
            t0_, tm_ = T[0.0][i].sum(), T[m][i].sum()
            if t0_ and tm_:
                dif.append(TK[m][i].sum() / tm_ - TK[0.0][i].sum() / t0_)
        dif = np.array(dif)
        out[m] = dict(ticks=obs, delta=obs - base,
                      ic95=[float(np.percentile(dif, 2.5)), float(np.percentile(dif, 97.5))])
    return out, base


if __name__ == "__main__":
    dias, _ = dias_del_atlas_sellado()
    salida = {}
    for var in ("A", "B"):
        print("=== corriendo variante %s (m=%s, rondas=%d) ===" % (var, M_LISTA, RONDAS), flush=True)
        salida[var] = correr(dias, RONDAS, M_LISTA, var)
    json.dump({v: {str(m): {g: d for g, d in gs.items()} for m, gs in t.items()}
               for v, t in salida.items()},
              open(os.path.join(AQUI, "por_dia.json"), "w"), separators=(",", ":"))
    print("guardado por_dia.json")

    # ---------------- 2. DEFF / N_eff sobre el placebo
    print()
    print("=" * 78)
    print("2. TAMANO EFECTIVO DEL DISENO PLACEBO (medido, no asumido)")
    print("=" * 78)
    filas = []
    for g in geometrias():
        filas.append((g, deff_y_neff(salida["A"], g)))
    print("%-14s %8s %9s %8s %8s %9s %9s" %
          ("geometria", "p", "n_anclas", "anc/dia", "DEFF", "N_eff", "N_eff/dia"))
    for g, d in filas:
        print("%-14s %8.4f %9d %8.2f %8.2f %9.1f %9.3f" %
              (g, d["p"], d["n_anclas"], d["anclas_por_dia"], d["deff"],
               d["n_eff"], d["n_eff"] / d["n_dias"]))
    deffs = np.array([d["deff"] for _, d in filas])
    neffs = np.array([d["n_eff"] for _, d in filas])
    apd = filas[0][1]["anclas_por_dia"]
    print()
    print("DEFF  : min=%.2f mediana=%.2f max=%.2f" % (deffs.min(), np.median(deffs), deffs.max()))
    print("N_eff : min=%.0f mediana=%.0f max=%.0f  (sobre %d dias)"
          % (neffs.min(), np.median(neffs), neffs.max(), filas[0][1]["n_dias"]))
    rho = (np.median(deffs) - 1) / (apd - 1)
    print("anclas/dia=%.2f  ->  correlacion intra-dia implicita rho = %.4f" % (apd, rho))
    json.dump(dict(deff_mediana=float(np.median(deffs)), n_eff_mediana=float(np.median(neffs)),
                   anclas_por_dia=float(apd), rho=float(rho), n_dias=filas[0][1]["n_dias"]),
              open(os.path.join(AQUI, "neff.json"), "w"), indent=1)

    # ---------------- 3. estadistico con signo
    print()
    print("=" * 78)
    print("3. ESTADISTICO CON SIGNO: expectativa neta en TICKS por ancla")
    print("=" * 78)
    print("   bajo B (senal de media cero) debe dar ~0. Si se mueve, es bug.")
    print()
    print("%-14s %10s | %-26s | %-26s" % ("geometria", "ticks(m=0)", "A: delta [IC95]", "B: delta [IC95]"))
    resumen = {}
    for g in geometrias():
        ra, base = estadistico_con_signo(salida["A"], g, M_LISTA)
        rb, _ = estadistico_con_signo(salida["B"], g, M_LISTA)
        a4, b4 = ra[4.0], rb[4.0]
        sa = "*" if (a4["ic95"][0] > 0 or a4["ic95"][1] < 0) else " "
        sb = "*" if (b4["ic95"][0] > 0 or b4["ic95"][1] < 0) else " "
        print("%-14s %10.4f | %+8.4f%s[%+.3f,%+.3f] | %+8.4f%s[%+.3f,%+.3f]" %
              (g, base, a4["delta"], sa, a4["ic95"][0], a4["ic95"][1],
               b4["delta"], sb, b4["ic95"][0], b4["ic95"][1]))
        resumen[g] = dict(base=base, A=a4, B=b4)
    json.dump(resumen, open(os.path.join(AQUI, "con_signo.json"), "w"), indent=1)
    nb = sum(1 for g in resumen if resumen[g]["B"]["ic95"][0] > 0 or resumen[g]["B"]["ic95"][1] < 0)
    print()
    print("geometrias donde B mueve el estadistico CON SIGNO: %d de 40" % nb)
    print("  (esperado ~2 por azar al 5%%; muchas mas seria bug)")
