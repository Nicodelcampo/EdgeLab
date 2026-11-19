r"""Picos robustos (diseño de Nico, 2026-11-19) — puntaje de pares de picos y de grupos, para M1. Target-free y causal.

Geometría de un par de techos consecutivos (los pisos son el espejo; se trabaja en espacio «techo» con x = −low):

            P1 ·─── d ───· P2               d   = |P1 − P2|                   (cercanía entre picos)
           /    \       /   \               C   = (P1 + P2)/2 − V             (excursión de la pierna central)
       L1 /      \  C  /     \ L2           L1  = pierna de confirmación izquierda (cuánto subió el precio hasta P1)
         /        \   /       \             L2  = pierna de confirmación derecha (cuánto se alejó después de P2)
        T0         · V         T2           A   = ATR(30) M1 causal en la vela que confirma P2 (unidad de medida)

Factores, todos en [0, 1]:
- fL (validez por piernas): Lp = min(L1, L2)/A (o media geométrica). Piernas cortas → casi sin valor.
- fC (central contra piernas): ρ = C / media(L1, L2). Central corta respecto de las piernas → poca importancia.
- fK (cercanía relativa): δ = d / C. Más cerca → más fuerte, y la misma distancia pesa menos cuanto más se alejó el
  precio entre los dos picos (por eso se divide por C).
- fS (tamaño de la central): C/A. La cercanía vale más cuanto mayor fue la excursión.
Puntaje del par S = 100 · combinación(fL, fC, fK, fS) (producto, suma ponderada o compuertas, según la variante).

Pareo: siempre el pico con el SIGUIENTE del mismo lado (P_k con P_k+1), nunca hacia atrás.

Grupo: picos consecutivos del mismo lado encadenados mientras cada par nuevo tiene δ ≤ δ_link y el pico nuevo queda a
≤ δ_link·C del nivel del grupo. Valor del grupo = percentil de su valor bruto (cantidad efectiva y tamaño) contra los
grupos TERMINADOS antes, en una ventana móvil de sesiones: compara su tamaño y su cantidad con los otros.

Causalidad: un swing se conoce en `cf` (vela en que el precio se alejó R = r·A del extremo). El par se emite en la
confirmación de P2 con `Sc` (L2 medida hasta ahí). `Sf` usa la L2 completa: sirve para mirar en el visor, NO para
operar en `cf`. Los percentiles de grupo usan sólo grupos terminados antes. Nada usa retornos ni P&L.
"""
from __future__ import annotations

import math

import numpy as np
from numba import njit

from edgelab.bridge.indicators.espejo_impulsos import atr_prev  # ATR(n) simple cerrado en la vela anterior (causal)

GAP_SESION_S = 1800        # hueco > 30 min = sesión nueva (pausa CME diaria y fines de semana)
TOPE_PIERNA = 600          # velas máximas para buscar el origen/fin de una pierna «por nivel»

BASE = dict(r=1.0, n_atr=30, min_ticks=4, piernas="swing", agg="min", l0=3.0, rho0=0.5, delta0=0.15, c0=4.0,
            comb="mult", gate_L=2.0, gate_rho=0.5, gate_delta=0.25, delta_link=0.35, grupo="mixto",
            escalas=None, a_fijo=False, ventana_sesiones=20)

VARIANTES = {
    "A_MULT":   dict(desc="Base: piernas = swing anterior/siguiente del zigzag; producto de los 4 factores."),
    "B_NIVEL":  dict(piernas="nivel", desc="Como A, pero cada pierna se mide hasta la última vez que el precio estuvo en el nivel del pico (piernas largas reales, no el último retroceso)."),
    "C_SUMA":   dict(piernas="nivel", comb="suma", desc="Como B, con suma ponderada de los factores (fL 0,25, fC 0,25, fK 0,30, fS 0,20): un factor flojo resta pero no anula."),
    "D_UMBRAL": dict(piernas="nivel", comb="umbral", desc="Compuertas duras (piernas ≥ 2 A, ρ ≥ 0,5, δ ≤ 0,25); el puntaje sólo mide cercanía × tamaño."),
    "E_MULTI":  dict(piernas="nivel", escalas=(1.0, 2.0, 4.0), desc="Como B en tres escalas de zigzag (1, 2 y 4 A): aparecen dobles techos que en escala chica tienen un pico intermedio."),
    "F_FIJO":   dict(piernas="nivel", a_fijo=True, desc="Como B, pero la unidad A es fija por sesión (mediana del ATR de las 20 sesiones anteriores): prueba si normalizar intradía ayuda."),
}


