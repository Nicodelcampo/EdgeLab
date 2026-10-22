"""AREAS-EXP-1: áreas de zonas OG/VI, expansión y regreso (spec `docs/research/areas_expansion_20261022/SPEC_AREAS_EXPANSION_V1.md`).

Autocontenido (numpy, pandas, numba) para poder empaquetarse en un kernel de Kaggle sin el repo.
Separación estricta: `eventos()` y `variables()` son target-free (sólo pasado de cada disparo); los desenlaces salen de
`simular()` y la estadística de `tensor_celdas()`. Precios en TICKS enteros del instrumento (float para el mid del índice).
"""
from __future__ import annotations

import numpy as np

try:
    from numba import njit
except ImportError:                                    # sin numba (tests mínimos): misma lógica, más lenta
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

VIDA_MIN = 500          # vida de una zona LUX-IMB y ventana de no repetición de áreas
TOPE_DISPARO_MIN = 500  # desde la marca del área
ESPERA_LIMITE = 120     # barras para llenar una orden límite
TOPE_OPERACION = 240    # barras de tenencia máxima
NS = (3, 5, 8)
WS = (5.0, 15.0, 40.0, 100.0)                 # altura máxima del área (puntos de precio; NQ y USATECH cotizan ~al mismo nivel)
XS = (0.75, 0.50, 0.25)
A_CORTES = (1.0, 2.0, 4.0, 8.0)         # A/H >= ...  (distancias muy variadas, espaciado geométrico)
MAX_CICLOS = 10                         # evaluaciones por área (atravesarla no la invalida)
COM_CORTES = (0.0, 1.0, 3.0)            # comercio <= ... (más "cualquiera")
PV_CORTES = (1 / 3, 2 / 3)              # p_vol < 1/3, 1/3-2/3, > 2/3
# ejecución: (dirección, objetivo) x entrada x stop x BE
DIR_OBJ = (("HACIA", "T1"), ("HACIA", "T2"), ("HACIA", "T3"), ("REBOTE", "1R"), ("REBOTE", "2R"), ("REBOTE", "E"))
# Momento de la entrada a mercado: NO es una regla universal (decisión de Nico, 2026-10-22: «depende del análisis»); acá se
# prueban las dos como perilla. E1C = al cierre de la vela de decisión; E1A = primer tick de la vela siguiente.
ENTRADAS = ("E1C", "E1A", "E2", "E3")
STOPS = ("S1", "S2", "S3")
BES = (0, 1)
EJEC = [(d, o, e, s, b) for (d, o) in DIR_OBJ for e in ENTRADAS for s in STOPS for b in BES]       # 108


# ----------------------------------------------------------------------------------------------- detector (copia de parity_luximb.detect)
def detect(o, h, l, c, show_og=True, show_vi=True):
    """Réplica de OnBarUpdate del ImbalanceDetectorLuxAlgoMTF (M1, OnBarClose). Paridad NT8 exacta medida en NQ."""
    out = []
    for i in range(3, len(c)):
        O0, H0, L0, C0, O1, H1, L1, C1 = o[i], h[i], l[i], c[i], o[i - 1], h[i - 1], l[i - 1], c[i - 1]
        bull_top, bull_btm = min(C0, O0), max(C1, O1)
        bear_top, bear_btm = min(C1, O1), max(C0, O0)
        bull_vi = show_vi and O0 > C1 and H1 > L0 and C0 > C1 and O0 > O1 and H1 < bull_top
        bear_vi = show_vi and O0 < C1 and L1 < H0 and C0 < C1 and O0 < O1 and L1 > bear_btm
        bull_og = show_og and L0 > H1
        bear_og = show_og and H0 < L1
        if bull_vi: out.append((i, "VI", "bull", bull_top, bull_btm))
        if bear_vi: out.append((i, "VI", "bear", bear_top, bear_btm))
        if bull_og: out.append((i, "OG", "bull", bull_top, bull_btm))
        if bear_og: out.append((i, "OG", "bear", bear_top, bear_btm))
    return out


