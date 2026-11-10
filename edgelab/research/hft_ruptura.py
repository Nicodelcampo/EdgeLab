"""HFT-RUPTURA (2026-11-10): ¿en qué toques de un cluster HFT grande el precio lo ATRAVIESA de forma distintiva?

Indagación (EF2, exploratoria, sobre DESC ya usado) seguida de confirmación en datos no usados. Pre-registro:
`docs/research/hft_clusters_u1_20261110/PREREGISTRO_RUPTURA.md`. Parte de HFT-REBOTES: en NQ el cluster grande no se defiende
(real ≈ 50/50 mientras un nivel cualquiera de la sesión rebota +0,07), pero en términos absolutos no hay ruptura operable.

Para cada toque D0 (primer regreso tras alejarse X/2), real y de control, se guarda un vector de rasgos causales (todo medido con ticks
anteriores o iguales al toque, salvo los desenlaces) y varios desenlaces. Signo: `rompe` = +1 si la carrera ±X termina del otro lado.
Rasgos (familias):
  aproximación   segundos de los últimos X/2, excursión previa (en X), segundos afuera
  cluster        edad, ancho (en X), zonas, packing, alineación del flujo de sus zonas con la dirección de llegada, nº de visita
  sesión         minutos desde la apertura (18:00 ET), avance de la sesión a favor de la llegada (en X), distancia al extremo de la sesión (en X),
                 rango de los últimos 30 min (en X)
  toque          volumen de los 30 s anteriores al toque contra la mediana de la sesión, desequilibrio (tick rule) en la dirección
                 de llegada en esos 30 s
Desenlaces: carrera ±X, ±X/2 y ±2X (+1 = rompe), segundos hasta resolver ±X, máximo avance a favor de la ruptura en 15 min (en X).
"""
from __future__ import annotations

from statistics import NormalDist

import numpy as np
import pandas as pd

from edgelab.research import hft_rebotes as RB
from edgelab.research.hft_clusters_info import HORIZONTE_S, VIDA_CLUSTER_S, _primero, barrera

NS = 1_000_000_000
RASGOS = ["aprox_s", "excursion_x", "afuera_s", "edad_s", "ancho_x", "n_zonas", "packing", "flujo_alineado", "visita",
          "minuto_et", "tendencia_alineada", "dist_extremo_x", "rango30_x", "vol30_rel", "deseq30",
          # Enmienda (Nico, 2026-11-10, antes de ver resultados): picos, expansión de salida, volumen del cluster y pendiente de EMAs
          "picos_dentro", "picos_sin_tomar", "salida_s", "vol_banda_rel", "ema9_pend", "ema21_pend",
          # Revisión R1 (2026-11-10, antes de ver resultados): la «expansión limpia» se mide en tres partes
          "salida_eficiencia", "pasada_s"]
# Estratos fijos para rasgos discretos (con cuantiles, los empates colapsaban todo en un tercil): (corte_1, corte_2), estrato =
# (v > corte_1) + (v > corte_2). El resto usa los terciles de los reales de cada activo con la misma regla.
CORTES_FIJOS = {"picos_dentro": (0.5, 1.5), "picos_sin_tomar": (0.5, 1.5),
                "flujo_alineado": (-0.5, 0.5), "visita": (2.5, 3.5)}
W_PICO = 3                                                         # pico = pivote de 3 velas de 1 min por lado (misma definición que espejo_picos)


def _carrera(px, j0, ref, d, X, j1):
    """+1 si llega antes a +X en la dirección d, −1 si a −X, 0 si ninguna antes de j1."""
    r = px[j0 + 1:j1]; g = _primero(d * (r - ref) >= X); p = _primero(d * (r - ref) <= -X)
    if g < 0 and p < 0: return 0, -1
    return (1, g) if (p < 0 or (0 <= g < p)) else (-1, p)


def _tick_rule(px):
    s = np.sign(np.diff(px, prepend=px[0]))
    for i in range(1, len(s)):                                                  # cero → se arrastra el último signo
        if s[i] == 0: s[i] = s[i - 1]
    return s


