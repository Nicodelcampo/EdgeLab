"""CONFLUENCIA-CVGAP-RACIMOS (2026-10-29): Síntesis en Espiral de las 6 Mejores Corridas de las Olas 1–9 (`CVGAP-NQ/CFD`, `U1-RACIMOS-GRILLA-NQ/ES`, `U1-ZONAS-BT2-ES/NQ` y `OTR930`).

Hipótesis física y microestructural (crecimiento en espiral apoyado en los hallazgos empíricos de Olas 1–9):
  1. En las Olas 1–9, seis campañas superaron las 4 compuertas del embudo (`DESC`, `INTEGRIDAD`, `OOS` y `TOPES`) y emitieron
     `ACTA_HOLDOUT.json`:
     - `CVGAP-NQ` (`+$19,13/op` OOS) y `CVGAP-CFD-NQ` (`+$10,50/op` OOS): agotamiento tras excursión tardía desde el Rectángulo
       Amarillo (`EmaCorridorTrendVolW2` P80/P90) barriendo gaps previos.
     - `U1-RACIMOS-GRILLA-NQ` (`+$32,83/op` OOS) y `U1-RACIMOS-GRILLA-ES` (`+$5,95/op`): regreso tras excursión desde un racimo
       compacto de zonas de absorción de volumen.
     - `U1-ZONAS-BT2-NQ` (`+$15,02/op`) y `U1-ZONAS-BT2-ES` (`+$2,47/op` OOS): absorción en velas trampa extremas (`BigTrap2`).
  2. Además, en `CVGAP-ES` identificamos que los cortes rígidos de gaps (`>= 4`) vaciaban celdas en activos de libro denso (`ES`),
     mientras que en `OTR930` vimos que la cercanía a los extremos del rango de apertura NY (`09:30 ET`) amplifica el retorno.
  3. Esta familia une esas 4 primitivas en un único motor causal e invariante de escala:
     - Detecta los impulsos del corredor `EMA20/EMA60` y su sector adelantado con Caja Amarilla (`P75 / P85` sobre ventana rodante).
     - Calcula causalmente la **densidad de racimo de absorción (`racimo_dens`)**: número de nodos de alto volumen (`v >= 1.35 * vol_med`
       o vela de rechazo tipo `BT2`) y gaps activos concentrados en la banda de excursión/regreso.
     - Reemplaza los umbrales rígidos de gaps por **cuantiles empíricos invariantes de escala** (`extremos`, `cuantiles=3`), garantizando
       densidad uniforme tanto en `NQ`/`USATECH` como en `ES`/`USA500`.
     - Mide la confluencia con el barrido de extremos de sesión/apertura (`confluencia_apertura`).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.grilla_generica import Variable
from edgelab.research.otr_930_sweep import _offset_ny_seg_nb

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "CONFLUENCIA-CVGAP-RACIMOS"
INDICADORES = ["CONFLUENCIA-CVGAP-RACIMOS", "EmaCorridorTrendVolW2", "ZONAS-GAPS"]

VARIABLES = [
    Variable("ancho_sector", "w_sec", "grupo", categoria=2),               # 0: W1=100% · 1: W2=200%
    Variable("gatillo_regreso", "gat_reg", "grupo", categoria=3),          # 0: R_ANTES_25 · 1: R_BORDE_CAJA · 2: R_POC_CAJA
    Variable("excursion_caja", "exc_caja", "ge", cortes=(1.0, 2.0)),       # excursión en múltiplos de la altura de la Caja Amarilla
    Variable("racimo_absorcion", "rac_dens", "ge", cortes=(1.0, 2.0)),     # densidad de nodos de volumen/BT2 en el racimo (0: >=0, 1: >=1, 2: >=2)
    Variable("gap_barrido_q", "g_tom_rel", "extremos", cuantiles=3),       # cuantiles invariantes de escala de gaps barridos en excursión
    Variable("gap_iman_q", "g_cam_rel", "extremos", cuantiles=3),          # cuantiles invariantes de escala de gaps imán hacia el origen
    Variable("confluencia_apertura", "conf_ny", "eq_any", categoria=2),    # 0: fuera de ventana NY · 1: confluencia barrido RTH/apertura · 2: cualquiera
    Variable("tamano_impulso", "tam_imp", "extremos", cuantiles=3),        # terciles causales de H_impulso / ATR14
    Variable("vwap_al", "vwap_al", "eq_any", categoria=2),                 # 0: lejos de VWAP · 1: reversión hacia VWAP · 2: cualquiera
]
EJES_ORDINALES = (2, 3)

MODOS_DIR = ("REVERSION_ORIGEN", "CONTINUACION_IMPULSO")
ENTRADAS = ("CIERRE", "SIG")
TARGETS = ("ORIG_100", "MID_50", "MID_30")
STOPS = ("S_EXT_RACIMO", "S_CAJA_AMARILLA")
EJECUCIONES = [(md, ent, tp, sl) for md in MODOS_DIR for ent in ENTRADAS for tp in TARGETS for sl in STOPS]

BASE = {
    "ancho_sector": 1,
    "gatillo_regreso": 1,
    "excursion_caja": 1,
    "racimo_absorcion": 1,
    "gap_barrido_q": 2,
    "gap_iman_q": 2,
    "confluencia_apertura": 2,
    "tamano_impulso": 2,
    "vwap_al": 2,
    "ejecución": EJECUCIONES.index(("REVERSION_ORIGEN", "SIG", "MID_50", "S_CAJA_AMARILLA")),
}


@njit(cache=False)
def _extraer_confluencia_nb(t, o, h, l, c, v, ses, tick):
    n = len(c)
    max_out = max(n // 3, 256)
    out_k = np.empty(max_out, dtype=np.int64)
    out_wsec = np.empty(max_out, dtype=np.int64)
    out_gat = np.empty(max_out, dtype=np.int64)
    out_lado = np.empty(max_out, dtype=np.int64)
    out_orig = np.empty(max_out, dtype=np.float64)
    out_himp = np.empty(max_out, dtype=np.float64)
    out_hcaja = np.empty(max_out, dtype=np.float64)
    out_eexc = np.empty(max_out, dtype=np.float64)
    out_exccaja = np.empty(max_out, dtype=np.float64)
    out_rac = np.empty(max_out, dtype=np.float64)
    out_gtom = np.empty(max_out, dtype=np.float64)
    out_gcam = np.empty(max_out, dtype=np.float64)
    out_confny = np.empty(max_out, dtype=np.int64)
    out_tam = np.empty(max_out, dtype=np.float64)
    out_vwap = np.empty(max_out, dtype=np.int64)
    cnt = 0

    # Memoria circular de nodos de volumen/BT2 (racimos) y de gaps
    MAX_NODOS = 64
    nodo_px = np.zeros(MAX_NODOS, dtype=np.float64)
    nodo_peso = np.zeros(MAX_NODOS, dtype=np.float64)
    nodo_vivo = np.zeros(MAX_NODOS, dtype=np.int64)
    nodo_head = 0

    MAX_GAPS = 64
    g_lo = np.zeros(MAX_GAPS, dtype=np.float64)
    g_hi = np.zeros(MAX_GAPS, dtype=np.float64)
    g_vivo = np.zeros(MAX_GAPS, dtype=np.int64)
    g_head = 0

    # Ventana rodante de 50 sectores para percentil P75 causal
    HIST_VOL = 50
    hist_vsec = np.zeros(HIST_VOL, dtype=np.float64)
    hist_cnt = 0
    hist_head = 0

    atr = max(h[0] - l[0], tick)
    vol_med = max(v[0], 1.0)
    ema20 = c[0]
    ema60 = c[0]
    a20 = 2.0 / 21.0
    a60 = 2.0 / 61.0

    ses_act = ses[0]
    vwap_num = 0.0
    vwap_den = 0.0

    # Estado del impulso actual del corredor EMA20/60
    dir_corr = 0
    orig_px = c[0]
    ext_imp = c[0]
    bar_orig = 0
    bar_ext = 0
    en_sector = 0
    lo_caja = 0.0
    hi_caja = 0.0
    poc_caja = 0.0
    vol_sec_acum = 0.0
    w_sec_actual = 0
    en_excursion = 0
    ext_tardio = 0.0
    g_tom_exc = 0.0
    disparado_gat = np.zeros(3, dtype=np.int64)

    for i in range(1, n):
        if ses[i] != ses_act:
            ses_act = ses[i]
            vwap_num = 0.0
            vwap_den = 0.0

        tr = max(h[i] - l[i], max(abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
        atr = (13.0 * atr + max(tr, tick)) / 14.0
        vol_med = 0.95 * vol_med + 0.05 * max(v[i], 1.0)
        ema20 = a20 * c[i] + (1.0 - a20) * ema20
        ema60 = a60 * c[i] + (1.0 - a60) * ema60

        tp_px = (h[i] + l[i] + c[i]) / 3.0
        vwap_num += tp_px * max(v[i], 1.0)
        vwap_den += max(v[i], 1.0)
        vwap_now = vwap_num / vwap_den if vwap_den > 0.0 else c[i]

        # 1. Registrar nodos de absorción (AVZP2 / BT2: volumen >= 1.35 * vol_med con mecha >= 30%)
        rng_b = max(h[i] - l[i], tick)
        mecha_sup = (h[i] - max(o[i], c[i])) / rng_b
        mecha_inf = (min(o[i], c[i]) - l[i]) / rng_b
        if v[i] >= 1.35 * vol_med and (mecha_sup >= 0.30 or mecha_inf >= 0.30):
            nodo_px[nodo_head] = h[i] if mecha_sup >= mecha_inf else l[i]
            nodo_peso[nodo_head] = min(v[i] / vol_med, 3.0)
            nodo_vivo[nodo_head] = 1
            nodo_head = (nodo_head + 1) % MAX_NODOS

        # 2. Actualizar ciclo de vida de gaps M1
        g_tom_bar = 0.0
        for g in range(MAX_GAPS):
            if g_vivo[g] == 1:
                if l[i] <= g_hi[g] and h[i] >= g_lo[g]:
                    g_tom_bar += 0.65
                    if l[i] <= g_lo[g] and h[i] >= g_hi[g]:
                        g_vivo[g] = 0

        if i >= 2:
            if l[i] - h[i - 2] >= 2.0 * tick:
                g_lo[g_head] = h[i - 2]
                g_hi[g_head] = l[i]
                g_vivo[g_head] = 1
                g_head = (g_head + 1) % MAX_GAPS
            elif l[i - 2] - h[i] >= 2.0 * tick:
                g_lo[g_head] = h[i]
                g_hi[g_head] = l[i - 2]
                g_vivo[g_head] = 1
                g_head = (g_head + 1) % MAX_GAPS

        # 3. Seguimiento causal del corredor EMA 20/60 y Caja Amarilla
        nueva_dir = 1 if ema20 > ema60 + 0.10 * atr else (-1 if ema20 < ema60 - 0.10 * atr else 0)
        if nueva_dir != 0 and nueva_dir != dir_corr:
            dir_corr = nueva_dir
            orig_px = l[i] if dir_corr == 1 else h[i]
            ext_imp = h[i] if dir_corr == 1 else l[i]
            bar_orig = i
            bar_ext = i
            en_sector = 0
            en_excursion = 0

        if dir_corr != 0 and en_sector == 0 and en_excursion == 0:
            if dir_corr == 1:
                if l[i] < orig_px:
                    orig_px = l[i]
                    bar_orig = i
                if h[i] > ext_imp:
                    ext_imp = h[i]
                    bar_ext = i
            else:
                if h[i] > orig_px:
                    orig_px = h[i]
                    bar_orig = i
                if l[i] < ext_imp:
                    ext_imp = l[i]
                    bar_ext = i

            H_imp = abs(ext_imp - orig_px)
            dur_imp = bar_ext - bar_orig
            # Si hubo al menos 5 barras de impulso y 2 barras de consolidación en el extremo, abrir sector adelantado
            if dur_imp >= 3 and (i - bar_ext) == 1 and H_imp >= 1.2 * atr:
                en_sector = 1
                lo_caja = ext_imp - 0.25 * H_imp if dir_corr == 1 else ext_imp - 0.25 * H_imp
                hi_caja = ext_imp + 0.25 * H_imp if dir_corr == 1 else ext_imp + 0.25 * H_imp
                poc_caja = ext_imp
                vol_sec_acum = 0.0
                w_sec_actual = 1 if (dur_imp >= 12) else 0

        elif en_sector == 1:
            # Acumular volumen causal dentro de [lo_caja, hi_caja]
            if l[i] <= hi_caja and h[i] >= lo_caja:
                ov = max(0.0, min(h[i], hi_caja) - max(l[i], lo_caja)) / rng_b
                vol_sec_acum += v[i] * ov
                if v[i] > vol_med:
                    poc_caja = 0.5 * (poc_caja + tp_px)

            dur_imp = max(bar_ext - bar_orig, 5)
            ancho_barras = dur_imp if w_sec_actual == 0 else 2 * dur_imp

            # Verificar si el volumen acumulado ya supera P70 de la ventana rodante de 50 sectores
            es_amarilla = 0
            if hist_cnt >= 8:
                menores = 0
                for j in range(hist_cnt):
                    if hist_vsec[j] <= vol_sec_acum:
                        menores += 1
                if float(menores) / float(hist_cnt) >= 0.45:
                    es_amarilla = 1
            elif vol_sec_acum >= 1.5 * vol_med:
                es_amarilla = 1

            # Ruptura en la misma dirección del impulso inicial desde una Caja Amarilla activa
            rompio_favor = (dir_corr == 1 and h[i] > hi_caja) or (dir_corr == -1 and l[i] < lo_caja)
            if es_amarilla == 1 and rompio_favor:
                hist_vsec[hist_head] = vol_sec_acum
                hist_head = (hist_head + 1) % HIST_VOL
                if hist_cnt < HIST_VOL:
                    hist_cnt += 1
                en_sector = 0
                en_excursion = 1
                ext_tardio = h[i] if dir_corr == 1 else l[i]
                g_tom_exc = g_tom_bar
                for g_idx in range(3):
                    disparado_gat[g_idx] = 0
            elif (i - bar_ext) > ancho_barras:
                hist_vsec[hist_head] = vol_sec_acum
                hist_head = (hist_head + 1) % HIST_VOL
                if hist_cnt < HIST_VOL:
                    hist_cnt += 1
                en_sector = 0

        elif en_excursion == 1:
            g_tom_exc += g_tom_bar
            if dir_corr == 1 and h[i] > ext_tardio:
                ext_tardio = h[i]
            elif dir_corr == -1 and l[i] < ext_tardio:
                ext_tardio = l[i]

            H_caja = max(hi_caja - lo_caja, 2.0 * tick)
            H_imp = max(abs(ext_imp - orig_px), H_caja)
            exc_abs = (ext_tardio - hi_caja) if dir_corr == 1 else (lo_caja - ext_tardio)
            exc_mult = max(exc_abs / H_caja, 0.0)

            if (i - bar_ext) > 90:
                en_excursion = 0
                continue

            if exc_mult >= 0.20:
                for gat_id in range(3):
                    if disparado_gat[gat_id] == 1:
                        continue
                    ok_reg = 0
                    if gat_id == 0:
                        # R_ANTES_25: retrocede al menos 35% de la excursión antes del borde de la caja
                        if dir_corr == 1 and c[i] <= ext_tardio - 0.35 * max(exc_abs, tick) and c[i] < o[i]:
                            ok_reg = 1
                        elif dir_corr == -1 and c[i] >= ext_tardio + 0.35 * max(exc_abs, tick) and c[i] > o[i]:
                            ok_reg = 1
                    elif gat_id == 1:
                        # R_BORDE_CAJA: regresa al borde de la Caja Amarilla
                        if dir_corr == 1 and l[i] <= hi_caja and c[i] <= hi_caja and c[i] < o[i]:
                            ok_reg = 1
                        elif dir_corr == -1 and h[i] >= lo_caja and c[i] >= lo_caja and c[i] > o[i]:
                            ok_reg = 1
                    else:
                        # R_POC_CAJA: regresa hasta el AnchorPOC de la Caja Amarilla
                        if dir_corr == 1 and c[i] <= poc_caja and c[i] < o[i]:
                            ok_reg = 1
                        elif dir_corr == -1 and c[i] >= poc_caja and c[i] > o[i]:
                            ok_reg = 1

                    if ok_reg == 1 and cnt < max_out:
                        disparado_gat[gat_id] = 1
                        # Calcular densidad de racimo de absorción alrededor del nivel de excursión/regreso
                        rac_score = 0.0
                        banda_rac = 0.75 * H_imp
                        for nd in range(MAX_NODOS):
                            if nodo_vivo[nd] == 1 and abs(nodo_px[nd] - c[i]) <= banda_rac:
                                rac_score += 0.75 * nodo_peso[nd]

                        # Calcular puntaje de gaps abiertos en el camino de regreso al origen
                        g_cam_val = 0.0
                        for g in range(MAX_GAPS):
                            if g_vivo[g] == 1:
                                g_mid = 0.5 * (g_lo[g] + g_hi[g])
                                if dir_corr == 1 and orig_px <= g_mid < c[i]:
                                    g_cam_val += 0.65
                                elif dir_corr == -1 and c[i] < g_mid <= orig_px:
                                    g_cam_val += 0.65

                        off_ny = _offset_ny_seg_nb(int(t[i]))
                        min_et = ((int(t[i]) + off_ny) % 86400) // 60
                        # Confluencia con la ventana activa de apertura / RTH de NY (09:30 a 12:30 ET = 570..750)
                        conf_ny = 1 if (570 <= min_et <= 750) else 0

                        dir_rev = -dir_corr
                        vwap_st = 1 if (vwap_now - c[i]) * float(dir_rev) > 0.0 else 0

                        out_k[cnt] = i
                        out_wsec[cnt] = w_sec_actual
                        out_gat[cnt] = gat_id
                        out_lado[cnt] = dir_corr
                        out_orig[cnt] = orig_px
                        out_himp[cnt] = H_imp
                        out_hcaja[cnt] = H_caja
                        out_eexc[cnt] = ext_tardio
                        out_exccaja[cnt] = exc_mult
                        out_rac[cnt] = rac_score
                        out_gtom[cnt] = g_tom_exc / max(atr, tick)
                        out_gcam[cnt] = g_cam_val / max(atr, tick)
                        out_confny[cnt] = conf_ny
                        out_tam[cnt] = H_imp / max(atr, tick)
                        out_vwap[cnt] = vwap_st
                        cnt += 1

    return (
        out_k[:cnt],
        out_wsec[:cnt],
        out_gat[:cnt],
        out_lado[:cnt],
        out_orig[:cnt],
        out_himp[:cnt],
        out_hcaja[:cnt],
        out_eexc[:cnt],
        out_exccaja[:cnt],
        out_rac[:cnt],
        out_gtom[:cnt],
        out_gcam[:cnt],
        out_confny[:cnt],
        out_tam[:cnt],
        out_vwap[:cnt],
    )


def disparos(ctx: dict) -> pd.DataFrame:
    t = np.asarray(ctx["t"], dtype=np.int64)
    o = np.asarray(ctx["o"], dtype=np.float64)
    h = np.asarray(ctx["h"], dtype=np.float64)
    l = np.asarray(ctx["l"], dtype=np.float64)
    c = np.asarray(ctx["c"], dtype=np.float64)
    v = np.asarray(ctx["v"], dtype=np.float64)
    ses = np.asarray(ctx["ses"], dtype=np.int64)
    tick = float(ctx["tick"])

    res = _extraer_confluencia_nb(t, o, h, l, c, v, ses, tick)
    k = res[0]
    return pd.DataFrame(
        {
            "k": k,
            "ses": ses[k],
            "w_sec": res[1],
            "gat_reg": res[2],
            "lado": res[3],
            "orig_px": res[4],
            "H_imp": res[5],
            "H_caja": res[6],
            "E_exc": res[7],
            "exc_caja": res[8],
            "rac_dens": res[9],
            "g_tom_rel": res[10],
            "g_cam_rel": res[11],
            "conf_ny": res[12],
            "tam_imp": res[13],
            "vwap_al": res[14],
        }
    )


def niveles(d, ej: tuple, ctx: dict):
    md, ent, tp_name, sl_name = ej
    k = int(d["k"])
    lado = int(d["lado"])
    orig_px = float(d["orig_px"])
    H_imp = float(d["H_imp"])
    H_caja = float(d["H_caja"])
    E_exc = float(d["E_exc"])
    tick = float(ctx["tick"])
    ck = float(ctx["c"][k])

    s = -lado if md == "REVERSION_ORIGEN" else lado
    lim = 0 if ent == "CIERRE" else 2
    e = np.round(ck / tick) * tick

    if md == "REVERSION_ORIGEN":
        if tp_name == "ORIG_100":
            tp_raw = orig_px
            min_m = 0.85
        elif tp_name == "MID_50":
            tp_raw = e + float(s) * 0.55 * H_imp
            min_m = 0.50
        else:
            tp_raw = e + float(s) * 0.35 * H_imp
            min_m = 0.30
        if (tp_raw - e) * float(s) < min_m * H_imp:
            tp_raw = e + float(s) * min_m * H_imp
    else:
        mult_tp = 0.90 if tp_name == "ORIG_100" else (0.55 if tp_name == "MID_50" else 0.35)
        tp_raw = e + float(s) * mult_tp * H_imp

    tp = np.round(tp_raw / tick) * tick
    if (tp - e) * float(s) < 2.0 * tick:
        tp = e + float(s) * 2.0 * tick

    dist_ext = max(abs(E_exc - e) + 2.0 * tick, 0.30 * H_imp) if md == "REVERSION_ORIGEN" else 0.35 * H_imp
    if sl_name == "S_EXT_RACIMO":
        sl_raw = e - float(s) * dist_ext
    else:
        dist_caja = max(1.25 * H_caja, 0.45 * H_imp)
        if abs(dist_caja - dist_ext) < 2.0 * tick:
            dist_caja = dist_ext + 3.0 * tick
        sl_raw = e - float(s) * dist_caja

    sl = np.floor(sl_raw / tick) * tick if s == 1 else np.ceil(sl_raw / tick) * tick
    if (e - sl) * float(s) < 2.0 * tick:
        sl = e - float(s) * 2.0 * tick

    return (k, lim, s, float(e), float(sl), float(tp), 0)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    m = len(D)
    out = np.full((m, 7), np.nan, dtype=np.float64)
    if m == 0:
        return out
    md, ent, tp_name, sl_name = ej
    k = D["k"].to_numpy(np.int64)
    lado = D["lado"].to_numpy(np.int64)
    orig_px = D["orig_px"].to_numpy(np.float64)
    H_imp = D["H_imp"].to_numpy(np.float64)
    H_caja = D["H_caja"].to_numpy(np.float64)
    E_exc = D["E_exc"].to_numpy(np.float64)
    tick = float(ctx["tick"])
    ck = np.asarray(ctx["c"], dtype=np.float64)[k]

    s = (-lado if md == "REVERSION_ORIGEN" else lado).astype(np.float64)
    lim = 0.0 if ent == "CIERRE" else 2.0
    e = np.round(ck / tick) * tick

    if md == "REVERSION_ORIGEN":
        if tp_name == "ORIG_100":
            tp_raw = orig_px
            min_m = 0.85
        elif tp_name == "MID_50":
            tp_raw = e + s * 0.55 * H_imp
            min_m = 0.50
        else:
            tp_raw = e + s * 0.35 * H_imp
            min_m = 0.30
        corto = (tp_raw - e) * s < min_m * H_imp
        tp_raw = np.where(corto, e + s * min_m * H_imp, tp_raw)
    else:
        mult_tp = 0.90 if tp_name == "ORIG_100" else (0.55 if tp_name == "MID_50" else 0.35)
        tp_raw = e + s * mult_tp * H_imp

    tp = np.round(tp_raw / tick) * tick
    tp = np.where((tp - e) * s < 2.0 * tick, e + s * 2.0 * tick, tp)

    dist_ext = np.maximum(np.abs(E_exc - e) + 2.0 * tick, 0.30 * H_imp) if md == "REVERSION_ORIGEN" else 0.35 * H_imp
    if sl_name == "S_EXT_RACIMO":
        sl_raw = e - s * dist_ext
    else:
        dist_caja = np.maximum(1.25 * H_caja, 0.45 * H_imp)
        dist_caja = np.where(np.abs(dist_caja - dist_ext) < 2.0 * tick, dist_ext + 3.0 * tick, dist_caja)
        sl_raw = e - s * dist_caja

    sl = np.where(s == 1.0, np.floor(sl_raw / tick) * tick, np.ceil(sl_raw / tick) * tick)
    sl = np.where((e - sl) * s < 2.0 * tick, e - s * 2.0 * tick, sl)

    out[:, 0] = k.astype(np.float64)
    out[:, 1] = lim
    out[:, 2] = s
    out[:, 3] = e
    out[:, 4] = sl
    out[:, 5] = tp
    out[:, 6] = 0.0
    return out
