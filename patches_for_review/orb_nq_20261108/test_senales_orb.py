"""Pruebas exclusivamente sintéticas del prototipo target-free ORB."""
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

spec = importlib.util.spec_from_file_location('orb_draft', Path(__file__).with_name('senales_orb.py'))
orb = importlib.util.module_from_spec(spec); spec.loader.exec_module(orb)


def contexto():
    t = pd.date_range('2026-03-10 08:50', periods=181, freq='min', tz='America/New_York').tz_convert('UTC').as_unit('s').asi8
    n = len(t); c = np.full(n, 100.0); h = c + .5; l = c - .5
    # Primera rotura tras cada una de las 3 cajas; es conocida al cierre.
    c[46] = 101.; h[46] = 101.5
    c[56] = 102.; h[56] = 102.5
    c[71] = 103.; h[71] = 103.5
    return dict(t=t, h=h, l=l, c=c, ses=np.full(n, 20260310), seg=np.zeros(n, dtype=int))


def test_tres_rangos_y_primera_ruptura():
    d = orb.disparos(contexto())
    assert list(d.duracion) == [5, 15, 30]
    assert list(d.k) == [46, 56, 71]
    assert list(d.lado) == [1, 1, 1]
    assert list(d.dia) == [1, 1, 1]
    assert list(d.hora) == [0, 0, 0]
    assert d.atr14.notna().all()


def test_corte_por_disparo_es_causal():
    ctx = contexto(); d = orb.disparos(ctx)
    for _, row in d.iterrows():
        k = int(row.k); parcial = {name: arr[:k+1] for name, arr in ctx.items()}
        d2 = orb.disparos(parcial); a = d2[d2.duracion == row.duracion].iloc[0]
        pd.testing.assert_series_equal(row, a, check_names=False)


def test_falta_en_caja_no_se_rellena():
    ctx = contexto(); i = 42
    ctx = {name: np.delete(arr, i) for name, arr in ctx.items()}
    assert orb.disparos(ctx).empty


def test_atr_falla_cerrado_si_hay_hueco():
    ctx = contexto(); i = 35
    ctx = {name: np.delete(arr, i) for name, arr in ctx.items()}
    d = orb.disparos(ctx)
    assert np.isnan(d.loc[d.duracion == 5, 'atr14'].iloc[0])


def test_no_mezcla_segmentos():
    ctx = contexto(); ctx['seg'][42:] = 1
    assert orb.disparos(ctx).empty


def test_datos_fuera_de_orden_fallan():
    ctx = contexto(); ctx['t'][10] = ctx['t'][9]
    with pytest.raises(ValueError): orb.disparos(ctx)


def test_hueco_tras_caja_no_permite_inventar_primera_ruptura():
    ctx = contexto(); i = 45  # 09:35, última vela de la caja de 5
    # En cambio, quitar 09:36 y fijar ruptura posterior.
    i = 46
    ctx = {name: np.delete(arr, i) for name, arr in ctx.items()}
    assert 5 not in orb.disparos(ctx).duracion.tolist()


@pytest.mark.parametrize("fecha,sesion", [("2026-03-06", 20260306), ("2026-03-09", 20260309),
                                           ("2026-11-02", 20261102)])
def test_conversion_reloj_ny_en_cambios_dst_sinteticos(fecha, sesion):
    ctx = contexto(); n = len(ctx['t'])
    ctx['t'] = pd.date_range(fecha + ' 08:50', periods=n, freq='min', tz='America/New_York').tz_convert('UTC').as_unit('s').asi8
    ctx['ses'][:] = sesion
    d = orb.disparos(ctx)
    assert list(d.duracion) == [5, 15, 30]
    assert list(d.hora) == [0, 0, 0]