def rasgos_evento(ts, px, vol, signo, i0, j, j_sal, ref, lado, X, ses_ini, c, n_visita, minuto_et):
    """Rasgos de un toque (índices absolutos). `lado` = +1 si el cluster hace de soporte (el precio llega desde arriba).
    La dirección de RUPTURA es −lado (sigue en la dirección de llegada)."""
    llegada = -lado; t = ts[j]
    w30 = slice(int(np.searchsorted(ts, t - 30 * NS)), j + 1)
    w1800 = slice(int(np.searchsorted(ts, t - 1800 * NS)), j + 1)
    dist = np.maximum(np.maximum(c["lo"] - px[j_sal:j + 1], px[j_sal:j + 1] - c["hi"]), 0.0)
    k = np.flatnonzero(dist >= X / 2); aprox_s = float((t - ts[j_sal + k[-1]]) / NS) if k.size else 0.0
    ses = slice(ses_ini, j + 1); p_ses = px[ses]
    vol_ses = vol[ses]; t_ses = ts[ses]
    # volumen por ventana de 30 s en lo que va de la sesión (mediana), para normalizar
    if t_ses[-1] - t_ses[0] > 60 * NS:
        cortes = np.arange(t_ses[0], t_ses[-1], 30 * NS); idx = np.searchsorted(t_ses, cortes)
        med30 = float(np.median(np.add.reduceat(vol_ses, idx))) if len(idx) > 1 else np.nan
    else: med30 = np.nan
    v30 = float(vol[w30].sum()); s30 = float((signo[w30] * vol[w30]).sum())
    extremo = float(p_ses.min() if llegada < 0 else p_ses.max())
    return dict(aprox_s=aprox_s, excursion_x=float(dist.max() / X) if dist.size else 0.0, afuera_s=float((t - ts[j_sal]) / NS),
                edad_s=float((t - c["t_ns"]) / NS), ancho_x=float((c["hi"] - c["lo"]) / X), n_zonas=float(c.get("n_zonas", np.nan)),
                packing=float(c.get("packing", np.nan)), flujo_alineado=float(np.sign(c.get("net_dir", np.nan)) * llegada), visita=float(n_visita),
                minuto_et=float(minuto_et), tendencia_alineada=float((px[j] - px[ses_ini]) / X * llegada),
                dist_extremo_x=float(abs(px[j] - extremo) / X), rango30_x=float((px[w1800].max() - px[w1800].min()) / X),
                vol30_rel=float(v30 / med30) if med30 and med30 > 0 else np.nan, deseq30=float(s30 / v30 * llegada) if v30 > 0 else 0.0)


def minutos(ts, px):
    """Velas de 1 minuto de la sesión: índice de vela por tick, primer tick de cada vela, máximos, mínimos, cierres y EMAs 9 y 21."""
    m = (ts - ts[0]) // (60 * NS); ini = np.flatnonzero(np.r_[True, m[1:] != m[:-1]])
    H = np.maximum.reduceat(px, ini); L = np.minimum.reduceat(px, ini); Cc = px[np.r_[ini[1:], len(px)] - 1]
    e9 = pd.Series(Cc).ewm(span=9, adjust=False).mean().to_numpy(); e21 = pd.Series(Cc).ewm(span=21, adjust=False).mean().to_numpy()
    vela = np.repeat(np.arange(len(ini)), np.diff(np.r_[ini, len(px)]))
    return dict(vela=vela, ini=ini, H=H, L=L, C=Cc, e9=e9, e21=e21, piv_H=pivotes(H), piv_L=pivotes(-L))


