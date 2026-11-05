"""U1-COMBO E0 (2026-10-30): censo SIN desenlaces de áreas combinadas: al menos A zonas de la fuente 1 y B de la fuente 2 dentro de una
ventana de tiempo y un rango de precio. Sólo cuenta áreas y sesiones: no hay disparos, retornos, P&L ni operaciones.

Definiciones (todas evaluadas sólo con el pasado de la marca `m`, en velas M1 de NQ):
- zona disponible: cierre de la primera vela que cierra EN O DESPUÉS de su creación (en ns, redondeado hacia arriba al segundo;
  `u1_zonas.zonas_almacen` trunca los ns, por eso se le pasa la hora ya redondeada). Vive `AX.VIDA_MIN`, o hasta `t_fin_ns` (BigTrap2).
- ATR: media simple de 14 rangos verdaderos M1 por segmento, hasta la vela inclusive.
- ventana V (min): edad máxima de cada zona de la banda en la marca.
- rango R (ATR): altura máxima de la banda, R·ATR de la marca.
- amplitud Am (ATR): alto máximo de cada zona, Am·ATR de la vela donde queda disponible.
- área: misma regla de `AX.eventos` (la banda debe incluir una zona nueva; más zonas, después la más angosta; sin solaparse; se descarta
  si queda a <= G de un área de la misma combinación marcada en los 500 min anteriores), exigiendo A y B por fuente.
- segmento: una zona sólo cuenta dentro del segmento de NQ en que queda disponible (no cruza contratos).
- traslado CFD→NQ: base = cierre NQ − cierre CFD, ambos as-of de la creación (última vela con cierre <= creación, a <= TOL_BASE_S).
  Sin base válida, o si la zona queda disponible en otro segmento que su base, se descarta y se cuenta.
- degenerada: sin áreas, todas de altura nula, o >= CONC_DEGENERADA de las áreas en una sola sesión.
- duplicada: mismas áreas (m, lo, hi) que una combinación anterior del par.
Cortes: cuantiles E0 de cada par (GUIA_GRILLA_MASIVA §1.5), medidos sólo en la ventana censada.
"""
from __future__ import annotations

import hashlib
from itertools import combinations, product

import numpy as np
import pandas as pd

from edgelab.research import areas_expansion as AX
from edgelab.research import u1_zonas as UZ

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

DESDE, HASTA = 20250805, 20260331
FUENTES = ("LUX_CFD", "LUX_NQ", "AVZP2", "AVCL", "BT2")
ATR_N, G_PTS, TOL_BASE_S = 14, 1.0, 300
Q_CANT, Q_RANGO, Q_VENTANA, Q_AMPLITUD = (0.5, 0.75, 0.9), (0.25, 0.5, 0.75), (0.25, 0.5, 0.75), (0.5, 0.75, 0.9)
MIN_AREAS, MIN_SESIONES, CONC_DEGENERADA = 30, 20, 0.5


def ceil_s(ns) -> np.ndarray:
    return (np.asarray(ns, np.int64) + 999_999_999) // 1_000_000_000


