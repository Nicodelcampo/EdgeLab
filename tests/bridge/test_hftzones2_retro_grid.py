"""HFTZones2 v2.1 — retroceso y altura sobre la grilla ENTERA de ticks.

Regresión del hallazgo ALTO de `docs/audits/AUDIT-001_comparaciones_en_grilla_de_ticks.md`:
`retro > allowed` comparaba `(swh - price) / tick_size` (double) contra un
`allowed` que puede ser un ENTERO exacto (rama del piso `retro_floor_ticks`, o
rama porcentual cuando `pct% × altura` cae en entero). Dividir doubles por
`tick_size` nunca da el entero exacto, así que el empate `retro == allowed` lo
decidía el error de punto flotante — y el `.cs` v2.1 lo resuelve en enteros.

Semántica declarada (contrato de paridad §4): retroceso y altura en índices
enteros de tick; **el empate NO corta la racha** (operador estricto `>`).
El kernel debe espejar al `.cs`: si se toca un solo lado, la paridad se rompe.
"""
import datetime as dt

import numpy as np

from edgelab.bridge import bars as B
from edgelab.bridge.common import snap_to_tick
from edgelab.bridge.indicators import hftzones2
from edgelab.bridge.ticks import TickSeries

NS = 1_000_000_000
TICK = 0.00005          # 6E
BASE = 22817            # nivel donde la aritmética vieja divergía (ver AUDIT-001)
FLOOR = 2               # retro_floor_ticks


# --------------------------------------------------------------------------- #
# 1) El bug que motivó el fix: la aritmética vieja NO es exacta
# --------------------------------------------------------------------------- #
def test_la_division_de_doubles_no_da_el_entero_exacto():
    """En el rango real del 6E, (a-b)/tick_size falla SIEMPRE, en ambos sentidos."""
    arriba = abajo = exacto = 0
    for hi in range(20000, 25001):
        r = (hi * TICK - (hi - FLOOR) * TICK) / TICK      # matemáticamente == 2
        if r > FLOOR:
            arriba += 1
        elif r < FLOOR:
            abajo += 1
        else:
            exacto += 1
    assert exacto == 0, "si esto pasa, el bug original no era reproducible"
    assert arriba > 0 and abajo > 0, "el desvío ocurre en las DOS direcciones"


def test_snap_to_tick_da_la_distancia_exacta_en_todo_el_rango():
    """El fix: diferencias de índices enteros, exactas en todo el rango del 6E."""
    for hi in range(20000, 25001):
        for d in (1, 2, 3, 5, 8, 13):
            lo = hi - d
            assert snap_to_tick(hi * TICK, TICK) - snap_to_tick(lo * TICK, TICK) == d


def test_snap_to_tick_es_away_from_zero_no_bankers():
    """Espejo exacto de PriceToTick del .cs: nunca banker's, nunca floor."""
    assert snap_to_tick(2.5 * TICK, TICK) == 3      # banker's daría 2
    assert snap_to_tick(-2.5 * TICK, TICK) == -3    # away from zero, no hacia -inf


def test_allowed_es_entero_exacto_con_altura_par():
    """La rama porcentual solo empata si pct%×altura cae en entero (altura par)."""
    for altura in (10, 20, 34):
        assert 50.0 / 100.0 * altura == altura // 2   # exacto, sin residuo binario


# --------------------------------------------------------------------------- #
# 2) Integración sobre el kernel: el empate no corta, un tick más sí
# --------------------------------------------------------------------------- #
def _rachas(price_ticks, retro_pct):
    """Corre el kernel y devuelve cuántas rachas (OBS) se exportaron."""
    px = np.asarray(price_ticks, np.int64)
    n = len(px)
    t0 = int(dt.datetime(2026, 6, 3, 12, 0,
                         tzinfo=dt.timezone.utc).timestamp() * NS)
    tk = TickSeries(
        ts_ns=np.asarray([t0 + i * 1_000_000 for i in range(n)], np.int64),
        price_ticks=px, volume=np.full(n, 10.0),
        bid_ticks=px - 1, ask_ticks=px + 1,
        sequence=np.arange(n, dtype=np.int64), tick_size=TICK,
        instrument="6E", contract="6E 06-26", source="test")
    return hftzones2.run(tk, B.build_time_bars(tk, 1), params=dict(
        adaptive_mode=False,            # sin calibración: umbrales manuales
        min_export_valid_steps=1, min_pasos=3, min_absorb_pasos=3,
        retro_floor_ticks=FLOOR, retro_pct_height=retro_pct, fallos_tolerados=1,
        manual_max_pausa_ms=100_000.0, manual_max_total_ms=100_000.0,
        manual_max_avg_ms=100_000.0, manual_min_vol_rate=0.0,
        manual_min_total_vol=0.0))["obs_count"]


def _sube(retro):
    """Sube 11 ticks, retrocede `retro`, vuelve a subir, y corta fuerte al final.

    La racha arranca en el SEGUNDO tick, así que `swl = BASE+1` y la altura al
    momento del retroceso es 10 (par ⇒ `allowed` entero en la rama porcentual).
    Si el retroceso NO corta hay 1 sola racha; si corta, hay 2.
    """
    top = BASE + 11
    return ([BASE + i for i in range(12)] + [top - retro]
            + [top - retro + i for i in range(1, 12)]
            + [top - retro + 11 - 40])


def _baja(retro):
    bot = BASE - 11
    return ([BASE - i for i in range(12)] + [bot + retro]
            + [bot + retro - i for i in range(1, 12)]
            + [bot + retro - 11 + 40])


# --- rama del PISO (pct=0 ⇒ allowed = retro_floor_ticks = 2) ---------------- #
def test_piso_empate_no_corta_al_alza():
    assert _rachas(_sube(FLOOR), 0.0) == 1


def test_piso_un_tick_mas_corta_al_alza():
    assert _rachas(_sube(FLOOR + 1), 0.0) == 2


def test_piso_empate_no_corta_a_la_baja():
    assert _rachas(_baja(FLOOR), 0.0) == 1


def test_piso_un_tick_mas_corta_a_la_baja():
    assert _rachas(_baja(FLOOR + 1), 0.0) == 2


# --- rama PORCENTUAL (pct=50, altura=10 ⇒ allowed = 5 exacto) --------------- #
def test_pct_empate_no_corta_al_alza():
    assert _rachas(_sube(5), 50.0) == 1


def test_pct_un_tick_mas_corta_al_alza():
    assert _rachas(_sube(6), 50.0) == 2


def test_pct_empate_no_corta_a_la_baja():
    assert _rachas(_baja(5), 50.0) == 1


def test_pct_un_tick_mas_corta_a_la_baja():
    assert _rachas(_baja(6), 50.0) == 2