def pivotes(x):
    """Índices q con x[q] ≥ las W velas de cada lado (pivote de máximo; para mínimos pasar −L). Se confirma en la vela q + W."""
    n = len(x); ok = np.zeros(n, bool); ok[W_PICO:n - W_PICO] = True
    for o in range(1, W_PICO + 1):
        ok[W_PICO:n - W_PICO] &= (x[W_PICO:n - W_PICO] >= x[W_PICO - o:n - W_PICO - o]) & (x[W_PICO:n - W_PICO] >= x[W_PICO + o:n - W_PICO + o])
    return np.flatnonzero(ok)


def _picos_vivos(x, piv, hasta_vela, x_parcial):
    """Pivotes de `piv` confirmados a más tardar en `hasta_vela` (q + W ≤ hasta_vela) y sin romper hasta el toque: ninguna vela
    completa posterior (≤ hasta_vela) ni el tramo parcial de la vela del toque (`x_parcial`) lo superó."""
    q = piv[piv + W_PICO <= hasta_vela]
    if not q.size: return q
    suf = np.maximum.accumulate(x[:hasta_vela + 1][::-1])[::-1]                   # suf[k] = máx de x[k..hasta_vela]
    despues = np.append(suf[1:], -np.inf)[q]
    return q[(despues < x[q]) & (x_parcial < x[q])]


def rasgos_extra(ts, px, vol, j, j_sal, lado, X, c, M, i0=0, pasada_s=np.nan):
    """Rasgos de la enmienda A1 y la revisión R1. Sólo velas de 1 min COMPLETAS antes del toque y ticks ≤ j.
    `j_sal` = salida previa (primer tick a X/4 del rango tras la visita anterior); `i0` = primer tick de la vida del cluster;
    `pasada_s` = segundos dentro del rango en la visita anterior (la última pasada del precio por el cluster)."""
    llegada = -lado; vj = int(M["vela"][j]); km = vj - 1                         # última vela COMPLETA antes del toque
    out = dict(picos_dentro=np.nan, picos_sin_tomar=np.nan, ema9_pend=np.nan, ema21_pend=np.nan, pasada_s=float(pasada_s))
    if km >= 2 * W_PICO:
        parcial = slice(int(M["ini"][vj]), j + 1); hp, lp = float(px[parcial].max()), float(px[parcial].min())
        altos = _picos_vivos(M["H"], M["piv_H"], km, hp); bajos = _picos_vivos(-M["L"], M["piv_L"], km, -lp)
        # liquidez dentro: picos vivos con precio en el rango (en la práctica, los del lado de llegada: los del otro lado ya se tomaron)
        out["picos_dentro"] = float(((M["H"][altos] >= c["lo"]) & (M["H"][altos] <= c["hi"])).sum()
                                    + ((M["L"][bajos] >= c["lo"]) & (M["L"][bajos] <= c["hi"])).sum())
        # picos que la aproximación dejó atrás sin tomar desde la salida previa: llega bajando → máximos arriba; subiendo → mínimos abajo
        v_sal = int(M["vela"][j_sal]); atras = altos if llegada < 0 else bajos
        out["picos_sin_tomar"] = float((atras >= v_sal).sum())
    for e, span in (("ema9_pend", "e9"), ("ema21_pend", "e21")):                 # pendiente en 5 velas; nada hasta que la EMA se asienta
        if km >= int(span[1:]) + 5: out[e] = float((M[span][km] - M[span][km - 5]) / X * llegada)   # > 0: la EMA va hacia el cluster
    # expansión de la última salida: desde el ÚLTIMO tick dentro del rango antes de j_sal hasta estar a X/2 (segundos y eficiencia)
    seg = px[i0:j_sal + 1]; adentro = np.flatnonzero((seg >= c["lo"]) & (seg <= c["hi"]))
    out["salida_s"] = out["salida_eficiencia"] = np.nan
    if adentro.size:
        a = i0 + int(adentro[-1]); dist = np.maximum(np.maximum(c["lo"] - px[a:j + 1], px[a:j + 1] - c["hi"]), 0.0)
        k = _primero(dist >= X / 2)
        if k > 0:
            out["salida_s"] = float((ts[a + k] - ts[a]) / NS)
            camino = float(np.abs(np.diff(px[a:a + k + 1])).sum())
            out["salida_eficiencia"] = float(abs(px[a + k] - px[a]) / camino) if camino > 0 else np.nan   # 1 = línea recta
    # volumen del cluster (proxy): negociado dentro del rango en los 30 min previos a la detección / volumen medio por 30 min de la sesión
    t0 = c["t_ns"]; a = int(np.searchsorted(ts, t0 - 1800 * NS)); b = int(np.searchsorted(ts, t0, side="right"))
    if b > a and vol[:b].sum() > 0:
        bloques = max((ts[b - 1] - ts[0]) / (1800 * NS), 1.0); en = (px[a:b] >= c["lo"]) & (px[a:b] <= c["hi"])
        out["vol_banda_rel"] = float(vol[a:b][en].sum() / (vol[:b].sum() / bloques))
    else: out["vol_banda_rel"] = np.nan
    return out


