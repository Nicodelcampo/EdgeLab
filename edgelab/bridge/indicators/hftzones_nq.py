"""HFTZonesNQ — motor de rachas HFT, espejo de `nt8/HFTClusterZonesNQ.cs`.

**Target-free.** Detecta candidatos; no evalúa nada contra retornos.

## La decisión de diseño que gobierna este módulo

El `.cs` **decide y descarta**: calcula una racha, le aplica diez umbrales y, si falla
alguno, la tira. Acá la detección y la aceptación están **separadas**:

    candidatos = detect_candidates(ticks...)      # caro: una pasada por tick
    zonas      = accept_all(candidatos, umbrales) # barato: aritmética sobre el censo

`detect_candidates` emite **todas** las rachas finalizadas con sus *estadísticos
suficientes*. Con eso, los diez umbrales de aceptación se pueden re-aplicar sin volver
a tocar los ticks. Un barrido de umbrales que en NT8 exigiría re-correr el chart
completo, acá cuesta un `for`.

Esto es lo que permite lo que pidió Nico: *exportar todas las zonas posibles* y recién
después decidir cuáles cuentan.

## Qué es estructural y qué es post-hoc

De los quince parámetros que el `.cs` expone, sólo **dos** cambian qué rachas existen:

- `tick_resolution` — define la subserie sobre la que corre el motor;
- `max_pausa_ms` — un silencio mayor corta la racha.

Los diez umbrales de aceptación (`min_pasos`, `min_sweep_ticks`, `max_avg_ms`,
`max_total_ms`, `min_volume_rate`, `min_total_volume`, `max_retroceso_ticks`,
`retroceso_pct_height`, `min_absorb_pasos`, `detect_absorb`) son **post-hoc**.

Y tres no hacen nada, verificado en el fuente:

- `fallos_tolerados` — la variable `fails` se incrementa y se resetea, **nunca se lee**
  (`HFTClusterZonesNQ.cs` líneas 342-367). Es un parámetro muerto en la UI.
- `max_rango_tick_por_vela` y `filtro_direccion_estricto` — con `tick_resolution=1`
  cada barra de la subserie es un tick, así que `high == low` (rango 0, el filtro
  siempre pasa) y `open == close` (la condición de cuerpo real se vuelve idéntica a la
  simple). Sólo tendrían efecto con `tick_resolution > 1`, que no está soportado acá.

## Sobre el rendimiento

La máquina de estados es secuencial por construcción: no se vectoriza. Una sesión de NQ
son ~10⁵–10⁶ ticks, lo que corre en segundos. Un contrato entero son ~10⁸ y va a
Kaggle, no a la máquina local.
"""
from __future__ import annotations

NAME = "HFTZonesNQ"
VERSION = "1.0"

STRUCTURAL_DEFAULTS = dict(
    tick_resolution=1,
    max_pausa_ms=100.0,
)

ACCEPT_DEFAULTS = dict(
    min_pasos=8,
    min_absorb_pasos=6,
    detect_absorb=True,
    min_sweep_ticks=4,
    max_avg_ms=25.0,
    max_total_ms=500.0,
    min_volume_rate=100.0,
    min_total_volume=50.0,
    max_retroceso_ticks=2.0,
    retroceso_pct_height=50.0,
)

# La configuracion de la campana NO es la certificada, y la diferencia es deliberada.
#
# ACCEPT_DEFAULTS reproduce el `.cs` v1.0.0 y es lo que el certificado de paridad
# valida (7.494/7.494 zonas, 20 campos). CAMPAIGN_FROZEN es lo que el test de
# estabilidad target-free eligio para medir: umbral de volumen 10 en vez de 50, porque
# con 50 el turnover de zonas da 38% contra un contrato de 5%.
#
# Se mantienen SEPARADAS a proposito. Si se hiciera de CAMPAIGN_FROZEN el default, el
# validador de paridad compararia contra otra poblacion y el certificado quedaria
# silenciosamente inaplicable. `tests/bridge/test_hftzones_nq.py` fija la divergencia.
CAMPAIGN_FROZEN = dict(ACCEPT_DEFAULTS, min_total_volume=10)

# Orden en que el .cs evalúa las compuertas. Importa para reportar CUÁL falló:
# se informa la primera, igual que el original corta en la primera.
GATE_ORDER = ("pasos", "sweep_o_absorb", "velocidad", "duracion",
              "tasa_volumen", "volumen_total", "retroceso")


def _p(defaults, overrides):
    out = dict(defaults)
    if overrides:
        out.update({k: v for k, v in overrides.items() if v is not None})
    return out


