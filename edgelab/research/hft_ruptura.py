"""HFT-RUPTURA (2026-11-10): ¿en qué toques de un cluster HFT grande el precio lo ATRAVIESA de forma distintiva?

Indagación (EF2, exploratoria, sobre DESC ya usado) seguida de confirmación en datos no usados. Pre-registro:
`docs/research/hft_clusters_u1_20261110/PREREGISTRO_RUPTURA.md`. Parte de HFT-REBOTES: en NQ el cluster grande no se defiende
(real ≈ 50/50 mientras un nivel cualquiera de la sesión rebota +0,07), pero en términos absolutos no hay ruptura operable.

Para cada toque D0 (primer regreso tras alejarse X/2), real y de control, se guarda un vector de rasgos causales (todo medido con ticks
anteriores o iguales al toque, salvo los desenlaces) y varios desenlaces. Signo: `rompe` = +1 si la carrera ±X termina del otro lado.
Rasgos (familias):
  aproximación   segundos de los últimos X/2, excursión previa (en X), segundos afuera
  cluster        edad, ancho (en X), zonas, packing, alineación del flujo de sus zonas con la dirección de llegada, nº de visita
  sesión         minuto del día (ET), tendencia de la sesión respecto de la llegada, distancia al extremo de la sesión (en X),
                 rango de los últimos 30 min (en X)
  toque          volumen de los 30 s anteriores al toque contra la mediana de la sesión, desequilibrio (tick rule) en la dirección
                 de llegada en esos 30 s
Desenlaces: carrera ±X, ±X/2 y ±2X (+1 = rompe), segundos hasta resolver ±X, máximo avance a favor de la ruptura en 15 min (en X).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import hft_rebotes as RB
from edgelab.research.hft_clusters_info import HORIZONTE_S, VIDA_CLUSTER_S, _primero, barrera

NS = 1_000_000_000
RASGOS = ["aprox_s", "excursion_x", "afuera_s", "edad_s", "ancho_x", "n_zonas", "packing", "flujo_alineado", "visita",
          "minuto_et", "tendencia_alineada", "dist_extremo_x", "rango30_x", "vol30_rel", "deseq30",
          # Enmienda (Nico, 2026-11-10, antes de ver resultados): picos, expansión de salida, volumen del cluster y pendiente de EMAs
          "picos_dentro", "picos_sin_tomar", "salida_s", "vol_banda_rel", "ema9_pend", "ema21_pend"]
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
                packing=float(c.get("packing", np.nan)), flujo_alineado=float(c.get("net_dir", 0) * llegada), visita=float(n_visita),
                minuto_et=float(minuto_et), tendencia_alineada=float(np.sign(px[j] - px[ses_ini]) * llegada),
                dist_extremo_x=float(abs(px[j] - extremo) / X), rango30_x=float((px[w1800].max() - px[w1800].min()) / X),
                vol30_rel=float(v30 / med30) if med30 and med30 > 0 else np.nan, deseq30=float(s30 / v30 * llegada) if v30 > 0 else 0.0)


def minutos(ts, px):
    """Velas de 1 minuto de la sesión: índice de vela por tick, primer tick de cada vela, máximos, mínimos, cierres y EMAs 9 y 21."""
    m = (ts - ts[0]) // (60 * NS); ini = np.flatnonzero(np.r_[True, m[1:] != m[:-1]])
    H = np.maximum.reduceat(px, ini); L = np.minimum.reduceat(px, ini); Cc = px[np.r_[ini[1:], len(px)] - 1]
    e9 = pd.Series(Cc).ewm(span=9, adjust=False).mean().to_numpy(); e21 = pd.Series(Cc).ewm(span=21, adjust=False).mean().to_numpy()
    vela = np.repeat(np.arange(len(ini)), np.diff(np.r_[ini, len(px)]))
    return dict(vela=vela, ini=ini, H=H, L=L, C=Cc, e9=e9, e21=e21)


def _picos_vivos(x, desde, hasta_vela, x_parcial):
    """Pivotes de máximo de `x` (velas) con índice en [desde, hasta_vela − W], confirmados W velas después (≤ hasta_vela) y sin
    romper hasta el toque (velas completas hasta `hasta_vela` y el tramo parcial de la vela en curso, `x_parcial`)."""
    out = []
    for q in range(max(W_PICO, desde), hasta_vela - W_PICO + 1):
        if all(x[q] >= x[q - o] and x[q] >= x[q + o] for o in range(1, W_PICO + 1)):
            if x[q + 1:hasta_vela + 1].max(initial=-np.inf) < x[q] and x_parcial < x[q]: out.append(q)
    return out


def rasgos_extra(ts, px, vol, j, j_sal, lado, X, c, M):
    """Rasgos de la enmienda. Sólo velas completas antes del toque y ticks ≤ j."""
    llegada = -lado; vj = int(M["vela"][j]); km = vj - 1                         # última vela COMPLETA antes del toque
    if km < 2 * W_PICO + 1: return dict(picos_dentro=np.nan, picos_sin_tomar=np.nan, salida_s=np.nan, vol_banda_rel=np.nan, ema9_pend=np.nan, ema21_pend=np.nan)
    parcial = slice(int(M["ini"][vj]), j + 1)
    hp, lp = float(px[parcial].max()), float(px[parcial].min())
    altos = _picos_vivos(M["H"], 0, km, hp); bajos = _picos_vivos(-M["L"], 0, km, -lp)
    dentro = sum(1 for q in altos if c["lo"] <= M["H"][q] <= c["hi"]) + sum(1 for q in bajos if c["lo"] <= M["L"][q] <= c["hi"])
    # picos que la aproximación dejó atrás sin tomar: llega bajando (llegada −1) → máximos que quedaron arriba; subiendo → mínimos
    v_sal = int(M["vela"][j_sal])
    atras = [q for q in (altos if llegada < 0 else bajos) if q >= v_sal]
    # expansión de la última salida: segundos desde que dejó el rango hasta estar a X/2 de él
    dist = np.maximum(np.maximum(c["lo"] - px[j_sal:j + 1], px[j_sal:j + 1] - c["hi"]), 0.0)
    k = _primero(dist >= X / 2); salida_s = float((ts[j_sal + k] - ts[j_sal]) / NS) if k >= 0 else np.nan
    # volumen negociado dentro del rango en los 30 min previos a la detección, contra el volumen medio por 30 min de la sesión
    t0 = c["t_ns"]; a = int(np.searchsorted(ts, t0 - 1800 * NS)); b = int(np.searchsorted(ts, t0))
    dentro_b = (px[a:b] >= c["lo"]) & (px[a:b] <= c["hi"]); horas = max((ts[b - 1] - ts[0]) / (1800 * NS), 1.0) if b > 0 else 1.0
    vol_rel = float(vol[a:b][dentro_b].sum() / (vol[:b].sum() / horas)) if b > a and vol[:b].sum() > 0 else np.nan
    pend = lambda e: float((e[km] - e[km - 5]) / X * llegada) if km >= 5 else np.nan   # >0: la EMA se mueve hacia el cluster
    return dict(picos_dentro=float(dentro), picos_sin_tomar=float(len(atras)), salida_s=salida_s, vol_banda_rel=vol_rel,
                ema9_pend=pend(M["e9"]), ema21_pend=pend(M["e21"]))


def desenlaces(ts, px, j, ref, lado, X):
    d = -lado; j1 = int(np.searchsorted(ts, ts[j] + HORIZONTE_S * NS, side="right"))
    rX, iX = _carrera(px, j, ref, d, X, j1); rh, _ = _carrera(px, j, ref, d, X / 2, j1); r2, _ = _carrera(px, j, ref, d, 2 * X, j1)
    j15 = int(np.searchsorted(ts, ts[j] + 900 * NS, side="right")); seg = px[j + 1:j15]
    mfe = float((d * (seg - ref)).max() / X) if seg.size else 0.0
    return dict(rompe=rX, rompe_media=rh, rompe_doble=r2, t_res_s=float((ts[j + 1 + iX] - ts[j]) / NS) if iX >= 0 else np.nan, avance15_x=mfe)


def _minutos_et(t_ns):
    return pd.to_datetime(np.asarray(t_ns), unit="ns", utc=True).tz_convert("America/New_York").map(lambda x: x.hour * 60 + x.minute).to_numpy()


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
        c = dict(info, lo=lo, hi=hi, t_ns=t0)
        filas.append(dict(inst=inst, fecha=int(fecha), placebo=placebo, lado=lado,
                          **rasgos_evento(ts, px, vol, signo, i0, j, j_sal, ref, lado, X, 0, c, nv, int(_minutos_et([ts[j]])[0])),
                          **rasgos_extra(ts, px, vol, j, j_sal, lado, X, c, M),
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
            uno(int(ts[kk]), plo, phi, dict(n_zonas=np.nan, packing=np.nan, net_dir=0), 1)
    return filas


def marginales(T: pd.DataFrame, rasgos=RASGOS, n_boot: int = 2000) -> list:
    """Por rasgo: terciles definidos en los eventos reales de cada activo; por tercil, desenlace medio de ruptura (real y control),
    diferencia real − control y estabilidad mensual del tercil extremo. Exploratorio: sin decisión, alimenta la regla de selección."""
    from edgelab.research.hft_clusters_info import contraste
    out = []
    for r in rasgos:
        if r not in T or T[r].notna().sum() < 300: continue
        X = T.copy()
        cortes = {i: np.nanquantile(h[h.placebo == 0][r], [1 / 3, 2 / 3]) for i, h in X.groupby("inst")}
        X["tercil"] = [np.searchsorted(cortes[i], v, side="right") if np.isfinite(v) else -1 for i, v in zip(X.inst, X[r])]
        for t in (0, 1, 2):
            S = X[X.tercil == t]
            if (S.placebo == 0).sum() < 100: continue
            reales = S[S.placebo == 0]
            c = contraste(S.assign(resultado=S.rompe), n_boot=n_boot) if (S.placebo == 1).sum() >= 30 else {}
            mes = reales.assign(m=reales.fecha // 100).groupby("m").rompe.mean()
            out.append(dict(rasgo=r, tercil=t, corte=[float(x) for x in np.nanmean(list(cortes.values()), axis=0)], n_real=int(len(reales)),
                            rompe_real=float(reales.rompe.mean()), rompe_media=float(reales.rompe_media.mean()), rompe_doble=float(reales.rompe_doble.mean()),
                            avance15=float(reales.avance15_x.mean()), dif_vs_control=c.get("diferencia"), ic90_vs_control=c.get("ic90"),
                            meses_positivos=int((mes > 0).sum()), meses=int(len(mes)),
                            por_activo={i: float(h.rompe.mean()) for i, h in reales.groupby("inst")}))
    return out


def seleccionar(M: list, max_reglas: int = 3) -> list:
    """Regla MECÁNICA (pre-registrada) para pasar de la indagación a la confirmación: celdas rasgo × tercil con ruptura real media
    ≥ 0,08 (paga la fricción), mejor que el control, ≥ 5 de 8 meses positivos y mismo signo en NQ y ES (o sólo NQ si ES < 100
    eventos). Se ordenan por ruptura media y se toman hasta 3, de rasgos distintos."""
    ok = [m for m in M if m["rompe_real"] >= 0.08 and (m["dif_vs_control"] is None or m["dif_vs_control"] > 0)
          and m["meses_positivos"] >= max(5, int(0.6 * m["meses"])) and all(v > 0 for v in m["por_activo"].values())]
    out, vistos = [], set()
    for m in sorted(ok, key=lambda m: -m["rompe_real"]):
        if m["rasgo"] in vistos: continue
        out.append(m); vistos.add(m["rasgo"])
        if len(out) == max_reglas: break
    return out