def ctx_m1(bloques) -> dict:
    """Velas M1 livianas (sin ticks ni perfil): el censo sólo necesita OHLC, sesión y segmento."""
    ps = []
    for b in bloques:
        if not len(b): continue
        d = pd.DataFrame(dict(t=(b.ts_ns.to_numpy() // 60_000_000_000 + 1) * 60, p=b.px.to_numpy(float), ses=b.sesion.to_numpy(), seg=b.segmento.to_numpy()))
        g = d.groupby("t", sort=True)
        ps.append(pd.DataFrame(dict(o=g.p.first(), h=g.p.max(), l=g.p.min(), c=g.p.last(), ses=g.ses.last(), seg=g.seg.last())))
    M = pd.concat(ps).sort_index()
    if M.index.has_duplicates: raise ValueError("minutos repetidos entre bloques")
    return dict(t=M.index.to_numpy(np.int64), **{k: M[k].to_numpy(float) for k in "ohlc"}, ses=M.ses.to_numpy(np.int64), seg=M.seg.to_numpy(np.int64))


def lux_almacen(ctx) -> pd.DataFrame:
    """LUX-IMB (OG y VI) por segmento en formato almacén: creación = cierre de la vela creadora."""
    t, seg = ctx["t"], ctx["seg"]; out = []
    for s in pd.unique(seg):
        i = np.flatnonzero(seg == s); a, b = i[0], i[-1] + 1
        Z = AX.zonas(t[a:b], *(ctx[k][a:b] for k in "ohlc"))
        out.append(pd.DataFrame(dict(t_ns=t[a:b][Z["zi"]] * 10**9, lo=Z["zlo"], hi=Z["zhi"])))
    return pd.concat(out, ignore_index=True)


def trasladar(Zs: pd.DataFrame, cfd: dict, nq: dict, tol_s: int = TOL_BASE_S) -> tuple:
    """Zonas CFD a precio NQ con la base as-of de su creación. Devuelve (zonas, descartadas)."""
    tz = ceil_s(Zs.t_ns.to_numpy()); i = np.searchsorted(nq["t"], tz, side="right") - 1; j = np.searchsorted(cfd["t"], tz, side="right") - 1
    ok = (i >= 0) & (j >= 0)
    ok[ok] = (tz[ok] - nq["t"][i[ok]] <= tol_s) & (tz[ok] - cfd["t"][j[ok]] <= tol_s)
    sig = np.searchsorted(nq["t"], tz, side="left")               # vela NQ donde quedará disponible: debe ser del segmento de la base
    ok &= sig < len(nq["t"])
    ok[ok] = nq["seg"][sig[ok]] == nq["seg"][i[ok]]
    Z = Zs[ok].copy(); base = nq["c"][i[ok]] - cfd["c"][j[ok]]
    Z["lo"] = Z.lo.to_numpy(float) + base; Z["hi"] = Z.hi.to_numpy(float) + base
    return Z.reset_index(drop=True), int((~ok).sum())


def indexar(Zs: pd.DataFrame, t) -> dict:
    """Zonas en índices de `t` sin adelantar ni la creación ni el cierre por truncar ns."""
    Z = Zs.assign(t_ns=ceil_s(Zs.t_ns.to_numpy()) * 10**9)
    if "t_fin_ns" in Z:
        tf = Z.t_fin_ns.to_numpy(np.int64); Z["t_fin_ns"] = np.where(tf > 0, ceil_s(tf) * 10**9, tf)
    return UZ.zonas_almacen(Z, t)


def atr(h, l, c, n: int = ATR_N) -> np.ndarray:
    tr = h - l
    if len(c) > 1: tr = np.r_[tr[0], np.maximum.reduce([h[1:] - l[1:], np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])])]
    return pd.Series(tr).rolling(n).mean().to_numpy()


@njit(cache=False)
def _areas_nb(zi, zlo, zhi, zfin, src, t, a_t, A, B, R, V, Am, G, vida_s):
    """Marcas (m, lo, hi) de una combinación. `zi` ordenado. src: 0 fuente 1, 1 fuente 2. Oráculo: `areas_py`."""
    K = len(zi); mk_m = np.empty(K, np.int64)
    mk_t = np.empty(K); mk_lo = np.empty(K); mk_hi = np.empty(K); ma = 0; mb = 0
    vivos = np.empty(K, np.int64); nv = 0; p = 0
    while p < K:
        m = zi[p]; nuevas = 0
        while p < K and zi[p] == m:
            if zhi[p] - zlo[p] <= Am * a_t[m]: vivos[nv] = p; nv += 1; nuevas += 1
            p += 1
        if nuevas == 0: continue
        q = 0
        for r in range(nv):
            z = vivos[r]
            if zfin[z] > m and t[m] - t[zi[z]] <= V * 60.0: vivos[q] = z; q += 1
        nv = q
        w = R * a_t[m]
        if nv < A + B or not w >= 0: continue
        while ma < mb and t[m] - mk_t[ma] > vida_s: ma += 1
        o = vivos[:nv][np.argsort(zlo[vivos[:nv]], kind="mergesort")]
        lo_v = zlo[o]; hi_v = zhi[o]; ct = np.zeros(nv, np.int64); alto = np.full(nv, -1e300); nc = 0; idx = np.empty(nv, np.int64)
        for i in range(nv):
            if i > 0 and lo_v[i] == lo_v[i - 1]: continue              # mismo piso, misma banda
            lim = lo_v[i] + w; ca = 0; cb = 0; nueva = False
            for j in range(i, nv):
                if lo_v[j] > lim: break
                if hi_v[j] <= lim:
                    if src[o[j]] == 0: ca += 1
                    else: cb += 1
                    if hi_v[j] > alto[i]: alto[i] = hi_v[j]
                    if zi[o[j]] == m: nueva = True
            if nueva and ca >= A and cb >= B: ct[i] = ca + cb; idx[nc] = i; nc += 1
        if nc == 0: continue
        idx = idx[:nc]
        idx = idx[np.argsort(alto[idx] - lo_v[idx], kind="mergesort")]
        idx = idx[np.argsort(-ct[idx], kind="mergesort")]
        u0 = mb
        for i in idx:
            lo_ = lo_v[i]; hi_ = alto[i]; dup = False
            for r in range(u0, mb):                                   # sin solaparse con las de esta misma vela
                if lo_ <= mk_hi[r] and hi_ >= mk_lo[r]: dup = True; break
            if dup: continue
            for r in range(ma, u0):
                if lo_ <= mk_hi[r] + G and hi_ >= mk_lo[r] - G: dup = True; break
            if dup: continue
            mk_m[mb] = m; mk_t[mb] = t[m]; mk_lo[mb] = lo_; mk_hi[mb] = hi_; mb += 1
    return mk_m[:mb], mk_lo[:mb], mk_hi[:mb]


def areas_py(zi, zlo, zhi, zfin, src, t, a_t, A, B, R, V, Am, G, vida_s):
    """Oráculo sin compilar de `_areas_nb`: recalcula todo vela por vela con listas."""
    marcas = []
    for m in sorted({int(x) for x, l_, h_ in zip(zi, zlo, zhi) if h_ - l_ <= Am * a_t[x]}):
        el = [z for z in range(len(zi)) if zi[z] <= m and zhi[z] - zlo[z] <= Am * a_t[zi[z]] and zfin[z] > m and t[m] - t[zi[z]] <= V * 60.0]
        w = R * a_t[m]
        if not w >= 0: continue
        cand = []
        for lo_ in sorted({float(zlo[z]) for z in el}):
            b = [z for z in el if lo_ <= zlo[z] and zhi[z] <= lo_ + w]
            if sum(src[z] == 0 for z in b) >= A and sum(src[z] == 1 for z in b) >= B and any(zi[z] == m for z in b):
                alto = max(float(zhi[z]) for z in b); cand.append((-len(b), alto - lo_, lo_, alto))
        previas = [x for x in marcas if t[m] - t[x[0]] <= vida_s]; aca = []
        for _, _, lo_, hi_ in sorted(cand, key=lambda x: x[:2]):
            if any(lo_ <= y and hi_ >= x for _, x, y in aca): continue
            if any(lo_ <= y + G and hi_ >= x - G for _, x, y in previas): continue
            aca.append((m, lo_, hi_))
        marcas += aca
    return marcas


def _cuantiles_enteros(x, qs) -> tuple:
    return tuple(sorted({max(1, int(np.ceil(v))) for v in np.quantile(x, qs)})) if len(x) else (1,)


def _cuantiles(x, qs) -> tuple:
    return tuple(sorted({round(float(v), 4) for v in np.quantile(x, qs)})) if len(x) else ()


def preparar(ctx: dict, zonas: dict) -> list:
    """Por segmento: slice de velas, ATR y zonas de cada fuente en índices del slice."""
    t, seg = ctx["t"], ctx["seg"]; out = []
    for s in pd.unique(seg):
        i = np.flatnonzero(seg == s); a, b = i[0], i[-1] + 1
        tt = t[a:b]
        out.append(dict(a=a, t=tt, atr=atr(ctx["h"][a:b], ctx["l"][a:b], ctx["c"][a:b]), Z={k: indexar(v, tt) for k, v in zonas.items()}))
    return out


def _concat(S, f1, f2) -> tuple:
    Za, Zb = S["Z"][f1], S["Z"][f2]
    zi = np.r_[Za["zi"], Zb["zi"]]; o = np.argsort(zi, kind="stable")
    cat = lambda k: np.r_[Za[k], Zb[k]][o]
    return zi[o].astype(np.int64), cat("zlo").astype(float), cat("zhi").astype(float), cat("zfin").astype(np.int64), np.r_[np.zeros(len(Za["zi"]), np.int64), np.ones(len(Zb["zi"]), np.int64)][o]


def cortes_par(segs: list, f1: str, f2: str) -> dict:
    """Cortes target-free del par. Para cada nacimiento de f1, la zona de f2 viva más cercana da edad (ventana) y altura conjunta (rango)."""
    edad, span, amp, ca, cb, pares = [], [], [], [], [], []
    for S in segs:
        Q = _concat(S, f1, f2); zi, lo, hi, zf, src = Q; t, a_t = S["t"], S["atr"]
        v = a_t[zi] > 0; amp.append((hi - lo)[v] / a_t[zi][v])
        ib = np.flatnonzero(src == 1)
        for z in np.flatnonzero(src == 0):
            m = zi[z]
            if not a_t[m] > 0: continue
            b = ib[(zi[ib] <= m) & (zf[ib] > m) & (t[m] - t[zi[ib]] <= AX.VIDA_MIN * 60)]
            if not len(b): continue
            c = (lo[z] + hi[z]) / 2; y = b[np.argmin(np.abs((lo[b] + hi[b]) / 2 - c))]
            edad.append((t[m] - t[zi[y]]) / 60); span.append((max(hi[z], hi[y]) - min(lo[z], lo[y])) / a_t[m]); pares.append((S, Q, m, c))
    R, V, Am = _cuantiles(span, Q_RANGO), _cuantiles(edad, Q_VENTANA), _cuantiles(np.concatenate(amp) if amp else [], Q_AMPLITUD)
    if R and V:
        rm, vm = float(np.median(span)), float(np.median(edad))
        for S, (zi, lo, hi, zf, src), m, c in pares:                     # zonas por fuente dentro de la banda mediana
            w = rm * S["atr"][m] / 2; v = (zi <= m) & (zf > m) & (S["t"][m] - S["t"][zi] <= vm * 60) & (lo >= c - w) & (hi <= c + w)
            ca.append(int((v & (src == 0)).sum())); cb.append(int((v & (src == 1)).sum()))
    return dict(A=_cuantiles_enteros(ca, Q_CANT), B=_cuantiles_enteros(cb, Q_CANT), R=R, V=V, Am=Am, n_pares=len(pares))


def censar_par(ctx: dict, segs: list, f1: str, f2: str, cortes: dict | None = None) -> dict:
    C = cortes or cortes_par(segs, f1, f2); ses = ctx["ses"]
    datos = [(S, _concat(S, f1, f2)) for S in segs]
    filas, vistos = [], set()
    for A, B, R, V, Am in product(C["A"], C["B"], C["R"], C["V"], C["Am"]):
        ms, h = [], hashlib.sha1(); dh = 0; n = 0
        for S, (zi, lo, hi, zf, src) in datos:
            m, l_, h_ = _areas_nb(zi, lo, hi, zf, src, S["t"].astype(float), S["atr"], A, B, R, V, Am, G_PTS, AX.VIDA_MIN * 60.0)
            ms.append(ses[m + S["a"]]); n += len(m); dh += int((h_ <= l_).sum())
            h.update((m + S["a"]).tobytes()); h.update(np.round(l_, 6).tobytes()); h.update(np.round(h_, 6).tobytes())
        s = np.concatenate(ms) if ms else np.zeros(0, np.int64)
        u, cn = np.unique(s, return_counts=True)
        deg = n == 0 or dh == n or cn.max() / n >= CONC_DEGENERADA
        dup = n > 0 and h.digest() in vistos; vistos.add(h.digest())
        filas.append(dict(A=A, B=B, R=R, V=V, Am=Am, areas=n, sesiones=len(u), degenerada=bool(deg), duplicada=bool(dup)))
    if not filas:
        return dict(par=[f1, f2], cortes=C, combinaciones=0, evaluables=0, degeneradas=0, duplicadas=0, evaluables_unicas=0, detalle=[])
    F = pd.DataFrame(filas); ev = (F.areas >= MIN_AREAS) & (F.sesiones >= MIN_SESIONES)
    return dict(par=[f1, f2], cortes=C, combinaciones=len(F), evaluables=int(ev.sum()), degeneradas=int(F.degenerada.sum()),
                duplicadas=int(F.duplicada.sum()), evaluables_unicas=int((ev & ~F.duplicada & ~F.degenerada).sum()), detalle=F.to_dict("records"))


def censar(ctx: dict, zonas: dict) -> list:
    segs = preparar(ctx, zonas)
    return [censar_par(ctx, segs, a, b) for a, b in combinations(FUENTES, 2) if a in zonas and b in zonas]
