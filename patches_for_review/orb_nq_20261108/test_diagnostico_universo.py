"""Pruebas sólo sintéticas del inventario target-free."""
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('diag_orb',Path(__file__).with_name('diagnostico_universo.py'))
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)


def test_clasifica_sesiones_y_ventana_cerrada_de_noticias():
    cal=[dict(trade_date=20260309,session_class='NORMAL'),
         dict(trade_date=20260310,session_class='EARLY_CLOSE'),
         dict(trade_date=20260311,session_class='CLOSED')]
    # DST de Nueva York: 13:29 UTC = 09:29 ET; el borde toca 09:30.
    eventos=[datetime(2026,3,9,13,29,tzinfo=timezone.utc),
             datetime(2026,3,10,19,57,tzinfo=timezone.utc)] # 15:57 ET, fuera
    out=d.resumir(cal,[20260309,20260310],eventos,20260309,20260311)
    assert out['observadas_por_clase']['NORMAL']==[20260309]
    assert out['observadas_por_clase']['EARLY_CLOSE']==[20260310]
    assert out['sin_grupo_por_clase']['CLOSED']==[20260311]
    assert out['fechas_obs_con_noticia_listada']==[20260309]
    assert out['fechas_obs_sin_noticia_listada']==[20260310]


def test_falta_calendario_falla_cerrado():
    with pytest.raises(ValueError, match='no cubre'):
        d.resumir([dict(trade_date=20260309,session_class='NORMAL')],[],[],20260309,20260310)


def test_rechaza_fecha_fuera_y_holdout():
    cal=[dict(trade_date=20260309,session_class='NORMAL')]
    with pytest.raises(ValueError, match='fuera del rango'):
        d.resumir(cal,[20260310],[],20260309,20260309)
    with pytest.raises(ValueError, match='reservado'):
        d.resumir(cal,[],[],20260309,20261001)


def test_rechaza_duplicados_y_noticia_sin_zona():
    cal=[dict(trade_date=20260309,session_class='NORMAL')]
    with pytest.raises(ValueError, match='duplicada'): d.resumir(cal+cal,[],[],20260309,20260309)
    with pytest.raises(ValueError, match='zona horaria'):
        d.resumir(cal,[20260309],[datetime(2026,3,9,14,0)],20260309,20260309)


@pytest.mark.parametrize('hora_utc,minuto,esperado', [(13,28,False),(13,29,True),(19,56,True),(19,57,False)])
def test_bordes_del_intervalo_en_horario_de_verano(hora_utc,minuto,esperado):
    cal=[dict(trade_date=20260309,session_class='NORMAL')]
    event=datetime(2026,3,9,hora_utc,minuto,tzinfo=timezone.utc)
    out=d.resumir(cal,[20260309],[event],20260309,20260309)
    assert bool(out['fechas_obs_con_noticia_listada']) is esperado


def test_borde_en_horario_de_invierno():
    cal=[dict(trade_date=20260112,session_class='NORMAL')]
    event=datetime(2026,1,12,14,29,tzinfo=timezone.utc)
    assert d.resumir(cal,[20260112],[event],20260112,20260112)['fechas_obs_con_noticia_listada']==[20260112]
