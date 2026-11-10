"""HFT-REBOTES (2026-11-10): varias definiciones de «rebote en un cluster de zonas HFT», medidas con la misma carrera y el mismo control.

Pre-registro: `docs/research/hft_clusters_u1_20261110/PREREGISTRO_REBOTES.md`. Clusters: definición elegida por el E0-b (NQ y ES).

Todo se construye sobre la HISTORIA DE VISITAS de un cluster, sólo con ticks posteriores a su detección `t_ns` (reloj en segundos):
  - visita = tramo que empieza cuando el precio entra al rango [lo, hi] y termina cuando se aleja al menos `SALIDA` (X/4) de él;
  - entre dos visitas se mide la excursión máxima, el tiempo afuera, la velocidad de la aproximación y el lado por el que volvió;
  - durante la visita, cuánto penetró, cuánto tiempo y volumen negoció adentro y por dónde salió.
Cada definición es una condición sobre esa historia que elige, como mucho, UN evento por cluster (el primero que la cumple).
Desenlace común: carrera simétrica a ±X desde el precio de referencia del evento (+1 rebote, −1 atravesó, 0 sin definir en 3.600 s).
Control: el mismo procedimiento sobre pseudo-clusters del mismo ancho centrados en el precio de otra hora de la misma sesión (lejos de
clusters reales), que comparten la condición del evento («el precio negoció en ese nivel y después se alejó/volvió»).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.hft_clusters_info import HORIZONTE_S, VIDA_CLUSTER_S, _primero, barrera

NS = 1_000_000_000
VENTANA_NACIMIENTO_S = 300        # los primeros 5 minutos de vida definen «aceptado» o «rechazado al nacer»
DEFINICIONES = {
    "D0_BASE": "Primer regreso al borde tras alejarse X/2 (la definición del paso INFO, como referencia).",
    "D1_FRESCO_LEJANO": "Regreso tras una excursión ≥ X desde la última visita; sólo mientras el cluster esté fresco: visita nº ≤ 3 y "
                        "≤ 600 s negociados adentro en total (después deja de considerarse).",
    "D2_ACEPTADO_Y_ABANDONADO": "En los primeros 300 s el precio pasó ≥ 120 s adentro y negoció ≥ 40 % del volumen de esa ventana "
                                "(el nivel fue aceptado como valor); después se alejó ≥ X; evento: el primer regreso.",
    "D3_RECHAZADO_AL_NACER": "En los primeros 300 s pasó ≤ 30 s adentro y ya se alejó ≥ X (el nivel se rechazó al nacer); evento: el primer "
                             "regreso.",
    "D4_MEMORIA": "Regreso tras ≥ 900 s afuera y una excursión ≥ X (¿el nivel se recuerda pasado un rato?).",
    "D5_DERIVA": "Regreso tras una excursión ≥ X/2 en el que los últimos X/2 de la aproximación tardaron ≥ 120 s (llega sin impulso).",
    "D6_PENETRACION_FALLIDA": "Tras una excursión ≥ X/2 el precio entra, penetra al menos 2 ticks y a lo sumo min(ancho/2, X/4) sin tocar el borde lejano y "
                              "vuelve a salir por el mismo lado (≥ 2 ticks) dentro de 120 s; evento en esa salida (entrada confirmada).",
}
DESFASES_S = (-2400, -1200, 1200, 2400)
MARGEN_S = 300


def visitas(t, p, v, lo, hi, salida):
    """Historia de visitas sobre arrays ya recortados a la vida del cluster (t en segundos desde la detección)."""
    dentro = (p >= lo) & (p <= hi); dist = np.maximum(np.maximum(lo - p, p - hi), 0.0)
    dt = np.diff(t, append=t[-1]); seg_dentro = np.cumsum(np.where(dentro, dt, 0.0))
    out = []; i = _primero(dentro)
    if i < 0: return out
    prev_fin = None
    while i >= 0:
        rel = _primero(dist[i:] >= salida); fin = i + rel if rel >= 0 else len(p) - 1
        reg = dict(ini=i, fin=fin, salio=rel >= 0, t_ini=float(t[i]), seg_dentro_antes=float(seg_dentro[i - 1]) if i else 0.0)
        tramo = slice(i, fin + 1)
        reg.update(seg_dentro=float(dt[tramo][dentro[tramo]].sum()), vol_dentro=float(v[tramo][dentro[tramo]].sum()))
        if rel >= 0: reg["lado_salida"] = 1 if p[fin] > hi else -1
        if prev_fin is not None:                                          # lo que pasó entre la salida anterior y este regreso
            ent = slice(prev_fin, i + 1); reg["excursion"] = float(dist[ent].max()); reg["t_afuera"] = float(t[i] - t[prev_fin])
            reg["lado_regreso"] = 1 if p[prev_fin] > hi else -1           # +1 = volvió desde arriba (el cluster es soporte)
            reg["_ent"] = (prev_fin, i)                                   # tramo afuera, para medir la aproximación
        out.append(reg)
        if rel < 0: break
        prev_fin = fin; nxt = _primero(dentro[fin + 1:]); i = fin + 1 + nxt if nxt >= 0 else -1
    return out


def _aprox_seg(t, dist, ent, umbral):
    """Segundos que tardó la aproximación desde la última vez que estuvo a `umbral` del rango hasta el toque."""
    a, b = ent; d = dist[a:b + 1]; k = np.flatnonzero(d >= umbral)
    return float(t[b] - t[a + k[-1]]) if k.size else 0.0


def eventos(t, p, v, lo, hi, X, tick):
    """{definición: (índice del evento, precio de referencia, lado)} — a lo sumo un evento por definición. `lado` = +1 si el rebote es
    hacia arriba (el cluster hace de soporte)."""
    V = visitas(t, p, v, lo, hi, X / 4); out = {}
    if not V: return out
    dist = np.maximum(np.maximum(lo - p, p - hi), 0.0); ancho = hi - lo
    ini_ok = V[0]["ini"] == 0 or t[V[0]["ini"]] <= 5.0                   # el cluster nace con el precio adentro (o a 5 s)
    # estado al nacer (primeros 300 s): sólo se usa para eventos posteriores a esa ventana
    w = t <= VENTANA_NACIMIENTO_S; dtw = np.diff(t, append=t[-1])
    dentro = (p >= lo) & (p <= hi)
    seg_in = float(dtw[w & dentro].sum()); vol_w = float(v[w].sum()); vol_in = float(v[w & dentro].sum())
    acept = ini_ok and seg_in >= 120 and vol_w > 0 and vol_in / vol_w >= 0.40
    rech = ini_ok and seg_in <= 30 and bool((dist[w] >= X).any())
    for k, r in enumerate(V):
        if k == 0: continue
        ref = (hi if r["lado_regreso"] > 0 else lo); lado = r["lado_regreso"]; i = r["ini"]
        ex, ta = r["excursion"], r["t_afuera"]
        if "D0_BASE" not in out and ex >= X / 2: out["D0_BASE"] = (i, ref, lado)
        if "D1_FRESCO_LEJANO" not in out and ex >= X and k <= 3 and r["seg_dentro_antes"] <= 600: out["D1_FRESCO_LEJANO"] = (i, ref, lado)
        if t[i] > VENTANA_NACIMIENTO_S and ex >= X:
            if acept and "D2_ACEPTADO_Y_ABANDONADO" not in out: out["D2_ACEPTADO_Y_ABANDONADO"] = (i, ref, lado)
            if rech and "D3_RECHAZADO_AL_NACER" not in out: out["D3_RECHAZADO_AL_NACER"] = (i, ref, lado)
        if "D4_MEMORIA" not in out and ex >= X and ta >= 900: out["D4_MEMORIA"] = (i, ref, lado)
        if "D5_DERIVA" not in out and ex >= X / 2 and _aprox_seg(t, dist, r["_ent"], X / 2) >= 120: out["D5_DERIVA"] = (i, ref, lado)
        if "D6_PENETRACION_FALLIDA" not in out and ex >= X / 2 and r["salio"]:
            tramo = slice(i, r["fin"] + 1); pen = float((hi - p[tramo].min()) if lado > 0 else (p[tramo].max() - lo))
            toca_lejano = bool((p[tramo] <= lo).any()) if lado > 0 else bool((p[tramo] >= hi).any())
            if (r["lado_salida"] == lado and 2 * tick <= pen <= min(ancho / 2, X / 4) and not toca_lejano and t[r["fin"]] - t[i] <= 120
                    and lado * (p[r["fin"]] - ref) >= 2 * tick):
                out["D6_PENETRACION_FALLIDA"] = (r["fin"], float(p[r["fin"]]), lado)
    return out


def _carrera(ts, px, j0, ref, lado, X):
    j1 = int(np.searchsorted(ts, ts[j0] + HORIZONTE_S * NS, side="right")); r = px[j0 + 1:j1]
    gana = _primero(lado * (r - ref) >= X); pierde = _primero(lado * (r - ref) <= -X)
    if gana < 0 and pierde < 0: return 0
    return 1 if (pierde < 0 or (0 <= gana < pierde)) else -1


def _cluster(ts, px, vol, t_ns, lo, hi, X, tick):
    i0 = int(np.searchsorted(ts, t_ns, side="right")); i1 = int(np.searchsorted(ts, t_ns + VIDA_CLUSTER_S * NS, side="right"))
    if i1 - i0 < 3: return {}
    t = (ts[i0:i1] - t_ns) / NS
    ev = eventos(t, px[i0:i1], vol[i0:i1], lo, hi, X, tick)
    return {d: (lado, _carrera(ts, px, i0 + j, ref, lado, X)) for d, (j, ref, lado) in ev.items()}


def rebotes_del_dia(inst, fecha, ts, px, vol, C: pd.DataFrame, tick, friccion) -> list:
    """Filas (definición, real/control, lado, resultado) de una sesión: clusters reales y pseudo-clusters de control."""
    X = barrera(friccion, tick); filas = []; reales = C.t_ns.to_numpy(np.int64)
    for c in C.itertuples(index=False):
        for d, (lado, res) in _cluster(ts, px, vol, int(c.t_ns), float(c.lo), float(c.hi), X, tick).items():
            filas.append(dict(inst=inst, fecha=int(fecha), definicion=d, placebo=0, lado=lado, resultado=res))
        w = float(c.hi - c.lo)
        for des in DESFASES_S:
            t2 = int(c.t_ns) + des * NS
            if t2 <= ts[0] or t2 >= ts[-1] or np.abs(reales - t2).min() < MARGEN_S * NS: continue
            k = int(np.searchsorted(ts, t2, side="right")) - 1; centro = float(px[k])
            for d, (lado, res) in _cluster(ts, px, vol, int(ts[k]), centro - w / 2, centro + w / 2, X, tick).items():
                filas.append(dict(inst=inst, fecha=int(fecha), definicion=d, placebo=1, lado=lado, resultado=res))
    return filas
