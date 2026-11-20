"""FILTRO-PICOS (2026-11-18, idea de Nico): capa de ENTRADA sobre gatillos de otras reglas. En vez de entrar al dispararse la regla, se
espera que se formen picos «blandos» en contra (pivotes de 1 vela) y se confirma la entrada cuando el precio vuelve x·D a favor (A,
«picos») o cuando primero barre el último pico y después vuelve x·D (B, «barrido»). No se entra si el precio llega al objetivo original,
si se aleja 1·D en contra del precio del gatillo o si vence la espera. Pre-registro: docs/research/filtro_picos_20261118/PREREGISTRO.md.

Gatillos (bases), todos causales y en unidades relativas (K36):
  LUX   marca de impulso LUX-IMB (D3_20, amplitud ≥ p60, ≥ 1 zona en el 25 % inicial); fade hacia A; stop 0,5·D; objetivo A
  IBV0  Madonna del IB (`ib_madonna` V0, su stop y objetivo)       IBV3  aceptación → continuación (`ib_madonna` V3)
  ESC   escalera plana (`escalonadas_m1`, ESC); stop 4·rg, objetivo 8·rg
  AZAR  gatillo al azar (hash del minuto, ≈ 1 cada 500 velas, lado por hash); stop 2·rango medio de la vela, objetivo 2× el stop
Configuraciones: {A, B} × espera {15, 60} velas × picos mínimos {1, 2} + placebo por espera (entra a las espera/4 velas con las mismas
cancelaciones, sin condición de picos) + INM (la entrada inmediata de la regla base). x_conf = 0,25·D0; cancelación en contra = 1·D0
(D0 = |cierre del gatillo − stop original|).
Cada fila = (gatillo, configuración) que entra; columnas booleanas «<BASE>__<CONF>»; `trig` identifica el gatillo para la comparación
pareada (un gatillo que no entra vale 0). Ejecuciones: stop original y stop detrás del pico/barrido (− 0,1·D0).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from numba import njit
except ImportError:                                     # sin numba: misma lógica (lento)
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "FILTRO-PICOS"
BASES = ("LUX", "IBV0", "IBV3", "ESC", "AZAR")
CONFIGS = [(lg, w, n) for lg in ("A", "B") for w in (15, 60) for n in (1, 2)]
X_CONF, X_CANCEL, BUF_B, P_AZAR, SEMILLA = 0.25, 1.0, 0.1, 1 / 500, 20261118
EJECUCIONES = [("PRECIOS", "obj", "stop", "fin"), ("PRECIOS", "obj", "stop_b", "fin")]
DEPENDENCIAS_KERNEL = ("edgelab.research.luximb_grilla", "edgelab.research.ib_madonna", "edgelab.research.escalonadas_m1",
                       "tools.escalonadas_det", "tools.peaks_rule", "tools.peaks_learn")


def nombre_conf(cf) -> str:
    lg, w, n = cf
    return f"{lg}{w}n{n}"


CONF_NOMBRES = ["INM"] + [nombre_conf(c) for c in CONFIGS] + ["PL15", "PL60"]
DEFINICIONES = [f"{b}__{c}" for b in BASES for c in CONF_NOMBRES]


@njit(cache=False)
def _confirmar(k, lado, c0, d0, obj, h, l, c, ses, logica, espera, nmin, xc, xk, placebo):
    """Vela de confirmación (−1 = no entra) y extremo del pico/barrido (para el stop B). Recorre las velas k+1 … k+espera de la sesión."""
    n = len(c); piv = 0; ult = np.nan; barrido = False; ext = np.nan
    for j in range(k + 1, min(n, k + espera + 1)):
        if ses[j] != ses[k]: return -1, np.nan
        if (lado == 1 and h[j] >= obj) or (lado == -1 and l[j] <= obj): return -1, np.nan            # llegó al objetivo: no se busca más
        if (lado == 1 and l[j] <= c0 - xk * d0) or (lado == -1 and h[j] >= c0 + xk * d0): return -1, np.nan   # se fue x en contra
        if placebo:
            if j - k >= espera // 4: return j, (l[j] if lado == 1 else h[j])
            continue
        # pivote blando en contra confirmado en j (vela j−1 extrema contra la operación, posterior al gatillo)
        if j - 1 > k:
            if lado == 1 and l[j - 1] < l[j - 2] and l[j - 1] <= l[j]:
                piv += 1; ult = l[j - 1]; barrido = False; ext = ult
            elif lado == -1 and h[j - 1] > h[j - 2] and h[j - 1] >= h[j]:
                piv += 1; ult = h[j - 1]; barrido = False; ext = ult
        if piv < nmin: continue
        if logica == 1:                                                                               # B: primero barre el último pico
            if not barrido:
                if (lado == 1 and l[j] < ult) or (lado == -1 and h[j] > ult): barrido = True; ext = l[j] if lado == 1 else h[j]
                else: continue
            ext = min(ext, l[j]) if lado == 1 else max(ext, h[j])
        if lado * (c[j] - ext) >= xc * d0: return j, ext                                              # volvió x·D a favor
    return -1, np.nan


def _gatillos(ctx) -> pd.DataFrame:
    """(k, lado, obj, stop, fin, base) de cada regla base, con sus propias reglas causales."""
    from edgelab.research import ib_madonna as IB, escalonadas_m1 as ES, luximb_grilla as LG
    c = np.asarray(ctx["c"], float); t = np.asarray(ctx["t"]); out = []
    # LUX: marcas de impulso (≥ 1 zona en el 25 % inicial), fade hacia A
    o, h, l, seg = (np.asarray(ctx[x]) for x in ("o", "h", "l", "seg"))
    for sg in pd.unique(seg):
        idx = np.flatnonzero(seg == sg); a, b = idx[0], idx[-1] + 1
        M = LG.marcas_segmento(t[a:b], o[a:b], h[a:b], l[a:b], c[a:b], float(ctx["tick"]), amp=((60.0, 0.0),), zon=((0.25, 1),))
        if len(M):
            k = M.k.to_numpy(np.int64) + a; lado = -M.d.to_numpy(np.int64); pa = M.pa.to_numpy(float); D = np.abs(c[k] - pa)
            out.append(pd.DataFrame(dict(k=k, lado=lado, obj=pa, stop=c[k] - lado * 0.5 * D, fin=np.nan, base="LUX")))
    E = IB.eventos(ctx)
    for nm, ob, st in (("IBV0", "obj_v0", "stop_v0"), ("IBV3", "obj_v3", "stop_v3")):
        g = E.loc[E["V0" if nm == "IBV0" else "V3"].astype(bool)]           # .loc + bool: una tabla vacía (object) no se lee como columnas
        out.append(pd.DataFrame(dict(k=g.k, lado=g.lado, obj=g[ob], stop=g[st], fin=np.nan, base=nm)))
    S = ES.eventos(ctx); g = S.loc[S.ESC.astype(bool)]
    if len(g):
        kg = g.k.to_numpy(np.int64); lg_ = g.lado.to_numpy(np.int64); rg_ = g.rg.to_numpy(float)
        out.append(pd.DataFrame(dict(k=kg, lado=lg_, obj=c[kg] + lg_ * 8 * rg_, stop=c[kg] - lg_ * 4 * rg_, fin=np.nan, base="ESC")))
    # AZAR: hash del minuto; rango medio causal de la vela (el de escalonadas) para el stop
    rg_s = ES.rango_causal(ctx); ses = np.asarray(ctx["ses"])
    kk = (t.astype(np.int64) // 60).astype(np.uint64); hsh = (kk * np.uint64(2246822519) + np.uint64(SEMILLA)) % np.uint64(2 ** 32)
    sel = np.flatnonzero(hsh.astype(np.float64) / 2 ** 32 < P_AZAR); rg = rg_s.reindex(ses[sel]).to_numpy(float)
    ok = rg > 0; sel, rg = sel[ok], rg[ok]; lado = np.where((hsh[sel].astype(np.int64) >> 9) & 1, 1, -1)
    out.append(pd.DataFrame(dict(k=sel, lado=lado, obj=c[sel] + lado * 4 * rg, stop=c[sel] - lado * 2 * rg, fin=np.nan, base="AZAR")))
    out = [x for x in out if len(x)]
    if not out: return pd.DataFrame(dict(k=np.zeros(0, np.int64), lado=np.zeros(0, np.int64), obj=[], stop=[], fin=[], base=[]))
    G = pd.concat(out, ignore_index=True)
    G = G[np.isfinite(G.obj) & np.isfinite(G.stop) & (G.lado * (c[G.k.to_numpy(np.int64)] - G.stop) > 0)].reset_index(drop=True)
    return G.astype(dict(k=np.int64, lado=np.int64))


def eventos(ctx) -> pd.DataFrame:
    h, l, c = (np.asarray(ctx[x], float) for x in ("h", "l", "c")); ses = np.asarray(ctx["ses"]).astype(np.int64)
    G = _gatillos(ctx); filas = []
    if not len(G): return pd.DataFrame(columns=["k", "lado", "ref", "ext", "rg", "obj", "stop", "stop_b", "fin", "trig", "base", "conf"] + DEFINICIONES)
    k0 = G.k.to_numpy(np.int64); lado = G.lado.to_numpy(np.int64); obj = G.obj.to_numpy(float); st = G.stop.to_numpy(float)
    c0 = c[k0]; d0 = np.abs(c0 - st); trig = (G.base + ":" + G.k.astype(str) + ":" + G.lado.astype(str)).to_numpy()
    filas.append(pd.DataFrame(dict(k=k0, lado=lado, obj=obj, stop=st, stop_b=st, trig=trig, base=G.base, conf="INM")))
    planes = [(nombre_conf(cf), 0 if cf[0] == "A" else 1, cf[1], cf[2], False) for cf in CONFIGS] + [("PL15", 0, 15, 0, True), ("PL60", 0, 60, 0, True)]
    for nom, lg, w, n, pl in planes:
        kc = np.full(len(G), -1, np.int64); ex = np.full(len(G), np.nan)
        for i in range(len(G)):
            kc[i], ex[i] = _confirmar(int(k0[i]), int(lado[i]), c0[i], d0[i], obj[i], h, l, c, ses, lg, w, n, X_CONF, X_CANCEL, pl)
        m = kc >= 0
        stb = np.where(np.isfinite(ex), ex - lado * BUF_B * d0, st)
        filas.append(pd.DataFrame(dict(k=kc[m], lado=lado[m], obj=obj[m], stop=st[m], stop_b=stb[m], trig=trig[m], base=G.base.to_numpy()[m], conf=nom)))
    E = pd.concat(filas, ignore_index=True)
    k = E.k.to_numpy(np.int64)
    E = E[(E.lado * (c[k] - E.stop) > 0) & (E.lado * (E.obj - c[k]) > 0)].reset_index(drop=True)   # a la entrada el stop y el objetivo siguen del lado correcto
    E["stop_b"] = np.where(E.lado * (c[E.k.to_numpy(np.int64)] - E.stop_b) > 0, E.stop_b, E.stop)
    E["fin"] = np.nan; E["ref"] = E.obj; E["ext"] = E.stop; E["rg"] = np.abs(c[E.k.to_numpy(np.int64)] - E.stop)
    clave = E.base + "__" + E.conf
    for d in DEFINICIONES: E[d] = (clave == d).to_numpy()
    cols = ["k", "lado", "ref", "ext", "rg", "obj", "stop", "stop_b", "fin", "trig", "base", "conf"] + DEFINICIONES
    return E[cols].sort_values(["k", "trig", "conf"], kind="mergesort").reset_index(drop=True)
