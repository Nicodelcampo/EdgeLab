"""Pruebas sintéticas del cotejo; no prueba selección ni cobertura real."""
import importlib.util
from pathlib import Path
import pytest
s=importlib.util.spec_from_file_location('conciliar',Path(__file__).with_name('conciliar_calendario.py'))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)


def cal():
    return [dict(trade_date=d,session_class=c) for d,c in [(20251224,'EARLY_CLOSE'),(20251225,'CLOSED'),(20251226,'NORMAL'),(20251227,'CLOSED'),(20251228,'CLOSED'),(20251229,'NORMAL')]]

def test_holiday_d1_y_fines_de_semana():
    rec=[dict(trade_date=20251225,prev_trade_date=20251224,status='SELECTED'),dict(trade_date=20251226,prev_trade_date=20251225,status='UNDETERMINED'),dict(trade_date=20251229,prev_trade_date=20251226,status='SELECTED')]
    out=m.conciliar(cal(),rec,20251225,20251229); rows={r['trade_date']:r for r in out['filas']}
    assert rows[20251225]['revision']=='CERRADO_CON_REGISTRO'
    assert rows[20251226]['revision']=='ANTERIOR_DIFIERE' and rows[20251226]['prev_cme']==20251224
    assert rows[20251229]['revision']=='ANTERIOR_COINCIDE' and rows[20251229]['prev_cme']==20251226
    assert out['estado']=='DIAGNOSTICO_NO_ELEGIBILIDAD'

def test_cierre_temprano_es_sesion_para_d1_aunque_excluido_de_orb():
    rec=[dict(trade_date=20251226,prev_trade_date=20251224,status='SELECTED')]
    assert m.conciliar(cal(),rec,20251226,20251226)['filas'][0]['revision']=='ANTERIOR_COINCIDE'

def test_sin_registro_y_anterior_desconocido():
    result=m.conciliar(cal(),[dict(trade_date=20251226,prev_trade_date=None,status='SELECTED')],20251226,20251229)
    assert [x['revision'] for x in result['filas']]==['ANTERIOR_REGISTRO_DESCONOCIDO','CERRADO_SIN_REGISTRO','CERRADO_SIN_REGISTRO','SESION_SIN_REGISTRO']

@pytest.mark.parametrize('c', [cal()[1:],cal()[:2]+cal()[3:],cal()+cal()[:1],cal()[:-1]+[dict(trade_date=20251229,session_class='UNKNOWN')]])
def test_calendario_incompleto_duplicado_o_invalido_aborta(c):
    with pytest.raises(ValueError): m.conciliar(c,[],20251226,20251229)

def test_registros_duplicados_y_fuera_de_alcance_aborta():
    rec=dict(trade_date=20251226,prev_trade_date=20251224,status='SELECTED')
    with pytest.raises(ValueError,match='duplicado'): m.conciliar(cal(),[rec,rec],20251226,20251229)
    with pytest.raises(ValueError,match='fuera'): m.conciliar(cal(),[rec],20251229,20251229)

def test_holdout_y_rango_invertido_abortan():
    with pytest.raises(ValueError): m.conciliar(cal(),[],20251226,20261001)
    with pytest.raises(ValueError): m.conciliar(cal(),[],20251229,20251226)
