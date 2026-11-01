"""Zonas de HFTZones2 adaptativo en numba, para el almacén de zonas.

`hftzones2.run` recorre TODAS las zonas creadas en cada tick (`update_zones`, archivadas incluidas): el costo crece con ticks × zonas y
en NQ/ES no entra en las 12 h de un kernel. Toques, invalidación y expiración no deciden si una zona nace ni dónde, así que acá sólo está
el motor de rachas y la calibración por sesión, con la misma aritmética de doubles. Identidad: tests/test_hft2_rapido.py.
"""
from __future__ import annotations

import sys

import numpy as np

from edgelab.research.otr_930_sweep import njit

SEEN, STRIDE, LARGO = 0, 1, 2                          # sampler
DIR, VALID, FAILS, NMS, T_LAST = 0, 1, 2, 3, 4         # racha, enteros
SWH, SWL, VOL, SUMA, COMP = 0, 1, 2, 3, 4              # racha, doubles
PRED, ULTRA, MAX_AVG, MAX_PAUSA, MAX_TOTAL, MIN_RATE, MIN_VOL = 0, 1, 2, 3, 4, 5, 6


@njit(cache=False)
def _prox_nb(ts, i, fin):
    """Primer índice >= i con ts >= fin: el criterio de `check_session`, tick a tick, aun con ts no monótonos."""
    n = len(ts)
    while i < n and ts[i] < fin: i += 1
    return i


@njit(cache=False)
def _snap_nb(precio, tick):
    x = precio / tick
    return int(np.floor(x + 0.5)) if x >= 0 else int(np.ceil(x - 0.5))


@njit(cache=False)
def _add_nb(vals, e, v, cap):
    e[SEEN] += 1
    if e[SEEN] % e[STRIDE] != 0: return
    if e[LARGO] >= cap:
        m = 0
        for j in range(1, e[LARGO], 2):
            vals[m] = vals[j]; m += 1
        e[LARGO] = m; e[STRIDE] *= 2
    vals[e[LARGO]] = v; e[LARGO] += 1


@njit(cache=False)
def _q_nb(orden, q):
    n = len(orden)
    return float(orden[max(0, min(n - 1, int(np.ceil(q * n)) - 1))])


@njit(cache=False)
def _reset_nb(si, sf):
    si[DIR] = 0; si[VALID] = 0; si[FAILS] = 0; si[NMS] = 0
    sf[:] = 0.0


@njit(cache=False)
def _start_nb(si, sf, d, price, vol, t_ns):
    si[DIR] = d; si[VALID] = 1; si[FAILS] = 0; si[NMS] = 0; si[T_LAST] = t_ns
    sf[SWH] = price; sf[SWL] = price; sf[VOL] = vol; sf[SUMA] = 0.0; sf[COMP] = 0.0


@njit(cache=False)
def _continue_nb(si, sf, price, vol, ms, t_ns, valid, kahan):
    if valid: si[VALID] += 1
    sf[SWH] = max(sf[SWH], price); sf[SWL] = min(sf[SWL], price); sf[VOL] += vol; si[T_LAST] = t_ns; si[NMS] += 1
    if kahan:                                          # sum() de floats de CPython >= 3.12
        s = sf[SUMA]; t = s + ms
        sf[COMP] += (s - t) + ms if abs(s) >= abs(ms) else (ms - t) + s
        sf[SUMA] = t
    else:
        sf[SUMA] += ms


@njit(cache=False)
def _finalize_nb(si, sf, eff, tick, kahan, min_pasos, min_absorb, min_sweep, alto_z, absorb, Z, nz):
    """`finalize_streak`. Devuelve el nuevo nz; quien llama garantiza lugar en Z."""
    if si[DIR] == 0:
        _reset_nb(si, sf); return nz
    alto = _snap_nb(sf[SWH], tick) - _snap_nb(sf[SWL], tick); sweep = alto >= min_sweep
    tot = sf[SUMA] + sf[COMP] if kahan and sf[COMP] != 0.0 else sf[SUMA]
    avg = tot / si[NMS] if si[NMS] else 0.0
    rate = sf[VOL] / (max(tot, 1.0) / 1000.0)
    req = min_pasos if sweep else min_absorb
    if si[VALID] >= req and (sweep or absorb) and avg <= eff[MAX_AVG] and tot <= eff[MAX_TOTAL] and rate >= eff[MIN_RATE] and sf[VOL] >= eff[MIN_VOL]:
        if si[DIR] == 1:
            up = _snap_nb(sf[SWL], tick); lo = up - alto_z
        else:
            lo = _snap_nb(sf[SWH], tick); up = lo + alto_z
        Z[nz, 0] = si[T_LAST]; Z[nz, 1] = lo; Z[nz, 2] = up; nz += 1
    _reset_nb(si, sf)
    return nz