def zonas(t_close, o, h, l, c):
    """Zonas como arreglos. zi = barra creadora (disponible a su cierre); zfin = primera barra cuyo cierre supera la vida."""
    z = detect(o, h, l, c)
    if not z:
        e = np.zeros(0)
        return dict(zi=e.astype(np.int64), zlo=e, zhi=e, zfin=e.astype(np.int64), og=e.astype(bool))
    zi = np.array([x[0] for x in z], np.int64)
    a = np.array([x[3] for x in z], float); b = np.array([x[4] for x in z], float)
    zfin = np.searchsorted(t_close, t_close[zi] + VIDA_MIN * 60, side="right")
    return dict(zi=zi, zlo=np.minimum(a, b), zhi=np.maximum(a, b), zfin=zfin, og=np.array([x[1] == "OG" for x in z]))


def visitas_acumuladas(Z, h, l, max_vida=VIDA_MIN + 5):
    """V[k, d] = cantidad de ENTRADAS del precio a la zona k (vela que la corta con la anterior afuera) entre zi+1 y zi+1+d."""
    n = len(h); K = len(Z["zi"])
    if K == 0: return np.zeros((0, max_vida), np.int16)
    off = np.arange(max_vida)
    idx = np.minimum(Z["zi"][:, None] + 1 + off[None, :], n - 1)
    vivo = (Z["zi"][:, None] + 1 + off[None, :]) < np.minimum(Z["zfin"], n)[:, None]
    dentro = (l[idx] <= Z["zhi"][:, None]) & (h[idx] >= Z["zlo"][:, None]) & vivo
    prev = np.concatenate([np.zeros((K, 1), bool), dentro[:, :-1]], axis=1)
    return np.cumsum(dentro & ~prev, axis=1).astype(np.int16)


def visitas_en(V, Z, miembros, k):
    d = k - Z["zi"][miembros] - 1
    v = np.where(d < 0, 0, V[miembros, np.clip(d, 0, V.shape[1] - 1)])
    return float(v.mean()) if len(v) else 0.0


# ----------------------------------------------------------------------------------------------- áreas (target-free)
@njit(cache=False)
def _eventos_nb(zi, zlo, zhi, zfin, t_close, ns, ws, G, vida_s):
    """Núcleo compilado de `eventos` (misma regla). Devuelve arreglos planos: m, lo, hi, idx_N, idx_W, inicio de miembros, y miembros."""
    K = len(zi); orden = np.argsort(zi, kind="mergesort")
    ev_m = []; ev_lo = []; ev_hi = []; ev_n = []; ev_w = []; ev_off = [0]; miembros = []
    nk = len(ns) * len(ws)
    mk_t = np.empty((nk, 4096)); mk_lo = np.empty((nk, 4096)); mk_hi = np.empty((nk, 4096)); mk_a = np.zeros(nk, np.int64); mk_b = np.zeros(nk, np.int64)
    nmin = ns.min(); p = 0; vivos = np.empty(K, np.int64); nv = 0
    while p < K:
        m = zi[orden[p]]
        while p < K and zi[orden[p]] == m:                                    # agrega las zonas nacidas en m
            vivos[nv] = orden[p]; nv += 1; p += 1
        q = 0
        for r in range(nv):                                                   # saca las vencidas
            if zfin[vivos[r]] > m: vivos[q] = vivos[r]; q += 1
        nv = q
        if nv < nmin: continue
        o = vivos[:nv][np.argsort(zlo[vivos[:nv]], kind="mergesort")]
        lo_v = zlo[o]; hi_v = zhi[o]
        for kk in range(nk):                                                  # poda: marcas de más de 500 min
            while mk_a[kk] < mk_b[kk] and t_close[m] - mk_t[kk, mk_a[kk] % 4096] > vida_s: mk_a[kk] += 1
        for wi in range(len(ws)):
            w = ws[wi]; cnt = np.zeros(nv, np.int64); alto = np.full(nv, -1e300); nueva = np.zeros(nv, np.bool_)
            for i in range(nv):
                lim = lo_v[i] + w; j0 = i
                while j0 > 0 and lo_v[j0 - 1] == lo_v[i]: j0 -= 1                 # incluye zonas con el mismo piso
                for j in range(j0, nv):
                    if lo_v[j] > lim: break
                    if hi_v[j] <= lim:
                        cnt[i] += 1
                        if hi_v[j] > alto[i]: alto[i] = hi_v[j]
                        if zi[o[j]] == m: nueva[i] = True
            nc = 0; idx = np.empty(nv, np.int64)
            for i in range(nv):
                if cnt[i] >= nmin and nueva[i]: idx[nc] = i; nc += 1
            if nc == 0: continue
            idx = idx[:nc]                                                     # dos ordenamientos estables (= lexsort): ancho, luego -cnt
            idx = idx[np.argsort(alto[idx] - lo_v[idx], kind="mergesort")]
            sel = idx[np.argsort(-cnt[idx], kind="mergesort")]
            u_lo = np.empty(nc); u_hi = np.empty(nc); nu = 0
            for i in sel:
                lo_ = lo_v[i]; hi_ = alto[i]; choca = False
                for u in range(nu):
                    if lo_ <= u_hi[u] and hi_ >= u_lo[u]: choca = True; break
                if choca: continue
                u_lo[nu] = lo_; u_hi[nu] = hi_; nu += 1
                for ni in range(len(ns)):
                    if cnt[i] < ns[ni]: continue
                    kk = ni * len(ws) + wi; dup = False
                    for r in range(mk_a[kk], mk_b[kk]):
                        if lo_ <= mk_hi[kk, r % 4096] + G and hi_ >= mk_lo[kk, r % 4096] - G: dup = True; break
                    if dup: continue
                    r = mk_b[kk] % 4096; mk_t[kk, r] = t_close[m]; mk_lo[kk, r] = lo_; mk_hi[kk, r] = hi_; mk_b[kk] += 1
                    ev_m.append(m); ev_lo.append(lo_); ev_hi.append(hi_); ev_n.append(ni); ev_w.append(wi)
                    lim = lo_ + w; j0 = i
                    while j0 > 0 and lo_v[j0 - 1] == lo_v[i]: j0 -= 1
                    for j in range(j0, nv):
                        if lo_v[j] > lim: break
                        if hi_v[j] <= lim: miembros.append(o[j])
                    ev_off.append(len(miembros))
    return (np.array(ev_m, np.int64), np.array(ev_lo), np.array(ev_hi), np.array(ev_n, np.int64), np.array(ev_w, np.int64),
            np.array(ev_off, np.int64), np.array(miembros, np.int64))