def desenlaces(ts, px, j, ref, lado, X):
    d = -lado; j1 = int(np.searchsorted(ts, ts[j] + HORIZONTE_S * NS, side="right"))
    rX, iX = _carrera(px, j, ref, d, X, j1); rh, _ = _carrera(px, j, ref, d, X / 2, j1); r2, _ = _carrera(px, j, ref, d, 2 * X, j1)
    j15 = int(np.searchsorted(ts, ts[j] + 900 * NS, side="right")); seg = px[j + 1:j15]
    mfe = float((d * (seg - ref)).max() / X) if seg.size else 0.0
    return dict(rompe=rX, rompe_media=rh, rompe_doble=r2, t_res_s=float((ts[j + 1 + iX] - ts[j]) / NS) if iX >= 0 else np.nan, avance15_x=mfe)


def _minutos_et(t_ns):
    m = pd.to_datetime(np.asarray(t_ns), unit="ns", utc=True).tz_convert("America/New_York").map(lambda x: x.hour * 60 + x.minute).to_numpy()
    return (m - 18 * 60) % 1440                                                    # minutos desde la apertura de la sesión (18:00 ET)


def ruptura_del_dia(inst, fecha, ts, px, vol, C: pd.DataFrame, tick, friccion) -> list:
    """Filas por toque D0 real (placebo 0) y de control (placebo 1, misma ubicación que hft_rebotes), con rasgos y desenlaces."""
    X = barrera(friccion, tick); filas = []; C = C.reset_index(drop=True); reales = C.t_ns.to_numpy(np.int64)
    r_lo, r_hi = C.lo.to_numpy(float), C.hi.to_numpy(float); signo = _tick_rule(px); M = minutos(ts, px)

    def uno(t0, lo, hi, info, placebo):
        i0 = int(np.searchsorted(ts, t0, side="right")); i1 = int(np.searchsorted(ts, t0 + VIDA_CLUSTER_S * NS, side="right"))
        if i1 - i0 < 3: return
        tt = (ts[i0:i1] - t0) / NS
        ev = RB.eventos(tt, px[i0:i1], vol[i0:i1], lo, hi, X, tick).get("D0_BASE")
        if ev is None: return
        j, ref, lado, j_sal = ev; j += i0; j_sal += i0
        V = RB.visitas(tt, px[i0:i1], vol[i0:i1], lo, hi, X / 4); nv = sum(1 for r in V if r["ini"] + i0 <= j)
        prev = [r for r in V if r["fin"] + i0 == j_sal]; pasada = prev[0]["seg_dentro"] if prev else np.nan
        c = dict(info, lo=lo, hi=hi, t_ns=t0)
        filas.append(dict(inst=inst, fecha=int(fecha), placebo=placebo, lado=lado,
                          **rasgos_evento(ts, px, vol, signo, i0, j, j_sal, ref, lado, X, 0, c, nv, int(_minutos_et([ts[j]])[0])),
                          **rasgos_extra(ts, px, vol, j, j_sal, lado, X, c, M, i0=i0, pasada_s=pasada),
                          **desenlaces(ts, px, j, ref, lado, X)))

    for k, c in enumerate(C.itertuples(index=False)):
        uno(int(c.t_ns), float(c.lo), float(c.hi), dict(n_zonas=getattr(c, "n_zonas", np.nan), packing=getattr(c, "packing", np.nan),
                                                         net_dir=getattr(c, "net_dir", 0)), 0)
        w = float(c.hi - c.lo)
        for des in RB.DESFASES_S:
            t2 = int(c.t_ns) + des * NS
            if t2 <= ts[0] or t2 >= ts[-1] or np.abs(reales - t2).min() < RB.MARGEN_S * NS: continue
            kk = int(np.searchsorted(ts, t2, side="right")) - 1; centro = float(px[kk]); plo, phi = centro - w / 2, centro + w / 2
            vivo = (reales < t2 + VIDA_CLUSTER_S * NS) & (reales + VIDA_CLUSTER_S * NS > t2)
            if (vivo & (r_lo <= phi + X / 4) & (plo - X / 4 <= r_hi)).any(): continue
            uno(int(ts[kk]), plo, phi, dict(n_zonas=np.nan, packing=np.nan, net_dir=np.nan), 1)   # el control no tiene zonas
    return filas


