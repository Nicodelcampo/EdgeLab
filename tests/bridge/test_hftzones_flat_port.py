"""Fija el comportamiento del puerto Python de HFTZonesESPureV2Flat.

La paridad contra el oraculo NT8 vive en docs/research/paridad_flat.json y no se
re-corre en la suite (necesita el snapshot congelado de 339 MB). Estos tests fijan, con
fixtures chicos y deterministas, las reglas que la paridad exige y que son faciles de
romper sin darse cuenta al refactorizar.
"""
from __future__ import annotations

import numpy as np
import pytest

from edgelab.bridge.kernels.hftzones_es_pure_v2_flat import Params, run

TICK = 0.25
CIERRE_MS = 200       # pausa > max_pausa_ms=50: fuerza Finalizar() y emite la zona
T0 = 1_700_000_000_000


def correr(precios, ms=10, vol=30.0, params=None, skip=1, ref=None):
    """Corre el puerto sobre una serie sintetica.

    `ref` es el tick de referencia ANTERIOR a `precios[0]`: sin el, el primer precio no
    puede iniciar racha porque no tiene `Closes[ds][1]` contra que compararse. Por
    defecto es plano (`precios[0]`), que con el fix Flat no inicia nada.
    """
    if ref is None:
        ref = precios[0]
    inter = [ms] * (len(precios) - 1) if np.isscalar(ms) else list(ms)
    assert len(inter) == len(precios) - 1
    px = np.array([ref] + list(precios) + [precios[-1]], dtype=np.float64)
    dt = np.array([0, 1] + inter + [CIERRE_MS], dtype=np.int64)
    ts_ns = (np.cumsum(dt) + T0) * 1_000_000
    vl = np.full(len(px), vol, dtype=np.float64)
    return run(ts_ns, px, vl, TICK, params or Params(), skip_primeros=skip)


def bajada(n=12, p0=5000.0):
    return [p0 - 0.25 * i for i in range(n)]


ARRIBA = 5000.25      # ref para que la primera bajada inicie racha


# --------------------------------------------------------------------------
# 1. El FIX: un tick plano no inicia racha
# --------------------------------------------------------------------------

def test_una_secuencia_toda_plana_no_produce_ninguna_zona():
    """Antes del fix esto emitia un ABSORB: `isDown` se evaluaba primero y con el precio
    plano `isDown` e `isUp` son AMBOS true, asi que toda racha arrancaba bajista. Sobre
    ticks el precio repite constantemente -> 92% de zonas dir=-1 en 23.863 zonas."""
    assert correr([5000.0] * 15) == []


def test_la_misma_secuencia_plana_SI_calificaria_por_los_demas_filtros():
    """Sin este test el anterior podria pasar por la razon equivocada — volumen
    insuficiente, pocos pasos — y no por el fix."""
    p = Params()
    n, ms, vol = 15, 10, 30.0
    total_ms = (n - 1) * ms
    assert n >= p.min_absorb_pasos                    # califica como ABSORB (sweep = 0)
    assert total_ms <= p.max_total_ms
    assert total_ms / (n - 1) <= p.max_avg_ms
    assert n * vol >= p.min_total_volume
    assert (n * vol) / (total_ms / 1000.0) >= p.min_volume_rate


def test_un_tick_plano_DENTRO_de_una_racha_no_la_corta():
    """El fix toca solo el INICIO. La continuacion queda igual que el .cs: para una
    racha bajista `isDown` es true con precio plano, asi que cuenta como paso valido."""
    precios = bajada(6) + [4998.75] + [5000.0 - 0.25 * i for i in range(6, 12)]
    z = correr(precios, ref=ARRIBA)
    assert len(z) == 1
    assert z[0].dir == -1
    assert z[0].pasos == len(precios)
    assert z[0].valid_steps == len(precios)


# --------------------------------------------------------------------------
# 2. Geometria y conteos
# --------------------------------------------------------------------------

