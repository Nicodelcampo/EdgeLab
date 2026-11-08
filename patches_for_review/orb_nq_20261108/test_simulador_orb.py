import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('sim_orb',Path(__file__).with_name('simulador_orb.py'))
sim=importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name]=sim
spec.loader.exec_module(sim)


def test_r_riesgo_fill_real_y_stop_con_gap():
    o=sim.simular([10,11,12],[101,102,98],senal_ns=9,cierre_ns=20,fin_sesion_ns=30,lado=1,stop=99,friccion_pts=1)
    assert o.motivo=='STOP' and o.entry==101 and o.exit==98 and o.riesgo==2 and o.neto_r==-2


def test_cierre_y_short():
    o=sim.simular([10,11,20],[99,98,96],senal_ns=9,cierre_ns=20,fin_sesion_ns=30,lado=-1,stop=101,friccion_pts=1)
    assert o.motivo=='CIERRE' and o.riesgo==2 and o.neto_r==1


def test_stop_invalido_por_gap_de_entrada_no_abre():
    assert sim.simular([10,11,20],[98,97,96],senal_ns=9,cierre_ns=20,fin_sesion_ns=30,lado=1,stop=99,friccion_pts=1) is None


def test_bloqueo_antes_de_mirar_que_salia_en_stop():
    for prices in ([100,98,101],[100,102,101]):
        assert sim.simular([10,11,20],prices,senal_ns=9,cierre_ns=20,fin_sesion_ns=30,lado=1,stop=99,friccion_pts=1,bloqueos=[(15,16)]) is None


def test_borde_de_noticia_es_cerrado():
    assert sim.simular([10,20],[100,101],senal_ns=9,cierre_ns=20,fin_sesion_ns=30,lado=1,stop=99,friccion_pts=1,bloqueos=[(20,21)]) is None


def test_no_hay_salida_falla_cerrado():
    with pytest.raises(ValueError, match='sin datos de salida'):
        sim.simular([10,11],[100,101],senal_ns=9,cierre_ns=20,fin_sesion_ns=30,lado=1,stop=99,friccion_pts=1)


def test_no_entrar_despues_del_cierre():
    assert sim.simular([20],[100],senal_ns=9,cierre_ns=20,fin_sesion_ns=30,lado=1,stop=99,friccion_pts=1) is None


def test_orden_de_ticks_no_es_ordenable_a_posteriori():
    with pytest.raises(ValueError, match='desordenados'):
        sim.simular([11,10],[100,100],senal_ns=9,cierre_ns=20,fin_sesion_ns=30,lado=1,stop=99,friccion_pts=1)


def test_tick_de_salida_retrasado_que_cruza_noticia_aborta():
    with pytest.raises(ValueError, match='cruza una ventana'):
        sim.simular([10,25],[100,101],senal_ns=9,cierre_ns=20,fin_sesion_ns=30,lado=1,stop=99,friccion_pts=1,bloqueos=[(22,23)])


def test_fill_estrictamente_posterior_a_la_senal_con_tiempos_empatados():
    # Todos los ticks con igual timestamp que la señal son no elegibles.
    o=sim.simular([10,10,11,20],[100,101,102,104],senal_ns=10,cierre_ns=20,fin_sesion_ns=30,
                  lado=1,stop=99,friccion_pts=1)
    assert o.fill_ns==11 and o.entry==102 and o.exit_ns==20
    assert o.riesgo==3 and o.neto_r==pytest.approx(1/3)


def test_solo_ticks_iguales_a_la_senal_no_son_fill():
    assert sim.simular([10,10,20],[100,101,102],senal_ns=10,cierre_ns=20,fin_sesion_ns=30,
                       lado=1,stop=99,friccion_pts=1) is None


def _oraculo_sintetico(times, prices, signal, close, side, stop, cost, blocked):
    """Implementación escalar independiente, exclusivamente para datos sintéticos."""
    if any(a <= close and b >= signal for a, b in blocked):
        return None
    # Selección sin searchsorted, desde el inicio del flujo.
    entry_i = next((i for i, t in enumerate(times) if t > signal), None)
    if entry_i is None or times[entry_i] >= close:
        return None
    entry = prices[entry_i]
    risk = side * (entry - stop)
    if risk <= 0:
        return None
    for i in range(entry_i + 1, len(times)):
        t, price = times[i], prices[i]
        if t >= close:
            if any(a <= t and b >= close for a, b in blocked):
                return 'ERROR'
            return (times[entry_i], t, entry, price, risk, (side * (price-entry)-cost)/risk, 'CIERRE')
        if (side == 1 and price <= stop) or (side == -1 and price >= stop):
            return (times[entry_i], t, entry, price, risk, (side * (price-entry)-cost)/risk, 'STOP')
    return 'ERROR'


def test_oraculo_independiente_aleatorio_sintetico():
    import random
    r = random.Random(20261108)
    for _ in range(1000):
        times = sorted(r.choices(range(8, 28), k=r.randrange(0, 22)))
        prices = [r.randrange(94, 107) for _ in times]
        side = r.choice([-1, 1]); stop = r.randrange(97, 104); cost = r.choice([0, 0.5, 1])
        blocked = [] if r.random() < .6 else [(a := r.randrange(7, 28), a + r.randrange(0, 4))]
        expected = _oraculo_sintetico(times, prices, 10, 20, side, stop, cost, blocked)
        kw = dict(senal_ns=10, cierre_ns=20,fin_sesion_ns=30, lado=side, stop=stop, friccion_pts=cost, bloqueos=blocked)
        if expected == 'ERROR':
            with pytest.raises(ValueError): sim.simular(times, prices, **kw)
            continue
        got = sim.simular(times, prices, **kw)
        if expected is None:
            assert got is None
        else:
            assert (got.fill_ns, got.exit_ns, got.entry, got.exit, got.riesgo, got.motivo) == (*expected[:5], expected[6])
            assert got.neto_r == pytest.approx(expected[5])


def test_no_salida_en_limite_de_sesion_ni_sesion_siguiente():
    for late in (30, 40):
        with pytest.raises(ValueError, match='fuera de la sesión'):
            sim.simular([11, late], [100,101], senal_ns=10, cierre_ns=20,
                        fin_sesion_ns=30, lado=1, stop=99, friccion_pts=1)


def test_cierre_no_puede_coincidir_con_fin_sesion():
    with pytest.raises(ValueError, match='límite de sesión'):
        sim.simular([11,20], [100,101], senal_ns=10, cierre_ns=20,
                    fin_sesion_ns=20, lado=1, stop=99, friccion_pts=1)
