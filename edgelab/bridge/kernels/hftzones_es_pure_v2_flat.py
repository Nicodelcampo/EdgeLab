"""Puerto Python de HFTZonesESPureV2Flat (NT8) — corre sobre ticks crudos de EdgeLab.

POR QUE ESTE PUERTO ES SIMPLE
=============================
El indicador declara `AddDataSeries(BarsPeriodType.Tick, TickResolution)` con
`TickResolution = 1`, asi que toda la maquina de estados corre sobre la serie de **1
tick**. El grafico de 25 Tick del chart es solo la serie primaria de DIBUJO
(`BarsInProgress == 0`); no entra en el algoritmo.

En una barra de 1 tick, `Open == High == Low == Close == precio del tick`. Eso colapsa
tres condiciones del .cs:

    rng    = (High - Low) / TickSize = 0        -> `small` es SIEMPRE true
    isDown = small && cl <= clP && cl <= op     -> `cl <= clP`
    isUp   = small && cl >= clP && cl >= op     -> `cl >= clP`
    plano  = isDown && isUp                     -> `cl == clP`

Y ahi se ve por que el bug importaba tanto: sobre ticks, el precio repite constantemente,
asi que `plano` es el caso mas frecuente. Evaluar `isDown` primero mandaba casi toda
racha a bajista — 92% medido sobre 23.863 zonas.

QUE SE REPRODUCE
================
`swH`/`swL` (la geometria de la zona), `tStart`/`tLast`, y las metricas que el .cs
persiste. `StartBar`/`EndBar` NO: son indices de la serie de dibujo de 25 Tick y no
tienen sentido fuera del chart.

Sin outcomes. Sin P&L. Geometria y microestructura.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

# Defaults leidos de SetDefaults del .cs (docs/research/parches/HFTZonesESPureV2Flat.cs).
# NO son numeros elegidos aca: si el chart corre con otros, se pasan explicitos.
DEFAULTS = dict(
    tick_resolution=1, min_pasos=10, max_rango_tick_por_vela=1, fallos_tolerados=1,
    filtro_direccion_estricto=True, min_sweep_ticks=5, max_avg_ms=15, max_total_ms=300,
    max_pausa_ms=50, min_volume_rate=500, min_total_volume=200, predator_avg_ms=3,
    ultra_avg_ms=10, mostrar_absorb=True, min_absorb_pasos=8)


@dataclass
class Params:
    min_pasos: int = 10
    max_rango_tick_por_vela: int = 1
    fallos_tolerados: int = 1
    filtro_direccion_estricto: bool = True
    min_sweep_ticks: int = 5
    max_avg_ms: int = 15
    max_total_ms: int = 300
    max_pausa_ms: int = 50
    min_volume_rate: int = 500
    min_total_volume: int = 200
    predator_avg_ms: int = 3
    ultra_avg_ms: int = 10
    mostrar_absorb: bool = True
    min_absorb_pasos: int = 8


@dataclass
class Zona:
    start_ts: int          # epoch ms UTC, igual que UnixMs del .cs
    end_ts: int
    bucket: str
    dir: int
    price_upper: float
    price_lower: float
    price_mid: float
    height_ticks: float
    pasos: int
    valid_steps: int
    avg_ms: float
    total_ms: float
    vol_rate: float
    total_vol: float
    max_tick_vol: float
    cvd_sweep: float
    buy_vol: float
    sell_vol: float
    delta_slope: float
    delta_first: float
    delta_second: float
    no_move_ticks: int
    no_move_vol: float
    max_level_ticks: int


@dataclass
class _Racha:
    """Estado mutable de la racha en curso. Espeja los campos del .cs uno a uno."""
    streak: int = 0
    valid_steps: int = 0
    dir: int = 0
    fails: int = 0
    sw_h: float = 0.0
    sw_l: float = 0.0
    total_vol: float = 0.0
    t_start: int = 0
    t_last: int = 0
    ms: List[float] = field(default_factory=list)      # msList: intervalos, NO el primero
    precio: List[float] = field(default_factory=list)
    vol: List[float] = field(default_factory=list)
    sign: List[float] = field(default_factory=list)

    def reset(self):
        self.streak = self.valid_steps = self.dir = self.fails = 0
        self.ms.clear(); self.precio.clear(); self.vol.clear(); self.sign.clear()
        self.total_vol = 0.0


def _emitir(r: _Racha, p: Params, tick_size: float,
            casi: Optional[list] = None) -> Optional[Zona]:
    """Traduce Finalizar() del .cs. Devuelve None si la racha no califica.

    Si se pasa `casi`, las rachas que fallan EXACTAMENTE UNO de los cuatro filtros de
    calidad (velocidad, duracion, tasa de volumen, volumen total) se acumulan ahi con el
    motivo. Sirven como control emparejado: misma geometria, mismo instante, misma
    sesion, el precio estuvo igual de presente -- pero no son zona.

    Es el control que F2.9 llamo K0 vs N0 (creadora contra no-creadora emparejada). El
    espejo geometrico NO sirve para esta familia: la zona es el rango del propio barrido
    y el barrido termina adentro, asi que la distancia al precio de creacion tiene
    mediana 1 tick y 39% de las zonas la tienen en 0 -- el espejo cae encima de la zona.
    """
    sweep_ticks = (r.sw_h - r.sw_l) / tick_size
    is_sweep = sweep_ticks >= p.min_sweep_ticks
    is_absorb = (not is_sweep) and p.mostrar_absorb
    min_pasos_req = p.min_pasos if is_sweep else p.min_absorb_pasos

    if r.valid_steps < min_pasos_req or not (is_sweep or is_absorb):
        return None

    total = float(sum(r.ms))
    avg_ms = total / max(1, len(r.ms))
    dur_s = max(total, 1.0) / 1000.0
    vol_rate = r.total_vol / dur_s

    fallos = [n for n, ok in (
        ("velocidad", avg_ms <= p.max_avg_ms),
        ("duracion", total <= p.max_total_ms),
        ("tasa_volumen", vol_rate >= p.min_volume_rate),
        ("volumen_total", r.total_vol >= p.min_total_volume)) if not ok]
    if fallos:
        if casi is not None and len(fallos) == 1:
            casi.append(dict(start_ts=r.t_start, end_ts=r.t_last, dir=r.dir,
                             price_upper=r.sw_h, price_lower=r.sw_l,
                             height_ticks=sweep_ticks, pasos=r.streak,
                             valid_steps=r.valid_steps, avg_ms=avg_ms,
                             total_ms=total, vol_rate=vol_rate,
                             total_vol=r.total_vol, motivo=fallos[0]))
        return None

    if is_absorb:
        bajo = r.precio[-1] < r.precio[0]
        bucket = "Absorb"
        _txt = "ABSORB_BEAR" if bajo else "ABSORB_BULL"     # noqa: F841  (solo dibujo)
    else:
        bucket = ("Predator" if avg_ms <= p.predator_avg_ms
                  else "Ultra" if avg_ms <= p.ultra_avg_ms else "Fast")

    cvd = buy = sell = max_tick_vol = 0.0
    for sv, v in zip(r.sign, r.vol):
        cvd += sv
        if sv >= 0:
            buy += v
        else:
            sell += v
        max_tick_vol = max(max_tick_vol, v)

    slope = d_first = d_second = 0.0
    n_s = len(r.sign)
    if n_s >= 2:
        sum_x = sum_y = sum_xy = sum_xx = cum = 0.0
        for i, sv in enumerate(r.sign):
            cum += sv
            sum_x += i; sum_y += cum; sum_xy += i * cum; sum_xx += float(i) * i
        den = n_s * sum_xx - sum_x * sum_x
        if abs(den) > 1e-9:
            slope = (n_s * sum_xy - sum_x * sum_y) / den
        half = n_s // 2
        for i, sv in enumerate(r.sign):
            if i < half:
                d_first += sv
            else:
                d_second += sv

    no_move_ticks, no_move_vol = 0, 0.0
    freq, prev_tk = {}, None
    for i, px in enumerate(r.precio):
        tk = int(round(px / tick_size))
        if i > 0 and tk == prev_tk:
            no_move_ticks += 1
            no_move_vol += r.vol[i]
        prev_tk = tk
        freq[tk] = freq.get(tk, 0) + 1
    max_level_ticks = max(freq.values()) if freq else 0

    return Zona(
        start_ts=r.t_start, end_ts=r.t_last, bucket=bucket, dir=r.dir,
        price_upper=r.sw_h, price_lower=r.sw_l, price_mid=(r.sw_h + r.sw_l) / 2.0,
        height_ticks=sweep_ticks, pasos=r.streak, valid_steps=r.valid_steps,
        avg_ms=avg_ms, total_ms=total, vol_rate=vol_rate, total_vol=r.total_vol,
        max_tick_vol=max_tick_vol, cvd_sweep=cvd, buy_vol=buy, sell_vol=sell,
        delta_slope=slope, delta_first=d_first, delta_second=d_second,
        no_move_ticks=no_move_ticks, no_move_vol=no_move_vol,
        max_level_ticks=max_level_ticks)


def run_con_casi(ts_ns, price, volume, tick_size, params=None, skip_primeros=5):
    """Como `run`, pero devuelve `(zonas, casi_zonas)`. Ver `_emitir`."""
    casi: list = []
    z = run(ts_ns, price, volume, tick_size, params, skip_primeros, _casi=casi)
    return z, casi


def run(ts_ns: np.ndarray, price: np.ndarray, volume: np.ndarray, tick_size: float,
        params: Optional[Params] = None, skip_primeros: int = 5,
        _casi: Optional[list] = None) -> List[Zona]:
    """Corre la maquina de estados sobre ticks crudos.

    `price` en PRECIO (no en ticks): el .cs compara contra `TickSize` y persiste precios.
    `skip_primeros` reproduce `if (CurrentBars[1] < 5) return;`. El primer tick usable
    es siempre el indice 1: el 0 no tiene barra previa contra la cual comparar.
    """
    p = params or Params()
    ts_ms = (np.asarray(ts_ns, dtype=np.int64) // 1_000_000)
    px = np.asarray(price, dtype=np.float64)
    vol = np.asarray(volume, dtype=np.float64)

    zonas: List[Zona] = []
    r = _Racha()
    last_side = 0

    def finalizar():
        z = _emitir(r, p, tick_size, _casi)
        if z is not None:
            zonas.append(z)
        r.reset()

    # max(.., 1): el tick 0 no tiene `Closes[ds][1]`. Sin esto, i=0 lee px[-1] y da la
    # vuelta al array, inventando una direccion inicial a partir del ultimo tick.
    for i in range(max(skip_primeros, 1), len(px)):
        cl, cl_p = px[i], px[i - 1]
        ms = float(ts_ms[i] - ts_ms[i - 1])
        v = vol[i]

        side = 1 if cl > cl_p else (-1 if cl < cl_p else last_side)
        if side == 0:
            side = 1
        last_side = side
        signed = side * v

        # En 1 tick, Open == Close, asi que la rama estricta y la laxa coinciden.
        is_down = cl <= cl_p
        is_up = cl >= cl_p

        if r.dir != 0 and ms > p.max_pausa_ms:
            finalizar()
            continue                       # el .cs hace `return`: este tick no inicia

        if r.dir == 0:
            if is_down and is_up:
                pass                       # FIX Flat: el tick plano no inicia racha
            elif is_down:
                r.dir = -1
                _iniciar(r, cl, v, signed, int(ts_ms[i]))
            elif is_up:
                r.dir = 1
                _iniciar(r, cl, v, signed, int(ts_ms[i]))
        else:
            avanza = is_down if r.dir == -1 else is_up
            if avanza:
                _continuar(r, ms, cl, v, signed, int(ts_ms[i]), True)
                r.fails = 0
            else:
                r.fails += 1
                if r.fails <= p.fallos_tolerados:
                    _continuar(r, ms, cl, v, signed, int(ts_ms[i]), False)
                else:
                    finalizar()

    return zonas


def _iniciar(r: _Racha, cl: float, v: float, signed: float, t_ms: int):
    r.streak = 1
    r.valid_steps = 1
    r.fails = 0
    r.sw_h = r.sw_l = cl                   # 1 tick: High == Low == precio
    r.ms.clear()                           # msList arranca VACIA: n intervalos = pasos-1
    r.precio.clear(); r.vol.clear(); r.sign.clear()
    r.precio.append(cl); r.vol.append(v); r.sign.append(signed)
    r.total_vol = v
    r.t_start = r.t_last = t_ms


def _continuar(r: _Racha, ms: float, cl: float, v: float, signed: float, t_ms: int,
               valid: bool):
    r.streak += 1
    if valid:
        r.valid_steps += 1
    r.sw_h = max(r.sw_h, cl)
    r.sw_l = min(r.sw_l, cl)
    r.ms.append(ms)
    r.precio.append(cl); r.vol.append(v); r.sign.append(signed)
    r.total_vol += v
    r.t_last = t_ms