def eventos(Z, t_close, G, ns=NS, ws=None):
    """Marca de áreas (spec v1.1): un ÁREA es una banda de precio de altura <= W con >= N zonas vivas enteras («X cantidad de
    zonas» en «X área»). En cada barra donde nace una zona se buscan las bandas que incluyen alguna zona nueva; se toma la de
    más zonas (desempate: la más angosta) y, sin superponerse, las siguientes. Se marca la PRIMERA vez que llega a N y se
    descarta si se superpone (o queda a <= G) con un área de la misma (N, W) marcada en los 500 min anteriores («dos pegadas
    cuentan una sola»). Devuelve {(N, W): [(m, lo, hi, miembros)]}. Núcleo compilado en `_eventos_nb`."""
    ws = tuple(ws or WS); out = {(n_, w_): [] for n_ in ns for w_ in ws}
    if len(Z["zi"]) == 0: return out
    m, lo, hi, en, ew, off, mem = _eventos_nb(Z["zi"].astype(np.int64), Z["zlo"].astype(float), Z["zhi"].astype(float),
                                              Z["zfin"].astype(np.int64), np.asarray(t_close, float), np.array(ns, np.int64),
                                              np.array(ws, float), float(G), float(VIDA_MIN * 60))
    for i in range(len(m)):
        out[(ns[en[i]], ws[ew[i]])].append((int(m[i]), float(lo[i]), float(hi[i]), mem[off[i]:off[i + 1]]))
    return out


