"""AACloseOpenDiffs — smoke + la invariante que lo hace distinto.

Lo valioso de este kernel: computa TODO sobre una subserie de 1 minuto, así que
su salida **no depende del `bar_spec` del chart primario**. Es el primer kernel
del proyecto con esa propiedad, y es la que se fija acá: si alguien la rompe, el
indicador pierde justamente lo que lo hacía útil.
"""
import numpy as np
import pytest

from edgelab.bridge import bars as B
from edgelab.bridge.indicators import M1_DRIVEN, REGISTRY, aacloseopendiffs as K
from edgelab.bridge.ticks import TickSeries, make_synthetic

TICK = 0.00005


def _serie(price_ticks, t0_ms=0, dt_ms=6000):
    """Ticks deterministas, uno cada 6 s ⇒ 10 por minuto."""
    import datetime as dt
    base = int(dt.datetime(2026, 6, 3, 12, 0,
                           tzinfo=dt.timezone.utc).timestamp() * 1e9)
    px = np.asarray(price_ticks, np.int64)
    n = len(px)
    return TickSeries(
        ts_ns=np.asarray([base + (t0_ms + i * dt_ms) * 1_000_000
                          for i in range(n)], np.int64),
        price_ticks=px, volume=np.full(n, 1.0),
        bid_ticks=px - 1, ask_ticks=px + 1,
        sequence=np.arange(n, dtype=np.int64), tick_size=TICK,
        instrument="6E", contract="6E 06-26", source="test")


# --------------------------------------------------------------------------- #
# Registro
# --------------------------------------------------------------------------- #
def test_esta_en_el_registry_y_declarado_m1_driven():
    assert REGISTRY["AACloseOpenDiffs"] is K
    assert "AACloseOpenDiffs" in M1_DRIVEN


def test_tiene_identidad_de_kernel_propia():
    from edgelab.bridge.identity import kernel_id, kernel_sources
    assert kernel_id("AACloseOpenDiffs")
    assert "aacloseopendiffs.py" in kernel_sources("AACloseOpenDiffs")


# --------------------------------------------------------------------------- #
# LA invariante: independencia del bar_spec del chart primario
# --------------------------------------------------------------------------- #
def _geom(res):
    return sorted((z["created_ms"], z["top"], z["bottom"],
                   z["features"]["overlap_at_birth"]) for z in res["zones"])


def test_la_salida_NO_depende_del_bar_spec_del_primario():
    """Mismo resultado con barras de tiempo o de tick, de cualquier tamaño.

    Es la propiedad que motiva portar este indicador: marca los gaps de M1
    igual en un chart de 10t, de 25t o de 1 minuto.
    """
    tk = make_synthetic(n_sessions=1, ticks_per_session=20000)
    refs = []
    for bars in (B.build_time_bars(tk, 1), B.build_time_bars(tk, 5),
                 B.build_tick_bars(tk, 10), B.build_tick_bars(tk, 25)):
        refs.append(_geom(K.run(tk, bars, params=None, chart_tz="UTC")))
    assert all(r == refs[0] for r in refs), (
        "la salida cambio con el bar_spec: se perdio la propiedad que hace util "
        "a este kernel")
    assert refs[0], "el fixture debe producir al menos una zona"


def test_ignora_las_barras_del_primario_incluso_si_son_None():
    tk = make_synthetic(n_sessions=1, ticks_per_session=20000)
    a = _geom(K.run(tk, B.build_tick_bars(tk, 25), chart_tz="UTC"))
    b = _geom(K.run(tk, None, chart_tz="UTC"))
    assert a == b


# --------------------------------------------------------------------------- #
# Definición del gap
# --------------------------------------------------------------------------- #
def test_el_gap_es_close_previo_contra_open_actual():
    # minuto 1: ticks 100..109 (cierra en 109) · minuto 2: abre en 120
    seq = list(range(100, 110)) + [120] * 10
    r = K.run(_serie(seq), None, params=dict(min_diff_ticks=1), chart_tz="UTC")
    assert len(r["zones"]) == 1
    z = r["zones"][0]
    assert z["features"]["diff_ticks"] == 11        # |109 - 120|
    assert z["upper_tick"] == 120 and z["lower_tick"] == 109
    assert z["kind"] == "gap_up"


def test_gap_bajista():
    seq = list(range(120, 110, -1)) + [100] * 10    # cierra 111 -> abre 100
    r = K.run(_serie(seq), None, params=dict(min_diff_ticks=1), chart_tz="UTC")
    z = r["zones"][0]
    assert z["kind"] == "gap_down"
    assert z["features"]["diff_ticks"] == 11


