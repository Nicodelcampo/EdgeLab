"""Motor único de ejecuciones tick a tick (2026-11-11, `docs/autopilot/AUTOMATIZACION_PROCESOS_20261111.md` I3/V1/V3).

Cada familia que mide P&L declaraba su propio simulador (op2 `_op`, `areas_expansion.simular`, `luximb_hvn`); el de LUXIMB-HVN
acreditaba el stop en su nivel aunque el precio saltara más allá y daba ≈ +0,3 R en una caminata sin efecto. Acá hay UNA
convención y una calibración automática que la vigila:
  - el stop es a mercado y sale al precio del tick que lo cruza (un salto se paga entero);
  - objetivo y toma parcial son límites y se cobran en su nivel;
  - la operación vence a `TOPE` velas de la entrada, al fin de la sesión o en un hueco > `GAP_S` (sale al último tick);
  - la entrada a mercado es el primer tick de la vela siguiente a la señal; una orden límite se llena con `fill_pasivo`
    (modelo «atraviesa»: un tick más allá).

Contrato de la tabla de eventos (columnas que la familia entrega; todo conocido al cierre de la vela `k`):
  k     vela de la señal          lado  +1 compra / −1 venta (dirección de la operación)
  ref   precio de referencia del objetivo, del lado de la ganancia (p. ej. el origen A de un impulso que se va a revertir)
  ext   extremo en contra al momento de la señal (p. ej. el B del impulso)          rg   escala de distancias (> 0, en precio)

Ejecuciones (tuplas; `nombre(spec)` da la columna):
  ("MERCADO", sl, tp, parcial, be)   entrada a mercado; D = lado·(ref − entrada); stop sl·D, objetivo tp·D; parcial del 50 % y/o
                                     break even a esa fracción de D (0 = sin)
  ("VUELTA", e, r, b, obj, c)        espera que el precio se extienda e·rg más allá de `ext` (en contra) y vuelva r·rg; entra a
                                     mercado; stop b·rg más allá del extremo; objetivo ref (obj 0) o la mitad entre ref y ext
                                     (obj 1); se cancela si se extiende más de c·rg, si toca ref antes o al vencer la espera
  ("LIMITE", x, sl, tp)              orden límite x·rg más allá de `ext` (en contra), viva durante la espera; stop sl·rg y
                                     objetivo tp·rg desde el límite (fill «atraviesa», `fill_pasivo.operar`)
Salida por ejecución: `r_<nombre>` (R bruto, NaN = sin operación) y `k_<nombre>` (riesgo inicial en precio, para restar la
fricción de `edgelab/costos.py` en el análisis). Además `mec_*`: el recorrido sin ejecución (extensión antes de tocar ref, si tocó
la mitad y ref).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from numba import njit
except ImportError:                                     # sin numba: misma lógica en Python (lento; sólo tests chicos)
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

TOPE = 240
GAP_S = 1800.0
NS = 1_000_000_000


def nombre(spec) -> str:
    t, *p = spec
    if t == "MERCADO":
        sl, tp, pt, be = p
        g = "N" if not pt and not be else ("P" if pt and not be else ("B" if be and not pt else "PB"))
        return f"M_sl{sl}_tp{tp}_{g}{max(pt, be) if g != 'N' else ''}"
    if t == "VUELTA":
        e, r, b, obj, c = p
        return f"V_e{e}_r{r}_b{b}_{'R' if obj == 0 else 'M'}_c{c}"
    if t == "LIMITE":
        x, sl, tp = p
        return f"L_x{x}_sl{sl}_tp{tp}"
    raise ValueError(f"ejecución desconocida: {spec!r}")


def validar(specs) -> list:
    """Errores de una lista de ejecuciones (vacía = válida): tipo, parámetros y nombres únicos."""
    e = []; vistos = set()
    for s in specs:
        try: n = nombre(s)
        except (ValueError, TypeError) as ex: e.append(str(ex)); continue
        if n in vistos: e.append(f"ejecución repetida: {n}")
        vistos.add(n)
        if s[0] == "MERCADO" and (s[1] <= 0 or s[2] <= 0 or max(s[3], s[4]) >= s[2]): e.append(f"{n}: stop y objetivo > 0; parcial/BE antes del objetivo")
        if s[0] == "VUELTA" and not (0 < s[2] and s[1] < s[5] and s[3] > 0): e.append(f"{n}: r > 0, b > 0 y c > e")
        if s[0] == "LIMITE" and not (s[2] > 0 and s[3] > 0): e.append(f"{n}: stop y objetivo > 0")
    return e


def limites(ctx, k):
    """Por señal: primer tick de la vela k+1 y tick de fin de la espera (TOPE velas, fin de sesión o hueco); y por vela, la
    primera vela fuera de su tramo continuo (para el vencimiento de una operación abierta en cualquier vela)."""
    t = np.asarray(ctx["t"], float); ses = np.asarray(ctx["ses"]); ts = np.asarray(ctx["tstart"], np.int64); n = len(t)
    corte = np.r_[(ses[1:] != ses[:-1]) | (np.diff(t) > GAP_S), True]
    fin = np.empty(n, np.int64); nxt = n
    for i in range(n - 1, -1, -1):
        if corte[i]: nxt = i + 1
        fin[i] = nxt
    k = np.asarray(k, np.int64)
    return ts[np.minimum(k + 1, n)], ts[np.minimum(np.minimum(k + 1 + TOPE, fin[np.minimum(k, n - 1)]), n)], fin


@njit(cache=False)
def _fin_operacion(ts, fin, j):
    kb = np.searchsorted(ts, j, side="right") - 1
    return ts[min(min(kb + 1 + 240, fin[kb]), len(ts) - 1)]


@njit(cache=False)
def _mercado_nb(tpx, j0, jw, lado, ref, sl, tp, pt, be):
    e = tpx[j0]; D = lado * (ref - e)
    if D <= 0: return np.nan, np.nan
    risk = sl * D; stop = -risk; pos = 1.0; real = 0.0; hp = pt <= 0; hb = be <= 0; fav = 0.0
    for j in range(j0 + 1, jw):
        fav = lado * (tpx[j] - e)
        if fav <= stop: return (real + pos * fav) / risk, risk            # stop a mercado: al tick que lo cruza
        if fav >= tp * D: return (real + pos * tp * D) / risk, risk       # objetivo límite: en su nivel
        if not hp and fav >= pt * D:
            real += 0.5 * pt * D; pos = 0.5; hp = True
        if not hb and fav >= be * D:
            stop = max(stop, 0.0); hb = True
    return (real + pos * fav) / risk, risk


@njit(cache=False)
def _vuelta_nb(tpx, ts, fin, j0, jw, lado, ref, ext, rg, e, r, b, obj, c):
    deep = ext; armado = False; je = -1
    for j in range(j0, jw):
        p = tpx[j]
        if lado * (deep - p) > 0: deep = p                                 # se extiende en contra de la operación
        if lado * (ext - deep) > c * rg: return np.nan, np.nan
        if lado * (p - ref) >= 0: return np.nan, np.nan                    # tocó la referencia sin entrar
        if not armado and lado * (ext - deep) >= e * rg: armado = True
        if armado and lado * (p - deep) >= r * rg:
            je = j; break
    if je < 0: return np.nan, np.nan
    ent = tpx[je]; stop = deep - lado * b * rg; o = ref if obj == 0 else (ref + ext) / 2.0
    risk = lado * (ent - stop); rew = lado * (o - ent)
    if risk <= 0 or rew <= 0: return np.nan, np.nan
    jend = _fin_operacion(ts, fin, je); fav = 0.0
    for j in range(je + 1, jend):
        fav = lado * (tpx[j] - ent)
        if fav <= -risk: return fav / risk, risk
        if fav >= rew: return rew / risk, risk
    return fav / risk, risk


@njit(cache=False)
def _limite_nb(tpx, ts, fin, j0, jw, lado, ext, rg, tick, x, sl, tp):
    lim = ext - lado * x * rg; jf = -1
    for j in range(j0, jw):                                                # «atraviesa»: un tick más allá del límite
        if lado * (tpx[j] - (lim - lado * tick)) <= 1e-12:
            jf = j; break
    if jf < 0: return np.nan, np.nan
    risk = sl * rg; rew = tp * rg; jend = _fin_operacion(ts, fin, jf); fav = 0.0
    for j in range(jf + 1, jend):
        fav = lado * (tpx[j] - lim)
        if fav <= -risk: return fav / risk, risk
        if fav >= rew: return rew / risk, risk
    return fav / risk, risk


@njit(cache=False)
def _mec_nb(tpx, j0, jw, lado, ref, ext, rg):
    deep = ext; xa = 0.0; xm = np.nan; ta = 0; tm = 0; mid = (ref + ext) / 2.0
    for j in range(j0, jw):
        p = tpx[j]
        if lado * (deep - p) > 0: deep = p
        x = lado * (ext - deep) / rg
        if not tm and lado * (p - mid) >= 0:
            tm = 1; xm = x
        if lado * (p - ref) >= 0:
            ta = 1; break
        xa = x
    return xa, xm, ta, tm


@njit(cache=False)
def _lote_mec(tpx, j0, jw, ok, lado, ref, ext, rg):
    n = len(j0); out = np.full((n, 4), np.nan)
    for q in range(n):
        if ok[q]:
            a, b, c, d = _mec_nb(tpx, j0[q], jw[q], lado[q], ref[q], ext[q], rg[q]); out[q, 0] = a; out[q, 1] = b; out[q, 2] = c; out[q, 3] = d
    return out


@njit(cache=False)
def _lote_mercado(tpx, j0, jw, ok, lado, ref, sl, tp, pt, be):
    n = len(j0); out = np.full((n, 2), np.nan)
    for q in range(n):
        if ok[q]:
            r, k = _mercado_nb(tpx, j0[q], jw[q], lado[q], ref[q], sl, tp, pt, be); out[q, 0] = r; out[q, 1] = k
    return out


@njit(cache=False)
def _lote_vuelta(tpx, ts, fin, j0, jw, ok, lado, ref, ext, rg, e, r, b, obj, c):
    n = len(j0); out = np.full((n, 2), np.nan)
    for q in range(n):
        if ok[q]:
            x, k = _vuelta_nb(tpx, ts, fin, j0[q], jw[q], lado[q], ref[q], ext[q], rg[q], e, r, b, obj, c); out[q, 0] = x; out[q, 1] = k
    return out


@njit(cache=False)
def _lote_limite(tpx, ts, fin, j0, jw, ok, lado, ext, rg, tick, x, sl, tp):
    n = len(j0); out = np.full((n, 2), np.nan)
    for q in range(n):
        if ok[q]:
            v, k = _limite_nb(tpx, ts, fin, j0[q], jw[q], lado[q], ext[q], rg[q], tick, x, sl, tp); out[q, 0] = v; out[q, 1] = k
    return out


def desenlaces(E: pd.DataFrame, ctx, specs) -> pd.DataFrame:
    """Agrega a la tabla de eventos (contrato del módulo) el recorrido `mec_*` y `r_`/`k_` de cada ejecución. Un solo pase numba
    por ejecución sobre TODOS los eventos (2026-11-11: antes una llamada por evento desde Python)."""
    err = validar(specs)
    if err: raise ValueError("; ".join(err))
    if not len(E): return E
    tpx = np.asarray(ctx["tpx"], float); ts = np.asarray(ctx["tstart"], np.int64); tick = float(ctx["tick"])
    j0, jw, fin = limites(ctx, E.k.to_numpy(np.int64))
    lado = E.lado.to_numpy(np.int64); ref = E.ref.to_numpy(float); ext = E.ext.to_numpy(float); rg = E.rg.to_numpy(float)
    ok = jw > j0 + 1; cols = {}
    mec = _lote_mec(tpx, j0, jw, ok, lado, ref, ext, rg)
    cols.update(mec_ext_antes_ref=mec[:, 0], mec_ext_antes_mitad=mec[:, 1], mec_toca_ref=mec[:, 2], mec_toca_mitad=mec[:, 3])
    for s in specs:
        p = [float(v) for v in s[1:]]
        if s[0] == "MERCADO": o = _lote_mercado(tpx, j0, jw, ok, lado, ref, *p)
        elif s[0] == "VUELTA": o = _lote_vuelta(tpx, ts, fin, j0, jw, ok, lado, ref, ext, rg, p[0], p[1], p[2], int(p[3]), p[4])
        else: o = _lote_limite(tpx, ts, fin, j0, jw, ok, lado, ext, rg, tick, *p)
        cols[f"r_{nombre(s)}"] = o[:, 0]; cols[f"k_{nombre(s)}"] = o[:, 1]
    return pd.concat([E.reset_index(drop=True), pd.DataFrame(cols)], axis=1)


# ------------------------------------------------------------------------------------------------- calibración (V3)
CALIBRACION_BASE = [("MERCADO", sl, tp, pt, be) for sl in (0.2, 0.5) for tp in (0.5, 1.0) for pt, be in ((0, 0), (0.25, 0), (0, 0.25))] + \
                   [("VUELTA", e, r, 0.1, o, e + 0.5) for e in (0.1, 0.25) for r in (0.05, 0.1) for o in (0, 1)] + \
                   [("LIMITE", x, 0.5, 1.0) for x in (0.1, 0.25)]


def huella_motor() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def calibrar(specs=None, n=3000, dias=40, seeds=(21, 22), escala=60.0, umbral_t=3.0) -> dict:
    """Entradas al azar (lado al azar, ref a `escala` puntos a favor, ext = cierre, rg = escala) sobre caminatas sintéticas sin
    deriva, con y sin saltos. Un motor honesto no puede dar R medio positivo y significativo en ninguna ejecución: `optimistas`
    lista las que superan t > `umbral_t` (con la convención del stop al tick, los saltos dan R NEGATIVO: eso no se marca).
    El t es por SESIÓN (suma de R de cada día como unidad): las entradas al azar del mismo día se superponen y un t por evento
    sale inflado (daba ±3–4,6 en caminatas sin efecto). Devuelve el detalle por ejecución y la huella del motor."""
    from edgelab.research import grilla_generica as GG, sintetico
    specs = list(specs or CALIBRACION_BASE); res = {}; malas = set()
    for seed in seeds:
        for saltos in (0.0, 0.005):
            ctx = GG.contexto_m1(sintetico.bloques(dias=dias, planta=False, seed=seed, prob_salto=saltos), tick=0.25)
            rng = np.random.default_rng(seed); m = len(ctx["c"]); k = rng.integers(50, m - TOPE - 5, n); lado = rng.choice([-1, 1], n)
            c = np.asarray(ctx["c"])[k]
            E = pd.DataFrame(dict(k=k, lado=lado, ref=c + lado * escala, ext=c, rg=escala))
            T = desenlaces(E, ctx, specs)
            ses = np.asarray(ctx["ses"])[k]
            for s in specs:
                y = T[f"r_{nombre(s)}"].to_numpy(float); m = np.isfinite(y)
                if m.sum() < 30: continue
                g = pd.Series(y[m]).groupby(ses[m]).sum().to_numpy()            # t por sesión: las entradas de un día se pisan
                y = y[m]; t = float(g.sum() / np.sqrt((g ** 2).sum())) if (g ** 2).sum() > 0 else 0.0
                res.setdefault(nombre(s), []).append(dict(seed=seed, saltos=saltos, n=int(len(y)), media=round(float(y.mean()), 4), t=round(t, 2)))
                if t > umbral_t: malas.add(nombre(s))
    return dict(huella=huella_motor(), optimistas=sorted(malas), detalle=res)
