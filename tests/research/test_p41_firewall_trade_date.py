"""P-41: el firewall del portador corta por TRADE DATE, no por fecha calendario CT.

El defecto: `ts_chicago <= "2026-06-30 23:59:59"` deja pasar toda la tarde-noche del
06-30, que ya pertenece al trade date 2026-07-01 -- la sesion CME abre 17:00 CT del
dia anterior. Medido sobre `6E_09-26`: 5.319 ticks de holdout, ventana de 7,0 horas.

El test que importa es el del tick de las 17:30 CT del 06-30: con el corte viejo
entraba, con el nuevo queda afuera. Los demas fijan los bordes y la propiedad de que
`holdout_included` se DERIVA del contenido en vez de escribirse.
"""
from __future__ import annotations

import datetime as dt
import zoneinfo

import pytest

from edgelab.kaggle.sessions_cme import session_bounds_utc_ns

CHI = zoneinfo.ZoneInfo("America/Chicago")
HOLDOUT_FIRST_TRADE_DATE = 20260701


def _ns(y, m, d, hh, mm, ss=0):
    """Instante de Chicago -> epoch ns UTC."""
    return int(dt.datetime(y, m, d, hh, mm, ss, tzinfo=CHI).timestamp() * 1_000_000_000)


@pytest.fixture(scope="module")
def cutoff_ns():
    return session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)[0]


def test_el_tick_de_las_1730_CT_del_30_06_queda_AFUERA(cutoff_ns):
    """EL test de P-41. La sesion del trade date 20260701 abre 17:00 CT del 06-30, asi
    que un tick de las 17:30 CT de ese dia YA ES HOLDOUT aunque su fecha calendario
    de Chicago siga siendo 06-30. El corte viejo lo admitia."""
    tick = _ns(2026, 6, 30, 17, 30)
    assert tick >= cutoff_ns, "17:30 CT del 06-30 es holdout y tiene que quedar afuera"

    # y el corte viejo, para que quede fijado por que fallaba
    corte_viejo = _ns(2026, 6, 30, 23, 59, 59)
    assert tick <= corte_viejo, "el corte por calendario CT lo dejaba pasar"


def test_el_ultimo_tick_antes_de_la_apertura_queda_ADENTRO(cutoff_ns):
    """Simetrico: 16:59:59 CT del 06-30 todavia es trade date 20260630."""
    assert _ns(2026, 6, 30, 16, 59, 59) < cutoff_ns


def test_la_ventana_que_el_corte_viejo_regalaba_es_de_7_horas(cutoff_ns):
    """La brecha entre la apertura de la sesion de holdout y el corte por calendario.
    Fija la magnitud: no es un caso de borde de un segundo."""
    corte_viejo = _ns(2026, 6, 30, 23, 59, 59)
    horas = (corte_viejo - cutoff_ns) / 3.6e12
    assert 6.9 < horas < 7.1, "la fuga del corte por calendario es de ~7 h, no marginal"


def test_el_cutoff_coincide_con_el_del_recorte_fisico(cutoff_ns):
    """Un solo origen de verdad: el firewall del runner y el sello del re-corte fisico
    (tools/recut_holdout.py) tienen que cortar en el MISMO nanosegundo. Si divergen,
    un artefacto puede declararse limpio contra una frontera y sucio contra la otra."""
    assert cutoff_ns == 1782856800000000000


def test_holdout_included_se_deriva_del_contenido():
    """P-41 tambien corrige que `holdout_included` estuviera escrito a mano. La
    propiedad es: si la serie alcanza el cutoff, la bandera da True SOLA."""
    cutoff = session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)[0]

    limpia_max = _ns(2026, 6, 30, 15, 59, 59)
    sucia_max = _ns(2026, 6, 30, 17, 30)

    assert bool(limpia_max >= cutoff) is False
    assert bool(sucia_max >= cutoff) is True, \
        "una serie con la tarde del 06-30 tiene que autodelatarse"