@njit(cache=False)
def _motor_nb(ts, pt, vo, tick, cortes, kahan, enteros, reales):
    min_pasos, min_absorb, fallos, min_sweep, retro_floor, cap, min_calib, alto_z, absorb = enteros
    q_pred, q_ult, q_max, pause_mult, total_mult, vol_mult, pause_excl, retro_pct = reales
    n = len(ts); Z = np.empty((1024, 3), np.int64); nz = 0
    ms_v = np.empty(cap + 1); vol_v = np.empty(cap + 1); ms_e = np.array([0, 1, 0], np.int64); vol_e = np.array([0, 1, 0], np.int64)
    si = np.zeros(5, np.int64); sf = np.zeros(5); eff = np.zeros(7); listo = False; ic = 0
    args = (tick, kahan, min_pasos, min_absorb, min_sweep, alto_z, absorb)
    for i in range(1, n):
        if nz + 3 >= len(Z):                           # como mucho dos cierres por tick
            G = np.empty((2 * len(Z), 3), np.int64); G[:nz] = Z[:nz]; Z = G
        t_ns = ts[i]; price = float(pt[i]) * tick; vol = float(vo[i])
        if ic < len(cortes) and cortes[ic] == i:       # check_session
            ic += 1
            nz = _finalize_nb(si, sf, eff, *args, Z, nz)
            if ms_e[LARGO] >= 100 and vol_e[LARGO] >= 100 and ms_e[SEEN] >= min_calib:
                a = np.sort(ms_v[:ms_e[LARGO]]); b = np.sort(vol_v[:vol_e[LARGO]])
                p50 = _q_nb(a, 0.50); med_v = _q_nb(b, 0.50)
                eff[PRED] = max(1.0, _q_nb(a, q_pred)); eff[ULTRA] = max(eff[PRED], _q_nb(a, q_ult)); eff[MAX_AVG] = max(eff[ULTRA], _q_nb(a, q_max))
                eff[MAX_PAUSA] = min(5000.0, max(eff[MAX_AVG], pause_mult * max(1.0, p50)))
                eff[MAX_TOTAL] = eff[MAX_AVG] * min_pasos * total_mult
                eff[MIN_VOL] = vol_mult * med_v * min_pasos
                eff[MIN_RATE] = eff[MIN_VOL] / (eff[MAX_TOTAL] / 1000.0)
                listo = True
            ms_e[0] = 0; ms_e[1] = 1; ms_e[2] = 0; vol_e[0] = 0; vol_e[1] = 1; vol_e[2] = 0
        ms = float(ts[i] - ts[i - 1]) / 1e6
        if 0 <= ms <= pause_excl: _add_nb(ms_v, ms_e, ms, cap)
        _add_nb(vol_v, vol_e, vol, cap)
        if not listo: continue
        prev = float(pt[i - 1]) * tick                 # step_engine
        if si[DIR] != 0 and ms > eff[MAX_PAUSA]:
            nz = _finalize_nb(si, sf, eff, *args, Z, nz); continue
        if si[DIR] == 0:
            if price < prev: _start_nb(si, sf, -1, price, vol, t_ns)
            elif price > prev: _start_nb(si, sf, 1, price, vol, t_ns)
            continue
        valid = price >= prev if si[DIR] == 1 else price <= prev
        if valid:
            _continue_nb(si, sf, price, vol, ms, t_ns, True, kahan); si[FAILS] = 0
        else:
            si[FAILS] += 1
            if si[FAILS] <= fallos:
                _continue_nb(si, sf, price, vol, ms, t_ns, False, kahan)
            else:
                nz = _finalize_nb(si, sf, eff, *args, Z, nz)
                if price < prev: _start_nb(si, sf, -1, price, vol, t_ns)
                elif price > prev: _start_nb(si, sf, 1, price, vol, t_ns)
                continue
        swh_t = _snap_nb(sf[SWH], tick); swl_t = _snap_nb(sf[SWL], tick); px_t = _snap_nb(price, tick)
        retro = swh_t - px_t if si[DIR] == 1 else px_t - swl_t
        if retro > max(float(retro_floor), retro_pct / 100.0 * (swh_t - swl_t)):
            nz = _finalize_nb(si, sf, eff, *args, Z, nz)
    return Z[:nz]


def zonas(ticks, sesion_fin_ns, params) -> np.ndarray:
    """Matriz (t_ns ZONE_CREATED, lower_t, upper_t) con la configuración adaptativa por defecto de `hftzones2`."""
    p = params
    if not (p["adaptive_mode"] and p["use_relative_retro"]): raise ValueError("hft2_rapido sólo cubre modo adaptativo con retroceso relativo")
    ts = np.asarray(ticks.ts_ns, np.int64)
    if len(ts) < 2: return np.empty((0, 3), np.int64)
    cortes = []; i = 1
    while i < len(ts):
        cortes.append(i); i = int(_prox_nb(ts, i + 1, sesion_fin_ns(int(ts[i]))))
    enteros = tuple(int(p[k]) for k in ("min_pasos", "min_absorb_pasos", "fallos_tolerados", "min_sweep_ticks", "retro_floor_ticks",
                                        "calib_sample_cap", "min_calib_samples", "zone_height_ticks", "detect_absorb"))
    reales = tuple(float(p[k]) for k in ("q_predator", "q_ultra", "q_max_avg", "pause_mult", "total_ms_mult", "vol_mult_median_tick",
                                         "pause_exclude_ms", "retro_pct_height"))
    return _motor_nb(ts, np.asarray(ticks.price_ticks, np.int64), np.asarray(ticks.volume, np.int64), float(ticks.tick_size),
                     np.array(cortes, np.int64), sys.version_info >= (3, 12), enteros, reales)