def test_min_diff_ticks_filtra():
    seq = [100] * 10 + [102] * 10                   # gap de 2 ticks
    assert len(K.run(_serie(seq), None, params=dict(min_diff_ticks=2))["zones"]) == 1
    assert len(K.run(_serie(seq), None, params=dict(min_diff_ticks=3))["zones"]) == 0


def test_el_ancla_es_el_boundary_no_la_barra_nueva():
    """`Times[1][1]` en el .cs: el gap se ancla en la M1 ANTERIOR."""
    seq = [100] * 10 + [120] * 10
    tk = _serie(seq)
    m1 = B.build_time_bars(tk, 1)
    z = K.run(tk, None, params=dict(min_diff_ticks=1))["zones"][0]
    assert z["created_ms"] == int(m1.end_ns[0] // 1_000_000), (
        "se anclo en la barra nueva en vez del boundary")


# --------------------------------------------------------------------------- #
# overlap_at_birth — la señal
# --------------------------------------------------------------------------- #
def test_una_zona_aislada_nace_con_overlap_1():
    seq = [100] * 10 + [120] * 10
    z = K.run(_serie(seq), None, params=dict(min_diff_ticks=1))["zones"][0]
    assert z["features"]["overlap_at_birth"] == 1


def test_dos_gaps_en_el_mismo_precio_confluyen():
    # gap1: 100->120 · vuelve a 100 · gap2: 100->120 otra vez, se solapan
    seq = ([100] * 10 + [120] * 10 + [100] * 10 + [120] * 10)
    zs = K.run(_serie(seq), None, params=dict(min_diff_ticks=1,
                                              extend_bars=50))["zones"]
    assert len(zs) >= 2
    assert zs[0]["features"]["overlap_at_birth"] == 1
    assert zs[-1]["features"]["overlap_at_birth"] >= 2, (
        "un gap en el mismo rango de precio debe registrar confluencia al nacer")


def test_la_confluencia_expira_con_extend_bars():
    """Una zona vencida ya no confluye.

    Ojo con el borde, que es el del `.cs`: `if (ExpiresM1Bar < StartM1Bar) continue`.
    Con `extend_bars=1` una zona nacida en `b` expira en `b+1` y en `b+1` TODAVIA
    cuenta. Para que no cuente, los gaps tienen que estar a >= 2 barras M1.
    """
    # gap en b=1, minutos planos en el medio, gap en b=4 (fuera de la ventana)
    seq = [100] * 10 + [120] * 10 + [120] * 10 + [120] * 10 + [100] * 10
    zs = K.run(_serie(seq), None, params=dict(min_diff_ticks=1,
                                              extend_bars=1))["zones"]
    assert len(zs) == 2, "el fixture debe dar exactamente 2 gaps"
    assert all(z["features"]["overlap_at_birth"] == 1 for z in zs), (
        "con la ventana vencida no puede haber solape")


def test_el_borde_de_expiracion_es_inclusivo_como_en_el_cs():
    """`expires == start` de la nueva SI cuenta: es la regla del .cs, no un
    detalle de implementacion. Fijarla evita que se 'corrija' por error."""
    seq = [100] * 10 + [120] * 10 + [100] * 10
    zs = K.run(_serie(seq), None, params=dict(min_diff_ticks=1,
                                              extend_bars=1))["zones"]
    assert zs[1]["features"]["overlap_at_birth"] == 2


def test_overlap_no_mira_el_futuro():
    """La primera zona conserva su overlap AL NACER aunque después aparezcan
    otras encima: sin lookahead, que es lo que la hace usable como feature."""
    seq = ([100] * 10 + [120] * 10) * 4
    zs = K.run(_serie(seq), None, params=dict(min_diff_ticks=1,
                                              extend_bars=50))["zones"]
    assert zs[0]["features"]["overlap_at_birth"] == 1


# --------------------------------------------------------------------------- #
# Contrato del REGISTRY
# --------------------------------------------------------------------------- #
def test_devuelve_el_contrato_comun():
    r = K.run(make_synthetic(n_sessions=1, ticks_per_session=8000), None)
    for k in ("indicator", "params", "header", "csv_lines", "events", "zones",
              "params_line"):
        assert k in r, "falta %s en el contrato del REGISTRY" % k
    assert r["indicator"] == "AACloseOpenDiffs"
    assert "bar_spec_independent=true" in r["params_line"]
    assert len(r["csv_lines"]) == len(r["zones"])