def disparos(ev, h, l, c, t_close, fin=None, xs=XS):
    """Ciclos de alejamiento y regreso sobre UNA área (pedido de Nico: atravesarla no la invalida; se evalúa varias veces).
    Un ciclo: el precio cierra fuera del área (lado), se aleja >= 1·H del borde cercano sin volver a cerrar adentro (si vuelve
    antes, el ciclo se reinicia sin descartar el área) y después regresa; el disparo de cada x es el primer cierre con
    D <= x·A. El ciclo termina cuando vuelve a cerrar dentro del área (o cruza); el siguiente arranca en la barra siguiente,
    del lado que sea. El área vive hasta que vence su última zona (`fin`, índice exclusivo). Sólo usa barras hasta cada disparo."""
    m, lo, hi, _ = ev; H = hi - lo
    if H <= 0: return []
    fin = min(len(c), fin if fin is not None else np.searchsorted(t_close, t_close[m] + TOPE_DISPARO_MIN * 60, side="right"))
    out, j0, ciclo = [], m + 1, 0
    while j0 < fin and ciclo < MAX_CICLOS:
        j = np.arange(j0, fin)
        fuera = np.flatnonzero((c[j] > hi) | (c[j] < lo))
        if len(fuera) == 0: break
        js = j[fuera[0]]; lado = 1 if c[js] > hi else -1; jj = np.arange(js, fin)
        if lado == 1: E = np.maximum.accumulate(h[jj]); A = E - hi; D = c[jj] - hi
        else: E = np.minimum.accumulate(l[jj]); A = lo - E; D = lo - c[jj]
        adentro = D <= 0                                                       # cerró dentro del área o del otro lado
        ok = A >= H
        if not ok.any(): break
        a1 = int(np.argmax(ok))
        if adentro[:a1].any():                                                 # volvió antes de alejarse 1·H: reinicia el ciclo
            j0 = int(jj[int(np.argmax(adentro[:a1]))]) + 1; continue
        reg = np.flatnonzero(adentro & (np.arange(len(jj)) > a1))
        q_fin = int(reg[0]) if len(reg) else len(jj) - 1                      # fin del ciclo: vuelve a cerrar adentro
        for xi, x in enumerate(xs):
            cond = ok & (D <= x * A) & (np.arange(len(jj)) > a1) & (np.arange(len(jj)) <= q_fin)
            if cond.any():
                q = int(np.argmax(cond)); k = int(jj[q])
                out.append(dict(m=m, k=k, xi=xi, ciclo=ciclo, lado=lado, lo=lo, hi=hi, H=H, E=float(E[q]), A=float(A[q]), D=float(D[q])))
        ciclo += 1; j0 = int(jj[q_fin]) + 1
    return out


def perfil_volumen(d, vp_min_start, vp_px, vp_vol):
    """Tramo de máximo volumen entre el borde cercano y el extremo, con las operaciones de m+1..k. Devuelve (p_vol, vol_conc, precio).
    (Versión de a uno; el conductor usa `perfiles_volumen`, compilada y en lote, con el mismo resultado.)"""
    r = perfiles_volumen(np.array([d["m"]]), np.array([d["k"]]), np.array([d["lado"]]), np.array([d["hi"] if d["lado"] == 1 else d["lo"]]),
                         np.array([d["A"]]), vp_min_start, vp_px, vp_vol)
    return r[0][0], r[1][0], r[2][0]


@njit(cache=False)
def perfiles_volumen(m, k, lado, borde, A, vp_min_start, vp_px, vp_vol):
    """En lote: para cada disparo, perfil de 10 tramos entre el borde cercano (0) y el extremo (1) con el volumen negociado
    de las barras m+1..k. Devuelve p_vol (centro del tramo de máximo volumen), volumen de ese tramo ±1 y su precio."""
    T = len(m); pv = np.full(T, np.nan); vc = np.zeros(T); pp = np.full(T, np.nan); hb = np.zeros(10)
    for t in range(T):
        hb[:] = 0.0; tot = 0.0
        for i in range(vp_min_start[m[t] + 1], vp_min_start[k[t] + 1]):
            pos = (vp_px[i] - borde[t]) * lado[t] / max(A[t], 1e-9)
            if pos < 0 or pos > 1: continue
            b = min(int(pos * 10), 9); hb[b] += vp_vol[i]; tot += vp_vol[i]
        if tot <= 0: continue
        j = 0
        for q in range(1, 10):
            if hb[q] > hb[j]: j = q
        pv[t] = (j + 0.5) / 10; vc[t] = hb[max(j - 1, 0):j + 2].sum(); pp[t] = borde[t] + lado[t] * pv[t] * A[t]
    return pv, vc, pp


# ----------------------------------------------------------------------------------------------- simulación (desenlaces)
@njit(cache=False)
def _primero_en_ticks(tpx, a, b, d, st, tp, tick):
    """Orden real dentro de una vela: primer tick que toca el stop (1) o atraviesa el objetivo por 1 tick (2), desde el
    índice de tick a hasta b. Devuelve (código, precio). Código 0 si ninguno (no debería, la vela los tocó)."""
    for i in range(a, b):
        x = tpx[i]
        if d == 1:
            if x <= st: return 1, min(st, x)
            if x >= tp + tick: return 2, tp
        else:
            if x >= st: return 1, max(st, x)
            if x <= tp - tick: return 2, tp
    return 0, np.nan


