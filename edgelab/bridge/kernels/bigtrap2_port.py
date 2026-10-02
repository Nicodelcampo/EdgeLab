"""Puerto Python de BigTrap2 (NT8 v2.5.2) — corre sobre ticks crudos.

POR QUE ES MUCHO MAS SIMPLE QUE EL .cs
======================================
El `.cs` dedica ~400 lineas a ANCLAR la subserie de 1 tick contra las barras primarias:
`DrenarPorOHLCV`, `Abstener`, `CoincideOHLCV`, `VerificarOHLC`, los contadores de
residuales y mismatch. Todo eso existe porque NT8 entrega dos series separadas y hay que
alinearlas sin adivinar.

Aca las barras se CONSTRUYEN desde los mismos ticks, asi que footprint y barra son el
mismo objeto por construccion. No hay anclaje, ni abstencion, ni mismatch.

CONSECUENCIA QUE HAY QUE MEDIR, NO ASUMIR
=========================================
NT8 se ABSTIENE de barras que no puede anclar (`nAbstenciones`, `nSnapsSalteados`) y ahi
no emite nada. Este puerto no tiene motivo para saltearlas, asi que puede emitir TRAPs
donde el original no emitio. Eso es una diferencia ESPERADA, no un bug, y la paridad la
cuantifica en vez de esconderla.

ARITMETICA EN ENTEROS
=====================
El `.cs` documenta un bug de 1 ULP que producia 101 falsos positivos (12,5% de las zonas)
al comparar el precio reconstruido contra el del feed en `double`. Por eso toda
comparacion fila-vs-close va en MEDIOS TICKS enteros, y el redondeo es
`AwayFromZero` -- nunca floor ni truncado.

Se replica exactamente: `closeHalfTick = 2*round_away(close/tick)`, y
`rowCenterHalfTick = 2*row*rowTicks + (rowTicks-1)`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np


def round_away(x: float) -> int:
    """Math.Round(x, MidpointRounding.AwayFromZero) de C#.

    numpy y Python usan banker's rounding: round(0.5)=0, round(2.5)=2. C# con
    AwayFromZero da 1 y 3. La diferencia es exactamente el off-by-one que el .cs
    documenta como origen de 101 falsos positivos.
    """
    return int(np.floor(x + 0.5)) if x >= 0 else int(np.ceil(x - 0.5))


def floor_div(a: int, b: int) -> int:
    """FloorDiv del .cs: division entera hacia -infinito, tambien para negativos."""
    q = a // b          # Python ya redondea hacia -inf
    return int(q)


@dataclass
class Params:
    """Defaults del oraculo 6E tick:25 (encabezado de BigTrap2_diag_tick25_6E_0926.csv)."""
    ticks_per_row: int = 1
    imbalance_ratio: float = 3.0
    imbalance_mode: str = "Diagonal"        # "Diagonal" | "Horizontal"
    trap_volume_source: str = "AggressiveSide"   # "AggressiveSide" | "Total"
    use_wick_filter: bool = True
    wick_zone_pct: float = 30.0
    min_delta_filter: float = 0.0
    min_export_volume: float = 0.0
    bar_ticks: int = 25                     # bar_spec: N ticks por barra


@dataclass
class Trap:
    bar: int
    ts_ns: int
    side: str                # trapped_buyers | trapped_sellers
    vol: float
    centroid: float
    zone_lo: float
    zone_hi: float
    n_rows: int
    max_ratio: float
    close: float
    bar_vol: float
    fp_vol: float
    n_quote: int
    n_rule: int


@dataclass
class _Barra:
    i0: int
    i1: int
    ts_ns: int
    o: float
    h: float
    l: float
    c: float
    vol: float


def construir_barras(price: np.ndarray, ts_ns: np.ndarray, vol: np.ndarray,
                     bar_ticks: int) -> List[_Barra]:
    """Barras de N TRADES (bar_spec de tick de NT8: cuenta impresiones, no volumen)."""
    n = len(price)
    out: List[_Barra] = []
    for i0 in range(0, n, bar_ticks):
        i1 = min(i0 + bar_ticks, n)
        p = price[i0:i1]
        out.append(_Barra(i0=i0, i1=i1, ts_ns=int(ts_ns[i1 - 1]),
                          o=float(p[0]), h=float(p.max()), l=float(p.min()),
                          c=float(p[-1]), vol=float(vol[i0:i1].sum())))
    return out


def clasificar_lado(price: np.ndarray, bid: Optional[np.ndarray],
                    ask: Optional[np.ndarray]) -> tuple:
    """`bidask_then_tickrule`, exactamente como AccumulateTick del .cs.

    Devuelve (side, by_quote). side en {+1 compra agresiva, -1 venta agresiva}.
    El fallback arrastra la ultima direccion; el primer tick sin informacion es +1,
    declarado en el contrato del indicador.
    """
    n = len(price)
    side = np.zeros(n, dtype=np.int8)
    by_quote = np.zeros(n, dtype=bool)
    if bid is not None and ask is not None:
        ok = (ask > 0) & (bid > 0) & (ask >= bid)
        compra = ok & (price >= ask)
        venta = ok & (price <= bid) & ~compra
        side[compra] = 1
        side[venta] = -1
        by_quote[compra | venta] = True
    # fallback tick rule, secuencial porque arrastra estado
    ultimo_precio = np.nan
    ultima_dir = 0
    for i in range(n):
        if side[i] == 0:
            s = 0
            if not np.isnan(ultimo_precio):
                if price[i] > ultimo_precio:
                    s = 1
                elif price[i] < ultimo_precio:
                    s = -1
                else:
                    s = ultima_dir
            if s == 0:
                s = 1
            side[i] = s
        ultimo_precio = price[i]
        ultima_dir = side[i]
    return side, by_quote


def _procesar_barra(b: _Barra, ticks_px: np.ndarray, ticks_vol: np.ndarray,
                    lado: np.ndarray, by_quote: np.ndarray, tick_size: float,
                    p: Params, idx_barra: int) -> List[Trap]:
    """ProcessBar + EmitSide del .cs."""
    rt = max(1, p.ticks_per_row)
    sl = slice(b.i0, b.i1)
    px_t = ticks_px[sl]
    vl = ticks_vol[sl]
    sd = lado[sl]

    row_ask: Dict[int, float] = {}
    row_bid: Dict[int, float] = {}
    for t, v, s in zip(px_t, vl, sd):
        r = floor_div(int(t), rt)
        if s > 0:
            row_ask[r] = row_ask.get(r, 0.0) + float(v)
        else:
            row_bid[r] = row_bid.get(r, 0.0) + float(v)
    if not row_ask and not row_bid:
        return []

    close_half = 2 * round_away(b.c / tick_size)
    rango = b.h - b.l
    wick_hi_floor = b.h - rango * (p.wick_zone_pct / 100.0)
    wick_lo_ceil = b.l + rango * (p.wick_zone_pct / 100.0)

    acc = {True: dict(vol=0.0, wsum=0.0, rows=0, lo=None, hi=None, mr=0.0),
           False: dict(vol=0.0, wsum=0.0, rows=0, lo=None, hi=None, mr=0.0)}

    for r in sorted(set(row_ask) | set(row_bid)):
        a = row_ask.get(r, 0.0)
        bb = row_bid.get(r, 0.0)
        if abs(a - bb) < p.min_delta_filter:
            continue
        if p.imbalance_mode == "Diagonal":
            b_dn = row_bid.get(r - 1, 0.0)
            a_up = row_ask.get(r + 1, 0.0)
            buy_ratio = a / max(b_dn, 1.0)
            sell_ratio = bb / max(a_up, 1.0)
        else:
            buy_ratio = a / max(bb, 1.0)
            sell_ratio = bb / max(a, 1.0)

        row_price = (r * rt + (rt - 1) / 2.0) * tick_size
        row_half = 2 * r * rt + (rt - 1)
        agresivo = p.trap_volume_source == "AggressiveSide"
        contrib_buy = a if agresivo else (a + bb)
        contrib_sell = bb if agresivo else (a + bb)

        if (a >= 1 and buy_ratio >= p.imbalance_ratio and row_half > close_half
                and (not p.use_wick_filter or (rango > 0 and row_price >= wick_hi_floor))):
            d = acc[True]
            d["vol"] += contrib_buy
            d["wsum"] += row_price * contrib_buy
            d["rows"] += 1
            d["lo"] = r if d["lo"] is None else min(d["lo"], r)
            d["hi"] = r if d["hi"] is None else max(d["hi"], r)
            d["mr"] = max(d["mr"], buy_ratio)

        if (bb >= 1 and sell_ratio >= p.imbalance_ratio and row_half < close_half
                and (not p.use_wick_filter or (rango > 0 and row_price <= wick_lo_ceil))):
            d = acc[False]
            d["vol"] += contrib_sell
            d["wsum"] += row_price * contrib_sell
            d["rows"] += 1
            d["lo"] = r if d["lo"] is None else min(d["lo"], r)
            d["hi"] = r if d["hi"] is None else max(d["hi"], r)
            d["mr"] = max(d["mr"], sell_ratio)

    fp_vol = float(vl.sum())
    n_quote = int(by_quote[sl].sum())
    n_rule = int(len(sd) - n_quote)

    out: List[Trap] = []
    for is_bull in (True, False):
        d = acc[is_bull]
        if d["rows"] == 0 or d["vol"] <= 0 or d["vol"] < p.min_export_volume:
            continue
        lo_tick = d["lo"] * rt
        hi_tick = (d["hi"] + 1) * rt - 1
        out.append(Trap(
            bar=idx_barra, ts_ns=b.ts_ns,
            side="trapped_buyers" if is_bull else "trapped_sellers",
            vol=d["vol"], centroid=d["wsum"] / d["vol"],
            zone_lo=lo_tick * tick_size - tick_size / 2.0,
            zone_hi=hi_tick * tick_size + tick_size / 2.0,
            n_rows=d["rows"], max_ratio=d["mr"], close=b.c,
            bar_vol=b.vol, fp_vol=fp_vol, n_quote=n_quote, n_rule=n_rule))
    return out


def run(ts_ns: np.ndarray, price_ticks: np.ndarray, volume: np.ndarray,
        tick_size: float, bid_ticks=None, ask_ticks=None,
        params: Optional[Params] = None) -> List[Trap]:
    """Corre BigTrap2 sobre ticks crudos y devuelve los eventos TRAP.

    `price_ticks`, `bid_ticks`, `ask_ticks` en TICKS ENTEROS (no en precio).
    """
    p = params or Params()
    px_t = np.asarray(price_ticks, dtype=np.int64)
    precio = px_t * tick_size
    vol = np.asarray(volume, dtype=np.float64)
    bid = None if bid_ticks is None else np.asarray(bid_ticks, dtype=np.int64) * tick_size
    ask = None if ask_ticks is None else np.asarray(ask_ticks, dtype=np.int64) * tick_size

    lado, by_quote = clasificar_lado(precio, bid, ask)
    barras = construir_barras(precio, np.asarray(ts_ns, dtype=np.int64), vol, p.bar_ticks)

    traps: List[Trap] = []
    for i, b in enumerate(barras):
        traps.extend(_procesar_barra(b, px_t, vol, lado, by_quote, tick_size, p, i))
    return traps
