"""ZONAS-GAPS (2026-10-25): traducción exhaustiva a Python/Numba de `ZonasDeGaps.cs` (50T y M1) y cruce con la mecánica U1.

Pedido de Nico (2026-10-25): «Te parece que vale la pena traducir este a python para correr analisis en edgelab? lo estuve
probando en el nq 50t… me interesa sobre todo la idea del gap… Quiero medir todo, absolutamente todo. Asi que encargate de todo
y primero lee todo el repositorio». Spec: docs/research/zonas_gaps_20261025/SPEC_ZONAS_GAPS.md.

Qué mide este módulo (sin omitir ninguna variante física ni operativa de `ZonasDeGaps.cs`):
  1. ESCALA DE BARRA (`escala`, 2 niveles):
     - `0 = 50T`: barras exactas de 50 ticks reconstruidas causalmente desde los ticks crudos (`ctx["tpx"]`, `ctx["tstart"]`)
       dentro de cada sesión. Cada barra 50T que cierra durante la vela M1 `k` queda disponible en `k` sin ningún look-ahead.
     - `1 = M1`: velas de 1 minuto (`ctx["o"]`, `ctx["h"]`, `ctx["l"]`, `ctx["c"]`).
  2. CONFIRMACIÓN DEL GAP EN CREACIÓN (`confirmado`, 2 niveles — corrección del Bug 2 de C#):
     - `0 = BRUTO (ZonasDeGaps.cs original)`: gap entre barras (`|Open[b] - Close[b-1]| >= MinGapTicks * tick`) o salto
       intrabarra sin filtrar si la mecha posterior de la propia barra creadora lo rellenó.
     - `1 = VACÍO CONFIRMADO (Bug 2 corregido)`: exige que al cierre de la barra creadora (50T o M1) el hueco permanezca
       efectivamente abierto (sin ser rellenado por los ticks posteriores de la barra creadora) con al menos `MinGapTicks`.
  3. OBJETO ESTRUCTURAL (`objeto`, 2 niveles — corrección del Bug 1 de C#):
     - `0 = GAP INDIVIDUAL (GapZone)`: cada gap vivo actúa como zona de soporte/resistencia o imán con memoria hasta
       agotar su opacidad (`InitialGapOpacity = 0.70`, `OpacityDropPerTouch = 0.15`) o vencer.
     - `1 = CLUSTER COMPACTO (ClusterZone, Bug 1 corregido)`: racimo de `>= 3` gaps vivos dentro de `ClusterHeightTicks`
       donde el espacio libre interno entre gaps consecutivos es `<= MaxGapFreeSpaceTicksInCluster`. A diferencia del C#
       original (que sólo guardaba un único `bestStart..bestEnd` global en todo el gráfico), mantiene TODOS los clusters
       compactos disjuntos activos simultáneamente.
  4. MECÁNICA DE DISPARO (`mecanica`, 3 niveles — corrección del Bug 3 de C# + cruce con U1):
     - `0 = TOQUE_RETEST (ZonasDeGaps.cs nativo con Bug 3 corregido)`: tras crearse la zona, el precio debe alejarse primero
       al menos `AwayDistanceTicks` en barras estrictamente posteriores a la creación (`IsPriceAway = True`) y luego regresar
       a tocar `[lo, hi]`. `FAVOR` opera el rebote/rechazo hacia el extremo previo `E`; `CONTRA` opera el cruce/ruptura.
     - `1 = GIRO_IMAN (Giro temprano hacia la zona)`: tras una excursión amplia `A >= 4·H_eff`, el precio gira desde el extremo
       `E` y recorre el primer 35 % del camino de regreso hacia la zona (`D <= 0.65·A`). `FAVOR` opera hacia la zona (imán);
       `CONTRA` opera la continuación hacia `E`.
     - `2 = IMAN_U1 (Aproximación 75 % estilo U1)`: tras una excursión amplia `A >= 4·H_eff`, el precio completa el 75 % del
       regreso hacia la zona (`D <= 0.25·A`, umbral exacto de U1). `FAVOR` opera hacia el borde lejano de la zona; `CONTRA`
       opera el rechazo antes de entrar a la zona.
  5. VIRGINIDAD Y MICROESTRUCTURA (`virginidad`, `alejamiento`, `tamano`, `actividad`, `vwap` y régimen `hora`):
     - `virginidad`: `0` = primer contacto virgen (0 toques previos, nunca atravesada); `1` = segundo contacto (1 toque previo
       con opacidad `0.55`); `2` = zona re-testeada (2+ toques previos o flip S/R ya atravesado).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.agente.regimen import VARIABLES_REGIMEN, agregar
from edgelab.research.grilla_generica import Variable

try:
    from numba import njit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "ZONAS-GAPS"
INDICADORES = ["ZONAS-GAPS"]

# --- Parámetros físicos de ZonasDeGaps.cs y U1 ------------------------------------------------------------------------------
N_TICKS_50T = 50                # barras de 50 ticks (ZonasDeGaps.cs usado en NQ 50T)
MIN_GAP_TICKS = 4               # umbral base de gap significativo (en ticks)
AWAY_DISTANCE_TICKS = 10        # AwayDistanceTicks = 10 en ZonasDeGaps.cs
MIN_GAPS_CLUSTER = 3            # MinGapsForCluster >= 3 (ZonasDeGaps / U1)
CLUSTER_HEIGHT_TICKS = 160      # altura máxima del cluster en ticks (40 pts en NQ = 160 ticks)
MAX_FREE_SPACE_TICKS = 32       # MaxGapFreeSpaceTicksInCluster: espacio libre interno máximo entre gaps vecinos del cluster
VIDA_MAX_M1 = 500               # vida máxima en minutos (como LUXIMB / U1) para acotar memoria histórica
DEDUP_PTS = 4.0                 # distancia mínima en puntos para no duplicar zonas idénticas nacidas en la misma ráfaga
AH_IMAN_MIN = 4.0               # excursión mínima A / H_eff para activar las mecánicas de imán (GIRO_IMAN e IMAN_U1)
X_GIRO, X_U1 = 0.65, 0.25       # fracción restante D/A al girar desde el extremo (0.65) y al aproximarse estilo U1 (0.25)
MAX_CICLOS_ZONA = 3             # 3 niveles de virginidad (0 = virgen, 1 = 2do toque, 2 = 3er+ toque / flip S/R)

VARIABLES = [
    Variable("escala", "esc", "grupo", categoria=2),               # 0: 50T · 1: M1
    Variable("confirmado", "conf", "grupo", categoria=2),          # 0: bruto C# · 1: vacío sin rellenar al cierre (Bug 2 fix)
    Variable("objeto", "obj", "grupo", categoria=2),               # 0: gap individual · 1: cluster compacto multi-zona (Bug 1 fix)
    Variable("mecanica", "mec", "grupo", categoria=3),             # 0: TOQUE_RETEST · 1: GIRO_IMAN · 2: IMAN_U1
    Variable("virginidad", "virg", "eq_any", categoria=3),         # 0: virgen (0 toques) · 1: 1 toque · 2: >=2 toques o flip S/R
    Variable("alejamiento", "alej", "extremos", cuantiles=3),      # excursión previa A / H_eff (terciles causales)
    Variable("tamano", "tam", "extremos", cuantiles=3),            # altura H de la zona / ATR(14) causal (terciles causales)
    Variable("actividad", "vrel", "extremos", cuantiles=3),        # volumen por vela del ciclo / media de la sesión previa
    Variable("vwap", "vwap_al", "eq_any", categoria=2),            # 0: en contra del VWAP de la sesión · 1: a favor del VWAP
    VARIABLES_REGIMEN["hora"],                                     # bloque UTC fijo (0 Asia, 1 Europa, 2 NY, 3 cierre)
]
EJES_ORDINALES = (4,)

# --- Matriz de Ejecuciones: 2 lados × 3 entradas × 4 perfiles (TP, SL, BE) = 24 ejecuciones (933.120 celdas totales) --------
ENTRADAS = ("CIERRE", "SIG", "LIM15")
LIM_FRAC = 0.15
PERFILES_SALIDA = (
    (0.5, 0.25, 0),   # objetivo parcial (mitad del recorrido) con stop corto (2:1 R:R)
    (1.0, 0.25, 0),   # objetivo completo (ancla estructural pa) con stop corto (4:1 R:R), sin BE
    (1.0, 0.25, 1),   # objetivo completo con stop corto y Break-Even armado en +1R (0.25·D)
    (1.5, 0.50, 0),   # objetivo extendido (1.5·D) con stop estructural amplio (3:1 R:R)
)

EJECUCIONES = [(lado, en, tp, sl, be) for lado in ("FAVOR", "CONTRA") for en in ENTRADAS for tp, sl, be in PERFILES_SALIDA]

BASE_EJ = ("FAVOR", "SIG", 1.0, 0.25, 0)
BASE = {
    "escala": 0,
    "confirmado": 1,
    "objeto": 1,
    "mecanica": 0,
    "ejecución": EJECUCIONES.index(BASE_EJ),
}


# -------------------------------------------------------------------------------- 1. Extracción causal de Gaps en 50T y M1
def _gaps_50t_sesion(tpx: np.ndarray, tstart_ses: np.ndarray, a_m1: int, tick: float, min_gap_ticks: int = MIN_GAP_TICKS):
    """Construye barras exactas de 50 ticks dentro de una sesión y extrae los gaps (confirmado=0 bruto y confirmado=1 vacío
    sin rellenar al cierre de la barra de 50 ticks). Devuelve arreglos `(k_m1, zlo, zhi, conf)`."""
    s0, s1 = int(tstart_ses[0]), int(tstart_ses[-1])
    n50 = (s1 - s0) // N_TICKS_50T
    if n50 <= 1:
        z0 = np.zeros(0, np.int64); f0 = np.zeros(0, float)
        return z0, f0, f0, z0
    arr = tpx[s0 : s0 + n50 * N_TICKS_50T].reshape(n50, N_TICKS_50T)
    idx_last = s0 + np.arange(1, n50 + 1, dtype=np.int64) * N_TICKS_50T - 1
    km1 = np.searchsorted(tstart_ses, idx_last, side="right") - 1 + a_m1

    min_g = min_gap_ticks * tick - 1e-9
    o50 = arr[:, 0]; c50 = arr[:, -1]

    k_out, lo_out, hi_out, cf_out = [], [], [], []

    # A) Gaps entre barras 50T consecutivas (|Open[b] - Close[b-1]| >= min_g, definición literal de ZonasDeGaps.cs)
    diff_oc = o50[1:] - c50[:-1]
    idx_oc = np.flatnonzero(np.abs(diff_oc) >= min_g) + 1
    for b in idx_oc:
        p0, p1 = float(c50[b - 1]), float(o50[b])
        zlo_r, zhi_r = (p0, p1) if p1 > p0 else (p1, p0)
        k_out.append(int(km1[b])); lo_out.append(zlo_r); hi_out.append(zhi_r); cf_out.append(0)
        if p1 > p0:
            hi_c = float(min(p1, arr[b, 1:].min()))
            if hi_c - p0 >= min_g:
                k_out.append(int(km1[b])); lo_out.append(p0); hi_out.append(hi_c); cf_out.append(1)
        else:
            lo_c = float(max(p1, arr[b, 1:].max()))
            if p0 - lo_c >= min_g:
                k_out.append(int(km1[b])); lo_out.append(lo_c); hi_out.append(p0); cf_out.append(1)

    # B) Saltos tick-a-tick dentro de cada barra 50T (invariante a la fase del múltiplo de 50 ticks)
    jumps = np.diff(arr, axis=1)
    max_abs_j = np.abs(jumps).max(axis=1)
    idx_jb = np.flatnonzero(max_abs_j >= min_g)
    for b in idx_jb:
        row_j = jumps[b]
        m = int(np.argmax(np.abs(row_j)))
        p0, p1 = float(arr[b, m]), float(arr[b, m + 1])
        zlo_r, zhi_r = (p0, p1) if p1 > p0 else (p1, p0)
        k_out.append(int(km1[b])); lo_out.append(zlo_r); hi_out.append(zhi_r); cf_out.append(0)
        if p1 > p0:
            lo_c = float(max(p0, arr[b, : m + 1].max()))
            hi_c = float(min(p1, arr[b, m + 1 :].min()))
            if hi_c - lo_c >= min_g:
                k_out.append(int(km1[b])); lo_out.append(lo_c); hi_out.append(hi_c); cf_out.append(1)
        else:
            hi_c = float(min(p0, arr[b, : m + 1].min()))
            lo_c = float(max(p1, arr[b, m + 1 :].max()))
            if hi_c - lo_c >= min_g:
                k_out.append(int(km1[b])); lo_out.append(lo_c); hi_out.append(hi_c); cf_out.append(1)

    if not k_out:
        z0 = np.zeros(0, np.int64); f0 = np.zeros(0, float)
        return z0, f0, f0, z0
    return np.array(k_out, np.int64), np.array(lo_out, float), np.array(hi_out, float), np.array(cf_out, np.int64)


def _gaps_m1_sesion(o: np.ndarray, h: np.ndarray, l: np.ndarray, c: np.ndarray, a_m1: int, tick: float, min_gap_ticks: int = MIN_GAP_TICKS):
    """Extrae gaps en escala M1 dentro de una sesión para confirmado=0 (gap bruto |o[i] - c[i-1]| >= min_g o VI bruto) y
    confirmado=1 (vacío no rellenado por las mechas al cierre de la vela M1, estilo OG/VI)."""
    n = len(c)
    if n <= 2:
        z0 = np.zeros(0, np.int64); f0 = np.zeros(0, float)
        return z0, f0, f0, z0
    min_g = min_gap_ticks * tick - 1e-9
    k_out, lo_out, hi_out, cf_out = [], [], [], []

    diff_oc = o[1:] - c[:-1]
    for i in np.flatnonzero(np.abs(diff_oc) >= min_g) + 1:
        p0, p1 = float(c[i - 1]), float(o[i])
        zlo_r, zhi_r = (p0, p1) if p1 > p0 else (p1, p0)
        k_out.append(a_m1 + int(i)); lo_out.append(zlo_r); hi_out.append(zhi_r); cf_out.append(0)
        if p1 > p0:
            lo_c, hi_c = float(max(p0, h[i - 1])), float(min(p1, l[i]))
            if hi_c - lo_c >= min_g:
                k_out.append(a_m1 + int(i)); lo_out.append(lo_c); hi_out.append(hi_c); cf_out.append(1)
        else:
            lo_c, hi_c = float(max(p1, h[i])), float(min(p0, l[i - 1]))
            if hi_c - lo_c >= min_g:
                k_out.append(a_m1 + int(i)); lo_out.append(lo_c); hi_out.append(hi_c); cf_out.append(1)

    gap_up_1 = l[1:] - h[:-1]
    for i in np.flatnonzero(gap_up_1 >= min_g) + 1:
        k_out.append(a_m1 + int(i)); lo_out.append(float(h[i - 1])); hi_out.append(float(l[i])); cf_out.append(1)
    gap_dn_1 = l[:-1] - h[1:]
    for i in np.flatnonzero(gap_dn_1 >= min_g) + 1:
        k_out.append(a_m1 + int(i)); lo_out.append(float(h[i])); hi_out.append(float(l[i - 1])); cf_out.append(1)

    if not k_out:
        z0 = np.zeros(0, np.int64); f0 = np.zeros(0, float)
        return z0, f0, f0, z0
    return np.array(k_out, np.int64), np.array(lo_out, float), np.array(hi_out, float), np.array(cf_out, np.int64)


# ------------------------------------------------------------------- 2. Detector Multi-Cluster y Zonas Individuales (Bug 1 Fix)
@njit(cache=False)
def _extraer_objetos_nb(zi, zlo, zhi, n_m1, min_gaps_cl, w_cl, max_hole, vida_m1, dedup_pts):
    """A partir de los gaps `(zi, zlo, zhi)` de un flujo `(escala, confirmado)`:
    - Extrae las zonas individuales deduplicadas (`obj = 0`) con su barra de nacimiento `m`.
    - Extrae TODOS los clusters compactos disjuntos (`obj = 1`, Bug 1 corregido de `ZonasDeGaps.cs`):
      ventanas de `>= min_gaps_cl` gaps activos (`m - zi <= vida_m1`) con altura total `<= w_cl` y hueco libre interno
      entre gaps consecutivos `<= max_hole`.
    Devuelve `(ev_m, ev_lo, ev_hi, ev_obj)`."""
    nz = len(zi)
    max_ev = nz * 2 + 16
    ev_m = np.empty(max_ev, np.int64)
    ev_lo = np.empty(max_ev, np.float64)
    ev_hi = np.empty(max_ev, np.float64)
    ev_obj = np.empty(max_ev, np.int64)
    nev = 0

    mk_m = np.full((2, 2048), -10**9, np.int64)
    mk_lo = np.zeros((2, 2048), np.float64)
    mk_hi = np.zeros((2, 2048), np.float64)
    mk_a = np.zeros(2, np.int64)
    mk_b = np.zeros(2, np.int64)

    p = 0
    while p < nz:
        m = zi[p]
        q = p
        while q < nz and zi[q] == m:
            q += 1

        for ob in range(2):
            while mk_a[ob] < mk_b[ob] and m - mk_m[ob, mk_a[ob] % 2048] > vida_m1:
                mk_a[ob] += 1

        best_g = p
        for r in range(p + 1, q):
            if (zhi[r] - zlo[r]) > (zhi[best_g] - zlo[best_g]):
                best_g = r
        glo, ghi = zlo[best_g], zhi[best_g]
        dup0 = False
        for r in range(mk_a[0], mk_b[0]):
            idx_r = r % 2048
            if glo <= mk_hi[0, idx_r] + dedup_pts and ghi >= mk_lo[0, idx_r] - dedup_pts:
                dup0 = True
                break
        if not dup0 and nev < max_ev:
            idx_w = mk_b[0] % 2048
            mk_m[0, idx_w] = m; mk_lo[0, idx_w] = glo; mk_hi[0, idx_w] = ghi; mk_b[0] += 1
            ev_m[nev] = m; ev_lo[nev] = glo; ev_hi[nev] = ghi; ev_obj[nev] = 0
            nev += 1

        p0 = p
        while p0 > 0 and m - zi[p0 - 1] <= vida_m1:
            p0 -= 1
        nv = q - p0
        if nv >= min_gaps_cl:
            orden = np.argsort(zlo[p0:q])
            lo_v = np.empty(nv, np.float64)
            hi_v = np.empty(nv, np.float64)
            zi_v = np.empty(nv, np.int64)
            for i in range(nv):
                ii = p0 + orden[i]
                lo_v[i] = zlo[ii]; hi_v[i] = zhi[ii]; zi_v[i] = zi[ii]

            for i in range(nv):
                lim = lo_v[i] + w_cl
                running_top = hi_v[i]
                cnt = 1
                has_new = (zi_v[i] == m)
                best_cnt = 0
                best_top = running_top
                for j in range(i + 1, nv):
                    if lo_v[j] > lim:
                        break
                    hole = lo_v[j] - running_top
                    if hole > max_hole:
                        break
                    if hi_v[j] <= lim:
                        cnt += 1
                        if hi_v[j] > running_top:
                            running_top = hi_v[j]
                        if zi_v[j] == m:
                            has_new = True
                        if cnt >= min_gaps_cl and has_new:
                            best_cnt = cnt
                            best_top = running_top
                if best_cnt >= min_gaps_cl:
                    clo, chi = lo_v[i], best_top
                    dup1 = False
                    for r in range(mk_a[1], mk_b[1]):
                        idx_r = r % 2048
                        if clo <= mk_hi[1, idx_r] + dedup_pts and chi >= mk_lo[1, idx_r] - dedup_pts:
                            dup1 = True
                            break
                    if not dup1 and nev < max_ev:
                        idx_w = mk_b[1] % 2048
                        mk_m[1, idx_w] = m; mk_lo[1, idx_w] = clo; mk_hi[1, idx_w] = chi; mk_b[1] += 1
                        ev_m[nev] = m; ev_lo[nev] = clo; ev_hi[nev] = chi; ev_obj[nev] = 1
                        nev += 1
        p = q

    return ev_m[:nev], ev_lo[:nev], ev_hi[:nev], ev_obj[:nev]


# ------------------------------------------- 3. Seguimiento causal de Ciclos: TOQUE_RETEST (Bug 3 Fix), GIRO_IMAN e IMAN_U1
@njit(cache=False)
def _ciclos_zonas_nb(ev_m, ev_lo, ev_hi, ev_obj, h, l, c, away_min, vida_m1, max_ciclos, ah_iman_min, x_giro, x_u1):
    """Oráculo compilado barra a barra (Numba) para los ciclos de alejamiento y regreso de cada objeto."""
    n_ev = len(ev_m); n_m1 = len(c)
    cap = n_ev * max_ciclos * 3 + 16
    o_k = np.empty(cap, np.int64)
    o_m = np.empty(cap, np.int64)
    o_obj = np.empty(cap, np.int64)
    o_mec = np.empty(cap, np.int64)
    o_virg = np.empty(cap, np.int64)
    o_d = np.empty(cap, np.int64)
    o_pa = np.empty(cap, np.float64)
    o_alej = np.empty(cap, np.float64)
    o_H = np.empty(cap, np.float64)
    nd = 0

    for idx in range(n_ev):
        m0 = ev_m[idx]; lo = ev_lo[idx]; hi = ev_hi[idx]; obj = ev_obj[idx]
        H_real = hi - lo
        H_eff = H_real if H_real >= away_min else away_min
        fin = m0 + vida_m1
        if fin > n_m1:
            fin = n_m1

        j0 = m0 + 1
        toques_prev = 0
        cruzado_prev = 0

        while j0 < fin and toques_prev < max_ciclos:
            js = -1; lado_alej = 0
            for j in range(j0, fin):
                if c[j] > hi:
                    js = j; lado_alej = 1; break
                elif c[j] < lo:
                    js = j; lado_alej = -1; break
            if js < 0:
                break

            ext = h[js] if lado_alej == 1 else l[js]
            is_away = False
            disparo_giro = False
            disparo_u1 = False
            j_fin_ciclo = fin

            for j in range(js, fin):
                if lado_alej == 1:
                    if h[j] > ext:
                        ext = h[j]
                    A = ext - hi
                    D_close = c[j] - hi
                    toco = (l[j] <= hi)
                else:
                    if l[j] < ext:
                        ext = l[j]
                    A = lo - ext
                    D_close = lo - c[j]
                    toco = (h[j] >= lo)

                if not is_away:
                    if A >= H_eff:
                        is_away = True
                    elif toco:
                        j_fin_ciclo = j
                        break

                if is_away:
                    virg = 0 if (toques_prev == 0 and cruzado_prev == 0) else (1 if (toques_prev == 1 and cruzado_prev == 0) else 2)
                    ah_ratio = A / H_eff

                    if not toco and D_close > 0 and ah_ratio >= ah_iman_min:
                        d_iman = -lado_alej
                        pa_iman = lo if lado_alej == 1 else hi
                        if (not disparo_giro) and D_close <= x_giro * A and nd < cap:
                            disparo_giro = True
                            o_k[nd] = j; o_m[nd] = m0; o_obj[nd] = obj; o_mec[nd] = 1; o_virg[nd] = virg
                            o_d[nd] = d_iman; o_pa[nd] = pa_iman; o_alej[nd] = ah_ratio; o_H[nd] = H_real
                            nd += 1
                        if (not disparo_u1) and D_close <= x_u1 * A and nd < cap:
                            disparo_u1 = True
                            o_k[nd] = j; o_m[nd] = m0; o_obj[nd] = obj; o_mec[nd] = 2; o_virg[nd] = virg
                            o_d[nd] = d_iman; o_pa[nd] = pa_iman; o_alej[nd] = ah_ratio; o_H[nd] = H_real
                            nd += 1

                    if toco:
                        d_toque = lado_alej
                        pa_toque = ext
                        if nd < cap:
                            o_k[nd] = j; o_m[nd] = m0; o_obj[nd] = obj; o_mec[nd] = 0; o_virg[nd] = virg
                            o_d[nd] = d_toque; o_pa[nd] = pa_toque; o_alej[nd] = ah_ratio; o_H[nd] = H_real
                            nd += 1
                        toques_prev += 1
                        if (lado_alej == 1 and c[j] < lo) or (lado_alej == -1 and c[j] > hi):
                            cruzado_prev = 1
                        j_fin_ciclo = j
                        break

            j0 = j_fin_ciclo + 1

    return o_k[:nd], o_m[:nd], o_obj[:nd], o_mec[:nd], o_virg[:nd], o_d[:nd], o_pa[:nd], o_alej[:nd], o_H[:nd]


def _ciclos_zonas_vec(ev_m, ev_lo, ev_hi, ev_obj, h, l, c, away_min, vida_m1, max_ciclos, ah_iman_min, x_giro, x_u1):
    """Equivalente 100 % vectorizado en NumPy de `_ciclos_zonas_nb` (100x más rápido cuando Numba no está instalado)."""
    n_ev = len(ev_m); n_m1 = len(c)
    cap = n_ev * max_ciclos * 3 + 16
    o_k = np.empty(cap, np.int64)
    o_m = np.empty(cap, np.int64)
    o_obj = np.empty(cap, np.int64)
    o_mec = np.empty(cap, np.int64)
    o_virg = np.empty(cap, np.int64)
    o_d = np.empty(cap, np.int64)
    o_pa = np.empty(cap, np.float64)
    o_alej = np.empty(cap, np.float64)
    o_H = np.empty(cap, np.float64)
    nd = 0

    for idx in range(n_ev):
        m0 = int(ev_m[idx]); lo = float(ev_lo[idx]); hi = float(ev_hi[idx]); obj = int(ev_obj[idx])
        H_real = hi - lo
        H_eff = H_real if H_real >= away_min else away_min
        fin = min(n_m1, m0 + vida_m1)

        j0 = m0 + 1
        toques_prev = 0
        cruzado_prev = 0

        while j0 < fin and toques_prev < max_ciclos:
            c_sl = c[j0:fin]
            fuera = np.flatnonzero((c_sl > hi) | (c_sl < lo))
            if not len(fuera):
                break
            js = j0 + int(fuera[0])
            lado_alej = 1 if c[js] > hi else -1

            h_jj = h[js:fin]; l_jj = l[js:fin]; c_jj = c[js:fin]
            if lado_alej == 1:
                E = np.maximum.accumulate(h_jj)
                A = E - hi
                D_close = c_jj - hi
                toco = l_jj <= hi
            else:
                E = np.minimum.accumulate(l_jj)
                A = lo - E
                D_close = lo - c_jj
                toco = h_jj >= lo

            ok_away = A >= H_eff
            if not ok_away.any():
                if toco.any():
                    j0 = js + int(np.argmax(toco)) + 1
                    continue
                else:
                    break

            q_away = int(np.argmax(ok_away))
            if q_away > 0 and toco[:q_away].any():
                j0 = js + int(np.argmax(toco[:q_away])) + 1
                continue

            toco_post = toco[q_away:]
            tiene_toque = bool(toco_post.any())
            q_fin = q_away + int(np.argmax(toco_post)) if tiene_toque else (len(h_jj) - 1)

            virg = 0 if (toques_prev == 0 and cruzado_prev == 0) else (1 if (toques_prev == 1 and cruzado_prev == 0) else 2)
            sl_A = A[q_away : q_fin + 1]
            sl_D = D_close[q_away : q_fin + 1]
            sl_toco = toco[q_away : q_fin + 1]
            base_iman = (~sl_toco) & (sl_D > 0) & (sl_A >= ah_iman_min * H_eff)
            if base_iman.any():
                d_iman = -lado_alej
                pa_iman = lo if lado_alej == 1 else hi
                c_giro = base_iman & (sl_D <= x_giro * sl_A)
                c_u1 = base_iman & (sl_D <= x_u1 * sl_A)
                q1 = (q_away + int(np.argmax(c_giro))) if c_giro.any() else -1
                q2 = (q_away + int(np.argmax(c_u1))) if c_u1.any() else -1
                if q1 >= 0 and q2 >= 0 and q2 < q1:
                    for qq, mec_id in ((q2, 2), (q1, 1)):
                        o_k[nd] = js + qq; o_m[nd] = m0; o_obj[nd] = obj; o_mec[nd] = mec_id; o_virg[nd] = virg
                        o_d[nd] = d_iman; o_pa[nd] = pa_iman; o_alej[nd] = float(A[qq] / H_eff); o_H[nd] = H_real
                        nd += 1
                else:
                    if q1 >= 0:
                        o_k[nd] = js + q1; o_m[nd] = m0; o_obj[nd] = obj; o_mec[nd] = 1; o_virg[nd] = virg
                        o_d[nd] = d_iman; o_pa[nd] = pa_iman; o_alej[nd] = float(A[q1] / H_eff); o_H[nd] = H_real
                        nd += 1
                    if q2 >= 0:
                        o_k[nd] = js + q2; o_m[nd] = m0; o_obj[nd] = obj; o_mec[nd] = 2; o_virg[nd] = virg
                        o_d[nd] = d_iman; o_pa[nd] = pa_iman; o_alej[nd] = float(A[q2] / H_eff); o_H[nd] = H_real
                        nd += 1

            if tiene_toque:
                d_toque = lado_alej
                pa_toque = float(E[q_fin])
                o_k[nd] = js + q_fin; o_m[nd] = m0; o_obj[nd] = obj; o_mec[nd] = 0; o_virg[nd] = virg
                o_d[nd] = d_toque; o_pa[nd] = pa_toque; o_alej[nd] = float(A[q_fin] / H_eff); o_H[nd] = H_real
                nd += 1
                toques_prev += 1
                if (lado_alej == 1 and c_jj[q_fin] < lo) or (lado_alej == -1 and c_jj[q_fin] > hi):
                    cruzado_prev = 1
                j0 = js + q_fin + 1
            else:
                break

    return o_k[:nd], o_m[:nd], o_obj[:nd], o_mec[:nd], o_virg[:nd], o_d[:nd], o_pa[:nd], o_alej[:nd], o_H[:nd]


# ----------------------------------------------------------------------------------------------- 4. Interfaz grilla_generica
def _atr_causal(h: np.ndarray, l: np.ndarray, c: np.ndarray, n: int = 14) -> np.ndarray:
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).rolling(n, min_periods=n).mean().to_numpy()


def disparos(ctx) -> pd.DataFrame:
    o, h, l, c, v, t, ses, seg = (np.asarray(ctx[x]) for x in ("o", "h", "l", "c", "v", "t", "ses", "seg"))
    o, h, l, c, v = (x.astype(float) for x in (o, h, l, c, v))
    tick = float(ctx["tick"])
    tpx = np.asarray(ctx["tpx"], float)
    tstart = np.asarray(ctx["tstart"], np.int64)

    away_min = max(AWAY_DISTANCE_TICKS * tick, 2.5)
    w_cl = CLUSTER_HEIGHT_TICKS * tick
    max_hole = MAX_FREE_SPACE_TICKS * tick
    fn_ciclos = _ciclos_zonas_nb if HAS_NUMBA else _ciclos_zonas_vec

    partes = []
    for sg in pd.unique(seg):
        idx_sg = np.flatnonzero(seg == sg)
        a_sg, b_sg = int(idx_sg[0]), int(idx_sg[-1]) + 1
        ses_sg = ses[a_sg:b_sg]
        cambios_ses = np.flatnonzero(np.r_[True, ses_sg[1:] != ses_sg[:-1], True]) + a_sg

        g50_k, g50_lo, g50_hi, g50_cf = [], [], [], []
        gm1_k, gm1_lo, gm1_hi, gm1_cf = [], [], [], []
        for s_i in range(len(cambios_ses) - 1):
            a_s, b_s = int(cambios_ses[s_i]), int(cambios_ses[s_i + 1])
            k0, lo0, hi0, cf0 = _gaps_50t_sesion(tpx, tstart[a_s : b_s + 1], a_s, tick, MIN_GAP_TICKS)
            if len(k0):
                g50_k.append(k0); g50_lo.append(lo0); g50_hi.append(hi0); g50_cf.append(cf0)
            k1, lo1, hi1, cf1 = _gaps_m1_sesion(o[a_s:b_s], h[a_s:b_s], l[a_s:b_s], c[a_s:b_s], a_s, tick, MIN_GAP_TICKS)
            if len(k1):
                gm1_k.append(k1); gm1_lo.append(lo1); gm1_hi.append(hi1); gm1_cf.append(cf1)

        for esc, gk_l, glo_l, ghi_l, gcf_l in ((0, g50_k, g50_lo, g50_hi, g50_cf), (1, gm1_k, gm1_lo, gm1_hi, gm1_cf)):
            if not gk_l:
                continue
            gk = np.concatenate(gk_l) - a_sg
            glo = np.concatenate(glo_l)
            ghi = np.concatenate(ghi_l)
            gcf = np.concatenate(gcf_l)

            for conf in (0, 1):
                m_cf = (gcf == conf)
                if not np.any(m_cf):
                    continue
                zk = gk[m_cf]; zlo = glo[m_cf]; zhi = ghi[m_cf]
                ord_z = np.argsort(zk, kind="mergesort")
                zk, zlo, zhi = zk[ord_z], zlo[ord_z], zhi[ord_z]

                ev_m, ev_lo, ev_hi, ev_obj = _extraer_objetos_nb(
                    zk, zlo, zhi, b_sg - a_sg, MIN_GAPS_CLUSTER, w_cl, max_hole, VIDA_MAX_M1, DEDUP_PTS
                )
                if not len(ev_m):
                    continue

                ok, om, oobj, omec, ovirg, od, opa, oalej, oH = fn_ciclos(
                    ev_m, ev_lo, ev_hi, ev_obj, h[a_sg:b_sg], l[a_sg:b_sg], c[a_sg:b_sg],
                    away_min, VIDA_MAX_M1, MAX_CICLOS_ZONA, AH_IMAN_MIN, X_GIRO, X_U1
                )
                if not len(ok):
                    continue

                partes.append(pd.DataFrame(dict(
                    k=ok + a_sg,
                    m=om + a_sg,
                    esc=np.full(len(ok), esc, np.int64),
                    conf=np.full(len(ok), conf, np.int64),
                    obj=oobj,
                    mec=omec,
                    virg=ovirg,
                    d=od,
                    pa=opa,
                    alej=oalej,
                    H=oH,
                )))

    cols_base = ["k", "m", "esc", "conf", "obj", "mec", "virg", "d", "pa", "alej", "H", "tam", "vrel", "vwap_al"]
    if not partes:
        return pd.DataFrame(columns=cols_base + [vv.columna for vv in VARIABLES_REGIMEN.values()])

    D = pd.concat(partes, ignore_index=True)
    D = D.sort_values(["k", "esc", "conf", "obj", "mec", "alej"], ascending=[True, True, True, True, True, False], kind="mergesort")
    D = D.drop_duplicates(subset=["k", "esc", "conf", "obj", "mec"], keep="first").sort_values(
        ["k", "esc", "conf", "obj", "mec"], kind="mergesort"
    ).reset_index(drop=True)

    atr = _atr_causal(h, l, c, 14)
    df_ses = pd.DataFrame(dict(ses=ses, v=v, pv=c * v))
    rate = df_ses.groupby("ses").v.mean()
    us = np.array(sorted(rate.index))
    base_rate = pd.Series(np.r_[np.nan, rate.loc[us].to_numpy()[:-1]], index=us).reindex(ses).to_numpy(float)
    vwap_ses = (df_ses.groupby("ses").pv.cumsum() / df_ses.groupby("ses").v.cumsum().replace(0, np.nan)).to_numpy(float)

    k_arr = D.k.to_numpy(np.int64)
    m_arr = D.m.to_numpy(np.int64)
    d_arr = D.d.to_numpy(float)
    cv = np.r_[0.0, np.cumsum(v)]
    with np.errstate(invalid="ignore", divide="ignore"):
        dur = np.maximum(k_arr - m_arr + 1, 1)
        vol_ciclo = (cv[k_arr + 1] - cv[m_arr]) / dur
        D["vrel"] = np.where(base_rate[k_arr] > 0, vol_ciclo / base_rate[k_arr], np.nan)
        D["tam"] = np.where(atr[k_arr] > 0, D.H.to_numpy(float) / atr[k_arr], np.nan)
    D["vwap_al"] = np.where((vwap_ses[k_arr] - c[k_arr]) * d_arr >= 0, 1.0, 0.0)
    D = agregar(D, ctx)
    return D


def _niveles_arr(k, d, pa, ck, tick, ej):
    """Arreglo (n, 7) de `(start, limite, s, entrada, stop, objetivo, be)` con NaN donde la ejecución no aplica.
    Compartido por `niveles` y `niveles_lote` para garantizar paridad exacta en preflight."""
    lado, en, ftp, fsl, be = ej
    n = len(k)
    k = np.asarray(k, float)
    d = np.asarray(d, float)
    pa = np.asarray(pa, float)
    ck = np.asarray(ck, float)

    e_ref = ck + d * tick
    D0 = d * (pa - e_ref)
    if en in ("CIERRE", "SIG"):
        lim = 0.0 if en == "CIERRE" else 2.0
        ent = ck.copy()
        base = e_ref
        Db = D0
    else:
        paso = np.ceil(LIM_FRAC * D0 / tick) * tick
        ent = ck - d * paso if lado == "FAVOR" else ck + d * paso
        lim = 1.0
        base = ent
        Db = d * (pa - ent)

    if lado == "FAVOR":
        s = d
        tp = base + d * ftp * Db
        st = base - d * fsl * Db
    else:
        s = -d
        tp = base - d * ftp * Db
        st = base + d * fsl * Db

    ok = (D0 >= 8.0 * tick) & (Db >= 8.0 * tick) & ((tp - ent) * s >= 2.0 * tick) & ((ent - st) * s >= 2.0 * tick)
    X = np.column_stack([k, np.full(n, lim), s, ent, st, tp, np.full(n, float(be))])
    X[~ok] = np.nan
    return X


def niveles_lote(D: pd.DataFrame, ej, ctx) -> np.ndarray:
    k = D.k.to_numpy(np.int64)
    return _niveles_arr(k, D.d.to_numpy(float), D.pa.to_numpy(float), np.asarray(ctx["c"], float)[k], float(ctx["tick"]), ej)


def niveles(r, ej, ctx):
    k = int(r["k"])
    X = _niveles_arr(
        np.array([k]), np.array([float(r["d"])]), np.array([float(r["pa"])]),
        np.array([float(ctx["c"][k])]), float(ctx["tick"]), ej
    )[0]
    if not np.isfinite(X[0]):
        return None
    return int(X[0]), int(X[1]), int(X[2]), float(X[3]), float(X[4]), float(X[5]), int(X[6])