@njit(cache=False)
def simular(start, s, limite, nivel, stop0, tp, be, o, h, l, c, sesion, tick, tpx, tstart):
    """Una operación por fila. s = +1 compra / -1 venta. limite=0: mercado al cierre de `start` (precio c[start]).
    limite=1: orden límite en `nivel`, se llena si el precio la atraviesa por 1 tick dentro de 120 barras.
    limite=2: mercado en el PRIMER TICK de la vela siguiente (misma sesión). El momento de llenado es una decisión de cada
    análisis: el simulador no impone ninguno; quien lo llama lo declara por operación.
    AMBIGÜEDAD M1 (pedido de Nico): si una vela toca stop y objetivo, o en la vela del llenado de una límite, se resuelve con
    el ORDEN DE LOS TICKS de esa vela (`tpx`, con `tstart[j]..tstart[j+1]` los ticks del minuto j). Sin ticks para esa vela:
    se toma el stop (conservador) y se cuenta. Stop con hueco al precio real. Salida por tiempo (240) o fin de sesión al cierre.
    Devuelve (pnl en precio por operación, NaN = sin llenado; código de resolución: 0 sin ambigüedad, 1 resuelta con ticks,
    2 sin ticks -> stop)."""
    T = len(start); pnl = np.full(T, np.nan); amb = np.zeros(T, np.int8); n = len(c)
    for t in range(T):
        k = start[t]; d = s[t]; st = stop0[t]; obj = tp[t]
        if limite[t] == 0:                                                 # E1C: llenado al cierre de la vela de decisión
            e = c[k]; f = k
        elif limite[t] == 2:                                               # E1A: llenado en el primer tick de la vela siguiente
            f = k + 1
            if f >= n or sesion[f] != sesion[k]: continue
            e = o[f]
            if tstart[f + 1] > tstart[f]:
                cod, px = _primero_en_ticks(tpx, tstart[f] + 1, tstart[f + 1], d, st, obj, tick)
                if cod == 1: pnl[t] = (px - e) * d; amb[t] = 1; continue
                if cod == 2: pnl[t] = (obj - e) * d; amb[t] = 1; continue
            elif (d == 1 and l[f] <= st) or (d == -1 and h[f] >= st):
                pnl[t] = (st - e) * d; amb[t] = 2; continue
        else:
            e = nivel[t]; f = -1; ia = 0
            for j in range(k + 1, min(n, k + 1 + 120)):
                if sesion[j] != sesion[k]: break
                if (d == 1 and l[j] <= e - tick) or (d == -1 and h[j] >= e + tick):
                    f = j; ia = tstart[j + 1]
                    for i in range(tstart[j], tstart[j + 1]):                        # tick exacto del llenado
                        if (d == 1 and tpx[i] <= e - tick) or (d == -1 and tpx[i] >= e + tick): ia = i + 1; break
                    break
            if f < 0: continue
            # resto de la vela del llenado, en orden de ticks
            if tstart[f + 1] > tstart[f]:
                cod, px = _primero_en_ticks(tpx, ia, tstart[f + 1], d, st, obj, tick)
                if cod == 1: pnl[t] = (px - e) * d; amb[t] = 1; continue
                if cod == 2: pnl[t] = (obj - e) * d; amb[t] = 1; continue
            elif (d == 1 and l[f] <= st) or (d == -1 and h[f] >= st):
                pnl[t] = (st - e) * d; amb[t] = 2; continue
        R = abs(e - stop0[t]); x = np.nan; armado = False
        j = f + 1; ult = f
        while j < n and j - f <= 240 and sesion[j] == sesion[f]:
            if d == 1: ts_, tt_ = l[j] <= st, h[j] >= obj + tick
            else: ts_, tt_ = h[j] >= st, l[j] <= obj - tick
            if ts_ and tt_:                                                         # ambigua en M1: orden de los ticks
                if tstart[j + 1] > tstart[j]:
                    cod, px = _primero_en_ticks(tpx, tstart[j], tstart[j + 1], d, st, obj, tick)
                    amb[t] = 1
                    if cod == 2: x = (obj - e) * d
                    else: x = ((px if cod == 1 else st) - e) * d
                else:
                    amb[t] = 2; x = ((min(st, o[j]) if d == 1 else max(st, o[j])) - e) * d
                break
            if ts_: x = ((min(st, o[j]) if d == 1 else max(st, o[j])) - e) * d; break
            if tt_: x = (obj - e) * d; break
            if be[t] == 1 and not armado and (h[j] - e if d == 1 else e - l[j]) >= R:
                armado = True; st = max(st, e) if d == 1 else min(st, e)
            ult = j; j += 1
        if np.isnan(x): x = (c[ult] - e) * d
        pnl[t] = x
    return pnl, amb


