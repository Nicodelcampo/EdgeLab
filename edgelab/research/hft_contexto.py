"""HFT-CONTEXTO (2026-11-10): ¿el rebote en un cluster depende de cuántos otros clusters hay, dónde están y qué edad tienen?

Pre-registro: `docs/research/hft_clusters_u1_20261110/PREREGISTRO_CONTEXTO.md`. Usa los eventos de UNA definición de rebote
(`hft_rebotes`), elegida con la regla escrita en el pre-registro, y les agrega el contexto en el instante del evento. Sólo cuentan
clusters YA detectados y todavía vivos (vida 1.800 s); el tocado no cuenta como vecino. Distancias en unidades de X y con signo en
el sentido del rebote: y > 0 = en el camino del rebote, y < 0 = detrás del borde tocado.

Variables (todas causales):
  respaldo     clusters vivos que cortan la franja y ∈ [−1, 0]        → 0 | 1 | ≥ 2
  obstaculo    el más cercano con borde en y ∈ (0, 1]                 → ninguno | cerca (≤ 0,5) | lejos (0,5–1]
  densidad     clusters vivos que cortan y ∈ [−2, 2]                  → 0 | 1–2 | ≥ 3
  confluencia  otro cluster vivo se solapa con el rango del tocado    → no | sí
  mas_nuevo    el tocado es el más nuevo de los de y ∈ [−2, 2]        → no | sí | (sin vecinos: fuera)
  huella       clusters detectados mientras el precio estaba afuera   → 0 | ≥ 1
Contrastes (estratos extremos, fijados antes): ver `CONTRASTES`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import hft_rebotes as RB
from edgelab.research.hft_clusters_info import VIDA_CLUSTER_S, barrera

NS = 1_000_000_000
CONTRASTES = {  # variable: (estrato A, estrato B, signo esperado de A − B; 0 = sin dirección declarada)
    "respaldo": ("≥2", "0", +1),
    "obstaculo": ("cerca", "ninguno", -1),
    "densidad": ("0", "≥3", 0),
    "confluencia": ("sí", "no", +1),
    "mas_nuevo": ("sí", "no", +1),
    "huella": ("0", "≥1", 0),
}
MIN_POR_ESTRATO = 150                     # compuerta de potencia (conteos, sin retornos): menos → la variable no se prueba


def contexto(C: pd.DataFrame, k_tocado, t_ev: int, t_sal: int, ref: float, lado: int, X: float, banda=None) -> dict:
    """`k_tocado` = fila del cluster tocado en C (real) o None (pseudo-cluster de control, con su `banda` = (lo, hi, t_ns))."""
    t = C.t_ns.to_numpy(np.int64); lo = C.lo.to_numpy(float); hi = C.hi.to_numpy(float)
    vivo = (t < t_ev) & (t + VIDA_CLUSTER_S * NS > t_ev)
    if k_tocado is not None: vivo[k_tocado] = False; b_lo, b_hi, b_t = lo[k_tocado], hi[k_tocado], t[k_tocado]
    else: b_lo, b_hi, b_t = banda
    y1, y2 = lado * (lo - ref) / X, lado * (hi - ref) / X; ylo, yhi = np.minimum(y1, y2), np.maximum(y1, y2)
    corta = lambda a, b: vivo & (yhi >= a) & (ylo <= b)
    n_resp = int(corta(-1.0, 0.0).sum()); n_dens = int(corta(-2.0, 2.0).sum())
    adelante = vivo & (ylo > 0) & (ylo <= 1.0); obst = float(ylo[adelante].min()) if adelante.any() else np.nan
    conf = bool((vivo & (lo <= b_hi) & (hi >= b_lo)).any())
    vec = corta(-2.0, 2.0)
    nuevo = None if not vec.any() else bool(b_t > t[vec].max())
    huella = int(((t > t_sal) & (t < t_ev)).sum())
    return dict(respaldo="0" if n_resp == 0 else ("1" if n_resp == 1 else "≥2"), n_respaldo=n_resp,
                obstaculo="ninguno" if np.isnan(obst) else ("cerca" if obst <= 0.5 else "lejos"), dist_obstaculo=obst,
                densidad="0" if n_dens == 0 else ("1-2" if n_dens <= 2 else "≥3"), n_densidad=n_dens,
                confluencia="sí" if conf else "no", mas_nuevo=None if nuevo is None else ("sí" if nuevo else "no"),
                huella="0" if huella == 0 else "≥1", n_huella=huella, edad_tocado_s=float((t_ev - b_t) / NS))


def _evento(ts, px, vol, t0, lo, hi, X, tick, definicion):
    i0 = int(np.searchsorted(ts, t0, side="right")); i1 = int(np.searchsorted(ts, t0 + VIDA_CLUSTER_S * NS, side="right"))
    if i1 - i0 < 3: return None
    ev = RB.eventos((ts[i0:i1] - t0) / NS, px[i0:i1], vol[i0:i1], lo, hi, X, tick).get(definicion)
    if ev is None: return None
    j, ref, lado, j_sal = ev
    return int(ts[i0 + j]), int(ts[i0 + j_sal]), ref, lado, RB._carrera(ts, px, i0 + j, ref, lado, X)


def contexto_del_dia(inst, fecha, ts, px, vol, C: pd.DataFrame, tick, friccion, definicion: str) -> list:
    """Una fila por evento de `definicion`: los REALES (placebo = 0) y los de los pseudo-clusters de control (placebo = 1, mismas reglas
    de ubicación que `hft_rebotes`), cada uno con su desenlace y su contexto respecto de los clusters reales vivos en ese instante."""
    X = barrera(friccion, tick); filas = []; C = C.reset_index(drop=True); reales = C.t_ns.to_numpy(np.int64)
    r_lo, r_hi = C.lo.to_numpy(float), C.hi.to_numpy(float)
    for k, c in enumerate(C.itertuples(index=False)):
        e = _evento(ts, px, vol, int(c.t_ns), float(c.lo), float(c.hi), X, tick, definicion)
        if e is not None:
            t_ev, t_sal, ref, lado, res = e
            filas.append(dict(inst=inst, fecha=int(fecha), definicion=definicion, placebo=0, lado=lado, resultado=res,
                              **contexto(C, k, t_ev, t_sal, ref, lado, X)))
        w = float(c.hi - c.lo)
        for des in RB.DESFASES_S:                                          # control: misma regla de ubicación que hft_rebotes
            t2 = int(c.t_ns) + des * NS
            if t2 <= ts[0] or t2 >= ts[-1] or np.abs(reales - t2).min() < RB.MARGEN_S * NS: continue
            kk = int(np.searchsorted(ts, t2, side="right")) - 1; centro = float(px[kk]); plo, phi = centro - w / 2, centro + w / 2
            vivo = (reales < t2 + VIDA_CLUSTER_S * NS) & (reales + VIDA_CLUSTER_S * NS > t2)
            if (vivo & (r_lo <= phi + X / 4) & (plo - X / 4 <= r_hi)).any(): continue
            e = _evento(ts, px, vol, int(ts[kk]), plo, phi, X, tick, definicion)
            if e is not None:
                t_ev, t_sal, ref, lado, res = e
                filas.append(dict(inst=inst, fecha=int(fecha), definicion=definicion, placebo=1, lado=lado, resultado=res,
                                  **contexto(C, None, t_ev, t_sal, ref, lado, X, banda=(plo, phi, int(ts[kk])))))
    return filas


def analizar(T: pd.DataFrame, n_boot: int = 20000) -> dict:
    """Por variable: conteos por estrato (compuerta), y si pasa, contraste A − B del desenlace (bootstrap por sesión, p a dos colas
    salvo que el pre-registro declare signo, en cuyo caso se informa también la de una cola). BH q 0,10 entre las que se prueban."""
    from edgelab.research.hft_clusters_info import contraste
    out = {}; T_ctrl = T[T.placebo == 1] if "placebo" in T else T.iloc[:0]; T = T[T.placebo == 0] if "placebo" in T else T
    for var, (a, b, signo) in CONTRASTES.items():
        cnt = {str(k): int(v) for k, v in T[var].value_counts(dropna=True).items()} if var in T else {}
        r = dict(conteos=cnt, estratos=[a, b], signo_esperado=signo)
        na, nb = cnt.get(a, 0), cnt.get(b, 0)
        if min(na, nb) < MIN_POR_ESTRATO: r["estado"] = f"SIN_POTENCIA (A {na}, B {nb} < {MIN_POR_ESTRATO})"; out[var] = r; continue
        S = T[T[var].isin([a, b])].assign(placebo=lambda d: (d[var] == b).astype(int))       # A como «real», B como «control»
        c = contraste(S, n_boot=n_boot); p1 = c.get("p_unilateral", 1.0)
        c["p_dos_colas"] = float(min(1.0, 2 * min(p1, 1 - p1)))
        c["p_declarada"] = float(p1 if signo > 0 else (1 - p1) if signo < 0 else c["p_dos_colas"])
        r.update(c, estado="PROBADA")
        # Diagnóstico (no entra al BH): el mismo contraste en los pseudo-clusters de control. Si el control muestra el mismo efecto,
        # lo que se mide es la estructura del precio alrededor (hora, volatilidad, tendencia), no el cluster vecino.
        Sc = T_ctrl[T_ctrl[var].isin([a, b])].assign(placebo=lambda d: (d[var] == b).astype(int)) if var in T_ctrl else T_ctrl
        if len(Sc) and Sc.placebo.nunique() == 2:
            cc = contraste(Sc, n_boot=n_boot); r["control"] = dict(n=int(len(Sc)), diferencia=cc.get("diferencia"), ic90=cc.get("ic90"))
            if cc.get("diferencia") is not None: r["dif_en_dif"] = float(c["diferencia"] - cc["diferencia"])
        out[var] = r
    ps = sorted((v["p_declarada"], k) for k, v in out.items() if v.get("estado") == "PROBADA"); m = len(ps)
    kmax = max([i + 1 for i, (p, _) in enumerate(ps) if p <= 0.10 * (i + 1) / max(m, 1)] or [0])
    return dict(variables=out, probadas=m, nominadas_bh_q010=[k for _, k in ps[:kmax]])


def elegir_definicion(res_rebotes: dict) -> str:
    """Regla escrita en el pre-registro: entre las definiciones nominadas por BH en HFT-REBOTES, la de más eventos reales; si no hay
    nominadas, D0_BASE (la de más eventos por construcción)."""
    nom = res_rebotes.get("nominadas_bh_q010") or []
    if not nom: return "D0_BASE"
    n = lambda d: (res_rebotes["por_definicion"][d].get("conjunto") or {}).get("n_real", 0)
    return max(nom, key=n)
