"""PRERANGE-HFT (2026-10-30): barrido del rango 08:12-09:12 NY con confluencia de zonas HFT. Spec:
`docs/research/prerange_hft_20261030/SPEC_PRERANGE_HFT.md`.

Disparo: el rango sale de la ventana `[08:12,09:12)` (hora de APERTURA de la vela, como `sessions.ym_prerange_matrices`) y se busca el
barrido en `[09:12,16:00)`, incluido 09:12-09:29, que OTR-930 excluye. No hay fade en el extremo: la entrada exige retorno confirmado
(reingreso o giro del 25 %) o, para continuar, cierre afuera. Niveles, offset DST y `niveles_lote` se reutilizan de `otr_930_sweep`.

Confluencia: port de `tools/ipc_nivel_hft.py`, S = Σ 1/(1 + dist/2) con dist en ticks (0 dentro) sobre zonas a <= 20 t, activas <= 500
velas y con desgaste por volumen (35/100/500). La distancia se escala por ATR (`ATR_REF_TICKS / ATR14 en ticks`, as-of k): 20 t
significan lo mismo en ES, NQ y YM. Diferencia con el original: velas M1, no 25 ticks; el vol/tick del desgaste es el de la vela M1.

Zonas sólo reales (almacén `ZONAS_<FUENTE>_<INST>`). Sin `sensor`/`SENSOR` ni `ctx["zonas"]` (preflight y tests) se usan zonas sintéticas
regulares que prueban la mecánica; con sensor, faltar el almacén falla: nunca cae a otra fuente ni a lo sintético.
"""
from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

from edgelab import sessions as SS
from edgelab.research import otr_930_sweep as OTR
from edgelab.research.grilla_generica import Variable
from edgelab.research.otr_930_sweep import _offset_ny_seg_nb, njit

NOMBRE = "PRERANGE-HFT"
INDICADORES = ["HFTZones2", "HFTZonesNQ"]
FUENTES_ZONAS = ("HFT2", "HFTNQ")
UMBRALES = (35.0, 100.0, 500.0)                 # desgaste: contratos por tick de zona (botones del visor)
GATILLOS = ("REINGRESO_CIERRE", "EXCURSION_U1_25", "CIERRE_FUERA")
MAXD, VIDA, ATR_REF_TICKS, DIST_SIN_ZONA = 20.0, 500, 10.0, 1e6
MIN_VELAS_RANGO, MIN_ALTO_TICKS = 50, 4          # 50 de 60 M1: en YM un minuto sin operaciones no invalida el día
_h = lambda s: int(s[:2]) * 60 + int(s[3:])
INI_RANGO, FIN_RANGO, FIN_BUSQUEDA = _h(SS.YM_PRERANGE_START), _h(SS.YM_PRERANGE_END), 16 * 60

VARIABLES = [
    Variable("fuente_zonas", "fue", "grupo", categoria=len(FUENTES_ZONAS)),
    Variable("desgaste", "des", "grupo", categoria=len(UMBRALES)),
    Variable("gatillo", "gat", "grupo", categoria=len(GATILLOS)),
    Variable("hay_zona", "hay", "eq_any", categoria=2),                     # nivel 2 = cualquiera: el control SIN S
    Variable("confluencia_S", "S", "extremos", cuantiles=3),                # terciles E0 (baja, alta, cualquiera)
    Variable("dist_barrido", "d_bar", "le", cuantiles=3),                   # distancia máxima extremo-zona, escalada (el último nivel admite todo)
]
EJES_ORDINALES = (4, 5)
MODOS_DIR = OTR.MODOS_DIR
EJECUCIONES = [(md, ent, tp, sl) for md in MODOS_DIR for ent in OTR.ENTRADAS for tp in ("OPUESTO_100", "MID_50") for sl in OTR.STOPS]
BASE = {"fuente_zonas": 0, "desgaste": 1, "gatillo": 0, "hay_zona": 2, "confluencia_S": 2, "dist_barrido": 2,
        "ejecución": EJECUCIONES.index(("RETORNO", "CIERRE", "OPUESTO_100", "S_SWEEP"))}