def niveles(d, ejec, pv_precio, tick, c):
    """Precios de entrada/stop/objetivo de una ejecución sobre un disparo. None si la combinación no aplica."""
    di, ob, en, sl, be = ejec; lado = d["lado"]; borde, lejos = (d["hi"], d["lo"]) if lado == 1 else (d["lo"], d["hi"])
    s = -lado if di == "HACIA" else lado                                       # HACIA: hacia el área
    if en == "E1C": lim, e = 0, float(c[d["k"]])
    elif en == "E1A": lim, e = 2, float(c[d["k"]])                         # niveles planeados al cierre; el llenado real es el tick siguiente
    elif en == "E2":
        if not np.isfinite(pv_precio): return None
        lim, e = 1, float(pv_precio)
        if (s == -1 and e <= c[d["k"]]) or (s == 1 and e >= c[d["k"]]): return None     # sólo del lado favorable
    else:
        if di == "HACIA": return None                                          # E3 (borde) sólo tiene sentido en REBOTE
        lim, e = 1, float(borde)
    if di == "HACIA":
        tp = {"T1": borde, "T2": (d["lo"] + d["hi"]) / 2, "T3": lejos}[ob]; dist = (e - tp) * -s
        if dist < tick: return None
        st = {"S1": e - s * 0.5 * dist, "S2": e - s * 1.0 * dist, "S3": d["E"] - s * tick}[sl]
    else:
        st = {"S1": e - s * 0.5 * d["H"], "S2": e - s * 1.0 * d["H"], "S3": lejos - s * tick}[sl]
        R = (e - st) * s
        if R < tick: return None
        tp = {"1R": e + s * R, "2R": e + s * 2 * R, "E": d["E"]}[ob]
        if (tp - e) * s < tick: return None
    if (e - st) * s < tick: return None
    return lim, s, e, st, tp, be


# ----------------------------------------------------------------------------------------------- tensor de celdas
def bins_variables(A_H, com, pv, vr, vr_cortes, com_cortes=COM_CORTES):
    """com_cortes: 3 cortes crecientes para «comercio <= ...» (E0 v1.1: cuartiles de cada fuente; con datos reales la mediana
    ronda 10 visitas por zona y los cortes fijos 0/1/3 dejaban casi todo en «cualquiera»)."""
    ab = np.digitize(A_H, A_CORTES) - 1                                  # 0: [1,2) 1: [2,4) 2: [4,8) 3: >=8  (-1: < 1)
    c1, c2, c3 = com_cortes
    cb = np.where(com <= c1, 0, np.where(com <= c2, 1, np.where(com <= c3, 2, 3)))
    pb = np.where(~np.isfinite(pv), -1, np.digitize(pv, PV_CORTES))
    vr = np.asarray(vr, float)
    vb = np.where(np.isfinite(vr), np.digitize(vr, vr_cortes), -1)       # 0 bajo, 1 medio, 2 alto; sin dato = fuera (v1.2 lo mandaba a «bajo»)
    return ab, cb, pb, vb


def perillas():
    """Perillas del experimento en el formato del núcleo genérico (edgelab/research/grilla_masiva.py)."""
    from edgelab.research.grilla_masiva import Perilla
    return [Perilla("N×W", len(NS) * len(WS), "grupo"), Perilla("x", len(XS), "grupo"), Perilla("ejecución", len(EJEC), "grupo"),
            Perilla("A/H", len(A_CORTES), "ge"), Perilla("comercio", 4, "le"), Perilla("p_vol", 3, "eq_any"), Perilla("v_rel", 3, "extremos")]


EJES_ORDINALES = (1, 3, 4)          # x, A/H, comercio (el stop se trata aparte: está dentro de la ejecución)


def tensor_celdas(ni, xi, ei, ab, cb, pb, vb, net, wi=None):
    """Compatibilidad: tensor de celdas vía el núcleo genérico. Con `wi`, la primera dimensión es N*len(WS)+W; sin `wi`, sólo N."""
    from edgelab.research.grilla_masiva import Perilla, tensor
    P = perillas()
    if wi is None: P[0] = Perilla("N", 3, "grupo"); g = ni
    else: g = ni * len(WS) + wi
    return tensor(P, [g, xi, ei, ab, cb, pb, vb], net)