def test_geometria_y_pasos_de_una_bajada_limpia():
    z = correr(bajada(12), ref=ARRIBA)
    assert len(z) == 1
    u = z[0]
    assert u.dir == -1
    assert u.price_upper == pytest.approx(5000.0)
    assert u.price_lower == pytest.approx(5000.0 - 0.25 * 11)
    assert u.height_ticks == pytest.approx(11.0)
    assert u.pasos == 12 and u.valid_steps == 12
    assert u.price_mid == pytest.approx((u.price_upper + u.price_lower) / 2)


def test_avg_ms_usa_pasos_menos_uno_intervalos():
    """`Iniciar` NO agrega a msList: hay `pasos - 1` intervalos, no `pasos`. Confundirlos
    da un avg_ms ~8% bajo con 12 pasos, y eso mueve el bucket."""
    z = correr(bajada(12), ms=10, ref=ARRIBA)
    assert z[0].total_ms == pytest.approx(110.0)      # 11 intervalos
    assert z[0].avg_ms == pytest.approx(10.0)


def test_bucket_por_avg_ms():
    assert correr(bajada(12), ms=2, ref=ARRIBA)[0].bucket == "Predator"    # <= 3
    assert correr(bajada(12), ms=8, ref=ARRIBA)[0].bucket == "Ultra"       # <= 10
    assert correr(bajada(12), ms=13, ref=ARRIBA)[0].bucket == "Fast"       # <= 15


def test_delta_y_volumen_de_una_bajada_son_todos_vendedores():
    z = correr(bajada(12), vol=30.0, ref=ARRIBA)[0]
    assert z.sell_vol == pytest.approx(12 * 30.0)
    assert z.buy_vol == pytest.approx(0.0)
    assert z.cvd_sweep == pytest.approx(-12 * 30.0)
    assert z.total_vol == pytest.approx(12 * 30.0)
    assert z.no_move_ticks == 0                       # ningun precio repetido


# --------------------------------------------------------------------------
# 3. La pausa corta y CONSUME el tick
# --------------------------------------------------------------------------

def test_la_pausa_parte_la_racha_en_dos_y_ninguna_mitad_califica():
    p = Params()
    ms = [10] * 5 + [p.max_pausa_ms + 1] + [10] * 5
    assert correr(bajada(12), ms=ms, ref=ARRIBA) == []


def test_el_tick_de_la_pausa_no_inicia_una_racha_nueva():
    """El .cs hace `return` despues de Finalizar(): ese tick se consume. Si el puerto
    cayera al bloque de inicio, la racha siguiente arrancaria un tick antes y TODOS los
    start_ts quedarian corridos — la paridad se caeria entera."""
    p = Params()
    pausa = p.max_pausa_ms + 1
    ms = [10] * 11 + [pausa] + [10] * 11
    z = correr(bajada(12) + bajada(12, p0=4990.0), ms=ms, ref=ARRIBA)
    assert len(z) == 2
    # la segunda arranca en el tick SIGUIENTE al de la pausa, no en el de la pausa
    assert z[1].start_ts == z[0].end_ts + pausa + 10
    assert z[1].price_upper == pytest.approx(4989.75)   # 4990.00 se consumio


# --------------------------------------------------------------------------
# 4. El warm-up de NT8 y el borde del arranque
# --------------------------------------------------------------------------

def test_skip_primeros_descarta_ticks_del_arranque():
    """`if (CurrentBars[1] < 5) return;`. Con el warm-up puesto, la bajada pierde pasos
    y deja de llegar a min_pasos."""
    assert correr(bajada(12), ref=ARRIBA, skip=1) != []
    assert correr(bajada(12), ref=ARRIBA, skip=6) == []      # ref + 5 ticks descartados


def test_el_primer_tick_nunca_inicia_racha_por_si_solo():
    """Con skip=0 el indice 0 no tiene barra previa. Si el puerto leyera px[-1] daria la
    vuelta al array e inventaria una direccion inicial a partir del ULTIMO tick."""
    a = correr(bajada(12), ref=ARRIBA, skip=0)
    b = correr(bajada(12), ref=ARRIBA, skip=1)
    assert [vars(x) for x in a] == [vars(x) for x in b]