def detect_candidates(ts_ns, price_ticks, volume, params=None):
    """Todas las rachas finalizadas, con sus estadísticos suficientes.

    Entrada: los tres arrays del tick stream, en orden y **de una sola sesión** — el
    motor no cruza sesiones, igual que NT8 reinicia su subserie.

    Salida: una lista de dicts. Ninguno está filtrado: son candidatos, no zonas.
    """
    p = _p(STRUCTURAL_DEFAULTS, params)
    if int(p["tick_resolution"]) != 1:
        raise NotImplementedError(
            "solo tick_resolution=1. Con resolucion mayor hay que construir la "
            "subserie de N ticks y los filtros de rango y cuerpo real dejan de ser "
            "inertes; portarlos exige medir el .cs en ese modo primero.")
    max_pausa = float(p["max_pausa_ms"])

    n = len(price_ticks)
    out = []

    # --- estado de la racha ---
    direccion = 0
    idx0 = 0
    streak = valid = 0
    sw_hi = sw_lo = 0
    extremo = 0
    max_retro = 0.0
    total_vol = 0.0
    ms_list = []
    signos = []
    vols = []
    precios = []
    last_side = 0

    def iniciar(i, vol, sv):
        nonlocal streak, valid, sw_hi, sw_lo, extremo, max_retro, total_vol, idx0
        streak = valid = 1
        sw_hi = sw_lo = extremo = price_ticks[i]
        max_retro = 0.0
        total_vol = vol
        idx0 = i
        ms_list.clear(); signos.clear(); vols.clear(); precios.clear()
        signos.append(sv); vols.append(vol); precios.append(price_ticks[i])

    def continuar(i, ms, vol, sv, es_valido):
        nonlocal streak, valid, sw_hi, sw_lo, extremo, max_retro, total_vol
        streak += 1
        if es_valido:
            valid += 1
        pt = price_ticks[i]
        if pt > sw_hi:
            sw_hi = pt
        if pt < sw_lo:
            sw_lo = pt
        # retroceso maximo acumulado contra el extremo alcanzado, tick a tick
        if direccion == 1:
            if pt > extremo:
                extremo = pt
            adv = extremo - pt
        else:
            if pt < extremo:
                extremo = pt
            adv = pt - extremo
        if adv > max_retro:
            max_retro = float(adv)
        ms_list.append(ms)
        total_vol += vol
        signos.append(sv); vols.append(vol); precios.append(pt)

    def finalizar(i_fin):
        if direccion == 0 or streak == 0:
            return
        out.append(_estadisticos(
            idx0, i_fin, direccion, streak, valid, sw_hi, sw_lo, max_retro,
            list(ms_list), total_vol, list(signos), list(vols), list(precios),
            ts_ns))

    for i in range(1, n):
        cl = price_ticks[i]
        cl_prev = price_ticks[i - 1]
        ms = (ts_ns[i] - ts_ns[i - 1]) / 1e6
        vol = float(volume[i])

        side = 1 if cl > cl_prev else (-1 if cl < cl_prev else last_side)
        if side == 0:
            side = 1
        last_side = side
        sv = side * vol

        # con tick_resolution=1 el filtro de rango y el de cuerpo real son inertes
        es_baja = cl <= cl_prev
        es_alza = cl >= cl_prev

        if direccion != 0 and ms > max_pausa:
            finalizar(i - 1)
            direccion = 0
            continue

        if direccion == 0:
            if es_baja:
                direccion = -1; iniciar(i, vol, sv)
            elif es_alza:
                direccion = 1; iniciar(i, vol, sv)
        elif direccion == -1:
            if es_baja:
                continuar(i, ms, vol, sv, True)
            else:
                retro = (cl - extremo)
                if retro <= _retro_permitido(sw_hi, sw_lo):
                    continuar(i, ms, vol, sv, False)
                else:
                    finalizar(i - 1)
                    if es_alza:
                        direccion = 1; iniciar(i, vol, sv)
                    else:
                        direccion = 0
        else:
            if es_alza:
                continuar(i, ms, vol, sv, True)
            else:
                retro = (extremo - cl)
                if retro <= _retro_permitido(sw_hi, sw_lo):
                    continuar(i, ms, vol, sv, False)
                else:
                    finalizar(i - 1)
                    if es_baja:
                        direccion = -1; iniciar(i, vol, sv)
                    else:
                        direccion = 0

    finalizar(n - 1)
    return out


# El retroceso permitido durante la racha usa los MISMOS dos parámetros que la
# compuerta final, así que es el único umbral de aceptación que también es
# estructural. Se deja fijo en los defaults del .cs a propósito: moverlo cambia qué
# rachas existen, y entonces deja de valer el barrido post-hoc.
_RETRO_FLOOR = ACCEPT_DEFAULTS["max_retroceso_ticks"]
_RETRO_PCT = ACCEPT_DEFAULTS["retroceso_pct_height"]


def _retro_permitido(sw_hi, sw_lo):
    return max(_RETRO_FLOOR, (_RETRO_PCT / 100.0) * (sw_hi - sw_lo))