def cortes_de(T, r):
    """(corte_1, corte_2) por activo: fijos si el rasgo es discreto; si no, terciles de los eventos REALES de ese activo."""
    if r in CORTES_FIJOS: return {i: tuple(CORTES_FIJOS[r]) for i in T.inst.unique()}
    return {i: tuple(np.nanquantile(h[h.placebo == 0][r], [1 / 3, 2 / 3])) for i, h in T.groupby("inst")}


def estrato(T, r, cortes):
    """0, 1, 2 con estrato = (v > corte_1) + (v > corte_2) usando los cortes del activo de cada fila; −1 sin dato o sin cortes."""
    out = np.full(len(T), -1)
    for i, (c1, c2) in cortes.items():
        m = (T.inst.to_numpy() == i) & np.isfinite(T[r].to_numpy(float)); v = T[r].to_numpy(float)[m]
        out[m] = (v > c1).astype(int) + (v > c2).astype(int)
    return out


def diagnostico_estratos(T: pd.DataFrame, rasgos=RASGOS) -> dict:
    """Preflight de cortes (error 2 de `preflight`): fracción de eventos reales por estrato y activo. Un estrato con < 10 % de los
    eventos de un activo queda marcado: esa celda casi no tiene muestra y su lectura se informa como tal."""
    out = {}; R = T[T.placebo == 0]
    for r in rasgos:
        if r not in R or R[r].notna().sum() == 0: out[r] = dict(sin_dato=True); continue
        e = estrato(R, r, cortes_de(T, r)); d = {}
        for i in R.inst.unique():
            m = (R.inst.to_numpy() == i) & (e >= 0); n = max(int(m.sum()), 1)
            d[i] = [round(float((e[m] == k).sum()) / n, 3) for k in (0, 1, 2)]
        out[r] = dict(fracciones=d, degenerado=any(min(v) < 0.10 for v in d.values()), sin_dato_frac=round(float(R[r].isna().mean()), 3))
    return out


