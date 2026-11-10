"""REBOTE_NIVEL_SESION (2026-11-10, idea de Nico): ¿el primer regreso a un nivel cualquiera de la sesión rebota, y más cuando cerca no
hay zonas HFT (ni clusters ni zonas individuales)? Pre-registro: `docs/research/hft_clusters_u1_20261110/PREREGISTRO_REBOTE_NIVEL.md`.

Generador causal para el banco de eventos (`banco_eventos.GENERADORES["niveles_sesion"]`).
  Nivel     cada PASO_S segundos desde el primer tick de la sesión, el último precio conocido; banda ± ANCHO_FRAC · X / 2.
  Evento    D0 de `hft_rebotes.eventos`: primer regreso a la banda tras alejarse X/2, dentro de VIDA_S (misma vida que un cluster).
  Desenlace carrera ±X (`hft_ruptura.desenlaces`: rompe = +1 atraviesa, −1 rebota).
  Rasgos    los 23 de `hft_ruptura` (llegada, sesión, picos, EMAs…) y los de «sin zonas», que son el PARÁMETRO espacial × temporal:
            dist_zona_<T>   distancia (en X) de la banda a la zona HFT individual más cercana disponible en los T s previos al
                            evento (T = 600, 1.800, 3.600); SIN_ZONA = 99 si no hubo ninguna
            dist_cluster    distancia (en X) al cluster HFT grande vivo más cercano (definición del E0-b del activo)
            n_zonas_1x_1800 zonas a ≤ 1 X en los 1.800 s previos
Todo es causal: sólo zonas con disponibilidad < t del evento y clusters detectados antes y todavía vivos.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import fill_pasivo as FP
from edgelab.research import hft_rebotes as RB
from edgelab.research import hft_ruptura as RU
from edgelab.research.hft_clusters_info import VIDA_CLUSTER_S, ZONAS, barrera

NS = 1_000_000_000
PASO_S, ANCHO_FRAC, VIDA_S = 600, 0.25, VIDA_CLUSTER_S
VENTANAS_S = (600, 1800, 3600)
SIN_ZONA = 99.0
# OP-1 (PLAN_OPERABLE_Y_CUERDAS.md §2 e iteración §7): orden límite en el borde del nivel, activa desde que el precio se alejó X/2,
# stop X, tres objetivos fijados ANTES de mirar (X/2, X, 2X), salida por tiempo a los 900 s del fill; dos modelos de fill.
GEOMETRIAS = {"g05": 0.5, "g1": 1.0, "g2": 2.0}
T_MAX_OP_S = 900
COLUMNAS_OP = [f"op_{m}_llena" for m in FP.MODELOS] + [f"op_{m}_{g}" for m in FP.MODELOS for g in GEOMETRIAS] + ["op_costo_r"]
TIPOS = ("reloj", "pivote")
RASGOS_ZONA = [f"dist_zona_{t}" for t in VENTANAS_S] + ["dist_cluster", "n_zonas_1x_1800"]
RASGOS = [r for r in RU.RASGOS if r not in ("ancho_x", "n_zonas", "packing", "flujo_alineado", "visita", "pasada_s")] + RASGOS_ZONA   # constantes o sin sentido para un nivel
CORTES_FIJOS = dict({k: list(v) for k, v in RU.CORTES_FIJOS.items() if k in RASGOS},
                    **{r: [0.5, 1.0] for r in RASGOS_ZONA if r.startswith("dist_")}, n_zonas_1x_1800=[0.5, 2.5])


def zonas_del_dia(ts_ns, px, vol, sesion, tick: float, zona: str = "Z_CERT") -> pd.DataFrame:
    """Zonas HFT individuales aceptadas (mismo detector y filtro que `hft_clusters_info.clusters_del_dia`): t_ns = disponibilidad."""
    from edgelab.bridge.indicators import hftzones_nq_rangos_pct_v2 as HZ
    pt = np.round(np.asarray(px, float) / tick).astype(np.int64); ts = np.asarray(ts_ns, np.int64); ses = np.asarray(sesion, np.int64)
    _, _, _, _, _, barra = HZ.construir_barras_ticks(ts, pt, ses, ticks_per_bar=5, tick_size=tick)
    ci, cf = HZ.detectar_candidatos_nb(ts, pt, np.asarray(vol, float), ses, barra, max_pausa_ms=100.0, retro_floor_ticks=2.0,
                                       retro_pct_height=50.0, has_prev_session_close=False, prev_session_close_ticks=0)
    z = ZONAS[zona]; acc, _, _ = HZ.filtrar_zonas_nb(ci, cf, max_avg_ms=z["max_avg_ms"], min_total_volume=z["min_total_volume"], detect_absorb=z["detect_absorb"])
    if not len(acc): return pd.DataFrame(dict(t_ns=np.array([], np.int64), lo=np.array([]), hi=np.array([])))
    zi = ci[acc]
    return pd.DataFrame(dict(t_ns=zi[:, 5].astype(np.int64), lo=zi[:, 11] * tick, hi=zi[:, 10] * tick))


def _dist(lo, hi, zlo, zhi, X):
    """Distancia (en X) entre la banda [lo, hi] y cada rango [zlo, zhi]; 0 si se solapan."""
    return np.maximum(np.maximum(zlo - hi, lo - zhi), 0.0) / X


def rasgos_zona(t_ev: int, lo: float, hi: float, X: float, Z: pd.DataFrame, C: pd.DataFrame | None) -> dict:
    out = {}
    zt = Z.t_ns.to_numpy(np.int64); d = _dist(lo, hi, Z.lo.to_numpy(float), Z.hi.to_numpy(float), X) if len(Z) else np.array([])
    for T in VENTANAS_S:
        m = (zt < t_ev) & (zt >= t_ev - T * NS)
        out[f"dist_zona_{T}"] = float(d[m].min()) if m.any() else SIN_ZONA
    m = (zt < t_ev) & (zt >= t_ev - 1800 * NS)
    out["n_zonas_1x_1800"] = float((d[m] <= 1.0).sum()) if m.any() else 0.0
    if C is not None and len(C):
        ct = C.t_ns.to_numpy(np.int64); vivo = (ct < t_ev) & (ct + VIDA_CLUSTER_S * NS > t_ev)
        dc = _dist(lo, hi, C.lo.to_numpy(float), C.hi.to_numpy(float), X)
        out["dist_cluster"] = float(dc[vivo].min()) if vivo.any() else SIN_ZONA
    else: out["dist_cluster"] = SIN_ZONA
    return out


def operacion_nivel(ts, px, i0: int, i1: int, lo: float, hi: float, X: float, tick: float, friccion: float) -> dict:
    """OP-1 sobre un nivel: la orden se activa en el primer tick a ≥ X/2 de la banda (antes, se llenaría en el acto) y vence con la
    vida del nivel. Compra límite en `hi` si el precio se fue arriba; venta límite en `lo` si se fue abajo. R bruto por geometría y
    modelo (0 si no se llenó) y el costo en R (fricción / X) para el neto."""
    d = np.maximum(np.maximum(lo - px[i0:i1], px[i0:i1] - hi), 0.0); k = np.flatnonzero(d >= X / 2)
    out = {c: np.nan for c in COLUMNAS_OP}; out["op_costo_r"] = float(friccion / X)
    if not k.size: return out
    ja = i0 + int(k[0]); lado = 1 if px[ja] > hi else -1; lim = hi if lado > 0 else lo
    for m in FP.MODELOS:
        for g, f in GEOMETRIAS.items():
            r = FP.operar(ts, px, ja, i1, lim, lado, X, f * X, T_MAX_OP_S, tick, m)
            out[f"op_{m}_{g}"] = r["r_bruto"] if r["llena"] else np.nan; out[f"op_{m}_llena"] = float(r["llena"])
    return out


def _niveles(ts, px, tipo: str):
    """[(t0, centro)]: «reloj» = cada PASO_S s el último precio; «pivote» = máximos y mínimos de 1 min (pivote de W velas por lado,
    misma definición que `hft_ruptura`) en el instante en que se CONFIRMAN (cierre de la vela q + W)."""
    if tipo == "reloj":
        return [(t0, float(px[int(np.searchsorted(ts, t0, side="right")) - 1]))
                for t0 in range(int(ts[0]) + PASO_S * NS, int(ts[-1]) - 60 * NS, PASO_S * NS)]
    M = RU.minutos(ts, px); fin = np.r_[M["ini"][1:], len(px)] - 1; out = []
    for piv, serie in ((M["piv_H"], M["H"]), (M["piv_L"], M["L"])):
        for q in piv:
            c = q + RU.W_PICO
            if c < len(fin): out.append((int(ts[fin[c]]) + 1, float(serie[q])))
    return sorted(out)


def niveles_del_dia(inst, fecha, ts, px, vol, Z: pd.DataFrame, C: pd.DataFrame | None, tick, friccion, tipo: str = "reloj",
                    con_operacion: bool = False) -> list:
    """Una fila por nivel que tuvo su primer regreso D0 (placebo = 0: el banco contrasta estratos de la misma tabla).
    `con_operacion` agrega las columnas de OP-1 (desenlaces: van en `columnas_desenlace` de la especificación)."""
    X = barrera(friccion, tick); w = ANCHO_FRAC * X; filas = []
    signo = RU._tick_rule(px); M = RU.minutos(ts, px)
    for t0, centro in _niveles(ts, px, tipo):
        lo, hi = centro - w / 2, centro + w / 2
        i0 = int(np.searchsorted(ts, t0, side="right")); i1 = int(np.searchsorted(ts, t0 + VIDA_S * NS, side="right"))
        if i1 - i0 < 3: continue
        tt = (ts[i0:i1] - t0) / NS
        ev = RB.eventos(tt, px[i0:i1], vol[i0:i1], lo, hi, X, tick).get("D0_BASE")
        if ev is None: continue
        j, ref, lado, j_sal = ev; j += i0; j_sal += i0
        c = dict(lo=lo, hi=hi, t_ns=t0, n_zonas=np.nan, packing=np.nan, net_dir=np.nan)
        r = RU.rasgos_evento(ts, px, vol, signo, i0, j, j_sal, ref, lado, X, 0, c, 2, int(RU._minutos_et([ts[j]])[0]))
        r.update(RU.rasgos_extra(ts, px, vol, j, j_sal, lado, X, c, M, i0=i0))
        r.update(rasgos_zona(int(ts[j]), lo, hi, X, Z, C))
        fila = dict(inst=inst, fecha=int(fecha), placebo=0, lado=lado, tipo_nivel=tipo, **{q: r[q] for q in RASGOS}, **RU.desenlaces(ts, px, j, ref, lado, X))
        if con_operacion: fila.update(operacion_nivel(ts, px, i0, i1, lo, hi, X, tick, friccion))
        filas.append(fila)
    return filas
