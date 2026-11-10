"""HFT-CLUSTERS-INFO (2026-11-10): ¿un cluster de zonas HFT trae información? En dos pasos, antes de cualquier P&L.

Reemplaza a la grilla `U1-HFT-CLUSTERS-GRILLA` de 20.736 celdas (dictamen:
`docs/research/hft_clusters_u1_20261110/DICTAMEN_ABOGADO_20261110.md`). Pre-registro:
`docs/research/hft_clusters_u1_20261110/PREREGISTRO_E0_E_INFORMACION.md`.

  Paso E0 (sin retornos): frecuencia, ancho, vida y estabilidad de pocas definiciones de cluster, en varios activos.
  Paso INFO (una hipótesis): tras alejarse y volver a tocar el borde del cluster, ¿el precio rebota más que en un nivel placebo
  (misma hora y mismo ancho, nivel desplazado)? Carrera simétrica a ±X desde el toque, en bruto.

Correcciones de diseño respecto de la propuesta original (errores K4–K9 de ERRORES_Y_GUARDAS):
  - la vigencia de zonas y clusters va en SEGUNDOS de reloj (se le pasa al detector el segundo como «barra»), no en barras de ticks;
  - la sesión es la CME (`trade_date` del release), nunca el día UTC;
  - la escala de volatilidad de una zona usa la barra ANTERIOR a su detección;
  - la geometría del cluster queda congelada al detectarse (`inmutable_en_detect=True`);
  - todo lo que se mide después de un cluster usa sólo ticks con `ts > t_ns`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.bridge.indicators import hftzones_nq_rangos_pct_v2 as HZ

# Definiciones (pocas, fijadas antes de mirar nada). Zona: la certificada en NT8 y una variante de volumen. Cluster: familia P.
ZONAS = {"Z_CERT": dict(max_avg_ms=25.0, min_total_volume=50.0, detect_absorb=True),
         "Z_VOL10": dict(max_avg_ms=25.0, min_total_volume=10.0, detect_absorb=True)}
CLUSTERS = {f"K4_PK{int(pk * 100):03d}_V{v}": dict(k=4, min_packing=pk, vida_zona_s=v) for pk in (0.85, 1.25) for v in (300, 900)}
# E0-b (enmienda §8.1): más zonas, ancho mínimo como fracción del stop mínimo X, sólo la zona certificada. Packing fijo 0,85.
CLUSTERS_B = {f"K{k}_A{int(a * 100):03d}_V{v}": dict(k=k, min_packing=0.85, vida_zona_s=v, ancho_min_frac=a)
              for k in (4, 6, 8, 12, 16) for a in (0.0, 0.25, 0.5, 1.0) for v in (900, 1800)}
VIDA_CLUSTER_S = 1800                                     # un cluster puede dar un toque hasta 30 min después de detectarse
HORIZONTE_S = 3600                                        # la carrera tras el toque dura a lo sumo 60 min (o el fin de la sesión)
FRICCION_R_MAX = 0.08                                     # palanca F-STOP-GRANDE-FRENTE-A-FRICCION
DESPLAZAMIENTOS = (-3.0, -1.5, 1.5, 3.0)                  # placebo: nivel corrido en múltiplos de X


def barrera(friccion_pts: float, tick: float) -> float:
    """X de la carrera = stop mínimo para que la fricción no pase de 0,08 R, redondeado al tick (NQ 19,5 pts; ES 11,25; GC 7,6)."""
    return float(np.ceil(friccion_pts / FRICCION_R_MAX / tick) * tick)


def clusters_del_dia(ts_ns, px, vol, sesion, tick: float, zonas=None, clusters=None, X: float = 0.0) -> dict:
    """{(zona, cluster): DataFrame[t_ns, lo, hi, n_zonas, packing, width_ticks]} de un bloque de ticks de UNA sesión CME."""
    pt = np.round(np.asarray(px, float) / tick).astype(np.int64); ts = np.asarray(ts_ns, np.int64)
    ses = np.asarray(sesion, np.int64); v = np.asarray(vol, float)
    bar_ts, bar_hi, bar_lo, _, _, barra_de_tick = HZ.construir_barras_ticks(ts, pt, ses, ticks_per_bar=5, tick_size=tick)
    esc = np.full(len(bar_hi) + 1, 24.0); e = 24.0                       # esc[b] = escala conocida AL ABRIR la barra b (usa hasta b-1)
    for b in range(len(bar_hi)):
        r = (bar_hi[b] - bar_lo[b]) / tick
        if r > 0: e = 0.98 * e + 0.02 * max(16.0, r * 2.5)
        esc[b + 1] = e
    ci, cf = HZ.detectar_candidatos_nb(ts, pt, v, ses, barra_de_tick, max_pausa_ms=100.0, retro_floor_ticks=2.0, retro_pct_height=50.0,
                                       has_prev_session_close=False, prev_session_close_ticks=0)
    out = {}
    for zk, z in (zonas or ZONAS).items():
        acc, buckets, _ = HZ.filtrar_zonas_nb(ci, cf, max_avg_ms=z["max_avg_ms"], min_total_volume=z["min_total_volume"], detect_absorb=z["detect_absorb"])
        if not len(acc): continue
        zi, zf = ci[acc], cf[acc]
        seg = zi[:, 5] // 1_000_000_000                                   # reloj: segundo de disponibilidad de la zona
        escala = esc[np.clip(zi[:, 17], 0, len(esc) - 1)]
        for ck, c in (clusters or CLUSTERS).items():
            ki, kf = HZ.evaluar_clusters_causales_nb(seg, zi[:, 5], zi[:, 11], zi[:, 10], zf[:, 3], zi[:, 7], buckets, ses[zi[:, 2]], escala,
                                                     tick_size=tick, mostrar_absorb=z["detect_absorb"], extension_dibujo=c["vida_zona_s"],
                                                     pct_extension_bars=VIDA_CLUSTER_S, min_zonas_cluster=c["k"], min_packing=c["min_packing"],
                                                     modo_compresion=HZ.MODO_PACKING_PURO, inmutable_en_detect=True)
            if len(ki) and c.get("ancho_min_frac", 0.0) > 0:               # ancho mínimo (post-detección: ver límite en el pre-registro §8.2)
                ok = kf[:, 3] * tick >= c["ancho_min_frac"] * X - 1e-9; ki, kf = ki[ok], kf[ok]
            if len(ki):
                out[(zk, ck)] = pd.DataFrame(dict(t_ns=ki[:, 2], lo=kf[:, 0], hi=kf[:, 1], n_zonas=ki[:, 3], packing=kf[:, 4], width_ticks=kf[:, 3]))
    return out


def e0_fila(inst, fecha, zk, ck, C, tick, friccion) -> dict:
    """Métricas sin retornos de una (sesión, definición). `C` None o vacío = sesión sin clusters (n = 0)."""
    if C is None or not len(C): return dict(inst=inst, fecha=int(fecha), zona=zk, cluster=ck, n=0)
    w = C.width_ticks.to_numpy(float) * tick; X = barrera(friccion, tick)
    return dict(inst=inst, fecha=int(fecha), zona=zk, cluster=ck, n=int(len(C)), ancho_pts_med=float(np.median(w)), n_zonas_med=float(C.n_zonas.median()),
                packing_med=float(C.packing.median()), frac_ancho_menor_X=float((w < X).mean()), friccion_r_stop_ancho=float(np.median(friccion / np.maximum(w, tick))))


def _primero(cond: np.ndarray) -> int:
    i = int(np.argmax(cond)); return i if cond.size and cond[i] else -1


def carrera(ts, px, t_ns: int, lo: float, hi: float, sep: float, X: float):
    """Tras `t_ns`: espera que el precio se aleje `sep` del cluster, después el primer toque del borde cercano (dentro de la vida del
    cluster) y corre una carrera simétrica a ±X desde ese borde. Devuelve (lado, resultado) con resultado +1 = rebote, −1 = atravesó,
    0 = sin definir en el horizonte; None si no hubo alejamiento o toque. Sólo usa ticks posteriores a `t_ns`."""
    i0 = int(np.searchsorted(ts, t_ns, side="right"))
    fin_vida = int(np.searchsorted(ts, t_ns + VIDA_CLUSTER_S * 1_000_000_000, side="right"))
    p = px[i0:fin_vida]
    if p.size < 3: return None
    a = _primero((p >= hi + sep) | (p <= lo - sep))
    if a < 0: return None
    arriba = p[a] >= hi + sep; borde = hi if arriba else lo                 # salió por arriba → el cluster es soporte, se toca `hi`
    q = p[a + 1:]; t = _primero(q <= borde) if arriba else _primero(q >= borde)
    if t < 0: return None
    j0 = i0 + a + 1 + t
    j1 = int(np.searchsorted(ts, ts[j0] + HORIZONTE_S * 1_000_000_000, side="right"))
    r = px[j0 + 1:j1]; d = 1.0 if arriba else -1.0                           # d = sentido del rebote
    gana = _primero(d * (r - borde) >= X); pierde = _primero(d * (r - borde) <= -X)
    if gana < 0 and pierde < 0: res = 0
    elif pierde < 0 or (0 <= gana < pierde): res = 1
    else: res = -1
    return (1 if arriba else -1), res


def iman(ts, px, t_ns: int, lo: float, hi: float, sep: float):
    """¿El cluster atrae? Tras `t_ns` el precio se aleja `sep` del rango; desde ese punto, a distancia d del borde cercano, se corre
    una carrera: +1 si vuelve a tocar el borde antes de alejarse otra d (nivel espejo), −1 si llega antes al espejo, 0 si ninguna en
    el horizonte. Bajo paseo al azar es 50/50. None si no hubo alejamiento. Sólo ticks posteriores a `t_ns`."""
    i0 = int(np.searchsorted(ts, t_ns, side="right"))
    fin_vida = int(np.searchsorted(ts, t_ns + VIDA_CLUSTER_S * 1_000_000_000, side="right"))
    p = px[i0:fin_vida]
    if p.size < 3: return None
    a = _primero((p >= hi + sep) | (p <= lo - sep))
    if a < 0: return None
    arriba = p[a] >= hi + sep; borde = hi if arriba else lo; d = abs(p[a] - borde); espejo = p[a] + (d if arriba else -d)
    j0 = i0 + a; j1 = int(np.searchsorted(ts, ts[j0] + HORIZONTE_S * 1_000_000_000, side="right")); r = px[j0 + 1:j1]
    toca = _primero(r <= borde) if arriba else _primero(r >= borde)
    huye = _primero(r >= espejo) if arriba else _primero(r <= espejo)
    if toca < 0 and huye < 0: res = 0
    elif huye < 0 or (0 <= toca < huye): res = 1
    else: res = -1
    return (1 if arriba else -1), res


DESFASES_S = (-2400, -1200, 1200, 2400)                   # placebo temporal del imán: mismo ancho, centrado en el precio de otra hora
MARGEN_S = 600                                            # el placebo temporal no puede caer a menos de 10 min de un cluster real


def iman_del_dia(inst, fecha, ts, px, C: pd.DataFrame, tick, friccion) -> list:
    """Carrera de imán para cada cluster real y para pseudo-clusters de control: mismo ancho, misma sesión, centrados en el precio que
    había 20 y 40 minutos antes y después (lejos de todo cluster real). El control tiene la MISMA condición que el real (el precio
    parte del nivel y se aleja `sep`), que es lo que faltaba en la «carrera contra el espejo» de BigTrap2."""
    X = barrera(friccion, tick); sep = X / 2; filas = []; reales = C.t_ns.to_numpy(np.int64)
    for c in C.itertuples(index=False):
        r = iman(ts, px, int(c.t_ns), c.lo, c.hi, sep)
        if r is not None: filas.append(dict(inst=inst, fecha=int(fecha), t_ns=int(c.t_ns), placebo=0, desplazamiento=0.0, lado=r[0], resultado=r[1]))
        w = float(c.hi - c.lo)
        for des in DESFASES_S:
            t2 = int(c.t_ns) + des * 1_000_000_000
            if t2 <= ts[0] or t2 >= ts[-1] or np.abs(reales - t2).min() < MARGEN_S * 1_000_000_000: continue
            k = int(np.searchsorted(ts, t2, side="right")) - 1; centro = float(px[k])
            r = iman(ts, px, int(ts[k]), centro - w / 2, centro + w / 2, sep)
            if r is not None: filas.append(dict(inst=inst, fecha=int(fecha), t_ns=int(ts[k]), placebo=1, desplazamiento=float(des), lado=r[0], resultado=r[1]))
    return filas


def info_del_dia(inst, fecha, ts, px, C: pd.DataFrame, tick, friccion) -> list:
    """Carreras reales y placebo de los clusters de una sesión. El placebo conserva hora y ancho y corre el nivel ±1,5X y ±3X."""
    X = barrera(friccion, tick); sep = X / 2; filas = []
    for c in C.itertuples(index=False):
        for k, mult in enumerate((0.0,) + DESPLAZAMIENTOS):
            r = carrera(ts, px, int(c.t_ns), c.lo + mult * X, c.hi + mult * X, sep, X)
            if r is not None:
                filas.append(dict(inst=inst, fecha=int(fecha), t_ns=int(c.t_ns), placebo=int(k > 0), desplazamiento=mult, lado=r[0], resultado=r[1]))
    return filas


def contraste(F: pd.DataFrame, n_boot: int = 20000, semilla: int = 20261110) -> dict:
    """Diferencia (real − placebo) del resultado medio de la carrera, bootstrap por sesión, p unilateral (H1: real > placebo)."""
    if not len(F): return dict(n_real=0, n_placebo=0)
    claves = [c for c in ("inst", "fecha") if c in F.columns]            # sesión = (activo, fecha): dos activos el mismo día son dos sesiones
    g = F.groupby(claves + ["placebo"]).resultado.agg(["sum", "count"]).unstack(fill_value=0)
    sr, nr, sp, n_p = (g[("sum", 0)].to_numpy(float), g[("count", 0)].to_numpy(float), g[("sum", 1)].to_numpy(float), g[("count", 1)].to_numpy(float)) \
        if (("sum", 0) in g and ("sum", 1) in g) else (None,) * 4
    if sr is None or nr.sum() == 0 or n_p.sum() == 0: return dict(n_real=int(0 if sr is None else nr.sum()), n_placebo=int(0 if sr is None else n_p.sum()))
    dif = lambda i: sr[i].sum() / max(nr[i].sum(), 1) - sp[i].sum() / max(n_p[i].sum(), 1)
    rng = np.random.default_rng(semilla); n = len(sr); obs = dif(np.arange(n))
    b = np.array([dif(rng.integers(0, n, n)) for _ in range(n_boot)])
    return dict(n_real=int(nr.sum()), n_placebo=int(n_p.sum()), sesiones=int(n), media_real=float(sr.sum() / nr.sum()), media_placebo=float(sp.sum() / n_p.sum()),
                diferencia=float(obs), ic90=[float(np.quantile(b, 0.05)), float(np.quantile(b, 0.95))], p_unilateral=float((b <= 0).mean()),
                se=float(b.std()), mde80=float(2.49 * b.std()))


def elegir_definicion(E0: pd.DataFrame) -> dict:
    """Regla MECÁNICA y sin retornos para elegir UNA definición por activo (declarada en el pre-registro). `E0` trae una fila por
    (sesión, definición), con n = 0 si no hubo clusters. Elegibles: al menos 0,5 clusters por sesión y CV ≤ 0,5 de la media mensual
    (con 3 meses o más). Entre las elegibles, la más cercana a 2 clusters por sesión. Sin elegibles, el activo no entra al paso INFO."""
    out = {}
    for inst, g in E0.groupby("inst"):
        cand = []
        for (zk, ck), h in g.groupby(["zona", "cluster"]):
            por_ses = float(h.n.mean()); m = h.assign(mes=h.fecha // 100).groupby("mes").n.mean()
            cv = float(m.std() / m.mean()) if len(m) >= 3 and m.mean() > 0 else 9.0
            if por_ses >= 0.5 and cv <= 0.5: cand.append((abs(por_ses - 2.0), zk, ck, por_ses, cv))
        if cand:
            _, zk, ck, ps, cv = sorted(cand)[0]; out[inst] = dict(zona=zk, cluster=ck, clusters_por_sesion=ps, cv=cv)
    return out


def elegir_equilibrio(E0: pd.DataFrame, friccion: dict) -> dict:
    """Enmienda §8.1: por activo, la definición estable (CV mensual ≤ 0,5) que minimiza `2,49/√N + fricción / ancho mediano`
    (borde bruto a la vez detectable y rentable). Devuelve la elegida y la tabla completa, sin mirar retornos."""
    out = {}
    for inst, g in E0.groupby("inst"):
        tabla = []
        for (zk, ck), h in g.groupby(["zona", "cluster"]):
            N = float(h.n.sum()); m = h.assign(mes=h.fecha // 100).groupby("mes").n.mean()
            cv = float(m.std() / m.mean()) if len(m) >= 3 and m.mean() > 0 else 9.0
            ancho = float(h.ancho_pts_med.median()) if "ancho_pts_med" in h and h.ancho_pts_med.notna().any() else float("nan")
            if N < 1 or not ancho > 0: continue
            fr = friccion[inst] / ancho
            tabla.append(dict(zona=zk, cluster=ck, eventos=int(N), por_sesion=float(h.n.mean()), ancho_pts=ancho, cv=cv, mde=2.49 / N ** 0.5,
                              friccion_r=fr, borde_detectable=2.49 / N ** 0.5 + fr, elegible=bool(cv <= 0.5)))
        tabla.sort(key=lambda r: r["borde_detectable"])
        el = next((r for r in tabla if r["elegible"]), None)
        out[inst] = dict(elegida=el, tabla=tabla)
    return out