def marginales(T: pd.DataFrame, rasgos=RASGOS, n_boot: int = 2000) -> list:
    """Por rasgo: terciles definidos en los eventos reales de cada activo; por tercil, desenlace medio de ruptura (real y control),
    diferencia real − control y estabilidad mensual del tercil extremo. Exploratorio: sin decisión, alimenta la regla de selección."""
    from edgelab.research.hft_clusters_info import contraste
    out = []
    for r in rasgos:
        if r not in T or T[r].notna().sum() < 300: continue
        X = T.copy(); cortes = cortes_de(X, r)
        X["tercil"] = estrato(X, r, cortes)
        for t in (0, 1, 2):
            S = X[X.tercil == t]
            if (S.placebo == 0).sum() < 100: continue
            reales = S[S.placebo == 0]
            c = contraste(S.assign(resultado=S.rompe), n_boot=n_boot) if (S.placebo == 1).sum() >= 30 else {}
            mes = reales.assign(m=reales.fecha // 100).groupby("m").rompe.mean(); mu, se = _media_por_sesion(reales.rompe, reales, n_boot)
            out.append(dict(rasgo=r, tercil=t, cortes_por_activo={i: [float(x) for x in v] for i, v in cortes.items()}, n_real=int(len(reales)),
                            rompe_real=float(reales.rompe.mean()), rompe_media=float(reales.rompe_media.mean()), rompe_doble=float(reales.rompe_doble.mean()),
                            avance15=float(reales.avance15_x.mean()), dif_vs_control=c.get("diferencia"), ic90_vs_control=c.get("ic90"),
                            meses_positivos=int((mes > 0).sum()), meses=int(len(mes)), se_real=se,
                            ic90_real=[mu - 1.645 * se, mu + 1.645 * se] if np.isfinite(se) else None,
                            p_real=float(1 - NormalDist().cdf(mu / se)) if se and np.isfinite(se) and se > 0 else 1.0,
                            por_activo={i: float(h.rompe.mean()) for i, h in reales.groupby("inst")},
                            n_por_activo={i: int(len(h)) for i, h in reales.groupby("inst")}))
    ps = sorted((m["p_real"], k) for k, m in enumerate(out)); n = len(ps)        # BH q 0,10 entre TODAS las celdas (H0: ruptura ≤ 0)
    kmax = max([i + 1 for i, (p, _) in enumerate(ps) if p <= 0.10 * (i + 1) / max(n, 1)] or [0])
    for _, k in ps[:kmax]: out[k]["nominada_bh"] = True
    for m in out: m.setdefault("nominada_bh", False)
    return out


def _media_por_sesion(x, D, n_boot):
    """Media y error estándar por bootstrap de sesiones (inst, fecha): los eventos de una misma sesión no son independientes."""
    g = pd.DataFrame(dict(x=x.to_numpy(float), k=D.inst.astype(str) + D.fecha.astype(str))).groupby("k").x.agg(["sum", "count"]).to_numpy(float)
    mu = float(g[:, 0].sum() / g[:, 1].sum())
    if len(g) < 5: return mu, np.nan
    rng = np.random.default_rng(7); idx = rng.integers(0, len(g), (n_boot, len(g)))
    b = g[idx, 0].sum(1) / g[idx, 1].sum(1); return mu, float(b.std(ddof=1))


def _activos_ok(m, n_min: int = 100):
    """Mismo signo (> 0) en cada activo con ≥ `n_min` eventos reales en la celda; NQ siempre cuenta."""
    n = m.get("n_por_activo") or {}
    return all(v > 0 for i, v in m["por_activo"].items() if i == "NQ" or n.get(i, n_min) >= n_min)


def seleccionar(M: list, max_reglas: int = 3) -> list:
    """Regla MECÁNICA (pre-registrada; R2: más nominación BH q 0,10 entre todas las celdas) para pasar de la indagación a la
    confirmación: celdas rasgo × tercil nominadas, con ruptura real media ≥ 0,08 (paga la fricción), mejor que el control, ≥ 5 de 8 meses positivos y mismo signo en NQ y ES (o sólo NQ si ES < 100
    eventos). Se ordenan por ruptura media y se toman hasta 3, de rasgos distintos."""
    ok = [m for m in M if m.get("nominada_bh", True) and m["rompe_real"] >= 0.08 and (m["dif_vs_control"] is None or m["dif_vs_control"] > 0)
          and m["meses_positivos"] >= max(5, int(0.6 * m["meses"])) and _activos_ok(m)]
    out, vistos = [], set()
    for m in sorted(ok, key=lambda m: -m["rompe_real"]):
        if m["rasgo"] in vistos: continue
        out.append(m); vistos.add(m["rasgo"])
        if len(out) == max_reglas: break
    return out