def _estadisticos(i0, i1, direccion, streak, valid, sw_hi, sw_lo, max_retro,
                  ms_list, total_vol, signos, vols, precios, ts_ns):
    total_ms = float(sum(ms_list))
    avg_ms = total_ms / max(1, len(ms_list))
    dur_sec = max(total_ms, 1.0) / 1000.0
    vol_rate = total_vol / dur_sec

    cvd = buy = sell = 0.0
    max_tick_vol = 0.0
    for sv, v in zip(signos, vols):
        cvd += sv
        if sv >= 0:
            buy += v
        else:
            sell += v
        if v > max_tick_vol:
            max_tick_vol = v

    slope = d_first = d_second = 0.0
    ns = len(signos)
    if ns >= 2:
        sx = sy = sxy = sxx = cum = 0.0
        for k, sv in enumerate(signos):
            cum += sv
            sx += k; sy += cum; sxy += k * cum; sxx += float(k) * k
        den = ns * sxx - sx * sx
        if abs(den) > 1e-9:
            slope = (ns * sxy - sx * sy) / den
        mitad = ns // 2
        for k, sv in enumerate(signos):
            if k < mitad:
                d_first += sv
            else:
                d_second += sv

    # niveles: cuánto tiempo estuvo la racha sin moverse de precio
    freq = {}
    no_move_ticks = 0
    no_move_vol = 0.0
    for k in range(1, len(precios)):
        if precios[k] == precios[k - 1]:
            no_move_ticks += 1
            no_move_vol += vols[k]
    for pt, v in zip(precios, vols):
        freq[pt] = freq.get(pt, 0) + 1
    max_level_ticks = max(freq.values()) if freq else 0

    return dict(
        idx_start=i0, idx_end=i1,
        ts_start=int(ts_ns[i0]), ts_end=int(ts_ns[i1]),
        direction=direccion,
        pasos=streak, valid_steps=valid,
        sw_hi_tk=int(sw_hi), sw_lo_tk=int(sw_lo),
        height_ticks=float(sw_hi - sw_lo),
        total_ms=total_ms, n_intervals=len(ms_list), avg_ms=avg_ms,
        total_vol=float(total_vol), vol_rate=vol_rate,
        max_retro_ticks=float(max_retro),
        cvd=cvd, buy_vol=buy, sell_vol=sell, max_tick_vol=max_tick_vol,
        delta_slope=slope, delta_first=d_first, delta_second=d_second,
        no_move_ticks=no_move_ticks, no_move_vol=no_move_vol,
        max_level_ticks=max_level_ticks,
    )


def accept(cand, thresholds=None):
    """¿Este candidato es una zona? Devuelve `(bool, compuerta_que_fallo)`.

    Corta en la primera compuerta que falla, igual que el `.cs`, para que el motivo
    reportado sea comparable entre los dos lados.
    """
    t = _p(ACCEPT_DEFAULTS, thresholds)
    is_sweep = cand["height_ticks"] >= t["min_sweep_ticks"]
    is_absorb = (not is_sweep) and t["detect_absorb"]
    min_req = t["min_pasos"] if is_sweep else t["min_absorb_pasos"]

    if cand["valid_steps"] < min_req:
        return False, "pasos"
    if not (is_sweep or is_absorb):
        return False, "sweep_o_absorb"
    if cand["avg_ms"] > t["max_avg_ms"]:
        return False, "velocidad"
    if cand["total_ms"] > t["max_total_ms"]:
        return False, "duracion"
    if cand["vol_rate"] < t["min_volume_rate"]:
        return False, "tasa_volumen"
    if cand["total_vol"] < t["min_total_volume"]:
        return False, "volumen_total"
    if not is_absorb:
        permitido = max(t["max_retroceso_ticks"],
                        (t["retroceso_pct_height"] / 100.0) * cand["height_ticks"])
        if cand["max_retro_ticks"] > permitido:
            return False, "retroceso"
    return True, None


def bucket(cand, thresholds=None, predator_ms=5.0, ultra_ms=15.0):
    """Clasificación por velocidad. No interviene en la aceptación."""
    t = _p(ACCEPT_DEFAULTS, thresholds)
    if cand["height_ticks"] < t["min_sweep_ticks"] and t["detect_absorb"]:
        return "Absorb"
    if cand["avg_ms"] <= predator_ms:
        return "Predator"
    if cand["avg_ms"] <= ultra_ms:
        return "Ultra"
    return "Fast"


def accept_all(candidates, thresholds=None, tick_size=0.25):
    """Aplica los umbrales al censo completo. Devuelve zonas y motivos de rechazo.

    El segundo valor es lo que hace medible un barrido: dice **por qué** se cae cada
    candidato, así un resultado vacío se distingue de un umbral mal puesto.
    """
    zonas = []
    motivos = {}
    for c in candidates:
        ok, gate = accept(c, thresholds)
        if ok:
            z = dict(c)
            z["lower"] = c["sw_lo_tk"] * tick_size
            z["upper"] = c["sw_hi_tk"] * tick_size
            z["bucket"] = bucket(c, thresholds)
            zonas.append(z)
        else:
            motivos[gate] = motivos.get(gate, 0) + 1
    return zonas, motivos