def config(variante: str) -> dict:
    cfg = dict(BASE); cfg.update({k: v for k, v in VARIANTES[variante].items() if k != "desc"}); return cfg


def sesiones(t: np.ndarray) -> np.ndarray:
    return np.r_[0, np.cumsum(np.diff(t) > GAP_SESION_S)].astype(np.int64)


def unidad(h, l, c, ses, cfg) -> np.ndarray:
    """A por vela (causal). `a_fijo`: mediana de A en las `ventana_sesiones` sesiones anteriores, constante en la sesión."""
    a = atr_prev(h, l, c, int(cfg["n_atr"]))
    if not cfg["a_fijo"]:
        return a
    out = np.full(len(a), np.inf); ini = np.flatnonzero(np.r_[True, ses[1:] != ses[:-1]]); fin = np.r_[ini[1:], len(a)]
    meds = [float(np.median(a[i:j][np.isfinite(a[i:j])])) if np.isfinite(a[i:j]).any() else np.inf for i, j in zip(ini, fin)]
    W = int(cfg["ventana_sesiones"])
    for s, (i, j) in enumerate(zip(ini, fin)):
        prev = [m for m in meds[max(0, s - W):s] if np.isfinite(m)]
        if len(prev) >= 3: out[i:j] = float(np.median(prev))
    return out


@njit(cache=True)
def zigzag_alterno(h, l, ses, R):
    """Swings alternados (H/L) con umbral variable R[j] (precio). Devuelve (i_ext, tipo ±1, precio, i_conf).
    Un techo se confirma en la primera vela j con ext − l[j] ≥ R[j]; un piso, con h[j] − ext ≥ R[j]. Se reinicia por sesión;
    el primer extremo de la sesión no se emite hasta que el precio recorre R en alguna dirección (sin pierna previa)."""
    n = len(h); I = []; K = []; P = []; C = []
    j0 = 0
    while j0 < n:
        j1 = j0
        while j1 + 1 < n and ses[j1 + 1] == ses[j0]: j1 += 1
        d = 0; hi = h[j0]; hii = j0; lo = l[j0]; loi = j0; ext = 0.0; ei = j0
        for j in range(j0 + 1, j1 + 1):
            r = R[j]
            if not np.isfinite(r): continue
            if d == 0:
                if h[j] > hi: hi = h[j]; hii = j
                if l[j] < lo: lo = l[j]; loi = j
                if hi - l[j] >= r and hii < j:
                    d = -1; I.append(hii); K.append(1); P.append(hi); C.append(j); ext = l[j]; ei = j
                elif h[j] - lo >= r and loi < j:
                    d = 1; I.append(loi); K.append(-1); P.append(lo); C.append(j); ext = h[j]; ei = j
                continue
            if d == 1:
                if h[j] > ext: ext = h[j]; ei = j
                elif ext - l[j] >= r:
                    I.append(ei); K.append(1); P.append(ext); C.append(j); d = -1; ext = l[j]; ei = j
            else:
                if l[j] < ext: ext = l[j]; ei = j
                elif h[j] - ext >= r:
                    I.append(ei); K.append(-1); P.append(ext); C.append(j); d = 1; ext = h[j]; ei = j
        j0 = j1 + 1
    return np.array(I, np.int64), np.array(K, np.int64), np.array(P, np.float64), np.array(C, np.int64)


def _sat(x, s):
    return 1.0 - math.exp(-max(x, 0.0) / s)