_COLS = ["k", "gat", "lado", "lo_rng", "hi_rng", "H_rng", "E_exc", "exc_rel", "atr"]


@njit(cache=False)
def _disparos_nb(t, o, h, l, c, ses, tick, ini, fin, fin_b, min_velas, min_alto):
    n = len(c); cap = max(n // 4, 256)
    K = np.empty(cap, np.int64); G = np.empty(cap, np.int64); LA = np.empty(cap, np.int64)
    F = np.empty((cap, 6), np.float64); cnt = 0
    atr = max(h[0] - l[0], tick); i = 0
    while i < n:
        s_ini = i
        while i < n and ses[i] == ses[s_ini]: i += 1
        lo_r, hi_r, velas = 1e18, -1e18, 0
        act = np.zeros(2, np.int64); ext = np.zeros(2); ini_sw = np.zeros(2, np.int64); hecho = np.zeros((3, 2), np.int64)
        for k in range(s_ini, i):
            if k > 0:
                pc = c[k - 1]; tr = max(h[k] - l[k], abs(h[k] - pc), abs(l[k] - pc))
                atr = 0.9285714 * atr + 0.0714286 * max(tr, tick)
            t0 = int(t[k]) - 60                                       # `t` es el CIERRE de la vela; la ventana se mide por su apertura
            m = ((t0 + _offset_ny_seg_nb(t0)) % 86400) // 60
            if ini <= m < fin:
                lo_r = min(lo_r, l[k]); hi_r = max(hi_r, h[k]); velas += 1
                continue
            if not (fin <= m < fin_b) or velas < min_velas: continue
            H = hi_r - lo_r
            if H < min_alto * tick: continue
            for li in range(2):
                lado = 1 if li == 1 else -1
                if act[li] == 2: continue
                exc = (h[k] - hi_r) if lado == 1 else (lo_r - l[k])
                if exc >= tick:
                    if act[li] == 0:
                        act[li] = 1; ext[li] = h[k] if lado == 1 else l[k]; ini_sw[li] = k
                    elif lado == 1: ext[li] = max(ext[li], h[k])
                    else: ext[li] = min(ext[li], l[k])
                if act[li] == 0: continue
                E = ext[li]; A = (E - hi_r) if lado == 1 else (lo_r - E)
                if A < tick: continue
                if (lado == 1 and l[k] <= lo_r) or (lado == -1 and h[k] >= hi_r):
                    act[li] = 2                                       # cruzó todo el rango: terminó el ciclo
                    continue
                dentro = (c[k] > lo_r + 0.20 * H and c[k] <= hi_r) if lado == 1 else (c[k] < hi_r - 0.20 * H and c[k] >= lo_r)
                g0 = (k > ini_sw[li] or A >= 2.0 * tick) and dentro
                resto = (c[k] - hi_r) if lado == 1 else (lo_r - c[k])
                g1 = A >= 0.12 * H and resto <= 0.75 * A and (c[k] > lo_r + 0.25 * H if lado == 1 else c[k] < hi_r - 0.25 * H)
                g2 = exc >= tick and resto > 0.0
                for g in range(3):
                    if hecho[g, li] == 1 or not (g0 if g == 0 else (g1 if g == 1 else g2)): continue
                    hecho[g, li] = 1
                    if cnt < cap:
                        K[cnt] = k; G[cnt] = g; LA[cnt] = lado
                        F[cnt, 0] = lo_r; F[cnt, 1] = hi_r; F[cnt, 2] = H; F[cnt, 3] = E; F[cnt, 4] = A / H; F[cnt, 5] = atr
                        cnt += 1
    return K[:cnt], G[:cnt], LA[:cnt], F[:cnt]


@njit(cache=False)
def _desgaste_nb(zi, zlo, zhi, ht, lt, v, umbrales, vida):
    """Por tick de cada zona, la vela en que acumula cada umbral (vol_vela / ticks_vela de las velas que lo cruzan, posteriores a la
    de la zona, dentro de su vida); -1 = no murió. `off[z]` ubica el primer tick de la zona z."""
    nz = len(zi); off = np.zeros(nz + 1, np.int64)
    for z in range(nz): off[z + 1] = off[z] + zhi[z] - zlo[z] + 1
    muerte = np.full((off[nz], len(umbrales)), -1, np.int64); n = len(ht)
    for z in range(nz):
        for lv in range(zhi[z] - zlo[z] + 1):
            p = zlo[z] + lv; acc = 0.0
            for j in range(zi[z] + 1, min(zi[z] + vida + 1, n)):
                if lt[j] <= p <= ht[j]:
                    acc += max(1.0, v[j] / (ht[j] - lt[j] + 1.0))
                    for u in range(len(umbrales)):
                        if muerte[off[z] + lv, u] < 0 and acc >= umbrales[u]: muerte[off[z] + lv, u] = j
    return off, muerte


@njit(cache=False)
def _confluencia_nb(kk, ref, ext, esc, zi, zlo, off, muerte, u, vida, maxd, sin_zona):
    """(S, distancia mínima del extremo barrido a una zona viva), ambas con distancia escalada. `zi` ordenado."""
    m = len(kk); S = np.zeros(m); D = np.full(m, sin_zona)
    for d in range(m):
        k = kk[d]; a = np.searchsorted(zi, k - vida, side="left"); b = np.searchsorted(zi, k, side="right")
        for z in range(a, b):
            lo, hi = 1 << 60, -(1 << 60)
            for q in range(off[z], off[z + 1]):
                if muerte[q, u] < 0 or muerte[q, u] > k:
                    p = zlo[z] + (q - off[z]); lo = min(lo, p); hi = max(hi, p)
            if hi < lo: continue
            x = lo - ref[d] if ref[d] < lo else (ref[d] - hi if ref[d] > hi else 0.0)
            x *= esc[d]
            if x <= maxd: S[d] += 1.0 / (1.0 + x / 2.0)
            y = lo - ext[d] if ext[d] < lo else (ext[d] - hi if ext[d] > hi else 0.0)
            D[d] = min(D[d], y * esc[d])
    return S, D


def _serie(bloques, tick):
    from edgelab.bridge.ticks import TickSeries
    bl = list(bloques)
    if not bl: return None
    cat = lambda c: np.concatenate([b[c].to_numpy() for b in bl])
    ts, px, vol = cat("ts_ns"), cat("px"), cat("vol")
    return TickSeries(ts_ns=ts, price_ticks=np.round(px / tick).astype(np.int64), volume=vol.astype(np.int64), bid_ticks=None, ask_ticks=None,
                      sequence=np.arange(len(ts), dtype=np.int64), tick_size=tick)


def zonas_hft2(bloques, tick, spec=25):
    """HFTZones2 adaptativo. Disponible en ZONE_CREATED (el tick que FINALIZA la racha), no en `created_ms`, que es anterior."""
    from edgelab.bridge import bars as B
    from edgelab.bridge.indicators import hftzones2 as H2
    tk = _serie(bloques, tick)
    if tk is None: return pd.DataFrame(columns=["t_ns", "lo", "hi"])
    r = H2.run(tk, B.build_tick_bars(tk, spec))
    alta = {e["zone_id"]: int(e["ts_ns"]) for e in r["events"] if e["type"] == "ZONE_CREATED"}
    return pd.DataFrame([dict(t_ns=alta[z["id"]], lo=float(z["bottom"]), hi=float(z["top"])) for z in r["zones"]], columns=["t_ns", "lo", "hi"])


def zonas_hftnq(bloques, tick, spec=1):
    """HFTZonesNQ con los umbrales CERTIFICADOS (`ACCEPT_DEFAULTS`), por sesión. Disponible en `ts_avail`."""
    from edgelab.bridge import bars as B
    from edgelab.bridge.indicators import hftzones_nq as HN
    tk = _serie(bloques, tick)
    if tk is None: return pd.DataFrame(columns=["t_ns", "lo", "hi"])
    ts, pt, vo = np.asarray(tk.ts_ns), np.asarray(tk.price_ticks), np.asarray(tk.volume)
    ses = B.session_ids(ts); cortes = np.r_[0, np.flatnonzero(np.diff(ses)) + 1, len(ts)]; filas = []; prev = None
    for a, b in zip(cortes[:-1], cortes[1:]):
        c = HN.detect_candidates(ts[a:b].tolist(), pt[a:b].tolist(), vo[a:b].tolist(), prev_session_close_ticks=prev)
        filas += [(int(z["ts_avail"]), z["lower"], z["upper"]) for z in HN.accept_all(c, tick_size=tick)[0]]
        prev = int(pt[b - 1])
    return pd.DataFrame(filas, columns=["t_ns", "lo", "hi"])


_GENERADORES = {"HFT2": zonas_hft2, "HFTNQ": zonas_hftnq}


def cargar(fuente: str, inst: str, entrada: str | None = None) -> pd.DataFrame:
    entrada = entrada or os.environ.get("ENTRADA", "/kaggle/input")
    f = glob.glob(f"{entrada}/**/ZONAS_{fuente}_{inst}.parquet", recursive=True)
    if f: return pd.read_parquet(f[0])[["t_ns", "lo", "hi"]]
    if os.environ.get("SELLADO") != "1": raise FileNotFoundError(f"sin almacén de zonas {fuente}/{inst} en {entrada}")
    from edgelab.research import fuentes_ticks as F                       # holdout: las mismas funciones sobre los ticks sellados
    r = glob.glob(f"{entrada}/**/{inst}_*ticks.parquet", recursive=True)
    if not r: raise FileNotFoundError(f"sin ticks sellados de {inst} en {entrada}")
    tick = F.TICK_FUTURO[inst]; hasta = int(os.environ.get("HASTA", 20991231))
    return _GENERADORES[fuente](F.bloques_nq_sellado(F.HOLDOUT_PRIMERA_SESION_INT, hasta, r[0], os.path.abspath("ACTA_HOLDOUT.json"), tick), tick)


def _zonas_control(ctx, fuente):
    """SOLO preflight y tests: una zona de 2 ticks cada 15/22 velas sobre el cierre. Sin relación con ninguna zona real."""
    paso = 15 if fuente == FUENTES_ZONAS[0] else 22
    k = np.arange(paso, len(ctx["c"]), paso); px = ctx["c"][k]; tick = ctx["tick"]
    return pd.DataFrame(dict(t_ns=ctx["t"][k].astype(np.int64) * 10**9, lo=px, hi=px + tick))


def _zonas_de(ctx, fuente):
    if "zonas" in ctx: return ctx["zonas"][fuente]
    sensor = ctx.get("sensor") or os.environ.get("SENSOR")
    return cargar(fuente, sensor) if sensor else _zonas_control(ctx, fuente)


def indices_zonas(Z, t_close, tick):
    """(zi, lo, hi en ticks) ordenados: zi = primera vela M1 que cierra en o después de la disponibilidad; lo que aún no cerró queda afuera."""
    t_close = np.asarray(t_close, np.int64); vacio = np.zeros(0, np.int64)
    if not len(Z) or not len(t_close): return vacio, vacio, vacio
    ts = np.ceil(Z.t_ns.to_numpy(np.int64) / 1e9).astype(np.int64)
    zi = np.searchsorted(t_close, ts, side="left"); ok = zi < len(t_close)
    a, b = Z.lo.to_numpy(float)[ok], Z.hi.to_numpy(float)[ok]
    lo, hi = np.round(np.minimum(a, b) / tick).astype(np.int64), np.round(np.maximum(a, b) / tick).astype(np.int64)
    zi = zi[ok].astype(np.int64); o = np.argsort(zi, kind="stable")
    return zi[o], lo[o], hi[o]


def disparos(ctx: dict) -> pd.DataFrame:
    """Una fila por disparo × fuente × desgaste: S y distancia varían con ambas perillas, el disparo no."""
    t, c, tick = np.asarray(ctx["t"], np.int64), np.asarray(ctx["c"], float), float(ctx["tick"])
    h, l, v = np.asarray(ctx["h"], float), np.asarray(ctx["l"], float), np.asarray(ctx["v"], float)
    K, G, LA, F = _disparos_nb(t, np.asarray(ctx["o"], float), h, l, c, np.asarray(ctx["ses"], np.int64), tick, INI_RANGO, FIN_RANGO, FIN_BUSQUEDA,
                               MIN_VELAS_RANGO, MIN_ALTO_TICKS)
    B = pd.DataFrame(dict(k=K, gat=G, lado=LA, lo_rng=F[:, 0], hi_rng=F[:, 1], H_rng=F[:, 2], E_exc=F[:, 3], exc_rel=F[:, 4], atr=F[:, 5]))
    if not len(B): return pd.DataFrame(columns=_COLS + ["fue", "des", "hay", "S", "d_bar"])
    borde = np.where(LA == 1, F[:, 1], F[:, 0]) / tick
    ext = F[:, 3] / tick; esc = ATR_REF_TICKS / (F[:, 5] / tick); ht, lt = np.round(h / tick), np.round(l / tick)
    umb = np.asarray(UMBRALES); out = []
    for fi, fuente in enumerate(FUENTES_ZONAS):
        zi, zlo, zhi = indices_zonas(_zonas_de(ctx, fuente), t, tick)
        off, muerte = _desgaste_nb(zi, zlo, zhi, ht, lt, v, umb, VIDA)
        for u in range(len(umb)):
            S, D = _confluencia_nb(K, borde, ext, esc, zi, zlo, off, muerte, u, VIDA, MAXD, DIST_SIN_ZONA)
            out.append(B.assign(fue=fi, des=u, S=S, d_bar=D, hay=(S > 0).astype(np.int64)))
    return pd.concat(out, ignore_index=True).sort_values(["k", "gat", "lado", "fue", "des"], kind="stable").reset_index(drop=True)


def _retorno_invalido(gat, ej):
    return ej[0] == "RETORNO" and gat == GATILLOS.index("CIERRE_FUERA")      # retornar desde un cierre afuera sería el fade en el extremo


def niveles(fila: dict, ej: tuple, ctx: dict):
    return None if _retorno_invalido(int(fila["gat"]), ej) else OTR.niveles(fila, ej, ctx)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    X = OTR.niveles_lote(D, ej, ctx)
    if ej[0] == "RETORNO": X[D["gat"].to_numpy() == GATILLOS.index("CIERRE_FUERA"), 0] = np.nan
    return X


def diagnostico_e0(D: pd.DataFrame, cortes=None) -> dict:
    """Target-free: degeneración de S por fuente y desgaste y celdas con >= 30 disparos por ejecución. `DEGENERADA` = casi todo S>0 o S=0."""
    from edgelab.research import grilla_generica as GG, grilla_masiva as GM
    filas = {}
    for (f, u), X in D.groupby(["fue", "des"]):
        p = float((X.S > 0).mean()); pos = X.S[X.S > 0]
        filas[f"{FUENTES_ZONAS[int(f)]}/{UMBRALES[int(u)]:g}"] = dict(
            disparos=int(len(X)), frac_S_pos=round(p, 4), S_q=[round(float(x), 3) for x in pos.quantile([.25, .5, .75])] if len(pos) else [],
            d_bar_mediana=round(float(X.d_bar[X.d_bar < DIST_SIN_ZONA].median()), 2) if (X.d_bar < DIST_SIN_ZONA).any() else None,
            veredicto="DEGENERADA_CASI_TODO_S_POS" if p >= 0.95 else "DEGENERADA_CASI_TODO_S_0" if p <= 0.05 else "OK")
    cortes = cortes or GG.cortes_e0(D, VARIABLES)
    P = [GM.Perilla(v.nombre, v.niveles(cortes.get(v.nombre) if v.cuantiles else None), v.modo) for v in VARIABLES]
    C = GM.tensor(P, GG.discretizar(D, VARIABLES, cortes), np.ones(len(D)))[2]
    return dict(por_fuente=filas, cortes=cortes, celdas_sin_ejecucion=int(C.size), con_30_disparos=int((C >= 30).sum()))
