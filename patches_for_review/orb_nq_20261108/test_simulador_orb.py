import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('sim_orb',Path(__file__).with_name('simulador_orb.py'))
sim=importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name]=sim
spec.loader.exec_module(sim)


def test_r_riesgo_fill_real_y_stop_con_gap():
    o=sim.simular([10,11,12],[101,102,98],senal_ns=10,cierre_ns=20,lado=1,stop=99,friccion_pts=1)
    assert o.motivo=='STOP' and o.entry==101 and o.exit==98 and o.riesgo==2 and o.neto_r==-2


def test_cierre_y_short():
    o=sim.simular([10,11,20],[99,98,96],senal_ns=10,cierre_ns=20,lado=-1,stop=101,friccion_pts=1)
    assert o.motivo=='CIERRE' and o.riesgo==2 and o.neto_r==1


def test_stop_invalido_por_gap_de_entrada_no_abre():
    assert sim.simular([10,11,20],[98,97,96],senal_ns=10,cierre_ns=20,lado=1,stop=99,friccion_pts=1) is None


def test_bloqueo_antes_de_mirar_que_salia_en_stop():
    for prices in ([100,98,101],[100,102,101]):
        assert sim.simular([10,11,20],prices,senal_ns=10,cierre_ns=20,lado=1,stop=99,friccion_pts=1,bloqueos=[(15,16)]) is None


def test_borde_de_noticia_es_cerrado():
    assert sim.simular([10,20],[100,101],senal_ns=10,cierre_ns=20,lado=1,stop=99,friccion_pts=1,bloqueos=[(20,21)]) is None


def test_no_hay_salida_falla_cerrado():
    with pytest.raises(ValueError, match='sin datos de salida'):
        sim.simular([10,11],[100,101],senal_ns=10,cierre_ns=20,lado=1,stop=99,friccion_pts=1)


def test_no_entrar_despues_del_cierre():
    assert sim.simular([20],[100],senal_ns=10,cierre_ns=20,lado=1,stop=99,friccion_pts=1) is None


def test_orden_de_ticks_no_es_ordenable_a_posteriori():
    with pytest.raises(ValueError, match='desordenados'):
        sim.simular([11,10],[100,100],senal_ns=10,cierre_ns=20,lado=1,stop=99,friccion_pts=1)


def test_tick_de_salida_retrasado_que_cruza_noticia_aborta():
    with pytest.raises(ValueError, match='cruza una ventana'):
        sim.simular([10,25],[100,101],senal_ns=10,cierre_ns=20,lado=1,stop=99,friccion_pts=1,bloqueos=[(22,23)])