def _pierna_izq(x, y, ses, i, modo, i_prev_opuesto):
    """Origen de la pierna izquierda de un pico en x[i] (espacio techo). Devuelve (índice del mínimo, valor)."""
    if modo == "swing":
        return i_prev_opuesto, y[i_prev_opuesto]
    k0 = i
    while k0 - 1 >= 0 and ses[k0 - 1] == ses[i] and i - (k0 - 1) <= TOPE_PIERNA and x[k0 - 1] < x[i]: k0 -= 1
    m = k0 + int(np.argmin(y[k0:i + 1])); return m, y[m]


def _pierna_der(x, y, ses, i, hasta, modo, i_sig_opuesto):
    """Fin de la pierna derecha (mínimo de y después de i) usando sólo velas ≤ `hasta`. Devuelve (índice, valor)."""
    if modo == "swing" and i_sig_opuesto is not None and i_sig_opuesto <= hasta:
        return i_sig_opuesto, y[i_sig_opuesto]
    k1 = i
    while k1 + 1 <= hasta and ses[k1 + 1] == ses[i] and (k1 + 1) - i <= TOPE_PIERNA and (modo == "swing" or x[k1 + 1] < x[i]): k1 += 1
    if k1 == i: return i, y[i]
    m = i + 1 + int(np.argmin(y[i + 1:k1 + 1])); return m, y[m]


def _puntaje(L1, L2, C, d, A, cfg):
    Lp = (min(L1, L2) if cfg["agg"] == "min" else math.sqrt(max(L1, 0) * max(L2, 0))) / A
    rho = C / max(0.5 * (L1 + L2), 1e-12); delta = d / max(C, 1e-12)
    fL, fC = _sat(Lp, cfg["l0"]), _sat(rho, cfg["rho0"])
    fK, fS = math.exp(-delta / cfg["delta0"]), _sat(C / A, cfg["c0"])
    if cfg["comb"] == "mult": s = fL * fC * fK * fS
    elif cfg["comb"] == "suma": s = 0.25 * fL + 0.25 * fC + 0.30 * fK + 0.20 * fS
    else:
        ok = Lp >= cfg["gate_L"] and rho >= cfg["gate_rho"] and delta <= cfg["gate_delta"]
        s = fK * fS if ok else 0.0
    return 100.0 * s, dict(Lp=Lp, rho=rho, delta=delta, fL=fL, fC=fC, fK=fK, fS=fS)


def pares_escala(t, h, l, ses, A, cfg, r, tick):
    """Pares de picos consecutivos de una escala de zigzag (r·A). Lista de dicts, ordenada por confirmación."""
    R = np.where(np.isfinite(A), np.maximum(r * A, cfg["min_ticks"] * tick), np.inf)
    I, K, P, Cf = zigzag_alterno(h, l, ses, R)
    out = []
    for kind in (1, -1):
        x, y = (h, l) if kind == 1 else (-l, -h)
        pos = np.flatnonzero(K == kind)
        for a_, b_ in zip(pos[:-1], pos[1:]):
            ia, ib = I[a_], I[b_]
            if ses[ia] != ses[ib] or b_ - a_ != 2 or a_ == 0 or ses[I[a_ - 1]] != ses[ia]: continue
            iv = I[a_ + 1]; cfb = int(Cf[b_]); Ab = A[cfb]
            if not np.isfinite(Ab) or Ab <= 0: continue
            pa, pb = x[ia], x[ib]
            i0, v0 = _pierna_izq(x, y, ses, ia, cfg["piernas"], I[a_ - 1])
            sig = I[b_ + 1] if b_ + 1 < len(I) and ses[I[b_ + 1]] == ses[ib] else None
            sig_cf = Cf[b_ + 1] if sig is not None else None
            i2c, v2c = _pierna_der(x, y, ses, ib, cfb, cfg["piernas"], None)
            fin = int(sig_cf) if sig_cf is not None else len(h) - 1
            i2f, v2f = _pierna_der(x, y, ses, ib, fin, cfg["piernas"], sig)
            L1, L2c, L2f = pa - v0, pb - v2c, pb - v2f
            Cc = 0.5 * (pa + pb) - y[iv]; d = abs(pa - pb)
            Sc, fc = _puntaje(L1, L2c, Cc, d, Ab, cfg)
            Sf, ff = _puntaje(L1, L2f, Cc, d, Ab, cfg)
            sg = 1 if kind == 1 else -1
            out.append(dict(k="H" if kind == 1 else "L", ia=int(ia), ib=int(ib), iv=int(iv), i0=int(i0), i2=int(i2f), cf=cfb,
                            pa=sg * pa, pb=sg * pb, pv=sg * y[iv], p0=sg * v0, p2=sg * v2f, A=float(Ab), r=r,
                            L1=L1 / Ab, L2c=L2c / Ab, L2f=L2f / Ab, C=Cc / Ab, d=d / Ab,
                            Sc=Sc, Sf=Sf, fc=fc, ff=ff))
    out.sort(key=lambda p: (p["cf"], p["ib"]))
    return out


