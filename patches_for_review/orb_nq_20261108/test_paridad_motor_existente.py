"""Paridad acotada sintética del stop ORB con el motor existente.
No compara cierre programado, timestamps empatados, noticias ni huecos de captura.
"""
import importlib.util
from pathlib import Path
import sys
import numpy as np
import pytest
from edgelab.research import areas_expansion as AX

spec=importlib.util.spec_from_file_location('sim_orb_paridad',Path(__file__).with_name('simulador_orb.py'))
sim=importlib.util.module_from_spec(spec); sys.modules[spec.name]=sim; spec.loader.exec_module(sim)

@pytest.mark.parametrize('lado,stop,ticks,esperado', [
    (1,99, [[101,98], [102], [103]], -3),
    (-1,101, [[99,102], [98], [97]], -3),
    (1,99, [[101,102], [100,98], [103]], -3),
    (-1,101, [[99,98], [100,102], [97]], -3),
])
def test_stop_igual_al_motor_existente(lado,stop,ticks,esperado):
    # Barra de señal y tres barras posteriores. Primer tick de cada barra > borde anterior.
    barras=[[100]]+ticks
    px=np.array(sum(barras,[]),float)
    start=np.cumsum([0]+[len(b) for b in barras]).astype(np.int64)
    o=np.array([b[0] for b in barras],float); h=np.array([max(b) for b in barras],float)
    l=np.array([min(b) for b in barras],float); c=np.array([b[-1] for b in barras],float)
    pnl,amb,fill,ex=AX.simular_cierre(np.array([0],np.int64),np.array([lado],np.int64),np.array([2],np.int64),
        np.array([100.]),np.array([stop],float),np.array([1e9 if lado==1 else -1e9]),np.array([0],np.int64),
        o,h,l,c,np.zeros(4,np.int64),.25,px,start)
    ts=[]
    for j,b in enumerate(barras): ts.extend([j*60+i+1 for i in range(len(b))])
    result=sim.simular(ts,px,senal_ns=60,cierre_ns=180,fin_sesion_ns=240,lado=lado,stop=stop,friccion_pts=0)
    assert result.motivo=='STOP'
    assert result.neto_r*result.riesgo == pytest.approx(esperado)
    assert pnl[0] == pytest.approx(esperado)