def _bruto(g, cfg):
    S = np.array(g["S"]) / 100.0; size = float(np.median(g["C"])); n_eff = 1.0 + float(S.sum())
    if cfg["grupo"] == "conteo": return n_eff
    if cfg["grupo"] == "tamano": return size * float(S.mean())
    return n_eff * math.log1p(size)


def grupos(pares, ses, cfg, clave="Sc"):
    """Encadena pares consecutivos del mismo lado. Asigna a cada par `g` (id) y `g_pct_c` (percentil causal del grupo en
    la confirmación del par, contra grupos terminados antes dentro de la ventana de sesiones)."""
    vivos = {}; G = []; terminados = []          # terminados: (cf_fin, sesion, bruto)
    for p in pares:
        k = p["k"]; g = vivos.get(k); s_now = ses[p["cf"]]
        # cierre de grupos de sesiones anteriores
        for kk in list(vivos):
            if ses[vivos[kk]["ult_cf"]] != s_now:
                terminados.append((vivos[kk]["ult_cf"], ses[vivos[kk]["ult_cf"]], _bruto(vivos[kk], cfg))); del vivos[kk]
        g = vivos.get(k)
        link = p["fc"]["delta"] <= cfg["delta_link"]
        if g is not None and g["picos"][-1][0] == p["ia"] and link and abs(p["pb"] - g["nivel"]) <= cfg["delta_link"] * p["C"] * p["A"]:
            g["picos"].append((p["ib"], p["pb"])); g["S"].append(p[clave]); g["C"].append(p["C"]); g["pares"].append(p)
            g["nivel"] = float(np.mean([q[1] for q in g["picos"]])); g["ult_cf"] = p["cf"]
        else:
            if g is not None:
                terminados.append((g["ult_cf"], ses[g["ult_cf"]], _bruto(g, cfg))); del vivos[k]
            if not link:
                p["g"] = None; p["g_pct_c"] = None; continue
            g = dict(id=len(G), k=k, picos=[(p["ia"], p["pa"]), (p["ib"], p["pb"])], S=[p[clave]], C=[p["C"]], pares=[p],
                     nivel=0.5 * (p["pa"] + p["pb"]), ult_cf=p["cf"]); G.append(g); vivos[k] = g
        ref = [b for (_, s, b) in terminados if s_now - cfg["ventana_sesiones"] <= s < s_now or (s == s_now)]
        bru = _bruto(g, cfg); p["g"] = g["id"]
        p["g_pct_c"] = (100.0 * float(np.mean(np.array(ref) < bru))) if len(ref) >= 30 else None
        g["pct"] = p["g_pct_c"]; g["bruto"] = bru
    return G


def calcular(t, h, l, c, cfg, tick):
    t = np.asarray(t, np.int64); h = np.asarray(h, float); l = np.asarray(l, float); c = np.asarray(c, float)
    ses = sesiones(t); A = unidad(h, l, c, ses, cfg)
    esc = cfg["escalas"] or (cfg["r"],)
    pares = []
    for r in esc:
        pares += pares_escala(t, h, l, ses, A, cfg, r, tick)
    if len(esc) > 1:              # el mismo P2 en varias escalas: queda la escala mayor (la estructura más grande)
        best = {}
        for p in pares:
            key = (p["k"], p["ib"])
            if key not in best or p["r"] > best[key]["r"]: best[key] = p
        pares = sorted(best.values(), key=lambda p: (p["cf"], p["ib"]))
    G = grupos(pares, ses, cfg)
    return pares, G
